"""论文 2 §7（贡献③，DynPort-Offline）的门禁。

存在理由（D2-028，2026-10-08）：贡献栏由 2 条改 3 条、正文插新 §7、并入机写对照表
`tab_dynport.tex`。原测试集不守护贡献数、新节与这张表的数字。本文件补三条：
  ① 贡献栏计数（"Our contributions are three"）且无残留 "two"；
  ② 新节 `sec:dynport-offline` 存在且被 `\\input` 的 `tab_dynport.tex` 在其内；
  ③ 表内数字逐位 == 两个 manifest（离线 21 格区间 + 在线 v2 批比值）；
  ④ 镜像逐字节一致（与 codec 表同一纪律；此处独立断言以防单文件被绕过）。
"""
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
# 2026-10-10 重写重构：v0 tex 已归档；活副本优先，否则用归档副本（重写期守护不空转）。
TEX_LIVE = REPO / "papers/paper2/paper2_cvm.tex"
TEX = TEX_LIVE if TEX_LIVE.exists() else REPO / "papers/paper2/archive/v0_2026-10-10/paper2_cvm.tex"
EVLATEX = REPO / "results/paper2_fulltable/evidence/latex"
PAPERTABLES = REPO / "papers/paper2/tables"
OFF_MAN = REPO / "results/dynport_offline/evidence_L3/manifest_offline_L1_L3.json"
ON_MAN = REPO / "results/dynport/evidence/manifest_L1_v2.json"
ON_SEQS = ["crowd2", "balloon2"]

# 骨架态守卫：Phase 3 重写期间活区 tex 带 "% skeleton" 标记时，§1 贡献栏/§7 尚未落笔，
# 终稿断言必然失败且无信息量 ⇒ 跳过（写完相应节后移除骨架标记即恢复终稿守护）。
# 与 test_paper2_figures_committed.py 同款守卫，两文件同步维护。
IS_SKELETON = TEX_LIVE.exists() and "% skeleton" in TEX_LIVE.read_text()


def _skeleton_skip(reason):
    return pytest.mark.skipif(IS_SKELETON, reason=reason)


@_skeleton_skip("活区新稿为骨架态，§1 贡献栏未落笔")
def test_contribution_count_is_three():
    tex = TEX.read_text()
    # 新稿（2026-10-12 Phase 3 重写）Intro 用 "we make three map-side contributions"
    # （v0 旧断言 "Our contributions are three" 已随 v0 归档）。
    assert "three map-side contributions" in tex, "贡献栏应为 three"
    # 贡献栏段内不得残留 "contributions are two"
    assert not re.search(r"contributions are two", tex), "残留 'contributions are two'"


@_skeleton_skip("活区新稿为骨架态，§7 未落笔")
def test_dynport_section_and_table_present():
    tex = TEX.read_text()
    # 新稿 §7 label = sec:offline（v0 旧 label sec:dynport-offline 已随 v0 归档）
    assert r"\label{sec:offline}" in tex, "缺 §7 label"
    # 表在其所属节内（label 到下一个 \section 之前出现 \input）
    seg = tex.split(r"\label{sec:offline}", 1)[1]
    seg = seg.split(r"\section{", 1)[0]
    assert r"\input{tables/tab_dynport.tex}" in seg, "tab_dynport 未被 §7 内 \\input"


def test_table_numbers_match_manifests():
    tex = (EVLATEX / "tab_dynport.tex").read_text()
    off = json.loads(OFF_MAN.read_text())["summary"]
    on = json.loads(ON_MAN.read_text())["summary"]

    j1 = [v["J1"] for v in off.values()]
    j2 = [v["J2"] for v in off.values()]
    j3 = [v["J3"] for v in off.values()]
    j4 = [v["J4_ratio"] for v in off.values()]
    n_cells = len(off)
    n_pass = sum(1 for v in off.values()
                 if abs(v["J3"]) <= 0.25 and v["J1"] >= 2.5 and v["J2"] <= 0.70)
    assert n_pass == n_cells, "离线非全过，但表按全过呈现"

    # 离线区间端点（与生成器同格式：符号用数学模式，区间端点用 en dash 或 "to"）
    assert f"${min(j1):+.2f}$--${max(j1):+.2f}$" in tex
    assert f"{min(j2):.2f}--{max(j2):.2f}" in tex
    assert f"${min(j3):+.3f}$ to ${max(j3):+.3f}$" in tex
    assert f"{min(j4):.2f}--{max(j4):.2f}" in tex
    assert f"pass {n_pass}/{n_cells}" in tex

    # 在线比值（v2 批，定序 crowd2/balloon2）
    assert f"+{on[ON_SEQS[0]]['J1']:.2f}/+{on[ON_SEQS[1]]['J1']:.2f}" in tex
    assert f"{on[ON_SEQS[0]]['J2']:.2f}/{on[ON_SEQS[1]]['J2']:.2f}" in tex
    assert f"{on[ON_SEQS[0]]['J3']:+.2f}/{on[ON_SEQS[1]]['J3']:+.2f}" in tex
    c0 = on[ON_SEQS[0]]["J4_overhead"] * 100
    c1 = on[ON_SEQS[1]]["J4_overhead"] * 100
    assert f"+{c0:.1f}/+{c1:.1f}" in tex


def test_table_mirror_byte_identical():
    a, b = EVLATEX / "tab_dynport.tex", PAPERTABLES / "tab_dynport.tex"
    assert a.exists() and b.exists()
    assert a.read_bytes() == b.read_bytes(), "tab_dynport 镜像漂移"


def _dynport_section(tex):
    seg = tex.split(r"\label{sec:offline}", 1)[1]
    return seg.split(r"\section{", 1)[0]


@_skeleton_skip("活区新稿为骨架态，§7 未落笔")
def test_section_prose_gate_numbers_match_manifests():
    """§7 散文里 `\\gate{}` 的数字必须与 manifest 一致（G2 重大：prose 无机器守护）。"""
    tex = TEX.read_text()
    seg = _dynport_section(tex)
    off = json.loads(OFF_MAN.read_text())["summary"]
    on = json.loads(ON_MAN.read_text())["summary"]

    j1 = [v["J1"] for v in off.values()]
    j2 = [v["J2"] for v in off.values()]
    j3 = [v["J3"] for v in off.values()]
    j4 = [v["J4_ratio"] for v in off.values()]
    n_cells = len(off)

    # 结果段（J1/J2 区间 + J3 端点 + 21 格 + 离线 cost 区间；新稿格式，2026-10-12）
    assert rf"\gate{{{min(j1):.2f}--{max(j1):.2f}}}" in seg, "J1 区间与 manifest 不符"
    assert rf"\gate{{{min(j2):.2f}--{max(j2):.2f}}}" in seg, "J2 区间与 manifest 不符"
    j3_lo = f"{min(j3):.2f}".replace("-", "-")
    j3_hi = f"{max(j3):.2f}"
    assert rf"\gate{{${j3_lo}$}} to \gate{{+{j3_hi}}}" in seg, "J3 端点与 manifest 不符"
    assert rf"\gate{{{n_cells}/{n_cells}}}" in seg, "格数与 manifest 不符"
    assert rf"\gate{{{min(j4):.2f}--{max(j4):.2f}$\times$}}" in seg, "离线 cost 区间不符"

    # 放置段（在线 cost +c%/+d%、J3 −a/−b；在线 J1/J2 只在表内守护，正文不重复）
    seq0, seq1 = ON_SEQS
    c0 = on[seq0]["J4_overhead"] * 100
    c1 = on[seq1]["J4_overhead"] * 100
    assert rf"\gate{{+{c0:.0f}\%/+{c1:.0f}\%}}" in seg, "在线 cost 不符"
    j3_on0 = f"{on[seq0]['J3']:.2f}"
    j3_on1 = f"{on[seq1]['J3']:.2f}"
    assert rf"\gate{{${j3_on0}/{j3_on1}$}}" in seg, "在线 J3 不符"
    assert rf"\gate{{{min(j4):.2f}--{max(j4):.2f}$\times$}}" in seg, "离线 cost 区间不符"



def test_4d_12bit_prose_matches_evidence():
    """§5 4D codec 12bit 句的 `\\gate{}` 数字必须与 evidence_4d12bit 判据一致（2026-10-13 增补）。

    守护的事实：正文 12bit 泛化句（"3.9--4.7×，J1 85--97%，四序列全过"）不是手写数字，
    而是 ratio_12bit.json + <seq>_R1_12bit_samepose.json 的可复现读数。
    """
    tex = TEX_LIVE.read_text()
    seg = tex.split(r"\paragraph{Compressing the repaired layers.}", 1)[1]
    seg = seg.split(r"\input{tables/tab4d_ablation.tex}", 1)[0]
    ev = REPO / "results/dynport_offline/evidence_4d12bit"
    r12 = json.load(open(ev / "ratio_12bit.json"))
    ratios = [r12[f"{s}_R1"]["ratio"] for s in ["crowd2", "crowd", "balloon2", "person_tracking"]]
    keeps = []
    for s in ["crowd2", "crowd", "balloon2", "person_tracking"]:
        d = json.load(open(ev / f"{s}_R1_12bit_samepose.json"))
        r1 = {"crowd2": 7.95, "crowd": 5.76, "balloon2": 6.08, "person_tracking": 7.38}[s]
        keeps.append(100 * d["J1_samepose_bad_psnr_delta"]["median"] / r1)
        # 判据全过
        assert d["J1_samepose_bad_psnr_delta"]["median"] >= 2.5, f"{s} J1 未过线"
        assert d["J2_samepose_bad_dl1_ratio"]["median"] <= 0.70, f"{s} J2 未过线"
        assert -0.25 <= d["J3_samepose_static_delta"]["median"] <= 0.25, f"{s} J3 未过线"
    rlo, rhi = f"{min(ratios):.1f}", f"{max(ratios):.1f}"
    klo, khi = f"{min(keeps):.0f}", f"{max(keeps):.0f}"
    assert rf"\gate{{{rlo}--{rhi}$\times$}}" in seg, f"12bit 压缩比区间 {rlo}--{rhi} 与证据不符"
    assert rf"\gate{{{klo}--{khi}\%}}" in seg, f"12bit J1 保持率 {klo}--{khi} 与证据不符"
    assert "all four sequences" in seg, "12bit 四序列全过句缺失"
