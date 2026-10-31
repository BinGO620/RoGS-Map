#!/usr/bin/env python3
"""l1b_gate_judge.py — L1b 证据门控批判据机（**程序化，禁手抄**）。

判据权威（**不得在本文件中重新定义**）
--------------------------------------
* 形状与数字 = `results/lifecycle_paper2/evidence/prereg_L1b_gate.md` §4–§6
  （先于任何 L1b run 提交；git 时间戳为准）。
* 主判据：Δᵢ = gate_i − exit_i（freshvac，cls12 修正仪器）；PASS ⟺
  （≥2/3 seed 的 Δᵢ < 0）∧（|mean(Δ)| > 门槛 = max(1.19, off_sd)）。
  **"为负"是判据的显式分支**（NOTES 2026-09-20 坑：只查同号会让"机制一致更差"也过）。
* 约束门（vs L3 exit）：ATE Δ ≤ +0.5cm 且 ≤ +5%；static PSNR Δ ≥ −0.25dB
  （基值量纲护栏 [8,60] dB）。
* 过程验证（不作判据，只报告）：alpha_gate_capped_total / alpha_carve_total 等
  （efficiency_raw.csv；exit 臂在 pt 上 carve=0 —— gate>0 是解锁信号）。

数据来源（工件键绑定）
----------------------
    freshvac / static_psnr ← render_metrics.json（cls12 dense 目录）
    ATE                    ← tables/tracking_raw.csv:ate_rmse_cm
    机制计数器             ← tables/efficiency_raw.csv:alpha_*

用法
----
    python scripts/02_analysis/l1b_gate_judge.py                    # 判真实批（缺数据则报缺）
    python scripts/02_analysis/l1b_gate_judge.py --selftest         # 合成数 + 对调两臂负对照
    python scripts/02_analysis/l1b_gate_judge.py --check-off-consistency
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.join(REPO, "results", "lifecycle_paper2")

SEQ = "person_tracking"
SEEDS = [0, 1, 2]
# 渲染目录模板（默认 = 本轮 canonical 掩码；_seg12dense = 2026-09-21 中途的 cls12 仪器，
# _dense = 历史 gtmc 仪器，均保留供审计复现）
RENDER_SUFFIX = "_canon"
GATE_TPL = "render_L1b_person_tracking_gate_s{seed}" + RENDER_SUFFIX
EXIT_TPL = "render_L3_person_tracking_exit_s{seed}" + RENDER_SUFFIX
OFF_TPL = "render_L3_person_tracking_off_s{seed}" + RENDER_SUFFIX

THRESHOLD_FLOOR_CM = 1.19   # prereg_L1b_gate §4（保守地板；off_sd 实测 0.5839 < 地板）
ATE_GATE_ABS_CM = 0.5       # prereg §5
ATE_GATE_REL = 0.05
PSNR_GATE_DB = -0.25
TIER1_MULT, TIER2_MULT = 2.0, 1.0


# ────────────────────────────── 读数 ──────────────────────────────
def load_render(tpl: str, seed: int) -> dict | None:
    p = os.path.join(ROOT, tpl.format(seed=seed), "render_metrics.json")
    if not os.path.isfile(p):
        return None
    m = json.load(open(p))
    return {
        "freshvac": m.get("mean_freshvac_ghost_excess_depth_l1_cm"),
        "static_psnr": m.get("mean_static_psnr"),
        "n_frames": m.get("n_frames"),
        "dir": os.path.dirname(p),
    }


def load_ate(tag: str) -> float | None:
    p = os.path.join(ROOT, tag, "tables", "tracking_raw.csv")
    if not os.path.isfile(p):
        return None
    with open(p, newline="") as f:
        rows = list(csv.DictReader(f))
    vals = [float(r["ate_rmse_cm"]) for r in rows
            if r.get("ate_rmse_cm") not in (None, "", "nan")]
    return vals[-1] if vals else None


def load_counters(tag: str) -> dict:
    p = os.path.join(ROOT, tag, "tables", "efficiency_raw.csv")
    if not os.path.isfile(p):
        return {}
    with open(p, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}
    r = rows[-1]
    keys = ["alpha_gate_capped_total", "alpha_gate_prevented_rise_sum",
            "alpha_gate_no_mask_kfs", "alpha_carve_total",
            "alpha_exit_reset_total", "alpha_lifecycle_steps",
            # L1c occupancy-memory ledger（关卡① C1 整改：判据机补 occ 九键输出，
            # 消除判决书"程序化禁手抄"与 occ 数字手抄 CSV 的矛盾）
            "occ_decay_events_total", "occ_warm_prims_total",
            "occ_alpha_lt_guard_total", "occ_no_mask_kfs"]
    return {k: r.get(k) for k in keys}


# ────────────────────────────── 判据 ──────────────────────────────
def judge(gate: list, ex: list, off_sd: float) -> dict:
    ds = [(g - e) for g, e in zip(gate, ex) if g is not None and e is not None]
    n_ok = len(ds)
    if n_ok < 3:
        return {"n_pairs": n_ok, "judgeable": False,
                "reason": f"配对不足（{n_ok}/3）"}
    n_neg = sum(1 for d in ds if d < 0)
    mean_d = statistics.mean(ds)
    thr = max(THRESHOLD_FLOOR_CM, off_sd)
    sign_ok = (n_neg >= 2) and (mean_d < 0)      # 方向是判据的一部分
    mag_ok = abs(mean_d) > thr
    ratio = abs(mean_d) / thr if thr > 0 else float("inf")
    tier = 1 if ratio > TIER1_MULT else (2 if ratio >= TIER2_MULT else 3)
    return {"n_pairs": n_ok, "judgeable": True, "deltas": ds, "n_neg": n_neg,
            "mean_delta": mean_d, "off_sd": off_sd, "threshold": thr,
            "sign_ok": sign_ok, "mag_ok": mag_ok,
            "PASS": bool(sign_ok and mag_ok), "ratio": ratio, "tier": tier}


def gate_ate(gate_ates, exit_ates) -> dict:
    pairs = [(g, e) for g, e in zip(gate_ates, exit_ates)
             if g is not None and e is not None]
    if not pairs:
        return {"ok": None, "reason": "无 ATE 读数"}
    d = statistics.mean(g - e for g, e in pairs)
    base = statistics.mean(e for _, e in pairs)
    rel = (d / base) if base else float("nan")
    return {"ok": bool(d <= ATE_GATE_ABS_CM and rel <= ATE_GATE_REL),
            "delta_cm": d, "rel": rel}


def gate_psnr(gate_ps, exit_ps) -> dict:
    pairs = [(g, e) for g, e in zip(gate_ps, exit_ps)
             if g is not None and e is not None]
    if not pairs:
        return {"ok": None, "reason": "无 static PSNR 读数"}
    base = statistics.mean(e for _, e in pairs)
    if not (8.0 <= base <= 60.0):
        raise AssertionError(
            f"static PSNR 基值 {base:.3f} dB 不在 [8,60] —— 喂错指标（量纲护栏）")
    d = statistics.mean(g - e for g, e in pairs)
    return {"ok": bool(d >= PSNR_GATE_DB), "delta_db": d}


# ────────────────────────────── 主批 ──────────────────────────────
def run_batch() -> int:
    gate_r = [load_render(GATE_TPL, s) for s in SEEDS]
    exit_r = [load_render(EXIT_TPL, s) for s in SEEDS]
    off_r = [load_render(OFF_TPL, s) for s in SEEDS]
    missing = [f"gate_s{s}" for s, r in zip(SEEDS, gate_r) if r is None]
    missing += [f"exit_s{s}" for s, r in zip(SEEDS, exit_r) if r is None]
    if missing:
        print(f"缺失渲染工件：{missing}（先跑 rerender_L1b_seg12.sh / 已有 cls12 基线）")
        return 2

    gate_fv = [r["freshvac"] for r in gate_r]
    exit_fv = [r["freshvac"] for r in exit_r]
    off_fv = [r["freshvac"] for r in off_r]
    off_sd = (statistics.stdev([v for v in off_fv if v is not None])
              if sum(v is not None for v in off_fv) >= 2 else 0.0)

    m = judge(gate_fv, exit_fv, off_sd)
    ga = gate_psnr([r["static_psnr"] for r in gate_r],
                   [r["static_psnr"] for r in exit_r])
    gate_ates = [load_ate(f"L1b_person_tracking_gate_s{s}") for s in SEEDS]
    exit_ates = [load_ate(f"L3_person_tracking_exit_s{s}") for s in SEEDS]
    at = gate_ate(gate_ates, exit_ates)

    print("## L1b gate 判据机（prereg_L1b_gate §4–§6；freshvac = cls12 修正仪器）")
    print(f"gate  freshvac = {[round(v, 4) if v is not None else None for v in gate_fv]}")
    print(f"exit  freshvac = {[round(v, 4) if v is not None else None for v in exit_fv]}")
    print(f"off   freshvac = {[round(v, 4) if v is not None else None for v in off_fv]}  (sd={off_sd:.4f})")
    print(json.dumps(m, indent=1))
    print("## 约束门（vs L3 exit）")
    print(f"ATE:   {json.dumps(at)}")
    print(f"PSNR:  {json.dumps(ga)}")
    print("## 过程验证（不作判据）")
    for s in SEEDS:
        c = load_counters(f"L1b_person_tracking_gate_s{s}")
        print(f"  gate_s{s}: {json.dumps(c)}")
    print(f"\n判定：PASS={m.get('PASS')}"
          if m.get("judgeable") else f"\n判定：{m.get('reason')}")
    return 0


# ────────────────────────────── 自测 ──────────────────────────────
def run_selftest() -> int:
    # 合成数（量级取自真实基线：exit 3.5/4.3/4.2，off 5.0/4.0/4.0）
    ex = [3.5053, 4.2651, 4.2156]
    off = [5.0066, 4.0329, 3.9613]
    off_sd = statistics.stdev(off)
    gate = [1.5, 2.0, 2.5]  # 假设 gate 起效：Δ ≈ −2.0/−2.27/−1.72
    m = judge(gate, ex, off_sd)
    assert m["PASS"] is True and m["n_neg"] == 3 and m["mean_delta"] < -1.19, m
    # 负对照 1：对调两臂（gate↔exit）⇒ Δ 全正 ⇒ PASS 必须 False
    m_sw = judge(ex, gate, off_sd)
    assert m_sw["PASS"] is False, m_sw
    # 负对照 2：机制一致更差（gate 全部更差但同号）⇒ PASS 必须 False（方向分支）
    m_worse = judge([5.0, 5.5, 6.0], ex, off_sd)
    assert m_worse["PASS"] is False and m_worse["n_neg"] == 0, m_worse
    # 负对照 3：幅度不足（同号但 |mean| < 门槛）
    m_small = judge([3.4, 4.2, 4.1], ex, off_sd)
    assert m_small["PASS"] is False, m_small
    print(f"selftest OK: mean Δ={m['mean_delta']:.3f} 3/3 负 门槛={m['threshold']:.3f} "
          f"PASS=True；对调两臂 PASS={m_sw['PASS']}；一致更差 PASS={m_worse['PASS']}；"
          f"幅度不足 PASS={m_small['PASS']}")
    return 0


def run_off_consistency() -> int:
    """§9（修正案 1 后）：三门。① 行为面 [硬]：gateoff 的 alpha_gate_* 全 0；
    ② 轨迹面 [诊断]：gateoff ATE 落在同序列同栈全部 L3 run 的实测带内；③ 提示代码面 diff 命令。
    """
    import glob as _glob
    a_off = load_ate("L1b_person_tracking_gateoff") or load_ate("L1b_person_tracking_gateoff")
    if a_off is None:
        print("缺 gateoff ATE 读数 —— tables 是否已拉回？")
        return 2

    # ① 行为面（硬门）：关闭态必须零动作
    c = load_counters("L1b_person_tracking_gateoff")
    capped = c.get("alpha_gate_capped_total")
    prevented = c.get("alpha_gate_prevented_rise_sum")
    nomask = c.get("alpha_gate_no_mask_kfs")
    behavior_ok = str(capped) in ("0", "0.0") and str(prevented) in ("0", "0.0") and str(nomask) in ("0", "0.0")
    print(f"① 行为面[硬]：capped={capped} prevented={prevented} no_mask_kfs={nomask} => "
          f"{'PASS（关闭态零动作）' if behavior_ok else 'FAIL'}")

    # ② 轨迹面（诊断）：同序列同栈（pt）全部 L3 run 的 ATE 实测带
    band = []
    for arm in ("off", "exit"):
        for s in SEEDS:
            v = load_ate(f"L3_person_tracking_{arm}_s{s}")
            if v is not None:
                band.append((f"L3_{arm}_s{s}", v))
    if not band:
        print("② 轨迹面：无 L3 参照读数（本地缺 tables）")
        return 0 if behavior_ok else 1
    lo = min(v for _, v in band); hi = max(v for _, v in band)
    in_band = lo <= a_off <= hi
    print(f"② 轨迹面[诊断]：gateoff ATE={a_off:.4f}；L3 pt 同栈实测带=[{lo:.4f}, {hi:.4f}] "
          f"=> {'带内（混沌一致）' if in_band else '带外 —— 停批人工排查后再消费本批'}")
    print(f"   （带 = {', '.join(f'{n}={v:.3f}' for n, v in band)}）")
    print("③ 代码面[硬]：git diff --stat <L3派发点>..<L1b提交> -- utils/ gaussian_splatting/ slam.py "
          "（应只含 flag-gated 新增）")
    return 0 if (behavior_ok and in_band) else 1


def _retemplate(suffix: str) -> None:
    """切换渲染目录后缀（canonical / 历史）。模块级模板，避免把参数穿到每个读取点。"""
    global RENDER_SUFFIX, GATE_TPL, EXIT_TPL, OFF_TPL
    RENDER_SUFFIX = suffix
    GATE_TPL = "render_L1b_person_tracking_gate_s{seed}" + suffix
    EXIT_TPL = "render_L3_person_tracking_exit_s{seed}" + suffix
    OFF_TPL = "render_L3_person_tracking_off_s{seed}" + suffix


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render-suffix", default=RENDER_SUFFIX,
                    help="渲染目录后缀：_canon（canonical 布尔掩码）/ _seg12dense / _dense（历史）")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check-off-consistency", action="store_true")
    args = ap.parse_args()
    _retemplate(args.render_suffix)
    if args.selftest:
        return run_selftest()
    if args.check_off_consistency:
        return run_off_consistency()
    return run_batch()


if __name__ == "__main__":
    raise SystemExit(main())
