#!/usr/bin/env python
"""probe_5seq_verdict.py — B-1 跨序列探针判读（prereg_dyn_probe_5seq_2026-10-05.md §3）。

读 results/embrace_dyn/evidence/dyn_probe_5seq_<seq>_results.json（每序列一份），
按 prereg §3 判据**逐序列独立判定**（禁全局均值一把过），输出：
  * 主表：逐序列 × 臂 的 bad 区 PSNR 增益 / dl1 比值 / 静态区 Δ / 全图 Δ / 成本 / 仪器比；
  * ①b 天花板是否过（≤0.70 且 ≥+2.0dB）；③ 无伤（±0.25）；④ 成本（≤50%）；⑤ 仪器（C−/P2 ≥1.15）；
  * k/5 汇总。

输出：results/paper2_fulltable/evidence/dyn_cost_5seq_2026-10-05.{md,json}
"""
from __future__ import annotations

import glob
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EV = REPO / "results/embrace_dyn/evidence"
OUT = REPO / "results/paper2_fulltable/evidence"

# prereg §3 阈值（先锁）
T_DL1_RATIO = 0.70
T_PSNR_GAIN = 2.0
T_STATIC = 0.25
T_COST = 0.50
T_INSTRUMENT = 1.15


def judge_one(armagg, n_static):
    """armagg = results['aggregate'][arm]（各臂 mean_* 字典）；n_static = meta[arm]['n_static']。"""
    P1, P2, C = armagg.get("P1"), armagg.get("P2"), armagg.get("C-")
    if not (P1 and P2 and C):
        return None
    dl1_ratio = P2["mean_dyn_bad_dl1_cm"] / P1["mean_dyn_bad_dl1_cm"]
    psnr_gain = P2["mean_dyn_bad_psnr"] - P1["mean_dyn_bad_psnr"]
    static_d = P2["mean_static_psnr"] - P1["mean_static_psnr"]
    full_d = P2["mean_full_psnr"] - P1["mean_full_psnr"]
    cost = P2["mean_n_dyn"] / max(1, n_static)
    instr = C["mean_dyn_dl1_cm"] / P2["mean_dyn_dl1_cm"]
    return {
        "bad_psnr_gain_db": psnr_gain,
        "bad_dl1_ratio": dl1_ratio,
        "static_delta_db": static_d,
        "full_delta_db": full_d,
        "instrument_ratio": instr,
        "n_dyn": P2["mean_n_dyn"],
        "n_dyn_frac": cost,
        "judge_ceiling": (dl1_ratio <= T_DL1_RATIO) and (psnr_gain >= T_PSNR_GAIN),
        "judge_noharm": (abs(static_d) <= T_STATIC) and (full_d >= -T_STATIC),
        "judge_cost": cost <= T_COST,
        "judge_instrument": instr >= T_INSTRUMENT,
    }


def main():
    rows = []
    for f in sorted(glob.glob(str(EV / "dyn_probe_5seq_*_results.json"))):
        seq = re.match(r"dyn_probe_5seq_(.+)_results", Path(f).stem).group(1)
        d = json.loads(Path(f).read_text())
        for arm, agg in d.get("aggregate", {}).items():
            j = judge_one(agg, d["meta"][arm].get("n_static"))
            if j:
                rows.append({"seq": seq, "arm": arm, **j, "mask": d["meta"][arm].get("mask_source"),
                             "n_static": d["meta"][arm].get("n_static")})

    k_ceil = sum(1 for r in rows if r["judge_ceiling"])
    k_noharm = sum(1 for r in rows if r["judge_noharm"])
    k_cost = sum(1 for r in rows if r["judge_cost"])
    k_instr = sum(1 for r in rows if r["judge_instrument"])
    out = {"thresholds": {"dl1_ratio": T_DL1_RATIO, "psnr_gain": T_PSNR_GAIN, "static": T_STATIC,
                          "cost": T_COST, "instrument": T_INSTRUMENT},
           "k_ceiling": k_ceil, "k_noharm": k_noharm, "k_cost": k_cost, "k_instrument": k_instr,
           "n_rows": len(rows), "rows": rows}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dyn_cost_5seq_2026-10-05.json").write_text(json.dumps(out, indent=2, default=str))

    md = ["# 反动态代价：跨序列探针判读（B-1，2026-10-05）", "",
          "> **判据**（prereg_dyn_probe_5seq §3，先锁，逐序列独立判定）："
          f"①b 天花板 bad-dl1 比 ≤{T_DL1_RATIO} 且 bad-PSNR 差 ≥+{T_PSNR_GAIN}dB；"
          f"③ 无伤 |Δstatic|≤{T_STATIC}；⑤ 仪器 C−/P2 ≥{T_INSTRUMENT}。",
          f"> **读出**：天花板 **{k_ceil}/{len(rows)}**；无伤 **{k_noharm}/{len(rows)}**；成本 **{k_cost}/{len(rows)}**；仪器 **{k_instr}/{len(rows)}**。", "",
          "| 序列 | 臂 | bad PSNR 增益(dB) | bad dl1 比 | 静态Δ(dB) | 全图Δ(dB) | 仪器比 | 成本 | ①b | ③ | ④ | ⑤ |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['seq']} | {r['arm']} | +{r['bad_psnr_gain_db']:.2f} | {r['bad_dl1_ratio']:.3f} | "
                  f"{r['static_delta_db']:+.3f} | {r['full_delta_db']:+.2f} | {r['instrument_ratio']:.2f} | "
                  f"{r['n_dyn_frac']*100:.1f}% | "
                  f"{'✓' if r['judge_ceiling'] else '✗'} | {'✓' if r['judge_noharm'] else '✗'} | "
                  f"{'✓' if r['judge_cost'] else '✗'} | {'✓' if r['judge_instrument'] else '✗'} |")
    md += ["", "**汇总**：每序列独立判定（不做全局均值）。结论按 k/N 记入 verdict。", ""]
    (OUT / "dyn_cost_5seq_2026-10-05.md").write_text("\n".join(md))
    print("\n".join(md))
    print(f"\nwrote {OUT}/dyn_cost_5seq_2026-10-05.md/.json")


if __name__ == "__main__":
    main()
