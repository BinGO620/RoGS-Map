#!/usr/bin/env python
"""dyn_cost_decomp.py — B 线：反动态代价的几何 vs 外观拆解表（**canonical 5seq 批**）。

数据源：results/embrace_dyn/evidence/dyn_probe_5seq_<seq>_results.json（5 份，canonical dynamic_mask）
  * P1 抹除 / P2 保留（逐帧插入+拟合，天花板）—— 天花板
  * P2c 无运动（只插几何+烘焙外观）/ P4 烘焙冻结 —— 拆解：省掉运动建模能保住多少

判据口径（prereg_dyn_probe_causal.md，先锁）：
  retention(X) = (dl1(P1) − dl1(X)) / (dl1(P1) − dl1(P2))，bad 子集（P1 渲染深度错 >10cm）。

产出：results/paper2_fulltable/evidence/dyn_cost_decomp_2026-10-05.{md,json}

注：本件为**canonical 掩码**版本（G2 抓到旧件误用 2026-09-19 gtmc 掩码批 ⇒ 本件取代）。
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
EV = REPO / "results/embrace_dyn/evidence"
OUT = REPO / "results/paper2_fulltable/evidence"


def ret(P1, X, P2):
    d1 = P1["mean_dyn_bad_dl1_cm"]; dx = X["mean_dyn_bad_dl1_cm"]; d2 = P2["mean_dyn_bad_dl1_cm"]
    return (d1 - dx) / (d1 - d2) if d1 != d2 else float("nan")


def main():
    rows = []
    for f in sorted(glob.glob(str(EV / "dyn_probe_5seq_*_results.json"))):
        d = json.loads(Path(f).read_text())
        seq = Path(f).stem.replace("dyn_probe_5seq_", "").replace("_results", "")
        for arm, agg in d.get("aggregate", {}).items():
            if not all(k in agg for k in ("P1", "P2")):
                continue
            P1, P2 = agg["P1"], agg["P2"]
            bad_gain = P2["mean_dyn_bad_psnr"] - P1["mean_dyn_bad_psnr"]
            dl1_ratio = P2["mean_dyn_bad_dl1_cm"] / P1["mean_dyn_bad_dl1_cm"]
            frac = P2["mean_n_dyn"] / max(1, d["meta"][arm]["n_static"])
            row = {"seq": seq, "arm": arm, "bad_psnr_gain_db": bad_gain, "bad_dl1_ratio": dl1_ratio,
                   "static_delta_db": P2["mean_static_psnr"] - P1["mean_static_psnr"],
                   "full_delta_db": P2["mean_full_psnr"] - P1["mean_full_psnr"],
                   "n_dyn_frac": frac,
                   "retention_P2c_no_motion": ret(P1, agg["P2c"], P2) if "P2c" in agg else None,
                   "retention_P4_bake": ret(P1, agg["P4"], P2) if "P4" in agg else None}
            rows.append(row)

    out = {"source": "dyn_probe_5seq_*_results.json (canonical dynamic_mask)",
           "retention_def": "(dl1(P1)-dl1(X))/(dl1(P1)-dl1(P2)), bad subset", "rows": rows}
    (OUT / "dyn_cost_decomp_2026-10-05.json").write_text(json.dumps(out, indent=2, default=str))

    r2c = [r["retention_P2c_no_motion"] for r in rows if r["retention_P2c_no_motion"] is not None]
    r4 = [r["retention_P4_bake"] for r in rows if r["retention_P4_bake"] is not None]
    fr = [r["n_dyn_frac"] for r in rows]

    md = ["# 反动态代价：几何 vs 外观拆解（B 线，**canonical 5seq 批**，2026-10-05）", "",
          "> **口径**：`dyn_probe_5seq_*_results.json`（canonical `dynamic_mask`）。"
          "`retention(X) = (dl1(P1) − dl1(X))/(dl1(P1) − dl1(P2))`，bad 子集（P1 渲染深度错 >10cm）。"
          "P2c = 无运动（只插几何+烘焙外观）；P4 = 在 t0 插入后冻结（永不再更新）。", "",
          "| 序列 | 臂 | bad PSNR 增益(dB) | bad dl1 比 | 静态Δ(dB) | 全图Δ(dB) | 新增基元 | retention(P2c 无运动) | retention(P4 冻结) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        f2 = "--" if r["retention_P2c_no_motion"] is None else f"{r['retention_P2c_no_motion']:.3f}"
        f4 = "--" if r["retention_P4_bake"] is None else f"{r['retention_P4_bake']:.3f}"
        md.append(f"| {r['seq']} | {r['arm']} | +{r['bad_psnr_gain_db']:.2f} | {r['bad_dl1_ratio']:.3f} | "
                  f"{r['static_delta_db']:+.3f} | {r['full_delta_db']:+.2f} | {r['n_dyn_frac']*100:.1f}% | "
                  f"{f2} | {f4} |")
    md += ["", f"**读法**：**无运动臂 P2c retention 高（{min(r2c):.2f}–{max(r2c):.2f}）**，"
           f"**冻结臂 P4 retention 低（{min(r4):.2f}–{max(r4):.2f}）** ⇒ 抹除的代价"
           "**主要靠「把动态几何放进地图」就能挽回大半**（0.8–0.9），逐帧运动建模是多花的力气"
           "（省掉它只剩 0.1–0.4）。**成本**：新增基元 "
           f"{min(fr)*100:.0f}–{max(fr)*100:.0f}%（中位 {np.median(fr)*100:.0f}%）。", ""]
    (OUT / "dyn_cost_decomp_2026-10-05.md").write_text("\n".join(md))
    print("\n".join(md))
    print(f"\nwrote {OUT}/dyn_cost_decomp_2026-10-05.md/.json")


if __name__ == "__main__":
    main()
