#!/usr/bin/env python3
"""ghost_population_census.py — 残影总体普查（离线，零训练；D2-009 Phase 0 分支器）。

背景（L1e 遗留 + 关卡① 两次怀疑）
----------------------------------
五批实验的每个 α 阈值（0.20/0.25/0.35）都对着 a_min 或"钉死值"传闻校准，
**从未直接测过残影基元本身的 α 分布**。渲染物理暗示有效不透明度 ≈0.5
（pt freshvac 超额 ≈3.5cm ÷ 深度差 5-10cm）——若属实，则全部阈值瞄错人群。

三个互斥物理假设（修法完全不同）
--------------------------------
* H-A 漏入的人内容：掩码 0.5% 漏检 × 数百帧把人物像素插进地图
      → 签名：基元颜色 ≈ 人物颜色，且 ≠ 该像素当前观测（背景）颜色
* H-B 被拉伸的背景膜：遮挡期无数据，优化器用相邻背景基元桥接空洞
      → 签名：基元颜色 ≈ 背景颜色（与当前观测一致），但深度差 5-10cm
* H-C 陈旧背景：旧深度基元未被重拟合
      → 签名：颜色 ≈ 背景，深度差符号/量级随相机运动漂移（非稳定前偏）

测量（与机制同透镜）
--------------------
复用 render_compare 的装载与 alpha_lifecycle 的
project_gaussians_to_view + sample_map_at_gaussians（与 carve/reset 同代码路径）。
对每个评估帧：
  1. vacated = ∪(严格早于 f 的掩码) ∧ ¬(当前掩码) ∧ GT 深度有效
  2. 投影全体基元；取 proj∈vacated 的集合 P_v
  3. 对 P_v 记 Δz = z − obs_at（GT 深度采样）、α（sigmoid 激活）
  4. **颜色归属**：d_obs = |c_prim − c_obs(pixel)|（对背景）、
     d_person = |c_prim − c_person_ref(f)|（当前帧掩码内 GT 颜色均值）
  5. **归因渲染**：把缝隙带∩vacated 基元 α 置 −20 重渲一次，比较
     "含幽灵"与"无幽灵"在 vacated 像素上的深度 L1 —— 差值 = 幽灵贡献；
     无幽灵残差 ≈ 背景重建误差（判"背后是否已补背景"，决定要不要重播种）

输出 JSON（聚合 + per-frame），供 D2-009 一页纸定向。

用法（远程 REPO 下，含 PLY 的 run 目录）:
    python scripts/02_analysis/ghost_population_census.py \
      --run-dir <rundir> --frames <f1,f2,...> --out <out.json> [--device cuda:0]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import collections
import numpy as np
import cv2
import torch
import yaml
from munch import munchify

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gaussian_splatting.gaussian_renderer import render  # noqa: E402
from gaussian_splatting.scene.gaussian_model import GaussianModel  # noqa: E402
from gaussian_splatting.utils.graphics_utils import getProjectionMatrix2  # noqa: E402
from gaussian_splatting.utils.sh_utils import C0  # noqa: E402
from utils import alpha_lifecycle  # noqa: E402
from utils.camera_utils import Camera  # noqa: E402
from utils.dataset import load_dataset  # noqa: E402
from utils.eval_utils import _undistort_depth_like  # noqa: E402
from render_compare import sh_degree_from_ply  # noqa: E402  （render_compare 的同一实现）
from utils.gtmc_mask import frozen_mask_index, load_frozen_mask  # noqa: E402
from utils.dynamic_mask_spec import resolve_eval_mask_dir  # noqa: E402
import bisect as _bisect  # noqa: E402

SEAM_LO, SEAM_HI = 0.05, 0.10   # 缝隙带（与 L1e 同定义）


def find_in_run(run_dir, *alts):
    for a in alts:
        p = os.path.join(run_dir, a)
        if os.path.exists(p):
            return p
    return None


def _is_ts(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def _hist(x, lo=0.0, hi=1.0, step=0.05):
    if x is None or x.numel() == 0:
        return {"n": 0}
    x = x.float()
    out = {"n": int(x.numel()), "mean": round(float(x.mean()), 4)}
    for q in (0.05, 0.25, 0.5, 0.75, 0.95):
        out[f"p{int(q*100)}"] = round(float(torch.quantile(x, q)), 4)
    bins = {}
    edges = np.arange(lo, hi + 1e-9, step)
    for i in range(len(edges) - 1):
        k = f"{edges[i]:.2f}-{edges[i+1]:.2f}"
        bins[k] = int(((x >= edges[i]) & (x < edges[i + 1])).sum())
    out["hist"] = bins
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--ply", default="final_after_opt")
    args = ap.parse_args()

    run_dir = str(Path(args.run_dir).resolve())
    config = yaml.safe_load(open(os.path.join(run_dir, "config.yml")))
    ply_path = find_in_run(run_dir, f"point_cloud/{args.ply}/point_cloud.ply",
                           "point_cloud/final/point_cloud.ply")
    trj_path = find_in_run(run_dir, "plot/trj_full_final.json")
    assert ply_path and trj_path, "no PLY/trj"

    device = torch.device(args.device)
    if str(device) != f"cuda:{torch.cuda.current_device()}":
        torch.cuda.set_device(device)

    model_params = munchify(config["model_params"])
    pipeline_params = munchify(config["pipeline_params"])
    dataset = load_dataset(model_params, model_params.source_path, config=config)
    dataset.device = str(device)
    W, H = dataset.width, dataset.height
    proj = getProjectionMatrix2(znear=0.01, zfar=100.0, fx=dataset.fx, fy=dataset.fy,
                                cx=dataset.cx, cy=dataset.cy, W=W, H=H,
                                ).transpose(0, 1).to(device=device)

    sh_deg = sh_degree_from_ply(ply_path)
    gaussians = GaussianModel(sh_deg, config=config)
    gaussians.load_ply(ply_path)
    n_prim = int(gaussians.get_xyz.shape[0])
    alpha_all = gaussians.get_opacity.squeeze(1).detach()
    # DC 颜色 → RGB（与渲染一致：rgb = C0 * features_dc + 0.5）
    rgb_all = torch.clamp(C0 * gaussians.get_features[:, 0, :] + 0.5, 0.0, 1.0).detach()
    print(f"[census] PLY={ply_path} n={n_prim}", flush=True)

    trj = json.load(open(trj_path))
    pose_by_id = dict(zip([int(v) for v in trj["trj_id"]],
                          [np.asarray(v, dtype=np.float64) for v in trj["trj_est"]]))

    ds_path = config["Dataset"].get("dataset_path", "")
    mdir, src, legacy = resolve_eval_mask_dir(ds_path)
    assert mdir, f"no canonical mask dir in {ds_path}"
    mask_index = frozen_mask_index(mdir)
    print(f"[census] mask={src} ({len(mask_index)} stems)", flush=True)
    mask_ts = sorted((float(k), v) for k, v in mask_index.items() if _is_ts(k))
    ts_keys = [t for t, _ in mask_ts]

    depth_paths = getattr(dataset, "depth_paths", None)
    color_paths = getattr(dataset, "color_paths", None)

    def frame_mask(idx):
        if depth_paths is None or idx >= len(depth_paths):
            return None
        stem = os.path.splitext(os.path.basename(depth_paths[idx]))[0]
        mpath = mask_index.get(stem)
        if mpath is None and color_paths is not None and idx < len(color_paths):
            mpath = mask_index.get(os.path.splitext(os.path.basename(color_paths[idx]))[0])
        if mpath is None and _is_ts(stem):
            i = _bisect.bisect_left(ts_keys, float(stem))
            best = None
            for j in (i - 1, i):
                if 0 <= j < len(ts_keys):
                    d = abs(ts_keys[j] - float(stem))
                    if best is None or d < best[0]:
                        best = (d, mask_ts[j][1])
            if best and best[0] <= 0.05:
                mpath = best[1]
        return load_frozen_mask(mpath) if mpath else None

    frame_ids = [int(x) for x in args.frames.split(",")]
    all_ids = sorted(pose_by_id.keys())

    acc = {"dz": [], "seam_alpha": [], "vac_alpha": [], "d_col_obs_seam": [],
           "d_col_person_seam": [], "exc_full": [], "exc_noghost": [], "exc_noghost_deep": [],
           "n_deep": [], "exc_fresh": [], "exc_noghost_fresh": [], "exc_ring": [],
           "n_vac_fresh": [], "exc_nowstat": [], "exc_nowstat_fresh": []}
    recent_masks = collections.deque(maxlen=30)
    per_frame = []
    for idx in frame_ids:
        if idx not in pose_by_id:
            continue
        gt_image, gt_depth, _ = dataset[idx]
        gt_image = torch.as_tensor(gt_image, device=device).float()
        if gt_image.dim() == 3 and gt_image.shape[0] != 3:
            gt_image = gt_image.permute(2, 0, 1)
        if float(gt_image.max()) > 1.5:
            gt_image = gt_image / 255.0
        gt_depth_u = _undistort_depth_like(dataset, gt_depth)
        gt_depth_t = torch.as_tensor(np.asarray(gt_depth_u), device=device,
                                     dtype=torch.float32).squeeze()
        dyn = frame_mask(idx)
        if dyn is None:
            continue
        dyn_t = torch.from_numpy(np.asarray(dyn, dtype=bool))
        past = None
        for j in all_ids:
            if j >= idx:
                break
            jm = frame_mask(j)
            if jm is not None:
                jm_t = torch.from_numpy(np.asarray(jm, dtype=bool))
                past = jm_t if past is None else (past | jm_t)
                recent_masks.append(jm_t.clone())
        if past is None:
            continue
        valid_gt = torch.isfinite(gt_depth_t) & (gt_depth_t > 0.01)
        # fresh-window（最近 30 个已处理帧的掩码并集；与官方 freshvac 同口径）
        # 显式 deque：只保留最近 30 个"有掩码"的帧（修 idx>=347 空集 bug）
        fresh_union = None
        recent = list(recent_masks)
        for jm_t in recent:
            fresh_union = jm_t if fresh_union is None else (fresh_union | jm_t)
        # 布尔组合统一在 CPU（past/dyn_t 为 CPU bool），结果再随采样上设备
        vac = (past & ~dyn_t & valid_gt.cpu()).to(device=device)
        vac_fresh = ((fresh_union if fresh_union is not None else past)
                     & ~dyn_t & valid_gt.cpu()).to(device=device)
        if int(vac.sum()) == 0:
            per_frame.append({"frame": idx, "n_vac_px": 0})
            continue

        w2c = np.linalg.inv(pose_by_id[idx])
        cam = Camera(uid=idx, color=None, depth=None,
                     gt_T=torch.eye(4, device=device), projection_matrix=proj,
                     fx=dataset.fx, fy=dataset.fy, cx=dataset.cx, cy=dataset.cy,
                     fovx=dataset.fovx, fovy=dataset.fovy,
                     image_height=H, image_width=W, device=str(device))
        cam.update_RT(torch.as_tensor(w2c[:3, :3], dtype=torch.float32, device=device),
                      torch.as_tensor(w2c[:3, 3], dtype=torch.float32, device=device))

        with torch.no_grad():
            pkg = render(cam, gaussians, pipeline_params, torch.zeros(3, device=device))
            depth_full = pkg["depth"].squeeze()
            u, v, z, proj_valid = alpha_lifecycle.project_gaussians_to_view(
                gaussians.get_xyz.detach(), cam.world_view_transform,
                cam.fx, cam.fy, cam.cx, cam.cy, H, W)
            obs_at = alpha_lifecycle.sample_map_at_gaussians(gt_depth_t, u, v, proj_valid, H, W)
            vac_at = alpha_lifecycle.sample_map_at_gaussians(
                vac.to(device=device, dtype=torch.float32), u, v, proj_valid, H, W) > 0.5
            person_at = alpha_lifecycle.sample_map_at_gaussians(
                dyn_t.to(device=device, dtype=torch.float32), u, v, proj_valid, H, W) > 0.5

            ok = proj_valid & torch.isfinite(obs_at) & (obs_at > 0.01) & vac_at
            dz = z - obs_at
            seam = ok & (dz >= SEAM_LO) & (dz < SEAM_HI)
            a = alpha_all.to(z.device)

            # 颜色归属（仅缝隙带）：基元色 vs 该像素观测色 / 该帧人区色均值
            n_seam = int(seam.sum())
            d_col_obs = d_col_person = None
            if n_seam > 0:
                uu = u[seam].long().clamp(0, W - 1)
                vv = v[seam].long().clamp(0, H - 1)
                c_obs = gt_image[:, vv, uu].transpose(0, 1)          # (n,3)
                c_prim = rgb_all.to(z.device)[seam]                  # (n,3)
                d_col_obs = (c_prim - c_obs).abs().mean(dim=1)
                if int(dyn_t.sum()) > 0:
                    c_person_ref = gt_image[:, dyn_t.to(gt_image.device)].mean(dim=1)
                    d_col_person = (c_prim - c_person_ref).abs().mean(dim=1)

            # 归因渲染：①抹缝隙带 ②抹全部 Δz>0.05（原 carve 目标带+更深）
            exc_full = exc_noghost = exc_noghost_deep = None
            exc_fresh = exc_noghost_fresh = exc_ring = None
            exc_nowstat = exc_nowstat_fresh = None
            if n_seam > 0:
                static_bg = (valid_gt.cpu() & ~dyn_t & ~vac.cpu()).to(device=device)
                # 邻域环（构型匹配对照：空间相邻 ⇒ 几何/入射角相近）
                vac_u8 = vac.cpu().numpy().astype(np.uint8) * 255
                k15 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
                k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
                ring = (cv2.dilate(vac_u8, k15) > 0) & ~(cv2.dilate(vac_u8, k5) > 0)
                ring_t = torch.from_numpy(ring & valid_gt.cpu().numpy()
                                          & ~dyn_t.numpy() & ~vac.cpu().numpy()).to(device=device)
                # TUM 口径：走廊覆盖全场 ⇒ 用"当前非动态"全体作对照（fresh 与全历史各一份）
                nowstat = (valid_gt.cpu() & ~dyn_t).to(device=device)
                nowstat_fresh = (valid_gt.cpu() & ~dyn_t & ~vac_fresh.cpu()).to(device=device)
                deep = ok & (dz > 0.05)
                with torch.no_grad():
                    l1_full = (depth_full - gt_depth_t).abs()
                    exc_full = (l1_full[vac].mean() - l1_full[static_bg].mean()) * 100.0
                    exc_fresh = (l1_full[vac_fresh].mean() - l1_full[static_bg].mean()) * 100.0
                    exc_ring = (l1_full[vac].mean() - l1_full[ring_t].mean()) * 100.0 if int(ring_t.sum()) > 100 else None
                    exc_nowstat = (l1_full[vac].mean() - l1_full[nowstat].mean()) * 100.0 if int(nowstat.sum()) > 100 else None
                    exc_nowstat_fresh = (l1_full[vac_fresh].mean() - l1_full[nowstat_fresh].mean()) * 100.0 if int(vac_fresh.sum()) > 100 else None
                    saved = gaussians._opacity.data[seam].clone()
                    gaussians._opacity.data[seam] = -20.0
                    pkg2 = render(cam, gaussians, pipeline_params, torch.zeros(3, device=device))
                    gaussians._opacity.data[seam] = saved
                    l1_ng = (pkg2["depth"].squeeze() - gt_depth_t).abs()
                    exc_noghost = (l1_ng[vac].mean() - l1_ng[static_bg].mean()) * 100.0
                    exc_noghost_fresh = (l1_ng[vac_fresh].mean() - l1_ng[static_bg].mean()) * 100.0
                    saved_d = gaussians._opacity.data[deep].clone()
                    gaussians._opacity.data[deep] = -20.0
                    pkg3 = render(cam, gaussians, pipeline_params, torch.zeros(3, device=device))
                    gaussians._opacity.data[deep] = saved_d
                    l1_nd = (pkg3["depth"].squeeze() - gt_depth_t).abs()
                    exc_noghost_deep = (l1_nd[vac].mean() - l1_nd[static_bg].mean()) * 100.0

        acc["dz"].append(dz[ok].cpu())
        acc["seam_alpha"].append(a[seam].cpu())
        acc["vac_alpha"].append(a[ok].cpu())
        if d_col_obs is not None:
            acc["d_col_obs_seam"].append(d_col_obs.cpu())
            acc["d_col_person_seam"].append(d_col_person.cpu() if d_col_person is not None else torch.tensor([]))
        if exc_full is not None:
            acc["exc_full"].append(torch.tensor([float(exc_full)]))
            acc["exc_noghost"].append(torch.tensor([float(exc_noghost)]))
            acc["exc_noghost_deep"].append(torch.tensor([float(exc_noghost_deep)]))
            acc["exc_fresh"].append(torch.tensor([float(exc_fresh)]))
            acc["n_vac_fresh"].append(torch.tensor([float(int(vac_fresh.sum()))]))
            if exc_nowstat is not None:
                acc["exc_nowstat"].append(torch.tensor([float(exc_nowstat)]))
            if exc_nowstat_fresh is not None:
                acc["exc_nowstat_fresh"].append(torch.tensor([float(exc_nowstat_fresh)]))
            if exc_ring is not None:
                acc["exc_ring"].append(torch.tensor([float(exc_ring)]))
            acc["exc_noghost_fresh"].append(torch.tensor([float(exc_noghost_fresh)]))
            acc["n_deep"].append(torch.tensor([float(int(deep.sum()))]))
        per_frame.append({
            "frame": idx, "n_vac_px": int(vac.sum()), "n_prims_in_vac": int(ok.sum()),
            "n_seam_band": n_seam,
            "seam_alpha_mean": round(float(a[seam].mean()), 4) if n_seam else None,
            "dz_median": round(float(dz[ok].median()), 4) if int(ok.sum()) else None,
            "exc_full_cm": round(float(exc_full), 4) if exc_full is not None else None,
            "exc_noghost_cm": round(float(exc_noghost), 4) if exc_noghost is not None else None,
            "exc_noghost_deep_cm": round(float(exc_noghost_deep), 4) if exc_noghost_deep is not None else None,
            "exc_fresh_cm": round(float(exc_fresh), 4) if exc_fresh is not None else None,
            "exc_ring_cm": round(float(exc_ring), 4) if exc_ring is not None else None,
            "n_vac_fresh": int(vac_fresh.sum()),
            "exc_nowstat_cm": round(float(exc_nowstat), 4) if exc_nowstat is not None else None,
            "exc_nowstat_fresh_cm": round(float(exc_nowstat_fresh), 4) if exc_nowstat_fresh is not None else None,
            "exc_noghost_fresh_cm": round(float(exc_noghost_fresh), 4) if exc_noghost_fresh is not None else None,
            "n_deep": int(deep.sum()) if n_seam else None,
            "d_col_obs_seam_mean": round(float(d_col_obs.mean()), 4) if d_col_obs is not None else None,
            "d_col_person_seam_mean": (round(float(d_col_person.mean()), 4)
                                       if d_col_person is not None and d_col_person.numel() else None),
        })
        print(f"  f{idx}: vac_px={int(vac.sum())} in_vac={int(ok.sum())} seam={n_seam} "
              f"seam_a={per_frame[-1]['seam_alpha_mean']} "
              f"exc_full={per_frame[-1]['exc_full_cm']} exc_noghost={per_frame[-1]['exc_noghost_cm']} "
              f"dcol_obs={per_frame[-1]['d_col_obs_seam_mean']} "
              f"dcol_person={per_frame[-1]['d_col_person_seam_mean']}", flush=True)

    def cat(key):
        xs = [t for t in acc[key] if t.numel()]
        return torch.cat(xs) if xs else torch.tensor([])

    out = {
        "run_dir": run_dir, "ply": ply_path, "frames": frame_ids,
        "n_prims_total": n_prim,
        "SEAM_alpha_hist": _hist(cat("seam_alpha")),
        "vac_alpha_hist": _hist(cat("vac_alpha")),
        "all_alpha_hist": _hist(alpha_all.cpu()),
        "dz_hist_vac": _hist(cat("dz"), lo=-0.2, hi=0.3, step=0.05),
        "color_d_obs_SEAM": _hist(cat("d_col_obs_seam"), lo=0.0, hi=1.0, step=0.1),
        "color_d_person_SEAM": _hist(cat("d_col_person_seam"), lo=0.0, hi=1.0, step=0.1),
        "excess_full_cm": [round(float(x), 4) for x in cat("exc_full").tolist()],
        "excess_noghost_cm": [round(float(x), 4) for x in cat("exc_noghost").tolist()],
        "excess_noghost_deep_cm": [round(float(x), 4) for x in cat("exc_noghost_deep").tolist()],
        "excess_fresh_cm": [round(float(x), 4) for x in cat("exc_fresh").tolist()],
        "excess_noghost_fresh_cm": [round(float(x), 4) for x in cat("exc_noghost_fresh").tolist()],
        "excess_ring_cm": [round(float(x), 4) for x in cat("exc_ring").tolist()],
        "n_vac_fresh_per_frame": [int(x) for x in cat("n_vac_fresh").tolist()],
        "excess_nowstat_cm": [round(float(x), 4) for x in cat("exc_nowstat").tolist()],
        "excess_nowstat_fresh_cm": [round(float(x), 4) for x in cat("exc_nowstat_fresh").tolist()],
        "n_deep_per_frame": [int(x) for x in cat("n_deep").tolist()],
        "per_frame": per_frame,
        "note": ("SEAM = Δz∈[0.05,0.10) ∧ proj∈vacated；color_d_obs = |基元色−该像素观测色|"
                 "（大 ⇒ 颜色与背景不符 ⇒ H-A 漏人特征）；color_d_person = |基元色−该帧人区均色|"
                 "（小 ⇒ 像人 ⇒ H-A）；exc_full vs exc_noghost = 抹掉缝隙带基元前后的"
                 "vacated-静态配对超额（差=幽灵贡献；noghost 残差≈背景重建误差）"),
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"[census] written {args.out}", flush=True)
    print(f"[census] SEAM α: n={out['SEAM_alpha_hist']['n']} mean={out['SEAM_alpha_hist'].get('mean')} "
          f"p50={out['SEAM_alpha_hist'].get('p50')}", flush=True)


if __name__ == "__main__":
    main()
