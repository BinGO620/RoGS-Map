#!/usr/bin/env python
"""paper2_fig1_overview.py — 论文 2 Fig.1 总览图（带真实数据的 schematic-led composite）。

设计（nature-figure 契约，schematic-led composite 原型）：
  上带 ONLINE SLAM LOOP — PRIOR STACK（全部 crowd2 f621 真实工件，一帧贯穿）：
      input RGB → dynamic-mask overlay（系统真实消费的 canonical 掩码）→
      3DGS map 俯视散点（真实 PLY）→ rasterised render（真实在线渲染）。
      tracking 由 input→mask 的箭头上标注（pose vs map），不占面板。
  下带 OFFLINE, MAP-SIDE — THIS PAPER（两个贡献，各带真实工件链 + 机写数字）：
      codec：stored map raw render → codec decode（真实重建渲染）；
      repair：erased（反动态范式）→ repaired（真实 samepose 修复渲染，动态内容回填）。

数字零手抄（缺失即硬失败）：
  - codec 比率 = results/gs_compress/evidence/rd/L2_*_b16-8-8-8-8.json ratio_full 均值；
  - repair 增益 = results/dynport_offline/evidence_v4/dynport_offline_L1_*_samepose.json
    的 J1_samepose_bad_psnr_delta.median 均值（三序列）。

真实工件来源：/tmp/fig1_assets/*.npy —— 由入库脚本
scripts/02_analysis/paper2_fig1_export_assets.py 现渲导出（judge_dynport 加载器；
先跑它再跑本脚本，命令见 papers/paper2/figures/fig1_pipeline/fig1_pipeline.PROVENANCE.md）。
输出：results/paper2_fulltable/evidence/figs/fig1_pipeline.{pdf,png}。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper2_figstyle as _fs  # noqa: E402  字体族与其余 8 图统一（G2-M4）
ASSETS = Path("/tmp/fig1_assets")
OUT_DIR = REPO / "results/paper2_fulltable/evidence/figs"

C_BLUE = "#0072B2"; C_ORANGE = "#D55E00"; C_GREY = "#555555"; C_DARK = "#333333"

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": _fs.FONT_STACK,
    "pdf.fonttype": 42, "svg.fonttype": "none",
})


def die(msg):
    raise SystemExit(f"[fig1-overview] {msg}")


# ────────────────────────── 数字：全部机写 ──────────────────────────
def codec_ratio_b16():
    fs = sorted((REPO / "results/gs_compress/evidence/rd").glob("L2_*_b16-8-8-8-8.json"))
    if len(fs) != 42:
        die(f"codec rd jsons {len(fs)} 份 ≠ 42（L2 全集 7 序列×2 臂×3 seed；口径不得漂移）")
    rs = [json.load(open(f))["ratio_full"] for f in fs]
    return float(np.mean(rs)), len(fs)


def repair_gain():
    vals = []
    for s in ("crowd2", "balloon2", "person_tracking2"):
        f = REPO / f"results/dynport_offline/evidence_v4/dynport_offline_L1_{s}_samepose.json"
        if not f.exists():
            die(f"missing {f}")
        vals.append(json.load(open(f))["J1_samepose_bad_psnr_delta"]["median"])
    return float(np.mean(vals)), vals


def load_assets():
    need = ["gt_621", "online_621", "erased_621", "repair_621", "dyn_621", "map_top"]
    out = {}
    for k in need:
        p = ASSETS / f"{k}.npy"
        if not p.exists():
            die(f"缺真实工件 {p}")
        out[k] = np.load(p)
    return out


def codec_pair():
    a = REPO / "results/gs_compress/render/L1_crowd2_baseline/cmp_f00240.png"
    b = REPO / "results/gs_compress/render/L1_crowd2_b16-8-8-8-8/cmp_f00240.png"
    if not a.exists() or not b.exists():
        die("codec cmp_f00240.png 缺")
    A = np.array(Image.open(a)); B = np.array(Image.open(b))
    return A[:, A.shape[1] // 2:], B[:, B.shape[1] // 2:]


def clip8(im):
    """归一到 0-255 uint8：输入可为 0-1 float 或 0-255 uint8（G2-C1 修复：显式按域缩放）。"""
    im = np.asarray(im)
    if im.dtype == np.uint8:
        return im
    return np.clip(im * 255.0, 0, 255).astype(np.uint8)


def mask_overlay(rgb, mask, color=(213, 94, 0), alpha=0.55, outline=True):
    """动态掩码叠加在原 RGB 上（竞品式：中间量可视化叠在真实输入上）。

    rgb 为 0-1 float（judge 导出口径）；输出同为 0-1 float，交 clip8 统一转 uint8。
    """
    m = (mask[..., 0] if mask.ndim == 3 else mask) > 0
    ov = np.asarray(rgb, dtype=np.float32).copy()
    if ov.max() <= 1.5:  # 0-1 域：颜色同步归一
        col = np.array(color, np.float32) / 255.0
    else:                # 0-255 域
        col = np.array(color, np.float32)
    ov[m] = alpha * col + (1 - alpha) * ov[m]
    if outline:
        from scipy.ndimage import binary_dilation
        edge = binary_dilation(m, iterations=2) & ~m   # G2-M1 修复：原式 m&~dilate 恒空
        ov[edge] = col
    return ov


def imgax(fig, rect, img, color, lw=0.9):
    ax = fig.add_axes(rect)
    ax.imshow(clip8(img), interpolation="bilinear")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color(color); sp.set_linewidth(lw)
    return ax


def arrow(fig, p0, p1, color=C_DARK, lw=1.0, ls="-", ms=8):
    fig.add_artist(mpl.patches.FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=ms, lw=lw, color=color, linestyle=ls,
        shrinkA=0, shrinkB=0))


def main():
    ratio, n_rd = codec_ratio_b16()
    gain, per = repair_gain()
    A = load_assets()
    base_rec, b16_rec = codec_pair()
    print(f"[fig1] codec ratio = {ratio:.2f}x (n={n_rd}) | repair J1 mean = {gain:.2f} dB {per}")

    fig = plt.figure(figsize=(7.2, 3.55), dpi=300)

    # ════════ 上带 ════════
    yt, ht = 0.635, 0.235          # 顶 = y+0.87
    xs = [0.012, 0.212, 0.412, 0.612]
    W = 0.155
    centers = [x + W / 2 for x in xs]

    imgax(fig, (xs[0], yt, W, ht), A["gt_621"], C_BLUE)
    imgax(fig, (xs[1], yt, W, ht), mask_overlay(A["gt_621"], A["dyn_621"]), C_ORANGE, lw=1.0)
    imgax(fig, (xs[2], yt, W, ht), A["map_top"], C_BLUE)
    imgax(fig, (xs[3], yt, W, ht), A["online_621"], C_BLUE)

    # 上带面板箭头（input→mask→map→render→…尾部出带）
    for i in range(3):
        arrow(fig, (xs[i] + W + 0.004, yt + ht / 2), (xs[i + 1] - 0.004, yt + ht / 2))
    arrow(fig, (xs[3] + W + 0.004, yt + ht / 2), (xs[3] + W + 0.048, yt + ht / 2))
    # tracking 注记：input 面板下方（pose vs map 的 loop 语义）
    fig.text(centers[0], yt - 0.022, "track (pose ↔ map)",
             ha="center", va="top", fontsize=7.6, color=C_GREY, style="italic")

    # 面板标签（面板上方）
    lab_kw = dict(ha="center", va="bottom", fontsize=8.0, color=C_DARK)
    fig.text(centers[0], yt + ht + 0.012, "RGB-D input", **lab_kw)
    fig.text(centers[1], yt + ht + 0.012, "dynamic weighting", **lab_kw)
    fig.text(centers[2], yt + ht + 0.012, "3DGS map (grown online)", **lab_kw)
    fig.text(centers[3], yt + ht + 0.012, "rasterised render", **lab_kw)

    # 带标题
    fig.text(0.5, 0.985, "ONLINE SLAM LOOP — PRIOR STACK", ha="center", va="top",
             fontsize=9.0, color="#444444", fontweight="bold")

    # ════════ 下带 ════════
    yb, hb = 0.055, 0.235
    # codec 链占左半（2 图），repair 链占右半（2 图）；中间留"算子"标签位
    xs_b = [0.012, 0.212, 0.612, 0.812]
    cb = [x + W / 2 for x in xs_b]

    imgax(fig, (xs_b[0], yb, W, hb), base_rec, C_BLUE)
    imgax(fig, (xs_b[1], yb, W, hb), b16_rec, C_ORANGE, lw=1.0)
    imgax(fig, (xs_b[2], yb, W, hb), A["erased_621"], C_BLUE)
    imgax(fig, (xs_b[3], yb, W, hb), A["repair_621"], C_ORANGE, lw=1.0)

    # 链内箭头
    arrow(fig, (xs_b[0] + W + 0.004, yb + hb / 2), (xs_b[1] - 0.004, yb + hb / 2))
    arrow(fig, (xs_b[2] + W + 0.004, yb + hb / 2), (xs_b[3] - 0.004, yb + hb / 2))

    # 面板标签
    fig.text(cb[0], yb - 0.032, "stored map render", ha="center", va="top", fontsize=8.0)
    fig.text(cb[1], yb - 0.032, f"codec decode ({ratio:.1f}×)", ha="center", va="top",
             fontsize=8.0, color=C_ORANGE, fontweight="bold")
    fig.text(cb[2], yb - 0.032, "erased (prior paradigm)", ha="center", va="top", fontsize=8.0)
    fig.text(cb[3], yb - 0.032, f"repaired (+{gain:.1f} dB dyn.)", ha="center", va="top",
             fontsize=8.0, color=C_ORANGE, fontweight="bold")

    # 算子标签（链上方小字）
    fig.text(cb[0] + 0.10, yb + hb + 0.012, "offline map codec", ha="center", va="bottom",
             fontsize=7.8, color=C_ORANGE, fontweight="bold")
    fig.text(cb[2] + 0.10, yb + hb + 0.012, "offline dynamic repair", ha="center", va="bottom",
             fontsize=7.8, color=C_ORANGE, fontweight="bold")

    # 带标题（左对齐放带左上角，避箭头穿越带中部）
    fig.text(0.012, 0.545, "OFFLINE, MAP-SIDE — THIS PAPER", ha="left", va="top",
             fontsize=9.0, color=C_ORANGE, fontweight="bold")

    # ════════ 上→下 虚线箭头（map 面板 → 两链中部，避开带标题）════════
    y_map_bot = yt - 0.006
    arrow(fig, (centers[2], y_map_bot), (cb[0] + 0.10 + 0.02, yb + hb + 0.045),
          color=C_ORANGE, ls="--", lw=1.0, ms=7)
    arrow(fig, (centers[2], y_map_bot), (cb[2] + 0.10 + 0.02, yb + hb + 0.045),
          color=C_ORANGE, ls="--", lw=1.0, ms=7)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig1_pipeline.{ext}", dpi=320, bbox_inches="tight", pad_inches=0.02)
    print(f"wrote {OUT_DIR}/fig1_pipeline.pdf/png")


if __name__ == "__main__":
    main()
