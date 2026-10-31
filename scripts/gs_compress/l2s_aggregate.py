#!/usr/bin/env python
"""l2s_aggregate.py — 聚合「均匀量化+体素合并」批为 R-D 表（与 L2 主表同口径）。

读 results/gs_compress/evidence/rd/L2S_*_b*_ded20mm.json（每图每点一份），
产出 values 与既有 l2_summary.json 同结构（键 = seq_arm，含 near_lossless/mid/aggressive），
便于 paper2_codec_tables.py 直接并入 R-D 主表。

输出：evidence/rd/l2s_summary.json + .md
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
RD = REPO / "results/gs_compress/evidence/rd"
WP = {"16,8,8,8,8": "near_lossless", "10,6,6,6,6": "mid", "8,4,4,4,4": "aggressive"}


def main():
    rows = defaultdict(lambda: defaultdict(list))
    n_files = 0
    for f in sorted(RD.glob("L2S_*_b*_ded20mm.json")):
        d = json.loads(f.read_text())
        # 文件名形如 L2S_balloon_baseline_s0_b16-8-8-8-8_ded20mm.json
        # （d['tag'] 只到 seed，不含位宽；位宽/位点在文件名里）
        m = re.match(r"L2S_(.+?)_(baseline|final)_s(\d+)_b([0-9-]+)_ded20mm", f.stem)
        if not m:
            continue
        seq, arm, bits = m.group(1), m.group(2), m.group(4)
        bits_csv = bits.replace("-", ",")
        if bits_csv not in WP:
            continue
        if not d.get("render"):
            continue
        n_files += 1
        rows[(seq, arm)][WP[bits_csv]].append(d)

    out = {}
    for (seq, arm), wp in rows.items():
        out[f"{seq}_{arm}"] = {}
        for name, recs in wp.items():
            out[f"{seq}_{arm}"][name] = {
                "n": len(recs),
                "ratio_full": float(np.mean([r["ratio_full"] for r in recs])),
                "rate": float(np.mean([r["rate_bytes_per_prim"] for r in recs])),
                "psnr": float(np.mean([r["render"]["mean_psnr"] for r in recs])),
                "static_psnr": float(np.mean([r["render"]["mean_static_psnr"] for r in recs])),
                "ghost": float(np.mean([r["render"]["mean_ghost_excess_depth_l1_cm"] for r in recs])),
                "dropped_frac": float(np.mean([r["prune"]["dropped"] / max(1, r["n_orig"]) for r in recs])),
            }
    (RD / "l2s_summary.json").write_text(json.dumps(out, indent=2))

    md = ["# L2S R-D 主表（均匀量化 + 体素合并 2cm；与 L2 同批同帧）", "",
          "| 工作点 | 全局 ratio | PSNR | static | ghost | 丢基元比 |", "|---|---|---|---|---|---|"]
    for name in ["near_lossless", "mid", "aggressive"]:
        recs = [v[name] for v in out.values() if name in v]
        if recs:
            md.append(f"| {name} | {np.mean([r['ratio_full'] for r in recs]):.2f}x | "
                      f"{np.mean([r['psnr'] for r in recs]):.3f} | "
                      f"{np.mean([r['static_psnr'] for r in recs]):.3f} | "
                      f"{np.mean([r['ghost'] for r in recs]):.3f} | "
                      f"{np.mean([r['dropped_frac'] for r in recs])*100:.1f}% |")
    md.append(f"\n（{n_files} 个点记录，{len(out)} 个 seq×arm 组）")
    (RD / "l2s_summary.md").write_text("\n".join(md))
    print("\n".join(md))
    print(f"wrote {RD}/l2s_summary.json / .md")


if __name__ == "__main__":
    main()
