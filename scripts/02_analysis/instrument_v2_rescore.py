#!/usr/bin/env python3
"""instrument_v2_rescore.py — 仪器 v2：matched-control freshvac 三参照重评分（离线，零训练）。

prereg：results/lifecycle_paper2/evidence/prereg_instrument_v2.md（判据先锁，3cecccfe）。
判据权威 = prereg §2/§4，本脚本只实现 §2 的口径，不重新定义判据。

三参照（逐帧并行，同一 vacated 区）：
  1. 全域静态  = GT 有效 ∧ ¬dyn ∧ ¬vac              （官方 freshvac 口径）
  2. 邻域环    = dilate15(vac) ∧ ¬dilate5(vac) ∧ 静态（census 现行实现）
  3. 深度-距离匹配（新增）：静态 ∧ GT 深度 ∈ vac GT 深度中位数±带 ∧ 离边 ≥15px
     深度源 = GT（被评对象不自证）；带 = ±15% 起步，对拍失败按 prereg §3 放宽序列。

输出 JSON-only（无 PNG/深度图——远程磁盘友好）。聚合 = median + IQR（禁均值单独作结论）。

用法（远程 REPO 下，含 PLY 的 run 目录）:
    python scripts/02_analysis/instrument_v2_rescore.py \
      --run-dir <rundir> --frames <f1,f2,...> --out <out.json> [--device cuda:0]
"""
from __future__ import annotations

import argparse
import bisect as _bisect
import collections
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
import yaml
from munch import munchify

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gaussian_splatting.gaussian_renderer import render  # noqa: E402
from gaussian_splatting.scene.gaussian_model import GaussianModel  # noqa: E402
from gaussian_splatting.utils.graphics_utils import getProjectionMatrix2  # noqa: E402
from utils import alpha_lifecycle  # noqa: E402
from utils.camera_utils import Camera  # noqa: E402
from utils.dataset import load_dataset  # noqa: E402
from utils.eval_utils import _undistort_depth_like  # noqa: E402
from render_compare import sh_degree_from_ply  # noqa: E402
from utils.gtmc_mask import frozen_mask_index, load_frozen_mask  # noqa: E402
from utils.dynamic_mask_spec import resolve_eval_mask_dir  # noqa: E402
from utils.instrument_v2_core import compute_matched_control_mask  # noqa: E402

EDGE_MARGIN_PX = 15        # prereg §2：与邻域环外半径一致
SUPPORT_MIN_PX = 200       # prereg §2：匹配对照支撑下限（仪器参数，非判效阈值）
SAMPLE_CAP_PX = 5000       # prereg §2：帧内采样上限（固定种子 0 下采样，可复现）
BAND_OPTIONS = [0.15, 0.25, 0.35]   # prereg §3：±15% 起步；对拍失败按序放宽，禁直接放宽起步
GEN = np.random.RandomState(0)     # 固定种子（prereg §2 采样上限条款，可复现）


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


def _summary(xs):
    """median + IQR（prereg §2 聚合口径）。xs = 逐帧数值列表。"""
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    a = np.asarray(xs, dtype=np.float64)
    return {
        "n": int(a.size),
        "median": round(float(np.median(a)), 4),
        "iqr": [round(float(np.quantile(a, 0.25)), 4), round(float(np.quantile(a, 0.75)), 4)],
        "mean": round(float(a.mean()), 4),  # 仅对照参考，不作结论
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--ply", default="final_after_opt")
    ap.add_argument("--config", default=None,
                    help="config 覆盖（默认 <run-dir>/config.yml；L2 gate 批的 run 目录未留 config 快照，"
                         "用 configs/experiments/lifecycle_paper2/l2_<seq>_gate.yaml）")
    ap.add_argument("--band", type=float, default=None,
                    help="匹配带宽覆盖（默认走 prereg §3 对拍序列 ±15/25/35%%）")
    ap.add_argument("--mask-subdir", default=None,
                    help="评测掩码子目录覆盖（默认 None = canonical dynamic_mask/，行为与历史逐位一致）。"
                         "用于并陈**新掩码**（如 dynamic_mask_mover）的读数；非 legacy 名由 "
                         "resolve_eval_mask_dir 直接放行。跨掩码读数**禁混引**（DISCIPLINE 比较前提 6）")
    args = ap.parse_args()

    run_dir = str(Path(args.run_dir).resolve())
    if args.config:
        # --config 走仓库继承解析器（L2 gate 批的 run 目录未留 config 快照，
        # 原 config 为 inherit_from 式：configs/experiments/lifecycle_paper2/l2_<seq>_gate.yaml）
        from utils.config_utils import load_config
        config = load_config(args.config)
    else:
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
    print(f"[v2] PLY={ply_path} n={n_prim}", flush=True)

    trj = json.load(open(trj_path))
    pose_by_id = dict(zip([int(v) for v in trj["trj_id"]],
                          [np.asarray(v, dtype=np.float64) for v in trj["trj_est"]]))

    ds_path = config["Dataset"].get("dataset_path", "")
    mdir, src, legacy = resolve_eval_mask_dir(ds_path, mask_subdir=args.mask_subdir)
    assert mdir, f"no canonical mask dir in {ds_path} (mask_subdir={args.mask_subdir})"
    mask_index = frozen_mask_index(mdir)
    print(f"[v2] mask={src} ({len(mask_index)} stems)", flush=True)
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

    k15 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
    k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))

    # 匹配带对拍状态（prereg §3）：从 ±15% 起步，支撑不足按序放宽，记录实际用值
    band_seq = [args.band] if args.band is not None else BAND_OPTIONS
    band_used = None
    per_frame = []
    exc_full_l, exc_ring_l, exc_m3_l = [], [], []
    vac_px_l = []
    recent_masks = collections.deque(maxlen=30)

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
        vac = (past & ~dyn_t & valid_gt.cpu()).to(device=device)
        vac_px = int(vac.sum())
        if vac_px == 0:
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
            l1_full = (depth_full - gt_depth_t).abs()

            static_bg = (valid_gt.cpu() & ~dyn_t & ~vac.cpu())
            n_static = int(static_bg.sum())
            vac_u8 = vac.cpu().numpy().astype(np.uint8) * 255
            ring = (cv2.dilate(vac_u8, k15) > 0) & ~(cv2.dilate(vac_u8, k5) > 0)
            ring_t = torch.from_numpy(ring & valid_gt.cpu().numpy()
                                      & ~dyn_t.numpy() & ~vac.cpu().numpy()).to(device=device)
            n_ring = int(ring_t.sum())

            # 全域静态对照空集守卫（crowd/TUM：人+腾空区几乎覆盖全视野 ⇒ 对照区为空）
            exc_full = (float((l1_full[vac].mean() - l1_full[static_bg.to(device)].mean()) * 100.0)
                        if n_static >= SUPPORT_MIN_PX else None)
            exc_ring = (float((l1_full[vac].mean() - l1_full[ring_t].mean()) * 100.0)
                        if int(ring_t.sum()) >= SUPPORT_MIN_PX else None)

            # —— 第三对照：深度-距离匹配（GT 深度源，prereg §2；纯函数核心可单测）——
            exc_m3 = None
            band_tried = []
            vac_z = gt_depth_t[vac]
            z_med = float(vac_z.median()) if vac_z.numel() else None
            for band in band_seq:
                m3 = compute_matched_control_mask(
                    gt_depth_t.cpu(), dyn_t, vac.cpu(), valid_gt.cpu(),
                    band=band, edge_margin_px=EDGE_MARGIN_PX,
                    support_min_px=SUPPORT_MIN_PX, sample_cap_px=SAMPLE_CAP_PX,
                    rng=GEN)
                n_m3 = int(m3.sum()) if m3 is not None else 0
                band_tried.append({"band": band, "n_px": n_m3})
                if m3 is not None:
                    m3_t = m3.to(device=device)
                    exc_m3 = float((l1_full[vac].mean() - l1_full[m3_t].mean()) * 100.0)
                    band_used = band_used or band   # 首帧锁带宽（run 级一致）
                    break

            if exc_full is not None:
                exc_full_l.append(exc_full)
            vac_px_l.append(vac_px)
            if exc_ring is not None:
                exc_ring_l.append(exc_ring)
            if exc_m3 is not None:
                exc_m3_l.append(exc_m3)

            per_frame.append({
                "frame": idx, "n_vac_px": vac_px,
                "n_static_bg_px": n_static, "n_ring_px": n_ring,
                "exc_full_cm": round(exc_full, 4) if exc_full is not None else None,
                "exc_ring_cm": round(exc_ring, 4) if exc_ring is not None else None,
                "exc_m3_cm": round(exc_m3, 4) if exc_m3 is not None else None,
                "m3_band_tried": band_tried if exc_m3 is None else None,
                "m3_z_med": round(z_med, 4) if z_med is not None else None,
            })
            print(f"  f{idx}: vac_px={vac_px} static_bg={n_static} exc_full={per_frame[-1]['exc_full_cm']} "
                  f"ring={per_frame[-1]['exc_ring_cm']} m3={per_frame[-1]['exc_m3_cm']}",
                  flush=True)

    def med(key):
        return _summary(exc_full_l if key == "full" else
                        exc_ring_l if key == "ring" else exc_m3_l)

    def sup_med(key):
        xs = [f[key] for f in per_frame if f.get(key) is not None]
        return int(np.median(xs)) if xs else None

    out = {
        "run_dir": run_dir, "ply": ply_path, "frames": frame_ids,
        "n_prims_total": n_prim,
        "prereg": "prereg_instrument_v2.md",
        "mask_subdir": args.mask_subdir if args.mask_subdir else "dynamic_mask",
        "band_used": band_used,
        "support_px_median": {"static_bg": sup_med("n_static_bg_px"),
                              "ring": sup_med("n_ring_px"), "vac": sup_med("n_vac_px")},
        "summary": {
            "exc_full_static": med("full"),
            "exc_ring": med("ring"),
            "exc_depth_matched": med("m3"),
        },
        "per_frame": per_frame,
        "instrument_params": {
            "edge_margin_px": EDGE_MARGIN_PX,
            "support_min_px": SUPPORT_MIN_PX,
            "sample_cap_px": SAMPLE_CAP_PX,
            "band_options": band_seq,
        },
        "note": ("三参照共用同一 vacated 区与同一渲染深度；m3 深度源 = GT（被评对象不自证）；"
                 "聚合 median+IQR（mean 仅对照参考，不作结论，NOTES:516）"),
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"[v2] written {args.out}", flush=True)
    print(f"[v2] band_used={band_used} "
          f"full={out['summary']['exc_full_static']} "
          f"ring={out['summary']['exc_ring']} m3={out['summary']['exc_depth_matched']}",
          flush=True)


if __name__ == "__main__":
    main()
