#!/usr/bin/env python3
"""l1c_occupancy_judge.py — L1c 时序先验批判据机（**程序化，禁手抄**）。

判据权威（**不得在本文件中重新定义**）
--------------------------------------
* 形状与数字 = `results/lifecycle_paper2/evidence/prereg_L1c_occupancy.md` §3
  （先于任何 L1c run 提交；D2-006 立项）。
* 主判据：Δᵢ = occ_i − exit_i（freshvac，canonical 仪器）；
  PASS ⟺ (∀3 seeds Δᵢ < 0) ∧ (|mean Δ| > 门槛 = max(1.19, off_sd))。
  **"为负"是判据的显式分支**（NOTES 2026-09-20 坑）。
* 约束门（同 L1b 限值，逐 seed 报告）：ATE ≤ +0.5cm 且 ≤ +5%；
  static PSNR ≥ −0.25dB（基值量纲护栏 [8,60] dB）。
* 过程验证（不作判据）：occ_* 计数器（点火必要条件）+ occoff 三门 + carve/a_min
  次要观察（明写：点火与否不改变判决——L1b 教训）。

复用 `l1b_gate_judge` 的读取函数与阈值常量（同源，防口径漂移）；**不改冻结判据机**。

用法
----
    python scripts/02_analysis/l1c_occupancy_judge.py              # 判真实批（缺数据则报缺）
    python scripts/02_analysis/l1c_occupancy_judge.py --selftest   # 合成数 + 对调两臂负对照
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
import l1b_gate_judge as L1B  # noqa: E402  读取函数 + 阈值常量复用（同源头）

SEQ = "person_tracking"
SUFFIX = "_canon"
OFF_ARM = "off"


def tpl_occ(seed: int) -> str:
    return f"render_L1c_{SEQ}_occ_s{{seed}}".format(seed=seed) + SUFFIX


def tpl_exit(seed: int) -> str:
    return f"render_L3_{SEQ}_exit_s{{seed}}".format(seed=seed) + SUFFIX


def tpl_off(seed: int) -> str:
    return f"render_L3_{SEQ}_off_s{{seed}}".format(seed=seed) + SUFFIX


def tag_occ(seed: int) -> str:
    return f"L1c_{SEQ}_occ_s{seed}"


def tag_occoff() -> str:
    return f"L1c_{SEQ}_occoff_s0"


def off_sd() -> float:
    vals = []
    for s in (0, 1, 2):
        r = L1B.load_render(tpl_off(s), s)
        if r is not None and r["freshvac"] is not None:
            vals.append(r["freshvac"])
    return statistics.stdev(vals) if len(vals) >= 2 else 0.0


def judge_occ(gate_fv: list, exit_fv: list, sd: float) -> dict:
    """prereg §3 主判据：PASS ⟺ 全 3 seed 负 ∧ |mean| > max(1.19, off_sd)。"""
    ds = [(g - e) for g, e in zip(gate_fv, exit_fv) if g is not None and e is not None]
    if len(ds) < 3:
        return {"judgeable": False, "reason": f"配对不足（{len(ds)}/3）"}
    n_neg = sum(1 for d in ds if d < 0)
    mean_d = statistics.mean(ds)
    thr = max(L1B.THRESHOLD_FLOOR_CM, sd)
    sign_ok = (n_neg == 3) and (mean_d < 0)      # 方向是判据的一部分
    mag_ok = abs(mean_d) > thr
    ratio = abs(mean_d) / thr if thr > 0 else float("inf")
    tier = 1 if ratio > L1B.TIER1_MULT else (2 if ratio >= L1B.TIER2_MULT else 3)
    return {"judgeable": True, "deltas": ds, "n_neg": n_neg, "mean_delta": mean_d,
            "off_sd": sd, "threshold": thr, "sign_ok": sign_ok, "mag_ok": mag_ok,
            "PASS": bool(sign_ok and mag_ok), "ratio": ratio, "tier": tier}


def run_batch() -> int:
    occ_r = [L1B.load_render(tpl_occ(s), s) for s in (0, 1, 2)]
    exit_r = [L1B.load_render(tpl_exit(s), s) for s in (0, 1, 2)]
    missing = ([f"occ_s{s}" for s, r in zip((0, 1, 2), occ_r) if r is None]
               + [f"exit_s{s}" for s, r in zip((0, 1, 2), exit_r) if r is None])
    if missing:
        print(f"缺失渲染工件：{missing}（先跑 run_L1c_remote.sh + rerender_all_canon.sh）")
        return 2

    occ_fv = [r["freshvac"] for r in occ_r]
    exit_fv = [r["freshvac"] for r in exit_r]
    m = judge_occ(occ_fv, exit_fv, off_sd())

    print("## L1c occupancy 判据机（prereg_L1c_occupancy §3；canonical 仪器）")
    print(f"occ  freshvac = {[round(v, 4) for v in occ_fv]}")
    print(f"exit freshvac = {[round(v, 4) for v in exit_fv]}")
    print(json.dumps(m, indent=1))
    print("## 约束门（逐 seed 报告，同 L1b 限值）")
    for s in (0, 1, 2):
        g = L1B.load_render(tpl_occ(s), s)
        e = L1B.load_render(tpl_exit(s), s)
        at = L1B.gate_ate([L1B.load_ate(tag_occ(s))], [L1B.load_ate(f"L3_{SEQ}_exit_s{s}")])
        ps = L1B.gate_psnr([g["static_psnr"]], [e["static_psnr"]])
        print(f"  s{s}: ATE={json.dumps(at)} PSNR={json.dumps(ps)}")
    print("## 过程验证（不作判据）")
    for s in (0, 1, 2):
        print(f"  occ_s{s}: {json.dumps(L1B.load_counters(tag_occ(s)))}")
    print(f"  occoff_s0: {json.dumps(L1B.load_counters(tag_occoff()))}")
    ok = m.get("judgeable")
    print(f"\n判定：PASS={m.get('PASS')}" if ok else f"\n判定：{m.get('reason')}")
    return 0


def run_selftest() -> int:
    """合成数三重负对照（判据形状的机械化校验，不接真实数据）。"""
    ex = [3.5, 4.3, 4.2]
    sd = 0.5
    m = judge_occ([1.5, 2.0, 2.5], ex, sd)
    assert m["PASS"] is True and m["n_neg"] == 3, m
    # 负对照 1：对调两臂 ⇒ Δ 全正 ⇒ PASS 必须 False
    assert judge_occ(ex, [1.5, 2.0, 2.5], sd)["PASS"] is False
    # 负对照 2：一致更差（全正）⇒ False
    assert judge_occ([5.0, 5.5, 6.0], ex, sd)["PASS"] is False
    # 负对照 3：2/3 负（差一个）⇒ prereg 要求 ∀3 ⇒ False（比 L1b 的 ≥2/3 更严）
    m23 = judge_occ([3.4, 2.0, 5.2], ex, sd)
    assert m23["n_neg"] == 2 and m23["PASS"] is False, m23
    print("selftest OK：全 3 负 PASS；对调两臂/一致更差/2-of-3 均正确拒绝")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    return run_batch()


if __name__ == "__main__":
    raise SystemExit(main())
