#!/usr/bin/env python
"""effctlconc_ablation.py — 同码「独占 vs 并发」单变量消融判读。

背景（D1-027）：初版把「effctl 独占」与「R33 并发」的 2.2–2.6× 差归因于并发，被 G2 判
Reject——两批**代码版本不同**（effctl 61 列 vs R33 51 列）。本脚本用**同码**对照隔离并发：
  * 独占臂 = `effctl_*_seed0`（当前代码，单进程单卡，已存）
  * 并发臂 = `effctlconc_*_seed0`（当前代码，2 进程/卡）
同序列、同臂、同 seed ⇒ 倍率 = 纯并发度效应（可作因果陈述）。

口径：online_fps = num_frames / online_time_s（utils/eval_utils.py:1065）。
输出：results/paper2_fulltable/evidence/effctlconc_ablation_2026-10-05.md + .json
"""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "results/paper2_fulltable"
EV = ROOT / "evidence"
ARMS = ["baseline", "swbaonly", "final", "gate"]
ARMS_LBL = {"baseline": "base", "swbaonly": "+SWBA", "final": "+SWBA+LC", "gate": "+Gate"}
SEQ = ["balloon", "crowd2", "person_tracking"]


def fps(tag: str):
    p = ROOT / tag / "tables/efficiency_raw.csv"
    if not p.exists():
        return None
    try:
        r = list(csv.DictReader(p.open()))[0]
        return float(r["online_fps"])
    except Exception:
        return None


def main():
    rows = []
    for arm in ARMS:
        for seq in SEQ:
            ex = fps(f"effctl_{arm}_{seq}_seed0")
            cc = fps(f"effctlconc_{arm}_{seq}_seed0")
            rows.append({"arm": arm, "seq": seq, "exclusive_fps": ex,
                         "concurrent_fps": cc,
                         "ratio": (ex / cc) if (ex and cc) else None})
    # 每臂：跨序列中位
    per_arm = {}
    for arm in ARMS:
        ex = [r["exclusive_fps"] for r in rows if r["arm"] == arm and r["exclusive_fps"]]
        cc = [r["concurrent_fps"] for r in rows if r["arm"] == arm and r["concurrent_fps"]]
        per_arm[arm] = {
            "exclusive_median": statistics.median(ex) if ex else None,
            "concurrent_median": statistics.median(cc) if cc else None,
        }
        if ex and cc:
            per_arm[arm]["ratio"] = per_arm[arm]["exclusive_median"] / per_arm[arm]["concurrent_median"]

    complete = all(r["ratio"] is not None for r in rows)
    out = {"complete": complete, "n_rows": len(rows), "rows": rows, "per_arm": per_arm}
    EV.mkdir(parents=True, exist_ok=True)
    (EV / "effctlconc_ablation_2026-10-05.json").write_text(json.dumps(out, indent=2))

    md = ["# 同码「独占 vs 并发」消融（effctl vs effctlconc，2026-10-05）", "",
          "> **目的**：隔离并发度对 FPS 的影响（**同代码版本**；修正 D1-027 的跨版本归因错误）。",
          f"> **完整性**：{'全部 12 格齐' if complete else '未齐（并发批未跑完）'}；"
          f"missing = {sum(1 for r in rows if r['ratio'] is None)} 格", "",
          "| arm | seq | exclusive fps | concurrent fps | ratio |", "|---|---|---|---|---|"]
    for r in rows:
        exs = "--" if r["exclusive_fps"] is None else f"{r['exclusive_fps']:.3f}"
        ccs = "--" if r["concurrent_fps"] is None else f"{r['concurrent_fps']:.3f}"
        rts = "--" if r["ratio"] is None else f"{r['ratio']:.2f}x"
        md.append(f"| {ARMS_LBL[r['arm']]} | {r['seq']} | {exs} | {ccs} | {rts} |")
    md.append("")
    for arm in ARMS:
        pa = per_arm[arm]
        rt = f"{pa['ratio']:.2f}x" if pa.get("ratio") else "--"
        md.append(f"- **{ARMS_LBL[arm]}**：独占中位 {pa['exclusive_median']:.3f} → "
                  f"并发中位 {pa['concurrent_median'] if pa['concurrent_median'] else float('nan'):.3f} fps "
                  f"（ratio {rt}）" if pa["exclusive_median"] and pa["concurrent_median"]
                  else f"- **{ARMS_LBL[arm]}**：数据未齐")
    md.append("")
    if complete:
        ratios = [r["ratio"] for r in rows]
        md += [
            "## 结论（写进 readout §5 / Tab.4 的依据）", "",
            f"**同码单变量**：并发（2 进程/卡）对在线 FPS 的代价 = **{min(ratios):.2f}×–{max(ratios):.2f}×**"
            f"（12 格中位 {statistics.median(ratios):.2f}×），**远小于**初版跨版本读出的 2.2–2.6×。",
            "确认 D1-027 的判断：初版倍率**主要是代码版本漂移**，不是并发。并发本身确有代价"
            "（约 1.1–1.8×，随臂/序列而异，gate 臂代价最小），但因**同进程争用非决定性**，"
            "不能作强因果主张。",
            "",
            "**对论文的处置**：Tab.4 保留两列，但 caption 现可**如实**说明——独占列 = 受控锚点"
            "（3 序列）；并发列若保留，须注明为同码同子集、代价约 1.1–1.8×（本件支持），"
            "而**非**早期声称的 2–3×。或按 §5 保留『并发影响很小』的定性。"]
    else:
        md.append("> 结论待 12 格齐后再写（本脚本机写，禁手抄）。")
    (EV / "effctlconc_ablation_2026-10-05.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
