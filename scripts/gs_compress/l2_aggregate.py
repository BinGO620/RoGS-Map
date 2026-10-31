#!/usr/bin/env python
"""l2_aggregate.py — 聚合 L2 主表批的 R-D 记录为论文表。

读 results/gs_compress/evidence/rd/L2_*_rd_table.json（每图一份），产出：
  * 每序列 × 每臂的 R-D 均值（跨 seed）；
  * 关键工作点（近无损 16/8/8/8/8、中等 10/6/6/6/6、激进 8/4/4/4/4）的
    ratio / PSNR / static / ghost 汇总；
  * Markdown + JSON。
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
RD = REPO / "results" / "gs_compress" / "evidence" / "rd"
WORKPOINTS = {
    "16,8,8,8,8": "near_lossless",
    "10,6,6,6,6": "mid",
    "8,4,4,4,4": "aggressive",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RD / "l2_summary"))
    args = ap.parse_args()

    rows = defaultdict(lambda: defaultdict(list))  # (seq,arm) -> wp -> [records]
    for f in sorted(RD.glob("L2_*_rd_table.json")):
        d = json.loads(f.read_text())
        m = re.match(r"L2_(.+)_(baseline|final)_s(\d+)", d["tag"])
        if not m:
            continue
        seq, arm, seed = m.group(1), m.group(2), int(m.group(3))
        for r in d["rows"]:
            if r.get("kind") == "baseline":
                continue
            bits = ",".join(map(str, r["bits"]))
            if bits in WORKPOINTS and r.get("render"):
                rows[(seq, arm)][WORKPOINTS[bits]].append(r)

    def agg(recs):
        return {
            "n": len(recs),
            "ratio_full": float(np.mean([r["ratio_full"] for r in recs])),
            "rate": float(np.mean([r["rate_bytes_per_prim"] for r in recs])),
            "psnr": float(np.mean([r["render"]["mean_psnr"] for r in recs])),
            "static_psnr": float(np.mean([r["render"]["mean_static_psnr"] for r in recs])),
            "ghost": float(np.mean([r["render"]["mean_ghost_excess_depth_l1_cm"] for r in recs])),
        }

    out = {}
    md = ["# L2 R-D 主表（baseline+final × Bonn 7 × 3 seed）", "",
          "## 近无损工作点 16/8/8/8/8", "",
          "| seq | arm | ratio | B/prim | PSNR | static | ghost |", "|---|---|---|---|---|---|---|"]
    for (seq, arm) in sorted(rows):
        wp = rows[(seq, arm)]
        out[f"{seq}_{arm}"] = {k: agg(v) for k, v in wp.items()}
        if "near_lossless" in wp:
            a = agg(wp["near_lossless"])
            md.append(f"| {seq} | {arm} | {a['ratio_full']:.2f}x | {a['rate']:.2f} | "
                      f"{a['psnr']:.3f} | {a['static_psnr']:.3f} | {a['ghost']:.3f} |")

    # 全局均值
    for wpname in ["near_lossless", "mid", "aggressive"]:
        allr = [agg(rows[k][wpname]) for k in rows if wpname in rows[k]]
        if allr:
            md.append("")
            md.append(f"**{wpname}** 全局：ratio {np.mean([x['ratio_full'] for x in allr]):.2f}x, "
                      f"PSNR {np.mean([x['psnr'] for x in allr]):.3f}, "
                      f"static {np.mean([x['static_psnr'] for x in allr]):.3f}, "
                      f"ghost {np.mean([x['ghost'] for x in allr]):.3f}")

    out_path = Path(args.out)
    out_path.with_suffix(".json").write_text(json.dumps(out, indent=2))
    out_path.with_suffix(".md").write_text("\n".join(md))
    print("\n".join(md))
    print(f"\nwrote {out_path}.json / .md  ({len(rows)} seq×arm groups)")


if __name__ == "__main__":
    main()
