#!/usr/bin/env python
"""analyze_r31.py — R31 self-checking SWBA gate analysis.

Reads the r31_selfcheck_{0p5,1,2} runs and, for each (arm, seq, seed):
  - full-frame ATE (tracking_raw.csv col 8) and keyframe (col 14)
  - SWBA gate two-state counts from the consolelog:
      applied  = lines matching "edges free="
      skipped  = lines matching "correction not applied"
  - rel_improve distribution of skipped vs applied events

NOTE: Log() uses rich Console, which strips [..] markup, so the code's
"[gate-skip]" / "[rel-gate skip]" markers never reach the log. Count the
surviving substrings instead (see NOTES 2026-09-15 pitfall).

Pre-registered criteria (evidence/prereg_r31_selfcheck.md):
  MAIN  (easy-seq no-regression): crowd2/crowd3/balloon ATE <= r29_framegate +3%
  SUB   (pt1 gain retained):      person_tracking ATE <= 8.2cm
  MECH  (two-state coexistence):  skipped > 0 AND applied > 0
"""
import argparse
import csv
import re
from pathlib import Path

SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2"]
ARMS = ["r31_selfcheck_0p5", "r31_selfcheck_1", "r31_selfcheck_2"]
EASY = ["crowd2", "crowd3", "balloon"]
COL_FULL, COL_KF = 7, 13

RE_SKIP_RI = re.compile(r"rel_improve=([\d.]+)%")
RE_APPLY_RI = re.compile(r"\|dc\| ([\d.]+)%")
RE_EDGES = re.compile(r"edges free=")
RE_SKIP = re.compile(r"correction not applied")

ROOT = Path("results/paper2_fulltable")


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


def gate_counts(tag):
    """(applied, skipped, skipped_ri[], applied_ri[]) from the consolelog."""
    p = ROOT / f"{tag}.consolelog"
    if not p.exists():
        return None
    ap = sk = 0
    sk_ri, ap_ri = [], []
    for line in open(p, errors="replace"):
        if RE_EDGES.search(line):
            ap += 1
            m = RE_APPLY_RI.search(line)
            if m:
                ap_ri.append(float(m.group(1)))
        elif RE_SKIP.search(line):
            sk += 1
            m = RE_SKIP_RI.search(line)
            if m:
                sk_ri.append(float(m.group(1)))
    return ap, sk, sk_ri, ap_ri


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def fmt(v, nd=3):
    return "  --  " if v is None else f"{v:.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="results/paper2_fulltable")
    a = ap.parse_args()
    global ROOT
    ROOT = Path(a.root)

    print("== per-run ATE (full-frame cm) + gate two-state ==")
    print(f"{'arm':18s} {'seq':16s} {'seed':>4s} {'full':>7s} {'kf':>7s} "
          f"{'apply':>6s} {'skip':>5s} {'skip%':>6s}")
    per = {}
    for arm in ARMS:
        for s in SEQS:
            for k in (0, 1):
                tag = f"{arm}_{s}_seed{k}"
                ate = read_ate(tag)
                gc = gate_counts(tag)
                if ate is None and gc is None:
                    continue
                full = ate[0] if ate else None
                kf = ate[1] if ate else None
                if gc:
                    apn, skn, _, _ = gc
                    tot = apn + skn
                    pct = f"{100.0*skn/tot:.0f}%" if tot else "--"
                else:
                    apn = skn = 0
                    pct = "--"
                print(f"{arm:18s} {s:16s} {k:>4d} {fmt(full):>7s} {fmt(kf):>7s} "
                      f"{apn:>6d} {skn:>5d} {pct:>6s}")
                per.setdefault((arm, s), []).append((full, apn, skn))
            print()

    print("== arm means (n=2) ==")
    print(f"{'arm':18s} {'seq':16s} {'full_mean':>9s} {'skip%':>6s}")
    means = {}
    for arm in ARMS:
        for s in SEQS:
            rows = per.get((arm, s), [])
            fulls = [r[0] for r in rows if r[0] is not None]
            apn = sum(r[1] for r in rows)
            skn = sum(r[2] for r in rows)
            m = mean(fulls)
            means[(arm, s)] = m
            tot = apn + skn
            pct = f"{100.0*skn/tot:.0f}%" if tot else "--"
            print(f"{arm:18s} {s:16s} {fmt(m):>9s} {pct:>6s}")
        print()

    # ---- pre-registered verdicts ----
    print("== pre-registered criteria ==")
    # r29 reference = 3-seed mean (matches verdict_f's gate0.38 column)
    ref = {}
    for s in SEQS:
        vals = [read_ate(f"r29_framegate_{s}_seed{k}") for k in (0, 1, 2)]
        vals = [v[0] for v in vals if v]
        ref[s] = mean(vals)

    for arm in ARMS:
        print(f"\n--- {arm} ---")
        # MAIN: easy seqs <= r29 + 3%
        main_ok = True
        for s in EASY:
            m = means.get((arm, s))
            r = ref[s]
            if m is None or r is None:
                print(f"  MAIN {s}: missing data")
                main_ok = False
                continue
            ok = m <= r * 1.03
            main_ok &= ok
            print(f"  MAIN {s}: {m:.3f} vs r29 {r:.3f} (+3%={r*1.03:.3f}) "
                  f"-> {'PASS' if ok else 'FAIL'}")
        # SUB: pt1 <= 8.2
        pt = means.get((arm, "person_tracking"))
        sub_ok = pt is not None and pt <= 8.2
        print(f"  SUB  person_tracking: {fmt(pt)} vs 8.2 -> "
              f"{'PASS' if sub_ok else 'FAIL'}")
        # MECH: both states present somewhere in the arm
        tot_ap = sum(r[1] for (aa, ss), rows in per.items() if aa == arm for r in rows)
        tot_sk = sum(r[2] for (aa, ss), rows in per.items() if aa == arm for r in rows)
        mech_ok = tot_ap > 0 and tot_sk > 0
        print(f"  MECH applied={tot_ap} skipped={tot_sk} -> "
              f"{'PASS' if mech_ok else 'FAIL'}")
        print(f"  => MAIN={'PASS' if main_ok else 'FAIL'} "
              f"SUB={'PASS' if sub_ok else 'FAIL'} "
              f"MECH={'PASS' if mech_ok else 'FAIL'}")


if __name__ == "__main__":
    main()
