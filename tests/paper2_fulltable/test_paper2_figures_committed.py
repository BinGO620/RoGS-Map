"""论文 2 图的已提交状态门禁 + 副本同步守护。

存在理由（2026-10-08，D2-028）：表侧早有 `test_paper2_codec_tables_committed.py`
的逐字节镜像守护，**图侧此前零守护**——`results/*/figs/` 的生成物手工 `cp` 进
`papers/paper2/figs/`，漂移无人抓，且正文 `\\includegraphics` 引用的图若不慎删除
只会在编译期以 `undefined` 或缺失暴露（编译脚本在 /tmp 跑、不进 CI）。

本文件补两条：
  ① 生成的图在 `results/*/figs/`（生成器输出）与 `papers/paper2/figs/`（提交副本）**逐字节一致**；
  ② 正文每个 `\\includegraphics{...}` 的文件在 `papers/paper2/figs/` **存在**（防悬空引用）。
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
# 2026-10-10 重写重构：v0 的 paper2_cvm.tex 已归档至 archive/v0_2026-10-10/。
# 图资产（figs/）与表资产（tables/）仍在活区、新稿继续用；正文 tex 现无活副本，
# 故 TEX 取「活副本优先、否则归档副本」——重写期守护不空转，新稿落地后自动指向新 tex。
TEX_LIVE = REPO / "papers/paper2/paper2_cvm.tex"
TEX_ARCHIVE = REPO / "papers/paper2/archive/v0_2026-10-10/paper2_cvm.tex"
TEX = TEX_LIVE if TEX_LIVE.exists() else TEX_ARCHIVE
PAPER_FIGS = REPO / "papers/paper2/figs"
PF_FIGS = REPO / "results/paper2_fulltable/evidence/figs"
GSC_FIGS = REPO / "results/gs_compress/figs"

# 骨架态守卫：Phase 3 重写期间活区 tex 带 "% skeleton" 标记时，正文尚无 \includegraphics，
# 终稿断言必然失败且无信息量 ⇒ 跳过（写完相应节后移除骨架标记即恢复终稿守护）。
# 与 test_paper2_dynport_section.py 同款守卫，两文件同步维护。
IS_SKELETON = TEX_LIVE.exists() and "% skeleton" in TEX_LIVE.read_text()

# 生成物 → 提交副本的镜像对（生成器：scripts/02_analysis/paper2_figures.py 与
# scripts/dynport_offline/dump_repair_render.py 写 PF_FIGS；scripts/gs_compress/make_figs.py 写 GSC_FIGS）
MIRRORS = [
    (PF_FIGS, "fig2_render_crowd2.pdf"),
    (PF_FIGS, "fig2b_render_person_tracking.pdf"),
    (PF_FIGS, "fig3_trajectory_crowd2.pdf"),
    (PF_FIGS, "fig4_tail.pdf"),
    (PF_FIGS, "fig5_accounting.pdf"),
    (PF_FIGS, "fig6_dynport_repair.pdf"),
    (PF_FIGS, "fig_teaser.pdf"),  # 首页图（Fig. 1，单栏，2026-10-18）
    (GSC_FIGS, "fig_rd_curves.pdf"),
    # fig_storage_accounting 已移出活区（2026-10-13 审阅 P2-6）：正文不引用、含 gate 臂
    # （红线），生成物留在 results/gs_compress/figs/ 作 provenance，不入 papers/paper2/figs/。
]


# fig1_pipeline 特例（2026-10-09）：唯一允许 AI 文生图的图（概念示意图、无实验数据，
# 见 papers/paper2/figures/README.md 红线表）。定稿版 = AI 生成（gpt-image-2，gen2_A，
# 人工逐字核标签后制版），不走 matplotlib 生成器 ⇒ 从上方生成器镜像对摘出，
# 改为「figures/ 工作区副本 ↔ figs/ 提交副本」镜像守护；程序版留档 _programmatic_backup。
AI_FIG_WORKSPACE = REPO / "papers/paper2/figures/fig1_pipeline"
AI_FIGS = ["fig1_pipeline.pdf", "fig1_pipeline.png"]

# AI 版几何门：定稿 = 300dpi @183mm、宽高比 3:1（换图须保持，防误换错比例/低分辨率版）。
# 2026-10-09 晚二次改版：fig1 换程序拼合真实数据总览图（paper2_fig1_overview.py，
# matplotlib，竞品式 overview），比例 3:1 → ~1.96:1 自然尺寸；门同步改版并留两版历史规格。
AI_FIG_MIN_DPI_AT_183MM = 300
AI_FIG_ASPECT_V1_RETIRED = 3.0  # v1（AI 生图）历史规格，现行见 test_ai_fig1_geometry_and_resolution


def test_ai_fig1_geometry_and_resolution():
    from PIL import Image
    im = Image.open(PAPER_FIGS / "fig1_pipeline.png")
    w, h = im.size
    # 总览图版（现行）：约 1.96:1；允许 1.8–2.1（figsize 7.2×3.55in 紧裁后自然浮动）
    assert 1.8 <= w / h <= 2.1, \
        f"fig1_pipeline.png 宽高比 {w / h:.3f} 超出总览图规格带 [1.8, 2.1]"
    eff = w / (183 / 25.4)
    assert eff >= AI_FIG_MIN_DPI_AT_183MM - 1, \
        f"fig1_pipeline.png 有效分辨率 {eff:.0f}dpi @183mm < {AI_FIG_MIN_DPI_AT_183MM}"


def test_ai_fig1_pdf_mediabox():
    # tex 实嵌的是 PDF——尺寸须为横向横幅（宽>高、比例带与 png 一致），防错包。
    import re
    raw = (PAPER_FIGS / "fig1_pipeline.pdf").read_bytes()
    m = re.search(rb"MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", raw)
    assert m, "fig1_pipeline.pdf 无 MediaBox"
    x0, y0, x1, y1 = (float(g) for g in m.groups())
    w, h = x1 - x0, y1 - y0
    assert w > h, f"pdf 非横向（{w:.0f}x{h:.0f}pt）"
    assert 1.8 <= w / h <= 2.1, f"pdf 宽高比 {w / h:.3f} 超出总览图规格带 [1.8, 2.1]"


def test_ai_fig1_workspace_mirror_byte_identical():
    for name in AI_FIGS:
        a, b = AI_FIG_WORKSPACE / name, PAPER_FIGS / name
        assert a.exists(), f"工作区副本缺失：{a}"
        assert b.exists(), f"提交副本缺失：{b}"
        assert a.read_bytes() == b.read_bytes(), \
            f"{name}: papers/paper2/figs 与 figures/fig1_pipeline 工作区漂移（须重新 cp 同步）"


def test_ai_fig1_programmatic_backup_kept():
    for ext in ("pdf", "png"):
        p = AI_FIG_WORKSPACE / f"fig1_pipeline_programmatic_backup.{ext}"
        assert p.exists(), f"程序版留档缺失：{p}（fig1 换版回退锚点）"


def test_fig1_mask_panel_is_photo_backed():
    # G2-C1 固化门（2026-10-09）：dynamic weighting 面板必须是「照片 + 掩码叠加」，
    # 不得退化为黑底剪影（dtype 域缺陷曾把 0-1 float 背景截成 0）。判据 = 提交 PNG 的
    # 面板 2 区域背景亮度中位数须达照片域水平（黑底剪影 ≈0）。
    import numpy as np
    from PIL import Image
    im = np.asarray(Image.open(PAPER_FIGS / "fig1_pipeline.png").convert("L"), dtype=float) / 255.0
    h, w = im.shape
    # 面板 2（dynamic weighting）约在 fig 横向 [0.215, 0.365]、纵向 [0.12, 0.42]（总览图版式）
    patch = im[int(h * 0.12):int(h * 0.42), int(w * 0.215):int(w * 0.365)]
    med = float(np.median(patch))
    assert med > 0.30, \
        f"fig1 面板 2 背景亮度中位数 {med:.3f} ≤ 0.30——疑似黑底剪影（G2-C1 dtype 域缺陷回归）"



def test_generated_figures_mirror_byte_identical():
    for src_dir, name in MIRRORS:
        a, b = src_dir / name, PAPER_FIGS / name
        assert a.exists(), f"生成物缺失：{a}"
        assert b.exists(), f"提交副本缺失：{b}"
        assert a.read_bytes() == b.read_bytes(), \
            f"{name}: papers/paper2/figs 与生成器输出漂移（须重新 cp 同步）"


@pytest.mark.skipif(IS_SKELETON, reason="活区新稿为骨架态，正文尚无 \\includegraphics")
def test_every_includegraphics_exists():
    tex = TEX.read_text()
    names = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex)
    assert names, "正文未发现 \\includegraphics"
    missing = [n for n in names if not (PAPER_FIGS / n).exists()]
    assert not missing, f"正文引用了不存在的图：{missing}"


def test_shared_figstyle_is_importable():
    # 共享样式模块（单一事实源）必须入库且可导入——三生成器都 import 它，
    # 缺了 clone 即 ImportError（G2-M1）。
    import importlib.util
    p = REPO / "scripts/02_analysis/paper2_figstyle.py"
    assert p.exists(), f"paper2_figstyle.py 缺失：{p}"
    spec = importlib.util.spec_from_file_location("paper2_figstyle", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.OKABE["blue"] == "#0072B2", "Okabe-Ito 基色漂移"
    assert mod.FONT_STACK[0] == "Arial", "字体栈首项应为 Arial"


def test_figure_text_size_meets_floor():
    # 图内有效印刷字号门（G2-C1 固化；按**真实排版栏宽**复算，勿用错栏宽声称）。
    # 复跑工件 = scripts/02_analysis/paper2_fig_textsize_audit.py。
    import subprocess
    r = subprocess.run(
        ["/data/conda_envs/monogs-ours/bin/python",
         str(REPO / "scripts/02_analysis/paper2_fig_textsize_audit.py")],
        cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, f"图内字号门 FAIL（<5pt）：\n{r.stdout}\n{r.stderr}"
    assert "fails: 0" in r.stdout, r.stdout


def test_figure_collisions_pass():
    # 全图碰撞审计门（G4 固化；审计器随仓入库保可复跑）。
    # 复跑工件 = scripts/02_analysis/paper2_fig_collision_audit.py + vendor/ 审计器。
    import subprocess
    r = subprocess.run(
        ["/data/conda_envs/monogs-ours/bin/python",
         str(REPO / "scripts/02_analysis/paper2_fig_collision_audit.py")],
        cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, f"图碰撞审计 FAIL：\n{r.stdout}\n{r.stderr}"
    assert "fails: 0" in r.stdout, r.stdout
