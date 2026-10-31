#!/usr/bin/env python3
"""l1f_obsdebt_judge.py — L1f 观测债补偿批判据机（**程序化，禁手抄**）。

判据权威（**不得在本文件中重新定义**）
--------------------------------------
* `results/lifecycle_paper2/evidence/prereg_L1f_obsdebt.md` §2/§2b/§3/§4（判据先锁 4d5dd720）。
* 主判据 Δ = obsdebt − exit_fill（**同管线单变量**；prereg §2）。主效果域 = **balloon2**；
  pt 族**只作 ATE/PSNR 约束门 + 点火计数诊断**，不判效（prereg §3）。
* 读法 = **跨 seed 聚合**：逐帧配对 Δ 后，逐 seed 取 median ⇒ 再取 **median-of-medians**
  + IQR；**禁单 seed 逐帧读数作判**（B0：IQR 3–7cm）。
* **PASS ⟺ median-of-medians < −1.48cm 且 ≥2/3 seed 为负**（负 = obsdebt 改善；1.48cm =
  2× 分辨力，B0 门槛）。
* 指标 = **instrument_v2 三参照**（m3 深度分层匹配为主读数参照；全域静态/邻域环并陈）
  + per-frame median/IQR（prereg §3；DISCIPLINE「测量口径」1：禁单参照 mean 作判据）。
* 击杀分支（prereg §3 预锁）：PASS=False ⇒ --confirm 6-seed 重判（配对 {s0,s3}{s1,s4}{s2,s5}）。

数据来源（工件键绑定）
----------------------
    三参照逐帧      ← instrument_v2/rescore/rescore_L1f*_canon.json（exc_full_cm/exc_ring_cm/exc_m3_cm）
    ATE             ← <runtag>/tables/tracking_raw.csv（**seed 列感知**；L1f tag 含多 seed 行）
    static PSNR/cov ← render_L1f*_canon/render_metrics.json
    基元数          ← <runtag>/tables/efficiency_raw.csv:num_gaussians（seed 感知）
    点火计数        ← <runtag>/datasets_bonn/*/seed_<s>/*/console.log（prereg §2b 三正则）

用法
----
    python scripts/02_analysis/l1f_obsdebt_judge.py                 # 主判（3 seed）+ 约束门 + 点火
    python scripts/02_analysis/l1f_obsdebt_judge.py --confirm       # 击杀分支 6-seed 重判
    python scripts/02_analysis/l1f_obsdebt_judge.py --selftest      # 合成数 + 负对照
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

REPO = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.join(REPO, "results", "lifecycle_paper2")
RESCORE_SUBDIR = os.path.join("instrument_v2", "rescore")

# ── 判据常量（prereg §3/§4；改这里即改判据 ⇒ 禁止，除非 prereg 修正案）──
THRESHOLD_CM = 1.48        # 2× 分辨力（B0 §2/§4；负方向 = obsdebt 改善）
PSNR_GATE_DB = -0.65       # D1-014 M6 修订界
ATE_GATE_REL = 0.05        # prereg §4：ΔATE ≤ +5%（vs off）
ATE_SINGLE_MAX_REL = 0.10  # prereg §4：逐 seed 无 >+10% 单点
COVERAGE_FLOOR = 0.99      # 护栏（L1e 同款）：破 = run 无效
PRIM_INFLATION_MAX = 0.80  # 预算上限：基元数膨胀 ≤ +80%

# 主参照（prereg §3：m3 为主读数参照）；三参照键
REFS = ["m3", "full", "ring"]
PRIMARY_REF = "m3"
RESCORE_JKEY = {"m3": "exc_m3_cm", "full": "exc_full_cm", "ring": "exc_ring_cm"}

SEEDS_MAIN = [0, 1, 2]
SEEDS_CONFIRM = [0, 1, 2, 3, 4, 5]

# 渲染 tag 模板（后缀 _canon 由 _suffix 拼接）
MAIN_RTAG = "L1f2_balloon2_obsdebt_s{seed}"
CTRL_RTAG = "L1f_balloon2_exitfill_ctrl_s{seed}"
PT_RTAG = "L1f_person_tracking_obsdebt_s{seed}"
# run tag（tag 级 tables；L1f 一 tag 含多 seed；s3-5 由击杀分支补训入同一 run tag）
MAIN_RUNTAG = "L1f2_balloon2_obsdebt"
CTRL_RUNTAG = "L1f_balloon2_balloon2_exitfill_ctrl"
PT_RUNTAG = "L1f_person_tracking_person_tracking_obsdebt"
RENDER_SUFFIX = "_canon"


# ────────────────────────────── 工件定位 ──────────────────────────────
def _rescore_path(rtag: str) -> str:
    return os.path.join(ROOT, RESCORE_SUBDIR, f"rescore_{rtag}{RENDER_SUFFIX}.json")


def load_rescore_frames(rtag: str) -> dict | None:
    """逐帧三参照：{frame: {m3, full, ring}}（None-safe）。缺文件 → None。"""
    p = _rescore_path(rtag)
    if not os.path.isfile(p):
        return None
    d = json.load(open(p))
    out = {}
    for f in d.get("per_frame", []):
        fr = f.get("frame")
        if fr is None:
            continue
        out[fr] = {k: f.get(RESCORE_JKEY[k]) for k in REFS}
    return out


def load_rescore_meta(rtag: str) -> dict:
    p = _rescore_path(rtag)
    if not os.path.isfile(p):
        return {}
    d = json.load(open(p))
    return {"band_used": d.get("band_used"), "support_px_median": d.get("support_px_median") or {}}


def _run_dirs(runtag: str, seed: int) -> list[str]:
    pat = os.path.join(ROOT, runtag, "datasets_bonn", "*", f"seed_{seed}", "*")
    return sorted(p for p in glob.glob(pat) if os.path.isdir(p))


def run_dir_of(runtag: str, seed: int) -> str | None:
    hits = _run_dirs(runtag, seed)
    return hits[-1] if hits else None


def find_in_run(run: str, *alts) -> str | None:
    for a in alts:
        p = os.path.join(run, a)
        if os.path.exists(p):
            return p
    return None


def _seed_rows(csv_path: str) -> dict[int, dict]:
    """读 tag 级 tables CSV（含多 seed 行）→ {seed: row}。

    ⚠ 关键：L1f 的一 tag 含 3（或 6）seed 行（seed 在第 4 列）；**禁**照抄 l1b 的
    `rows[-1]`（那只读末行 = 单 seed）。种子列缺失时退化为单行 seed=0。
    """
    if not os.path.isfile(csv_path):
        return {}
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))
    out: dict[int, dict] = {}
    for i, r in enumerate(rows):
        s = r.get("seed")
        try:
            sd = int(float(s)) if s not in (None, "") else i
        except (TypeError, ValueError):
            sd = i
        out[sd] = r          # 同 seed 重复时后者覆盖（异常情形，可判性由计数暴露）
    return out


def load_ate(tag: str) -> dict[int, float]:
    """{seed: ate_rmse_cm}（seed 感知）。"""
    rows = _seed_rows(os.path.join(ROOT, tag, "tables", "tracking_raw.csv"))
    out = {}
    for sd, r in rows.items():
        v = r.get("ate_rmse_cm")
        if v not in (None, "", "nan"):
            try:
                out[sd] = float(v)
            except (TypeError, ValueError):
                pass
    return out


def load_num_gaussians(tag: str) -> dict[int, int]:
    rows = _seed_rows(os.path.join(ROOT, tag, "tables", "efficiency_raw.csv"))
    out = {}
    for sd, r in rows.items():
        v = r.get("num_gaussians")
        if v not in (None, ""):
            try:
                out[sd] = int(float(v))
            except (TypeError, ValueError):
                pass
    return out


def load_render_metrics(rtag: str) -> dict | None:
    p = os.path.join(ROOT, f"render_{rtag}{RENDER_SUFFIX}", "render_metrics.json")
    if not os.path.isfile(p):
        return None
    m = json.load(open(p))
    return {
        "static_psnr": m.get("mean_static_psnr"),
        "static_coverage": m.get("mean_static_coverage"),
        "n_frames": m.get("n_frames"),
        "mask_validity": m.get("mask_validity"),
        "mask_source": m.get("mask_source"),
        "online_num_gaussians": m.get("online_num_gaussians"),
        "dir": os.path.dirname(p),
    }


# ────────────────────────────── 点火计数（prereg §2b）──────────────────────────────
FIRING_PATTERNS = {
    # ① 账本增长：obsdebt KF <uid>: ... total=<int>
    "ledger_lines": re.compile(r"obsdebt KF \d+: .*total=(\d+)"),
    # ② 预算重分配：obsdebt-fill KF <uid>: ... kept=<int>
    "fill_lines": re.compile(r"obsdebt-fill KF \d+: .*kept=(\d+)"),
    # ③ 迭代配额：obsdebt-boost KF <uid>: ... extra_steps=<1..9>（不含 SKIP/skipped 两种字面）
    "boost_lines": re.compile(r"obsdebt-boost KF \d+: .*extra_steps=([1-9]\d*)"),
    # ② 结构性证据：两条分支的 vacated 事件规模（prereg §2b 已知风险条款）
    "vacated": re.compile(r"vacated=(\d+)"),
    "alpha_fill": re.compile(r"alpha-fill .*?inserted=(\d+)"),
}


def count_firing(console_path: str) -> dict:
    """按 prereg §2b 三正则提取点火计数；附账本 total 单调性与 vacated 峰值。"""
    if not console_path or not os.path.isfile(console_path):
        return {"present": False}
    led, boost, totals = 0, 0, []
    fill_kept, vac = [], []
    with open(console_path, errors="replace") as f:
        for line in f:
            m = FIRING_PATTERNS["ledger_lines"].search(line)
            if m:
                led += 1
                totals.append(int(m.group(1)))
            m = FIRING_PATTERNS["fill_lines"].search(line)
            if m:
                fill_kept.append(int(m.group(1)))
            if FIRING_PATTERNS["boost_lines"].search(line):
                boost += 1
            m = FIRING_PATTERNS["vacated"].search(line)
            if m:
                vac.append(int(m.group(1)))
    increasing = all(b >= a for a, b in zip(totals, totals[1:])) if len(totals) >= 2 else False
    return {
        "present": True,
        "ledger_lines": led,                        # ①
        "ledger_total_max": max(totals) if totals else 0,
        "ledger_monotone": increasing,
        "fill_lines": len(fill_kept),               # ②
        "fill_kept_total": sum(fill_kept),
        "fill_kept_max": max(fill_kept) if fill_kept else 0,
        "boost_lines": boost,                       # ③
        "vacated_max_px": max(vac) if vac else None,  # ② 结构性证据
    }


def firing_of(runtag: str, seed: int) -> dict:
    run = run_dir_of(runtag, seed)
    if run is None:
        return {"present": False, "reason": "no run dir"}
    c = count_firing(find_in_run(run, "console.log"))
    # 点火合格 = ①在增长 或 ②kept>0 或 ③boost>0 任一非零（prereg §2b）
    fired = bool(c.get("ledger_lines")) or bool(c.get("fill_kept_total")) or bool(c.get("boost_lines"))
    c["FIRING"] = "yes" if fired else "none"
    return c


# ────────────────────────────── 纯判据（可单测）──────────────────────────────
def paired_frames(a: dict, b: dict, ref: str) -> tuple[list[float], list[int]]:
    """同帧集配对 Δ = a − b（逐帧，两臂该帧该参照均有效才计）。"""
    diffs, frames = [], []
    for fr in sorted(set(a) & set(b)):
        va, vb = a[fr].get(ref), b[fr].get(ref)
        if va is None or vb is None:
            continue
        diffs.append(va - vb)
        frames.append(fr)
    return diffs, frames


def med_iqr(xs: list[float]) -> dict | None:
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    med = statistics.median(s)
    q1 = s[max(0, int(round(0.25 * (n - 1))))] if n > 1 else s[0]
    q3 = s[min(n - 1, int(round(0.75 * (n - 1))))] if n > 1 else s[0]
    return {"median": round(med, 4), "iqr": [round(q1, 4), round(q3, 4)], "n": n}


def median_of_medians(seed_deltas: dict[int, list[float]]) -> dict:
    """prereg §3 跨 seed 聚合：逐 seed median → median-of-medians（+ across-seed IQR）。"""
    per_seed = {sd: med_iqr(v) for sd, v in seed_deltas.items() if v}
    meds = [x["median"] for x in per_seed.values() if x]
    if not meds:
        return {"judgeable": False, "reason": "无可用 seed 配对"}
    mom = statistics.median(meds)
    s = sorted(meds)
    n = len(s)
    q1 = s[max(0, int(round(0.25 * (n - 1))))] if n > 1 else s[0]
    q3 = s[min(n - 1, int(round(0.75 * (n - 1))))] if n > 1 else s[0]
    n_neg = sum(1 for m in meds if m < 0)
    return {
        "judgeable": True,
        "per_seed": {str(k): v for k, v in per_seed.items()},
        "seed_medians": [round(m, 4) for m in meds],
        "median_of_medians": round(mom, 4),
        "across_seed_iqr": [round(q1, 4), round(q3, 4)],
        "n_neg": n_neg, "n_seed": len(meds),
        "n_neg_ratio": f"{n_neg}/{len(meds)}",
    }


def judge_main(seed_deltas: dict[int, list[float]], threshold: float = THRESHOLD_CM) -> dict:
    """prereg §3 主判据：PASS ⟺ median-of-medians < −threshold 且 ≥2/3 seed 为负。"""
    agg = median_of_medians(seed_deltas)
    if not agg.get("judgeable"):
        return agg
    mom = agg["median_of_medians"]
    need = (2 * agg["n_seed"] + 2) // 3     # 3 seed → 2；6 seed → 4（≥2/3）
    sign_ok = agg["n_neg"] >= need and mom < 0
    mag_ok = mom < -threshold
    return {
        **agg,
        "threshold": threshold,
        "sign_ok": bool(sign_ok),
        "mag_ok": bool(mag_ok),
        "PASS": bool(sign_ok and mag_ok),
    }


def leave_one_seed_out(seed_deltas: dict[int, list[float]],
                       threshold: float = THRESHOLD_CM) -> dict:
    """**诊断（不作判据）**：逐 seed 留一后重施加 prereg §3 形状，暴露 PASS 的脆弱性。

    判据本体不变（仍见 judge_main）；本函数只回答"结论对单个 seed 的依赖度"。
    逐 seed median（固定）、跨 seed 散布、以及 n−1 子集里 PASS 的个数。
    """
    per = {sd: med_iqr(v) for sd, v in seed_deltas.items() if v}
    meds = {sd: x["median"] for sd, x in per.items() if x}
    if len(meds) < 2:
        return {"available": False}
    loo = {}
    n_pass = 0
    for drop in sorted(meds):
        sub = {sd: [m] for sd, m in meds.items() if sd != drop}
        j = judge_main(sub, threshold)
        loo[str(drop)] = {"mom": j.get("median_of_medians"),
                          "n_neg_ratio": j.get("n_neg_ratio"),
                          "PASS": j.get("PASS")}
        n_pass += int(bool(j.get("PASS")))
    vals = sorted(meds.values())
    return {
        "available": True,
        "seed_medians": {str(k): round(v, 4) for k, v in sorted(meds.items())},
        "min": round(vals[0], 4), "max": round(vals[-1], 4),
        "across_seed_spread": round(vals[-1] - vals[0], 4),
        "n_sign_flips": sum(1 for v in vals if v > 0),
        "loo": loo,
        "loo_pass_count": f"{n_pass}/{len(meds)}",
        "note": "PASS 对单 seed 的依赖度；仅诊断，不替代 judge_main。",
    }


def is_judgeable(rescore_a: dict, rescore_b: dict, min_frac: float = 0.5) -> tuple[bool, dict]:
    """DISCIPLINE「测量口径」2（可判性先于判效）：任一参照在两臂共同帧上可用帧 < 50%
    共同帧，或该帧集为空 ⇒ 不可判（不是"未通过"）。"""
    common = sorted(set(rescore_a) & set(rescore_b))
    diag = {"n_common_frames": len(common), "per_ref_available": {}}
    if not common:
        return False, diag
    ok = True
    for ref in REFS:
        avail = sum(1 for fr in common
                    if rescore_a[fr].get(ref) is not None and rescore_b[fr].get(ref) is not None)
        diag["per_ref_available"][ref] = f"{avail}/{len(common)}"
        if avail < min_frac * len(common):
            ok = False
    return ok, diag


def gate_ate(main_ate: dict[int, float], off_ate: dict[int, float],
             seeds: list[int]) -> dict:
    """prereg §4：ΔATE ≤ +5%（vs off）且逐 seed 无 >+10% 单点。"""
    per = []
    for sd in seeds:
        a, b = main_ate.get(sd), off_ate.get(sd)
        if a is None or b is None or not b:
            per.append({"seed": sd, "rel": None})
            continue
        per.append({"seed": sd, "ate": round(a, 4), "off": round(b, 4),
                    "rel": round((a - b) / b, 4)})
    rels = [p["rel"] for p in per if p["rel"] is not None]
    if not rels:
        return {"ok": None, "reason": "无 ATE 配对", "per_seed": per}
    mean_rel = statistics.mean(rels)
    single_ok = all(r <= ATE_SINGLE_MAX_REL for r in rels)
    return {"ok": bool(mean_rel <= ATE_GATE_REL and single_ok),
            "mean_rel": round(mean_rel, 4),
            "max_rel": round(max(rels), 4),
            "single_ok": bool(single_ok),
            "per_seed": per}


def gate_psnr(arm_ps: list[tuple[int, float]], base_ps: list[tuple[int, float]]) -> dict:
    """canon 口径 Δ ≥ −0.65dB（arm − base，逐 seed 均值）。"""
    b = {s: v for s, v in base_ps if v is not None}
    pairs = [(v, b[s]) for s, v in arm_ps if v is not None and s in b]
    if not pairs:
        return {"ok": None, "reason": "无 PSNR 配对"}
    base = statistics.mean(x for _, x in pairs)
    if not (8.0 <= base <= 60.0):
        raise AssertionError(f"static PSNR 基值 {base:.3f} dB 不在 [8,60] —— 喂错指标（量纲护栏）")
    d = statistics.mean(a - x for a, x in pairs)
    return {"ok": bool(d >= PSNR_GATE_DB), "delta_db": round(d, 4), "base_db": round(base, 4)}


def guard_coverage(covs: list[tuple[int, float | None]]) -> dict:
    bad = [{"seed": s, "coverage": c} for s, c in covs if c is not None and c < COVERAGE_FLOOR]
    return {"floor": COVERAGE_FLOOR, "invalid_runs": bad, "all_valid": not bad}


def guard_prim(main_g: dict[int, int], ctrl_g: dict[int, int]) -> dict:
    infl = {}
    for sd, v in main_g.items():
        b = ctrl_g.get(sd)
        if b:
            infl[sd] = (v - b) / b
    if not infl:
        return {"ok": None, "reason": "无基元数配对"}
    worst = max(infl.values())
    return {"ok": bool(worst <= PRIM_INFLATION_MAX),
            "per_seed_inflation": {str(k): round(v, 4) for k, v in infl.items()},
            "worst": round(worst, 4), "limit": PRIM_INFLATION_MAX}


# ────────────────────────────── 臂装配 ──────────────────────────────
def _arm_rescore(rtag_tpl: str, seeds: list[int]) -> dict:
    """{seed: 逐帧三参照}；缺文件 → None。s3-5 与 s0-2 用同一模板（种子进模板）。"""
    return {sd: load_rescore_frames(rtag_tpl.format(seed=sd)) for sd in seeds}


def mechanism_active_seeds(runtag: str, seeds: list[int]) -> tuple[list[int], list[int]]:
    """**诊断**：按点火计数把 seed 分为「机制实际动作」与「机制零动作」两集。

    机制动作 = ② fill kept>0 或 ③ boost>0（① 账本记账不改变优化，不算"动作"）。
    用途：回答"观测到的 Δ 是否可归因于机制"——若负号只出现在零动作 seed，
    则 PASS 是噪声而非机制效应（关卡① 致命项）。
    """
    active, idle = [], []
    for sd in seeds:
        f = firing_of(runtag, sd)
        acted = bool(f.get("fill_kept_total")) or bool(f.get("boost_lines"))
        (active if acted else idle).append(sd)
    return active, idle


def judge_balloon2(seeds: list[int]) -> dict:
    """balloon2 主效果域：Δ = obsdebt − exit_fill（同管线单变量）。"""
    main = _arm_rescore(MAIN_RTAG, seeds)
    ctrl = _arm_rescore(CTRL_RTAG, seeds)
    missing = [f"main_s{s}" for s in seeds if main.get(s) is None]
    missing += [f"ctrl_s{s}" for s in seeds if ctrl.get(s) is None]
    if missing:
        return {"judgeable": False, "reason": f"缺失重评分工件：{missing}"}

    per_ref: dict[str, dict[int, list[float]]] = {r: {} for r in REFS}
    judgeability = {}
    # 误删护栏（prereg §4）：static_coverage < 0.99 ⇒ run 无效（剔除出配对）
    coverage = {}
    excluded = []
    for sd in seeds:
        mm = load_render_metrics(MAIN_RTAG.format(seed=sd))
        cc = load_render_metrics(CTRL_RTAG.format(seed=sd))
        covs = [x["static_coverage"] for x in (mm, cc) if x and x.get("static_coverage") is not None]
        coverage[sd] = covs
        if any(c < COVERAGE_FLOOR for c in covs):
            excluded.append(sd)

    valid = [sd for sd in seeds if sd not in excluded]
    if len(valid) < len(seeds):
        seeds_used = valid
    else:
        seeds_used = seeds
    for sd in seeds_used:
        okj, diag = is_judgeable(main[sd], ctrl[sd])
        judgeability[sd] = {"judgeable": okj, **diag}
        for ref in REFS:
            d, _ = paired_frames(main[sd], ctrl[sd], ref)
            per_ref[ref][sd] = d

    primary = judge_main(per_ref[PRIMARY_REF])
    # 归因诊断（**不作判据**）：限机制实际动作的 seed 重施加 prereg §3 形状
    act, idle = mechanism_active_seeds(MAIN_RUNTAG, seeds_used)
    attribution = None
    if act and idle:
        attribution = {
            "active_seeds": act, "idle_seeds": idle,
            "note": ("若负号集中于零动作 seed ⇒ Δ 不可归因于机制。"
                     "active = ② fill kept>0 或 ③ boost>0。"),
            "refs": {r: judge_main({sd: per_ref[r][sd] for sd in act if sd in per_ref[r]})
                     for r in REFS},
        }
    out = {
        "domain": "balloon2",
        "judgeable": True,
        "primary_ref": PRIMARY_REF,
        "delta_definition": "obsdebt(L1f2) − exit_fill_ctrl(L1f)；同管线单变量（prereg §2）",
        "judgeability": judgeability,
        "coverage_guard": {"floor": COVERAGE_FLOOR, "excluded_seeds": excluded,
                           "per_seed_coverage": {str(k): v for k, v in coverage.items()}},
        "seeds_used": seeds_used,
        "primary": primary,
        # 诊断（不作判据）：PASS 对单 seed 的依赖度与跨 seed 散布
        "primary_robustness": leave_one_seed_out(per_ref[PRIMARY_REF]),
        # 诊断（不作判据）：限机制实际动作 seed 的读数（可归因性）
        "mechanism_attribution": attribution,
        # 三参照并陈（prereg §3：m3 主读数，全域静态/邻域环并陈）
        "refs": {r: median_of_medians(per_ref[r]) for r in REFS},
        "refs_robustness": {r: leave_one_seed_out(per_ref[r]) for r in REFS},
    }
    # 可判性护栏：主参照若不可判 ⇒ 记不可判（不改判据，只封判效资格）
    if not all(v["judgeable"] for v in judgeability.values()):
        out["PRIMARY_JUDGEABLE"] = False
    else:
        out["PRIMARY_JUDGEABLE"] = True
    out["PASS"] = bool(primary.get("PASS")) and out["PRIMARY_JUDGEABLE"]
    return out


def judge_pt_constraint(seeds: list[int]) -> dict:
    """pt 只作约束门 + 点火诊断（prereg §3；不判效）。"""
    pt_ate = load_ate(PT_RUNTAG)
    off_ate = _off_ate("person_tracking", seeds)
    at = gate_ate(pt_ate, off_ate, seeds)
    pt_ps, off_ps = [], []
    for sd in seeds:
        m = load_render_metrics(PT_RTAG.format(seed=sd))
        pt_ps.append((sd, m["static_psnr"] if m else None))
        mo = load_render_metrics(f"L3_person_tracking_off_s{sd}")
        off_ps.append((sd, mo["static_psnr"] if mo else None))
    ps = gate_psnr(pt_ps, off_ps)
    return {"domain": "person_tracking", "role": "constraint-only (prereg §3)",
            "ATE": at, "PSNR": ps}


def _off_ate(seq: str, seeds: list[int]) -> dict[int, float]:
    """off 基准 ATE：L3 的 off tag 为**单 seed 一 tag**（_s{N}），逐 seed 读该 tag。"""
    out = {}
    for sd in seeds:
        v = load_ate(f"L3_{seq}_off_s{sd}")
        if sd in v:
            out[sd] = v[sd]
        elif v:                      # 兜底：单行无 seed 列
            out[sd] = next(iter(v.values()))
    return out


def collect_firing(runtag: str, seeds: list[int]) -> dict:
    return {sd: firing_of(runtag, sd) for sd in seeds}


# ────────────────────────────── 主批 ──────────────────────────────
def run_batch(confirm: bool = False) -> int:
    seeds = SEEDS_CONFIRM if confirm else SEEDS_MAIN
    print(f"## L1f obsdebt 判据机（prereg_L1f_obsdebt §2/§2b/§3/§4；instrument_v2 三参照）")
    print(f"- 读法：Δ = obsdebt − exit_fill（同帧集配对）→ 逐 seed median → **median-of-medians**；"
          f"门槛 {THRESHOLD_CM}cm（负 = obsdebt 改善）")
    print(f"- seeds = {seeds}{'（--confirm 击杀分支）' if confirm else ''}；后缀 = {RENDER_SUFFIX}\n")

    b2 = judge_balloon2(seeds)
    print("## 1. 主效果域 balloon2（prereg §3 主判据）")
    print(json.dumps(b2, indent=1, ensure_ascii=False))

    # 约束门 + 护栏（balloon2）
    off_ate = _off_ate("balloon2", seeds)
    main_ate = load_ate(MAIN_RUNTAG)
    at = gate_ate(main_ate, off_ate, seeds)
    main_ps, ctrl_ps, covs = [], [], []
    for sd in seeds:
        mm = load_render_metrics(MAIN_RTAG.format(seed=sd))
        cc = load_render_metrics(CTRL_RTAG.format(seed=sd))
        main_ps.append((sd, mm["static_psnr"] if mm else None))
        ctrl_ps.append((sd, cc["static_psnr"] if cc else None))
        covs.append((sd, mm["static_coverage"] if mm else None))
    ps = gate_psnr(main_ps, ctrl_ps)
    cov = guard_coverage(covs)
    prim = guard_prim(load_num_gaussians(MAIN_RUNTAG), load_num_gaussians(CTRL_RUNTAG))

    print("## 2. 约束门 + 护栏（balloon2）")
    print(f"ATE (vs off):          {json.dumps(at, ensure_ascii=False)}")
    # 补充诊断（**不参与判据**）：同批单变量对照的 ATE——off 是 L3 批（跨批），
    # 「比较前提」5 要求跨批须等价门；此处并陈同批 exit_fill_ctrl 的读数供一致性核对。
    at_ctrl = gate_ate(load_ate(MAIN_RUNTAG), load_ate(CTRL_RUNTAG), seeds)
    print(f"ATE (vs exit_fill, 同批·补充非判据): {json.dumps(at_ctrl, ensure_ascii=False)}")
    print(f"static PSNR (vs ctrl): {json.dumps(ps, ensure_ascii=False)}")
    print(f"coverage guard:        {json.dumps(cov, ensure_ascii=False)}")
    print(f"primitive budget:      {json.dumps(prim, ensure_ascii=False)}\n")

    print("## 3. 约束域 person_tracking（只作约束门 + 点火诊断，不判效）")
    pt = judge_pt_constraint(seeds)
    print(json.dumps(pt, indent=1, ensure_ascii=False))

    print("\n## 4. 点火计数（prereg §2b 三正则；零点火 = run 无效）")
    fire_main = collect_firing(MAIN_RUNTAG, seeds)
    fire_ctrl = collect_firing(CTRL_RUNTAG, seeds)
    fire_pt = collect_firing(PT_RUNTAG, seeds)
    print(f"主臂 balloon2:  {json.dumps(fire_main, ensure_ascii=False)}")
    print(f"对照 balloon2:  {json.dumps(fire_ctrl, ensure_ascii=False)}")
    print(f"约束域 pt:      {json.dumps(fire_pt, ensure_ascii=False)}")

    # 汇总判定
    print("\n## 5. 判定汇总")
    rob = b2.get("primary_robustness", {})
    attr = b2.get("mechanism_attribution") or {}
    attr_primary = (attr.get("refs", {}).get(PRIMARY_REF) or {}) if attr else {}
    prereg_pass = b2.get("PASS")
    # 可归因性：机制实际动作 seed 子集上主参照是否仍 PASS
    attributable_pass = attr_primary.get("PASS") if attr_primary else None
    verdict = {
        # 一、prereg §3 的机械应用（判据本体，不改）
        "prereg_mechanical_PASS": prereg_pass,
        "primary_median_of_medians": b2.get("primary", {}).get("median_of_medians"),
        "threshold": THRESHOLD_CM,
        "n_neg_ratio": b2.get("primary", {}).get("n_neg_ratio"),
        # 二、可归因性诊断（关卡① 致命项：负号是否只落在机制零动作 seed）
        "attributable_readings": {
            "active_seeds": attr.get("active_seeds"),
            "idle_seeds": attr.get("idle_seeds"),
            "active_only_mom": attr_primary.get("median_of_medians"),
            "active_only_n_neg": attr_primary.get("n_neg_ratio"),
            "active_only_PASS": attributable_pass,
        },
        "attribution_ok": (attributable_pass is True) if attributable_pass is not None else None,
        # 三、脆弱性诊断
        "robustness": {
            "seed_medians": rob.get("seed_medians"),
            "across_seed_spread": rob.get("across_seed_spread"),
            "loo_pass_count": rob.get("loo_pass_count"),
            "n_sign_flips": rob.get("n_sign_flips"),
        },
        # 四、约束门 / 护栏（balloon2）
        "constraint_ATE_ok": at.get("ok"),
        "constraint_PSNR_ok": ps.get("ok"),
        "coverage_guard_ok": cov.get("all_valid"),
        "prim_budget_ok": prim.get("ok"),
        "prim_worst_inflation": prim.get("worst"),
        "firing_main_any": any(v.get("FIRING") == "yes" for v in fire_main.values()),
    }
    print(json.dumps(verdict, indent=1, ensure_ascii=False))

    # 终判：prereg 机械 PASS 但不可归因 ⇒ 判 PASS 不成立（如实，不改判据本体）
    if prereg_pass and attributable_pass is False:
        final = "PASS不成立（机械 PASS 不可归因于机制：负号集中于零动作 seed）"
    elif prereg_pass:
        final = "PASS"
    else:
        final = "FAIL"
    print(f"\n终判：{final}")
    if confirm:
        print(f"VERDICT_KILL = {final != 'PASS'}"
              f"  （非 PASS ⇒ 观测债族按 R2 关闭/立判，prereg §3）")
    return 0 if b2.get("judgeable") else 2


# ────────────────────────────── 自测 ──────────────────────────────
def run_selftest() -> int:
    # 主判据形状：三 seed 全负、幅度足够 ⇒ PASS
    good = {0: [-2.0, -1.0, -3.0], 1: [-1.6, -2.2, -1.8], 2: [-1.9, -2.5, -1.5]}
    m = judge_main(good)
    assert m["PASS"] is True and m["n_neg"] == 3, m
    assert m["median_of_medians"] < -THRESHOLD_CM
    # 负对照 1：对调两臂（Δ 全正）⇒ PASS 必 False
    m_sw = judge_main({s: [-x for x in v] for s, v in good.items()})
    assert m_sw["PASS"] is False and m_sw["n_neg"] == 0, m_sw
    # 负对照 2：同号但幅度不足（< 1.48）⇒ False
    m_small = judge_main({0: [-0.4, -0.5], 1: [-0.3, -0.6], 2: [-0.5, -0.2]})
    assert m_small["PASS"] is False and m_small["sign_ok"] and not m_small["mag_ok"], m_small
    # 负对照 3：仅 1/3 seed 为负（方向不一致）⇒ False
    m_mixed = judge_main({0: [-2.0, -1.8], 1: [1.5, 2.0], 2: [1.2, 1.9]})
    assert m_mixed["PASS"] is False and m_mixed["n_neg"] == 1, m_mixed
    # 可判性：某参照可用帧 < 50% ⇒ 不可判
    a = {i: {"m3": 1.0, "full": 1.0, "ring": 1.0} for i in range(10)}
    b = {i: {"m3": 1.0, "full": 1.0, "ring": 1.0} for i in range(10)}
    okj, _ = is_judgeable(a, b)
    assert okj is True
    b2 = dict(b)
    b2[9] = {"m3": None, "full": 1.0, "ring": 1.0}   # 仍 9/10 ≥ 50%
    assert is_judgeable(a, b2)[0] is True
    b3 = {i: {"m3": None, "full": 1.0, "ring": 1.0} for i in range(10)}
    assert is_judgeable(a, b3)[0] is False            # m3 0/10 < 50%
    # 点火正则：只认 fired 形态（不误吞 SKIP/skipped）
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as fh:
        fh.write("MonoGS: obsdebt KF 50: masked_px=1 voxels=1 table=1 total=1\n")
        fh.write("MonoGS: obsdebt KF 55: masked_px=1 voxels=1 table=2 total=7\n")
        fh.write("MonoGS: obsdebt-boost KF 95: new=1 d_hat_mean=1.000 extra_steps=5 opt=independent-adam\n")
        fh.write("MonoGS: obsdebt-boost KF 100: SKIP -- ledger absent (obsdebt on but no debt recorded yet)\n")
        fh.write("MonoGS: obsdebt-boost skipped: element 0 of tensors does not require grad\n")
        fh.write("MonoGS: obsdebt-fill KF 60: vacated=10 kept=4 dropped=6 debt_max=3\n")
        path = fh.name
    c = count_firing(path)
    os.unlink(path)
    assert c["ledger_lines"] == 2 and c["ledger_monotone"] is True, c
    assert c["boost_lines"] == 1, c               # SKIP/skipped 不计
    assert c["fill_lines"] == 1 and c["fill_kept_total"] == 4, c
    print(f"selftest OK：mom={m['median_of_medians']:.3f} PASS=True；对调 PASS={m_sw['PASS']}；"
          f"幅度不足 PASS={m_small['PASS']}；方向不一致 PASS={m_mixed['PASS']}；"
          f"点火正则 boost={c['boost_lines']} fill_kept={c['fill_kept_total']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true",
                    help="6-seed 击杀分支重判（prereg §3）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    return run_batch(confirm=args.confirm)


if __name__ == "__main__":
    raise SystemExit(main())
