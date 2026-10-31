"""paper2_tables.py 生成器测试（门禁：L1 结构 + 口径隔离 + 阳性对照）。

覆盖四条纪律（DISCIPLINE #12）：
  ① 阳性对照：本脚本自算的 SE3-ATE 必须等于 run 自报的 tracking_raw col8；
  ② 口径隔离：col8（全帧）与 col14（关键帧）分文件、分标题声明，且数值确实不同；
  ③ 数字完整性：LaTeX 单元格数字必须逐位等于 JSON（生成器不得引入新数字）；
  ④ 结构：CVM 模板风格的 LaTeX 环境配对、列数一致、`_` 已转义。

用法：/data/conda_envs/monogs-ours/bin/python -m pytest tests/paper2_fulltable -v
"""
import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("paper2_tables", REPO / "scripts/02_analysis/paper2_tables.py")
pt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pt)


@pytest.fixture(scope="module")
def table():
    return pt.build_table()


@pytest.fixture(scope="module")
def latex_dir(tmp_path_factory, table):
    d = tmp_path_factory.mktemp("latex")
    pt.write_latex(table, d)
    return d


# ── ① 覆盖与阳性对照 ──

def test_coverage_7x4(table):
    assert len(table) == len(pt.ARMS) * len(pt.SEQS) == 28
    for a in pt.ARMS:
        for s in pt.SEQS:
            v = table[(a, s)]
            assert v["ate_mean"] is not None, f"{a}/{s} 缺 ATE"
            assert v["psnr"] is not None, f"{a}/{s} 缺渲染"
            assert v["static_psnr"] is not None, f"{a}/{s} 缺静态"


def test_sim3_positive_control_matches_col8(table):
    """自算 SE3-ATE == tracking_raw col8（两种独立路径必须给出同一个数）。"""
    checked = 0
    for a in pt.ARMS:
        for s in pt.SEQS:
            v = table[(a, s)]
            for k in pt.SEEDS:
                a8, a_calc = v["ate_seeds"][k], v["sim3_ate_se3_seeds"][k]
                if a8 is None or a_calc is None:
                    continue
                checked += 1
                assert abs(a8 - a_calc) < 0.01, f"{a}/{s}/seed{k}: col8={a8} 自算={a_calc}"
    assert checked >= 60, f"阳性对照样本太少：{checked}"


def test_sim3_not_worse_than_se3(table):
    for a in pt.ARMS:
        for s in pt.SEQS:
            v = table[(a, s)]
            for k in pt.SEEDS:
                s3, s3b = v["sim3_ate_seeds"][k], v["sim3_ate_se3_seeds"][k]
                if s3 is None or s3b is None:
                    continue
                assert s3 <= s3b + 0.01, f"{a}/{s}/seed{k}: Sim3 {s3} > SE3 {s3b}"


def test_selfcheck_clean(table, latex_dir):
    assert pt.selfcheck(table, latex_dir) == []


# ── ② 口径隔离 ──

def test_col8_and_col14_are_different(table):
    same = [f"{a}/{s}" for a in pt.ARMS for s in pt.SEQS
            if table[(a, s)]["ate_mean"] is not None
            and table[(a, s)]["ate_mean"] == table[(a, s)]["kf_ate_mean"]]
    assert len(same) <= 3, f"col8 与 col14 大面积相同（疑混引）：{same}"


def test_captions_declare_protocol(latex_dir):
    main = (latex_dir / "tab1_main.tex").read_text()
    kf = (latex_dir / "tab5_ladder.tex").read_text()
    assert "all-frames protocol" in main and "ate\\_rmse\\_cm" in main
    # 2026-10-10：tab5 由"关键帧口径附表"改为"阶梯消融表"；系统表降为前作栈单列。
    # 该表标注为消融，并声明阶梯净效应是一滩水、全栈相对 Base 5/7 劣化。
    assert "Component-ladder ablation" in kf, "tab5 应为阶梯消融表"
    assert "wash" in kf and "5 of 7" in kf, "tab5 须声明阶梯净效应与劣化披露"
    assert "tab:ladder" in kf, "tab5 标签应为 tab:ladder"


# ── ③ 数字完整性（LaTeX 单元格 == JSON） ──

def _cells(tex, skip_header=True):
    body = tex.split("\\midrule", 1)[1].split("\\bottomrule")[0]
    return [ln for ln in (l.strip() for l in body.splitlines()) if ln and not ln.startswith("\\")]


def test_tab1_numbers_match_json(table, latex_dir):
    """系统表 = 前作栈单列（Base），数字须逐位等于 JSON。"""
    rows = _cells((latex_dir / "tab1_main.tex").read_text())
    assert len(rows) == len(pt.SEQS)
    for ln, s in zip(rows, pt.SEQS):
        parts = [p.strip() for p in ln.replace("\\\\", "").split("&")]
        assert len(parts) - 1 == len(pt.MAIN_ARMS), f"主表列数应 = {len(pt.MAIN_ARMS)}"
        for p, a in zip(parts[1:], pt.MAIN_ARMS):
            v = table[(a, s)]
            if v["ate_mean"] is None:
                assert p == "--"
                continue
            m, sd = p.replace("$\\pm$", "|").split("|")
            assert abs(float(m) - v["ate_mean"]) < 0.005, f"{a}/{s}: {m} vs {v['ate_mean']}"
            assert abs(float(sd) - v["ate_sd"]) < 0.005, f"{a}/{s}: sd {sd} vs {v['ate_sd']}"


def test_ladder_table_has_full_arms(table, latex_dir):
    """附表（tab:ladder）须保留完整四梯（审计用），数字逐位等于 JSON。"""
    rows = _cells((latex_dir / "tab5_ladder.tex").read_text())
    assert len(rows) == len(pt.SEQS)
    for ln, s in zip(rows, pt.SEQS):
        parts = [p.strip() for p in ln.replace("\\\\", "").split("&")]
        assert len(parts) - 1 == len(pt.ARMS), f"阶梯表列数应 = {len(pt.ARMS)}"
        for p, a in zip(parts[1:], pt.ARMS):
            v = table[(a, s)]
            m = p.replace("$\\pm$", "|").split("|")[0]
            assert abs(float(m) - v["ate_mean"]) < 0.005, f"ladder {a}/{s}: {m} vs {v['ate_mean']}"


# tab2_pt_seed 表已于 2026-10-09 删除（正文零 \input 的死件）；其逐 seed/Sim3 读数仍在
# tables_paper2_preview.json/md 中保留，本测试不再核。


# ── ④ LaTeX 结构 ──

def test_latex_files_exist(latex_dir):
    names = {"tab1_main.tex", "tab5_ladder.tex", "tab2r_render.tex",
             "tab3s_static.tex", "tab4_efficiency.tex"}
    assert names <= {p.name for p in latex_dir.glob("*.tex")}


def test_latex_environments_balanced(latex_dir):
    for f in sorted(latex_dir.glob("tab*.tex")):
        t = f.read_text()
        for env in ("table*", "table", "tabular", "center"):
            assert t.count(f"\\begin{{{env}}}") == t.count(f"\\end{{{env}}}"), f"{f.name}: {env} 不配对"


def test_latex_column_counts(latex_dir):
    for f in sorted(latex_dir.glob("tab*.tex")):
        t = f.read_text()
        body = t.split("\\midrule", 1)[0]
        header = [ln for ln in body.splitlines() if ln.strip().endswith("\\\\")][-1]
        ncol = header.count("&") + 1
        for ln in _cells(t):
            assert ln.count("&") + 1 == ncol, f"{f.name}: 列数不一致 -> {ln}"


def test_tex_escape():
    assert pt.tex_escape("person_tracking2") == "person\\_tracking2"
    assert pt.tex_escape("a&b%c#d") == "a\\&b\\%c\\#d"


def test_texseqlabels_are_escaped(latex_dir):
    t = (latex_dir / "tab1_main.tex").read_text()
    assert "person\\_tracking &" in t
    assert re.search(r"(?<!\\)person_tracking ", t) is None, "存在未转义的下划线"
