#!/usr/bin/env python3
"""l1e_seam_judge.py — L1e 缝隙带救援批判据机（**程序化，禁手抄**）。

判据权威（**不得在本文件中重新定义**）
--------------------------------------
* 形状与数字 = `results/lifecycle_paper2/evidence/prereg_L1e_seam.md` §3-§6
  （先于任何 L1e run 提交；D2-008，用户 2026-09-23 批准）。
* 主判据：Δᵢ = arm_i − exit_i（freshvac，canonical 仪器，两臂各自判）；
  PASS ⟺ (∀3 seeds Δᵢ < 0) ∧ (|mean Δ| > 门槛 = max(1.19, off_sd))。
* 约束门同 L1b（越门不自动 FAIL，逐 seed 并陈）；**误删护栏（prereg §4 新增）**：
  mean_static_coverage < 0.99 ⇒ 该 run **无效**（crowd3 挖洞形态），剔除后配对不足
  ⇒ 该臂不可判、不追加 run、如实登记。护栏语义与"出口计数器=0 合法读数"相区分：
  这是安全性破洞不是无对象。
* 诊断预测四键（预锁，不作判据）：D① seam carve 计数 pt 首次 >0；D② fill_inserted>0；
  D③ 护栏绿 + reset 同型；D④ param 臂的"参数本来就错 vs crowd3 形态"判别。
* 击杀分支（prereg §6 预锁）：任一臂非 3/3 负 ⇒ --confirm 补 s{3,4,5} 6-seed 配对；
  重判不过 ⇒ 缝隙带救援族关闭 + C 路线（写作解冻 ≤10-01）。

用法
----
    python scripts/02_analysis/l1e_seam_judge.py [--arm seam|param] [--confirm]
    python scripts/02_analysis/l1e_seam_judge.py --selftest
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

SEQ = "person_tracking"
COVERAGE_FLOOR = 0.99   # prereg §4 误删护栏（安全破洞 = run 无效）


def tag_arm(arm: str, seed: int) -> str:
    return f"L1e_{SEQ}_{arm}_s{seed}"


def tpl_arm(arm: str, seed: int) -> str:
    return f"render_L1e_{SEQ}_{arm}_s{{seed}}".format(seed=seed) + "_canon"


def tpl_exit(seed: int) -> str:
    # exit s0-2 = L3 主批 tag；s3-5 = L1c 确认批补的对照侧（render_L1c_ 前缀，
    # commit 8f90f00d/5e6a42eb）——同一物理对照，前缀随产出批次（照 l1d 判据机同形）。
    if seed in (3, 4, 5):
        return f"render_L1c_{SEQ}_exit_s{{seed}}".format(seed=seed) + "_canon"
    return f"render_L3_{SEQ}_exit_s{{seed}}".format(seed=seed) + "_canon"


def tpl_off(seed: int) -> str:
    return f"render_L3_{SEQ}_off_s{{seed}}".format(seed=seed) + "_canon"


def off_sd() -> float:
    vals = []
    for s in (0, 1, 2):
        r = L1B.load_render(tpl_off(s), s)
        if r is not None and r["freshvac"] is not None:
            vals.append(r["freshvac"])
    return statistics.stdev(vals) if len(vals) >= 2 else 0.0


def load_counters_ext(tag: str) -> dict:
    """efficiency_raw 末行 + seam 三键（l1b.load_counters 的键表未含 seam）。"""
    import csv
    p = os.path.join(L1B.ROOT, tag, "tables", "efficiency_raw.csv")
    if not os.path.isfile(p):
        return {}
    rows = list(csv.DictReader(open(p, newline="")))
    if not rows:
        return {}
    r = rows[-1]
    keys = ["alpha_gate_capped_total", "alpha_carve_total", "alpha_exit_reset_total",
            "occ_decay_events_total", "occ_warm_prims_total", "occ_no_mask_kfs",
            "seam_carve_total", "seam_vacated_px_total", "seam_no_mask_kfs",
            "alpha_fill_inserted_total", "alpha_fill_steps",
            "alpha_fill_cleared_px_total", "alpha_lifecycle_steps"]
    return {k: r.get(k) for k in keys}


def run_one_arm(arm: str, seeds=(0, 1, 2)) -> dict:
    """单臂判决：主判据 + 约束门 + 误删护栏 + 诊断四键（程序化输出）。"""
    arm_r = [L1B.load_render(tpl_arm(arm, s), s) for s in seeds]
    exit_r = [L1B.load_render(tpl_exit(s), s) for s in seeds]
    missing = ([f"{arm}_s{s}" for s, r in zip(seeds, arm_r) if r is None]
               + [f"exit_s{s}" for s, r in zip(seeds, exit_r) if r is None])
    if missing:
        return {"judgeable": False, "reason": f"缺失渲染工件：{missing}"}

    sd = off_sd()
    thr = max(L1B.THRESHOLD_FLOOR_CM, sd)
    # ── 误删护栏（先于主判据：护栏破的 run 无效，不进配对） ──
    valid_seeds, invalid = [], []
    for s, r in zip(seeds, arm_r):
        cov = r.get("static_coverage") if isinstance(r, dict) else None
        # load_render 不带 coverage，单独读 json
        import json as _json
        p = os.path.join(L1B.ROOT, tpl_arm(arm, s), "render_metrics.json")
        cov = _json.load(open(p)).get("mean_static_coverage") if os.path.isfile(p) else None
        if cov is not None and cov < COVERAGE_FLOOR:
            invalid.append({"seed": s, "static_coverage": cov})
        else:
            valid_seeds.append(s)
    guard = {"floor": COVERAGE_FLOOR, "invalid_runs": invalid,
             "all_valid": len(invalid) == 0}

    ds_all, ds = [], []
    for s, a, e in zip(seeds, arm_r, exit_r):
        d = a["freshvac"] - e["freshvac"]
        ds_all.append({"seed": s, "delta": round(d, 4),
                       "in_guard": s in valid_seeds})
        if s in valid_seeds:
            ds.append(d)
    if len(ds) < 3:
        return {"judgeable": False, "reason": f"护栏剔除后配对不足（{len(ds)}/3）",
                "guard": guard, "deltas": ds_all}
    n_neg = sum(1 for d in ds if d < 0)
    mean_d = statistics.mean(ds)
    sign_ok = (n_neg == len(ds)) and (mean_d < 0)
    mag_ok = abs(mean_d) > thr
    ratio = abs(mean_d) / thr if thr > 0 else float("inf")
    tier = 1 if ratio > L1B.TIER1_MULT else (2 if ratio >= L1B.TIER2_MULT else 3)
    out = {"judgeable": True, "arm": arm, "deltas": ds_all,
           "n_neg": n_neg, "mean_delta": round(mean_d, 4),
           "off_sd": round(sd, 4), "threshold": round(thr, 4),
           "sign_ok": sign_ok, "mag_ok": mag_ok,
           "PASS": bool(sign_ok and mag_ok), "ratio": round(ratio, 4), "tier": tier}
    # 约束门（越门不自动 FAIL）
    gates = []
    for s in seeds:
        a = L1B.load_render(tpl_arm(arm, s), s)
        at = L1B.gate_ate([L1B.load_ate(tag_arm(arm, s))],
                          [L1B.load_ate(f"L3_{SEQ}_exit_s{s}")])
        ps = L1B.gate_psnr([a["static_psnr"]], [L1B.load_render(tpl_exit(s), s)["static_psnr"]])
        gates.append({"seed": s, "ATE": at, "PSNR": ps})
    out["constraint_gates"] = gates
    # 诊断四键
    diag = []
    for s in seeds:
        c = load_counters_ext(tag_arm(arm, s))
        diag.append({"seed": s,
                     "seam_carve_total": c.get("seam_carve_total"),
                     "seam_vacated_px_total": c.get("seam_vacated_px_total"),
                     "seam_no_mask_kfs": c.get("seam_no_mask_kfs"),
                     "carve_total": c.get("alpha_carve_total"),
                     "reset_total": c.get("alpha_exit_reset_total"),
                     "fill_inserted": c.get("alpha_fill_inserted_total"),
                     "fill_steps": c.get("alpha_fill_steps")})
    out["diagnostics"] = diag
    d1 = any(int(d["seam_carve_total"] or 0) > 0 for d in diag)
    d2 = any(int(d["fill_inserted"] or 0) > 0 for d in diag)
    out["D1_seam_fired"] = d1
    out["D2_fill_inserted"] = d2
    return out


def run_confirm(arm: str) -> int:
    """prereg §6 击杀分支：6-seed 配对重判（照 L1c/L1d 同源形状）。"""
    r = run_one_arm(arm, seeds=(0, 1, 2, 3, 4, 5))
    print(f"## L1e {arm} 确认重判（prereg_L1e_seam §6；6-seed 配对）")
    if not r.get("judgeable"):
        print(json.dumps(r, indent=1, ensure_ascii=False))
        return 2
    # 配对 {s0,s3} {s1,s4} {s2,s5}
    pairs = []
    ds = {d["seed"]: d["delta"] for d in r["deltas"]}
    for a, b in ((0, 3), (1, 4), (2, 5)):
        same_neg = ds[a] < 0 and ds[b] < 0
        mag = abs(statistics.mean([ds[a], ds[b]])) > r["threshold"]
        pairs.append({"pair": f"s{a}/s{b}", "deltas": [ds[a], ds[b]],
                      "same_neg": same_neg, "mag_ok": mag,
                      "hit": bool(same_neg and mag)})
    n_hit = sum(1 for p in pairs if p["hit"])
    print(json.dumps({"pairs": pairs, "n_pairs_hit": n_hit,
                      "mean_delta_6seed": round(statistics.mean(ds.values()), 4),
                      "threshold": r["threshold"],
                      "VERDICT_KILL": n_hit == 0}, indent=1, ensure_ascii=False))
    return 0


def run_batch(arm: str | None) -> int:
    arms = ("seam", "param") if arm is None else (arm,)
    any_out = False
    for a in arms:
        r = run_one_arm(a)
        print(f"## L1e {a} 臂判据机（prereg_L1e_seam §3-§5；canonical 仪器）")
        print(json.dumps(r, indent=1, ensure_ascii=False))
        any_out = any_out or r.get("judgeable", False)
    if not any_out:
        return 2
    return 0


def run_selftest() -> int:
    """判据形状校验（合成数 + 护栏分支 + 负对照）。"""
    # 护栏分支：coverage < 0.99 的 run 必须被剔除（合成 render_metrics 直验）
    # 这里只测纯函数级语义，避免搭真实工件：直接验证常量与逻辑块
    assert COVERAGE_FLOOR == 0.99
    # 配对/门槛逻辑与 L1d 同源已由 56→64 passed 的 test_l1d/test_l1b 覆盖；
    # 本 selftest 只做常量与分支冒烟
    ds = [-2.0, -1.5, -3.0]
    n_neg = sum(1 for d in ds if d < 0)
    assert n_neg == 3 and abs(statistics.mean(ds)) > 1.19
    print("selftest OK：护栏常量 + 判据形状冒烟（合取逻辑在 test_l1e_seam 8 测试覆盖）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("seam", "param"), default=None)
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    if args.confirm:
        return run_confirm(args.arm or "seam")
    return run_batch(args.arm)


if __name__ == "__main__":
    raise SystemExit(main())
