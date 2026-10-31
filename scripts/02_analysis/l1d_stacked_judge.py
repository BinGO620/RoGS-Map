#!/usr/bin/env python3
"""l1d_stacked_judge.py — L1d gate×occupancy 叠加批判据机（**程序化，禁手抄**）。

判据权威（**不得在本文件中重新定义**）
--------------------------------------
* 形状与数字 = `results/lifecycle_paper2/evidence/prereg_L1d_stacked.md` §3-§5
  （先于任何 L1d run 提交；D2-007，用户 2026-09-23 批准）。
* 主判据：Δᵢ = stacked_i − exit_i（freshvac，canonical 仪器）；
  PASS ⟺ (∀3 seeds Δᵢ < 0) ∧ (|mean Δ| > 门槛 = max(1.19, off_sd))。
  "为负"是判据的显式分支；复用 `l1b_gate_judge` 读取函数与阈值常量（同源防漂移）。
* 约束门（同 L1b 限值，逐 seed 报告；**越门不自动 FAIL**，prereg §4——照 L1b 先例
  如实并陈、喂 L2 headroom 设计）：ATE ≤ +0.5cm 且 ≤ +5%；static PSNR ≥ −0.25dB。
* 诊断预测四键（预锁，不作判据；prereg §5，各带数据源工件键）：
  D① a_min 连续占据段单调下行穿 0.20 —— consolelog alpha-gate 行逐 KF `a_min=`；
  D② alpha_carve_total 首次 >0（pt 族从未发生过）—— counters（efficiency_raw.csv）；
  D③ 棘轮不触 α≥guard —— occ_alpha_lt_guard_total + carve 审计；
  D④ 人走后 α 回升（EMA 0.81α+0.09 竞速窗口）—— consolelog a_min 序列回升段。
* 两种失败形态预锁判读（prereg §5）：计数器全零 = 组合未生效（实装级）；
  a_min 下行但 carve=0 = 窗口竞速失败（机制时序级，决定 occ v2 是否立项）。

用法
----
    python scripts/02_analysis/l1d_stacked_judge.py              # 判真实批（缺数据则报缺）
    python scripts/02_analysis/l1d_stacked_judge.py --selftest   # 合成数 + 负对照
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import l1b_gate_judge as L1B  # noqa: E402  读取函数 + 阈值常量复用（同源头）

SEQ = "person_tracking"
TAU_CARVE = 0.20   # prereg 锁定常量（诊断阈值，非判据）

GATE_LINE = re.compile(
    r"alpha-gate KF (\d+):.*?capped=(\d+).*?a_min=([0-9.]+)")
OCC_LINE = re.compile(
    r"occupancy KF (\d+):.*?warm=(\d+) decayed=(\d+).*?a_min=([0-9.]+)")


def tag_stacked(seed: int) -> str:
    return f"L1d_{SEQ}_stacked_s{seed}"


def tpl_stacked(seed: int) -> str:
    return f"render_L1d_{SEQ}_stacked_s{{seed}}".format(seed=seed) + "_canon"


def tpl_exit(seed: int) -> str:
    # exit s0-2 = L3 主批 tag；s3-5 = L1c 确认批补的对照侧（render_L1c_ 前缀，
    # commit 8f90f00d/5e6a42eb）——同一物理对照，前缀随产出批次。
    if seed in (3, 4, 5):
        return f"render_L1c_{SEQ}_exit_s{{seed}}".format(seed=seed) + "_canon"
    return f"render_L3_{SEQ}_exit_s{{seed}}".format(seed=seed) + "_canon"


def tpl_off(seed: int) -> str:
    return f"render_L3_{SEQ}_off_s{{seed}}".format(seed=seed) + "_canon"


def consolelog_path(tag: str) -> str:
    return os.path.join(L1B.ROOT, f"{tag}.consolelog")


def parse_gate_series(tag: str) -> list[dict]:
    """D①/D④ 数据源：consolelog 的 alpha-gate 逐 KF 行（工件键 = 本函数输出）。"""
    p = consolelog_path(tag)
    if not os.path.isfile(p):
        return []
    out = []
    with open(p, errors="replace") as f:
        for line in f:
            m = GATE_LINE.search(line)
            if m:
                out.append({"kf": int(m.group(1)), "capped": int(m.group(2)),
                            "a_min": float(m.group(3))})
    return out


def parse_occ_series(tag: str) -> list[dict]:
    """occupancy 逐 KF 行（decay 侧指纹；与 gate 序列互补验证 warm 区存在）。"""
    p = consolelog_path(tag)
    if not os.path.isfile(p):
        return []
    out = []
    with open(p, errors="replace") as f:
        for line in f:
            m = OCC_LINE.search(line)
            if m:
                out.append({"kf": int(m.group(1)), "warm": int(m.group(2)),
                            "decayed": int(m.group(3)),
                            "a_min": float(m.group(4))})
    return out


def diagnose_ratchet(gate_series: list[dict], counters: dict) -> dict:
    """prereg §5 四诊断键 + 两种失败形态判读（预锁语义，照 prereg 原文机械应用）。"""
    if not gate_series:
        return {"diagnosable": False, "reason": "consolelog 无 alpha-gate 行"}
    amins = [g["a_min"] for g in gate_series]
    n_kf = len(amins)
    # D①：连续占据段的 a_min 单调下行穿 0.20（棘轮指纹）。
    # 段 = 从首个 capped>0 的 KF 起，到最后一个 capped>0 的 KF 止（gate 在拦 = 在占据）。
    capped_idx = [i for i, g in enumerate(gate_series) if g["capped"] > 0]
    if capped_idx:
        seg = amins[capped_idx[0]:capped_idx[-1] + 1]
        mono = all(b < a for a, b in zip(seg, seg[1:]))
        crossed = any(a < TAU_CARVE for a in seg)
    else:
        mono, crossed = False, False
    carve_total = int(counters.get("alpha_carve_total") or 0)
    capped_total = sum(g["capped"] for g in gate_series)
    decay_total = sum(int(c.get("occ_decay_events_total") or 0)
                      for c in [counters])
    # D④：末段回升检测（人走后 EMA 抬升不再被拦 ⇒ a_min 回升 = 竞速窗口的证据）
    tail = amins[-3:] if n_kf >= 3 else amins
    rebound = all(b > a for a, b in zip(tail, tail[1:])) if len(tail) >= 2 else False
    # 失败形态预锁判读（prereg §5）
    if capped_total == 0 and decay_total == 0:
        form = "combination_inert（实装级：组合未生效——验证层应已拦住，若出现 = 验证失效，如实登记）"
    elif mono and crossed and carve_total == 0:
        form = "window_race_failure（机制时序级：棘轮下行成立但 carve 未点火——人走后 EMA 回升跑赢持续性条件；直接决定 occ v2 是否立项）"
    elif carve_total > 0:
        form = "carve_fired（D② 命中：pt 族首次 carve 点火）"
    else:
        form = "partial（棘轮指纹不完整：mono={} crossed={}）".format(mono, crossed)
    return {"diagnosable": True, "n_gate_kfs": n_kf,
            "a_min_series": amins, "segment_monotonic_down": mono,
            "crossed_tau_carve": crossed, "carve_total": carve_total,
            "capped_total": capped_total, "occ_decay_events_total": decay_total,
            "tail_rebound": rebound, "failure_form": form,
            "D1_monotonic_cross": bool(mono and crossed),
            "D2_carve_first_fire": carve_total > 0,
            "D3_safety": None,  # 由调用方用 occ_alpha_lt_guard_total 填
            "D4_tail_rebound": rebound}


def off_sd() -> float:
    vals = []
    for s in (0, 1, 2):
        r = L1B.load_render(tpl_off(s), s)
        if r is not None and r["freshvac"] is not None:
            vals.append(r["freshvac"])
    return statistics.stdev(vals) if len(vals) >= 2 else 0.0


def judge_stacked(stacked_fv: list, exit_fv: list, sd: float) -> dict:
    """prereg §3 主判据：PASS ⟺ 全 3 seed 负 ∧ |mean| > max(1.19, off_sd)。"""
    ds = [(g - e) for g, e in zip(stacked_fv, exit_fv) if g is not None and e is not None]
    if len(ds) < 3:
        return {"judgeable": False, "reason": f"配对不足（{len(ds)}/3）"}
    n_neg = sum(1 for d in ds if d < 0)
    mean_d = statistics.mean(ds)
    thr = max(L1B.THRESHOLD_FLOOR_CM, sd)
    sign_ok = (n_neg == 3) and (mean_d < 0)
    mag_ok = abs(mean_d) > thr
    ratio = abs(mean_d) / thr if thr > 0 else float("inf")
    tier = 1 if ratio > L1B.TIER1_MULT else (2 if ratio >= L1B.TIER2_MULT else 3)
    return {"judgeable": True, "deltas": ds, "n_neg": n_neg, "mean_delta": mean_d,
            "off_sd": sd, "threshold": thr, "sign_ok": sign_ok, "mag_ok": mag_ok,
            "PASS": bool(sign_ok and mag_ok), "ratio": ratio, "tier": tier}


def parse_pairs_to_confirmation() -> dict:
    """prereg §6 击杀确认分支：6-seed 配对重判（照 L1c verdict §0.1 同源形状）。

    对 = {s0,s3} {s1,s4} {s2,s5}；对达标 ⟺ 两 seed Δ 同负 ∧ |mean Δ|>门槛
    （门槛 = max(1.19, off_sd)，与主判据同源）。0/3 对达标 ⇒ 链式假说关闭。
    """
    stacked = [L1B.load_render(tpl_stacked(s), s) for s in (0, 1, 2, 3, 4, 5)]
    exit_r = [L1B.load_render(tpl_exit(s), s) for s in (0, 1, 2, 3, 4, 5)]
    missing = ([f"stacked_s{s}" for s, r in zip((0, 1, 2, 3, 4, 5), stacked) if r is None]
               + [f"exit_s{s}" for s, r in zip((0, 1, 2, 3, 4, 5), exit_r) if r is None])
    if missing:
        print(f"缺失渲染工件：{missing}（确认批 = stacked s3-5 渲染；exit s3-5 已入库）")
        return {"judgeable": False, "reason": f"配对工件缺失：{missing}"}
    sd = off_sd()
    thr = max(L1B.THRESHOLD_FLOOR_CM, sd)
    ds = [r["freshvac"] - e["freshvac"] for r, e in zip(stacked, exit_r)]
    rows = []
    for i, (a, b) in enumerate(zip((0, 1, 2), (3, 4, 5))):
        pair_d = (ds[a], ds[b])
        same_neg = pair_d[0] < 0 and pair_d[1] < 0
        mag = abs(statistics.mean(pair_d)) > thr
        rows.append({"pair": f"s{a}/s{b}", "deltas": [round(d, 4) for d in pair_d],
                     "same_neg": same_neg, "mag_ok": mag,
                     "hit": bool(same_neg and mag)})
    n_hit = sum(1 for r in rows if r["hit"])
    return {"judgeable": True, "pairs": rows, "n_pairs_hit": n_hit,
            "deltas_6seed": [round(d, 4) for d in ds],
            "mean_delta_6seed": round(statistics.mean(ds), 4),
            "off_sd": sd, "threshold": thr,
            "VERDICT_KILL": n_hit == 0}


def run_batch() -> int:
    stacked_r = [L1B.load_render(tpl_stacked(s), s) for s in (0, 1, 2)]
    exit_r = [L1B.load_render(tpl_exit(s), s) for s in (0, 1, 2)]
    missing = ([f"stacked_s{s}" for s, r in zip((0, 1, 2), stacked_r) if r is None]
               + [f"exit_s{s}" for s, r in zip((0, 1, 2), exit_r) if r is None])
    if missing:
        print(f"缺失渲染工件：{missing}（先跑 run_L1d_remote.sh + rerender_all_canon.sh）")
        return 2

    stacked_fv = [r["freshvac"] for r in stacked_r]
    exit_fv = [r["freshvac"] for r in exit_r]
    m = judge_stacked(stacked_fv, exit_fv, off_sd())

    print("## L1d stacked 判据机（prereg_L1d_stacked §3；canonical 仪器）")
    print(f"stacked freshvac = {[round(v, 4) for v in stacked_fv]}")
    print(f"exit    freshvac = {[round(v, 4) for v in exit_fv]}")
    print(json.dumps(m, indent=1))
    print("## 约束门（逐 seed 报告，同 L1b 限值；越门不自动 FAIL——prereg §4）")
    for s in (0, 1, 2):
        g = L1B.load_render(tpl_stacked(s), s)
        e = L1B.load_render(tpl_exit(s), s)
        at = L1B.gate_ate([L1B.load_ate(tag_stacked(s))],
                          [L1B.load_ate(f"L3_{SEQ}_exit_s{s}")])
        ps = L1B.gate_psnr([g["static_psnr"]], [e["static_psnr"]])
        print(f"  s{s}: ATE={json.dumps(at)} PSNR={json.dumps(ps)}")
    print("## 诊断预测四键（预锁，不作判据——prereg §5）")
    for s in (0, 1, 2):
        tag = tag_stacked(s)
        counters = L1B.load_counters(tag)
        d = diagnose_ratchet(parse_gate_series(tag), counters)
        lt_guard = counters.get("occ_alpha_lt_guard_total")
        if d.get("diagnosable"):
            d["D3_safety"] = f"occ_alpha_lt_guard_total={lt_guard}（审计键）"
        print(f"  {tag}: {json.dumps(d, ensure_ascii=False)}")
    ok = m.get("judgeable")
    print(f"\n判定：PASS={m.get('PASS')}" if ok else f"\n判定：{m.get('reason')}")
    return 0


def run_selftest() -> int:
    """合成数三重负对照 + 棘轮诊断三形态（判据形状的机械化校验，不接真实数据）。"""
    ex = [3.5, 4.3, 4.2]
    sd = 0.5
    m = judge_stacked([1.5, 2.0, 2.5], ex, sd)
    assert m["PASS"] is True and m["n_neg"] == 3, m
    assert judge_stacked(ex, [1.5, 2.0, 2.5], sd)["PASS"] is False
    assert judge_stacked([5.0, 5.5, 6.0], ex, sd)["PASS"] is False
    m23 = judge_stacked([3.4, 2.0, 5.2], ex, sd)
    assert m23["n_neg"] == 2 and m23["PASS"] is False, m23
    # 诊断形态 1：计数器全零 = combination_inert
    d0 = diagnose_ratchet([{"kf": 5, "capped": 0, "a_min": 0.22}],
                          {"alpha_carve_total": 0, "occ_decay_events_total": 0})
    assert "combination_inert" in d0["failure_form"], d0
    # 诊断形态 2：a_min 单调下行穿阈但 carve=0 = window_race_failure
    series = [{"kf": k, "capped": 10, "a_min": a} for k, a in
              zip((5, 10, 15, 20, 25), (0.22, 0.198, 0.178, 0.16, 0.145))]
    d1 = diagnose_ratchet(series, {"alpha_carve_total": 0,
                                   "occ_decay_events_total": 50})
    assert d1["D1_monotonic_cross"] is True and d1["D2_carve_first_fire"] is False, d1
    assert "window_race_failure" in d1["failure_form"], d1
    # 诊断形态 3：carve 点火
    d2 = diagnose_ratchet(series, {"alpha_carve_total": 7,
                                   "occ_decay_events_total": 50})
    assert d2["D2_carve_first_fire"] is True and "carve_fired" in d2["failure_form"], d2
    # 非单调下行 ⇒ D① 不命中
    series_nm = [{"kf": k, "capped": 10, "a_min": a} for k, a in
                 zip((5, 10, 15), (0.22, 0.25, 0.19))]
    assert diagnose_ratchet(series_nm, {"alpha_carve_total": 0})[
        "D1_monotonic_cross"] is False
    print("selftest OK：主判据三负对照 + 诊断三形态（inert/race/fired）+ 非单调拒绝")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--confirm", action="store_true",
                    help="prereg §6 击杀确认分支：6-seed 配对重判")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    if args.confirm:
        r = parse_pairs_to_confirmation()
        print("## L1d 确认重判（prereg_L1d_stacked §6 预锁分支；6-seed 配对）")
        print(json.dumps(r, indent=1, ensure_ascii=False))
        if r.get("judgeable") and r["VERDICT_KILL"]:
            print("\n判定：0/3 对达标 ⇒ gate×occupancy 链式假说关闭（prereg §6 关闭范围预锁）")
        elif r.get("judgeable"):
            print(f"\n判定：{r['n_pairs_hit']}/3 对达标 ⇒ 按 prereg §6 处置")
        return 0 if r.get("judgeable") else 2
    return run_batch()


if __name__ == "__main__":
    raise SystemExit(main())
