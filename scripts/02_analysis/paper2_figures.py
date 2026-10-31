#!/usr/bin/env python
"""paper2_figures.py — 论文 2 图集生成器（CVM 风格 + 惯例 + 特色）。

**两类图**（依 CVM 惯例观察，见 resources/lit_dyn_mapping/venue_cvm.md §7 + template 指南）：
  A. 惯例图（这类论文都有，缺了就"不像该领域的稿"）：
     fig1_pipeline   架构/管线框图（**2026-10-09 起论文改用 AI 定稿版，见
                     papers/paper2/figures/fig1_pipeline/PROVENANCE.md；本生成器仍画
                     matplotlib 版作留档/回退锚点，evidence/figs/ 同名副本不再是论文图源**）
     fig2_render     GT|render 对比网格 + 局部放大框（CVM 主视觉；现稿无放大框、caption 烧进图）
     fig3_traj       轨迹对比（GT vs base vs gate；**惯例图但现稿缺**）
  B. 特色图（本文贡献的"指纹"，别人没有）：
     fig4_tail       重尾直方图 + 范围膨胀（本稿唯一反直觉事实，却没图）
     fig5_accounting 地图解剖堆叠条（字节构成：inert/structural/payload）

**风格规约**（CVM template 指南 + 去 AI 味）：**无衬线字体（统一自 paper2_figstyle）**、
字号≥8pt、无标题（caption 在 LaTeX）、颜色少而稳（Okabe-Ito 色盲安全）、线宽可打印、
**caption 不进图面**（改由 LaTeX \caption）。
输出：results/paper2_fulltable/evidence/figs/*.{pdf,png}
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper2_figstyle as fs  # noqa: E402  统一出图样式（单一事实源）

FIGS = REPO / "results/paper2_fulltable/evidence/figs"
FIGS.mkdir(parents=True, exist_ok=True)
RD = REPO / "results/gs_compress/evidence/rd"

fs.apply()

SEQ = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
       "person_tracking", "person_tracking2"]
SEQ_LBL = {"person_tracking": "pt1", "person_tracking2": "pt2"}
ARMS = ["baseline", "swbaonly", "final", "gate"]
ARM_LBL = {"baseline": "prior stack", "swbaonly": "+SWBA", "final": "+SWBA+LC", "gate": "+Gate"}

# 语义色（统一自 figstyle）：base=蓝、gate/ours=朱红、GT=灰
C = {"base": fs.ARM_COLOR["base"], "mid": fs.OKABE["skyblue"], "warm": fs.ACCENT,
     "green": fs.OKABE["green"], "grey": fs.GREY, "sand": fs.OKABE["orange"],
     "lightblue": fs.OKABE["skyblue"]}


def save(fig, name):
    fs.save_pub(fig, FIGS, name)


# ============================================================ A1. pipeline (conventional)
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(7.2, 2.3))
    ax.set_xlim(0, 10); ax.set_ylim(0, 3); ax.axis("off")
    boxes = [
        (0.15, 1.0, "RGB-D\nframes", C["lightblue"]),
        (1.85, 1.0, "tracking\n(pose vs map)", "#dbe7f3"),
        (3.55, 1.0, "dynamic\nweighting", "#f2e2d0"),
        (5.25, 1.0, "3DGS map\n(grown online)", "#dfe9d8"),
        (6.95, 1.0, "rasterised\nrender", C["lightblue"]),
    ]
    for x, y, t, col in boxes:
        ax.add_patch(FancyBboxPatch((x, y), 1.45, 0.95, boxstyle="round,pad=0.06,rounding_size=0.12",
                                    linewidth=0.9, edgecolor="#333", facecolor=col))
        ax.text(x + 0.72, y + 0.47, t, ha="center", va="center", fontsize=8)
    for x in (0.15, 1.85, 3.55, 5.25, 6.95):
        ax.add_patch(FancyArrowPatch((x + 1.45, 1.47), (x + 1.7, 1.47),
                                     arrowstyle="-|>", mutation_scale=9, color="#333", lw=1.0))
    # offline branches (this paper's contributions): codec | repair operator
    ax.add_patch(FancyBboxPatch((4.62, 0.05), 1.98, 0.66, boxstyle="round,pad=0.06,rounding_size=0.12",
                                linewidth=1.0, edgecolor=C["warm"], facecolor="#fbe9e7", linestyle="--"))
    ax.text(5.61, 0.38, "offline map codec\n(this paper)", ha="center", va="center",
            fontsize=6.8, color=C["warm"])
    ax.add_patch(FancyBboxPatch((6.72, 0.05), 2.28, 0.66, boxstyle="round,pad=0.06,rounding_size=0.12",
                                linewidth=1.0, edgecolor=C["warm"], facecolor="#fbe9e7", linestyle="--"))
    ax.text(7.86, 0.38, "offline dynamic repair\n(this paper)", ha="center", va="center",
            fontsize=6.8, color=C["warm"])
    # dashed drop arrows from the map box to both offline operators
    ax.add_patch(FancyArrowPatch((5.6, 1.0), (5.6, 0.73), arrowstyle="-|>",
                                 mutation_scale=9, color=C["warm"], lw=1.0, linestyle="--"))
    ax.add_patch(FancyArrowPatch((7.7, 1.0), (7.86, 0.73), arrowstyle="-|>",
                                 mutation_scale=9, color=C["warm"], lw=1.0, linestyle="--"))
    # ⚠ 论文 fig1 已换程序拼合真实数据总览图（paper2_fig1_overview.py）。
    # 本函数产物仅为留档/回退锚点：写进**图工作区**（figures/fig1_pipeline/），与
    # 既有回退副本同名，且**不写受守护的 evidence/figs/**（否则跑一次就弄脏 git 目录）；
    # 已从 __main__ 摘出、不再默认重跑（G2-M2）。
    backup = REPO / "papers/paper2/figures/fig1_pipeline"
    for ext in ("pdf", "png"):
        fig.savefig(backup / f"fig1_pipeline_programmatic_backup.{ext}")
    plt.close(fig)
    print(f"  wrote fig1_pipeline_programmatic_backup.pdf/png → {backup}")


# ============================================================ A2. render montage w/ zoom
def _load_cmp(tag_dir, frame, half, crop_top=22):
    """half='gt'|'render'：从 [GT|render] 横拼图切一半，去掉顶部烧入文字带。"""
    for ext in ("png", "jpg"):
        p = Path(tag_dir) / f"cmp_f{frame:05d}.{ext}"
        if p.exists():
            im = np.asarray(plt.imread(p))
            h, w = im.shape[:2]
            im = im[crop_top:, :, :]
            half_w = w // 2
            return im[:, :half_w, :] if half == "gt" else im[:, half_w:, :]
    return None


def fig_render(seq="crowd2", frames=(125, 380, 635), seed=0, out_name=None, arms=("baseline",)):
    """行 = GT / 各 arm，列 = 帧。GT 只出现一次（左半），render 取各臂右半。

    arms 默认只画 baseline：SWBA/gate 复合臂排除（R2_NARRATIVE §7 红线，SWBA 一字不提）。
    """
    def tag_dir(arm):
        g = glob.glob(str(REPO / f"results/paper2_fulltable/render_compare/"
                                f"r33_rebase_{arm}_{seq}_seed{seed}_*"))
        return g[0] if g else None
    dirs = {a: tag_dir(a) for a in arms}
    if not all(dirs.values()):
        print(f"  [skip] fig_render {seq}: dirs={ {a: bool(d) for a, d in dirs.items()} }")
        return
    rows = [("Ground truth", dirs[arms[0]], "gt")]
    for a in arms:
        # 行标 = 论文匿名名（prior stack），不用内部臂名（G2 匿名规则）
        rows.append(("prior stack (erased)", dirs[a], "render"))
    nr, nc = len(rows), len(frames)
    fig, axes = plt.subplots(nr, nc, figsize=(1.75 * nc + 0.9, 1.42 * nr))
    for i, (lbl, d, half) in enumerate(rows):
        for j, fr in enumerate(frames):
            ax = axes[i, j]
            im = _load_cmp(d, fr, half)
            if im is None:
                ax.axis("off"); continue
            ax.imshow(im); ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_visible(False)
            if half == "render" and i >= 1:
                h, w = im.shape[:2]
                zx, zy, zw, zh = int(w*0.42), int(h*0.30), int(w*0.56), int(h*0.42)
                axi = ax.inset_axes([0.66, 0.60, 0.32, 0.36])
                axi.imshow(im[zy:zy+zh, zx:zx+zw])
                axi.set_xticks([]); axi.set_yticks([])
                for sp in axi.spines.values():
                    sp.set_edgecolor(C["warm"]); sp.set_linewidth(0.9)
                ax.add_patch(plt.Rectangle((zx, zy), zw, zh, fill=False,
                                           edgecolor=C["warm"], linewidth=0.9))
        axes[i, 0].set_ylabel(rows[i][0], fontsize=7.5, rotation=0,
                              ha="right", va="center", labelpad=6)
    fig.subplots_adjust(wspace=0.03, hspace=0.03)
    save(fig, out_name or f"fig2_render_{seq}")


# ============================================================ A3. trajectory (conventional)
def _umeyama_se3(src, dst):
    """SE(3) 对齐（无尺度）：把 src 点集刚体变换到 dst。与 ATE 口径一致。"""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    S, D = src - mu_s, dst - mu_d
    H = S.T @ D
    U, _, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1] *= -1
        R = Vt.T @ U.T
    t = mu_d - R @ mu_s
    return (src @ R.T) + t


def _trj(arm, seq, seed=0):
    g = glob.glob(str(REPO / f"results/paper2_fulltable/r33_rebase_{arm}_{seq}_seed{seed}/"
                             f"datasets_bonn/*/seed_{seed}/*/plot/trj_full_final.json"))
    if not g:
        return None
    d = json.loads(Path(g[0]).read_text())
    est = np.array([np.asarray(T) for T in d["trj_est"]], dtype=np.float64)  # C2W list
    gt = np.array([np.asarray(T) for T in d["trj_gt"]], dtype=np.float64) if "trj_gt" in d else None
    return {"est": est[:, :3, 3], "gt": gt[:, :3, 3] if gt is not None else None}


def fig_trajectory(seq="crowd2", seed=0, arms=("baseline",)):
    """惯例图：GT（世界帧）+ 各臂 est（SE(3) 对齐到 GT 后绘于世界帧）。

    arms 默认只画 baseline：SWBA/gate 复合臂排除（R2_NARRATIVE §7 红线，SWBA 一字不提）。
    native 宽 ≈ 单栏槽（0.92×3.28in≈3.0in）⇒ 缩放≈1（G2-C1 修复：原 4.0in 被缩到
    0.84×，8pt 字实印 <7pt）。
    """
    fig, ax = plt.subplots(figsize=(3.0, 2.35))
    gt_plot = None
    for arm in arms:
        col, ls = fs.ARM_COLOR[arm], fs.ARM_STYLE[arm]
        t = _trj(arm, seq, seed)
        if t is None or t["gt"] is None or len(t["gt"]) != len(t["est"]):
            continue
        est_al = _umeyama_se3(t["est"], t["gt"])     # 对齐到 GT 世界帧
        if gt_plot is None:
            gt_plot = t["gt"]
        ax.plot(est_al[:, 0], est_al[:, 2], linestyle=ls, color=col, lw=1.0,
                alpha=0.85, label=ARM_LBL[arm])
        ax.plot([est_al[0, 0]], [est_al[0, 2]], "o", color=col, ms=3.5)
        ax.plot([est_al[-1, 0]], [est_al[-1, 2]], "s", color=col, ms=3.5)
    if gt_plot is not None:
        ax.plot(gt_plot[:, 0], gt_plot[:, 2], linestyle=fs.GT_STYLE, color=fs.GT_COLOR,
                lw=1.0, label="ground truth")
    ax.set_aspect("equal", "datalim")
    ax.set_xlabel("x (m)"); ax.set_ylabel("z (m)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=3,
              fontsize=7, columnspacing=1.2, handlelength=1.6)
    ax.grid(True, alpha=0.25)
    # 单面板图不加面板标号（README §6：标号用于多面板图；G2-M5）
    save(fig, f"fig3_trajectory_{seq}")


# ============================================================ B1. heavy-tail (signature)
def _scale_smax(seq, arm, seed=0):
    """返回该地图全体基元的 max-axis log-scale（真实分布，用于直方图）。"""
    g = glob.glob(str(REPO / f"results/paper2_fulltable/r33_rebase_{arm}_{seq}_seed{seed}/"
                             f"datasets_bonn/*/seed_{seed}/*/point_cloud/final/point_cloud.ply"))
    if not g:
        return None
    try:
        from plyfile import PlyData
        v = PlyData.read(g[0])["vertex"]
        s = np.stack([np.asarray(v[f"scale_{i}"], dtype=np.float64) for i in range(3)], 1)
        return s.max(1)
    except Exception:
        return None


def fig_tail():
    d = json.loads((REPO / "results/gs_compress/evidence/tail_census.json").read_text())
    # native 宽 ≈ 单栏槽（0.95×3.28in≈3.1in）⇒ 缩放≈1（G2-C1 修复：原 7.2in 在单栏
    # 环境被缩到 0.52×、字实印仅 2.7–4.6pt）。两面板纵向堆叠 + 紧凑高度。
    fig, axes = plt.subplots(2, 1, figsize=(3.1, 3.3))
    # left: real histogram of max-axis log-scale (crowd2 gate), tail shaded
    ax = axes[0]
    smax = _scale_smax("crowd2", "gate")
    if smax is not None:
        p999 = np.exp(np.percentile(smax, 99.9))
        thr = np.log(p999)
        ax.hist(smax, bins=80, color=C["base"], edgecolor="none")
        ax.axvline(thr, color=C["warm"], lw=1.0, ls="--",
                   label=f"p99.9 = {p999:.2f} m")
        ax.set_yscale("log")
        ax.set_xlabel("max-axis log-scale", fontsize=8)
        ax.set_ylabel("primitive count (log)", fontsize=8)
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=1, fontsize=7.0, handlelength=1.4)
        ax.grid(True, axis="y", alpha=0.25)
    fs.label_panel(axes[0], "a")
    # right: range inflation per sequence (mean over arms), scale vs xyz
    ax = axes[1]
    agg = {}
    for m in d["maps"]:
        agg.setdefault(m["seq"], {"scale": [], "xyz": []})
        agg[m["seq"]]["scale"].append(m["groups"]["scale"]["q0.1"]["inflation"])
        agg[m["seq"]]["xyz"].append(m["groups"]["xyz"]["q0.1"]["inflation"])
    seqs = sorted(agg, key=lambda s: np.mean(agg[s]["scale"]), reverse=True)
    labels = [SEQ_LBL.get(s, s) for s in seqs]
    scale = [np.mean(agg[s]["scale"]) for s in seqs]
    xyz = [np.mean(agg[s]["xyz"]) for s in seqs]
    x = np.arange(len(labels)); w = 0.38
    ax.bar(x - w/2, scale, w, color=C["warm"], label="scale")
    ax.bar(x + w/2, xyz, w, color=C["base"], label="xyz")
    ax.axhline(1.0, color="#333", lw=0.7, ls=":")
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7.0)
    ax.set_ylabel("range inflation", fontsize=8)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2, fontsize=7.0, columnspacing=1.0, handlelength=1.4)
    ax.grid(True, axis="y", alpha=0.25)
    fs.label_panel(axes[1], "b")
    fig.tight_layout()
    save(fig, "fig4_tail")


# ============================================================ B2. byte accounting (signature)
def fig_accounting():
    # 20-field f32 = 80 B/prim; renderer uses 14 fields (56 B); 6 accounting (24 B = 30%)
    # native 宽 ≈ 单栏槽（0.95×3.28in≈3.1in）⇒ 缩放≈1（G2-C1 修复：原 4.6in 被缩到 0.84×）。
    fig, ax = plt.subplots(figsize=(3.1, 1.5))
    total = 80.0
    ax.barh(0, 56, height=0.42, color=C["base"], edgecolor="white", linewidth=0.6,
            label="render payload (14 fields the rasteriser reads)")
    ax.barh(0, 24, left=56, height=0.42, color=C["warm"], edgecolor="white", linewidth=0.6,
            label="accounting fields (6 fields, never read; entropy-coded to near-zero)")
    ax.text(28, 0, "56 B", ha="center", va="center", fontsize=8, color="white")
    ax.text(68, 0, "24 B", ha="center", va="center", fontsize=8, color="white")
    ax.set_xlim(0, total); ax.set_yticks([]); ax.set_ylim(-0.5, 0.9)
    ax.set_xlabel("bytes per primitive (20-field f32)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.42), ncol=1, fontsize=7.5)
    save(fig, "fig5_accounting")


if __name__ == "__main__":
    print("generating paper-2 figures ...")
    # fig_pipeline() 不再默认重跑（退役；回退锚点已由 figures/ 工作区内 _programmatic_backup 持有）
    fig_render("crowd2", (125, 380, 635))
    # 第二序列（独立审稿 P1-6：不只 crowd2）——person_tracking 帧号不同于 crowd2 的网格
    # 2026-10-21: 换中间帧 245→165（A8 整改：f410 的 erased 面板残留红衣轮廓，f165 两人居中且擦除干净）
    fig_render("person_tracking", (80, 165, 410), out_name="fig2b_render_person_tracking")
    fig_trajectory("crowd2")
    fig_tail()
    fig_accounting()
    print("done.")
