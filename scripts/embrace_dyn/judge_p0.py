#!/usr/bin/env python
"""P0 embrace_online 判据机（prereg_P0_embrace_online.md §4；程序化产出，禁手抄）。

输入：一或两份 (cmd_render 产物 JSON, 探针 config YAML)——每份 config 一个序列
（pt2 主域 / balloon 泛化，tag 区分图）。
输出：online_judgments JSON——J1–J8 逐条读数（median+IQR）+ 出口判定
（PASS / 边界 / FAIL / VOID）。

口径（与 prereg §4 逐条对应）：
- 配对 = 因果可评帧（> t0、两侧臂都有指标）上逐帧求差/比，再取 median/IQR（测量口径 #1）。
- 主域 config（sequence ≠ generality_sequence）= J1/J2/J3/J4/J7/J8 判定域；
  泛化 config（sequence == generality_sequence，即 balloon）= J5 域。
- 出口（prereg §4）：PASS / 边界 / FAIL / VOID（阴性对照通过主判 ⇒ 仪器无效整批作废）。
  操作化补注（D1 机械解释，判决书须引用）：主域图"不可判"（J6）⇒ FAIL；泛化图"不可判"
  ⇒ PASS 不可达、最高出口 = 边界（prereg FAIL 行的"J6 不可判"按主域解释）。

用法：
  python scripts/embrace_dyn/judge_p0.py \
    --results results/embrace_online/evidence/p0_probe_pt2_results.json \
              results/embrace_online/evidence/p0_probe_balloon_results.json \
    --config  configs/experiments/embrace_online/probe_pt2_online.yaml \
              configs/experiments/embrace_online/probe_balloon_online.yaml \
    --out results/embrace_online/evidence/p0_online_judgments.json
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("dyn_probe", REPO / "scripts/02_analysis/dyn_probe.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

MAIN_PASS_DB = 2.5      # J1（prereg §4，先锁）
BOUND_LO_DB = 1.0       # 边界下界 = 判据的 40%
STATIC_GATE_DB = -0.65  # J3（prereg §4）
COST_LINE = 0.15        # J4 成本登记线
CTRL_RATIO_MIN = 1.15   # J7 阴性对照判别力（历史四轮同阈）


def _med_iqr(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    if not xs:
        return None, None, 0
    a = np.asarray(xs, dtype=float)
    return (round(float(np.median(a)), 4),
            round(float(np.percentile(a, 75) - np.percentile(a, 25)), 4), len(a))


def _paired(recs_a, recs_b):
    """按帧配对两臂记录（双方都有 dyn_bad_psnr 才计入）。"""
    b = {r["frame"]: r for r in recs_b if r.get("dyn_bad_psnr") is not None}
    out = []
    for r in sorted((r for r in recs_a if r.get("dyn_bad_psnr") is not None),
                    key=lambda r: r["frame"]):
        if r["frame"] in b:
            out.append((r, b[r["frame"]]))
    return out


def judge_map(per_arm, meta, t0, domain):
    """单图（tag）读数：J1–J6 + J7（若有 C-o）+ P2 oracle 锚。"""
    p1 = [r for r in per_arm.get("P1", []) if r.get("frame", 0) > t0]
    out = {"domain": domain, "n_causal_frames_p1": len([r for r in p1 if r.get("dyn_bad_psnr") is not None])}
    pairs = _paired(per_arm.get("P0o", []), p1)
    out["n_paired"] = len(pairs)
    if not pairs:
        out.update({"j6_judgeable": False, "note": "无配对帧"})
        return out
    d_psnr = [a["dyn_bad_psnr"] - b["dyn_bad_psnr"] for a, b in pairs]
    d_stat = [a["static_psnr"] - b["static_psnr"] for a, b in pairs
              if a.get("static_psnr") is not None and b.get("static_psnr") is not None]
    ratios_dl1 = [a["dyn_bad_dl1_cm"] / b["dyn_bad_dl1_cm"] for a, b in pairs
                  if a.get("dyn_bad_dl1_cm") is not None and b.get("dyn_bad_dl1_cm") and
                  b["dyn_bad_dl1_cm"] > 0]
    j1m, j1i, _ = _med_iqr(d_psnr)
    j3m, j3i, _ = _med_iqr(d_stat)
    j2m, j2i, n2 = _med_iqr(ratios_dl1)
    bad_px = [b["dyn_bad_px"] for _a, b in pairs]
    sup_frac = round(sum(1 for x in bad_px if x > 0) / len(bad_px), 4)
    n_dyn_max = max(int(a.get("n_dyn", 0)) for a, _ in pairs)
    out.update({
        "j1_bad_psnr_delta": {"median": j1m, "iqr": j1i},
        "j2_bad_dl1_ratio": {"median": j2m, "iqr": j2i, "n": n2},
        "j3_static_delta": {"median": j3m, "iqr": j3i},
        "j4_cost": {"n_dyn_max": n_dyn_max, "n_static": meta.get("n_static"),
                    "frac": (None if not meta.get("n_static")
                             else round(n_dyn_max / meta["n_static"], 4))},
        "j6_judgeable": bool(sup_frac >= 0.5 and float(np.median(bad_px)) > 0),
        "j6_support_frac": sup_frac,
        "j6_bad_px_median": float(np.median(bad_px)),
    })
    ctrl = _paired(per_arm.get("C-o", []), p1)
    if ctrl:
        c_d = [a["dyn_bad_psnr"] - b["dyn_bad_psnr"] for a, b in ctrl]
        c_r = [a["dyn_bad_dl1_cm"] / b["dyn_bad_dl1_cm"] for a, b in ctrl
               if a.get("dyn_bad_dl1_cm") is not None and b.get("dyn_bad_dl1_cm") and
               b["dyn_bad_dl1_cm"] > 0]
        cm, _ci, _ = _med_iqr(c_d)
        rm, _ri, _ = _med_iqr(c_r)
        out["j7_negative_control"] = {
            "bad_psnr_delta_median": cm, "bad_dl1_ratio_median": rm,
            "fails_main": bool(cm is not None and cm < MAIN_PASS_DB),
            "instrument_detects": bool(rm is not None and rm >= CTRL_RATIO_MIN)}
    # 仪器可判别力锚（prereg §9 修订 2026-09-25）：C- = P2 型臂 + 0.30m 错位（历史四轮的
    # 仪器检验形态）。其 depth-L1 比值 = canonical 仪器对错位的真实分辨力读数（诊断，
    # 不决定出口）；1.15 为 GTMC 时代历史参照值，仅并陈。
    anch = _paired(per_arm.get("C-", []), p1)
    if anch:
        a_r = [a["dyn_bad_dl1_cm"] / b["dyn_bad_dl1_cm"] for a, b in anch
               if a.get("dyn_bad_dl1_cm") is not None and b.get("dyn_bad_dl1_cm") and
               b["dyn_bad_dl1_cm"] > 0]
        a_d = [a["dyn_bad_psnr"] - b["dyn_bad_psnr"] for a, b in anch]
        am, _ai, _ = _med_iqr(a_d)
        arm_r, _ari, _ = _med_iqr(a_r)
        out["j7b_instrument_anchor_C_"] = {
            "bad_psnr_delta_median": am, "bad_dl1_ratio_median": arm_r,
            "historical_gtmc_ref": CTRL_RATIO_MIN,
            "resolves_shift": bool(arm_r is not None and arm_r >= CTRL_RATIO_MIN)}
    p2 = _paired(per_arm.get("P2", []), p1)
    if p2:
        p2d = [a["dyn_bad_psnr"] - b["dyn_bad_psnr"] for a, b in p2]
        p2m, _pi, _ = _med_iqr(p2d)
        out["p2_oracle_anchor"] = {"bad_psnr_delta_median": p2m}
        if j1m is not None and p2m:
            out["j1_frac_of_oracle"] = round(j1m / p2m, 4) if p2m > 0 else None
    return out


def judge(pairs):
    """pairs = [(results_dict, cfg_dict), ...]。出口规则见模块 docstring。"""
    main_pairs = [(r, c) for r, c in pairs if c.get("sequence") != c.get("generality_sequence")]
    if not main_pairs:
        raise SystemExit("[judge_p0] 无主域 config（sequence ≠ generality_sequence）")

    per_map, meta_by_tag = {}, {}
    for r, c in pairs:
        domain = "main" if c.get("sequence") != c.get("generality_sequence") else "generality"
        t0 = int(r["t0_frame"])
        for tag in r["arms"]:
            m = judge_map(r["arms"][tag], r["meta"].get(tag, {}), t0, domain)
            per_map[f"{c.get('sequence')}:{tag}"] = m
            meta_by_tag[f"{c.get('sequence')}:{tag}"] = r["meta"].get(tag, {})

    mt = [k for k, m in per_map.items() if m["domain"] == "main"]
    gt = [k for k, m in per_map.items() if m["domain"] == "generality"]

    j8, j8_alive = {}, {}
    for k in per_map:
        vit = (meta_by_tag[k].get("online_vitality") or {}).get("P0o") or {}
        log = vit.get("log") or []
        first = log[0].get("rho_med") if log else None
        j8[k] = {x: vit.get(x) for x in ("inserted_total", "evicted_total", "cap_hits",
                                         "buf_final", "rho_med_final")}
        j8[k]["rho_med_first"] = first
        j8_alive[k] = bool(vit.get("inserted_total", 0) > 0 and
                           (vit.get("evicted_total", 0) > 0 or
                            (vit.get("rho_med_final") is not None and first is not None
                             and vit["rho_med_final"] < first - 1e-4)))

    def _all(taglist, key, cond):
        vals = [per_map[t].get(key) for t in taglist if isinstance(per_map[t].get(key), dict)]
        return bool(vals) and all(cond(v) for v in vals)

    main_undecidable = any(not per_map[t].get("j6_judgeable", False) for t in mt)
    gen_undec = any(not per_map[t].get("j6_judgeable", False) for t in gt)
    # J7a（出口决定项）：阴性对照"通过"主判 ⇒ 仪器无效。J7b（C- 锚的深度分辨力）为诊断读数，
    # 不决定出口——prereg §9 修订 2026-09-25（1.15 阈值系 GTMC 仪器历史值，canonical 仪器未标定）。
    ctrl_fail = all((per_map[t].get("j7_negative_control") or {}).get("fails_main")
                    for t in mt)
    j1 = {k: (per_map[k].get("j1_bad_psnr_delta") or {}).get("median") for k in per_map}
    main_j1 = _all(mt, "j1_bad_psnr_delta", lambda v: v["median"] is not None and v["median"] >= MAIN_PASS_DB)
    main_j2 = _all(mt, "j2_bad_dl1_ratio", lambda v: v["median"] is not None and v["median"] < 1.0)
    main_j3 = _all(mt, "j3_static_delta", lambda v: v["median"] is not None and v["median"] >= STATIC_GATE_DB)
    main_j4 = _all(mt, "j4_cost", lambda v: v["frac"] is not None and v["frac"] <= COST_LINE)
    gen_ok = _all(gt, "j1_bad_psnr_delta", lambda v: v["median"] is not None and v["median"] > 0) if gt else None
    main_j8 = all(j8_alive.get(t, False) for t in mt)
    boundary_j1 = all(v is not None and BOUND_LO_DB <= v < MAIN_PASS_DB for v in (j1[t] for t in mt))
    one_map_pass = (len([1 for t in mt if j1[t] is not None and j1[t] >= MAIN_PASS_DB]) == 1)

    if main_undecidable:
        exit_, reason = "FAIL", "主域图不可判（J6）"
    elif not main_j8:
        exit_, reason = "FAIL", "机制未生效（J8）：零插入或 ρ 无实际变化"
    elif not ctrl_fail:
        exit_, reason = "VOID", "阴性对照通过主判 ⇒ 仪器无效，整批作废（J7）"
    elif main_j1 and main_j2 and main_j3 and main_j4 and main_j8 and gen_ok and not gen_undec:
        exit_, reason = "PASS", "J1–J5 全过且成本 ≤15%（J4）"
    elif (boundary_j1 or one_map_pass) and main_j3 and main_j8:
        exit_, reason = "边界", "J1 在 [1.0, 2.5) 或仅一图过线，机制诉求明确（J3/J8 过）"
    elif main_j1 and main_j2 and main_j3 and main_j4 and main_j8 and (gen_undec or gen_ok is False):
        exit_, reason = "边界", "主域全过但泛化不可判或方向不一致（J5）"
    else:
        exit_, reason = "FAIL", "主判/参照/静态门未达（详见逐图读数）"

    return {
        "prereg": "results/embrace_online/evidence/prereg_P0_embrace_online.md",
        "locked_thresholds": {"j1_main_pass_db": MAIN_PASS_DB, "boundary_lo_db": BOUND_LO_DB,
                              "j3_static_gate_db": STATIC_GATE_DB, "j4_cost_line": COST_LINE,
                              "j7_ctrl_ratio_min": CTRL_RATIO_MIN},
        "main_tags": mt, "generality_tags": gt,
        "j1_bad_psnr_delta_median_per_map": j1,
        "per_map": per_map,
        "j8_vitality": j8, "j8_alive": j8_alive,
        "exit": exit_, "exit_reason": reason,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True, help="cmd_render 产物 JSON（可多份）")
    ap.add_argument("--config", nargs="+", required=True, help="探针 config YAML（与 --results 一一对应）")
    ap.add_argument("--out", required=True, help="online_judgments 输出 JSON")
    args = ap.parse_args()
    assert len(args.results) == len(args.config), "--results 与 --config 数量须一致"
    pairs = [(json.load(open(rp)), yaml.safe_load(open(cp)))
             for rp, cp in zip(args.results, args.config)]
    out = judge(pairs)
    out["sources"] = {"results": list(args.results), "config": list(args.config)}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"[judge_p0] exit = {out['exit']} — {out['exit_reason']}")
    for t, m in out["per_map"].items():
        print(f"  {t}: J1={(m.get('j1_bad_psnr_delta') or {}).get('median')} dB "
              f"J2={(m.get('j2_bad_dl1_ratio') or {}).get('median')} "
              f"J3={(m.get('j3_static_delta') or {}).get('median')} dB "
              f"J4={(m.get('j4_cost') or {}).get('frac')} judgeable={m.get('j6_judgeable')}")
    print(f"[judge_p0] written {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
