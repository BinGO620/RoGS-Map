#!/usr/bin/env python3
"""judge_reread_median.py — 历史判决的 median+IQR 重读表（D1-014 M4 整改；重读不改判）。

背景
----
NOTES:516 规则（2026-09-24 固化）：任何分区指标判效须 ≥2 参照 + 报 median/IQR（均值可被
少数帧主导）。D1-014 审计发现：除 instrument_v2_judge 外，全部 7 台判据机只读聚合 mean
（单参照）。**本脚本不改任何判决**——判决原文的 PASS/FAIL 维持原口径（单参照 mean），
本脚本只从**已在盘的** `render_*/render_metrics.json` 的 `per_frame` 逐帧明细
（109/109 canon 目录全有，D1-014 探针已核）离线重算每对臂的逐帧配对 Δ 的 median/IQR，
落成"重读表"（附件式），供写作轨与关卡② 引用时同时看到两读法。

读法（与 instrument_v2_judge.paired_delta 同口径）
--------------------------------------------------
- 同帧集配对：Δ_f = 臂值 − off 值（逐帧，两臂都有该帧才计）；
- 报 median + IQR + n（可用帧数）；附 mean 对照（标注"仅参考"）；
- **不改判**：不输出 PASS/FAIL，不与门槛比较；判决原文零改动（仅允许头部加带日期指针）。

用法
----
    /data/conda_envs/monogs-ours/bin/python scripts/02_analysis/judge_reread_median.py \
        --out results/lifecycle_paper2/evidence/judge_reread_median_2026-09-24.md
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "results" / "lifecycle_paper2"

# 每台判据机的臂对（arm_dir_template, off_dir_template, seeds）——目录名模板与各判据机一致
PAIRS = {
    "L1b gate vs off (pt)": (
        ["render_L1b_person_tracking_gate_s{seed}_canon"],
        ["render_L3_person_tracking_off_s{seed}_canon"],
        [0, 1, 2]),
    "L1c occ vs off (pt)": (
        ["render_L1c_person_tracking_occ_s{seed}_canon"],
        ["render_L1c_person_tracking_occoff_s{seed}_canon"],
        [0]),
    "L1d stacked vs exit (pt)": (
        ["render_L1d_person_tracking_stacked_s{seed}_canon"],
        ["render_L3_person_tracking_exit_s{seed}_canon",      # s0-2（L3 批）
         "render_L1c_person_tracking_exit_s{seed}_canon"],    # s3-5（L1c 确认批补齐件）
        [0, 1, 2, 3, 4, 5]),
    "L1e seam vs exit (pt)": (
        ["render_L1e_person_tracking_seam_s{seed}_canon"],
        ["render_L3_person_tracking_exit_s{seed}_canon",      # s0-2
         "render_L1c_person_tracking_exit_s{seed}_canon"],    # s3-5
        [0, 1, 2, 3, 4, 5]),
    "L1e param vs exit (pt)": (
        ["render_L1e_person_tracking_param_s{seed}_canon"],
        ["render_L3_person_tracking_exit_s{seed}_canon",      # s0-2
         "render_L1c_person_tracking_exit_s{seed}_canon"],    # s3-5
        [0, 1, 2, 3, 4, 5]),
    "L2 gate (crowd)": (
        ["render_L2_crowd_gate_s{seed}_canon"],
        ["render_L3_crowd_off_s{seed}_canon"],
        [0, 1]),
    "L2 gate (crowd2)": (
        ["render_L2_crowd2_gate_s{seed}_canon"],
        ["render_L3_crowd2_off_s{seed}_canon"],
        [0, 1]),
    "L2 gate (pt2)": (
        ["render_L2_person_tracking2_gate_s{seed}_canon"],
        ["render_L3_person_tracking2_off_s{seed}_canon"],
        [0, 1]),
    "L3 exit vs off (balloon2)": (
        ["render_L3_balloon2_exit_s{seed}_canon"],
        ["render_L3_balloon2_off_s{seed}_canon"],
        [0, 1, 2]),
    "L3 exit vs off (person_tracking)": (
        ["render_L3_person_tracking_exit_s{seed}_canon"],
        ["render_L3_person_tracking_off_s{seed}_canon"],
        [0, 1, 2]),
    "L3 exit vs off (person_tracking2)": (
        ["render_L3_person_tracking2_exit_s{seed}_canon"],
        ["render_L3_person_tracking2_off_s{seed}_canon"],
        [0, 1, 2]),
    "L3 exit vs off (crowd)": (
        ["render_L3_crowd_exit_s{seed}_canon"],
        ["render_L3_crowd_off_s{seed}_canon"],
        [0, 1, 2]),
    "L3 exit vs off (crowd2)": (
        ["render_L3_crowd2_exit_s{seed}_canon"],
        ["render_L3_crowd2_off_s{seed}_canon"],
        [0, 1, 2]),
    "L3 exit vs off (crowd3)": (
        ["render_L3_crowd3_exit_s{seed}_canon"],
        ["render_L3_crowd3_off_s{seed}_canon"],
        [0, 1, 2]),
    "L3 exit vs off (balloon)": (
        ["render_L3_balloon_exit_s{seed}_canon"],
        ["render_L3_balloon_off_s{seed}_canon"],
        [0, 1, 2]),
    "L3 exit vs off (mvnobox)": (
        ["render_L3_mvnobox_exit_s{seed}_canon"],
        ["render_L3_mvnobox_off_s{seed}_canon"],
        [0, 1, 2]),
    "L3 exit vs off (mvnobox2)": (
        ["render_L3_mvnobox2_exit_s{seed}_canon"],
        ["render_L3_mvnobox2_off_s{seed}_canon"],
        [0, 1, 2]),
    "L2 TUM exit vs off (wk_rpy)": (
        ["render_L3_tum_wk_rpy_exit_s{seed}_canon"],
        ["render_L3_tum_wk_rpy_off_s{seed}_canon"],
        [0, 1, 2, 3, 4, 5]),
}

KEYS = [("freshvac", "freshvac_ghost_excess_depth_l1_cm"),
        ("ghost_allhist", "ghost_excess_depth_l1_cm")]


def load_frames(dirname):
    p = ROOT / dirname / "render_metrics.json"
    if not p.is_file():
        return None
    d = json.load(open(p))
    return {f["frame"]: f for f in d.get("per_frame", [])}


def paired(d_arm, d_off, key):
    out = []
    for fr in sorted(set(d_arm) & set(d_off)):
        a, b = d_arm[fr].get(key), d_off[fr].get(key)
        if a is None or b is None:
            continue
        out.append(a - b)
    return out


def med_iqr(xs):
    if not xs:
        return None
    xs = sorted(xs)
    n = len(xs)
    med = statistics.median(xs)
    q1 = xs[max(0, int(round(0.25 * (n - 1))))] if n > 1 else xs[0]
    q3 = xs[min(n - 1, int(round(0.75 * (n - 1))))] if n > 1 else xs[0]
    return med, q1, q3, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    header = [
        "# 历史判决 median+IQR 重读表（D1-014 M4 整改；**重读不改判**）",
        "",
        "- 生成：`scripts/02_analysis/judge_reread_median.py`；数据 = 各 `render_*_canon/render_metrics.json`",
        "  的 `per_frame` 逐帧明细（109/109 canon 目录在盘，D1-014 探针已核）。",
        "- **读法**：逐帧配对 Δ = 臂 − off（同帧集），报 **median [IQR] (n=可用帧数)**；mean 仅对照。",
        "- **不改判声明**：历史判决的 PASS/FAIL 维持原口径（单参照 mean，见各 verdict 原文）；",
        "  本表只提供第二读法。两读法冲突时的权威 = `verdict_instrument_v2.md`（三参照 + thin 可判性）。",
        "- freshvac = 最近 30 帧窗口腾空区（官方口径）；ghost_allhist = 全历史并集口径（污染代理）。",
        "",
    ]
    rows = []
    missing = []
    for label, (arm_tpls, off_tpls, seeds) in PAIRS.items():
        for key_label, key in KEYS:
            for seed in seeds:
                d_arm = d_off = None
                a_name = o_name = "?"
                for t in arm_tpls:
                    n = t.format(seed=seed)
                    x = load_frames(n)
                    if x:
                        d_arm, a_name = x, n
                        break
                for t in off_tpls:
                    n = t.format(seed=seed)
                    x = load_frames(n)
                    if x:
                        d_off, o_name = x, n
                        break
                if d_arm is None or d_off is None:
                    _w = ("arm " + a_name) if d_arm is None else ("off " + o_name)
                    missing.append((label, seed, key_label, _w))
                    continue
                xs = paired(d_arm, d_off, key)
                r = med_iqr(xs)
                if r is None:
                    rows.append((label, seed, key_label, "无共同有效帧", ""))
                    continue
                med, q1, q3, n = r
                rows.append((label, seed, key_label,
                             f"**{med:+.2f}** [{q1:+.2f}, {q3:+.2f}] (n={n})",
                             f"{statistics.mean(xs):+.2f}"))
    text = "\n".join(header)
    text += "\n| 臂对 | seed | 参照 | median [IQR] (n) | mean（仅参考） |\n"
    text += "|---|---|---|---|---|\n"
    for label, seed, key_label, m, mean in rows:
        text += f"| {label} | s{seed} | {key_label} | {m} | {mean} |\n"
    if missing:
        text += "\n## 缺目录（如实登记；不重算不补跑）\n\n"
        text += "| 臂对 | seed | 参照 | 缺什么 |\n|---|---|---|---|\n"
        for label, seed, key_label, what in missing:
            text += f"| {label} | s{seed} | {key_label} | {what} |\n"
    text += "\n"
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(text)
    print(f"written {args.out} ({len(rows)} rows, {len(missing)} missing)")
    print(text[-1500:])


if __name__ == "__main__":
    main()
