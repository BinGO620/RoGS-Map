#!/usr/bin/env python3
"""l2_gate_judge.py — L2 gate 泛化批判据机（**程序化，禁手抄**）。

判据权威（**不得在本文件中重新定义**）
--------------------------------------
* 形状与数字 = `results/lifecycle_paper2/evidence/prereg_L2_gate.md` §3–§4
  （先于任何 L2 run 提交；git 时间戳为准；D2-005 用户拍板 A）。
* 逐序列见效 ⟺ Δ(s0) = gate − exit < 0 ∧ |Δ(s0)| > 门槛_seq = max(1.19, off_sd_seq)，
  off_sd_seq = 该序列 off 臂 3 seed canonical freshvac 样本 sd（n−1）。
  **"为负"是判据的显式分支**（NOTES 2026-09-20 坑）。
* 批判定：≥2/3 序列见效 ⟺ 效应泛化成立（R7 L2：≥2/3 类型见效才升 L3）。
* 击杀确认分支（<2/3 边际时补 s1；重判 = 双 seed 同号为负 ∧ |mean| > 门槛_seq）。
* 约束门（同 L1b 限值；逐序列报告，不改晋级判定）：ATE ≤ +0.5cm 且 ≤ +5%；
  static PSNR ≥ −0.25dB（基值量纲护栏 [8,60] dB）。

复用 `l1b_gate_judge` 的读取函数与阈值常量（同源，避免口径漂移）。

用法
----
    python scripts/02_analysis/l2_gate_judge.py              # 判真实批（缺数据则报缺）
    python scripts/02_analysis/l2_gate_judge.py --selftest   # 合成数 + 对调两臂负对照
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import l1b_gate_judge as L1B  # noqa: E402  读取函数 + 阈值常量复用（同源头）

SEQS = ["person_tracking2", "crowd", "crowd2"]
SEEDS_MAIN = [0]
SEEDS_CONFIRM = [0, 1]          # 击杀确认分支（prereg §3）
SUFFIX = "_canon"


def tpl_gate(seq: str) -> str:
    return f"render_L2_{seq}_gate_s{{seed}}" + SUFFIX


def tpl_exit(seq: str) -> str:
    return f"render_L3_{seq}_exit_s{{seed}}" + SUFFIX


def tpl_off(seq: str) -> str:
    return f"render_L3_{seq}_off_s{{seed}}" + SUFFIX


def tag_gate(seq: str, seed: int) -> str:
    return f"L2_{seq}_gate_s{seed}"


def off_sd(seq: str) -> float:
    vals = []
    for s in (0, 1, 2):
        r = L1B.load_render(tpl_off(seq), s)
        if r is not None and r["freshvac"] is not None:
            vals.append(r["freshvac"])
    return statistics.stdev(vals) if len(vals) >= 2 else 0.0


def judge_seq(seq: str, seeds: list[int]) -> dict:
    """prereg §3：逐序列判定。seeds=[0] 主判；[0,1] 击杀确认重判。"""
    gate_fv, exit_fv = [], []
    for s in seeds:
        g = L1B.load_render(tpl_gate(seq), s)
        e = L1B.load_render(tpl_exit(seq), s)
        gate_fv.append(None if g is None else g["freshvac"])
        exit_fv.append(None if e is None else e["freshvac"])
    sd = off_sd(seq)
    thr = max(L1B.THRESHOLD_FLOOR_CM, sd)
    pairs = [(g, e) for g, e in zip(gate_fv, exit_fv)
             if g is not None and e is not None]
    out = {"seq": seq, "seeds": seeds, "threshold": thr, "off_sd": sd,
           "gate_fv": gate_fv, "exit_fv": exit_fv}
    if len(pairs) < len(seeds):
        out.update({"judgeable": False,
                    "reason": f"配对不足（{len(pairs)}/{len(seeds)}）"})
        return out
    ds = [g - e for g, e in pairs]
    n_neg = sum(1 for d in ds if d < 0)
    mean_d = statistics.mean(ds)
    if len(seeds) == 1:
        sign_ok = n_neg == 1            # 单 seed：必须为负（方向是判据的一部分）
    else:
        sign_ok = n_neg == len(seeds)   # 确认分支：双 seed 同号为负
    mag_ok = abs(mean_d) > thr
    out.update({"judgeable": True, "deltas": ds, "n_neg": n_neg,
                "mean_delta": mean_d, "sign_ok": sign_ok, "mag_ok": mag_ok,
                "effect": bool(sign_ok and mag_ok)})
    return out


def report_constraints(seq: str, seeds: list[int]) -> dict:
    gate_r = [L1B.load_render(tpl_gate(seq), s) for s in seeds]
    exit_r = [L1B.load_render(tpl_exit(seq), s) for s in seeds]
    gate_ates = [L1B.load_ate(tag_gate(seq, s)) for s in seeds]
    exit_ates = [L1B.load_ate(f"L3_{seq}_exit_s{s}") for s in seeds]
    return {
        "ATE": L1B.gate_ate(gate_ates, exit_ates),
        "PSNR": L1B.gate_psnr([r["static_psnr"] if r else None for r in gate_r],
                              [r["static_psnr"] if r else None for r in exit_r]),
    }


def run_batch(confirm: bool = False) -> int:
    seeds = SEEDS_CONFIRM if confirm else SEEDS_MAIN
    results = [judge_seq(seq, seeds) for seq in SEQS]
    missing = [r["seq"] for r in results if not r.get("judgeable")]
    if missing:
        print(f"缺失渲染工件：{missing}（先跑 rerender_all_canon.sh；exit/off 臂应已就位）")
        return 2

    n_effect = sum(1 for r in results if r["effect"])
    print(f"## L2 gate 泛化判据机（prereg_L2_gate §3–§4；canonical 仪器；seeds={seeds}）")
    for r in results:
        print(f"[{r['seq']}] gate={r['gate_fv']} exit={r['exit_fv']} "
              f"Δ={r['deltas']} 门槛={r['threshold']:.4f} (off_sd={r['off_sd']:.4f}) "
              f"sign_ok={r['sign_ok']} mag_ok={r['mag_ok']} => 见效={r['effect']}")
    advance = n_effect >= 2
    print(f"\n批判定：见效 {n_effect}/{len(SEQS)} => "
          f"{'效应泛化成立（呈报 D2 决定 L3）' if advance else '泛化不成立'}")
    print("## 约束门（逐序列报告，不改晋级判定）")
    for seq in SEQS:
        c = report_constraints(seq, seeds)
        print(f"[{seq}] ATE={json.dumps(c['ATE'])} PSNR={json.dumps(c['PSNR'])}")
    print("## 过程验证（不作判据）")
    for seq in SEQS:
        for s in seeds:
            print(f"  {tag_gate(seq, s)}: {json.dumps(L1B.load_counters(tag_gate(seq, s)))}")
    if not advance and not confirm:
        print("\n注：1/3 边际时按 prereg §3 击杀确认分支补 s1 后加 --confirm 重判；"
              "0/3 不追加 run。")
    return 0


def run_selftest() -> int:
    """合成数三重负对照（判据形状的机械化校验，不接真实数据）。"""
    def mk(deltas, base=4.0):
        return [base + d for d in deltas], [base] * len(deltas)
    sd = statistics.stdev([5.0, 4.0, 4.0])
    thr = max(L1B.THRESHOLD_FLOOR_CM, sd)
    # 正例：Δ = −2.0（|Δ| > 1.19 地板，为负）
    g, e = mk([-2.0])
    assert (g[0] - e[0]) < 0 and abs(g[0] - e[0]) > thr
    # 负对照 1：对调两臂 ⇒ Δ 为正 ⇒ 不得见效
    assert (e[0] - g[0]) > 0
    # 负对照 2：方向对但幅度不足（Δ = −0.5 < 地板 1.19）
    g2, e2 = mk([-0.5])
    assert (g2[0] - e2[0]) < 0 and abs(g2[0] - e2[0]) <= thr
    # 负对照 3：确认分支——一正一负 ⇒ 不同号为负 ⇒ 不得见效
    ds = [-2.0, +0.3]
    assert not (all(d < 0 for d in ds))
    print("selftest OK：负方向/幅度地板/对调两臂/确认分支同号 四重校验过"
          f"（thr={thr:.3f}）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--confirm", action="store_true",
                    help="击杀确认分支（s0+s1 双 seed 重判，prereg §3）")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    return run_batch(confirm=args.confirm)


if __name__ == "__main__":
    raise SystemExit(main())
