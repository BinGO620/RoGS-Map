#!/usr/bin/env python
"""gen_manifest_r31.py — regenerate manifest_r31.json from raw outputs.

Reads tracking_raw.csv (col 8 full-frame ate_rmse_cm, col 14 keyframe) for the
r31_selfcheck_{0p5,1,2} arms across the 7 Bonn sequences and seeds 0..1, plus
the SWBA gate two-state counts from each consolelog. Deterministic: re-running
on the same results tree reproduces the same file.

Gate counting口径 (see NOTES.md 踩坑 2026-09-15, P22): Log() runs through rich
Console, which silently strips "[..]" markup, so the "[rel-gate skip]" /
"[gate-skip]" markers never reach the log. Count the surviving substrings:
  applied = "edges free="            (SWBA correction written back)
  skipped = "correction not applied" (self-check gate rejected the correction)
The literal token `applied` must NOT be used: it also matches inside
"correction not applied" and the LoopClosure line "applied to N KFs", so it
would return >0 even for a 100%-skip run.
"""
import csv
import json
import re
from pathlib import Path

SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2"]
ARMS = ["r31_selfcheck_0p5", "r31_selfcheck_1", "r31_selfcheck_2"]
EASY = ["crowd2", "crowd3", "balloon"]
COL_FULL, COL_KF = 7, 13
ROOT = Path("results/paper2_fulltable")

RE_EDGES = re.compile(r"edges free=")
RE_SKIP = re.compile(r"correction not applied")


def read_ate(tag):
    p = ROOT / tag / "tables" / "tracking_raw.csv"
    if not p.exists():
        return None
    rows = list(csv.reader(open(p)))
    if len(rows) < 2:
        return None
    try:
        return float(rows[-1][COL_FULL]), float(rows[-1][COL_KF])
    except (ValueError, IndexError):
        return None


def gate_counts(tag):
    p = ROOT / f"{tag}.consolelog"
    if not p.exists():
        return None
    t = open(p, errors="replace").read()
    return len(RE_EDGES.findall(t)), len(RE_SKIP.findall(t))


def mean(xs):
    return round(sum(xs) / len(xs), 4) if xs else None


runs = {}
n_runs = 0
for arm in ARMS:
    runs[arm] = {}
    for s in SEQS:
        per = []
        for k in (0, 1):
            tag = f"{arm}_{s}_seed{k}"
            ate = read_ate(tag)
            gc = gate_counts(tag)
            if ate is None:
                continue
            rec = {"seed": k, "full_cm": round(ate[0], 4),
                   "kf_cm": round(ate[1], 4)}
            if gc:
                rec["applied"], rec["skipped"] = gc
                rec["skip_pct"] = round(100.0 * gc[1] / (gc[0] + gc[1]), 1)
            per.append(rec)
            n_runs += 1
        if per:
            runs[arm][s] = {
                "per_seed": per,
                "mean_full_cm": mean([p["full_cm"] for p in per]),
                "applied": sum(p.get("applied", 0) for p in per),
                "skipped": sum(p.get("skipped", 0) for p in per),
            }

# r29_framegate reference (3-seed mean, col 8) — NOTE: measured on the
# 2026-09-07 tree, i.e. BEFORE the 2026-09-09 SWBA Jacobian fixes
# (a21e0773 / 1150fb25). Cross-version, recorded here for traceability only.
ref = {}
for s in SEQS:
    v = [read_ate(f"r29_framegate_{s}_seed{k}") for k in (0, 1, 2)]
    v = [x[0] for x in v if x]
    ref[s] = {"mean_full_cm": mean(v), "per_seed": v}

verdict = {}
for arm in ARMS:
    m = {s: runs[arm].get(s, {}).get("mean_full_cm") for s in SEQS}
    main = {s: (m[s] is not None and m[s] <= ref[s]["mean_full_cm"] * 1.03)
            for s in EASY}
    sub = m["person_tracking"] is not None and m["person_tracking"] <= 8.2
    ap = sum(runs[arm][s]["applied"] for s in SEQS)
    sk = sum(runs[arm][s]["skipped"] for s in SEQS)
    verdict[arm] = {
        "MAIN": "PASS" if all(main.values()) else "FAIL",
        "MAIN_detail": {s: (m[s], ref[s]["mean_full_cm"]) for s in EASY},
        "SUB": "PASS" if sub else "FAIL",
        "SUB_value": m["person_tracking"],
        "MECH": "PASS" if (ap > 0 and sk > 0) else "FAIL",
        "MECH_counts": {"applied": ap, "skipped": sk},
        "arm_skip_pct": round(100.0 * sk / (ap + sk), 1),
    }

doc = {
    "experiment": "r31_selfcheck_gate",
    "date": "2026-09-15",
    "prereg": "results/paper2_fulltable/evidence/prereg_r31_selfcheck.md",
    "question": ("H1: is SWBA rel_improve (self-check) a sequence-independent "
                 "substitute for the static_conf absolute threshold?"),
    "verdict": ("NOT ESTABLISHED — no arm passes all three gates; "
                "SUB fails at every threshold; gate skip-rate is flat across "
                "sequence difficulty. Excluded direction."),
    "ate_column": "ate_rmse_cm (col8, full-frame)",
    "seeds": "n=2 (seed 0,1) — screening discipline",
    "runs_rc0": n_runs,
    "batch": "remote jiangwenheng 3090x2, r31.done 42/42 finished rc=0",
    "reference_note": ("r29_framegate reference is the 2026-09-07 run tree "
                       "(pre-Jacobian-fix); R31 ran 2026-09-15. Comparison is "
                       "cross-version — see verdict_r31.md section 5."),
    "arms": runs,
    "reference_r29_framegate": ref,
    "criteria_verdict": verdict,
}
with open(ROOT / "evidence" / "manifest_r31.json", "w") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
print(f"written manifest_r31.json  runs={n_runs}")
for arm in ARMS:
    v = verdict[arm]
    print(f"  {arm:20s} MAIN={v['MAIN']} SUB={v['SUB']} "
          f"MECH={v['MECH']} skip={v['arm_skip_pct']}%")
