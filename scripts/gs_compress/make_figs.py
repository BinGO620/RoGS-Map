#!/usr/bin/env python
"""make_figs.py — 论文出图（R-D 曲线族 + 存储代价账）。

读 results/gs_compress/evidence/rd/L2_*_rd_table.json，产出：
  fig_rd_curves.{pdf,png}    每序列 R-D 曲线（rate vs PSNR），跨 seed 均值 + IQR
  fig_storage_accounting.{pdf,png}  baseline vs final 地图体量（跨序列）
输出到 results/gs_compress/figs/。
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "02_analysis"))
import paper2_figstyle as fs  # noqa: E402  统一出图样式（单一事实源）

RD = REPO / "results" / "gs_compress" / "evidence" / "rd"
FIGS = REPO / "results" / "gs_compress" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

# 印刷级风格统一自 paper2_figstyle（无衬线、Okabe-Ito、caption 不进图面）。
fs.apply()

SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3", "person_tracking", "person_tracking2"]
seq_label = {"person_tracking": "pt1", "person_tracking2": "pt2"}

# Okabe-Ito 色盲安全调色板（统一自 figstyle）。每序列一个色 + 一个标记形状，
# 色相不是唯一编码（防色盲/黑白打印）：见 SEQ_STYLE。
OKABE = fs.OKABE
# 固定 (色, 标记) 每序列——crowd 族＝暖色族，pt 族＝冷/中性，两族内部靠标记区分
SEQ_STYLE = {
    "balloon": ("blue", "o"), "balloon2": ("skyblue", "s"), "crowd": ("vermillion", "^"),
    "crowd2": ("orange", "v"), "crowd3": ("purple", "D"),
    "person_tracking": ("green", "p"), "person_tracking2": ("black", "*"),
}


def load_curves():
    """(seq, arm) -> {rate: (psnr_list, static_list)}"""
    data = defaultdict(lambda: defaultdict(lambda: ([], [])))
    for f in sorted(RD.glob("L2_*_rd_table.json")):
        d = json.loads(f.read_text())
        m = re.match(r"L2_(.+)_(baseline|final)_s(\d+)", d["tag"])
        if not m:
            continue
        seq, arm = m.group(1), m.group(2)
        for r in d["rows"]:
            if r.get("kind") == "baseline" or not r.get("render"):
                continue
            key = round(r["rate_bytes_per_prim"], 2)
            data[(seq, arm)][key][0].append(r["render"]["mean_psnr"])
            data[(seq, arm)][key][1].append(r["render"]["mean_static_psnr"])
    return data


def fig_rd_curves(data):
    # figure* 双栏槽 = 0.95*textwidth(6.875in)=6.53in；native 取同宽 ⇒ 缩放≈1，字号=印刷字号。
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.9))
    # baseline = 实线 + 空心标记；final = 虚线 + 同色实心标记（线型+标记双重区分，非仅色相）
    for seq in SEQS:
        ckey, mk = SEQ_STYLE[seq]
        col = OKABE[ckey]
        for arm, ls, mfc in [("baseline", "-", "none"), ("final", "--", col)]:
            if (seq, arm) not in data:
                continue
            pts = data[(seq, arm)]
            rates = sorted(pts)
            mean = [np.mean(pts[k][0]) for k in rates]
            lo = [np.percentile(pts[k][0], 25) for k in rates]
            hi = [np.percentile(pts[k][0], 75) for k in rates]
            # 图例每序列只出一条（baseline 线型）；solid/dashed 的臂含义在题注里说明
            # （原 7×(baseline/final) 共 14 条 ⇒ 5.5pt 图例占去三分之一版面；2026-10-13 审阅 P2）
            lab = seq_label.get(seq, seq) if arm == "baseline" else None
            axes[0].plot(rates, mean, ls, marker=mk, ms=4, color=col, mfc=mfc, mew=0.8,
                         label=lab, lw=1.0)
            axes[0].fill_between(rates, lo, hi, color=col, alpha=0.14, lw=0)
    axes[0].set_xlabel("rate (bytes/primitive)")
    axes[0].set_ylabel("PSNR (dB)")
    fs.label_panel(axes[0], "a")
    axes[0].legend(fontsize=7.0, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.01), columnspacing=1.0, handlelength=1.6, handletextpad=0.4)
    axes[0].grid(alpha=0.25)

    # static PSNR（baseline 臂；同色同标记）
    for seq in SEQS:
        if (seq, "baseline") not in data:
            continue
        ckey, mk = SEQ_STYLE[seq]
        col = OKABE[ckey]
        pts = data[(seq, "baseline")]
        rates = sorted(pts)
        mean = [np.mean(pts[k][1]) for k in rates]
        axes[1].plot(rates, mean, "-", marker=mk, ms=4, color=col, mfc="none", mew=0.8,
                     label=seq_label.get(seq, seq), lw=1.0)
    axes[1].set_xlabel("rate (bytes/primitive)")
    axes[1].set_ylabel("static-region PSNR (dB)")
    fs.label_panel(axes[1], "b")
    axes[1].legend(fontsize=6.5, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.01), columnspacing=1.0, handlelength=1.6, handletextpad=0.4)
    axes[1].grid(alpha=0.25)

    fig.tight_layout()
    fs.save_pub(fig, FIGS, "fig_rd_curves")


def fig_storage():
    # 2026-10-05 修正：改用权威 census（storage_census.json，r33_rebase 同批），
    # 不再用旧批 glob（{seq}_{arm}_seed* 与论文主表非同批 —— 与 storage_accounting 件同 bug）。
    import json
    census = json.loads((RD.parent / "storage_census.json").read_text())
    rows = {r["seq"]: r["mb"] for r in census["rows"]}

    # 单栏槽 ≈ (6.875-0.25)/2=3.31in；native 取同宽 ⇒ 缩放≈1。
    fig, ax = plt.subplots(figsize=(3.3, 2.2))
    x = np.arange(len(SEQS))
    w = 0.38
    base = [rows.get(s, {}).get("baseline", np.nan) for s in SEQS]
    fin = [rows.get(s, {}).get("gate", np.nan) for s in SEQS]
    ax.bar(x - w / 2, base, w, label="base", color=OKABE["blue"])
    ax.bar(x + w / 2, fin, w, label="gate", color=OKABE["vermillion"])
    ax.set_xticks(x)
    ax.set_xticklabels([seq_label.get(s, s) for s in SEQS], rotation=45, ha="right")
    ax.set_ylabel("map size (MB, 20-field f32)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2, fontsize=7)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fs.save_pub(fig, FIGS, "fig_storage_accounting")


if __name__ == "__main__":
    data = load_curves()
    if data:
        fig_rd_curves(data)
    fig_storage()
