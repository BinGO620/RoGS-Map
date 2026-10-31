#!/usr/bin/env python
"""paper2_fig_teaser.py — 论文 2 首页图（Fig. teaser，单栏，右栏顶部）生成器。

设计（用户终审选定版式 F，2026-10-18）：
  上行（钩子）＝ erased (prior paradigm) → repaired (+6.8 dB dyn.)；
  下行（证据）＝ stored map render → codec decode (6.0×)。
  全部真实工件（crowd2 f621 samepose 渲染 + codec 重建渲染），数字零手抄：
  - codec 比率 = results/gs_compress/evidence/rd/L2_*_b16-8-8-8-8.json ratio_full 均值；
  - repair 增益 = results/dynport_offline/evidence_v4/dynport_offline_L1_*_samepose.json
    的 J1_samepose_bad_psnr_delta.median 均值（三序列）。

真实工件来源：/tmp/fig1_assets/*.npy —— 由入库脚本
scripts/02_analysis/paper2_fig1_export_assets.py 现渲导出（judge_dynport 加载器；
先跑它再跑本脚本）。红线：本图为实验渲染照片拼图（真实工件）⇒ 不得用生成模型
（papers/paper2/figures/README.md 判据表）。

输出：results/paper2_fulltable/evidence/figs/fig_teaser.{pdf,png}；
镜像 papers/paper2/figs/fig_teaser.{pdf,png}（cp，由 test_paper2_figures_committed 守护）。
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper2_figstyle as _fs          # noqa: E402  字体族与其余图统一
import paper2_fig1_overview as F       # noqa: E402  复用工件加载与两条机写数字聚合

C_BLUE = "#0072B2"; C_ORANGE = "#D55E00"; C_DARK = "#333333"
mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": _fs.FONT_STACK,
                     "pdf.fonttype": 42})

ASSETS = F.ASSETS
OUT_DIR = REPO / "results/paper2_fulltable/evidence/figs"


def die(msg):
    raise SystemExit(f"[fig-teaser] {msg}")


def ld(k):
    p = ASSETS / f"{k}.npy"
    if not p.exists():
        die(f"缺真实工件 {p}（先跑 paper2_fig1_export_assets.py）")
    return np.load(p)


def crop(im, ratio):
    """中心裁切到宽高比 ratio（w/h），只裁上下。"""
    a = np.asarray(im)
    h, w = a.shape[:2]
    th = int(round(w / ratio))
    if th <= h:
        y0 = (h - th) // 2
        a = a[y0:y0 + th]
    return a


def imgax(fig, rect, img, color, lw=0.9):
    ax = fig.add_axes(rect)
    ax.imshow(F.clip8(img), interpolation="bilinear")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color(color); sp.set_linewidth(lw)
    return ax


def tag(fig, rect, text, color=C_DARK, fs=6.4, bold=False):
    x, y, w, h = rect
    fig.text(x + 0.015, y + 0.012, text, ha="left", va="bottom", fontsize=fs,
             color=color, fontweight=("bold" if bold else "normal"),
             bbox=dict(facecolor="white", alpha=0.80, edgecolor="none", pad=1.0))


def main():
    ratio, n_rd = F.codec_ratio_b16()
    gain, per = F.repair_gain()
    erased = ld("erased_621")
    rep = ld("repair_621")
    base_rec, b16_rec = F.codec_pair()
    print(f"[fig-teaser] codec {ratio:.2f}x (n={n_rd}) | repair +{gain:.2f} dB {per}")

    W, H = 3.1, 2.0
    m, g, rg = 0.015, 0.06, 0.09
    pw = (1 - 2 * m - g) / 2
    ph = pw * W / (16 / 9) / H
    y1 = 1 - m - ph
    y0 = y1 - rg - ph
    fig = plt.figure(figsize=(W, H))
    r = [(m, y1), (m + pw + g, y1), (m, y0), (m + pw + g, y0)]
    for rect, im, c in zip(r,
                           [crop(erased, 16 / 9), crop(rep, 16 / 9),
                            crop(base_rec, 16 / 9), crop(b16_rec, 16 / 9)],
                           [C_BLUE, C_ORANGE, C_BLUE, C_ORANGE]):
        imgax(fig, (*rect, pw, ph), im, c)
    for y in (y1, y0):
        F.arrow(fig, (m + pw + 0.006, y + ph / 2), (m + pw + g - 0.006, y + ph / 2),
                color=C_DARK, lw=0.9, ms=6)
    tag(fig, (*r[0], pw, ph), "erased (prior paradigm)")
    tag(fig, (*r[1], pw, ph), f"repaired (+{gain:.1f} dB dyn.)", C_ORANGE, bold=True)
    tag(fig, (*r[2], pw, ph), "stored map render")
    tag(fig, (*r[3], pw, ph), f"codec decode ({ratio:.1f}×)", C_ORANGE, bold=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig_teaser.{ext}", dpi=400,
                    bbox_inches="tight", pad_inches=0.01)
    print(f"wrote {OUT_DIR}/fig_teaser.pdf/png")


if __name__ == "__main__":
    main()
