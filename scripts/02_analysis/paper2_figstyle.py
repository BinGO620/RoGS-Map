#!/usr/bin/env python
"""paper2_figstyle.py — 论文 2 出图统一样式（单一事实源）。

**为什么存在**（2026-10-09，D2-028 图片美观化轮）：三个生成器曾各写一套 rcParams——
`paper2_figures.py`（fig2/2b/3/4/5）与 `dump_repair_render.py`（fig6）用 serif 字体 +
seaborn 旧配色；`make_figs.py`（fig_rd/storage）用 Arial + Okabe-Ito。同稿图风格应统一
（README.md 全局规范），故抽成本模块，全部生成器 `import paper2_figstyle as fs`。

**规范来源**：papers/paper2/figures/README.md —— 无衬线字体、图内正文 5–7pt、
Okabe-Ito 色盲安全调色板、颜色非唯一编码、caption 不进图面、矢量优先。

**用法**：
    import sys; sys.path.insert(0, str(REPO / "scripts" / "02_analysis"))
    import paper2_figstyle as fs
    fs.apply()                       # 装载 rcParams
    fs.label_panel(ax, "a")          # 多面板图左上角 (a)(b)
    fs.save_pub(fig, out_dir, name)  # 落 pdf+png（300dpi png）
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Okabe-Ito 色盲安全调色板（Color Universal Design）──
OKABE = {
    "blue": "#0072B2", "skyblue": "#56B4E9", "green": "#009E73", "yellow": "#F0E442",
    "orange": "#E69F00", "vermillion": "#D55E00", "purple": "#CC79A7", "black": "#000000",
}
GREY = "#666666"

# ── 语义色（跨图统一）：arm / 角色 → 色 ──
# base/baseline = 蓝（前作栈）；gate/final/ours = 朱红（本文机制/强调）；GT = 灰点线
ARM_COLOR = {"baseline": OKABE["blue"], "base": OKABE["blue"],
             "swbaonly": OKABE["skyblue"], "final": OKABE["vermillion"],
             "gate": OKABE["vermillion"], "ours": OKABE["vermillion"]}
ARM_STYLE = {"baseline": "-", "base": "-", "swbaonly": (0, (4, 2)),
             "final": (0, (1, 1.5)), "gate": (0, (1, 1.5))}
GT_COLOR = GREY
GT_STYLE = (0, (1, 2))
ACCENT = OKABE["vermillion"]      # 高亮框/inset/强调（原用 #C44E52，统一到 Okabe）

# ── 字体：Arial 优先，Arial 度量兼容克隆兜底（本机无 Arial/Helvetica）──
FONT_STACK = ["Arial", "Helvetica", "Liberation Sans", "Nimbus Sans", "DejaVu Sans"]

_RC = {
    "font.family": "sans-serif",
    "font.sans-serif": FONT_STACK,
    "font.size": 8,
    "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7,
    "axes.linewidth": 0.7, "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 1.0, "lines.markersize": 3.5, "lines.markeredgewidth": 0.8,
    "grid.linewidth": 0.4, "grid.alpha": 0.25,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "legend.frameon": True, "legend.facecolor": "white", "legend.edgecolor": "none",
    "legend.framealpha": 1.0, "legend.borderaxespad": 0.4,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",  # 文字可编辑
    "figure.dpi": 150,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
}


def apply(**overrides):
    """装载统一 rcParams（可传覆盖，如 font.size）。"""
    rc = dict(_RC)
    rc.update(overrides)
    plt.rcParams.update(rc)


def label_panel(ax, letter, x=-0.02, y=1.06, size=9):
    """多面板图左上角粗体小写面板标号（README §6）。"""
    ax.text(x, y, f"({letter})", transform=ax.transAxes, fontsize=size,
            fontweight="bold", va="bottom", ha="left")


def save_pub(fig, out_dir, name, dpi=300):
    """落盘 pdf（矢量，文字可编辑）+ png（dpi）。"""
    from pathlib import Path
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{name}.pdf")
    fig.savefig(out_dir / f"{name}.png", dpi=dpi)
    plt.close(fig)
    print(f"  wrote {name}.pdf/png → {out_dir}")
