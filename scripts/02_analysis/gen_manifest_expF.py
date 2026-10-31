#!/usr/bin/env python
"""gen_manifest_expF.py — regenerate manifest_f_sensitivity.json from raw outputs.

Reads tracking_raw.csv (col 8 full-frame ate_rmse_cm, col 14 keyframe) for
baseline / gate0.30 / gate0.38 / gate0.45 across the 7 Bonn sequences and
seeds 0..2, and writes the manifest JSON. Deterministic given the same results
tree AND the same --date/--verdict.

gate0.38 = r32_regate038_* (the rebaselined arm, rerun on post-jacobian-fix
code; see evidence/prereg_f_rebase.md). The original r29_framegate column ran
on pre-fix code and was declared void (joint_correct/README.md 2.5c); it is
read only under --include-void-old-arm and lands in a "void_arm" provenance
block that consumers must not cite.

--date and --verdict are REQUIRED: they used to be hardcoded, so re-running
this script after a rebaseline silently produced "new numbers + stale
conclusion". There is deliberately no default verdict.

Usage:
  python scripts/02_analysis/gen_manifest_expF.py \
      --date 2026-09-15 --verdict "<one-line verdict, must match verdict_f_sensitivity.md>"
"""
import argparse
import csv
import json
from pathlib import Path

SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2"]
ARMS = {
    "baseline": "r33_rebase_baseline_{s}_seed{k}",
    "gate0.30": "r30_conf030_{s}_seed{k}",
    "gate0.38": "r32_regate038_{s}_seed{k}",
    "gate0.45": "r30_conf045_{s}_seed{k}",
}
OLD_ARM = ("gate0.38_old", "r29_framegate_{s}_seed{k}")
COL_FULL = 7
COL_KF = 13
ROOT = Path("results/paper2_fulltable")

_ap = argparse.ArgumentParser()
_ap.add_argument("--date", required=True,
                 help="manifest date (no default: avoids stale dates)")
_ap.add_argument("--verdict", required=True,
                 help="one-line verdict; must match verdict_f_sensitivity.md")
_ap.add_argument("--include-void-old-arm", action="store_true",
                 help="also emit the void r29 column into arms[gate0.38_old]")
args = _ap.parse_args()
OLD_ARM_INCLUDED = args.include_void_old_arm
if OLD_ARM_INCLUDED:
    ARMS[OLD_ARM[0]] = OLD_ARM[1]


def read_ate(dirname):
    p = ROOT / dirname / "tables" / "tracking_raw.csv"
    if not p.exists():
        return None
    rows = list(csv.reader(open(p)))
    if len(rows) < 2:
        return None
    try:
        return float(rows[-1][COL_FULL]), float(rows[-1][COL_KF])
    except (ValueError, IndexError):
        return None


out = {}
n_runs = 0
n_void = 0
for arm, pat in ARMS.items():
    out[arm] = {}
    is_void = arm == OLD_ARM[0]
    for s in SEQS:
        per = []
        for k in (0, 1, 2):
            r = read_ate(pat.format(s=s, k=k))
            if r:
                per.append({"seed": k, "full_cm": round(r[0], 4),
                            "kf_cm": round(r[1], 4)})
                if is_void:
                    n_void += 1
                else:
                    n_runs += 1
        if per:
            out[arm][s] = {
                "per_seed": per,
                "mean_full_cm": round(sum(p["full_cm"] for p in per) / len(per), 4),
            }

doc = {
    "experiment": "expF_threshold_sensitivity",
    "date": args.date,
    "criterion": "K8: gate gain independent of exact threshold",
    "verdict": args.verdict,
    "ate_column": "ate_rmse_cm (col8, full-frame)",
    "seeds": "n=3 for all arms",
    "runs_rc0": n_runs,
    "arms": out,
}
if OLD_ARM_INCLUDED:
    doc["void_runs"] = n_void
    doc["void_arm"] = {
        "name": "gate0.38_old(r29_framegate)",
        "reason": ("ran 2026-09-07, before the SWBA jacobian fixes "
                   "a21e0773/1150fb25 (2026-09-09); numbers were declared void "
                   "in archive/closed_families/joint_correct/results/README.md 2.5c "
                   "(族 2026-10-10 归档). Kept for provenance only — do not cite."),
        "rebased_to": "gate0.38 (r32_regate038, prereg_f_rebase.md)",
    }
with open(ROOT / "evidence" / "manifest_f_sensitivity.json", "w") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
print(f"written manifest_f_sensitivity.json  runs={n_runs}")
