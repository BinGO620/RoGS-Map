#!/usr/bin/env python3
"""instrument_v2_judge.py — 仪器 v2 判读（程序化，禁手抄数字）。

prereg：evidence/prereg_instrument_v2.md（判据权威 §4）；测量代码 = instrument_v2_rescore.py。
从 rescore/*.json 程序化汇总：C1 支柱三参照 Δ、pt 超额性质、全臂对照表。
用法：
    python scripts/02_analysis/instrument_v2_judge.py [--out <table.md>]
"""
from __future__ import annotations

import argparse
import json
import numpy as np
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

DEFAULT_RESCORE = REPO / "results/lifecycle_paper2/instrument_v2/rescore"
REFS = ["exc_full_static", "exc_ring", "exc_depth_matched"]
REF_LABEL = {"exc_full_static": "全域静态", "exc_ring": "邻域环",
             "exc_depth_matched": "深度分层匹配(m3)"}

def arm_summary(rescore_dir):
    out = {}
    for p in sorted(Path(rescore_dir).glob("rescore_*.json")):
        try:
            d = json.load(open(p))
        except json.JSONDecodeError:
            continue
        name = p.stem.replace("rescore_", "").replace("_canon", "")
        out[name] = d
    return out


def pair_common_frames(run_a, run_b):
    fa = {f["frame"] for f in run_a.get("per_frame", [])}
    fb = {f["frame"] for f in run_b.get("per_frame", [])}
    return len(fa & fb)


def thin_pair(d, n_pair_frames, sup_a=None, sup_b=None):
    """可判性判据（唯一化定义，见 prereg §9 修正案 1）。

    分母 = 该对**两臂共同帧数**（n_pair_frames，= §1c "帧数"栏的比较基准，与 §1b 的
    "三参照同时可用帧数"是**不同量**，后者只用于回答"三参照是否同一批帧同号"）。
    分子 = 该参照在**两臂皆有效**的帧数（paired_delta 的 `n`）。
    判定（任一成立即 ⚠稀薄 ⇒ 判效不可用）：
      ① 任一参照 分子 < 50% 分母（对照区在多数帧上结构性缺失）；
      ② 任一臂的 support 像素中位为 0（像素级缺失；帧数够也可能像素稀缺）。
    """
    if not d or not n_pair_frames:
        return True
    for sup in (sup_a, sup_b):
        if sup and (sup.get("static_bg") == 0 or sup.get("ring") == 0):
            return True
    for ref in REFS:
        x = d.get(ref)
        if not x or x["n"] < 0.5 * n_pair_frames:
            return True
    return False


def is_thin(runs, a, b, d):
    """对 (run_a, run_b) 应用 thin_pair（自动取共同帧数与 support 元数据）。"""
    sa = runs[a].get("support_px_median") or {}
    sb = runs[b].get("support_px_median") or {}
    return thin_pair(d, pair_common_frames(runs[a], runs[b]), sa, sb)


def paired_delta(run_exit, run_off, common_only=False):
    """prereg §2 主读数：逐帧配对 Δ = exit − off（同帧集），再取 median + IQR。

    common_only=True 时进一步限制在**三参照都可用**的帧（同帧集严格版，用于回答
    "三参照是否真的在同一批帧上同号"）。
    返回 {ref: {median, iqr, n, exit_med, off_med}}（None-safe）。
    """
    if not run_exit or not run_off:
        return None
    fe = {f["frame"]: f for f in run_exit.get("per_frame", [])}
    fo = {f["frame"]: f for f in run_off.get("per_frame", [])}
    jkey = {"exc_full_static": "exc_full_cm", "exc_ring": "exc_ring_cm",
            "exc_depth_matched": "exc_m3_cm"}
    common = sorted(set(fe) & set(fo))
    if common_only:
        common = [fr for fr in common
                  if all(fe[fr].get(jkey[k]) is not None and fo[fr].get(jkey[k]) is not None
                         for k in REFS)]
    out = {}
    for ref in REFS:
        diffs, ev, ov = [], [], []
        for fr in common:
            a, b = fe[fr].get(jkey[ref]), fo[fr].get(jkey[ref])
            if a is None or b is None:
                continue
            diffs.append(a - b)
            ev.append(a)
            ov.append(b)
        if not diffs:
            out[ref] = None
            continue
        arr = np.asarray(diffs, dtype=np.float64)
        out[ref] = {
            "median": round(float(np.median(arr)), 4),
            "iqr": [round(float(np.quantile(arr, 0.25)), 4), round(float(np.quantile(arr, 0.75)), 4)],
            "n": int(arr.size),
            "exit_med": round(float(np.median(ev)), 4),
            "off_med": round(float(np.median(ov)), 4),
        }
    return out


def avail_signs(d):
    """可用参照的同号判定（参照结构性缺省时用；描述性，不替代 prereg §4 三参照判据）。"""
    if not d:
        return None, []
    vals = [d[r]["median"] for r in REFS if d.get(r)]
    if len(vals) < 2:
        return None, vals
    signs = [1 if v < 0 else (-1 if v > 0 else 0) for v in vals]
    return (len(set(signs)) == 1 and 0 not in signs), vals


def triple_sign(d):
    if not d:
        return False, None, None
    vals = [d[r]["median"] for r in REFS if d.get(r)]
    if len(vals) < 3 or any(v is None for v in vals):
        return False, None, None
    signs = [1 if v < 0 else (-1 if v > 0 else 0) for v in vals]
    return (len(set(signs)) == 1 and 0 not in signs), signs, min(abs(v) for v in vals)


def fmt_delta(d):
    if d is None:
        return "—（缺臂）"
    cells = []
    for ref in REFS:
        x = d[ref]
        cells.append(f"{x['median']:+.2f}" if x else "—")
    same, signs, mabs = triple_sign(d)
    av, _ = avail_signs(d)
    if same:
        tag = "同号|≥0.5" if mabs >= 0.5 else f"同号<0.5({mabs:.2f})"
    elif signs:
        tag = "混号"
    elif av is not None:
        tag = "参照缺省·可用同号" if av else "参照缺省·可用混号"
    else:
        tag = "参照不足"
    return f"{' / '.join(cells)} {tag}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rescore-dir", default=str(DEFAULT_RESCORE))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    runs = arm_summary(args.rescore_dir)
    lines = []
    lines.append("# 仪器 v2 判读一页表（程序化生成；prereg_instrument_v2 §4 + 修正案 1/§9）\n")
    try:
        import subprocess as _sp
        head_sha = _sp.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=10).stdout.strip() or "?"
    except Exception:
        head_sha = "?"
    lines.append(f"- **双溯源**：测量代码 = 73 run @ `2864c997` + 30 run @ `5695bc94`"
                 f"（等价性工件 `instrument_v2/control/control_report.md`）；"
                 f"分析代码 = `instrument_v2_judge.py` @ 生成时 HEAD `{head_sha}`。")
    lines.append(f"- 来源目录：`{os.path.relpath(args.rescore_dir, REPO)}/`，rescore run 数 = {len(runs)}")
    lines.append("- 读法：Δ = exit − off（median，cm；负 = exit 改善）。三列 = 全域静态 / 邻域环 / 深度分层匹配(m3)。")
    lines.append("- C1 存活判据（prereg §4）：三参照 median 同号 且 |median| ≥ 0.5cm。"
                 "**⚠稀薄** = 任一参照可用帧 < 50% 共同帧 ⇒ 读数由少数帧支撑，按判据不可用（详 §5）。\n")

    # ---- C1 支柱（prereg §4 子集 = balloon2/mvnobox/crowd3；另两序列为扩展）----
    lines.append("## 1. C1 支柱\n")
    lines.append("- **prereg §4 判据子集 = balloon2 / mvnobox / crowd3**（9 对）；balloon / mvnobox2 为**扩展**（非 prereg 判据，仅参考）。")
    lines.append("- 判据（prereg §4）：三参照 median 同号 且 |median| ≥ 0.5cm。方向：**负 = exit 改善**（C1 假设方向）。")
    lines.append("- **⚠稀薄** = 任一参照可用帧 < 50% 共同帧（对照区在多数帧上结构性缺失）⇒ **判效不可用**，"
                 "不计入存活；此类读数仅由少数帧支撑（详 §5）。\n")
    lines.append("| 支柱 | 判据集 | seed 对 | Δ 全域静态 | Δ 邻域环 | Δ m3 | 读数 |")
    lines.append("|---|---|---|---|---|---|---|")
    pillars = [
        ("balloon2", "L3_balloon2_exit_s", "L3_balloon2_off_s", True),
        ("mvnobox", "L3_mvnobox_exit_s", "L3_mvnobox_off_s", True),
        ("crowd3", "L3_crowd3_exit_s", "L3_crowd3_off_s", True),
        ("balloon", "L3_balloon_exit_s", "L3_balloon_off_s", False),
        ("mvnobox2", "L3_mvnobox2_exit_s", "L3_mvnobox2_off_s", False),
    ]
    c1_rows = []
    for name, exit_pre, off_pre, in_prereg in pillars:
        for s in "012":
            en, on = f"{exit_pre}{s}", f"{off_pre}{s}"
            if en not in runs or on not in runs:
                continue
            d = paired_delta(runs[en], runs[on])
            dcom = paired_delta(runs[en], runs[on], common_only=True)
            same, signs, mabs = triple_sign(d)
            same_c, signs_c, mabs_c = triple_sign(dcom)
            thin_flag = is_thin(runs, en, on, d)
            if thin_flag:
                verdict = "不可判(对照区缺)"
            elif same and mabs and mabs >= 0.5:
                verdict = "存活·改善" if mabs and d[REFS[0]]["median"] < 0 else "存活·变差"
            elif same:
                verdict = "同号<0.5"
            elif signs:
                verdict = "混号"
            else:
                verdict = "参照不足"
            c1_rows.append({"name": name, "seed": s, "verdict": verdict, "d": d,
                            "dcom": dcom, "thin": thin_flag, "prereg": in_prereg,
                            "n_common": pair_common_frames(runs[en], runs[on])})
            lines.append(f"| {name} | {'✓' if in_prereg else '扩展'} | s{s} | {fmt_delta(d)} | {verdict} |")

    def _cnt(pred):
        return sum(1 for r in c1_rows if pred(r))
    n_pre = _cnt(lambda r: r["prereg"])
    n_pre_alive = _cnt(lambda r: r["prereg"] and r["verdict"].startswith("存活"))
    n_pre_alive_imp = _cnt(lambda r: r["prereg"] and r["verdict"] == "存活·改善")
    n_pre_alive_worse = _cnt(lambda r: r["prereg"] and r["verdict"] == "存活·变差")
    n_pre_thin = _cnt(lambda r: r["prereg"] and r["thin"])
    n_ext_alive = _cnt(lambda r: not r["prereg"] and r["verdict"].startswith("存活"))
    lines.append(f"\n**C1 汇总（prereg §4 子集）：{n_pre_alive}/{n_pre} 对达标**"
                 f"（其中 exit 改善 {n_pre_alive_imp}、exit 变差 {n_pre_alive_worse}；"
                 f"另有 {n_pre_thin} 对因对照区缺失不可判）。"
                 f"扩展序列（balloon/mvnobox2）达标 {n_ext_alive}/6。\n")
    # 三参照共同帧重算（回答"三参照是否真的在同一批帧上同号"）
    lines.append("### 1b. 三参照共同帧重算（同帧集严格版；原判读各参照各自取交集）\n")
    lines.append("| 支柱 | seed 对 | 共同帧数 | Δ 全域静态 | Δ 邻域环 | Δ m3 | 同号? |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in c1_rows:
        dc = r["dcom"]
        if not dc:
            continue
        same_c, signs_c, _ = triple_sign(dc)
        ncom = max((dc[x]["n"] for x in REFS if dc.get(x)), default=0)
        cells = [f"{dc[x]['median']:+.2f}" if dc.get(x) else "—" for x in REFS]
        lines.append(f"| {r['name']} | s{r['seed']} | {ncom} | {' / '.join(cells)} | "
                     f"{'同号' if same_c else '混号'} |")
    lines.append("")
    # 全量明细（median + IQR + 帧数）——prereg §2 要求 median+IQR
    lines.append("### 1c. 明细（median [IQR] · 可用帧数；prereg §2 聚合口径）\n")
    lines.append("| 支柱 | seed | 参照 | median | IQR | 帧数(分子) | 共同帧(分母) |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in c1_rows:
        for ref in REFS:
            x = r["d"].get(ref) if r["d"] else None
            _den = r.get("n_common")
            if not x:
                lines.append(f"| {r['name']} | s{r['seed']} | {REF_LABEL[ref]} | — | — | 0 | {_den} |")
                continue
            lines.append(f"| {r['name']} | s{r['seed']} | {REF_LABEL[ref]} | {x['median']:+.2f} | "
                         f"[{x['iqr'][0]:+.2f}, {x['iqr'][1]:+.2f}] | {x['n']} | {_den} |")
    lines.append("")

    # ---- 描述性聚合（非判据；仅供参考其离散度）----
    lines.append("### 1d. 描述性聚合（**非判据**；prereg §4 判据仍是逐对三参照）\n")
    lines.append("| 支柱 | 各 seed Δ（全域静态/邻域环/m3 的中位数-of-medians） |")
    lines.append("|---|---|")
    for name, exit_pre, off_pre, _in_pre in pillars:
        per_ref = {r: [] for r in REFS}
        for s in "012":
            en, on = f"{exit_pre}{s}", f"{off_pre}{s}"
            if en not in runs or on not in runs:
                continue
            d = paired_delta(runs[en], runs[on])
            if not d:
                continue
            for r in REFS:
                if d.get(r):
                    per_ref[r].append(d[r]["median"])
        if not any(per_ref.values()):
            continue
        import statistics as _st
        cells = []
        for r in REFS:
            v = per_ref[r]
            cells.append(f"{_st.median(v):+.2f}" if v else "—")
        lines.append(f"| {name} | {' / '.join(cells)} |")
    lines.append("")

    # ---- pt 超额性质 ----
    lines.append("## 2. pt 超额性质（person_tracking / person_tracking2）\n")
    lines.append("| 序列 | seed 对 | Δ 三参照 | 同号? |")
    lines.append("|---|---|---|---|")
    pt_sign_sets = []
    for seq, exit_pre, off_pre in [
            ("person_tracking", "L3_person_tracking_exit_s", "L3_person_tracking_off_s"),
            ("person_tracking2", "L3_person_tracking2_exit_s", "L3_person_tracking2_off_s")]:
        for s in "012":
            en, on = f"{exit_pre}{s}", f"{off_pre}{s}"
            if en not in runs or on not in runs:
                continue
            d = paired_delta(runs[en], runs[on])
            same, signs, _ = triple_sign(d)
            if same:
                pt_sign_sets.append(signs[0])
            _thin = is_thin(runs, en, on, d)
            lines.append(f"| {seq} | s{s} | {fmt_delta(d)} | {'同号' if same else '混号'}"
                         f"{' ⚠稀薄' if _thin else ''} |")
    lines.append("")
    if pt_sign_sets and len(set(pt_sign_sets)) == 1:
        lines.append(f"**pt 判读：三参照符号一致（sign={pt_sign_sets[0]}）⇒ 报该符号与量级。**\n")
    else:
        lines.append("**pt 判读：符号不一致 ⇒ 效应量 < 仪器分辨力，pt 侧 1-2cm 级效应不可判"
                     "（night_report §3b 预期结果）。**\n")

    # ---- 其余臂全表 ----
    lines.append("## 3. 其余臂对照全表（同帧集配对，如实落表）\n")
    lines.append("| 臂 | off 对照 | Δ 三参照 |")
    lines.append("|---|---|---|")
    arm_pairs = [
        ("L3 crowd", "L3_crowd_exit_s", "L3_crowd_off_s"),
        ("L3 crowd2", "L3_crowd2_exit_s", "L3_crowd2_off_s"),
        ("L1b gate", "L1b_person_tracking_gate_s", "L3_person_tracking_off_s"),
        ("L1c occ", "L1c_person_tracking_occ_s", "L1c_person_tracking_occoff_s"),
        ("L1d stacked", "L1d_person_tracking_stacked_s", "L1c_person_tracking_exit_s"),
        ("L1e seam", "L1e_person_tracking_seam_s", "L3_person_tracking_exit_s"),
        ("L1e param", "L1e_person_tracking_param_s", "L3_person_tracking_exit_s"),
    ]
    for label, arm_pre, base_pre in arm_pairs:
        for s in "012345":
            an, bn = f"{arm_pre}{s}", f"{base_pre}{s}"
            if an not in runs or bn not in runs:
                continue
            d = paired_delta(runs[an], runs[bn])
            _thin3 = is_thin(runs, an, bn, d)
            lines.append(f"| {label} s{s} | {bn} | {fmt_delta(d)}"
                         f"{' ⚠稀薄' if _thin3 else ''} |")
    for label, arm_pre in [("L2 crowd gate", "L2_crowd_gate_s"),
                           ("L2 crowd2 gate", "L2_crowd2_gate_s"),
                           ("L2 pt2 gate", "L2_person_tracking2_gate_s")]:
        for s in "012345":
            an = f"{arm_pre}{s}"
            if an not in runs:
                continue
            s3 = runs[an].get("summary", {})

            def g(k):
                v = s3.get(k)
                return f"{v['median']:+.2f}" if v else "—"
            lines.append(f"| {label} s{s} | （gate 单臂落 summary） | {g('exc_full_static')} / {g('exc_ring')} / {g('exc_depth_matched')} |")

    # ---- TUM ----
    lines.append("\n## 4. TUM（prereg §2b：只落表，判读以官方 render_compare 为准）\n")
    lines.append("| run | 全域静态 | 邻域环 | m3 | band |")
    lines.append("|---|---|---|---|---|")
    for name in sorted(runs):
        if "tum" not in name.lower():
            continue
        s3 = runs[name].get("summary", {})

        def g(k):
            v = s3.get(k)
            return f"{v['median']:+.2f}" if v else "—"
        lines.append(f"| {name} | {g('exc_full_static')} | {g('exc_ring')} | {g('exc_depth_matched')} | {runs[name].get('band_used')} |")

    text = "\n".join(lines) + "\n"
    text += (
        "\n## 5. 参照可用性（仪器局限证据：对照区是否存在）\n\n"
        "支撑像素数中位数（`support_px_median`，仅重跑件落盘）。**判定规则**：任一参照的\n"
        "**可用帧 < 50% 共同帧**（等价于对照区在多数帧上结构性不存在）⇒ 该对**判效不可用**（⚠稀薄），\n"
        "不计入达标；support 中位为 0 是另一充分条件。**分母在 §1c 最后一列明示**（\"共同帧(分母)\"），\n"
        "分子为同表 \"帧数(分子)\"；§1b 的 \"共同帧数\"是\"三参照同时可用\"的另一量，**不是**本判据分母。\n\n"
        "| 序列（代表 run） | vac px | 全域静态 px | 邻域环 px | m3 可用 |\n"
        "|---|---|---|---|---|\n")
    for nm in sorted(runs):
        s = runs[nm]
        supd = s.get("support_px_median") or {}
        summ = s.get("summary", {})
        vac = supd.get("vac")
        st = supd.get("static_bg")
        rg = supd.get("ring")
        if vac is None and st is None and rg is None:
            continue  # 无元数据（主批 73 run）
        m3ok = "是" if summ.get("exc_depth_matched") else "**否**"
        stc = "**0**" if st == 0 else (str(st) if st is not None else "?")
        rgc = "**0**" if rg == 0 else (str(rg) if rg is not None else "?")
        text += f"| {nm} | {vac if vac is not None else '?'} | {stc} | {rgc} | {m3ok} |\n"
    text += (
        "\n**推论**：密人群序列（crowd/crowd2）与 TUM walking 上，`past`（历史掩码并集）近乎覆盖全视野，\n"
        "⇒ 参照区结构性消失（crowd2：static_bg = ring = 0，vac ≈ 20.4 万 px ≈ 全图 66%）。\n"
        "此类域**任何「腾空区 vs 静止区」型仪器都判不了效**（与 night_report §3 的 TUM 结论同源，\n"
        "现于 Bonn 人群族复现）。仅 m3（深度匹配）在部分帧尚可构造，但其自身也依赖同一批静态像素，\n"
        "序列越密越不可靠。\n")

    text += (
        "\n## 6. 覆盖率与范围偏差（如实登记）\n\n"
        f"- 期望 109 run（prereg §2b 全臂清单）；本次可评分 **{len(runs)} run**（= 109 − L2 6 run）。\n"
        "- **L2 gate 6 run（crowd/crowd2/person_tracking2 × s0/s1）v2 不可评分**：该批 run 目录未留\n"
        "  `config.yml` 快照，且 `plot/trj_full_final.json` 两侧工作副本已空（git 亦从未跟踪；远程\n"
        "  目录 mtime 2026-09-22 23:57 的被清空的 plot/reliability 等目录为证）⇒ 无相机位姿无法重渲。\n"
        "  补跑已尝试（`--config` 指向 `configs/experiments/lifecycle_paper2/l2_*_gate.yaml`，解析成功）\n"
        "  但止于 trj 缺失。替代路径（用 canon 渲染存盘的 17 张 depth PNG 反算）存在但未采用：属第二条\n"
        "  测量代码路径，且 L2 是已关闭的诊断臂（D1-008），不影响 §4 判读支柱（balloon2/mvnobox/crowd3/pt 全覆盖）。\n"
        "- **代码版本（双溯源）**：**73 run @ 测量代码 `2864c997`**（主批保留件）+ **30 run @ `5695bc94`**\n"
        "  （crowd 族 + TUM 的对照空集守卫修正重跑件）；L2 补跑驱动 @ `3ac72fd0`（仅加 `--config`，0 产出）。\n"
        "  阳性对照 ×2：①`3ac72fd0` 复算同一 run 与主批产物 **diff = 0 行**（除 run_dir）；\n"
        "  ②**守卫路径对照**（旧码 `2864c997` 与新码 `5695bc94` 在同一 crowd run 上逐帧比对）：\n"
        "  两臂皆有效的帧数值**逐位一致**，新码判 None 的帧正是旧码产出 NaN 的帧 ⇒ 守卫只改可判性不改数值。\n")
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text)
        print(f"[judge] written {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
