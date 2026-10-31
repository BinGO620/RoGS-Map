#!/usr/bin/env python3
"""l2_tum_judge.py — TUM wk_rpy 新域移植批判据机（**程序化，禁手抄**）。

判据权威（**不得在本文件中重新定义**）
--------------------------------------
* 形状与数字 = `results/lifecycle_paper2/evidence/prereg_L2_tum_wk.md` §3-§6
  （先于任何 run 提交；D2-009 夜间保守执行件，R3/R7）。
* 主判据：Δᵢ = exit_i − off_i（freshvac，canonical 仪器）；
  PASS ⟺ (∀3 seeds Δᵢ < 0) ∧ (|mean Δ| > 门槛 = max(1.19, off_sd))。
  照 L1b/L1c/L1d/L1e 同源门槛；读取函数复用 l1b_gate_judge（同源防漂移）。
* 约束门（同 L1b）：ATE ≤ +0.5cm 且 ≤ +5%；static PSNR ≥ −0.25dB。逐 seed 报告，
  越门不自动 FAIL。
* 诊断读数（预锁，不作判据）：reset/carve 计数；census 的 exc_nowstat_fresh（另跑）。

用法
----
    python scripts/02_analysis/l2_tum_judge.py            # 主判
    python scripts/02_analysis/l2_tum_judge.py --selftest
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import l1b_gate_judge as L1B  # noqa: E402

SEQ_TAG = "L3_tum_wk_rpy"


def tpl(arm: str, seed: int) -> str:
    return f"render_{SEQ_TAG}_{arm}_s{seed}_canon"


def tag(arm: str, seed: int) -> str:
    return f"{SEQ_TAG}_{arm}_s{seed}"


def judge(off_fv: list, exit_fv: list, sd: float) -> dict:
    ds = [e - o for o, e in zip(off_fv, exit_fv) if e is not None and o is not None]
    if len(ds) < 3:
        return {"judgeable": False, "reason": f"配对不足（{len(ds)}/3）"}
    n_neg = sum(1 for d in ds if d < 0)
    mean_d = statistics.mean(ds)
    thr = max(L1B.THRESHOLD_FLOOR_CM, sd)
    sign_ok = (n_neg == 3) and (mean_d < 0)
    mag_ok = abs(mean_d) > thr
    ratio = abs(mean_d) / thr if thr > 0 else float("inf")
    tier = 1 if ratio > L1B.TIER1_MULT else (2 if ratio >= L1B.TIER2_MULT else 3)
    return {"judgeable": True, "deltas": [round(d, 4) for d in ds], "n_neg": n_neg,
            "mean_delta": round(mean_d, 4), "off_sd": round(sd, 4),
            "threshold": round(thr, 4), "sign_ok": sign_ok, "mag_ok": mag_ok,
            "PASS": bool(sign_ok and mag_ok), "ratio": round(ratio, 4), "tier": tier}


def off_sd(off_r: list) -> float:
    vals = [r["freshvac"] for r in off_r if r is not None and r["freshvac"] is not None]
    return statistics.stdev(vals) if len(vals) >= 2 else 0.0


def run_batch() -> int:
    off_r = [L1B.load_render(tpl("off", s), s) for s in (0, 1, 2)]
    ex_r = [L1B.load_render(tpl("exit", s), s) for s in (0, 1, 2)]
    missing = ([f"off_s{s}" for s, r in zip((0, 1, 2), off_r) if r is None]
               + [f"exit_s{s}" for s, r in zip((0, 1, 2), ex_r) if r is None])
    if missing:
        print(f"缺失渲染工件：{missing}（先跑 run_L2_tum_wk_remote.sh + rerender_all_canon.sh）")
        return 2
    off_fv = [r["freshvac"] for r in off_r]
    ex_fv = [r["freshvac"] for r in ex_r]
    m = judge(off_fv, ex_fv, off_sd(off_r))
    print("## TUM wk_rpy 新域移植判据机（prereg_L2_tum_wk §3；canonical 仪器）")
    print(f"off  freshvac = {[round(v, 4) for v in off_fv]}")
    print(f"exit freshvac = {[round(v, 4) for v in ex_fv]}")
    print(json.dumps(m, indent=1))
    print("## 约束门（逐 seed；越门不自动 FAIL——prereg §4）")
    for s in (0, 1, 2):
        at = L1B.gate_ate([L1B.load_ate(tag("exit", s))], [L1B.load_ate(tag("off", s))])
        ps = L1B.gate_psnr([ex_r[s]["static_psnr"]], [off_r[s]["static_psnr"]])
        print(f"  s{s}: ATE={json.dumps(at)} PSNR={json.dumps(ps)}")
    print("## 诊断读数（不作判据）")
    for s in (0, 1, 2):
        print(f"  exit_s{s}: {json.dumps(L1B.load_counters(tag('exit', s)))}")
        print(f"  off_s{s}:  {json.dumps(L1B.load_counters(tag('off', s)))}")
    print(f"\n判定：PASS={m.get('PASS')}" if m.get("judgeable") else f"\n判定：{m.get('reason')}")
    return 0


def run_confirm() -> int:
    """prereg §6 击杀分支：6-seed 配对重判（照 L1c/L1d 判据机同形；读法见
    prereg_L2_tum_wk_amendment_1_confirm_reading.md 的带日期定义）。"""
    off_r = [L1B.load_render(tpl("off", s), s) for s in range(6)]
    ex_r = [L1B.load_render(tpl("exit", s), s) for s in range(6)]
    missing = ([f"off_s{s}" for s, r in zip(range(6), off_r) if r is None]
               + [f"exit_s{s}" for s, r in zip(range(6), ex_r) if r is None])
    if missing:
        print(f"缺失渲染工件：{missing}（先跑确认批 + 渲染）")
        return 2
    off_fv = [r["freshvac"] for r in off_r]
    ex_fv = [r["freshvac"] for r in ex_r]
    ds = [e - o for o, e in zip(off_fv, ex_fv)]
    sd = off_sd(off_r)
    thr = max(L1B.THRESHOLD_FLOOR_CM, sd)
    pairs, hits = [], 0
    for a, b in ((0, 3), (1, 4), (2, 5)):
        same_neg = ds[a] < 0 and ds[b] < 0
        mag = abs(statistics.mean([ds[a], ds[b]])) > thr
        hit = bool(same_neg and mag)
        hits += int(hit)
        pairs.append({"pair": f"s{a}/s{b}", "deltas": [round(ds[a], 4), round(ds[b], 4)],
                      "same_neg": same_neg, "mag_ok": mag, "hit": hit})
    all6_neg = sum(1 for d in ds if d < 0)
    all6_pass = (all6_neg == 6) and (abs(statistics.mean(ds)) > thr)
    out = {"pairs": pairs, "n_pairs_hit": hits,
           "deltas_6seed": [round(d, 4) for d in ds],
           "n_neg_6seed": all6_neg,
           "mean_delta_6seed": round(statistics.mean(ds), 4),
           "off_sd": round(sd, 4), "threshold": round(thr, 4),
           "reading_pair": "命中 ⟺ 同负 ∧ |mean|>门槛（L1c/L1d 同形）",
           "reading_all6": f"∀6 负 ∧ |mean|>门槛 ⇒ {all6_pass}（对照读法，也 FAIL）",
           "VERDICT_KILL": hits == 0}
    print("## TUM wk_rpy 确认重判（prereg §6 + 修正案 1 读法；6-seed 配对）")
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if hits == 0:
        print("\n判定：0/3 对达标 ⇒ 本域移植支关闭（prereg §6 预锁）")
    else:
        print(f"\n判定：{hits}/3 对达标")
    return 0


def run_selftest() -> int:
    ex = [-2.0, -2.5, -3.0]
    off = [0.0, 0.1, -0.1]
    m = judge(off, ex, 0.1)
    assert m["PASS"] is True and m["n_neg"] == 3, m
    assert judge(ex, off, 0.1)["PASS"] is False          # 对调 ⇒ 全正
    assert judge(off, [0.5, -1.0, -1.5], 0.1)["PASS"] is False   # 2/3 负
    assert judge(off, [-0.3, -0.4, -0.2], 0.1)["PASS"] is False  # 幅度不足
    print("selftest OK：主判二负一正 + 三负对照")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--confirm", action="store_true",
                    help="prereg §6 击杀分支：6-seed 配对重判")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    return run_confirm() if args.confirm else run_batch()


if __name__ == "__main__":
    raise SystemExit(main())
