#!/usr/bin/env python
"""gen_manifest_L1f.py — 从原始工件确定性重建 L1f 判决的机器可读 manifest（双溯源）。

数字来源 = run 原始输出 + 判据机输出（**机械生成，禁手抄**）：
  - 主判摘要：直接**导入 l1f_obsdebt_judge** 的函数（同源防漂移，照 gen_manifest_r34 惯例）；
  - ATE：<runtag>/tables/tracking_raw.csv（seed 感知）；
  - 双溯源 sha：prereg commit / 测量代码 commit / 分析代码 commit（调用方传入，来自 git）。

用法:
  python scripts/02_analysis/gen_manifest_L1f.py --date 2026-09-25 \
      --verdict "<一行结论>" --prereg-commit <sha> --measure-commit <sha> --analysis-commit <sha>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("l1f_obsdebt_judge", _HERE / "l1f_obsdebt_judge.py")
_J = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_J)  # __main__ guard ⇒ 无副作用


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--verdict", required=True)
    ap.add_argument("--prereg-commit", required=True)
    ap.add_argument("--measure-commit", required=True)
    ap.add_argument("--analysis-commit", required=True)
    ap.add_argument("--seeds", default="0,1,2", help="主判 seeds（击杀分支用 0,1,2,3,4,5）")
    ap.add_argument("--out", default=str(_J.ROOT + "/evidence/l1f_obsdebt_manifest.json"))

    args = ap.parse_args()
    seeds = [int(x) for x in args.seeds.split(",")]

    b2 = _J.judge_balloon2(seeds)
    b2_pre = _J.judge_balloon2([0, 1, 2])     # 预注册主批（3-seed）读数，与 6-seed 并陈
    pt = _J.judge_pt_constraint(seeds)
    fire_main = _J.collect_firing(_J.MAIN_RUNTAG, seeds)
    fire_ctrl = _J.collect_firing(_J.CTRL_RUNTAG, seeds)

    off_ate = _J._off_ate("balloon2", seeds)          # noqa: SLF001（同源复用）
    at = _J.gate_ate(_J.load_ate(_J.MAIN_RUNTAG), off_ate, seeds)
    # static PSNR 逐 seed 与门（vs exit_fill 对照）
    main_ps = [(s, (_J.load_render_metrics(_J.MAIN_RTAG.format(seed=s)) or {}).get("static_psnr"))
               for s in seeds]
    ctrl_ps = [(s, (_J.load_render_metrics(_J.CTRL_RTAG.format(seed=s)) or {}).get("static_psnr"))
               for s in seeds]
    ps = _J.gate_psnr(main_ps, ctrl_ps)
    prim = _J.guard_prim(_J.load_num_gaussians(_J.MAIN_RUNTAG),
                         _J.load_num_gaussians(_J.CTRL_RUNTAG))
    attr = b2.get("mechanism_attribution") or {}
    attr_primary = (attr.get("refs", {}).get(_J.PRIMARY_REF) or {}) if attr else {}

    doc = {
        "experiment": "lifecycle_paper2/l1f_obsdebt",
        "date": args.date,
        "prereg": "evidence/prereg_L1f_obsdebt.md",
        "verdict": "evidence/verdict_L1f_obsdebt.md",
        "verdict_oneliner": args.verdict,
        "verdict_rule": ("prereg §3 机械 PASS 但**不可归因**（负号集中于机制零动作 seed）"
                         "⇒ 判 PASS 不成立；判据本体零改动。"),
        "dual_provenance": {
            "prereg_commit": args.prereg_commit,
            "measurement_commit": args.measure_commit,
            "analysis_commit": args.analysis_commit,
        },
        "instrument": {
            "suffix": _J.RENDER_SUFFIX,
            "mask_source": "dynamic_mask (canonical boolean)",
            "references": ["exc_depth_matched (m3, primary)", "exc_full_static", "exc_ring"],
            "rescore_batch": "instrument_v2/rescore_batch_manifest_L1f.json",
        },
        "arms": {
            "main_obsdebt": _J.MAIN_RUNTAG,
            "control_exit_fill": _J.CTRL_RUNTAG,
            "constraint_pt": _J.PT_RUNTAG,
            "delta_definition": "obsdebt − exit_fill（同管线单变量，prereg §2）",
        },
        "seeds": seeds,
        "main_criterion": {
            "domain": "balloon2",
            "primary_ref": _J.PRIMARY_REF,
            "threshold_cm": _J.THRESHOLD_CM,
            "judgeable": b2.get("judgeable"),
            "primary": b2.get("primary"),
            "refs_all": b2.get("refs"),
            "mechanical_PASS": b2.get("PASS"),
            "preregistered_3seed_reading": {
                "primary": b2_pre.get("primary"),
                "mechanical_PASS": b2_pre.get("PASS"),
            },
        },
        "attribution_diagnostic": {
            "rule": "机制动作 = ② fill kept>0 或 ③ boost>0（① 账本记账不算动作）",
            "active_seeds": attr.get("active_seeds"),
            "idle_seeds": attr.get("idle_seeds"),
            "active_only_mom": attr_primary.get("median_of_medians"),
            "active_only_n_neg": attr_primary.get("n_neg_ratio"),
            "active_only_PASS": attr_primary.get("PASS"),
        },
        "robustness_diagnostic": b2.get("primary_robustness"),
        "constraint_gates": {
            "ATE_vs_off": at,
            "static_PSNR_vs_ctrl": ps,
            "primitive_budget": prim,
            "coverage_guard": b2.get("coverage_guard"),
            "person_tracking": pt,
        },
        "firing_prereg_2b": {
            "main_balloon2": fire_main,
            "control_balloon2": fire_ctrl,
        },
        "prereg_3_amendment_note": (
            "② 预算重分配结构性不触发（vacated 峰值远小于 fill_max_points=2000，实测 0 事件）；"
            "③ 迭代配额全批仅 4 事件（s4/s5 零）⇒ 机制在本域作用面过薄；"
            "负号集中于零动作 seed ⇒ 效应不可归因。如实登记，不作改判。"
        ),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"written {args.out}")
    print(f"  PASS={b2.get('PASS')}  mom={b2.get('primary', {}).get('median_of_medians')}"
          f"  seeds={seeds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
