#!/usr/bin/env python
"""gen_manifest_r33.py — 从原始 tracking_raw.csv 确定性重建 manifest_r33.json。

manifest_r33.json 是**当前** Tab.1/Tab.3（四臂同批）的单一事实源。
历史件 `manifest.json`（seed3_promotion，head f43788b8 / 2026-09-07）保留为
带日期的记录，其值已被本批取代，见其中的 `superseded_r29_framegate` 块。

用法:
  python scripts/02_analysis/gen_manifest_r33.py --date 2026-09-16 --verdict "<一行结论>"
"""
import argparse
import csv
import json
import statistics
from pathlib import Path

SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2"]
SEEDS = [0, 1, 2]
COL_FULL, COL_KF = 7, 13
ROOT = Path("results/paper2_fulltable")
ARMS = {"baseline": "r33_rebase_baseline_{s}_seed{k}",
        "swbaonly": "r33_rebase_swbaonly_{s}_seed{k}",
        "final": "r33_rebase_final_{s}_seed{k}",
        "gate": "r33_rebase_gate_{s}_seed{k}"}

_ap = argparse.ArgumentParser()
_ap.add_argument("--date", required=True)
_ap.add_argument("--verdict", required=True)
args = _ap.parse_args()


def read(d):
    p = ROOT / d / "tables" / "tracking_raw.csv"
    if not p.exists():
        return None
    rows = list(csv.reader(open(p)))
    try:
        return float(rows[-1][COL_FULL]), float(rows[-1][COL_KF])
    except Exception:
        return None


out, n = {}, 0
for arm, pat in ARMS.items():
    out[arm] = {}
    for s in SEQS:
        per = []
        for k in SEEDS:
            r = read(pat.format(s=s, k=k))
            if r:
                per.append({"seed": k, "full_cm": round(r[0], 4), "kf_cm": round(r[1], 4)})
                n += 1
        if per:
            full = [p["full_cm"] for p in per]
            out[arm][s] = {
                "per_seed": per,
                "mean_full_cm": round(statistics.mean(full), 4),
                "sd_full_cm": round(statistics.stdev(full), 4) if len(full) > 1 else None,
                "mean_kf_cm": round(statistics.mean(p["kf_cm"] for p in per), 4),
            }

doc = {
    "experiment": "paper2_fulltable/rebase_r33",
    "date": args.date,
    "batch": "R33: 4 arms x 7 seq x 3 seed = 84 run, all rc=0 (2026-09-16 01:37 -> 15:31)",
    "arms_note": ("all four arms same batch, same code (current HEAD); supersedes the "
                  "seed3_promotion manifest.json whose baseline/final/gate columns were "
                  "run on 2026-09-06/07 code and a different batch"),
    "ate_column": "ate_rmse_cm (col8, full-frame); kf_cm = keyframe col14",
    "prereg": "evidence/prereg_rebase_arms.md",
    "verdict": args.verdict,
    "runs_rc0": n,
    "arms": out,
}
# 逐序列派生列（gate vs final / gate vs baseline）
deriv = {}
for s in SEQS:
    b = out["baseline"][s]["mean_full_cm"]
    f = out["final"][s]["mean_full_cm"]
    g = out["gate"][s]["mean_full_cm"]
    deriv[s] = {"gate_vs_final_pct": round(100 * (g - f) / f, 2),
                "gate_vs_baseline_pct": round(100 * (g - b) / b, 2)}
doc["derived"] = deriv
json.dump(doc, open(ROOT / "evidence" / "manifest_r33.json", "w"), indent=1, ensure_ascii=False)
open(ROOT / "evidence" / "manifest_r33.json", "a").write("\n")
print(f"written manifest_r33.json  runs={n}")
