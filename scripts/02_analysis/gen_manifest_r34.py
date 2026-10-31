#!/usr/bin/env python
"""gen_manifest_r34.py — 从原始 tracking_raw.csv 确定性重建 manifest.json（R34 判决的机器可读档；落在 results/paper2_rollout/evidence/）。

数字来源 = run 目录原始输出（col8 全帧 / col14 keyframe），机械生成。
K5/K6 判据常量（FROZEN / PRIOR_ALL_OFF）**直接从 analyze_r34.py 导入**，
杜绝双源漂移；K5 状态与 K6 降级判定按与 analyze_r34.py 相同的规则复算
（复核两文件一致性：同输入下两者的 K5/K6 字段必须一致）。

用法:
  python scripts/02_analysis/gen_manifest_r34.py --date 2026-09-18 \
      --verdict "<一行结论>" [--out results/paper2_rollout/evidence/manifest.json]
"""
import argparse
import csv
import importlib.util
import json
import statistics
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("analyze_r34", _HERE / "analyze_r34.py")
_a = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_a)  # __main__ guard => 无副作用

SEQS = _a.SEQS
ARMS = _a.ARMS
FROZEN = _a.FROZEN
PRIOR_ALL_OFF = _a.PRIOR_ALL_OFF
ROOT = Path("results/paper2_rollout")

_ap = argparse.ArgumentParser()
_ap.add_argument("--date", required=True)
_ap.add_argument("--verdict", required=True)
_ap.add_argument("--out", default=str(ROOT / "evidence" / "manifest.json"))
args = _ap.parse_args()


def read(tag):
    p = ROOT / tag / "tables" / "tracking_raw.csv"
    if not p.exists():
        return None
    rows = [r for r in csv.DictReader(open(p)) if r.get("status") == "OK"]
    if not rows:
        return None
    r = rows[-1]
    return float(r["ate_rmse_cm"]), float(r["keyframe_ate_rmse_cm"])


out, n = {}, 0
for arm in ARMS:
    out[arm] = {}
    for seq in SEQS:
        per = []
        for k in (0, 1, 2):
            r = read(f"r34_{arm}_{seq}_seed{k}")
            if r:
                per.append({"seed": k, "full_cm": round(r[0], 4), "kf_cm": round(r[1], 4)})
                n += 1
        if per:
            full = [p["full_cm"] for p in per]
            out[arm][seq] = {
                "per_seed": per,
                "mean_full_cm": round(statistics.mean(full), 4),
                "sd_full_cm": round(statistics.stdev(full), 4) if len(full) > 1 else None,
                "mean_kf_cm": round(statistics.mean(p["kf_cm"] for p in per), 4),
            }

# 派生列（rb→sw / rb→gate）+ K5（与 analyze_r34.py 同规则）
deriv, k5 = {}, {}
for seq in SEQS:
    b = out["rb"][seq]["mean_full_cm"]
    s = out["sw"][seq]["mean_full_cm"]
    g = out["gate"][seq]["mean_full_cm"]
    deriv[seq] = {"rb_to_sw_cm": round(s - b, 4), "rb_to_gate_cm": round(g - b, 4)}
    frz = FROZEN[seq][0]
    d = b - frz
    prior = PRIOR_ALL_OFF.get(seq, [frz])
    spread = (max(prior) - min(prior)) if len(prior) > 1 else None
    tol = max(1.0, spread) if spread is not None else 1.0
    k5[seq] = {
        "frozen_rb_cm": frz,
        "prior_obs_cm": prior,
        "delta_cm": round(d, 4),
        "tol_cm": round(tol, 4),
        "pass": abs(d) <= tol,
    }

# K6（含 K5 剔除语义；与 analyze_r34.py §E 同规则）
hARM = ["f1_room", "f3_st_rpy", "f3_office", "moving_obstructing_box", "f3_wk_rpy"]
harm_kept = [s for s in hARM if k5[s]["pass"]]
harm_dropped = [s for s in hARM if not k5[s]["pass"]]
kept_ok = [s for s in harm_kept if deriv[s]["rb_to_gate_cm"] > 0 and abs(deriv[s]["rb_to_gate_cm"]) > 1.0]
if len(harm_dropped) >= 3:
    k6_verdict = ("auto-downgraded to NOT-REPRODUCIBLE: K5 dropped >=3 of 5 harm seq "
                  f"({', '.join(harm_dropped)}); kept {len(harm_kept)} ({', '.join(harm_kept)}), "
                  f"of which gate-harmed >1.0cm: {len(kept_ok)}")
elif len(kept_ok) >= 3:
    k6_verdict = f"maintained: {len(kept_ok)}/{len(harm_kept)} harm seq kept with gate>+1.0cm"
else:
    k6_verdict = f"partially failed: only {len(kept_ok)}/{len(harm_kept)} kept harm seq exceed +1.0cm"

doc = {
    "experiment": "paper2_rollout/reverification_r34",
    "date": args.date,
    "batch": "R34: 3 arms x 6 seq x 3 seed = 54 run, all rc=0 (2026-09-17 07:24 -> 22:14)",
    "arms_note": ("same-batch, same-code re-verification of the 6 |delta|>1.5cm held-out sequences "
                  "(prereg selection rule). rb = fixed-stack baseline (SWBA/LoopClosure/gate all off, "
                  "K7: same-batch contrast ONLY, must not be used as a standalone method baseline or "
                  "extrapolated across experiments); sw = rb+SWBA (attribution arm); gate = deployment form"),
    "ate_column": "ate_rmse_cm (col8, full-frame); kf_cm = keyframe col14",
    "prereg": "evidence/prereg_r34.md",
    "analyzer_output": "evidence/analyze_r34_output.txt",
    "verdict": args.verdict,
    "runs_rc0": n,
    "arms": out,
    "derived": deriv,
    "k5_reproducibility": k5,
    "k6": {"harm_seq_kept": harm_kept, "harm_seq_dropped_k5": harm_dropped,
           "kept_with_gate_gt_1cm": kept_ok, "verdict": k6_verdict},
}
Path(args.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
print(f"written {args.out}  runs={n}  k6={k6_verdict[:80]}")
