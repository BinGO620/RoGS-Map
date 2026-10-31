#!/usr/bin/env python
"""dyn_probe.py — 建图/渲染侧「保留动态」生死筛（离线，本地 2060；零核心代码改动）。

问题：现行系统是"反动态"范式（`SemanticMask.mask_mapping/mask_insertion` 均开），
动态物体**既不进建图损失也不进插入** ⇒ 地图里要么没有它（洞）、要么留早期残影。
本探针在同一张**冻结地图**上量化"保留动态"这一族机制的空间（天花板与代价）。

子命令
------
`materials`  内容判据（跑前，不产生任何渲染指标）：
             ① 7 序列掩码面积表（选序列用）；② 冻结地图的残影盘点
             （把 PLY 高斯投影进各帧，统计落在动态掩码内的点数/占比）——
             回答"交接笔记里'只对掩码内已有高斯拟合形变'是否有料可做"。
`render`     四臂阶梯（判据锁定后跑，见 results/embrace_dyn/evidence/prereg_dyn_probe.md）：
             P1 erase（冻结地图原样） / P2 逐帧瞬态插入（天花板，含局部拟合） /
             C- 错位对照（P2 拟合结果 + 固定偏移 ⇒ 仪器判别力自检） /
             P4 烘焙（t0 插入并拟合后冻结，永不再更新 ⇒ 朴素做法的鬼影代价）

指标口径（全部逐帧、配对；同一地图/同位姿/同帧 ⇒ 无 seed 噪声）
  dyn_psnr      掩码内 PSNR（DynaGSLAM 的 DynaPSNR 协议的我们实现；另要求 GT 深度有效）
  dyn_dl1_cm    掩码内**惩罚式**深度 L1（洞按 d_max 计罚，与项目 P-A 同函数）
  dyn_cov       掩码内渲染覆盖率（不透明度 ≥ a_eval）
  full_psnr     全图 PSNR（与 render_compare.py 同口径，用于阳性对照）
  static_psnr   静态区 PSNR（utils.static_eval.static_background_metrics，同源）
  ghost_excess  残影对比（vacated_contrast_metrics，同源）
  n_dyn         插入的动态基元数（成本列）

用法
  PY=/data/conda_envs/monogs-ours/bin/python
  $PY scripts/02_analysis/dyn_probe.py materials --out results/embrace_dyn/evidence/materials_dyn_probe.json
  $PY scripts/02_analysis/dyn_probe.py render --config configs/experiments/embrace_dyn/probe_pt2.yaml
"""
import argparse
import bisect
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
os.chdir(REPO)

import yaml  # noqa: E402
from munch import munchify  # noqa: E402

from gaussian_splatting.gaussian_renderer import render  # noqa: E402
from gaussian_splatting.scene.gaussian_model import GaussianModel  # noqa: E402
from gaussian_splatting.utils.graphics_utils import getProjectionMatrix2  # noqa: E402
from gaussian_splatting.utils.image_utils import psnr  # noqa: E402
from utils.camera_utils import Camera  # noqa: E402
from utils.dataset import load_dataset  # noqa: E402
from utils.eval_utils import _undistort_depth_like  # noqa: E402
from utils.static_eval import (  # noqa: E402
    masked_psnr,
    penalized_depth_l1_cm,
    static_background_metrics,
    static_coverage,
    vacated_contrast_metrics,
)

BONN_SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3", "person_tracking", "person_tracking2"]


# ────────────────────────── 通用读取 ──────────────────────────

def sh_degree_from_ply(ply_path):
    """与 render_compare.py 同法：从 PLY header 反推 max_sh_degree。"""
    n_rest = 0
    with open(ply_path, "rb") as fh:
        while True:
            line = fh.readline()
            if not line:
                break
            s = line.decode("ascii", errors="strict").strip()
            if s.startswith("property float f_rest_"):
                n_rest += 1
            if s == "end_header":
                break
    if n_rest == 0:
        return 0
    d = int(round((n_rest / 3 + 1) ** 0.5 - 1))
    assert 3 * ((d + 1) ** 2 - 1) == n_rest, f"f_rest 数 {n_rest} 与整 degree 不符"
    return d


class Run:
    """一个冻结 run 的只读句柄：config / dataset / 高斯 / 位姿 / 掩码索引。"""

    def __init__(self, run_dir, ply="final_after_opt", device="cuda:0", mask_subdir="auto", mask_class=15):
        self.run_dir = str(Path(run_dir).resolve())
        self.device = device
        self.config = yaml.safe_load(open(os.path.join(self.run_dir, "config.yml")))
        self.model_params = munchify(self.config["model_params"])
        self.pipeline_params = munchify(self.config["pipeline_params"])
        self.bg = torch.tensor([0.0, 0.0, 0.0], dtype=torch.float32, device=device)
        self.dataset = load_dataset(self.model_params, self.model_params.source_path, config=self.config)
        self.dataset.device = device
        self.W, self.H = self.dataset.width, self.dataset.height
        self.proj = getProjectionMatrix2(
            znear=0.01, zfar=100.0, fx=self.dataset.fx, fy=self.dataset.fy,
            cx=self.dataset.cx, cy=self.dataset.cy, W=self.W, H=self.H,
        ).transpose(0, 1).to(device=device)
        hits = sorted(Path(self.run_dir).glob(f"point_cloud/{ply}/point_cloud.ply")) or \
            sorted(Path(self.run_dir).glob("point_cloud/final/point_cloud.ply"))
        assert hits, f"no PLY in {self.run_dir}"
        self.ply_path = str(hits[0])
        self.sh_deg = sh_degree_from_ply(self.ply_path)
        self.gaussians = GaussianModel(self.sh_deg, config=self.config)
        self.gaussians.load_ply(self.ply_path)
        # 位姿（trj_est = C2W）
        trj = json.load(open(os.path.join(self.run_dir, "plot/trj_full_final.json")))
        ids = [int(v) for v in trj["trj_id"]]
        self.pose_by_id = {i: np.asarray(p, dtype=np.float64) for i, p in zip(ids, trj["trj_est"])}
        self.N = self.dataset.num_imgs
        self.depth_paths = getattr(self.dataset, "depth_paths", None)
        self.color_paths = getattr(self.dataset, "color_paths", None)
        # 掩码索引（gtmc 优先，其次 seg_mask）
        self.mask_subdir = mask_subdir
        self.mask_class = mask_class
        self._init_masks()
        self._depth_cache = {}

    def _init_masks(self):
        self.mask_index, self.mask_source = {}, None
        cands = ["dynamic_mask"] if self.mask_subdir == "auto" else [self.mask_subdir]  # 重构：canonical 优先
        ds_path = self.config["Dataset"].get("dataset_path", "")
        from utils.gtmc_mask import frozen_mask_index
        for sub in cands:
            if sub == "none":
                continue
            idx = frozen_mask_index(os.path.join(ds_path, sub))
            if idx:
                self.mask_index, self.mask_source = idx, sub
                break
        ts = sorted((float(k), v) for k, v in self.mask_index.items() if _is_ts(k))
        self._mask_ts_keys = [t for t, _ in ts]
        self._mask_ts = ts

    def frame_mask(self, idx):
        """动态掩码 (H,W) bool；三级匹配（depth stem → RGB stem → 最近邻 ts），
        与 render_compare.py:239-256 同协议。"""
        if not self.mask_index or self.depth_paths is None or idx >= len(self.depth_paths):
            return None
        stem = os.path.splitext(os.path.basename(self.depth_paths[idx]))[0]
        mp = self.mask_index.get(stem)
        if mp is None and self.color_paths is not None and idx < len(self.color_paths):
            mp = self.mask_index.get(os.path.splitext(os.path.basename(self.color_paths[idx]))[0])
        if mp is None and _is_ts(stem):
            mp = self._nearest_mask(float(stem), tol=0.05)
        if mp is None:
            return None
        if self.mask_source == "seg_mask":
            from PIL import Image
            a = np.asarray(Image.open(mp).convert("L"))
            return a == self.mask_class
        from utils.gtmc_mask import load_frozen_mask
        return load_frozen_mask(mp)

    def _nearest_mask(self, ts, tol=0.05):
        if not self._mask_ts_keys:
            return None
        i = bisect.bisect_left(self._mask_ts_keys, ts)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(self._mask_ts_keys):
                d = abs(self._mask_ts_keys[j] - ts)
                if best is None or d < best[0]:
                    best = (d, self._mask_ts[j][1])
        return best[1] if best is not None and best[0] <= tol else None

    def frame_data(self, idx):
        """(gt_image(C,H,W) [0,1] on device, gt_depth undistorted (H,W) tensor, w2c 4x4 numpy)。"""
        if idx not in self.pose_by_id:
            return None
        gt_image, gt_depth, _ = self.dataset[idx]
        if not torch.is_tensor(gt_image):
            gt_image = torch.as_tensor(gt_image, device=self.device)
        gt_image = gt_image.to(self.device).float()
        if gt_image.dim() == 3 and gt_image.shape[0] != 3:
            gt_image = gt_image.permute(2, 0, 1)
        if gt_image.max() > 1.5:
            gt_image = gt_image / 255.0
        gd = None
        if gt_depth is not None:
            gdu = _undistort_depth_like(self.dataset, gt_depth)
            gd = torch.as_tensor(np.asarray(gdu), device=self.device, dtype=torch.float32)
        return gt_image, gd, np.linalg.inv(self.pose_by_id[idx])

    def camera(self, idx, w2c):
        cam = Camera(uid=idx, color=None, depth=None, gt_T=torch.eye(4, device=self.device),
                     projection_matrix=self.proj, fx=self.dataset.fx, fy=self.dataset.fy,
                     cx=self.dataset.cx, cy=self.dataset.cy, fovx=self.dataset.fovx,
                     fovy=self.dataset.fovy, image_height=self.H, image_width=self.W, device=self.device)
        cam.update_RT(torch.as_tensor(w2c[:3, :3], dtype=torch.float32, device=self.device),
                      torch.as_tensor(w2c[:3, 3], dtype=torch.float32, device=self.device))
        return cam


def _is_ts(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


# ────────────────────────── 动态基元（只读渲染视图 + 插入） ──────────────────────────

class PackedPC:
    """静态高斯 + 动态基元的只读渲染视图。

    `gaussian_renderer.render` 只读对象的 `get_xyz / get_opacity / get_scaling /
    get_rotation / get_features`（**属性而非方法**）+ `active_sh_degree / max_sh_degree`
    ⇒ 本类无需改动 GaussianModel 即可组合渲染（核心代码零改动）。
    """

    def __init__(self, base):
        self.max_sh_degree = base.max_sh_degree
        self.active_sh_degree = base.active_sh_degree
        self.static = (base.get_xyz.detach(), base.get_opacity.detach(), base.get_scaling.detach(),
                       base.get_rotation.detach(), base.get_features.detach())
        self.n_static = int(self.static[0].shape[0])
        self.set_dynamic(None)

    def set_dynamic(self, dyn):
        """dyn = dict(xyz, opacity(已激活), scaling(已激活), rotation(已归一), features) 或 None。"""
        if dyn is None:
            self.get_xyz, self.get_opacity, self.get_scaling, self.get_rotation, self.get_features = self.static
            self.n_dyn = 0
            return
        self.get_xyz = torch.cat([self.static[0], dyn["xyz"]], 0)
        self.get_opacity = torch.cat([self.static[1], dyn["opacity"]], 0)
        self.get_scaling = torch.cat([self.static[2], dyn["scaling"]], 0)
        self.get_rotation = torch.cat([self.static[3], dyn["rotation"]], 0)
        self.get_features = torch.cat([self.static[4], dyn["features"]], 0)
        self.n_dyn = int(dyn["xyz"].shape[0])


def unproject_mask(run, idx, gt_image, gt_depth, w2c, stride=2, dmin=0.2, dmax=8.0, mask_override=None):
    """掩码内像素 + 深度 → 世界坐标点与颜色（供插入动态基元）。

    `mask_override` 可传入自定掩码（如最大连通域）——用于因果轮 II 的掩码稳定消融。

    只对 `mask ∧ valid depth ∧ valid rgb` 的像素做反投影；`stride` 像素下采样
    （固定值，所有臂同口径）。返回 (points_world (N,3) float32, colors (N,3) [0,1])。
    """
    dyn = run.frame_mask(idx) if mask_override is None else mask_override
    if dyn is None or gt_depth is None:
        return None, None
    m = np.asarray(dyn, dtype=bool) & np.isfinite(np.asarray(gt_depth.cpu())) & \
        (np.asarray(gt_depth.cpu()) > dmin) & (np.asarray(gt_depth.cpu()) < dmax)
    vs, us = np.nonzero(m)
    keep = ((vs % stride) == 0) & ((us % stride) == 0)
    vs, us = vs[keep], us[keep]
    if vs.size == 0:
        return None, None
    d = np.asarray(gt_depth.cpu())[vs, us].astype(np.float64)
    x = (us - run.dataset.cx) * d / run.dataset.fx
    y = (vs - run.dataset.cy) * d / run.dataset.fy
    pc = np.stack([x, y, d], 1)
    c2w = np.linalg.inv(w2c)
    pw = (c2w[:3, :3] @ pc.T).T + c2w[:3, 3]
    rgb = gt_image.permute(1, 2, 0).detach().cpu().numpy()[vs, us]
    return pw.astype(np.float32), rgb.astype(np.float32)


def make_dynamic(run, run_dyn_model, points, colors, opacity_floor=None):
    """按**仓库自身插入约定**建动态基元（`_gaussians_from_points`：KNN 尺度 + RGB2SH +
    反 sigmoid(0.5) 不透明度），返回可微参数字典（raw 参数空间，供局部拟合）。
    """
    import torch.nn as nn
    point_size = float(run.config["Dataset"]["point_size"])
    pts = torch.as_tensor(points, dtype=torch.float32, device=run.device)
    cols = torch.as_tensor(colors, dtype=torch.float32, device=run.device)
    xyz, feats, log_scales, rots, opa = run_dyn_model._gaussians_from_points(pts, cols, point_size)
    # feats: (N,3,K) → 拆 dc/rest（与 GaussianModel.get_features 的 (N,K,3) 布局对接）
    K = feats.shape[2]
    dc = feats[:, :, 0:1].transpose(1, 2).contiguous()
    rest = feats[:, :, 1:].transpose(1, 2).contiguous()
    if opacity_floor is not None:  # 仅诊断用（默认 None：不偏离仓库约定）
        opa = torch.full_like(opa, float(opacity_floor))
    return {
        "xyz": nn.Parameter(xyz.detach().clone()),
        "log_scale": nn.Parameter(log_scales.detach().clone()),
        "rot": nn.Parameter(rots.detach().clone()),
        "opa": nn.Parameter(opa.detach().clone()),
        "dc": nn.Parameter(dc.detach().clone()),
        "rest": rest.detach(),
        "K": K,
    }


def dyn_tensors(d):
    """raw 参数 → 渲染所需激活值。

    `d["rho"]`（P0 在线臂的存在量 logit，(N,1)）可选：有效不透明度 = σ(opa)·σ(ρ)。
    无 rho 键的臂行为不变（既有单测 `test_dyn_tensors_ranges` 守护）。
    """
    feat = torch.cat([d["dc"], d["rest"]], 1)  # (N,K,3)
    opa = torch.sigmoid(d["opa"])
    if d.get("rho") is not None:
        opa = opa * torch.sigmoid(d["rho"])
    return {
        "xyz": d["xyz"],
        "opacity": opa,
        "scaling": torch.exp(d["log_scale"]),
        "rotation": torch.nn.functional.normalize(d["rot"], dim=1),
        "features": feat,
    }


def translate(d, delta):
    """返回平移后的 raw 参数字典副本（用于错位对照/烘焙快照）。"""
    out = dict(d)
    out["xyz"] = d["xyz"] + torch.as_tensor(delta, dtype=torch.float32, device=d["xyz"].device)
    return out


def with_xyz(d, new_xyz):
    """返回把 xyz 换掉（tensor 或 numpy）的 raw 参数字典副本。"""
    out = dict(d)
    out["xyz"] = (new_xyz if torch.is_tensor(new_xyz) else
                  torch.as_tensor(np.asarray(new_xyz), dtype=torch.float32, device=d["xyz"].device))
    return out


def largest_cc(mask):
    """掩码的最大连通域（8 邻接）。消融 F5：KF 掩码碎片化时只取主连通域。"""
    from scipy import ndimage
    m = np.asarray(mask, dtype=bool)
    if m.sum() == 0:
        return m
    lab, n = ndimage.label(m, structure=np.ones((3, 3), dtype=int))
    if n <= 1:
        return m
    sizes = ndimage.sum(m, lab, index=np.arange(1, n + 1))
    return lab == (int(np.argmax(sizes)) + 1)


def median_velocity(pts_k, pts_kprev, gap):
    """中位质心平移速度（m/帧）——比均值抗掩码形状漂移（F4 根因）。"""
    a = np.median(np.asarray(pts_k, dtype=float), axis=0)
    b = np.median(np.asarray(pts_kprev, dtype=float), axis=0)
    return (a - b) / float(max(gap, 1))


def rigid_between(A, B, iters=3, keep_pct=80.0):
    """估计把 A（较早 KF 的 CC 点云）对齐到 B（较晚 KF）的刚性变换 (R,u) 与残差。

    三轮 NN + Umeyama（无尺度），每轮保留最近 keep_pct% 对应以抗部分可见/外点。
    """
    from scipy.spatial import cKDTree
    from evo.core import geometry
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    src = A.copy()
    R_acc, u_acc = np.eye(3), np.zeros(3)
    tree = cKDTree(B)
    d = np.zeros(len(src))
    for _ in range(max(1, iters)):
        d, idx = tree.query(src)
        keep = d <= np.percentile(d, keep_pct) if d.size > 10 else np.ones_like(d, dtype=bool)
        if keep.sum() < 4:
            keep = np.ones_like(d, dtype=bool)
        R, u, _c = geometry.umeyama_alignment(src[keep].T, B[idx[keep]].T, with_scale=False)
        src = (R @ src.T).T + u
        R_acc = R @ R_acc
        u_acc = R @ u_acc + u
    rmse = float(np.sqrt(np.mean(d ** 2))) if d.size else None
    return R_acc, u_acc, rmse


def pointwise_velocity(pts_new, pts_prev, lam_d=0.05, d_bar=None):
    """逐基元 KNN 速度（文献 V2 / DynaGSLAM T2 的离线近似）。

    对 `pts_new` 中每个点在前一帧点云 `pts_prev` 里找 1-NN；距离 ≤ λ_d·d̄ 则
    v=(p−q)/Δ（Δ=1 帧），否则 v=0。返回 (v (N,3), matched_frac, d_bar)。

    **d̄ 的解释（关键，且必须落盘）**：文献只给记号 `λ_d·d̄`。首次实现把 d̄ 取成
    点云**内部 NN 间距**（≈1mm）⇒ 阈值≈1mm ⇒ 几乎无匹配（该臂退化为不动的臂）。
    现取 **d̄ = 掩码内平均深度**（距离量纲，≈2.6m）⇒ 阈值 = λ_d·d̄ ≈ 13cm（λ_d=0.05），
    即"位移在深度的 5% 以内才认为可复用"。相机系深度由调用方给出。
    **不做任何整团估计** ⇒ 抗掩码形状漂移（F4/F9 的根因）。
    """
    from scipy.spatial import cKDTree
    A = np.asarray(pts_new, dtype=float)
    B = np.asarray(pts_prev, dtype=float)
    if A.size == 0 or B.size == 0:
        return np.zeros_like(A), 0.0, d_bar
    if d_bar is None:
        inner = cKDTree(A).query(A, k=2)[0][:, 1]
        d_bar = float(np.mean(inner)) if inner.size else 0.0
    dist, idx = cKDTree(B).query(A, k=1)
    hit = dist <= max(lam_d * d_bar, 1e-6)
    v = np.zeros_like(A)
    v[hit] = (A[hit] - B[idx[hit]])
    return v, float(hit.mean()), d_bar


def rigid_extrapolate(xyz_t, R, u, frac, pivot):
    """常扭转外推：绕 pivot 旋转 rotvec(R)*frac、再平移 u*frac（frac=0 即恒等）。"""
    from scipy.spatial.transform import Rotation as Rot
    if frac is None or R is None:
        return xyz_t
    xyz = xyz_t.detach().cpu().numpy()
    rf = Rot.from_rotvec(Rot.from_matrix(np.asarray(R, dtype=float)).as_rotvec() * float(frac))
    new = rf.apply(xyz - pivot) + pivot + np.asarray(u, dtype=float) * float(frac)
    return torch.as_tensor(new, dtype=torch.float32, device=xyz_t.device)


# 因果轮 II 臂规格：掩码模式 × 运动模式（prereg_dyn_probe_causal2.md §1）
ARM_SPEC = {
    "P2c": dict(mask="raw", motion="none"),
    "P2cs": dict(mask="cc", motion="none"),
    "P2cm": dict(mask="cc", motion="median"),
    "P2cr": dict(mask="cc", motion="rigid"),
    "P2cv": dict(mask="raw", motion="mean"),
    "P2cu": dict(mask="union", motion="none"),
    "P2cuv": dict(mask="union", motion="pointwise"),
    "C-c": dict(mask="cc", motion="rigid", shift_cam=[0.30, 0.0, 0.0]),
    "C-u": dict(mask="union", motion="pointwise", shift_cam=[0.30, 0.0, 0.0]),
    # P0 在线生命周期臂（prereg_P0_embrace_online.md §3；online=True ⇒ 走逐帧仿真主循环，
    # 不进 KF 因果臂循环）
    "P0o": dict(mask="raw", motion="none", online=True),
    "P0n": dict(mask="raw", motion="none", online=True, no_retire=True),
    "C-o": dict(mask="raw", motion="none", online=True, shift_cam=[0.30, 0.0, 0.0]),
    # E2 对象级瞬态层 + 回填（prereg_E2_object_layer_L1.md §3.1）；E2n = 无回填消融
    "E2o": dict(mask="raw", motion="none", online=True, mode="object"),
    "E2n": dict(mask="raw", motion="none", online=True, mode="object", no_fill=True),
    # DYNp = DynaGSLAM 式忠实移植（prereg §3.2；纯模仿对照，J9）
    "DYNp": dict(mask="raw", motion="none", online=True, mode="dynport"),
    # §9-ter J3 归因批（2026-10-01，判据先锁）：回填质量消融
    #   E2g15 = 占用门收紧 3×（H-A）；E2g00 = 关占用门（H-A 反证）；E2c20 = 回填量上限 20%（H-B）
    "E2g15": dict(mask="raw", motion="none", online=True, mode="object", overrides={"e2_fill_gate_m": 0.15}),
    "E2g00": dict(mask="raw", motion="none", online=True, mode="object", overrides={"e2_fill_gate_m": 0.0}),
    "E2c03": dict(mask="raw", motion="none", online=True, mode="object", overrides={"e2_fill_max_frac": 0.03}),
}


# ────────────────────────── P0 在线生命周期臂（prereg_P0_embrace_online.md §3.1） ──────────────────────────

def _logit(p):
    return float(np.log(p / (1.0 - p)))


def _voxel_keys_np(points, voxel):
    """(N,3) 世界点 → 体素整数坐标（逐帧插入的确定性去重）。"""
    return np.floor(np.asarray(points, dtype=np.float64) / float(voxel)).astype(np.int64)


def voxel_dedup_mask(points, occ, voxel):
    """返回 (keep_mask, keys)：未占据体素的点保留（纯函数，供单测）。"""
    keys = _voxel_keys_np(points, voxel)
    keep = np.array([tuple(k) not in occ for k in keys], dtype=bool)
    return keep, keys


def rolling_window_frame(j, t0, window, steps_pf, s):
    """滚动窗轮转取样（确定性；prereg §3.1 第 3 条）：第 j 帧、第 s 步 → 窗内帧号。"""
    win = list(range(max(t0, j - window + 1), j + 1))
    return win[(j * steps_pf + s) % len(win)] if win else None


def online_step_loss(pkg, gt_image, gt_depth, d, lam_rho=0.01):
    """P0o 单步损失：全帧 RGB L1 + 0.1·全帧深度 L1(m) + λ_ρ·mean σ(ρ)。

    全帧（掩码不限）是"生灭由损失梯度裁定"的实现本体（prereg §3.1 第 3 条）：
    人所在处静态地图解释不了 ⇒ 梯度支持新基元（生）；人离开处动态基元与 GT 冲突
    ⇒ 梯度压其 ρ（灭）；无任何显式删除条件/阈值。
    """
    r = torch.clamp(pkg["render"], 0.0, 1.0)
    m_rgb = gt_image > 0
    loss = torch.abs(r[m_rgb] - gt_image[m_rgb]).mean()
    if gt_depth is not None:
        m_d = torch.isfinite(gt_depth) & (gt_depth > 0)
        loss = loss + 0.1 * torch.abs(pkg["depth"].squeeze()[m_d] - gt_depth[m_d]).mean()
    if isinstance(d.get("rho"), torch.nn.Parameter):
        loss = loss + lam_rho * torch.sigmoid(d["rho"]).mean()
    return loss


class OnlineBuffer:
    """在线生命周期缓冲（探针层仿真；零训练、不动核心代码）。

    机制（prereg §3.1，数值先锁）：逐帧插入（体素 0.02 m 去重）+ 滚动窗连续优化
    （W=4 窗、每走帧 S=10 步、全帧光度+深度损失）+ ρ 梯度退役（零阈值：
    生灭由损失梯度仲裁，稀疏先验 λ_ρ=0.01 只作正则）。60k 硬顶 = 工程护栏
    （预声明非机制；触顶即逐出 σ(ρ) 最低者并计数）。
    实现注记：插入/逐出会重建拼接张量并重建 Adam（动量清零）——判据不依赖动量连续性。
    """

    def __init__(self, run, pc, voxel=0.02, cap=60000, lam_rho=0.01, lr_rho=5.0e-2,
                 rho_init=0.9, no_retire=False):
        self.run = run
        self.pc = pc
        self.voxel = float(voxel)
        self.cap = int(cap)
        self.lam_rho = float(lam_rho)
        self.lr_rho = float(lr_rho)
        self.rho_init = float(rho_init)
        self.no_retire = bool(no_retire)
        self.d = None
        self.occ = set()            # 插入时刻的体素键（加法维护；xyz 漂移后仍保守去重）
        self.inserted_total = 0
        self.evicted_total = 0
        self.cap_hits = 0
        self.opt = None
        self.log = []

    @property
    def n(self):
        return 0 if self.d is None else int(self.d["xyz"].shape[0])

    def _concat(self, newd, n_new):
        if self.d is None:
            self.d = newd
        else:
            merged = {}
            for k in ("xyz", "log_scale", "rot", "opa", "dc"):
                merged[k] = torch.nn.Parameter(
                    torch.cat([self.d[k].detach(), newd[k].detach()], 0))
            merged["rest"] = torch.cat([self.d["rest"], newd["rest"]], 0)
            merged["K"] = self.d["K"]
            merged["rho"] = torch.cat([self.d["rho"], newd["rho"]], 0) \
                if not isinstance(self.d["rho"], torch.nn.Parameter) \
                else torch.nn.Parameter(torch.cat([self.d["rho"].detach(), newd["rho"].detach()], 0))
            self.d = merged
        self.opt = None  # 形状变化 ⇒ 重建优化器（动量清零，见类 docstring）

    def insert_frame(self, j, stride):
        """帧 j 掩码反投影 → 体素去重 → 追加。返回实际插入数。"""
        fd = self.run.frame_data(j)
        if fd is None:
            return 0
        gt_image, gt_depth, w2c = fd
        pts, cols = unproject_mask(self.run, j, gt_image, gt_depth, w2c, stride=stride)
        if pts is None or len(pts) == 0:
            return 0
        keep, keys = voxel_dedup_mask(pts, self.occ, self.voxel)
        if not keep.any():
            return 0
        p, c = np.asarray(pts, dtype=np.float32)[keep], np.asarray(cols, dtype=np.float32)[keep]
        for k in map(tuple, keys[keep]):
            self.occ.add(k)
        newd = make_dynamic(self.run, self.run.gaussians, p, c)
        rho = torch.full((p.shape[0], 1), _logit(self.rho_init),
                         dtype=torch.float32, device=newd["xyz"].device)
        newd["rho"] = rho if self.no_retire else torch.nn.Parameter(rho)
        n_new = int(p.shape[0])
        self._concat(newd, n_new)
        self.inserted_total += n_new
        self._evict_to_cap()
        return n_new

    def _rebuild_opt(self, lrs):
        params = [
            {"params": [self.d["xyz"]], "lr": lrs["xyz"]},
            {"params": [self.d["log_scale"]], "lr": lrs["scale"]},
            {"params": [self.d["rot"]], "lr": lrs["rot"]},
            {"params": [self.d["opa"]], "lr": lrs["opa"]},
            {"params": [self.d["dc"]], "lr": lrs["dc"]},
        ]
        if isinstance(self.d["rho"], torch.nn.Parameter):
            params.append({"params": [self.d["rho"]], "lr": self.lr_rho})
        self.opt = torch.optim.Adam(params)

    def _evict_to_cap(self):
        """工程护栏：超 60k 时逐出 σ(ρ) 最低者（P0n 的 ρ 恒定 ⇒ 按 index 稳定排序）。"""
        if self.n <= self.cap:
            return 0
        n_remove = self.n - self.cap
        with torch.no_grad():
            sig = torch.sigmoid(self.d["rho"] if not isinstance(self.d["rho"], torch.nn.Parameter)
                                else self.d["rho"].detach()).squeeze(1)
            remove = torch.argsort(sig)[:n_remove]
            keep = torch.ones(self.n, dtype=torch.bool, device=sig.device)
            keep[remove] = False
            merged = {}
            for k in ("xyz", "log_scale", "rot", "opa", "dc"):
                t = self.d[k]
                merged[k] = torch.nn.Parameter(t.detach()[keep].clone()) \
                    if isinstance(t, torch.nn.Parameter) else t[keep]
            merged["rest"] = self.d["rest"][keep]
            merged["K"] = self.d["K"]  # 逐出后必须保留（缺 K ⇒ 下次 _concat KeyError，2026-09-25 远程批事故）
            r = self.d["rho"]
            merged["rho"] = (torch.nn.Parameter(r.detach()[keep].clone())
                             if isinstance(r, torch.nn.Parameter) else r[keep])
            self.d = merged
        self.evicted_total += int(n_remove)
        self.cap_hits += 1
        self.opt = None
        return int(n_remove)

    def opt_steps(self, cam, fd, steps, lrs):
        """对缓冲做 steps 步 Adam（损失 = `online_step_loss`，prereg §3.1 第 3 条）。

        返回该次调用的损失证据 dict。
        """
        if self.d is None or steps <= 0:
            return None
        if self.opt is None:
            self._rebuild_opt(lrs)
        gt_image, gt_depth, _w2c = fd
        losses = []
        for _ in range(int(steps)):
            self.pc.set_dynamic(dyn_tensors(self.d))
            pkg = render(cam, self.pc, self.run.pipeline_params, self.run.bg)
            if pkg is None or pkg.get("render") is None:
                return {"failed": "render None"}
            loss = online_step_loss(pkg, gt_image, gt_depth, self.d, self.lam_rho)
            if not torch.isfinite(loss):
                return {"failed": "loss nan"}
            self.opt.zero_grad(set_to_none=True)
            loss.backward()
            self.opt.step()
            losses.append(float(loss.detach()))
        return {"loss_first": round(losses[0], 5), "loss_last": round(losses[-1], 5)}

    def vitality(self):
        """机制生效证据（DISCIPLINE #9 / prereg J8）：ρ 中位数首末 + 插入/逐出计数。"""
        with torch.no_grad():
            if self.d is None:
                rho_med = None
            else:
                r = self.d["rho"]
                r = r.detach() if isinstance(r, torch.nn.Parameter) else r
                rho_med = round(float(torch.sigmoid(r).median()), 5)
        return {"inserted_total": self.inserted_total, "evicted_total": self.evicted_total,
                "cap_hits": self.cap_hits, "buf_final": self.n, "rho_med_final": rho_med}


def run_online_arms(run, pc, tag, cfg, per_arm, p1_depth, advance_union):
    """P0 在线臂主循环：走帧 stride=1（t0..max(eval)−1），评估帧用 <e 的状态（严格因果）。

    C-o = P0o 状态在评估时刻的**平移副本**（比"重放"更严格：逐位配对，拟合后施加、
    无纠正机会——prereg §3 C-o 行）。返回 (vitality, cfg_used) 供 meta 落盘。
    """
    online_arms = [a for a in cfg["arms"] if a in ("P0o", "P0n", "C-o")]
    if not online_arms:
        return {}, {}
    oc = dict(cfg.get("online") or {})
    voxel = float(oc.get("voxel", 0.02))
    cap = int(oc.get("cap", 60000))
    lam_rho = float(oc.get("lam_rho", 0.01))
    lr_rho = float(oc.get("lr_rho", 5.0e-2))
    rho_init = float(oc.get("rho_init", 0.9))
    window = int(oc.get("window", 4))
    steps_pf = int(oc.get("steps_per_frame", 10))
    shift = np.asarray(oc.get("shift_cam_m", cfg.get("control_shift_cam_m", [0.30, 0.0, 0.0])),
                       dtype=np.float64)
    stride = int(cfg.get("unproj_stride", 3))
    lrs = cfg["lrs"]
    t0 = int(cfg["t0_frame"])
    frames = sorted(int(f) for f in cfg["frames"])
    torch.manual_seed(int(oc.get("seed", 0)))

    bufs = {}
    if "P0o" in online_arms:
        bufs["P0o"] = OnlineBuffer(run, pc, voxel, cap, lam_rho, lr_rho, rho_init, no_retire=False)
    if "P0n" in online_arms:
        bufs["P0n"] = OnlineBuffer(run, pc, voxel, cap, lam_rho, lr_rho, rho_init, no_retire=True)

    eval_set = [e for e in frames if e > t0]
    eval_set_set = set(eval_set)
    for e in frames:  # 冷启动帧：不进因果判据（prereg §2），留记录
        if e <= t0:
            for a in online_arms:
                per_arm.setdefault(a, []).append({"frame": int(e), "cold_start": True})
    if not eval_set:
        return ({a: {**b.vitality(), "log": b.log} for a, b in bufs.items()}, oc)

    max_j = max(eval_set) - 1
    fd_cache = {}

    def fd_of(j):
        if j not in fd_cache:
            fd_cache[j] = run.frame_data(j)
            while len(fd_cache) > window + 2:
                fd_cache.pop(min(fd_cache))
        return fd_cache[j]

    for j in range(t0, max_j + 1):
        for name, b in bufs.items():
            n_new = b.insert_frame(j, stride)
            # 滚动窗轮转取样（确定性：全局步计数决定起点）
            for s in range(steps_pf):
                wj = rolling_window_frame(j, t0, window, steps_pf, s)
                if wj is None:
                    break
                fdw = fd_of(wj)
                if fdw is None:
                    continue
                camw = run.camera(wj, fdw[2])
                ev = b.opt_steps(camw, fdw, steps=1, lrs=lrs)
                if ev and ev.get("failed"):
                    print(f"  [{tag}] {name} f{j}: opt {ev['failed']}", flush=True)
                    break
            with torch.no_grad():
                r = b.d["rho"] if b.d is not None else None
                if r is not None:
                    r = r.detach() if isinstance(r, torch.nn.Parameter) else r
                    rho_med = round(float(torch.sigmoid(r).median()), 5) if r.numel() else None
                else:
                    rho_med = None
            b.log.append({"frame": int(j), "inserted": int(n_new), "buf": int(b.n),
                          "evicted_total": int(b.evicted_total), "rho_med": rho_med})
        e = j + 1
        if e not in eval_set_set:
            continue
        pu = advance_union(e)
        fd_e = run.frame_data(e)
        if fd_e is None:
            continue
        gt_e, gd_e, w2c_e = fd_e
        cam_e = run.camera(e, w2c_e)
        dyn_e = run.frame_mask(e)
        dvec = np.linalg.inv(w2c_e)[:3, :3] @ shift  # 相机系 → 世界系（与 C- 同口径）
        variants = []
        if "P0o" in bufs:
            variants.append(("P0o", bufs["P0o"].d))
            if "C-o" in online_arms:
                variants.append(("C-o", translate(bufs["P0o"].d, dvec)))
        if "P0n" in bufs:
            variants.append(("P0n", bufs["P0n"].d))
        for name, dvar in variants:
            pc.set_dynamic(dyn_tensors(dvar))
            pkg = render_once(run, cam_e, pc)
            if pkg is None:
                continue
            rec = frame_metrics(run, e, pkg, gt_e, gd_e, dyn_e,
                                bad_mask=bad_mask_of(p1_depth.get(e), gd_e, dyn_e))
            rec.update(ghost_metrics(run, e, pkg, gt_e, gd_e, dyn_e, pu))
            rec["n_dyn"] = int(dvar["xyz"].shape[0])
            rec["shift_cam_m"] = (list(map(float, shift)) if name == "C-o" else None)
            per_arm.setdefault(name, []).append(rec)
            print(f"  [{tag}] {name} f{e}: bad={rec.get('dyn_bad_psnr')} dB "
                  f"dl1={rec.get('dyn_bad_dl1_cm')} static={rec.get('static_psnr')} "
                  f"n_dyn={rec.get('n_dyn')}", flush=True)
    return ({a: {**b.vitality(), "log": b.log} for a, b in bufs.items()}, oc)


# ────────────────────────── E2 对象级瞬态层 + 占用证据回填（prereg_E2_object_layer_L1.md §3.1） ──────────────────────────

def _project_points(run, pts_world, w2c):
    """世界点 → 源帧像素 (u,v) 与有效掩码（供回填找源）。返回 (us, vs, valid)。"""
    P = np.asarray(pts_world, dtype=np.float64)
    cam = (np.asarray(w2c, dtype=np.float64)[:3, :3] @ P.T).T + np.asarray(w2c, dtype=np.float64)[:3, 3]
    z = cam[:, 2]
    u = run.dataset.fx * cam[:, 0] / np.maximum(z, 1e-6) + run.dataset.cx
    v = run.dataset.fy * cam[:, 1] / np.maximum(z, 1e-6) + run.dataset.cy
    ui = np.round(u).astype(int)
    vi = np.round(v).astype(int)
    ok = (z > 0) & (ui >= 0) & (ui < run.W) & (vi >= 0) & (vi < run.H)
    return ui, vi, ok


def _voxel_keys(points, voxel):
    return np.floor(np.asarray(points, dtype=np.float64) / float(voxel)).astype(np.int64)


class ObjectBuffer:
    """E2 对象级瞬态层（探针层仿真；prereg §3.1，数值先锁）。

    与 `OnlineBuffer` 的三个结构性差别（对应 P0 的两个 binding 失败）：
      1. **逐帧替换不累积**：每 tracklet 一个簇，逐帧用当前观测重建 ⇒ 成本有界（对 J4）；
      2. **整对象退役**：连续 `n_absent` 帧无掩码命中 ⇒ 整簇移除（时间确认防闪烁）；
      3. **占用证据回填**：对象让出的体素用"对象到来之前"的观测回填 ⇒ 消 census"删=露洞"病理（对 J3）。
    无 ρ 存在量、无稀疏先验（本层不做逐基元梯度生灭）。
    """

    def __init__(self, run, pc, oc, no_fill=False, overrides=None):
        if overrides:
            oc = {**dict(oc), **dict(overrides)}   # 臂级覆盖（§9-ter J3 归因批）
        self.run, self.pc = run, pc
        self.voxel = float(oc.get("e2_voxel", 0.02))
        self.stride = int(oc.get("e2_stride", 3))
        self.topk = int(oc.get("e2_topk", 3))
        self.min_area = int(oc.get("e2_min_area", 200))
        self.n_absent = int(oc.get("e2_n_absent", 3))
        self.cap = int(oc.get("e2_cap", 20000))
        self.gate_m = float(oc.get("e2_gate_m", 0.5))
        self.steps = int(oc.get("steps_per_frame", 10))
        self.fit_tol = float(oc.get("e2_fit_tol", 0.0))   # 0 = 关闭早停（R2 修正用 1e-3）
        self.fit_used = None
        self.no_fill = bool(no_fill)
        self.tracks = []          # [{id, pts, cols, centroid, last_seen, birth, covered(set)}]
        self.fill_pts = None
        self.fill_cols = None
        self.filled_keys = set()
        self.d = None
        self.log = []
        self.evicted_total = 0
        self.retired_total = 0
        self.fill_total = 0
        self.inserted_points_total = 0   # 累计写入对象层的点数（含逐帧替换；≠ 末尾簇规模）
        # 回填占用门（L2 失败模式诊断 → 第二改进点）：只填冻结静态图**无支撑**的体素
        self.fill_gate_m = float(oc.get("e2_fill_gate_m", 0.05))
        # §9-ter H-B：回填总量上限（占静态图基元比例；0 = 不限）
        self.fill_max_frac = float(oc.get("e2_fill_max_frac", 0.0))
        self.n_static_ref = int(getattr(run.gaussians, "get_xyz").shape[0]) if hasattr(run.gaussians, "get_xyz") else 0
        self._static_tree = None
        self.cap_hits = 0
        self._next_id = 0
        self._last_disp = 0.0

    @property
    def n(self):
        return 0 if self.d is None else int(self.d["xyz"].shape[0])

    @property
    def n_track(self):
        """对象层（track）基元数——**J4 成本口径**（prereg §3.1-6：回填单独计数）。"""
        return int(sum(t["pts"].shape[0] for t in self.tracks))

    @property
    def n_fill(self):
        """永久回填基元数（单独计数，不计入动态层成本）。"""
        return 0 if self.fill_pts is None else int(self.fill_pts.shape[0])

    # ── 对象提取 ──
    def _components(self, j):
        fd = self.run.frame_data(j)
        if fd is None:
            return []
        gt_image, gt_depth, w2c = fd
        mask = self.run.frame_mask(j)
        if mask is None:
            return []
        from scipy import ndimage
        m = np.asarray(mask, dtype=bool)
        if not m.any():
            return []
        lab, n = ndimage.label(m, structure=np.ones((3, 3), dtype=int))
        if n == 0:
            return []
        sizes = ndimage.sum(m, lab, index=np.arange(1, n + 1))
        thr = max(float(self.min_area), 0.05 * float(sizes.max()))
        order = [i + 1 for i in np.argsort(sizes)[::-1] if sizes[i] >= thr][:self.topk]
        out = []
        for l in order:
            pts, cols = unproject_mask(self.run, j, gt_image, gt_depth, w2c,
                                       stride=self.stride, mask_override=(lab == l))
            if pts is not None and len(pts):
                out.append((pts, cols))
        return out

    # ── 关联 / 退役 / 回填 ──
    def _associate(self, j, comps):
        for pts, cols in comps:
            c = np.median(np.asarray(pts, dtype=float), axis=0)
            best, bd = None, None
            for t in self.tracks:
                dd = float(np.linalg.norm(c - t["centroid"]))
                if bd is None or dd < bd:
                    best, bd = t, dd
            gate = max(self.gate_m, 2.0 * self._last_disp)
            if best is not None and bd is not None and bd <= gate:
                self._last_disp = bd if self._last_disp == 0.0 else 0.5 * (self._last_disp + bd)
                self.inserted_points_total += int(np.asarray(pts).shape[0])
                best["pts"], best["cols"] = pts, cols
                best["centroid"], best["last_seen"] = c, j
                self._cover(best, pts, j)
            else:
                self.inserted_points_total += int(np.asarray(pts).shape[0])
                t = {"id": self._next_id, "pts": pts, "cols": cols, "centroid": c,
                     "last_seen": j, "birth": j, "covered": set()}
                self._next_id += 1
                self._cover(t, pts, j)
                self.tracks.append(t)

    def _cover(self, t, pts, j):
        """记录簇当前体素；把**新让出**的体素交给回填（源帧 = 该 tracklet 到来之前）。"""
        keys = set(map(tuple, _voxel_keys(pts, self.voxel)))
        newly_vacated = t["covered"] - keys
        t["covered"] |= keys
        if newly_vacated and not self.no_fill:
            self._fill(newly_vacated, before=t["birth"])

    def _fill(self, voxel_keys, before):
        """对让出的体素，用该 tracklet **到来之前最近 ≤3 帧**的观测回填（占用证据）。

        源帧必须早于对象出现（此时该处未被遮挡）；用源帧深度重建像素的世界点，
        颜色取源帧 RGB——写入永久回填集合（不计入动态层成本，prereg §3.1-6）。
        """
        todo = [k for k in voxel_keys if k not in self.filled_keys]
        if not todo:
            return
        centers = (np.asarray(todo, dtype=np.float64) + 0.5) * self.voxel
        # 占用门（e2_fill_gate_m>0 时启用）：静态图已有支撑的体素**不填**（只补真正的洞）。
        # 依据：L2 诊断——无条件回填使 fill/n_static 达 1.2–2.3 时静态区被错误背景覆盖（J3 破）。
        if self.fill_gate_m > 0:
            if self._static_tree is None:
                from scipy.spatial import cKDTree
                xyz = getattr(self.run.gaussians, "get_xyz", None)
                if xyz is not None:
                    self._static_tree = cKDTree(xyz.detach().cpu().numpy())
            if self._static_tree is not None:
                dmin, _idx = self._static_tree.query(centers, k=1)
                keep = dmin > self.fill_gate_m
                if not keep.any():
                    return
                todo = [todo[i] for i in np.nonzero(keep)[0]]
                centers = centers[keep]
        added_p, added_c = [], []
        srcs = [s for s in sorted(self.run.pose_by_id) if s < before][-3:]
        for s in srcs:
            fd = self.run.frame_data(s)
            if fd is None:
                continue
            gt_i, gt_d, w2c = fd
            mk = self.run.frame_mask(s)
            mk = np.zeros((self.run.H, self.run.W), dtype=bool) if mk is None else np.asarray(mk, dtype=bool)
            ui, vi, ok = _project_points(self.run, centers, w2c)
            gd = np.asarray(gt_d.cpu())
            gi = gt_i.permute(1, 2, 0).detach().cpu().numpy()
            for i in range(len(centers)):
                k = tuple(todo[i])
                if k in self.filled_keys or not ok[i]:
                    continue
                uu, vv = int(ui[i]), int(vi[i])
                if mk[vv, uu]:
                    continue
                d = float(gd[vv, uu])
                if not np.isfinite(d) or d <= 0.2 or d >= 8.0:
                    continue
                # 用源帧深度重建该像素的世界点（占用证据：该处曾见到背景）
                x = (uu - self.run.dataset.cx) * d / self.run.dataset.fx
                y = (vv - self.run.dataset.cy) * d / self.run.dataset.fy
                c2w = np.linalg.inv(np.asarray(w2c, dtype=np.float64))
                pw = c2w[:3, :3] @ np.array([x, y, d]) + c2w[:3, 3]
                added_p.append(pw.astype(np.float32))
                added_c.append(gi[vv, uu].astype(np.float32))
                self.filled_keys.add(k)
        if added_p:
            if self.fill_max_frac > 0 and self.n_static_ref > 0:
                cap_n = int(self.fill_max_frac * self.n_static_ref)
                have = 0 if self.fill_pts is None else int(self.fill_pts.shape[0])
                room = max(0, cap_n - have)
                if room <= 0:
                    self.fill_capped = getattr(self, "fill_capped", 0) + 1
                    return
                if len(added_p) > room:
                    sel = np.linspace(0, len(added_p) - 1, room).astype(int)
                    added_p = [added_p[i] for i in sel]
                    added_c = [added_c[i] for i in sel]
                    self.fill_capped = getattr(self, "fill_capped", 0) + 1
            self.fill_pts = np.asarray(added_p, dtype=np.float32) if self.fill_pts is None else \
                np.concatenate([self.fill_pts, np.asarray(added_p, dtype=np.float32)], 0)
            self.fill_cols = np.asarray(added_c, dtype=np.float32) if self.fill_cols is None else \
                np.concatenate([self.fill_cols, np.asarray(added_c, dtype=np.float32)], 0)
            self.fill_total += len(added_p)

    def _retire(self, j):
        gone = [t for t in self.tracks if j - t["last_seen"] >= self.n_absent]
        for t in gone:
            self.tracks.remove(t)
            self.retired_total += 1
            if not self.no_fill:
                self._fill(t["covered"], before=t["birth"])

    # ── 组装 / 拟合 ──
    def _rebuild(self):
        pts, cols = [], []
        for t in self.tracks:
            pts.append(t["pts"]); cols.append(t["cols"])
        if not self.no_fill and self.fill_pts is not None:
            pts.append(self.fill_pts); cols.append(self.fill_cols)
        if not pts:
            self.d = None
            return
        P = np.concatenate(pts, 0)
        C = np.concatenate(cols, 0)
        self.d = make_dynamic(self.run, self.run.gaussians, P, C)

    def _local_fit(self, j):
        if self.steps <= 0:
            return
        fd = self.run.frame_data(j)
        if fd is None or self.d is None:
            return
        gt_i, gt_d, w2c = fd
        cam = self.run.camera(j, w2c)
        mk = self.run.frame_mask(j)
        mk = np.zeros((self.run.H, self.run.W), dtype=bool) if mk is None else np.asarray(mk, dtype=bool)
        m_rgb = torch.from_numpy(mk).to(gt_i.device) & (gt_i > 0)
        m_d = torch.from_numpy(mk).to(gt_d.device) & torch.isfinite(gt_d) & (gt_d > 0) if gt_d is not None else None
        lrs = self.lrs
        params = [self.d["xyz"], self.d["log_scale"], self.d["rot"], self.d["opa"], self.d["dc"]]
        opt = torch.optim.Adam([
            {"params": [self.d["xyz"]], "lr": lrs["xyz"]},
            {"params": [self.d["log_scale"]], "lr": lrs["scale"]},
            {"params": [self.d["rot"]], "lr": lrs["rot"]},
            {"params": [self.d["opa"]], "lr": lrs["opa"]},
            {"params": [self.d["dc"]], "lr": lrs["dc"]},
        ])
        prev, plateau = None, 0
        for it in range(self.steps):
            self.pc.set_dynamic(dyn_tensors(self.d))
            pkg = render(cam, self.pc, self.run.pipeline_params, self.run.bg)
            if pkg is None or pkg.get("render") is None:
                break
            r = torch.clamp(pkg["render"], 0.0, 1.0)
            if bool(m_rgb.any()):
                loss = torch.abs(r[m_rgb] - gt_i[m_rgb]).mean()
            else:
                loss = torch.abs(r - gt_i).mean() * 0.0
            if m_d is not None and bool(m_d.any()):
                loss = loss + 0.1 * torch.abs(pkg["depth"].squeeze()[m_d] - gt_d[m_d]).mean()
            if not torch.isfinite(loss):
                break
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            cur = float(loss.detach())
            self.fit_used = it + 1
            if self.fit_tol > 0.0 and prev is not None and prev > 0.0:
                if (prev - cur) / prev < self.fit_tol:
                    plateau += 1
                    if plateau >= 5:      # 连续 5 步相对降幅 < tol ⇒ 视为收敛（R2 早停）
                        break
                else:
                    plateau = 0
            prev = cur

    def _evict_to_cap(self):
        """护栏：**只对对象层（track）计数**（prereg §3.1-6：回填单独计数、不计入动态层成本，
        故禁止逐出回填）。超顶 ⇒ 退役**最旧 tracklet**（整簇）并计数——与"时间确认退役"
        （`retired_total`）**分开统计**，防 J8 机制生效判据被护栏动作冒充。
        """
        while self.tracks and self.n_track > self.cap:
            t = self.tracks.pop(0)
            self.evicted_total += int(t["pts"].shape[0])
            self.cap_hits += 1
        return 0

    def step(self, j, lrs):
        self.lrs = lrs
        comps = self._components(j)
        self._associate(j, comps)
        self._retire(j)
        self._rebuild()
        if self.d is not None:
            self._local_fit(j)
            self._evict_to_cap()
        self.log.append({"frame": int(j), "fit_steps_used": self.fit_used,
                         "n_tracklets": len(self.tracks),
                         "cluster_size": self.n_track, "fill_size": self.n_fill,
                         "retired": self.retired_total,
                         "fill_inserted": self.fill_total, "covered": len(self.filled_keys)})

    def vitality(self):
        return {"inserted_total": self.inserted_points_total,   # 累计写入点数（非末尾簇规模，G4b 条件①）
                "n_track_final": self.n_track,
                "evicted_total": self.evicted_total, "cap_hits": self.cap_hits,
                "buf_final": self.n, "n_track": self.n_track, "n_fill": self.n_fill,
                "n_tracklets": len(self.tracks),
                "retired_total": self.retired_total, "fill_total": self.fill_total,
                "filled_voxels": len(self.filled_keys)}


class DynPortBuffer:
    """DYNp = DynaGSLAM 式忠实移植（prereg §3.2）：复用优先插入（Case1/2）+ Cond1/2 删除。

    纯模仿对照臂：无 ρ 存在量、无稀疏先验、无回填——用于回答"纯模仿够不够到天花板"（J9）。
    """

    def __init__(self, run, pc, oc):
        self.run, self.pc = run, pc
        self.voxel = float(oc.get("dynp_voxel", 0.02))
        self.stride = int(oc.get("dynp_stride", 3))
        self.lam_d = float(oc.get("dynp_lam_d", 0.05))
        self.lmax = int(oc.get("dynp_lmax", 45))
        self.cap = int(oc.get("dynp_cap", 60000))
        self.steps = int(oc.get("steps_per_frame", 10))
        self.d = None
        self.first_seen = None      # (N,) 每基元的加入帧
        self.log = []
        self.case1_hits = 0
        self.case2_new = 0
        self.cond1_deleted = 0
        self.cond2_deleted = 0
        self.evicted_total = 0
        self.cap_hits = 0

    @property
    def n(self):
        return 0 if self.d is None else int(self.d["xyz"].shape[0])

    def _dbar(self, gt_depth, mask):
        gd = np.asarray(gt_depth.cpu())
        m = np.asarray(mask, dtype=bool) & np.isfinite(gd) & (gd > 0)
        return float(np.mean(gd[m])) if m.any() else None

    def step(self, j, lrs):
        self.lrs = lrs
        fd = self.run.frame_data(j)
        if fd is None:
            return
        gt_i, gt_d, w2c = fd
        mask = self.run.frame_mask(j)
        pts, cols = unproject_mask(self.run, j, gt_i, gt_d, w2c, stride=self.stride)
        if pts is None or len(pts) == 0:
            self.log.append({"frame": int(j), "inserted": 0, "case1_hits": self.case1_hits,
                             "buf": self.n, "cond1_deleted": self.cond1_deleted,
                             "cond2_deleted": self.cond2_deleted})
            return
        from scipy.spatial import cKDTree
        dbar = self._dbar(gt_d, mask)
        thr = max(self.lam_d * (dbar or 0.0), 1e-3)
        n_new = 0
        if self.d is not None and self.n > 0:
            buf_xyz = self.d["xyz"].detach().cpu().numpy()
            dist, idx = cKDTree(buf_xyz).query(np.asarray(pts, dtype=float), k=1)
            hit = dist <= thr
            if hit.any():
                with torch.no_grad():
                    new_xyz = np.asarray(pts, dtype=np.float32)[hit]
                    self.d["xyz"][torch.as_tensor(idx[hit], dtype=torch.long,
                                                  device=self.d["xyz"].device)] = \
                        torch.as_tensor(new_xyz, dtype=torch.float32, device=self.d["xyz"].device)
                self.case1_hits += int(hit.sum())
                newd = make_dynamic(self.run, self.run.gaussians,
                                    np.asarray(pts, dtype=np.float32)[~hit],
                                    np.asarray(cols, dtype=np.float32)[~hit]) if (~hit).any() else None
                if newd is not None:
                    n_new = int((~hit).sum())
                    self._append(newd, j)
            else:
                newd = make_dynamic(self.run, self.run.gaussians, pts, cols)
                n_new = len(pts); self._append(newd, j)
        else:
            newd = make_dynamic(self.run, self.run.gaussians, pts, cols)
            n_new = len(pts); self._append(newd, j)
        self.case2_new += int(n_new)
        # Cond1 可观测性删除：当前观测点云中无近邻者删
        if self.d is not None and self.n > 0:
            buf_xyz = self.d["xyz"].detach().cpu().numpy()
            dd, _ii = cKDTree(np.asarray(pts, dtype=float)).query(buf_xyz, k=1)
            obs = dd <= thr
            self._delete_mask(~obs, "cond1")
        # Cond2 寿命删除
        if self.first_seen is not None and self.d is not None:
            old = (j - self.first_seen) > self.lmax
            if old.any():
                self._delete_mask(old, "cond2")
        self._evict_to_cap()
        if self.d is not None:
            self._local_fit(j)
        self.log.append({"frame": int(j), "inserted": int(n_new), "case1_hits": self.case1_hits,
                         "buf": self.n, "cond1_deleted": self.cond1_deleted,
                         "cond2_deleted": self.cond2_deleted})

    def _append(self, newd, j):
        import torch.nn as nn
        n = int(newd["xyz"].shape[0])
        if self.d is None:
            self.d = newd
            self.first_seen = np.full(n, int(j), dtype=np.int64)
        else:
            merged = {}
            for k in ("xyz", "log_scale", "rot", "opa", "dc"):
                merged[k] = nn.Parameter(torch.cat([self.d[k].detach(), newd[k].detach()], 0))
            merged["rest"] = torch.cat([self.d["rest"], newd["rest"]], 0)
            merged["K"] = self.d["K"]
            self.d = merged
            self.first_seen = np.concatenate([self.first_seen, np.full(n, int(j), dtype=np.int64)])

    def _delete_mask(self, mask, which):
        import torch.nn as nn
        keep = ~np.asarray(mask, dtype=bool)
        n_removed = int((~keep).sum())
        if n_removed == 0 or self.d is None:
            return
        if not keep.any():
            self.d = None
            self.first_seen = None
        else:
            with torch.no_grad():
                kt = torch.as_tensor(keep, device=self.d["xyz"].device)
                merged = {}
                for k in ("xyz", "log_scale", "rot", "opa", "dc"):
                    merged[k] = nn.Parameter(self.d[k].detach()[kt].clone())
                merged["rest"] = self.d["rest"][kt]
                merged["K"] = self.d["K"]
                self.d = merged
            self.first_seen = self.first_seen[keep]
        if which == "cond1":
            self.cond1_deleted += n_removed
        elif which == "cond2":
            self.cond2_deleted += n_removed
        else:
            self.evicted_total += n_removed

    def _evict_to_cap(self):
        if self.n <= self.cap:
            return 0
        n_remove = self.n - self.cap
        keep = np.ones(self.n, dtype=bool); keep[:n_remove] = False
        self._delete_mask(~keep, "cap")
        self.evicted_total += int(n_remove)
        self.cap_hits += 1
        return int(n_remove)

    def _local_fit(self, j):
        if self.steps <= 0:
            return
        fd = self.run.frame_data(j)
        if fd is None or self.d is None:
            return
        gt_i, gt_d, w2c = fd
        cam = self.run.camera(j, w2c)
        mk = self.run.frame_mask(j)
        mk = np.zeros((self.run.H, self.run.W), dtype=bool) if mk is None else np.asarray(mk, dtype=bool)
        m_rgb = torch.from_numpy(mk).to(gt_i.device) & (gt_i > 0)
        m_d = torch.from_numpy(mk).to(gt_d.device) & torch.isfinite(gt_d) & (gt_d > 0) if gt_d is not None else None
        lrs = self.lrs
        opt = torch.optim.Adam([
            {"params": [self.d["xyz"]], "lr": lrs["xyz"]},
            {"params": [self.d["log_scale"]], "lr": lrs["scale"]},
            {"params": [self.d["rot"]], "lr": lrs["rot"]},
            {"params": [self.d["opa"]], "lr": lrs["opa"]},
            {"params": [self.d["dc"]], "lr": lrs["dc"]},
        ])
        for _ in range(self.steps):
            self.pc.set_dynamic(dyn_tensors(self.d))
            pkg = render(cam, self.pc, self.run.pipeline_params, self.run.bg)
            if pkg is None or pkg.get("render") is None:
                break
            r = torch.clamp(pkg["render"], 0.0, 1.0)
            loss = torch.abs(r[m_rgb] - gt_i[m_rgb]).mean() if bool(m_rgb.any()) else r.sum() * 0.0
            if m_d is not None and bool(m_d.any()):
                loss = loss + 0.1 * torch.abs(pkg["depth"].squeeze()[m_d] - gt_d[m_d]).mean()
            if not torch.isfinite(loss):
                break
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()

    def vitality(self):
        return {"inserted_total": int(self.case1_hits + self.case2_new),
                "evicted_total": int(self.cond1_deleted + self.cond2_deleted + self.evicted_total),
                "cap_hits": self.cap_hits, "buf_final": self.n,
                "case1_hits": self.case1_hits, "case2_new": self.case2_new,
                "cond1_deleted": self.cond1_deleted, "cond2_deleted": self.cond2_deleted}


def run_e2_arms(run, pc, tag, cfg, per_arm, p1_depth, advance_union):
    """E2 臂主循环（prereg_E2_object_layer_L1.md §3.1/§3.2）。

    骨架与 `run_online_arms` 同：走帧 stride=1（t0..max(eval)−1），评估帧用 <e 的状态
    （严格因果）；臂类由 `ARM_SPEC[name]["mode"]` 选择。阴性对照（C-o）**不在此产生**
    ——按 prereg §3 复用 P0 批的 C-o 读数。返回 vitality dict。
    """
    names = [a for a in cfg["arms"]
             if ARM_SPEC.get(a, {}).get("mode") in ("object", "dynport")]
    if not names:
        return {}
    oc = dict(cfg.get("online") or {})
    t0 = int(cfg["t0_frame"])
    frames = sorted(int(f) for f in cfg["frames"])
    lrs = cfg["lrs"]
    torch.manual_seed(int(oc.get("seed", 0)))
    bufs = {}
    for name in names:
        spec = ARM_SPEC[name]
        bufs[name] = (ObjectBuffer(run, pc, oc, no_fill=bool(spec.get("no_fill")),
                                   overrides=spec.get("overrides"))
                      if spec["mode"] == "object" else DynPortBuffer(run, pc, oc))
    eval_set = [e for e in frames if e > t0]
    for e in frames:
        if e <= t0:
            for a in names:
                per_arm.setdefault(a, []).append({"frame": int(e), "cold_start": True})
    if not eval_set:
        return {a: {**b.vitality(), "log": b.log} for a, b in bufs.items()}
    eval_set_set = set(eval_set)
    max_j = max(eval_set) - 1
    for j in range(t0, max_j + 1):
        for name, b in bufs.items():
            b.step(j, lrs)
        e = j + 1
        if e not in eval_set_set:
            continue
        fd_e = run.frame_data(e)
        if fd_e is None:
            continue
        gt_e, gd_e, w2c_e = fd_e
        cam_e = run.camera(e, w2c_e)
        dyn_e = run.frame_mask(e)
        pu = advance_union(e)
        for name, b in bufs.items():
            if b.d is None:
                per_arm.setdefault(name, []).append({"frame": int(e), "empty": True, "n_dyn": 0})
                continue
            pc.set_dynamic(dyn_tensors(b.d))
            pkg = render_once(run, cam_e, pc)
            if pkg is None:
                continue
            rec = frame_metrics(run, e, pkg, gt_e, gd_e, dyn_e,
                                bad_mask=bad_mask_of(p1_depth.get(e), gd_e, dyn_e))
            rec.update(ghost_metrics(run, e, pkg, gt_e, gd_e, dyn_e, pu))
            # J4 口径：`n_dyn` = **对象层（track）**基元数；回填单独计数（prereg §3.1-6）
            rec["n_dyn"] = int(getattr(b, "n_track", b.n))
            rec["n_fill"] = int(getattr(b, "n_fill", 0))
            rec["n_layer"] = int(b.n)
            per_arm.setdefault(name, []).append(rec)
            print(f"  [{tag}] {name} f{e}: bad={rec.get('dyn_bad_psnr')} dB "
                  f"dl1={rec.get('dyn_bad_dl1_cm')} static={rec.get('static_psnr')} "
                  f"n_dyn={rec.get('n_dyn')} n_fill={rec.get('n_fill')}", flush=True)
    return {a: {**b.vitality(), "log": b.log} for a, b in bufs.items()}


# ────────────────────────── 渲染与指标 ──────────────────────────

def render_once(run, cam, pc):
    with torch.no_grad():
        pkg = render(cam, pc, run.pipeline_params, run.bg)
    return pkg


def bad_mask_of(p1_depth, gt_depth, dyn_mask, tol_m=0.10):
    """真损坏子集 M_bad（预注册补遗 `prereg_dyn_probe_badsubset_addendum.md`）。

    `mask ∧ 有效GT深度 ∧ (P1 渲染深度无效 或 |P1−GT| > tol)`。**所有臂共用同一 P1 深度** ⇒ 配对；
    它衡量"反动态范式实际弄坏的像素"，从而把"复制已经正确的背景"这一虚假增益排除在外。
    """
    if p1_depth is None or gt_depth is None or dyn_mask is None:
        return None
    dev = gt_depth.device
    m = (torch.isfinite(gt_depth) & (gt_depth > 0)) & \
        torch.from_numpy(np.asarray(dyn_mask, dtype=bool)).to(dev)
    p1 = p1_depth.to(dev)
    bad = (~torch.isfinite(p1)) | (p1 <= 0) | (torch.abs(p1 - gt_depth) > tol_m)
    return m & bad


def frame_metrics(run, idx, pkg, gt_image, gt_depth, dyn_mask, bad_mask=None):
    """逐帧指标（同口径、可复现）。dyn_mask 为 (H,W) bool numpy 或 None。

    `bad_mask`（可选）= 真损坏子集（见 `bad_mask_of`）⇒ 额外产出 dyn_bad_* 三列。
    """
    rendering = torch.clamp(pkg["render"], 0.0, 1.0)
    depth_r = pkg["depth"]
    # 全图 PSNR：与 render_compare.py:316-317 **逐行同口径**（用 (3,H,W) 掩码 + image_utils.psnr），
    # 以便 P1 臂与该脚本既有结果做阳性对照
    f3 = gt_image > 0
    out = {
        "frame": int(idx),
        "full_psnr": _f(psnr(rendering[f3].unsqueeze(0), gt_image[f3].unsqueeze(0)).item()),
    }
    if gt_depth is not None and dyn_mask is not None:
        dyn_t = torch.from_numpy(np.asarray(dyn_mask, dtype=bool)).to(gt_depth.device)
        m_dyn = (torch.isfinite(gt_depth) & (gt_depth > 0)) & dyn_t
        out.update({
            "dyn_px": int(m_dyn.sum()),
            "dyn_psnr": _f(masked_psnr(rendering, gt_image, m_dyn)),
            "dyn_dl1_cm": _f(penalized_depth_l1_cm(depth_r.squeeze(), gt_depth, m_dyn, 50.0)),
            "dyn_cov": _f(static_coverage(depth_r.squeeze(), m_dyn, render_opacity=pkg.get("opacity"), a_eval=0.5)),
        })
        sm = static_background_metrics(
            rendering, gt_image, depth_r.squeeze(), gt_depth, dynamic_mask=dyn_t,
            render_opacity=pkg.get("opacity"), d_max_cm=50.0, a_eval=0.5, lpips_fn=None,
        )
        out["static_psnr"] = _f(sm["static_psnr"])
    if bad_mask is not None and gt_depth is not None:
        m_bad = bad_mask & torch.isfinite(gt_depth) & (gt_depth > 0)
        out.update({
            "dyn_bad_px": int(m_bad.sum()),
            "dyn_bad_psnr": _f(masked_psnr(rendering, gt_image, m_bad)),
            "dyn_bad_dl1_cm": _f(penalized_depth_l1_cm(depth_r.squeeze(), gt_depth, m_bad, 50.0)),
        })
        # M_good = 掩码 ∧ 有效GT ∧ ¬bad（补遗要求：把"复制已正确背景"那一部分单独量化）
        if dyn_mask is not None:
            m_dyn_all = (torch.isfinite(gt_depth) & (gt_depth > 0)) & \
                torch.from_numpy(np.asarray(dyn_mask, dtype=bool)).to(gt_depth.device)
            m_good = m_dyn_all & (~bad_mask)
            out.update({
                "dyn_good_px": int(m_good.sum()),
                "dyn_good_psnr": _f(masked_psnr(rendering, gt_image, m_good)),
                "dyn_good_dl1_cm": _f(penalized_depth_l1_cm(depth_r.squeeze(), gt_depth, m_good, 50.0)),
            })
    return out


def _f(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)


def ghost_metrics(run, idx, pkg, gt_image, gt_depth, dyn_mask, past_union):
    """残影对比（vacated_contrast_metrics，与运行期 P-A 同函数）。"""
    if gt_depth is None or dyn_mask is None or past_union is None:
        return {}
    dyn_t = torch.from_numpy(np.asarray(dyn_mask, dtype=bool)).to(gt_image.device)
    vm = vacated_contrast_metrics(torch.clamp(pkg["render"], 0.0, 1.0), gt_image,
                                  pkg["depth"].squeeze(), gt_depth, dyn_t, past_union, d_max_cm=50.0)
    return {"ghost_excess_cm": _f(vm.get("ghost_excess_depth_l1_cm")),
            "vacated_px": int(vm.get("vacated_support_px", 0))}


def fit_dynamic(run, cam, pc, d, gt_image, gt_depth, dyn_mask, iters, lrs, seed=0):
    """局部拟合（所有臂同一预算/超参）：只优化动态基元的 5 组参数。

    损失 = 掩码内 RGB L1 + 0.1 × 掩码内深度 L1(m)。返回 (raw 参数字典, 证据 dict)。
    说明：本拟合是"插入后即用"的最小形式（DynaGSLAM/Flow4DGS 的在线优化在此退化为
    单帧局部拟合），对 P2（逐帧插入）与 P4（t0 插入）给**同一预算**以保证可比。
    """
    if iters <= 0:
        return d, {"iters": 0}
    torch.manual_seed(seed)
    params = [d["xyz"], d["log_scale"], d["rot"], d["opa"], d["dc"]]
    opt = torch.optim.Adam([
        {"params": [d["xyz"]], "lr": lrs["xyz"]},
        {"params": [d["log_scale"]], "lr": lrs["scale"]},
        {"params": [d["rot"]], "lr": lrs["rot"]},
        {"params": [d["opa"]], "lr": lrs["opa"]},
        {"params": [d["dc"]], "lr": lrs["dc"]},
    ])
    gt = gt_image
    m_rgb = gt_image > 0                     # (3,H,W)，与全图 PSNR 同口径
    if dyn_mask is not None:
        m_rgb = m_rgb & torch.from_numpy(np.asarray(dyn_mask, dtype=bool)).to(gt.device)
    m_d = None
    if gt_depth is not None and dyn_mask is not None:
        m_d = (torch.isfinite(gt_depth) & (gt_depth > 0)) & torch.from_numpy(np.asarray(dyn_mask, dtype=bool)).to(gt_depth.device)
    opa0 = float(torch.sigmoid(d["opa"]).mean())
    p0 = None
    losses = []
    for it in range(iters):
        pc.set_dynamic(dyn_tensors(d))
        pkg = render(cam, pc, run.pipeline_params, run.bg)
        if pkg is None or pkg.get("render") is None:
            return d, {"iters": it, "failed": "render None"}
        r = torch.clamp(pkg["render"], 0.0, 1.0)
        loss = torch.abs(r[m_rgb] - gt[m_rgb]).mean()
        if m_d is not None:
            dcur = pkg["depth"].squeeze()
            dd = torch.abs(dcur[m_d] - gt_depth[m_d]).mean()
            loss = loss + 0.1 * dd
        if not torch.isfinite(loss):
            return d, {"iters": it, "failed": "loss nan"}
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        losses.append(float(loss.detach()))
        if it == 0:
            p0 = losses[0]
    pc.set_dynamic(dyn_tensors(d))
    return d, {"iters": iters, "loss_first": round(losses[0], 5), "loss_last": round(losses[-1], 5),
               "opa_mean_before": round(opa0, 4),
               "opa_mean_after": round(float(torch.sigmoid(d["opa"]).mean()), 4)}


# ────────────────────────── 子命令：materials ──────────────────────────

def keyframes_of(log_path):
    """从 run 的 consolelog 解析插入关键帧（`Candidate insert KF <n>: inserted ...`）。

    PLY 不落盘 KF 字段（`construct_list_of_attributes` 只存 opacity/static_prob/
    static_obs_count/unmapped_score）⇒ consolelog 是唯一来源，**已在预注册中声明**。
    """
    import re as _re
    txt = Path(log_path).read_text(errors="ignore")
    kfs = sorted({int(m) for m in _re.findall(r"Candidate insert KF (\d+):", txt)})
    assert kfs, f"consolelog 中未找到插入关键帧: {log_path}"
    return kfs


def cmd_coverage(args):
    """逐帧动态掩码覆盖率 + 预注册选帧规则的可复算落地（内容判据，非结果指标）。"""
    from utils.gtmc_mask import frozen_mask_index, load_frozen_mask
    ds = args.dataset
    idx = frozen_mask_index(os.path.join(ds, args.mask_subdir))
    assert idx, f"无掩码索引: {ds}/{args.mask_subdir}"
    rgb = [l.split()[1] for l in open(os.path.join(ds, "rgb.txt")) if l.strip() and not l.startswith("#")]
    dep = [l.split()[1] for l in open(os.path.join(ds, "depth.txt")) if l.strip() and not l.startswith("#")]
    keys = sorted((float(k), v) for k, v in idx.items())
    kts = [t for t, _ in keys]

    def _near(ts, tol=0.05):
        i = bisect.bisect_left(kts, ts)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(kts):
                dd = abs(kts[j] - ts)
                if best is None or dd < best[0]:
                    best = (dd, keys[j][1])
        return best[1] if best is not None and best[0] <= tol else None

    cov, src = [], {"depth_stem": 0, "rgb_stem": 0, "nearest_ts": 0, "miss": 0}
    for cp, dp in zip(rgb, dep):
        stem = os.path.splitext(os.path.basename(dp))[0]
        p = idx.get(stem)
        if p is not None:
            src["depth_stem"] += 1
        else:
            p = idx.get(os.path.splitext(os.path.basename(cp))[0])
            if p is not None:
                src["rgb_stem"] += 1
            elif _is_ts(stem):
                p = _near(float(stem))
                src["nearest_ts" if p is not None else "miss"] += 1
            else:
                src["miss"] += 1
        cov.append(0.0 if p is None else float(np.asarray(load_frozen_mask(p)).mean()))
    cov = np.asarray(cov)
    nz = cov[cov > 0]
    thr = float(np.median(nz))
    cand = np.nonzero(cov >= thr)[0]
    n_sel = int(args.n_frames)
    sel = sorted(set(int(x) for x in cand[np.round(np.linspace(0, len(cand) - 1, n_sel)).astype(int)]))
    t0 = int(sel[int(np.argmax([cov[i] for i in sel]))])
    out = {"dataset": ds, "mask_subdir": args.mask_subdir, "n_frames_rgb": len(rgb),
           "n_frames_depth": len(dep), "n_coverage_entries": int(cov.shape[0]),
           "pairing_note": "coverage 逐项 = zip(rgb.txt, depth.txt) 的配对帧（Bonn 两清单长度可不同）",
           "mask_match_sources": src,
           "selection_rule": "coverage >= median(coverage>0) then evenly spaced in time (np.linspace, round)",
           "median_nonzero_coverage": round(thr, 6), "n_candidates": int(len(cand)),
           "selected_frames": sel, "selected_coverage": [round(float(cov[i]), 6) for i in sel],
           "t0_frame": t0, "t0_coverage": round(float(cov[t0]), 6),
           "coverage_per_frame": [round(float(c), 6) for c in cov]}
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"[coverage] written {args.out}: median_nonzero={thr:.4f} cand={len(cand)} "
          f"selected={sel} t0={t0} (cov={cov[t0]:.3f})")
    return 0


def cmd_materials(args):
    out = {"protocol": "content-only (no rendering metrics); used to select sequence and lock frames",
           "seqs": {}, "ghost_inventory": {}}
    # ① 7 序列掩码面积表（只需掩码文件，无需 PLY）
    for seq in BONN_SEQS:
        ds = f"datasets/bonn/rgbd_bonn_{seq}"
        rec = {}
        for sub in ("dynamic_mask_gtmc", "seg_mask"):
            d = os.path.join(ds, sub)
            if not os.path.isdir(d):
                continue
            from utils.gtmc_mask import frozen_mask_index
            idx = frozen_mask_index(d)
            if not idx:
                continue
            from PIL import Image
            fr = []
            keys = sorted(idx)
            for k in keys[:: max(1, len(keys) // 40)]:
                a = np.asarray(Image.open(idx[k]).convert("L"))
                v = (a == args.mask_class) if sub == "seg_mask" else (a > 0)
                fr.append(float(v.mean()))
            fr = np.asarray(fr)
            rec[sub] = {"n_masks": len(idx), "cov_mean": round(float(fr.mean()), 4),
                        "cov_med": round(float(np.median(fr)), 4), "cov_max": round(float(fr.max()), 4),
                        "frac_frames_nz": round(float((fr > 0.005).mean()), 3)}
        out["seqs"][seq] = rec

    # ② 冻结地图残影盘点（投影高斯进掩码）
    inv = {}
    for tag, rd in args.map_dirs.items():
        run = Run(rd, ply=args.ply, device=args.device, mask_subdir=args.mask_subdir,
                  mask_class=args.mask_class)
        xyz = run.gaussians.get_xyz.detach().cpu().numpy()
        opa = run.gaussians.get_opacity.detach().cpu().numpy().ravel()
        recs = []
        for idx in range(0, run.N, args.stride):
            fd = run.frame_data(idx)
            if fd is None:
                continue
            gt_image, gt_depth, w2c = fd
            dyn = run.frame_mask(idx)
            if dyn is None or gt_depth is None:
                continue
            p = xyz @ w2c[:3, :3].T + w2c[:3, 3]          # world → cam
            z = p[:, 2]
            u = run.dataset.fx * p[:, 0] / np.maximum(z, 1e-6) + run.dataset.cx
            v = run.dataset.fy * p[:, 1] / np.maximum(z, 1e-6) + run.dataset.cy
            ui = np.round(u).astype(np.int64)
            vi = np.round(v).astype(np.int64)
            ok = (z > 0.05) & (ui >= 0) & (ui < run.W) & (vi >= 0) & (vi < run.H)
            gd = np.asarray(gt_depth.cpu())
            inm = np.zeros_like(ok)
            inm[ok] = dyn[vi[ok], ui[ok]] & (gd[vi[ok], ui[ok]] > 0)
            if inm.sum() == 0:
                recs.append({"frame": int(idx), "n_proj": int(ok.sum()), "n_in_mask": 0})
                continue
            gd_at = gd[vi[inm], ui[inm]]
            pz = z[inm]
            front = pz < (gd_at - 0.10)                     # 挡在 GT 表面之前的 = 残影/鬼影
            recs.append({
                "frame": int(idx), "n_proj": int(ok.sum()), "n_in_mask": int(inm.sum()),
                "share_in_mask": round(float(inm.sum()) / max(int(ok.sum()), 1), 4),
                "n_in_mask_front": int(front.sum()),
                "n_in_mask_front_opaque": int((front & (opa[inm] > 0.3)).sum()),
                "mean_opa_in_mask": round(float(opa[inm].mean()), 4),
                "med_z_in_mask": round(float(np.median(pz)), 3),
                "med_gt_depth_in_mask": round(float(np.median(gd_at)), 3),
            })
        inv[tag] = {"run_dir": rd, "ply": run.ply_path, "n_gauss": int(xyz.shape[0]),
                    "mask_source": run.mask_source, "frames": recs}
    out["ghost_inventory"] = inv

    out_p = Path(args.out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(out_p, "w"), indent=1)
    print(f"[materials] written {out_p}")
    for seq, rec in out["seqs"].items():
        for sub, s in rec.items():
            print(f"  {seq:18s} {sub:18s} n={s['n_masks']:4d} cov_med={s['cov_med']:.3f} "
                  f"cov_mean={s['cov_mean']:.3f} frac_nz={s['frac_frames_nz']:.2f}")
    for tag, rec in inv.items():
        fr = [r for r in rec["frames"] if r.get("n_in_mask")]
        if not fr:
            print(f"  [{tag}] n_gauss={rec['n_gauss']} 无掩码命中帧")
            continue
        sh = np.mean([r["share_in_mask"] for r in fr])
        nf = np.mean([r["n_in_mask"] for r in fr])
        print(f"  [{tag}] n_gauss={rec['n_gauss']} mask={rec['mask_source']} "
              f"帧数={len(rec['frames'])} 掩码命中帧={len(fr)} 平均命中点={nf:.0f} "
              f"占比={sh:.4f} 挡在GT前者均值={np.mean([r['n_in_mask_front'] for r in fr]):.0f}")
    return 0


# ────────────────────────── 子命令：render（四臂阶梯） ──────────────────────────

def cmd_render(args):
    cfg = yaml.safe_load(open(args.config))
    device = cfg.get("device", "cuda:0")
    print(f"[dyn_probe] config={args.config} arms={cfg['arms']} frames={cfg['frames']}", flush=True)
    results = {"config": args.config, "prereg": cfg.get("prereg"), "arms": {}, "meta": {},
               # 可追溯（DISCIPLINE #12③）：把锁定的关键参数一并落盘
               "t0_frame": int(cfg["t0_frame"]), "frames": list(cfg["frames"]),
               "fit_iters": int(cfg["fit_iters"]), "lrs": cfg["lrs"],
               "unproj_stride": int(cfg.get("unproj_stride", 3)),
               "control_shift_cam_m": cfg.get("control_shift_cam_m")}
    t0 = int(cfg["t0_frame"])

    for map_seed in cfg["maps"]:
        tag = map_seed["tag"]
        run = Run(map_seed["run_dir"], ply=cfg.get("ply", "final_after_opt"), device=device,
                  mask_subdir=cfg.get("mask_subdir", "auto"), mask_class=int(cfg.get("mask_class", 15)))
        pc = PackedPC(run.gaussians)
        results["meta"][tag] = {"run_dir": map_seed["run_dir"], "ply": run.ply_path,
                                "n_static": pc.n_static, "mask_source": run.mask_source,
                                "W": run.W, "H": run.H, "n_frames": run.N}
        print(f"[dyn_probe] {tag}: n_static={pc.n_static} mask={run.mask_source}", flush=True)

        # past_union（严格早于 idx 的所有掩码并集）——残影指标用；
        # 每臂独立重置，保证各臂口径一致（DISCIPLINE #12）
        all_ids = sorted(run.pose_by_id)
        state = {"ptr": 0, "union": None}
        per_arm = {a: [] for a in cfg["arms"]}

        def reset_union():
            state["ptr"], state["union"] = 0, None

        def advance_union(idx):
            while state["ptr"] < len(all_ids) and all_ids[state["ptr"]] < idx:
                j = all_ids[state["ptr"]]
                state["ptr"] += 1
                jm = run.frame_mask(j)
                if jm is not None:
                    jt = torch.from_numpy(np.asarray(jm, dtype=bool))
                    state["union"] = jt if state["union"] is None else (state["union"] | jt)
            return state["union"]

        # ── P1 erase：冻结地图原样（同时落 P1 渲染深度，供 M_bad 子集用）──
        p1_depth = {}
        if "P1" in cfg["arms"]:
            reset_union()
            for idx in cfg["frames"]:
                fd = run.frame_data(idx)
                if fd is None:
                    continue
                gt_image, gt_depth, w2c = fd
                cam = run.camera(idx, w2c)
                pkg = render_once(run, cam, pc)
                if pkg is None:
                    continue
                dyn = run.frame_mask(idx)
                pu = advance_union(idx)
                p1_depth[idx] = pkg["depth"].squeeze().detach().clone()
                rec = frame_metrics(run, idx, pkg, gt_image, gt_depth, dyn,
                                    bad_mask=bad_mask_of(p1_depth[idx], gt_depth, dyn))
                rec.update(ghost_metrics(run, idx, pkg, gt_image, gt_depth, dyn, pu))
                rec["n_dyn"] = 0
                per_arm["P1"].append(rec)
                print(f"  [{tag}] P1 f{idx}: {rec.get('dyn_psnr')} dB dl1={rec.get('dyn_dl1_cm')}", flush=True)

        # ── P4 bake：t0 插入 + 拟合一次，之后冻结 ──
        if "P4" in cfg["arms"]:
            reset_union()
            fd0 = run.frame_data(t0)
            gt_i0, gt_d0, w2c0 = fd0
            dyn0 = run.frame_mask(t0)
            pts, cols = unproject_mask(run, t0, gt_i0, gt_d0, w2c0, stride=int(cfg.get("unproj_stride", 2)))
            if pts is not None:
                d4 = make_dynamic(run, run.gaussians, pts, cols)
                cam0 = run.camera(t0, w2c0)
                d4, fit_ev = fit_dynamic(run, cam0, pc, d4, gt_i0, gt_d0, dyn0,
                                         int(cfg["fit_iters"]), cfg["lrs"])
                print(f"  [{tag}] P4 fit@{t0}: {fit_ev}", flush=True)
                for idx in cfg["frames"]:
                    fd = run.frame_data(idx)
                    if fd is None:
                        continue
                    gt_image, gt_depth, w2c = fd
                    cam = run.camera(idx, w2c)
                    pc.set_dynamic(dyn_tensors(d4))
                    pkg = render_once(run, cam, pc)
                    if pkg is None:
                        continue
                    dyn = run.frame_mask(idx)
                    pu = advance_union(idx)
                    rec = frame_metrics(run, idx, pkg, gt_image, gt_depth, dyn,
                                        bad_mask=bad_mask_of(p1_depth.get(idx), gt_depth, dyn))
                    rec.update(ghost_metrics(run, idx, pkg, gt_image, gt_depth, dyn, pu))
                    rec["n_dyn"] = pc.n_dyn
                    per_arm["P4"].append(rec)
                    print(f"  [{tag}] P4 f{idx}: {rec.get('dyn_psnr')} dB dl1={rec.get('dyn_dl1_cm')}", flush=True)
                results["meta"][tag]["P4_fit"] = fit_ev
                results["meta"][tag]["P4_n_dyn"] = pc.n_dyn

        # ── P2 逐帧瞬态插入（天花板）+ C- 错位对照 ──
        if "P2" in cfg["arms"]:
            reset_union()
            for idx in cfg["frames"]:
                fd = run.frame_data(idx)
                if fd is None:
                    continue
                gt_image, gt_depth, w2c = fd
                dyn = run.frame_mask(idx)
                pts, cols = unproject_mask(run, idx, gt_image, gt_depth, w2c, stride=int(cfg.get("unproj_stride", 3)))
                cam = run.camera(idx, w2c)
                pu = advance_union(idx)
                if pts is None:
                    rec = {"frame": int(idx), "empty": True, "n_dyn": 0}
                    per_arm["P2"].append(rec)
                    continue
                d2 = make_dynamic(run, run.gaussians, pts, cols)
                d2, fit_ev = fit_dynamic(run, cam, pc, d2, gt_image, gt_depth, dyn,
                                         int(cfg["fit_iters"]), cfg["lrs"])
                pc.set_dynamic(dyn_tensors(d2))
                pkg = render_once(run, cam, pc)
                rec = frame_metrics(run, idx, pkg, gt_image, gt_depth, dyn,
                                    bad_mask=bad_mask_of(p1_depth.get(idx), gt_depth, dyn))
                rec.update(ghost_metrics(run, idx, pkg, gt_image, gt_depth, dyn, pu))
                rec["n_dyn"] = pc.n_dyn
                rec["fit"] = fit_ev
                per_arm["P2"].append(rec)
                print(f"  [{tag}] P2 f{idx}: {rec.get('dyn_psnr')} dB dl1={rec.get('dyn_dl1_cm')} "
                      f"(fit {fit_ev.get('loss_first')}->{fit_ev.get('loss_last')})", flush=True)
                if "C-" in cfg["arms"]:
                    # 错位对照：沿**相机系**横轴平移，在拟合之后施加（拟合不得有机会纠正）
                    dc = np.asarray(cfg.get("control_shift_cam_m", [0.3, 0.0, 0.0]), dtype=np.float64)
                    delta_world = np.linalg.inv(w2c)[:3, :3] @ dc
                    dshift = translate(d2, delta_world)
                    pc.set_dynamic(dyn_tensors(dshift))
                    pkg2 = render_once(run, cam, pc)
                    rec2 = frame_metrics(run, idx, pkg2, gt_image, gt_depth, dyn,
                                         bad_mask=bad_mask_of(p1_depth.get(idx), gt_depth, dyn))
                    rec2.update(ghost_metrics(run, idx, pkg2, gt_image, gt_depth, dyn, pu))
                    rec2["n_dyn"] = pc.n_dyn
                    rec2["shift_cam_m"] = cfg.get("control_shift_cam_m")
                    per_arm.setdefault("C-", []).append(rec2)
                    print(f"  [{tag}] C- f{idx}: {rec2.get('dyn_psnr')} dB dl1={rec2.get('dyn_dl1_cm')}", flush=True)

        # ── 因果臂（预注册 prereg_dyn_probe_causal.md / _causal2.md）：只用帧号 ≤ t 的数据 ──
        causal_arms = [a for a in ARM_SPEC if a in cfg["arms"] and not ARM_SPEC[a].get("online")]
        if causal_arms:
            kf_log = map_seed.get("kf_log")
            assert kf_log, f"{tag}: 因果臂需要 map 级 kf_log（consolelog 路径）"
            kfs = keyframes_of(kf_log)
            kf_pos = {k: i for i, k in enumerate(kfs)}
            results["meta"][tag].update({"kf_source": kf_log, "n_kf": len(kfs),
                                         "kf_gap_med": int(np.median(np.diff(kfs))) if len(kfs) > 1 else None,
                                         "arm_spec": {a: ARM_SPEC[a] for a in causal_arms}})
            print(f"  [{tag}] 因果臂 {causal_arms}：KF 数={len(kfs)} 首={kfs[0]} 末={kfs[-1]}", flush=True)
            reset_union()
            for idx in cfg["frames"]:
                pu = advance_union(idx)
                past = [k for k in kfs if k <= idx]
                if not past:
                    for a in causal_arms:
                        per_arm.setdefault(a, []).append({"frame": int(idx), "cold_start": True})
                    print(f"  [{tag}] causal f{idx}: 冷启动（无前置 KF）⇒ 不计入因果判据", flush=True)
                    continue
                k = past[-1]
                kp = kfs[kf_pos[k] - 1] if kf_pos.get(k, 0) > 0 else None
                gt_k, gd_k, w2c_k = run.frame_data(k)
                raw_mask_k = run.frame_mask(k)
                cc_mask_k = largest_cc(raw_mask_k) if raw_mask_k is not None else None
                # 每个掩码模式各插入 + 拟合一次（同帧同掩码 ⇒ 共用，避免重复拟合）
                base, fit_ev, pts_cache, union_pts_holder = {}, {}, {}, {}
                w_win = int(cfg.get("union_window", 4))
                union_pts = union_cols = None
                for mode in sorted({ARM_SPEC[a]["mask"] for a in causal_arms}):
                    if mode == "union":
                        # 因果多帧并集：帧 [k-w, k] 的掩码点云拼接（全部 ≤ k）
                        if union_pts is None:
                            ps, cs = [], []
                            for j in range(max(0, k - w_win), k + 1):
                                fdj = run.frame_data(j)
                                if fdj is None:
                                    continue
                                pj, cj = unproject_mask(run, j, fdj[0], fdj[1], fdj[2],
                                                        stride=int(cfg.get("unproj_stride", 3)),
                                                        mask_override=run.frame_mask(j))
                                if pj is not None:
                                    ps.append(pj)
                                    cs.append(cj)
                            union_pts = np.concatenate(ps) if ps else None
                            union_cols = np.concatenate(cs) if cs else None
                            if union_pts is not None:
                                union_pts_holder["union"] = union_pts
                        pts, cols = union_pts, union_cols
                        mk = raw_mask_k
                    else:
                        mk = raw_mask_k if mode == "raw" else cc_mask_k
                        pts, cols = unproject_mask(run, k, gt_k, gd_k, w2c_k,
                                                   stride=int(cfg.get("unproj_stride", 3)), mask_override=mk)
                    if pts is None:
                        continue
                    cam_k = run.camera(k, w2c_k)
                    d_k = make_dynamic(run, run.gaussians, pts, cols)
                    d_k, fe = fit_dynamic(run, cam_k, pc, d_k, gt_k, gd_k, mk,
                                          int(cfg["fit_iters"]), cfg["lrs"])
                    base[mode], fit_ev[mode], pts_cache[mode] = d_k, fe, pts
                if not base:
                    for a in causal_arms:
                        per_arm.setdefault(a, []).append({"frame": int(idx), "kf": k, "empty": True})
                    continue
                # 逐点速度（懒计算一次，供 pointwise 臂共用）：KF 云 vs 上一帧云
                if any(ARM_SPEC[a]["motion"] == "pointwise" for a in causal_arms):
                    fd_prev = run.frame_data(k - 1) if k >= 1 else None
                    if fd_prev is not None:
                        pk, ck = unproject_mask(run, k, gt_k, gd_k, w2c_k,
                                                stride=int(cfg.get("unproj_stride", 3)), mask_override=raw_mask_k)
                        pp, cp = unproject_mask(run, k - 1, fd_prev[0], fd_prev[1], fd_prev[2],
                                                stride=int(cfg.get("unproj_stride", 3)),
                                                mask_override=run.frame_mask(k - 1))
                        if pk is not None and pp is not None and "union" in union_pts_holder:
                            # d̄ = 掩码内平均 GT 深度（相机系距离量纲）
                            gd_np = np.asarray(gd_k.cpu())
                            mk_np = np.asarray(raw_mask_k, dtype=bool) & np.isfinite(gd_np) & (gd_np > 0)
                            d_bar_m = float(np.mean(gd_np[mk_np])) if mk_np.any() else None
                            v_full, mfrac, dbar = pointwise_velocity(
                                pk, pp, float(cfg.get("lam_d", 0.05)), d_bar=d_bar_m)
                            uxy = np.asarray(union_pts_holder["union"], dtype=float)
                            from scipy.spatial import cKDTree
                            nn = cKDTree(pk).query(uxy, k=1)[1]
                            pts_cache["pointwise_vel"] = v_full[nn]
                            pts_cache["pointwise_stats"] = {"matched_frac": round(mfrac, 4),
                                                            "d_bar_m": (None if dbar is None else round(dbar, 5)),
                                                            "v_med_m_per_frame": round(float(np.median(
                                                                np.linalg.norm(v_full, axis=1))), 5)}
                # 运动估计（只用观测）：raw 均值（legacy P2cv）、CC 中位、CC 刚性
                vel_mean = vel_med = None
                R_rel = u_rel = icp_rmse = pivot = None
                if kp is not None:
                    fd_p = run.frame_data(kp)
                    if fd_p is not None:
                        gap = float(k - kp)
                        if "raw" in pts_cache:
                            mkp = run.frame_mask(kp)
                            pr, _ = unproject_mask(run, kp, fd_p[0], fd_p[1], fd_p[2],
                                                   stride=int(cfg.get("unproj_stride", 3)), mask_override=mkp)
                            if pr is not None:
                                vel_mean = (np.asarray(pts_cache["raw"]).mean(0) - np.asarray(pr).mean(0)) / gap
                        if "cc" in pts_cache:
                            mkp = run.frame_mask(kp)
                            ccp = largest_cc(mkp) if mkp is not None else None
                            pc_prev, _ = unproject_mask(run, kp, fd_p[0], fd_p[1], fd_p[2],
                                                        stride=int(cfg.get("unproj_stride", 3)), mask_override=ccp)
                            if pc_prev is not None:
                                vel_med = median_velocity(pts_cache["cc"], pc_prev, gap)
                                try:
                                    R_rel, u_rel, icp_rmse = rigid_between(pc_prev, pts_cache["cc"])
                                    pivot = np.median(np.asarray(pts_cache["cc"], dtype=float), axis=0)
                                except Exception as e:  # noqa: BLE001
                                    print(f"  [{tag}] f{idx}: rigid 估计失败 {type(e).__name__}: {e}", flush=True)
                gt_t, gd_t, w2c_t = run.frame_data(idx)
                cam_t = run.camera(idx, w2c_t)
                dyn_t = run.frame_mask(idx)
                cc_frac = (None if raw_mask_k is None or cc_mask_k is None else
                           round(float(np.asarray(cc_mask_k).sum()) / max(float(np.asarray(raw_mask_k).sum()), 1), 4))
                frac = ((idx - k) / float(k - kp)) if (kp is not None and k > kp) else None
                for a in causal_arms:
                    spec = ARM_SPEC[a]
                    mode = spec["mask"]
                    if mode not in base:
                        per_arm.setdefault(a, []).append({"frame": int(idx), "kf": k, "empty": True})
                        continue
                    d_obj = base[mode]
                    vnorm = None
                    if spec["motion"] == "mean":
                        if vel_mean is None:
                            per_arm.setdefault(a, []).append({"frame": int(idx), "kf": k, "no_velocity": True})
                            continue
                        moved = translate(d_obj, vel_mean * (idx - k))
                        vnorm = float(np.linalg.norm(vel_mean))
                    elif spec["motion"] == "median":
                        if vel_med is None:
                            per_arm.setdefault(a, []).append({"frame": int(idx), "kf": k, "no_velocity": True})
                            continue
                        moved = translate(d_obj, vel_med * (idx - k))
                        vnorm = float(np.linalg.norm(vel_med))
                    elif spec["motion"] == "pointwise":
                        pv = pts_cache.get("pointwise_vel")
                        if pv is None:
                            per_arm.setdefault(a, []).append({"frame": int(idx), "kf": k, "no_velocity": True})
                            continue
                        moved = with_xyz(d_obj, d_obj["xyz"] + torch.as_tensor(
                            pv * float(idx - k), dtype=torch.float32, device=d_obj["xyz"].device))
                    elif spec["motion"] == "rigid":
                        if R_rel is None or frac is None:
                            per_arm.setdefault(a, []).append({"frame": int(idx), "kf": k, "no_velocity": True})
                            continue
                        moved = with_xyz(d_obj, rigid_extrapolate(d_obj["xyz"], R_rel, u_rel, frac, pivot))
                    else:
                        moved = d_obj
                    if spec.get("shift_cam"):
                        dc = np.asarray(spec["shift_cam"], dtype=np.float64)
                        dvec = np.linalg.inv(w2c_t)[:3, :3] @ dc
                        moved = with_xyz(moved, moved["xyz"] + torch.as_tensor(
                            dvec, dtype=torch.float32, device=moved["xyz"].device))
                    pc.set_dynamic(dyn_tensors(moved))
                    pkg = render_once(run, cam_t, pc)
                    if pkg is None:
                        continue
                    rec = frame_metrics(run, idx, pkg, gt_t, gd_t, dyn_t,
                                        bad_mask=bad_mask_of(p1_depth.get(idx), gd_t, dyn_t))
                    rec.update(ghost_metrics(run, idx, pkg, gt_t, gd_t, dyn_t, pu))
                    rec.update({"n_dyn": pc.n_dyn, "kf": int(k), "dt_eval": float(idx - k),
                                "dt_kf": (float(k - kp) if kp is not None else None),
                                "mask_mode": mode, "motion": spec["motion"], "mask_cc_frac": cc_frac,
                                "frac": (None if frac is None else round(float(frac), 4)),
                                "icp_rmse_m": (None if icp_rmse is None else round(float(icp_rmse), 6)),
                                "union_window": (int(cfg.get("union_window", 4)) if mode == "union" else None),
                                "pointwise_stats": (pts_cache.get("pointwise_stats") if spec["motion"] == "pointwise" else None),
                                "v_norm": (None if vnorm is None else round(vnorm, 6))})
                    if a in ("P2c", "P2cs", "P2cr"):
                        rec["fit"] = fit_ev.get(mode)
                    per_arm.setdefault(a, []).append(rec)
                    print(f"  [{tag}] {a} f{idx} (KF {k}, dt={idx-k}, mask={mode}, motion={spec['motion']}): "
                          f"{rec.get('dyn_psnr')} dB bad={rec.get('dyn_bad_psnr')} dl1={rec.get('dyn_dl1_cm')} "
                          f"n_dyn={rec.get('n_dyn')}", flush=True)

        # ── P0 在线生命周期臂（prereg_P0_embrace_online.md）：逐帧插入+滚动优化+ρ 退役 ──
        if any(a in ("P0o", "P0n", "C-o") for a in cfg["arms"]):
            reset_union()
            vit, oc_used = run_online_arms(run, pc, tag, cfg, per_arm, p1_depth, advance_union)
            results["meta"][tag]["online_vitality"] = vit
            results["meta"][tag]["online_cfg_used"] = oc_used

        # ── E2 对象级瞬态层 / DYNp 忠实移植（prereg_E2_object_layer_L1.md §3.1/§3.2）──
        if any(ARM_SPEC.get(a, {}).get("mode") in ("object", "dynport") for a in cfg["arms"]):
            reset_union()
            results["meta"][tag]["e2_vitality"] = run_e2_arms(
                run, pc, tag, cfg, per_arm, p1_depth, advance_union)

        results["arms"][tag] = per_arm

    # 聚合
    agg = {}
    for tag, per_arm in results["arms"].items():
        agg[tag] = {}
        for arm, recs in per_arm.items():
            good = [r for r in recs if r.get("dyn_psnr") is not None]
            if not good:
                continue
            keys = ("dyn_psnr", "dyn_dl1_cm", "dyn_bad_psnr", "dyn_bad_dl1_cm", "dyn_bad_px",
                    "dyn_good_psnr", "dyn_good_dl1_cm", "dyn_good_px",
                    "dyn_cov", "full_psnr", "static_psnr", "ghost_excess_cm", "n_dyn")
            agg[tag][arm] = {"n": len(good),
                             **{f"mean_{k}": round(float(np.mean([r[k] for r in good if r.get(k) is not None])), 4)
                                for k in keys if any(r.get(k) is not None for r in good)}}
    results["aggregate"] = agg
    out_p = Path(cfg["out"])
    out_p.parent.mkdir(parents=True, exist_ok=True)
    json.dump(results, open(out_p, "w"), indent=1)
    print(f"[dyn_probe] written {out_p}")
    for tag, arms in agg.items():
        print(f"── {tag} ──")
        for arm, s in arms.items():
            print(f"  {arm:3s} n={s['n']:3d} dyn_psnr={s.get('mean_dyn_psnr')} dB "
                  f"dyn_dl1={s.get('mean_dyn_dl1_cm')} cm cov={s.get('mean_dyn_cov')} "
                  f"static={s.get('mean_static_psnr')} n_dyn={s.get('mean_n_dyn')}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("materials", help="内容判据：掩码面积表 + 冻结地图残影盘点")
    m.add_argument("--map-dirs", nargs="*", default=[],
                   help="tag=run_dir 形式，可多个（如 gate=results/.../2026-09-16-14-47-45）")
    m.add_argument("--ply", default="final_after_opt")
    m.add_argument("--mask-subdir", default="auto")
    m.add_argument("--mask-class", type=int, default=15)
    m.add_argument("--stride", type=int, default=25, help="残影盘点的帧步长")
    m.add_argument("--device", default="cuda:0")
    m.add_argument("--out", default="results/embrace_dyn/evidence/materials_dyn_probe.json")
    m.set_defaults(func=cmd_materials)

    c = sub.add_parser("coverage", help="逐帧掩码覆盖率 + 选帧规则落地（内容判据）")
    c.add_argument("--dataset", default="datasets/bonn/rgbd_bonn_person_tracking2")
    c.add_argument("--mask-subdir", default="dynamic_mask_gtmc")
    c.add_argument("--n-frames", type=int, default=16)
    c.add_argument("--out", default="results/embrace_dyn/evidence/frame_coverage_pt2.json")
    c.set_defaults(func=cmd_coverage)

    r = sub.add_parser("render", help="四臂阶梯 P1/P2/C-/P4")
    r.add_argument("--config", required=True)
    r.set_defaults(func=cmd_render)

    args = ap.parse_args()
    if args.cmd == "materials":
        args.map_dirs = dict(x.split("=", 1) for x in args.map_dirs)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
