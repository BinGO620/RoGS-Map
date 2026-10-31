#!/usr/bin/env python3
"""compare_mask_coverage.py — 并陈**两种评测掩码**下的同一批臂（canonical vs mover）。

用途（用户 2026-09-25 定的目标：建图侧正向效果）
--------------------------------------------------
L3 主臂运行期不读掩码 ⇒ 换掩码只是换度量。本脚本回答第一个决定性问题：

  **把评测区从"人轨迹"扩到"人+箱/气球等所有移动体"后，
   exit vs off 的建图侧效应是变大/现身，还是被稀释/反号？**

- 变大/现身 ⇒ 方法**本就在清**非人行体，只是旧度量看不见（正向被低估）⇒ 直接是正向证据。
- 稀释/反号 ⇒ 存在**未被清**的非人行体残影 ⇒ 才需要改方法（在线非人行体检测）。

读法（与仓库判据同源）
----------------------
- 逐帧配对 Δ = exit − off（同帧集），逐 seed 取 **median + IQR**（**禁 mean 单独作结论**，
  DISCIPLINE「测量口径」1）；跨 seed 并陈。
- 两参照并陈：`freshvac_ghost_excess_depth_l1_cm`（最近 30 帧窗口腾空区）与
  `ghost_excess_depth_l1_cm`（全历史并集）。
- 同时报**支撑像素**（`mean_vacated_support_px` / per-frame `freshvac_support_px`）——
  证明"度量窗口确实变大了"，否则两列不可比。
- **跨掩码读数禁混引**（DISCIPLINE「比较前提」6）：本脚本只做**并陈对照**，不改任何历史判决。

用法
----
    python scripts/02_analysis/compare_mask_coverage.py [--mask-suffix _mover] [--out <md>]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "results" / "lifecycle_paper2"

SEQS = ["balloon", "balloon2", "mvnobox", "mvnobox2"]
# seq -> Bonn 目录名（掩码/数据目录）
SEQ_DIR = {"balloon": "rgbd_bonn_balloon", "balloon2": "rgbd_bonn_balloon2",
           "mvnobox": "rgbd_bonn_moving_nonobstructing_box",
           "mvnobox2": "rgbd_bonn_moving_nonobstructing_box2"}
KEYS = [("freshvac", "freshvac_ghost_excess_depth_l1_cm"),
        ("ghost_allhist", "ghost_excess_depth_l1_cm")]


def load_frames(tag: str) -> dict | None:
    p = ROOT / f"render_{tag}" / "render_metrics.json"
    if not p.is_file():
        return None
    d = json.load(open(p))
    return {f["frame"]: f for f in d.get("per_frame", [])}


def meta(tag: str) -> dict:
    p = ROOT / f"render_{tag}" / "render_metrics.json"
    if not p.is_file():
        return {}
    d = json.load(open(p))
    return {"mask_source": d.get("mask_source"), "mask_validity": d.get("mask_validity"),
            "n_frames": d.get("n_frames"),
            "mean_vacated_support_px": d.get("mean_vacated_support_px")}


def paired(a: dict, b: dict, key: str) -> list[float]:
    out = []
    for fr in sorted(set(a) & set(b)):
        va, vb = a[fr].get(key), b[fr].get(key)
        if va is None or vb is None:
            continue
        out.append(va - vb)
    return out


def med_iqr(xs):
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    med = statistics.median(s)
    q1 = s[max(0, int(round(0.25 * (n - 1))))] if n > 1 else s[0]
    q3 = s[min(n - 1, int(round(0.75 * (n - 1))))] if n > 1 else s[0]
    return med, q1, q3, n


def vac_support(frames: dict | None, key_suffix="freshvac_support_px"):
    if not frames:
        return None
    xs = [f[key_suffix] for f in frames.values() if f.get(key_suffix) is not None]
    return int(statistics.median(xs)) if xs else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mask-suffix", default="_mover", help="并陈掩码后缀（默认 _mover vs _canon）")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    lines = []
    lines.append(f"# 掩码覆盖并陈：canonical(`_canon`, 人) vs `{args.mask_suffix}`（人+非人行体）\n")
    lines.append("逐帧配对 Δ = exit − off（同帧集），median [IQR] (n)；**负 = exit 改善**。")
    lines.append("支撑列 = `freshvac_support_px` 中位（证明度量窗口是否真变大）。\n")
    lines.append("| 序列 | seed | 掩码 | Δ freshvac | Δ ghost(全历史) | freshvac 支撑 px |")
    lines.append("|---|---|---|---|---|---|")

    summary = {}
    for seq in SEQS:
        for seed in (0, 1, 2):
            row = {}
            for label, suff in (("canon", "_canon"), (args.mask_suffix.strip("_"), args.mask_suffix)):
                off = load_frames(f"L3_{seq}_off_s{seed}{suff}")
                ex = load_frames(f"L3_{seq}_exit_s{seed}{suff}")
                if off is None or ex is None:
                    lines.append(f"| {seq} | s{seed} | {label} | 缺工件 | — | — |")
                    row[label] = None
                    continue
                cells = []
                vals = {}
                for klabel, k in KEYS:
                    r = med_iqr(paired(ex, off, k))
                    vals[klabel] = r[0] if r else None
                    cells.append(f"**{r[0]:+.2f}** [{r[1]:+.2f},{r[2]:+.2f}] (n={r[3]})" if r else "—")
                sup = vac_support(ex)
                row[label] = vals
                lines.append(f"| {seq} | s{seed} | {label} | {cells[0]} | {cells[1]} | {sup} |")
            summary[f"{seq}_s{seed}"] = row

    # 跨 seed 并陈（median-of-medians，仅描述性）
    lines.append("\n## 跨 seed 汇总（逐 seed median 的 median；描述性，非判据）\n")
    lines.append("| 序列 | 掩码 | freshvac mom | ghost mom |")
    lines.append("|---|---|---|---|")
    for seq in SEQS:
        for label in ("canon", args.mask_suffix.strip("_")):
            fv = [summary[f"{seq}_s{s}"][label]["freshvac"] for s in (0, 1, 2)
                  if summary[f"{seq}_s{s}"][label]]
            gh = [summary[f"{seq}_s{s}"][label]["ghost_allhist"] for s in (0, 1, 2)
                  if summary[f"{seq}_s{s}"][label]]
            if not fv:
                continue
            lines.append(f"| {seq} | {label} | {statistics.median(fv):+.3f} | "
                         f"{statistics.median(gh):+.3f} |")
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text)
        print(f"written {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
