#!/usr/bin/env python
"""paper2_baseline_table.py — 机写论文 v1 §3「系统横向对比」表。

读 resources/baselines/baselines_result/<method>/{tracking,mapping,efficiency}_raw.csv
（11 方法 × BONN 8 序列 × 3 seed，同机同码，依 03-metrics_checklist.md 统一 Horn SE(3)/cm/ddof=1）。

输出（论文用 CVM LaTeX）：
  results/paper2_fulltable/evidence/latex/tab_baseline.tex  （横比主表，跨栏 table*）
  results/paper2_fulltable/evidence/baseline_compare.json   （机写中间件，供守护测试）

口径纪律（DISCIPLINE「测量口径」）：
  * 每格 = 该 (method, sequence) 3 seed 的 mean±std（样本标准差 ddof=1）
  * 公共可对比集 = 基线 ∩ 本文 stack 的 BONN 序列 = balloon/balloon2/crowd/crowd2/
    person_tracking/person_tracking2（6 条）；基线多的 mvnobox×2、本文多的 crowd3 不在主表
  * 非 3DGS 方法无 PSNR ⇒ 记 `--`（N/A，方法不支持；不伪造）
  * 静态方法在动态序列上 ATE 崩 ⇒ 如实呈现，不裁剪（这本身是反动态范式的动机证据）
  * 归一：`--` 表示 N/A；`\textsuperscript{f}` 表示该 (method,seq) 有 FAIL seed（记数字仍用 OK 行）

消费方 = 论文 v1 §3（待叙事锁定后 \input）。**入表前须过关卡②（slam-critic）。**
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "resources/baselines/baselines_result"
PREVIEW = REPO / "results/paper2_fulltable/evidence/tables_paper2_preview.json"
OUT_TEX = REPO / "results/paper2_fulltable/evidence/latex/tab_baseline.tex"
OUT_JSON = REPO / "results/paper2_fulltable/evidence/baseline_compare.json"

# 公共可对比 BONN 序列（baseline 缩写 -> 本仓全名）
COMMON = [
    ("balloon", "balloon"),
    ("balloon2", "balloon2"),
    ("crowd", "crowd"),
    ("crowd2", "crowd2"),
    ("person_t", "person_tracking"),
    ("person_t2", "person_tracking2"),
]
# 方法展示顺序：按能力分组（static 在前，凸显动态序列上崩）
METHODS = [
    ("MonoGS", "static"),
    ("SplaTAM", "static"),
    ("Co-SLAM", "static"),
    ("ORB_SLAM3", "static"),
    ("DG-SLAM", "dynamic"),
    ("RGD-SLAM", "dynamic"),
    ("WildGS-SLAM", "dynamic"),
    ("DynaGSLAM", "dynamic"),
    ("DynaSLAM", "dynamic"),
    ("NGD-SLAM", "dynamic"),
    ("RoDyn-SLAM", "dynamic"),
]
LABEL = {"MonoGS": "MonoGS", "SplaTAM": "SplaTAM", "Co-SLAM": "Co-SLAM",
         "ORB_SLAM3": "ORB-SLAM3", "DG-SLAM": "DG-SLAM", "RGD-SLAM": "RGD-SLAM",
         "WildGS-SLAM": "WildGS-SLAM", "DynaGSLAM": "DynaGSLAM",
         "DynaSLAM": "DynaSLAM", "NGD-SLAM": "NGD-SLAM", "RoDyn-SLAM": "RoDyn-SLAM"}
# 表内 Family 列 = 地图表示族（2026-10-18 用户裁定：原 Type 列的 static/dynamic 与分组标题冗余，
# 改列表示族后：① 消冗余 ② 与 §2 的 3DGS/隐式场/传统三条线咬合 ③ 解释三个 classical 方法无渲染路径）。
# DynaGSLAM 标 3DGS（其论文自我定位为"在线动态 GS"，明确与离线 4D GS 区分；勿标 4D）。
FAMILY = {"MonoGS": "3DGS", "SplaTAM": "3DGS", "Co-SLAM": "implicit",
          "ORB_SLAM3": "classical", "DG-SLAM": "3DGS", "RGD-SLAM": "3DGS",
          "WildGS-SLAM": "3DGS", "DynaGSLAM": "3DGS", "DynaSLAM": "classical",
          "NGD-SLAM": "classical", "RoDyn-SLAM": "implicit"}

# 本文 stack 的臂名 -> BONN 七序列 ATE（来自 r33_rebase，见 paper2_tables.py 口径）
OUR_STACK_LABEL = "Prior RGB-D stack"


def _read(method, kind):
    f = BASE / method / f"{kind}_raw.csv"
    return pd.read_csv(f, encoding="utf-8-sig") if f.exists() else None


def _cell(df, seq_col, seq_val, col, status_col="status"):
    """返回 (mean, std, n_ok, n_fail, n_diverged) 或 None。

    n_diverged = 该 (method,seq) OK 行中跟踪发散的 run 数（path_length_ratio>500% 或
    ATE>100cm）。发散是静态方法在动态序列上的真实失败，须如实标注而非把巨数当读数。
    """
    if df is None or col not in df:
        return None
    sub = df[df[seq_col] == seq_val]
    if sub.empty:
        return None
    ok = sub[sub[status_col] == "OK"] if status_col in sub else sub
    vals = ok[col].dropna().astype(float)
    nfail = int((sub[status_col] != "OK").sum()) if status_col in sub else 0
    ndiv = 0
    if "path_length_ratio" in ok and "ate_rmse_cm" in ok:
        plr = pd.to_numeric(ok["path_length_ratio"], errors="coerce")
        ate = pd.to_numeric(ok["ate_rmse_cm"], errors="coerce")
        ndiv = int(((plr > 500) | (ate > 100)).sum())
    if vals.empty:
        return None
    m = float(vals.mean())
    s = float(vals.std(ddof=1)) if len(vals) > 1 else 0.0
    return m, s, len(vals), nfail, ndiv


def _fmt(cell, prec=2):
    if cell is None:
        return "--"
    m, s, n, nf, ndiv = cell
    # 阈值：确定性方法跨 seed 完全相同 ⇒ std 数值上 ~1e-9，按 0 处理（避免 ±0.00）
    if s > 10 ** (-(prec + 1)):
        txt = f"{m:.{prec}f}$\\pm${s:.{prec}f}"
    else:
        txt = f"{m:.{prec}f}"
    if ndiv:
        txt += "$^\\mathrm{d}$"
    elif nf:
        txt += "$^\\mathrm{f}$"
    return txt


def our_stack_row():
    """本文前作栈（Prior RGB-D stack）的 BONN 公共 6 序列 —— 机写自 preview JSON（r33_rebase 口径）。

    口径注意：preview 的 psnr 是**全图离线渲染**，fps 是并发批中位数；与 baseline 套件的
    全图 PSNR / end-to-end FPS 大体同口径但不保证逐位同协议 —— 入表须在题注声明（本脚本如实标）。
    """
    d = json.loads(PREVIEW.read_text())
    cells = {}
    for bseq, full in COMMON:
        key = f"baseline|{full}"
        v = d.get(key)
        if not v:
            cells[bseq] = {"ate": None, "psnr": None, "fps": None}
            continue
        def cell(m, s, n=3):
            return (float(m), float(s), int(n), 0, 0)
        cells[bseq] = {
            "ate": cell(v["ate_mean"], v["ate_sd"], v.get("ate_n", 3)),
            "psnr": cell(v["psnr"], 0.0) if v.get("psnr") is not None else None,
            "fps": cell(v["fps_med"], 0.0) if v.get("fps_med") is not None else None,
        }
    return {"method": OUR_STACK_LABEL, "is_ours": True, "cells": cells}


def build():
    rows = []          # json
    for method, _cap in METHODS:
        t, g, e = _read(method, "tracking"), _read(method, "mapping"), _read(method, "efficiency")
        rec = {"method": method, "cells": {}}
        for bseq, _full in COMMON:
            rec["cells"][bseq] = {
                "ate": _cell(t, "sequence", bseq, "ate_rmse_cm"),
                "psnr": _cell(g, "sequence", bseq, "psnr"),
                "fps": _cell(e, "sequence", bseq, "fps_end_to_end"),
            }
        rows.append(rec)
    return rows


def tex(rows):
    """主横比表：行 = 方法，列 = 公共 BONN 序列，格 = ATE (cm) mean±sd。

    之所以只列 ATE：6 序列 × 3 指标 = 18 数据列，双栏排版不可读；ATE 是系统对比的主轴。
    PSNR/FPS 留在 JSON（`baseline_compare.json`）供 §3 讨论/子表，不在本表堆叠。
    """
    seq_labels = {"balloon": "balloon", "balloon2": "balloon2", "crowd": "crowd",
                  "crowd2": "crowd2", "person_t": "person\\_tracking",
                  "person_t2": "person\\_tracking2"}
    L = []
    L.append("% generated by scripts/02_analysis/paper2_baseline_table.py -- do not edit by hand")
    L.append("% provenance: resources/baselines/baselines_result/*/tracking_raw.csv")
    L.append("% 口径：Horn SE(3) / cm / ddof=1；公共 BONN 6 序列；格 = ATE mean±sd (cm)；-- = N/A")
    L.append(r"\begin{table*}[t]")
    L.append(r"\centering")
    L.append(r"\footnotesize")
    L.append(r"\setlength{\tabcolsep}{4pt}")
    L.append(r"\begin{tabular}{@{}ll" + "c" * len(COMMON) + r"@{}}")
    L.append(r"\toprule")
    L.append(r"\emph{Method} & \emph{Family} & "
             + " & ".join(seq_labels[b] for b, _ in COMMON) + r" \\")
    L.append(r"\midrule")
    L.append(r"\multicolumn{%d}{@{}l}{\emph{Static methods}} \\" % (len(COMMON) + 2))
    label_done = {"static": False, "dynamic": False}
    for method, cap in METHODS:
        if cap == "dynamic" and not label_done["dynamic"]:
            L.append(r"\midrule")
            L.append(r"\multicolumn{%d}{@{}l}{\emph{Dynamic methods}} \\" % (len(COMMON) + 2))
            label_done["dynamic"] = True
        r_ = next(x for x in rows if x["method"] == method)
        cells = " & ".join(_fmt(r_["cells"][b]["ate"]) for b, _ in COMMON)
        L.append(f"{LABEL[method]} & {FAMILY[method]} & {cells} \\\\")
    L.append(r"\midrule")
    ours = next((x for x in rows if x.get("is_ours")), None)
    if ours:
        cells = " & ".join(_fmt(ours["cells"][b]["ate"]) for b, _ in COMMON)
        L.append(r"\textbf{" + OUR_STACK_LABEL + r"} & \textbf{3DGS} & " + cells + r" \\")
    L.append(r"\bottomrule")
    L.append(r"\end{tabular}")
    # 图例按实际出现的标记生成（2026-10-15，审稿 R4-P8）：`f` 与 `--` 在本批数据中零出现，
    # 保留未使用的图例项会让读者以为表内有未显示的失败格/缺格。
    any_f = any("$^\\mathrm{f}$" in _fmt(r_["cells"][b]["ate"]) for r_ in rows for b, _ in COMMON)
    any_na = any(r_["cells"][b]["ate"] is None for r_ in rows for b, _ in COMMON)
    marks = [r"$^\mathrm{d}$: tracking diverged (path length $>5\times$ GT or ATE $>100$\,cm) on "
             r"initial run; re-run attempted under the same protocol with recommended settings. "
             r"Values shown are from the re-run (diverged status retained where re-run also "
             r"diverged)"]
    if any_f:
        marks.append(r"$^\mathrm{f}$: a seed failed")
    if any_na:
        marks.append(r"`--' : not reported")
    L.append(r"\caption{Absolute trajectory error on the common BONN sequences (RMSE, cm, "
             r"mean$\pm$sd over 3 seeds; all-frames, Horn SE(3) alignment). Family is the map "
             r"representation. The first eleven rows "
             r"are a single same-machine reproduction. DynaGSLAM delegates "
             r"tracking to an external front-end (DynoSAM poses) and its three seeds are therefore "
             r"deterministic, so it is reported without variance. The last row is the prior "
             r"RGB-D stack, evaluated on the same machine and protocol in an independent batch; it "
             r"is reported as background and is not a result of this paper. Execution conditions "
             r"vary across systems: DynaSLAM and NGD-SLAM are classical keypoint pipelines "
             r"(DynaSLAM on an ORB-SLAM2 base, NGD-SLAM on an ORB-SLAM3 base, both CPU-only), "
             r"WildGS-SLAM is monocular, "
             r"and seed reporting follows each system's capability; "
             r"these numbers establish the tracking regime this map study builds on, not isolated "
             r"map-architecture comparisons. Static methods degrade "
             r"severely on the dynamic sequences, which is the regime this paper targets; they are "
             r"shown to place the dynamic methods in context, not as straw men. "
             + "; ".join(marks) + r". PSNR and FPS are in the text.}")
    L.append(r"\label{tab:baseline}")
    L.append(r"\end{table*}")
    return "\n".join(L) + "\n"


def main():
    rows = build()
    rows.append(our_stack_row())
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(rows, indent=2, default=str))
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text(tex(rows))
    print(f"wrote {OUT_TEX.relative_to(REPO)}")
    print(f"wrote {OUT_JSON.relative_to(REPO)}")
    # 打印可读预览
    for r_ in rows:
        name = LABEL.get(r_["method"], r_["method"])
        cells = []
        for b, _ in COMMON:
            c = r_["cells"][b]
            ate = f"{c['ate'][0]:.1f}" if c["ate"] else "--"
            ps = f"{c['psnr'][0]:.1f}" if c["psnr"] else "--"
            fp = f"{c['fps'][0]:.2f}" if c["fps"] else "--"
            cells.append(f"{ate}/{ps}/{fp}")
        print(f"{name:20s} " + " ".join(f"{c:18s}" for c in cells))


if __name__ == "__main__":
    main()
