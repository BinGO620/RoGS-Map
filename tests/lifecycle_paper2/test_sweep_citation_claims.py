"""sweep_citation_claims 的门禁（跨文件错误引证类扫；成因 = 2026-09-25 关卡① 致命-1）。

守护的事实：引证类残留"必须可复跑 + 带负对照"（DISCIPLINE「整改验收轮的方法」）；
本文件即该门禁的负/正对照，并锚定当前实例（乙 prereg §0 的引证已换为 grep 证据）。
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "sweep_citation_claims", REPO / "scripts/02_analysis/sweep_citation_claims.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


mod = _load()


def test_negative_control_old_citation_flagged():
    old = '| D2-016 | `verdict_L1f_obsdebt.md` §0/§4（资源形态证伪、存在性形态未试） |'
    assert mod.scan_text(old, host_contains_phrase=False), "未标记的旧引证未被抓到"


def test_positive_control_marked_correction_passes():
    marked = ('3. **资源形态已证伪、存在性形态未试**（`verdict_L1f_obsdebt.md` §0/§4）：\n'
              '   **⚠ 更正：该引证不成立——措辞不在该文件**')
    assert not mod.scan_text(marked, host_contains_phrase=False), "带更正标记被误判"


def test_host_present_means_citation_is_valid():
    old = '（`verdict_L1f_obsdebt.md` §0/§4 存在性形态未试）'
    assert not mod.scan_text(old, host_contains_phrase=True), "宿主确含措辞时不应判红"


def test_selftest_and_live_sweep_pass():
    assert mod.selftest() == 0
    assert mod.sweep() == 0, "仓库当前存在未标记的跨文件错误引证"


def test_prereg_v2_uses_grep_evidence_not_bad_citation():
    """锚定整改事实：乙 prereg §0 必须带 grep 证据，且不再把该措辞挂在 L1f 名下。"""
    t = (REPO / "results/lifecycle_paper2/evidence/prereg_rho_existence_L1.md").read_text()
    assert "grep" in t and "0 命中" in t
    assert "该措辞**不在该文件中**" in t


# ── "必须标记"表（2026-09-27 新增；E2 在线 G1 重大-6 的机制化）──
def test_require_marker_bare_reference_flagged_without_host_name():
    """负对照：**不点宿主名**的裸引用也必须变红（这正是原实现的假绿盲区）。"""
    bare = "**禁**「首个对象级动态 SLAM」（DOGL-SLAM RA-L'26 近占）；我们 = 对象级 + 自持跟踪"
    assert "lit_dyn_mapping" not in bare, "本负对照的前提是'宿主 basename 未出现在行内'"
    assert mod.scan_require_marker(bare), "裸引用未被抓到 ⇒ 该类门失效（假绿）"


def test_require_marker_marked_reference_passes():
    marked = "**禁**「首个对象级动态 SLAM」（**DOGL-SLAM RA-L'26 近占；⚠ 非卡来源**）"
    assert not mod.scan_require_marker(marked), "带「非卡来源」被误判"


def test_require_marker_table_not_empty_and_wired_into_sweep():
    """守护"机制在位"：表非空，且 sweep() 真的消费它（防日后被摘除而测试仍绿）。"""
    assert mod.REQUIRE_MARKER, "必须标记表被清空 —— 机制摘除"
    src = (REPO / "scripts/02_analysis/sweep_citation_claims.py").read_text()
    assert "scan_require_marker((REPO / rel)" in src, "sweep() 未接线" \
        " scan_require_marker ⇒ 表在但门不在"
