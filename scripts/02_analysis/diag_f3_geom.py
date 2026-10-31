#!/usr/bin/env python
"""
⚠ 2026-09-21 掩码体系重构：本脚本审计的 seg_mask/ 与 dynamic_mask_gtmc/ 均已**退出评估链**
（前者口径混用、后者失效；见 results/lifecycle_paper2/evidence/l3_instrument_rescore_2026-09-21.md）。
保留作历史审计工具；新的评估掩码是 <seq>/dynamic_mask/（0/255 布尔）。
diag_f3_geom.py — f3 家族自洽几何异常诊断（本地 CPU，无 GPU/open3d 依赖）。

背景：R34 补充批 `evidence/geom_selfconsist_r34.json`（54 run）中，
f3_office / f3_st_rpy / f3_wk_rpy 的 accuracy_cm（rec→GT）异常（42–253cm），
而 completion_cm（GT→rec）≈5cm 正常 —— 典型"rec 含远场 floaters / 尺度不匹配"签名
（见 evidence/geom_selfconsist_r34_note.md 的 3 步诊断建议）。

本脚本做"不需要 PLY/trj"的 3 步中的第 2、3 步（第 1 步需 PLY，在远程 CPU 探针做）：
  1. 掩码类别编码：对每个序列扫 seg_mask / dynamic_mask_gtmc 全帧类别直方图、
     有掩码帧数、命中指定类（默认 15）的帧/像素数 —— 验证 note 的"class 15 稀疏/person 类不对应"线索。
  2. 标定/深度尺度：从各 run config.yml 取 Calibration（fx/fy/cx/cy/distorted/k*）与
     depth_scale；从 depth/ 计算融合深度分位（中位/p95/max）—— 对比 f3 vs f1。
  3. R34 几何读数汇总：从 geom_selfconsist_r34.json 汇总各序列 per-seed acc/completion。

输出：results/paper2_fulltable/evidence/diag_f3_geom.json

用法：
  /data/conda_envs/monogs-ours/bin/python scripts/02_analysis/diag_f3_geom.py
  （可选 --mask-class 15 --max-mask-frames 300 限制扫描量）
"""
import argparse
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
os.chdir(REPO)

# 6 序列：seq -> (数据集子目录, run 前缀 stem)
SEQS = {
    "f3_office": ("datasets/tum/rgbd_dataset_freiburg3_long_office_household", "f3_office"),
    "f3_st_rpy": ("datasets/tum/rgbd_dataset_freiburg3_sitting_rpy", "f3_st_rpy"),
    "f3_wk_rpy": ("datasets/tum/rgbd_dataset_freiburg3_walking_rpy", "f3_wk_rpy"),
    "f1_room": ("datasets/tum/rgbd_dataset_freiburg1_room", "f1_room"),
    "f1_desk2": ("datasets/tum/rgbd_dataset_freiburg1_desk2", "f1_desk2"),
    "moving_obstructing_box": ("datasets/bonn/rgbd_bonn_moving_obstructing_box", "moving_obstructing_box"),
}
ARMS = ("rb", "sw", "gate")


def mask_dir_of(ds_path):
    for sub in ("seg_mask", "dynamic_mask_gtmc"):
        d = os.path.join(ds_path, sub)
        if os.path.isdir(d):
            return d, sub
    return None, None


def scan_mask(ds_path, mask_class, max_frames):
    """扫掩码目录：返回类别直方图、有掩码帧、命中 mask_class 的帧/像素。"""
    mdir, sub = mask_dir_of(ds_path)
    if mdir is None:
        return {"mask_subdir": None, "n_files": 0, "note": "no mask dir"}
    files = sorted(glob.glob(os.path.join(mdir, "*.png")))
    n = len(files)
    out = {
        "mask_subdir": sub,
        "n_files": n,
        "frames_scanned": 0,
        "class_hist": {},
        "frames_with_any_label": 0,
        "frames_hitting_class": 0,
        "total_px_hitting_class": 0,
    }
    if sub == "dynamic_mask_gtmc":
        # gtmc 是二值掩码（>127 = 动态）
        frames_hit = 0
        tot = 0
        for k, p in enumerate(files):
            if max_frames and k >= max_frames:
                break
            a = np.asarray(Image.open(p).convert("L"))
            m = a > 127
            out["frames_scanned"] += 1
            if m.any():
                frames_hit += 1
                tot += int(m.sum())
        out["class_hist"] = {"binary>127": "gtmc (dynamic=1)"}
        out["frames_with_any_label"] = frames_hit
        out["frames_hitting_class"] = frames_hit
        out["total_px_hitting_class"] = tot
        return out
    # seg_mask：label 图，统计全类直方图 + 命中 mask_class
    hist = {}
    frames_any = 0
    frames_hit = 0
    tot_hit = 0
    for k, p in enumerate(files):
        if max_frames and k >= max_frames:
            break
        a = np.asarray(Image.open(p))
        if a.ndim == 3:
            a = a[..., 0]
        out["frames_scanned"] += 1
        uniq, cnt = np.unique(a, return_counts=True)
        if len(uniq) > 1 or (len(uniq) == 1 and uniq[0] != 0):
            frames_any += 1
        for u, c in zip(uniq.tolist(), cnt.tolist()):
            hist[u] = hist.get(u, 0) + int(c)
        hit = int((a == mask_class).sum())
        if hit > 0:
            frames_hit += 1
            tot_hit += hit
    # 只保留 top 类别，避免 json 过大
    top = dict(sorted(hist.items(), key=lambda kv: -kv[1])[:15])
    out["class_hist"] = {int(k): v for k, v in top.items()}
    out["class_hist_full_nclasses"] = len(hist)
    out["class_1_px"] = int(hist.get(1, 0))
    out["class_15_px"] = int(hist.get(15, 0))
    out["frames_with_any_label"] = frames_any
    out["frames_hitting_class"] = frames_hit
    out["total_px_hitting_class"] = tot_hit
    return out


def fused_depth_stats(ds_path, max_frames=40):
    """从 depth/ 抽 max_frames 帧算融合深度分位（raw/ depth_scale 由 config 给）。"""
    ddir = os.path.join(ds_path, "depth")
    if not os.path.isdir(ddir):
        return None
    files = sorted(glob.glob(os.path.join(ddir, "*.png")))
    if not files:
        return None
    step = max(1, len(files) // max_frames)
    vals = []
    for p in files[::step]:
        a = np.asarray(Image.open(p), dtype=np.float64)
        v = a[a > 0]
        if v.size:
            vals.append(v)
    if not vals:
        return None
    v = np.concatenate(vals)
    return {
        "n_frames_sampled": len(vals),
        "raw_median": float(np.median(v)),
        "raw_p95": float(np.percentile(v, 95)),
        "raw_max": float(v.max()),
    }


def config_of(seq_stem, arm, seed):
    """定位 R34 run 的运行时 config.yml。"""
    base = Path(f"results/paper2_rollout/r34_{arm}_{seq_stem}_seed{seed}")
    hits = sorted(base.glob(f"datasets_*/**/seed_{seed}/*/config.yml"))
    return hits[-1] if hits else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mask-class", type=int, default=15)
    ap.add_argument("--max-mask-frames", type=int, default=0, help="0 = 全扫")
    ap.add_argument("--out", default="results/paper2_fulltable/evidence/diag_f3_geom.json")
    args = ap.parse_args()

    import yaml
    report = {"mask_class_probed": args.mask_class, "sequences": {}}

    for seq, (ds_path, stem) in SEQS.items():
        ds_path = str(Path(ds_path).resolve())
        entry = {"dataset_path": ds_path, "exists": os.path.isdir(ds_path)}

        # 掩码扫描
        if os.path.isdir(ds_path):
            entry["mask"] = scan_mask(ds_path, args.mask_class, args.max_mask_frames)
            entry["fused_depth_raw_stats"] = fused_depth_stats(ds_path)
        else:
            entry["mask"] = {"error": "dataset path missing"}
            entry["fused_depth_raw_stats"] = None

        # config 标定（取 rb seed0）
        cfgp = config_of(stem, "rb", 0)
        entry["config_path"] = str(cfgp) if cfgp else None
        if cfgp and cfgp.exists():
            cfg = yaml.safe_load(open(cfgp))
            cal = cfg.get("Dataset", {}).get("Calibration", {})
            entry["calibration"] = {
                "fx": cal.get("fx"), "fy": cal.get("fy"),
                "cx": cal.get("cx"), "cy": cal.get("cy"),
                "distorted": cal.get("distorted"),
                "depth_scale": cal.get("depth_scale"),
                "k1": cal.get("k1"), "k2": cal.get("k2"),
                "p1": cal.get("p1"), "p2": cal.get("p2"),
            }
            entry["config_dataset_path"] = cfg.get("Dataset", {}).get("dataset_path")
        # depth_scale 应用到融合深度
        if entry.get("fused_depth_raw_stats") and entry.get("calibration", {}).get("depth_scale"):
            s = float(entry["calibration"]["depth_scale"])
            f = entry["fused_depth_raw_stats"]
            entry["fused_depth_m"] = {
                "median": round(f["raw_median"] / s, 3),
                "p95": round(f["raw_p95"] / s, 3),
                "max": round(f["raw_max"] / s, 3),
            }
        report["sequences"][seq] = entry

    # R34 几何读数汇总
    gjson = Path("results/paper2_fulltable/evidence/geom_selfconsist_r34.json")
    if gjson.exists():
        d = json.load(open(gjson))
        agg = {}
        for e in d:
            rd = e.get("run_dir", "")
            seq = next((s for s in SEQS if s in rd), None)
            if seq is None:
                continue
            m = e.get("results", {}).get("est", {}).get("metrics")
            fst = e.get("results", {}).get("est", {}).get("fusion", {})
            if not m:
                continue
            agg.setdefault(seq, []).append({
                "run_dir": rd,
                "accuracy_cm": m.get("accuracy_cm"),
                "completion_cm": m.get("completion_cm"),
                "fscore": m.get("fscore"),
                "mask_source": e.get("mask_source"),
                "masked_px_skipped": fst.get("masked_px_skipped"),
                "fusion_frames_used": fst.get("frames_used"),
            })
        geo = {}
        for seq, rows in agg.items():
            acc = np.array([r["accuracy_cm"] for r in rows if r["accuracy_cm"] is not None])
            comp = np.array([r["completion_cm"] for r in rows if r["completion_cm"] is not None])
            geo[seq] = {
                "n": len(rows),
                "acc_median": round(float(np.median(acc)), 3) if acc.size else None,
                "acc_min": round(float(acc.min()), 3) if acc.size else None,
                "acc_max": round(float(acc.max()), 3) if acc.size else None,
                "comp_median": round(float(np.median(comp)), 3) if comp.size else None,
                "mask_sources": sorted({str(r["mask_source"]) for r in rows}),
                "masked_px_skipped_set": sorted({r["masked_px_skipped"] for r in rows}),
                "rows": rows,
            }
        report["geom_r34"] = geo

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"written {out}")

    # 控制台摘要
    for seq, e in report["sequences"].items():
        m = e.get("mask", {})
        cal = e.get("calibration", {})
        fd = e.get("fused_depth_m", {})
        g = report.get("geom_r34", {}).get(seq, {})
        print(f"[{seq:26s}] mask={m.get('mask_subdir')} files={m.get('n_files')} "
              f"hit_class_frames={m.get('frames_hitting_class')} hit_px={m.get('total_px_hitting_class')} "
              f"| distorted={cal.get('distorted')} fx={cal.get('fx')} depth_scale={cal.get('depth_scale')} "
              f"| depth_med={fd.get('median')}m | acc_med={g.get('acc_median')} comp_med={g.get('comp_median')}")


if __name__ == "__main__":
    sys.exit(main())
