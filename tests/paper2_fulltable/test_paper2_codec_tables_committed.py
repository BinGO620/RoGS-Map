"""论文 2 codec 表（tab_rd / tab_storage）的已提交状态门禁 + 副本同步守护。

存在理由（关卡② G2 2026-10-05，M4/M5）：
  * M4：`test_paper2_tables.py` 只测 `paper2_tables.write_latex()`（不产 tab_rd/tab_storage），
    `grep tab_rd tests/` 曾零命中 ⇒ 这两张真正被 \\input 的表**无任何门**。
  * M5：`papers/paper2/tables/{tab_rd,tab_storage}.tex` 是 `evidence/latex/` 生成物的**手工副本**，
    无脚本/测试保持同步 ⇒ 漂移无守护。

本文件补两条：① 数字逐位 == JSON 工件（tab_rd 各工作点 ratio/psnr、tab_storage 区间端点）；
② `papers/paper2/tables/` 与生成器输出 `evidence/latex/` 逐字节一致（两份都入库的副本必须同步）。
"""
import json
import re
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
RD = REPO / "results/gs_compress/evidence/rd"
EVLATEX = REPO / "results/paper2_fulltable/evidence/latex"
PAPERTABLES = REPO / "papers/paper2/tables"
WC = REPO / "results/gs_compress/evidence/storage_census.json"


def _body(tex):
    """tabular 数据行：`\\midrule` 之后到 `\\bottomrule` 之间，丢掉分组标题行与裸 rule。

    2026-10-09：tab_rd 改 booktabs 风格（\\toprule/\\midrule/\\bottomrule），
    且含 `\\multicolumn{8}{@{}l}{\\emph{...}}` 分组标题行（非数据行，须剔）。
    """
    b = tex.split("\\midrule", 1)[1].split("\\bottomrule", 1)[0]
    out = []
    for ln in b.strip().splitlines():
        s = ln.strip()
        if not s or s == "\\midrule":
            continue
        if s.startswith("\\multicolumn"):   # 分组标题行
            continue
        out.append(s.rstrip("\\\\").strip())
    return out


def _cells(ln):
    cs = [c.strip() for c in ln.replace("\\\\", "").split("&")]
    cs[0] = cs[0].replace("\\quad", "").strip()   # 去掉行首缩进宏
    return cs


def _num(s):
    """从单元格取数值，去掉 $\\times$/$\\pm$ 等 LaTeX 包装。"""
    return float(s.replace("$\\times$", "").replace("$", "").replace("\\,", "").strip())


def test_tab_rd_structure_and_numbers():
    """tab_rd 结构（列数）+ 数字逐位 == 工件（L2/L2S/lossless-baselines/L3 baseline）。

    2026-10-09 改版：8 列（Method/quant/comp/B-per-prim/full/Δ/static/held-out），
    booktabs 风格；新增 4 行 lossless 通用基线带（zlib/zstd/lzma/blosc2，同分母）。
    2026-10-15（审稿 R4-P3）：再增 2 行通用**有损**基线带（blosc2 TRUNC_PREC 16/8，
    同输入同分母、无训练），使 6× 工作点不再只与无损基线对照；其渲染质量未测 ⇒ 质量列记 '--'。
    2026-10-16（R4-P3 方案 A′）：再增 1 行 **learned 压缩器**基线（SOG，ECCV'24，
    官方非排序通路、无训练；同分母，记账 6 字段 lzma 旁路计入分子），并入有损组
    （页码硬顶 14：独立组头会顶破一页，实测）。未量化档 1.81× 只写 §5 正文。
    2026-10-16（R4-P3 方案 A′ 第二基线）：再增 1 行 **Niedermayr c3dgs（CVPR'24）**，并入同一有损组。
    它是以冻结地图为初始化 + 5000 步 QAT 渲染监督微调的"重训再压"（Δ 可为正）；其参考实现
    **无随机种子** ⇒ 题注登记跑间离散度。加行后实测 15 页 ⇒ 压 `\arraystretch` 0.90 + 削题注，
    压回 14 页。
    行数 = 1 source + 4 lossless + 2 blosc2 + 2 learned + 3 codec + 3 ablation = 15。
    """
    tex = (EVLATEX / "tab_rd.tex").read_text()
    rows = _body(tex)
    assert len(rows) == 15, f"tab_rd 应 15 行（1+4+2+2+3+3），实 {len(rows)}"
    for ln in rows:
        assert len(_cells(ln)) == 8, f"tab_rd 列数应 8：{ln}"
    src_row = rows[0]
    lossless_rows, lossy_rows = rows[1:5], rows[5:7]
    learned_rows = rows[7:9]
    codec_rows, abl_rows = rows[9:12], rows[12:15]

    def src_mean(pat):
        ps = [json.loads(f.read_text())["render"]["mean_psnr"] for f in RD.glob(pat)]
        return float(np.mean(ps))
    # source 行：comp=1.00, B/prim=80, full PSNR == baseline 均值；held-out Δ = 0
    s = _cells(src_row)
    assert s[0].startswith("source")
    assert abs(_num(s[2]) - 1.0) < 0.01
    assert abs(_num(s[3]) - 80.0) < 0.01
    assert abs(_num(s[4]) - src_mean("L2_*_baseline.json")) < 0.01, "source L2 PSNR 不符"
    assert abs(_num(s[7]) - 0.0) < 0.01, "source held-out Δ 应为 0"

    # lossless 带：ratio == posthoc_baselines.json（同分母），Δ=0（无损）
    ph = json.loads((RD / "posthoc_baselines.json").read_text())["splits"]["L2"]["summary"]
    keys = ["zlib", "zstd", "lzma", "blosc2"]
    for row, key in zip(lossless_rows, keys):
        c = _cells(row)
        assert "lossless" in c[0]
        assert abs(_num(c[2]) - ph[f"ratio_{key}"]["mean"]) < 0.01, f"{key} ratio 不符"
        assert abs(_num(c[5]) - 0.0) < 0.01, f"{key} 无损 Δ 应为 0"
        assert abs(_num(c[7]) - 0.0) < 0.01, f"{key} 无损 held-out Δ 应为 0"

    # 通用有损基线带：ratio == posthoc_baselines.json（同分母）；渲染质量未测 ⇒ 质量列 '--'
    for row, key in zip(lossy_rows, ["blosc2_trunc16", "blosc2_trunc8"]):
        c = _cells(row)
        assert "lossy" in c[0]
        assert abs(_num(c[2]) - ph[f"ratio_{key}"]["mean"]) < 0.01, f"{key} ratio 不符"
        assert c[4] == "--" and c[5] == "--", f"有损基线质量列应为 '--'：{row}"

    # learned 基线行（2026-10-16，R4-P3 方案 A′）：ratio/PSNR/Δ/static == learned_sog_L2.json 均值
    sog2 = json.loads((RD / "learned_sog_L2.json").read_text())["rows"]
    src2m = src_mean("L2_*_baseline.json")
    for row, cfg in zip(learned_rows, ["jxl_quant"]):
        c = _cells(row)
        assert "SOG" in c[0], f"learned 行标签应含 SOG：{row}"
        rs = [r["ratio_full"] for r in sog2 if r["config"] == cfg]
        ps = [r["render"]["mean_psnr"] for r in sog2 if r["config"] == cfg and r.get("render")]
        ss = [r["render"]["mean_static_psnr"] for r in sog2 if r["config"] == cfg
              and r.get("render") and r["render"].get("mean_static_psnr") is not None]
        assert abs(_num(c[2]) - float(np.mean(rs))) < 0.01, f"SOG {cfg} ratio 不符"
        assert abs(_num(c[4]) - float(np.mean(ps))) < 0.01, f"SOG {cfg} PSNR 不符"
        assert abs(_num(c[5]) - (float(np.mean(ps)) - src2m)) < 0.01, f"SOG {cfg} Δ 不符"
        assert abs(_num(c[6]) - float(np.mean(ss))) < 0.01, f"SOG {cfg} static PSNR 不符"

    # 第二 learned 基线（2026-10-16，R4-P3 方案 A′）：Niedermayr c3dgs
    # ratio/PSNR/static == learned_nied_L2.json 均值；held-out Δ == L3 均值 − 源
    nied2 = json.loads((RD / "learned_nied_L2.json").read_text())["rows"]
    nied3 = json.loads((RD / "learned_nied_L3.json").read_text())["rows"]
    assert len(nied2) == 42 and len(nied3) == 36, \
        f"Niedermayr 必须覆盖整个 split（L2 {len(nied2)}/42, L3 {len(nied3)}/36）"
    row = learned_rows[1]
    c = _cells(row)
    assert "Niedermayr" in c[0], f"第二 learned 行标签应含 Niedermayr：{row}"
    p2 = [r["render"]["mean_psnr"] for r in nied2]
    ss2 = [r["render"]["mean_static_psnr"] for r in nied2
           if r["render"].get("mean_static_psnr") is not None]
    assert abs(_num(c[2]) - float(np.mean([r["ratio_full"] for r in nied2]))) < 0.01, "Nied ratio 不符"
    assert abs(_num(c[4]) - float(np.mean(p2))) < 0.01, "Nied PSNR 不符"
    assert abs(_num(c[5]) - (float(np.mean(p2)) - src2m)) < 0.01, "Nied Δ 不符"
    assert abs(_num(c[6]) - float(np.mean(ss2))) < 0.01, "Nied static PSNR 不符"
    src3m = src_mean("L3_*_baseline.json")
    p3 = [r["render"]["mean_psnr"] for r in nied3]
    assert abs(_num(c[7]) - (float(np.mean(p3)) - src3m)) < 0.01, "Nied held-out Δ 不符"

    # codec 工作点：ratio == l2_summary 均值；held-out Δ == L3 泛化 PSNR - 源 PSNR
    l2 = json.loads((RD / "l2_summary.json").read_text())
    src3 = src_mean("L3_*_baseline.json")
    for row, name in zip(codec_rows, ["near_lossless", "mid", "aggressive"]):
        rs = [v[name]["ratio_full"] for v in l2.values() if name in v]
        got = _num(_cells(row)[2])
        assert abs(got - float(np.mean(rs))) < 0.01, f"{name} ratio {got} vs {np.mean(rs)}"
        assert "--" not in row
        # held-out Δ 列：从 L3 泛化聚合复算（与 paper2_codec_tables.l3_row 同口径）
        bits = {"near_lossless": "16,8,8,8,8", "mid": "10,6,6,6,6", "aggressive": "8,4,4,4,4"}[name]
        pn3s = []
        for f in RD.glob("L3_*_rd_table.json"):
            try:
                d = json.loads(f.read_text())
            except Exception:
                continue
            for r in d.get("rows", []):
                if r.get("render") and r.get("bits") == [int(x) for x in bits.split(",")]:
                    pn3s.append(r["render"].get("mean_psnr"))
        if pn3s:
            expect = float(np.mean(pn3s)) - src3
            assert abs(_num(_cells(row)[7]) - expect) < 0.01, \
                f"{name} held-out Δ {_num(_cells(row)[7])} vs {expect:.2f}"

    # 消融行：ratio/PSNR == l2s_summary；held-out/static 为 '--'
    l2s = json.loads((RD / "l2s_summary.json").read_text())
    for row, name in zip(abl_rows, ["near_lossless", "mid", "aggressive"]):
        c = _cells(row)
        assert "+ voxel merge" in c[0]
        rs = [v[name]["ratio_full"] for v in l2s.values() if name in v]
        ps = [v[name]["psnr"] for v in l2s.values() if name in v]
        assert abs(_num(c[2]) - float(np.mean(rs))) < 0.01
        assert abs(_num(c[4]) - float(np.mean(ps))) < 0.01
        assert c[6] == "--" and c[7] == "--", f"消融行 static/held-out 应为 '--'：{row}"


def test_tab_storage_structure_and_interval():
    """tab_storage 结构 + 区间端点 == storage_census.json。"""
    tex = (EVLATEX / "tab_storage.tex").read_text()
    rows = _body(tex)
    d = json.loads(WC.read_text())["rows"]
    assert len(rows) == len(d), f"tab_storage 应 {len(d)} 行，实 {len(rows)}"
    gbs = []
    for r in d:
        m = r["mb"]
        if "baseline" in m and "gate" in m:
            gbs.append(m["gate"] / m["baseline"] * 100 - 100)
    cap = tex.split("\\caption{", 1)[1]
    assert f"{min(gbs):+.1f}" in cap and f"{max(gbs):+.1f}" in cap, "区间端点不符"
    # 不得报数值均值（sign-mixed 分布均值无意义）；"not a mean" 的说明性提及允许
    assert not re.search(r"mean\s*[+\-−]?\d", cap), "存储表不应报数值均值"


def test_paper_tables_are_byte_identical_to_generator_output():
    """M5：papers/paper2/tables/ 的副本必须与 evidence/latex/ 生成物逐字节一致。

    2026-10-22：`tab1_main.tex` 与 `tab_storage.tex` 移入 `tables/archive/`——两者零
    `\\input`（前者内容与 `tab_baseline.tex` 末行重复；后者是 D2-031 裁定从 §6 删除后
    留下的死件），留在活区只会让「哪些表真进 PDF」变得模糊。归档原文仍在
    `evidence/latex/` 供追溯。本测试因此只守护**当前被正文 `\\input` 的表**，
    并以正文明文作唯一真源，防止将来再挂一张死表而不自知。
    """
    tex = (REPO / "papers/paper2/paper2_cvm.tex").read_text()
    inputs = set(re.findall(r"\\input\{tables/([^}]+)\}", tex))
    assert inputs, "正文未 \\input 任何表（解析失败？）"
    # 生成物落在 evidence/latex/ 的镜像表（其余被 \input 的表由别的生成器产出，不在此守护）
    mirrored = ("tab_rd.tex", "tab4_efficiency.tex", "tab2r_render.tex",
                "tab3s_static.tex", "tab_dynport.tex")
    for name in mirrored:
        assert name in inputs, f"{name} 已不被正文 \\input（死表应归档）"
        a, b = (EVLATEX / name), (PAPERTABLES / name)
        assert a.exists() and b.exists(), f"缺 {name}"
        assert a.read_bytes() == b.read_bytes(), \
            f"{name}: papers/paper2/tables 与生成器输出漂移（须重新 cp 同步）"
    # 活区不得出现未被 \input 的表（死件应归档）
    orphans = sorted({p.name for p in PAPERTABLES.glob("*.tex")} - inputs)
    assert not orphans, f"papers/paper2/tables 有未 \\input 的表（应移入 archive/）：{orphans}"


def test_generalisation_prose_dynamic_tum_matches_evidence():
    """§5 Generalisation 段 f3_wk_rpy 动态 TUM 句的数字必须与 L3p 判据一致（2026-10-13 增补）。

    守护的事实：正文"near-lossless 动态区损失 ≤0.007 dB across six runs"不是手写，
    而是 `evidence/rd/L3p_f3_wk_rpy_{rb,gate}_s{0,1,2}_rd_table.json` 的可复现读数
    （canonical TUM dynamic_mask 分区渲染，2026-10-13）。
    """
    tex = (REPO / "papers/paper2/paper2_cvm.tex").read_text()
    seg = tex.split(r"\paragraph{Generalisation.}", 1)[1]
    seg = seg.split(r"\paragraph{Cost.}", 1)[0]
    tags = [f"L3p_f3_wk_rpy_{arm}_s{seed}" for arm in ("rb", "gate") for seed in (0, 1, 2)]
    dels = []
    for tag in tags:
        d = json.load(open(RD / f"{tag}_rd_table.json"))
        rows = d["rows"]
        base = next(r["render"]["mean_psnr"] for r in rows if r.get("kind") == "baseline")
        for r in rows:
            if r.get("kind") == "baseline" or r.get("alloc") is None:
                continue
            if r.get("bits") == [16, 8, 8, 8, 8]:   # 近无损点
                dels.append(r["render"]["mean_psnr"] - base)
    assert len(dels) == 6, f"近无损点应有 6 组合，实为 {len(dels)}"
    worst = max(abs(d) for d in dels)
    assert rf"\gate{{0.008}}" in seg, "正文 0.008 dB 与判据不符"
    assert worst <= 0.008, f"实测最差损失 {worst:.4f} 超过正文 0.008"
    assert "six runs" in seg, "正文 six runs 缺失"
    assert "freiburg3" in seg.replace("\\_", "_"), "正文 f3_wk_rpy 序列名缺失"
