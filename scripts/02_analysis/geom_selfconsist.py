#!/usr/bin/env python
"""geom_selfconsist.py — 轨迹锚定自洽几何比较（方案 B，2026-09-18 定稿 v2）。

背景（证据链见 resources/notes/bonn_geometry_alignment_2026-09-18.md）：
  ① 官方 Bonn T_g 对齐链**不可复现**——GT 深度+GT 位姿融合云套官方链仍偏 6.8m
     （GT-in/GT-out 决定性检验）；全候选变换搜索+ICP 最优 0.19m/<5cm 15%。
  ② 全局 umeyama（相机中心 est→gt）在本项目短序列上**退化**：balloon 实测给出
     174.9° 伪解（相机中心残差 4cm，但套到地图上偏 268cm vs 恒等 4.33cm）；
     crowd2 同类（172.3°）。渲染对照定论：**地图在 est 位姿系**
     （est 位姿渲染 19.8dB vs GT 位姿 9.8dB；F(map) 渲染 4.5dB 全毁）。
  ③ 本项目所有 run 在 GT 帧 0 启动（est[0]==gt[0] 精确一致，10+ run 验证）
     ⇒ 原生帧即"到 GT 的固定变换"（Identity），与官方"固定变换、不拟合"精神一致。

主协议（本脚本默认）：
  参考云 = GT 深度**用本臂自身 est 位姿**融合（`--fusion-pose est`），
  **排除冻结动态掩码像素**（gtmc 优先 / seg_mask class15；三级时间戳匹配）——
  排除动态像素是必须的：否则"残影越多、与参考云匹配越好"的反向激励。
  比较 = 地图（原样）vs 参考云（恒等变换）：两者同在本臂 est 系，无需任何对齐，
  跨臂可比，度量 = 地图与传感器深度观测的自洽性（鬼影→precision 罚、
  空洞→completion 罚）。
  次级参考（`--fusion-pose mocap`）：用 groundtruth.txt 位姿融合（mocap 系）——
  仅在 est[0]==gt[0] 锚定下与地图近同帧，作为交叉检查，不作主读数。

指标（`compute_geometry_metrics`，阈值默认 5cm）：
  accuracy_cm（rec→ref 均值；低=少鬼影）、completion_cm（ref→rec 均值；低=少空洞）、
  precision@5cm / recall@5cm / fscore。

口径声明：**与官方 accuracy/completion 数字不可比**（自洽口径）；跨臂可比（同参数）。
论文引用须写明口径，不得与官方数字混引。

用法：
  PY=/data/conda_envs/monogs-ours/bin/python
  $PY scripts/02_analysis/geom_selfconsist.py --run-dir <run_dir>
  $PY scripts/02_analysis/geom_selfconsist.py --list runlist.txt --summary out.json
  （可选 --fusion-pose mocap 出交叉检查；--no-mask 关闭动态像素排除（不建议））
"""
import argparse
import bisect
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = None
for _cand in (os.environ.get("MONOGS_REPO"),):
    if _cand and os.path.isdir(os.path.join(_cand, "utils")):
        REPO = Path(_cand)
if REPO is None:
    try:
        _p = Path(__file__).resolve()
        if _p.parents[1].name == "02_analysis" and (_p.parents[2] / "utils").is_dir():
            REPO = _p.parents[2]
    except IndexError:
        REPO = None
if REPO is None:
    for _cand in ("/data/monogs-ours", "/home/jiangwenheng/cron/monogs-ours"):
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
    read_gaussian_xyz,
    backproject_depth,
    load_tum_associations,
    compute_geometry_metrics,
    sample_indices,
)


# ── 掩码（与 render_compare 同款三级匹配：depth stem → RGB stem → 最近邻 ts）──
def build_mask_lookup(ds_path, mask_subdir="auto", mask_class=15):
    import glob as _glob
    cands = ["dynamic_mask"] if mask_subdir == "auto" else [mask_subdir]  # 重构：canonical 优先
    for sub in cands:
        mdir = os.path.join(ds_path, sub)
        if not os.path.isdir(mdir):
            continue
        idx = {}
        for p in sorted(_glob.glob(os.path.join(mdir, "*.png"))):
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


def fuse_gt_depth(config, fusion_pose, mask_idx, mask_src, mask_cls, frame_stride, pixel_stride, max_depth, trj_est_by_id):
    """GT 深度融合：mask-aware + 位姿可选（est/mocap）。返回 (points, stats)。"""
    cal = config["Dataset"]["Calibration"]
    fx, fy, cx, cy = float(cal["fx"]), float(cal["fy"]), float(cal["cx"]), float(cal["cy"])
    s = float(cal["depth_scale"])
    frames = load_tum_associations(config["Dataset"]["dataset_path"])
    ts_lookup = None
    if mask_idx:
        ks = sorted((float(k), v) for k, v in mask_idx.items() if k.replace(".", "", 1).isdigit())
        ts_lookup = ([t for t, _ in ks], [v for _, v in ks])

    pts, n_used, n_masked_skip, n_nomask = [], 0, 0, 0
    for i, fr in enumerate(frames):
        if i % frame_stride:
            continue
        dep = np.array(Image.open(fr["depth_path"]), dtype=np.float64) / s
        # 掩码（按 depth stem；RGB stem 兜底）
        m = mask_for_stem(
            mask_idx, mask_src, mask_cls,
            os.path.splitext(os.path.basename(fr["depth_path"]))[0],
            os.path.splitext(os.path.basename(fr["rgb_path"]))[0],
            ts_lookup,
        )
        if m is None:
            n_nomask += 1
        elif m.shape == dep.shape:
            # 掩码像素置 0 → backproject 的 valid 条件自然排除
            keep = 1.0 - m.astype(np.float64)
            dep = dep * keep
            n_masked_skip += int(m.sum())
        p = backproject_depth(dep, fx, fy, cx, cy, pixel_stride, max_depth)
        if len(p) == 0:
            continue
        T = trj_est_by_id[i] if (fusion_pose == "est" and i in trj_est_by_id) else fr["c2w"]
        pts.append((T[:3, :3] @ p.T).T + T[:3, 3])
        n_used += 1
    if not pts:
        return np.empty((0, 3)), {"frames_used": 0}
    return np.concatenate(pts, 0), {
        "frames_used": n_used,
        "frames_total": len(frames),
        "frame_stride": frame_stride,
        "pixel_stride": pixel_stride,
        "masked_px_skipped": n_masked_skip,
        "frames_without_mask": n_nomask,
        "fusion_pose": fusion_pose,
    }


def robust_nn_stats(a, b, sample_count, seed=0, threshold_m=0.05):
    """鲁棒最近邻统计（rec→ref 与 ref→rec 对称调用）。

    背景（2026-09-18 f3 诊断）：mean 会被极小远场尾巴支配 —— 当参考云深度被
    `max_depth` 裁剪、而 rec 覆盖超出裁剪范围时，far 部分无匹配点，mean 爆炸
    而 median 仍小。故除 mean 外加：median / p95 / p99 / trimmed_mean(≤p95) /
    各类占比（≤5cm、>1m、>5m）。**只增不改**：既有 mean 列（accuracy_cm /
    completion_cm）保持不变，以免破坏已收口数字。
    """
    rng = np.random.default_rng(seed)
    aa = a[sample_indices(len(a), sample_count, rng)] if len(a) > sample_count else a
    tree_b = cKDTree(b)
    d, _ = tree_b.query(aa, k=1, workers=-1)
    d = d * 100.0  # cm
    p95 = float(np.percentile(d, 95))
    return {
        "mean_cm": round(float(d.mean()), 4),
        "median_cm": round(float(np.median(d)), 4),
        "p95_cm": round(float(p95), 4),
        "p99_cm": round(float(np.percentile(d, 99)), 4),
        "trimmed_mean_p95_cm": round(float(np.mean(d[d <= p95])), 4),
        "frac_within_5cm": round(float((d <= 5.0).mean()), 5),
        "frac_over_1m": round(float((d > 100.0).mean()), 6),
        "frac_over_5m": round(float((d > 500.0).mean()), 6),
        "n_eval": int(len(aa)),
    }


def run_one(run_dir, args):
    run_dir = str(run_dir)
    cfg_path = os.path.join(run_dir, "config.yml")
    trj_path = os.path.join(run_dir, "plot", "trj_full_final.json")
    ply_path = None
    for rel in ("point_cloud/final_after_opt/point_cloud.ply", "point_cloud/final/point_cloud.ply"):
        if os.path.exists(os.path.join(run_dir, rel)):
            ply_path = os.path.join(run_dir, rel); break
    for p, nm in ((cfg_path, "config.yml"), (trj_path, "trj_full_final.json")):
        assert os.path.exists(p), f"missing {nm}: {run_dir}"
    assert ply_path, f"missing PLY: {run_dir}"

    config = yaml.safe_load(open(cfg_path))
    trj = json.load(open(trj_path))
    est_by_id = {int(i): np.asarray(m) for i, m in zip(trj["trj_id"], trj["trj_est"])}
    gt_by_id = {int(i): np.asarray(m) for i, m in zip(trj["trj_id"], trj["trj_gt"])}

    # 帧 0 锚定核验（本协议的地基）
    anchor_cm = float(np.linalg.norm(est_by_id[0][:3, 3] - gt_by_id[0][:3, 3]) * 100.0)

    mask_idx, mask_src, mask_cls = ({}, None, args.mask_class)
    if not args.no_mask:
        mask_idx, mask_src, mask_cls = build_mask_lookup(
            config["Dataset"]["dataset_path"], args.mask_subdir, args.mask_class)

    rec = read_gaussian_xyz(ply_path, sample_count=args.sample_count, seed=0)

    out = {
        "run_dir": run_dir,
        "ply": ply_path,
        "protocol": "trajectory-anchored self-consistent v2 (identity frame; NOT the official Bonn T_g chain)",
        "anchor_est0_gt0_cm": round(anchor_cm, 4),
        "mask_source": mask_src,
        "results": {},
    }
    for pose_mode in args.fusion_pose:
        ref, fstats = fuse_gt_depth(
            config, pose_mode, mask_idx, mask_src, mask_cls,
            args.stride, args.pixel_stride, args.max_depth, est_by_id,
        )
        if len(ref) == 0:
            out["results"][pose_mode] = {"error": "empty fusion"}
            continue
        m = compute_geometry_metrics(rec, ref, sample_count=args.sample_count, threshold_m=args.threshold, seed=0)
        m_robust = robust_nn_stats(rec, ref, args.sample_count, seed=0, threshold_m=args.threshold)
        out["results"][pose_mode] = {"fusion": fstats, "metrics": m, "robust": m_robust}
        tag = "PRIMARY" if pose_mode == args.fusion_pose[0] else "xcheck "
        print(
            f"[geom_selfconsist] {os.path.basename(run_dir):<34} [{tag}|{pose_mode:5s}|mask={mask_src}] "
            f"acc={m['accuracy_cm']:8.2f}cm (med={m_robust['median_cm']:7.2f} p95={m_robust['p95_cm']:8.2f} "
            f">1m={m_robust['frac_over_1m']:.3f}) comp={m['completion_cm']:8.2f}cm "
            f"P@5={m['precision_ratio']:5.1f}% R@5={m['completion_ratio']:5.1f}% F={m['fscore']:5.1f} "
            f"(anchor={anchor_cm:.3f}cm)",
            flush=True,
        )

    out_path = args.out or os.path.join(run_dir, "geometry_selfconsist.json")
    json.dump(out, open(out_path, "w"), indent=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--run-dir", help="单个 run 的时间戳目录")
    src.add_argument("--list", help="文本文件，每行一个 run 目录")
    ap.add_argument("--stride", type=int, default=20, help="GT 融合帧步长")
    ap.add_argument("--pixel-stride", type=int, default=5, help="GT 融合像素步长")
    ap.add_argument("--max-depth", type=float, default=5.0, help="GT 融合最大深度（m）")
    ap.add_argument("--sample-count", type=int, default=200000, help="参与指标的采样点数")
    ap.add_argument("--threshold", type=float, default=0.05, help="5cm 阈值")
    ap.add_argument("--fusion-pose", nargs="+", default=["est"], choices=["est", "mocap"],
                    help="参考云的融合位姿；默认 est（自洽主协议）；mocap 作交叉检查")
    ap.add_argument("--mask-subdir", default="auto")
    ap.add_argument("--mask-class", type=int, default=15)
    ap.add_argument("--no-mask", action="store_true", help="关闭动态像素排除（不建议：会造成残影反向激励）")
    ap.add_argument("--out", default=None, help="单 run 的 json 输出路径")
    ap.add_argument("--summary", default=None, help="批模式汇总 json 输出路径")
    args = ap.parse_args()

    runs = [args.run_dir] if args.run_dir else []
    if args.list:
        import glob as _glob
        for ln in open(args.list):
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            if any(ch in ln for ch in "*?["):
                hits = sorted(_glob.glob(ln))
                if hits:
                    runs.append(hits[-1])  # glob 取最新时间戳目录
                else:
                    print(f"[geom_selfconsist] NO MATCH: {ln}", flush=True)
            else:
                runs.append(ln)
    results = []
    for rd in runs:
        try:
            results.append(run_one(rd, args))
        except Exception as exc:  # noqa: BLE001
            print(f"[geom_selfconsist] FAILED {rd}: {exc}", flush=True)
            results.append({"run_dir": rd, "error": str(exc)})

    if args.summary:
        json.dump(results, open(args.summary, "w"), indent=1)
        n_ok = sum(1 for r in results if "results" in r)
        print(f"[geom_selfconsist] summary -> {args.summary} ({n_ok}/{len(results)} ok)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
