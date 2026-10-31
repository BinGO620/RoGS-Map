#!/usr/bin/env python
"""repair_map.py — DynPort-Offline：离线地图动态修复算子（单序列单次）。

设计本体 = resources/notes/dynport_offline_design_2026-10-06.md；
判据本体 = results/dynport_offline/evidence/prereg_dynport_offline_L1.md。

做什么（一次修复）：
  1. 载入底图 run（`dyn_probe.Run`：最终 PLY + 逐帧轨迹 + 数据集 + 掩码索引）；
  2. 取**底图 run 的 KF 日程**（console `Candidate insert KF <n>`，严格 stride=5）；
  3. 逐 KF：离线重算 MaskRCNN 掩码 → 掩码∧传感器深度反投影 → 决策核
     （Case1 KNN 复用 / Case2 新建 / Cond1 可观测删 / Cond2 寿命删）；
  4. 冻结静态拟合（只对动态层参数跑 Adam；静态底图张量不在优化器 ⇒ 逐位不动）；
  5. 落盘：逐 KF 快照 `dynport_causal/frame_<kf>.npz` + `dynamic_rows.npy`
     + 合并 PLY + `dynport_counters.csv` + `repair_timing.json`。

default-off（J9）：`--disable` ⇒ 输出的 PLY 与底图**逐位一致**（直接复制），无快照。

复用（零核心代码改动）：`dyn_probe.Run/PackedPC/render/unproject_mask/make_dynamic/dyn_tensors/
fit_dynamic/frame_data`；`utils.dyn_port_buffer.DynPortBuffer`（决策核）；
`utils.dyn_port_offline.OfflineDynMap`（自持动态层 MapAccess）；
`utils.semantic_mask.compute_semantic_dynamic_mask`（方法输入掩码，离线重算）。

用法：
  python scripts/dynport_offline/repair_map.py \
      --base-run <R33 baseline run dir> --out <out dir> --arm R1 \
      --enable --fit-iters 300 --lam-d 0.20 --cap 50000 --lmax 45 --unproj-stride 3
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

_spec = importlib.util.spec_from_file_location(
    "dyn_probe", REPO / "scripts/02_analysis/dyn_probe.py")
probe = importlib.util.module_from_spec(_spec)
sys.modules["dyn_probe"] = probe
_spec.loader.exec_module(probe)

from utils.dyn_port_buffer import dynport_cfg, write_counters_csv  # noqa: E402
from utils.dyn_port_offline import OfflineDynMap, build_offline_map, make_core  # noqa: E402


# ── KF 日程（底图 console）──────────────────────────────────────────────────
def parse_kf_schedule(console_log) -> list[int]:
    """底图 run 的 KF 日程（`Candidate insert KF <n>`）。与 dyn_probe.keyframes_of 同源。"""
    import re
    txt = Path(console_log).read_text(errors="ignore")
    return sorted({int(m) for m in re.findall(r"Candidate insert KF (\d+):", txt)})


# ── 合并 PLY 写出（judge/load_ply 可读；degree-0 底图）──────────────────────
_PLY_ATTRS = ["x", "y", "z", "nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2",
              "opacity", "scale_0", "scale_1", "scale_2",
              "rot_0", "rot_1", "rot_2", "rot_3",
              "static_prob", "static_obs_count", "unmapped_score"]


def _to_np(x):
    if x is None:
        return None
    return x.detach().cpu().numpy() if hasattr(x, "detach") else np.asarray(x)


def write_merged_ply(base_model, dyn, out_path):
    """底图（全静态）+ 动态层 → 单 PLY（schema 与 run 的 final_after_opt 同）。

    返回 `dynamic_rows`（bool (n_total,)：后 n_dyn 行为 True）。
    """
    from plyfile import PlyData, PlyElement
    m = base_model
    xyz = _to_np(m.get_xyz)
    n_static = int(xyz.shape[0])
    fdc = _to_np(m._features_dc).reshape(n_static, 3)      # (N,1,3)→(N,3)
    opa = _to_np(m._opacity).reshape(n_static, 1)
    scl = _to_np(m._scaling).reshape(n_static, 3)
    rot = _to_np(m._rotation).reshape(n_static, 4)
    sp = _to_np(getattr(m, "static_prob", None))
    sp = sp.reshape(n_static, 1) if sp is not None else np.full((n_static, 1), 0.7)
    soc = _to_np(getattr(m, "static_obs_count", None))
    soc = soc.reshape(n_static, 1) if soc is not None else np.zeros((n_static, 1))
    ums = _to_np(getattr(m, "unmapped_score", None))
    ums = ums.reshape(n_static, 1) if ums is not None else np.zeros((n_static, 1))

    if dyn is not None and int(dyn["xyz"].shape[0]) > 0:
        nd = int(dyn["xyz"].shape[0])
        d_xyz = _to_np(dyn["xyz"])
        d_fdc = _to_np(dyn["dc"]).reshape(nd, 3)
        d_opa = _to_np(dyn["opa"]).reshape(nd, 1)
        d_scl = _to_np(dyn["log_scale"]).reshape(nd, 3)
        d_rot = _to_np(dyn["rot"]).reshape(nd, 4)
        d_sp = np.zeros((nd, 1)); d_soc = np.zeros((nd, 1)); d_ums = np.zeros((nd, 1))
        xyz = np.concatenate([xyz, d_xyz], 0)
        fdc = np.concatenate([fdc, d_fdc], 0)
        opa = np.concatenate([opa, d_opa], 0)
        scl = np.concatenate([scl, d_scl], 0)
        rot = np.concatenate([rot, d_rot], 0)
        sp = np.concatenate([sp, d_sp], 0)
        soc = np.concatenate([soc, d_soc], 0)
        ums = np.concatenate([ums, d_ums], 0)
        is_dyn = np.concatenate([np.zeros(n_static, bool), np.ones(nd, bool)])
    else:
        is_dyn = np.zeros(n_static, bool)

    n = int(xyz.shape[0])
    normals = np.zeros_like(xyz)
    table = np.concatenate([xyz, normals, fdc, opa, scl, rot, sp, soc, ums], axis=1)
    dtype_full = [(a, "f4") for a in _PLY_ATTRS]
    elements = np.empty(n, dtype=dtype_full)
    elements[:] = list(map(tuple, table))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(elements, "vertex")]).write(out_path)
    return is_dyn


def write_snapshot(cdir: Path, kf: int, c2w: np.ndarray, dyn: dict) -> bool:
    """逐 KF 动态层快照（格式 = utils/dynport_causal_log 同款；judge --causal 零改动消费）。"""
    if dyn is None or int(dyn["xyz"].shape[0]) == 0:
        return False
    cdir.mkdir(parents=True, exist_ok=True)
    np.savez(cdir / f"frame_{int(kf):06d}.npz",
             frame_idx=np.int64(kf), c2w=np.asarray(c2w, dtype=np.float64),
             xyz=_to_np(dyn["xyz"]).astype(np.float32),
             log_scale=_to_np(dyn["log_scale"]).astype(np.float32),
             rot=_to_np(dyn["rot"]).astype(np.float32),
             opa=_to_np(dyn["opa"]).astype(np.float32),
             f_dc=_to_np(dyn["dc"]).astype(np.float32))
    return True


def _cam_RT(run, kf, w2c):
    """从 w2c 拆 R/T（仓库约定：R=w2c[:3,:3], T=w2c[:3,3]）。"""
    return np.asarray(w2c)[:3, :3], np.asarray(w2c)[:3, 3]


def _offline_mask(config, image, erode_px=0):
    """离线重算方法输入掩码（MaskRCNN，同 config）；返回 (H,W) bool 或 None。

    `erode_px > 0` = **掩码收边**（prereg §4「一次结构快修」）：动态基元的 KNN 尺度
    （~2cm）会越过语义掩码边界渗入静态评估区（S5 诊断：受损像素 100% 落在边界 ≤5px 内）；
    插入前把掩码腐蚀 k 像素 ⇒ 基元足迹落在掩码内侧，不污染静态区。
    """
    from utils.semantic_mask import compute_semantic_dynamic_mask
    m = compute_semantic_dynamic_mask(config, image)
    if m is None:
        return None
    m = np.asarray(_to_np(m), dtype=bool)
    m = m[0] if m.ndim == 3 else m
    if int(erode_px) > 0:
        from scipy import ndimage
        m = ndimage.binary_erosion(m, iterations=int(erode_px))
    return m


def _clamp_dyn_scale(dyn, max_scale_m, max_xyz_delta=None):
    """拟合后把动态层 raw log_scale 夹到 log(max_scale_m)（S5 结构快修之一）。

    根因（2026-10-06 L1 实测）：`fit_dynamic` 只优化 5 组参数、**无尺度上界**，个别动态基元
    拟合后尺度从 0.001 涨到 max **2.06 m**（插入期的 `max_scale_m=0.02` 约束被绕过），
    其渲染足迹溢出语义掩码、遮住静态评估区 ⇒ J3 破线（与"掩码收边"无关：收边反而更差）。
    夹回插入约束 ⇒ 动态基元足迹不越界。
    """
    if dyn is None or max_scale_m is None or float(max_scale_m) <= 0:
        return 0
    import math as _m
    import torch as _t
    with _t.no_grad():
        hi = _m.log(float(max_scale_m))
        ls = dyn["log_scale"]
        before = int((ls > hi).sum().item())
        ls.data.clamp_(max=hi)
    return before


def _suppress_out_of_mask(dyn, run, w2c, mask, log=print):
    """**投影掩码剪枝**（S5 结构快修主项；prereg §4「动态层→静态区污染路径」的靶）。

    机制：拟合无 xyz 约束 ⇒ 动态基元会漂到人物掩码之外，其渲染足迹遮住静态评估区
    （S5 决定性诊断：oracle 逐帧层静态 Δ≈+0.003，而累积/拟合层 Δ 达 −0.9~−3.9）。
    做法：把第 `kf` 帧动态层基元按 `kf` 位姿投影回像素，**投影中心落在方法掩码（MaskRCNN）
    之外的基元不透明度置 −30（等效剪除）**。因果（只用当前 KF 的掩码/位姿）+ 方法侧掩码
    （非 canonical，口径合规）。返回被抑制数。
    """
    if dyn is None or int(dyn["xyz"].shape[0]) == 0 or mask is None:
        return 0
    import torch as _t
    fx, fy, cx, cy = float(run.dataset.fx), float(run.dataset.fy), float(run.dataset.cx), float(run.dataset.cy)
    H, W = mask.shape
    with _t.no_grad():
        xyz = dyn["xyz"].detach().cpu().numpy()
        R = np.asarray(w2c)[:3, :3]; T = np.asarray(w2c)[:3, 3]
        pc = (R @ xyz.T).T + T
        z = pc[:, 2]
        ok = z > 1e-3
        zz = np.where(ok, z, 1.0)
        u = (fx * pc[:, 0] / zz + cx).astype(np.int64)
        v = (fy * pc[:, 1] / zz + cy).astype(np.int64)
        inside = ok & (u >= 0) & (u < W) & (v >= 0) & (v < H)
        inmask = np.zeros(xyz.shape[0], dtype=bool)
        inmask[inside] = mask[v[inside], u[inside]]
        out = ~inmask
        n = int(out.sum())
        if n:
            o = dyn["opa"]
            o.data[_t.as_tensor(np.nonzero(out)[0], device=o.device)] = -30.0
    return n


def repair(run, out_dir, cfg, enable, log=print, max_kf=None, erode_px=0, max_scale_m=0.02,
           suppress_out_mask=True, naive=False):
    """执行一次修复；返回 timing dict。default-off ⇒ 只复制底图 PLY。max_kf 仅冒烟用（截断 KF）。

    `erode_px` 从 `run.config["DynPort"]["mask_erode_px"]` 直取（**不经 `dynport_cfg`**——该函数
    白名单会静默丢弃未登记键，2026-10-06 实测），避免"配置静默丢弃"类缺陷。
    `suppress_out_mask` = **投影掩码剪枝**（S5 结构快修主项；默认开）。
    `naive` = **朴素插入对照臂**（prereg_naive_ctrl_2026-10-13.md）：跳过生命周期决策核
    （DynPortBuffer 的 Case1/Cond1/Cond2/cap）与 S5（剪枝+夹回）——逐 KF 把掩码反投影点
    全部作为新基元插入，其余管线（掩码源/深度源/stride/fit/快照/合并 PLY）与 R1 逐位同口径。
    **单变量 = 生命周期 + S5**；该臂用于回答"完整算子是否优于同口径朴素插入"（审阅 P0-1）。
    """
    erode_px = int(erode_px or 0)
    n_sup = 0
    n_clamped = 0
    out_dir = Path(out_dir)
    (out_dir / "point_cloud" / "final_after_opt").mkdir(parents=True, exist_ok=True)
    (out_dir / "plot").mkdir(parents=True, exist_ok=True)
    (out_dir / "dynport_causal").mkdir(parents=True, exist_ok=True)

    base_ply = Path(run.ply_path)
    out_ply = out_dir / "point_cloud" / "final_after_opt" / "point_cloud.ply"
    # trj 逐位复制（J8 构造核验）
    shutil.copy2(Path(run.run_dir) / "plot" / "trj_full_final.json",
                 out_dir / "plot" / "trj_full_final.json")
    shutil.copy2(Path(run.run_dir) / "config.yml", out_dir / "config.yml")

    if not enable:
        # default-off（J9）：输出 PLY 与底图**逐位一致**；dynamic_rows 全 False；无快照。
        shutil.copy2(base_ply, out_ply)
        np.save(out_dir / "dynport_causal" / "dynamic_rows.npy",
                np.zeros(_n_base(run), dtype=bool))
        timing = {"enabled": False, "repair_wall_s": 0.0, "n_kf": 0, "bit_identical": True}
        (out_dir / "repair_timing.json").write_text(json.dumps(timing, indent=2))
        return timing

    pc = probe.PackedPC(run.gaussians)
    omap = build_offline_map(run.gaussians, cfg["lineage_base"],
                             min_scale=0.001, max_scale=0.02)
    core = make_core(cfg, omap) if not naive else None

    schedule = parse_kf_schedule(Path(run.run_dir) / "console.log")
    if not schedule:
        raise SystemExit(f"底图 console 无 KF 日程: {run.run_dir}/console.log")
    if max_kf is not None and int(max_kf) > 0:
        schedule = schedule[:int(max_kf)]
        log(f"[repair] ⚠ 冒烟截断：只跑前 {len(schedule)} 个 KF（非权威）")
    log(f"[repair] KF 日程 {len(schedule)} 个（{schedule[:3]}…{schedule[-1]}），"
        f"底图 {int(run.gaussians.get_xyz.shape[0])} 基元"
        + ("；**朴素插入对照臂（无生命周期/无 S5）**" if naive else ""))

    t_all = time.perf_counter()
    t_fit = t_mask = 0.0
    n_snap = 0
    n_inserted = 0
    for kf in schedule:
        fd = run.frame_data(kf)
        if fd is None:
            continue
        gt_image, gt_depth, w2c = fd
        mask = _offline_mask(run.config, gt_image, erode_px=erode_px)
        if mask is None:
            continue
        R, T = _cam_RT(run, kf, w2c)
        t0 = time.perf_counter()
        pts, cols = probe.unproject_mask(run, kf, gt_image, gt_depth, w2c,
                                         stride=cfg["unproj_stride"], mask_override=mask)
        t_mask += time.perf_counter() - t0
        if pts is None or len(pts) == 0:
            if core is not None:
                core.step(kf, np.empty((0, 3), np.float32), np.empty((0, 3), np.float32), None)
        else:
            if float(cfg.get("control_shift_m", 0.0)) != 0.0:
                pts = _shift_cam_x(pts, np.linalg.inv(w2c), cfg["control_shift_m"])
            if naive:
                # 朴素臂：全量插入为新基元（无 KNN 复用 / 无 Cond1/Cond2 / 无 cap）
                omap.insert(np.asarray(pts, dtype=np.float32),
                            np.asarray(cols, dtype=np.float32),
                            cfg["lineage_base"] + kf)
                n_inserted += int(len(pts))
            else:
                dbar = float(np.mean(gt_depth.cpu().numpy()[mask]))
                core.step(kf, pts, cols, dbar)
        # 冻结静态拟合（只优化动态层参数）
        if omap.d is not None and int(omap.d["xyz"].shape[0]) > 0 and cfg["fit_iters"] > 0:
            cam = run.camera(kf, w2c)
            t0 = time.perf_counter()
            probe.fit_dynamic(run, cam, pc, omap.d, gt_image, gt_depth, mask,
                              int(cfg["fit_iters"]), _LRS)
            t_fit += time.perf_counter() - t0
            if not naive:
                # 尺度夹回（S5 结构快修之一；28283206a 引入、72a05c27d 误删调用 ⇒ 本轮恢复）。
                # 拟合无尺度上界 ⇒ 个别基元从 0.001 涨到 2.06 m；夹回插入期上界防足迹溢出。
                n_clamped += _clamp_dyn_scale(omap.d, max_scale_m)
                if suppress_out_mask:
                    n_sup += _suppress_out_of_mask(omap.d, run, w2c, mask)
        # 快照（用最终轨迹位姿，c2w = inv(w2c)）
        c2w = np.linalg.inv(np.asarray(w2c, dtype=np.float64))
        if write_snapshot(out_dir / "dynport_causal", kf, c2w, omap.d):
            n_snap += 1

    is_dyn = write_merged_ply(run.gaussians, omap.d, out_ply)
    np.save(out_dir / "dynport_causal" / "dynamic_rows.npy", is_dyn)
    if core is not None:
        write_counters_csv(core, str(out_dir / "dynport_counters.csv"))
    else:
        # 朴素臂：简单逐帧计数落盘（无生命周期语义；J5 不适用于本臂，标注）
        import csv as _csv
        with open(out_dir / "dynport_counters.csv", "w", newline="") as _f:
            w = _csv.DictWriter(_f, fieldnames=["frame", "inserted", "n_buf"])
            w.writeheader()
            for kf in schedule:
                w.writerow({"frame": kf, "inserted": 0, "n_buf": n_inserted})
    wall = time.perf_counter() - t_all
    # J4 参照：底图 SLAM 全程墙钟（来自底图 run 的 efficiency_raw.csv，只读）
    online_time_s = _read_online_time_s(run.run_dir)
    timing = {"enabled": True, "naive": bool(naive), "repair_wall_s": round(wall, 2),
              "fit_time_s": round(t_fit, 2), "unproject_time_s": round(t_mask, 2),
              "online_time_s": online_time_s,
              "n_kf": int(len(schedule)), "n_snapshots": int(n_snap),
              "n_static": int(run.gaussians.get_xyz.shape[0]),
              "n_dyn": int(0 if omap.d is None else omap.d["xyz"].shape[0]),
              "n_naive_inserted": n_inserted,
              "vitality": (core.vitality() if core is not None else
                           {"case1_hits": 0, "case2_new": n_inserted,
                            "cond1_deleted": 0, "cond2_deleted": 0,
                            "evicted_total": 0, "cap_hits": 0, "buf_final": n_inserted}),
              "mask_erode_px": erode_px, "n_suppressed": n_sup,
              "n_clamped": n_clamped, "max_scale_m": max_scale_m,
              # S5 结构快修开态**显式落盘**（G1 v4 major#6）：批次 provenance 可机检，不靠 CLI 默认。
              "s5_suppress_out_mask": (bool(suppress_out_mask) and not naive),
              "s5_scale_clamp": (bool(max_scale_m and float(max_scale_m) > 0) and not naive),
              **{k: cfg[k] for k in
              ("lam_d", "cap", "lmax", "unproj_stride", "fit_iters", "control_shift_m")}}
    (out_dir / "repair_timing.json").write_text(json.dumps(timing, indent=2))
    log(f"[repair] 完成：dyn={timing['n_dyn']} 快照={n_snap} 墙钟={wall:.1f}s "
        f"（拟合 {t_fit:.1f}s）")
    return timing


_LRS = {"xyz": 5e-4, "scale": 5e-3, "rot": 1e-3, "opa": 5e-2, "dc": 5e-3}


def _n_base(run):
    return int(run.gaussians.get_xyz.shape[0])


def _read_online_time_s(run_dir):
    """底图 SLAM 全程墙钟（efficiency_raw.csv 的 online_time_s）——J4 参照，只读。"""
    import csv
    f = Path(run_dir) / "efficiency_raw.csv"
    if not f.exists():
        return None
    rows = list(csv.DictReader(open(f)))
    if not rows:
        return None
    try:
        return float(rows[0].get("online_time_s"))
    except (TypeError, ValueError):
        return None


def _shift_cam_x(pts_w, w2c, shift_m):
    """世界点沿相机 x 轴平移（C− 阴性对照；与在线 _shift_cam_x 同式）。"""
    c2w = np.linalg.inv(w2c)
    pc = (w2c[:3, :3] @ np.asarray(pts_w, dtype=np.float64).T).T + w2c[:3, 3]
    pc[:, 0] += float(shift_m)
    return ((c2w[:3, :3] @ pc.T).T + c2w[:3, 3]).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-run", required=True, help="底图 run 目录（R33 baseline）")
    ap.add_argument("--out", required=True, help="输出目录（R1/C− 各一份）")
    ap.add_argument("--arm", default="R1")
    ap.add_argument("--enable", action="store_true", help="启用修复；缺省 = default-off（J9）")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--lam-d", type=float, default=0.20)
    ap.add_argument("--cap", type=int, default=50000)
    ap.add_argument("--lmax", type=int, default=45)
    ap.add_argument("--unproj-stride", type=int, default=3)
    ap.add_argument("--fit-iters", type=int, default=300)
    ap.add_argument("--lineage-base", type=int, default=402653184)
    ap.add_argument("--control-shift-m", type=float, default=0.0)
    ap.add_argument("--mask-erode-px", type=int, default=0,
                    help="插入掩码收边（kxpx；0=关）——prereg §4 一次结构快修的靶")
    ap.add_argument("--max-scale-m", type=float, default=0.02,
                    help="动态基元尺度上界（拟合后夹回；= 插入期 max_scale_m，S5 结构快修靶）")
    ap.add_argument("--no-suppress-out-mask", action="store_true",
                    help="关闭投影掩码剪枝（S5 结构快修主项；默认开）")
    ap.add_argument("--naive", action="store_true",
                    help="朴素插入对照臂（prereg_naive_ctrl_2026-10-13）：跳过生命周期决策核与 S5，"
                         "逐 KF 全量插入为新基元；其余管线与 R1 同口径")
    ap.add_argument("--max-kf", type=int, default=0, help="冒烟用：只跑前 N 个 KF（0 = 全跑）")
    args = ap.parse_args()

    import yaml
    base_cfg = yaml.safe_load(open(Path(args.base_run) / "config.yml"))
    base_cfg["DynPort"] = {"enabled": bool(args.enable), "lam_d": args.lam_d, "cap": args.cap,
                           "lmax": args.lmax, "unproj_stride": args.unproj_stride,
                           "fit_iters": args.fit_iters, "lineage_base": args.lineage_base,
                           "control_shift_m": args.control_shift_m,
                           "mask_erode_px": args.mask_erode_px}
    cfg = dynport_cfg(base_cfg)
    run = probe.Run(args.base_run, device=args.device)
    # Run 只读 config.yml；此处把开关并入 run.config 供掩码重算/落盘使用。
    run.config = base_cfg
    # 若原 config 无 SemanticMask，补 MaskRCNN 口径（与在线同）。
    run.config.setdefault("SemanticMask", {"enabled": True, "model": "maskrcnn",
                                           "dynamic_classes": [1], "dilate_px": 7})
    timing = repair(run, args.out, cfg, args.enable, max_kf=(args.max_kf or None),
                    erode_px=args.mask_erode_px, max_scale_m=args.max_scale_m,
                    suppress_out_mask=(not args.no_suppress_out_mask),
                    naive=args.naive)
    print(json.dumps(timing, indent=2))


if __name__ == "__main__":
    main()
