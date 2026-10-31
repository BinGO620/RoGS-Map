#!/usr/bin/env python
"""diag_f3_probe.py — f3 几何异常诊断的"第 1 步"探针（远程 CPU，nice 19，不碰 GPU）。

目的：验证 acc（rec→GT）爆炸是否由**远场 floaters / 尺度不匹配**造成——
对比 rec 点云与融合参考云的空间范围，并给出 **robust NN 统计**
（mean vs median vs p95 vs >1m 占比 vs trimmed mean）。若 mean 被极小远场尾巴支配，
则 median/p95/inlier 等鲁棒列才是可用读数。

复用 `utils.geometry_metrics` 的 read_gaussian_xyz / backproject_depth / load_tum_associations。
不写任何仓库文件（只打印 + 可选 --out 写 1 个 json）。

用法（远程，nice 19）：
  nice -n 19 <py> scripts/02_analysis/diag_f3_probe.py --runs <run_dir> [<run_dir> ...] [--out /tmp/diag_f3_probe.json]
"""
import argparse
import bisect
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = None
# 允许从 /tmp 运行：优先环境变量，其次从 __file__ 推断，最后用远程仓库默认路径。
for _cand in (os.environ.get("MONOGS_REPO"), ):
    if _cand and os.path.isdir(_cand):
        REPO = Path(_cand)
if REPO is None:
    try:
        _p = Path(__file__).resolve()
        if _p.parents[1].name == "02_analysis" and (_p.parents[2] / "utils").is_dir():
            REPO = _p.parents[2]
    except IndexError:
        REPO = None
if REPO is None:
    for _cand in ("/home/jiangwenheng/cron/monogs-ours", "/data/monogs-ours"):
        if os.path.isdir(os.path.join(_cand, "utils")):
            REPO = Path(_cand)
            break
if REPO is None:
    raise SystemExit("cannot locate repo root; set MONOGS_REPO")
sys.path.insert(0, str(REPO))
os.chdir(REPO)

import yaml  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402
from utils.geometry_metrics import (  # noqa: E402
    read_gaussian_xyz, backproject_depth, load_tum_associations,
)


def build_mask_lookup(ds_path, mask_subdir="auto", mask_class=15):
    cands = ["dynamic_mask"] if mask_subdir == "auto" else [mask_subdir]  # 重构：canonical 优先
    for sub in cands:
        mdir = os.path.join(ds_path, sub)
        if not os.path.isdir(mdir):
            continue
        idx = {}
        for p in sorted(glob.glob(os.path.join(mdir, "*.png"))):
            idx[os.path.splitext(os.path.basename(p))[0]] = p
        if idx:
            return idx, sub, mask_class
    return {}, None, mask_class


def mask_for_stem(idx, source, cls, depth_stem, rgb_stem=None, ts_lookup=None):
    if not idx:
        return None
    p = idx.get(depth_stem)
    if p is None and rgb_stem is not None:
        p = idx.get(rgb_stem)
    if p is None and ts_lookup is not None:
        try:
            ts = float(depth_stem)
        except ValueError:
            return None
        keys, vals = ts_lookup
        i = bisect.bisect_left(keys, ts)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(keys):
                d = abs(keys[j] - ts)
                if best is None or d < best[0]:
                    best = (d, vals[j])
        if best is not None and best[0] <= 0.05:
            p = best[1]
    if p is None:
        return None
    a = np.asarray(Image.open(p).convert("L"))
    return a > 127 if source in ("dynamic_mask", "dynamic_mask_gtmc") else (a == cls)


def fuse_gt_depth(config, mask_idx, mask_src, mask_cls, frame_stride, pixel_stride, max_depth, trj_est_by_id):
    cal = config["Dataset"]["Calibration"]
    fx, fy, cx, cy = float(cal["fx"]), float(cal["fy"]), float(cal["cx"]), float(cal["cy"])
    s = float(cal["depth_scale"])
    frames = load_tum_associations(config["Dataset"]["dataset_path"])
    ts_lookup = None
    if mask_idx:
        ks = sorted((float(k), v) for k, v in mask_idx.items() if k.replace(".", "", 1).isdigit())
        ts_lookup = ([t for t, _ in ks], [v for _, v in ks])
    pts, n_masked = [], 0
    for i, fr in enumerate(frames):
        if i % frame_stride:
            continue
        dep = np.array(Image.open(fr["depth_path"]), dtype=np.float64) / s
        m = mask_for_stem(mask_idx, mask_src, mask_cls,
                          os.path.splitext(os.path.basename(fr["depth_path"]))[0],
                          os.path.splitext(os.path.basename(fr["rgb_path"]))[0], ts_lookup)
        if m is not None and m.shape == dep.shape:
            dep = dep * (1.0 - m.astype(np.float64))
            n_masked += int(m.sum())
        p = backproject_depth(dep, fx, fy, cx, cy, pixel_stride, max_depth)
        if len(p) == 0:
            continue
        T = trj_est_by_id.get(i, fr["c2w"])
        pts.append((T[:3, :3] @ p.T).T + T[:3, 3])
    if not pts:
        return np.empty((0, 3)), 0
    return np.concatenate(pts, 0), n_masked


def bbox_stats(pts):
    if len(pts) == 0:
        return {}
    lo = np.percentile(pts, 1, axis=0)
    hi = np.percentile(pts, 99, axis=0)
    diag = float(np.linalg.norm(hi - lo))
    c = pts.mean(axis=0)
    r = np.linalg.norm(pts - c, axis=1)
    return {
        "n": int(len(pts)),
        "bbox_diag_m": round(diag, 3),
        "radius_median_m": round(float(np.median(r)), 3),
        "radius_p99_m": round(float(np.percentile(r, 99)), 3),
        "radius_max_m": round(float(r.max()), 3),
    }


def nn_stats(a, b, tree_b, threshold=0.05):
    """a→b 最近邻距离统计（鲁棒）。"""
    d, _ = tree_b.query(a, k=1)
    d = d * 100.0  # cm
    return {
        "mean_cm": round(float(d.mean()), 3),
        "median_cm": round(float(np.median(d)), 3),
        "p95_cm": round(float(np.percentile(d, 95)), 3),
        "p99_cm": round(float(np.percentile(d, 99)), 3),
        "trimmed_mean_cm": round(float(np.mean(d[d <= np.percentile(d, 95)])), 3),
        "frac_within_5cm": round(float((d <= 5.0).mean()), 4),
        "frac_over_1m": round(float((d > 100.0).mean()), 5),
        "frac_over_5m": round(float((d > 500.0).mean()), 5),
    }


def scale_sweep(rec, ref, args):
    """在给定尺度 s 上缩放 rec（关于原点），看 median NN 是否在某 s 处骤降。
    若存在明显最优 s≈1/(bbox ratio) 且 median 落到 cm 级 → 尺度不匹配（可修）；
    若 median 全程高 → 地图本身有大范围 floaters/位移（不可靠）。"""
    tree_ref = cKDTree(ref)
    out = []
    for s in np.round(np.linspace(0.2, 3.0, 29), 3):
        d, _ = tree_ref.query(rec * float(s), k=1)
        d = d * 100.0
        out.append({
            "s": float(s),
            "median_cm": round(float(np.median(d)), 3),
            "mean_cm": round(float(d.mean()), 3),
            "frac_within_5cm": round(float((d <= 5.0).mean()), 4),
        })
    best = min(out, key=lambda o: o["median_cm"])
    return {"best_s": best["s"], "best_median_cm": best["median_cm"],
            "best_frac_within_5cm": best["frac_within_5cm"], "curve": out}


def probe(run_dir, args):
    cfg_path = os.path.join(run_dir, "config.yml")
    trj_path = os.path.join(run_dir, "plot", "trj_full_final.json")
    ply_path = None
    for rel in ("point_cloud/final_after_opt/point_cloud.ply", "point_cloud/final/point_cloud.ply"):
        if os.path.exists(os.path.join(run_dir, rel)):
            ply_path = os.path.join(run_dir, rel); break
    if not (os.path.exists(cfg_path) and os.path.exists(trj_path) and ply_path):
        return {"run_dir": run_dir, "error": "missing cfg/trj/ply"}

    config = yaml.safe_load(open(cfg_path))
    trj = json.load(open(trj_path))
    est_by_id = {int(i): np.asarray(m) for i, m in zip(trj["trj_id"], trj["trj_est"])}
    rec = read_gaussian_xyz(ply_path, sample_count=args.sample_count, seed=0)
    mask_idx, mask_src, mask_cls = build_mask_lookup(config["Dataset"]["dataset_path"], "auto", 15)
    ref, n_masked = fuse_gt_depth(config, mask_idx, mask_src, mask_cls,
                                  args.stride, args.pixel_stride, args.max_depth, est_by_id)
    if len(ref) == 0:
        return {"run_dir": run_dir, "error": "empty fusion"}

    # 参考云抽稀到同量级，避免 KDTree 过慢
    if len(ref) > args.sample_count:
        idx = np.random.default_rng(0).choice(len(ref), size=args.sample_count, replace=False)
        ref = ref[idx]
    tree_rec = cKDTree(rec)
    tree_ref = cKDTree(ref)
    out = {
        "run_dir": run_dir,
        "calib": {k: config["Dataset"]["Calibration"].get(k) for k in ("fx", "fy", "cx", "cy", "distorted", "depth_scale")},
        "dataset_path": config["Dataset"]["dataset_path"],
        "mask_source": mask_src,
        "masked_px_skipped": n_masked,
        "rec_stats": bbox_stats(rec),
        "ref_stats": bbox_stats(ref),
        "acc_rec_to_ref": nn_stats(rec, ref, tree_ref, args.threshold),
        "comp_ref_to_rec": nn_stats(ref, rec, tree_rec, args.threshold),
    }
    rs, fs = out["rec_stats"], out["ref_stats"]
    out["scale_ratio_rec_over_ref"] = round(rs["bbox_diag_m"] / fs["bbox_diag_m"], 4) if fs.get("bbox_diag_m") else None
    out["scale_sweep"] = scale_sweep(rec, ref, args)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--stride", type=int, default=20)
    ap.add_argument("--pixel-stride", type=int, default=5)
    ap.add_argument("--max-depth", type=float, default=5.0)
    ap.add_argument("--sample-count", type=int, default=200000)
    ap.add_argument("--threshold", type=float, default=0.05)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    results = [probe(rd, args) for rd in args.runs]
    for r in results:
        if "error" in r:
            print(f"[probe] FAIL {r['run_dir']}: {r['error']}")
            continue
        print(f"[probe] {r['run_dir'].split('/')[-3]:28s} mask={str(r['mask_source']):18s} "
              f"rec_diag={r['rec_stats']['bbox_diag_m']}m ref_diag={r['ref_stats']['bbox_diag_m']}m "
              f"ratio={r['scale_ratio_rec_over_ref']} | acc mean={r['acc_rec_to_ref']['mean_cm']} "
              f"med={r['acc_rec_to_ref']['median_cm']} p95={r['acc_rec_to_ref']['p95_cm']} "
              f">1m={r['acc_rec_to_ref']['frac_over_1m']}")
    if args.out:
        json.dump(results, open(args.out, "w"), indent=1, ensure_ascii=False)
        print(f"[probe] wrote {args.out}")


if __name__ == "__main__":
    sys.exit(main())
