"""关卡① 类扫门禁的负/正对照（脚本 = scripts/02_analysis/gate1_class_sweep.py）

来源：2026-09-20 第 6 轮 slam-critic 审查指出——门禁"从未演示能变红"，其 UNMARKED=0 不构成证据。
本文件即该门禁的**负对照**：注入已知残留必须变红（rc=1），干净文本必须为绿（rc=0），
并覆盖第 6 轮抓到的两个自掩蔽缺陷（MARKERS 裸词 / 轮次数字失明）。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/02_analysis/gate1_class_sweep.py"


def _load():
    spec = importlib.util.spec_from_file_location("gate1_class_sweep", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sweep_mod = _load()


def _scan(text: str, capsys) -> tuple[int, int, int, int]:
    """返回 (命中, UNMARKED, ALLOWED, 轮次非规范)，并吞掉打印。"""
    out = sweep_mod.scan_lines("fixture.md", text.split("\n"))
    capsys.readouterr()
    return out


# ── 负对照：注入已知残留 ⇒ 必须变红 ─────────────────────────────────────────────
def test_negative_control_stale_claim_without_marker(capsys):
    """口径类残留（无撤回标记）必须计为 UNMARKED。"""
    _, unmarked, _, _ = _scan("本判决：crowd 族 = 机制退化、离线不可评测（+22% 基元）。", capsys)
    assert unmarked >= 1, "注入的口径残留未被抓到 ⇒ 门禁失效"  # 该行含两个口径关键词


def test_negative_control_stale_round_number(capsys):
    """旧轮次写法必须计为 ROUND?（第 6 轮缺陷 (b)：对轮次数字失明）。"""
    _, _, _, rounds_bad = _scan("本次整改已完成，待第 5 轮复核。", capsys)
    assert rounds_bad >= 1, "旧轮次写法未被抓到 ⇒ 轮次一致性检查失效"


def test_negative_control_stale_budget(capsys):
    """旧预算（无标记）必须计为 UNMARKED。"""
    _, unmarked, _, _ = _scan("候选 0 的后续条件成立后再 2–4 run。", capsys)
    assert unmarked >= 1, "旧预算未被抓到 ⇒ 预算类失效"


def test_no_self_masking_by_bare_words(capsys):
    """自掩蔽回归（第 6 轮缺陷 (a)）：仅含"四轮"字样的旧轮次行**不得**因裸词被判 MARKED。

    旧实现中 MARKERS 含裸词"四轮"，于是"待四轮"被自匹配 ⇒ UNMARKED 恒 0。
    """
    _, _, _, rounds_bad = _scan("该项待四轮复核。", capsys)
    assert rounds_bad >= 1, "旧轮次写法被裸词自掩蔽了"


# ── 正对照：带撤回标记/规范轮次 ⇒ 必须为绿 ────────────────────────────────────
def test_positive_control_marked_claim_passes(capsys):
    text = ("1. 地图病理：~~不透明度中位数 0.647→1.000~~（⚠️ 2026-09-20 §8 C2 撤回：无工件键）\n"
            "轮次见 DECISIONS.md D1-003（单一事实源）。")
    _, unmarked, _, rounds_bad = _scan(text, capsys)
    assert (unmarked, rounds_bad) == (0, 0), "带标记 + 指针式轮次的文本被判红 ⇒ 过度报警"


def test_round_number_outside_ledger_is_flat(capsys):
    """单一事实源不变式：非账本文件出现轮次数字必须计 ROUND-dup。"""
    _, _, _, rounds_bad = _scan("本文件状态：关卡① 已送 7 轮，待复核。", capsys)
    assert rounds_bad >= 1, "非账本文件的轮次数字未被抓到 ⇒ 单一事实源失效"


def test_ledger_accepts_canonical_round(capsys):
    """账本内规范轮次写法必须放行。"""
    out = sweep_mod.scan_lines("DECISIONS.md", ["关卡① 已送 7 轮（第 7 轮 = Accept-with-conditions）。"], True)
    assert out[3] == 0, f"账本内规范写法被误判：{out}"


def test_allowlist_passes_only_documented_context(capsys):
    """放行只对已写明理由的语境生效（R7 原文引用）。"""
    _, unmarked, allowed, _ = _scan('累计 15 run ≫ R7 的"L1 = 2–4 run、击杀只补 1–2 seed"。', capsys)
    assert (unmarked, allowed) == (0, 1)


def test_d2014_ledger_sunk_cost_allowed_but_bare_claim_red(capsys):
    """D2-014 账本行可逆性列的沉没成本描述放行（呈报事实，非预算主张）；
    同一关键词的裸预算主张仍必须红（防放行过宽自掩蔽）。"""
    _, unmarked, allowed, _ = _scan(
        '乙实装前零成本；实装后 default-off 单 commit 可停；L1 沉没 ≈2h GPU；丙未实装零成本', capsys)
    assert (unmarked, allowed) == (0, 1)
    _, unmarked2, _, _ = _scan('下一批预算 2h GPU 跑完即收口。', capsys)
    assert unmarked2 >= 1, "裸预算主张未被预算类抓到"


# ── 内部交叉引用一致性（2026-10-01 新增；来源 = swba_lifecycle G4 复核，P30 类）──────
def test_voidref_negative_control_unmarked_ref_red(capsys):
    """已作废标签的**未标注**引用点必须计 VOIDREF（P30 类：整改按点改不按类扫）。

    注意：本 fixture **不得**含"作废/不成立/~~"等标记词（否则自掩蔽）。"""
    lines = ["- face 极见 §2-B 的说明（本行无任何标记）。"]
    n = sweep_mod.scan_void_refs(
        "results/swba_lifecycle/evidence/prereg_swba_lifecycle.md", lines)
    capsys.readouterr()
    assert n >= 1, "已作废标签的裸引用未被抓到 ⇒ 类扫门禁失效"


def test_voidref_marked_ref_passes(capsys):
    """带作废标记的引用点必须放行（防过度报警）。"""
    lines = ["- §2-B〔已作废，见 §9〕；§2-C〔该设计不成立〕。"]
    n = sweep_mod.scan_void_refs(
        "results/swba_lifecycle/evidence/prereg_swba_lifecycle.md", lines)
    capsys.readouterr()
    assert n == 0, "带作废标记的引用被判红 ⇒ 过度报警"


def test_voidref_other_file_ignored(capsys):
    """未登记进 VOIDED 的文件不参与该类扫（防误伤）。"""
    n = sweep_mod.scan_void_refs("some/other.md", ["见 §2-B（裸引用）"])
    capsys.readouterr()
    assert n == 0


# ── per-primitive α 动作 ⇔ 撞墙 A（2026-10-02 新增；来源 = mope_layer G1 致命项）────────────
def test_alpha_conflict_negative_control(capsys):
    """声称绕开 α 墙却引入 per-primitive α 动作 ⇒ 必须计 ALPHA-CONFLICT。"""
    lines = ["本节不撞墙 A（全在像素空间）",
             "机制：对动态区 alpha_i ← max(rho·alpha_i, 0.1) 衰减"]
    n = sweep_mod.scan_alpha_conflict("results/x/evidence/prereg_x.md", lines)
    capsys.readouterr()
    assert n >= 1, "走墙 A 的动作未被抓到 ⇒ 门禁失效"


def test_alpha_conflict_positive_control(capsys):
    """真·像素空间机制（无 per-primitive α 动作）不得变红。"""
    lines = ["本节不撞墙 A", "机制：逐像素权重 ω̃=(1−p_t)ω；插入门 M^keep 逐像素 0/1"]
    n = sweep_mod.scan_alpha_conflict("results/x/evidence/prereg_x.md", lines)
    capsys.readouterr()
    assert n == 0, "像素空间机制被误判为撞墙 A ⇒ 过度报警"


def test_alpha_conflict_scope_limited_to_prereg(capsys):
    """非 prereg 文件（如大帐本）不参与该检查（防叙述性 `=` 假阳）。"""
    lines = ["不撞墙 A 的讨论……", "A2 基准 = R0 臂"]
    n = sweep_mod.scan_alpha_conflict("DECISIONS.md", lines)
    capsys.readouterr()
    assert n == 0


def test_alpha_conflict_ignores_documented_removal(capsys):
    """文档化"已删除该动作"的行不算冲突（整改/变更记录）。"""
    lines = ["删去 MoPe 用途④（该处 alpha_i ← max(...) = per-primitive α 操作）",
             "本移植不撞墙 A"]
    n = sweep_mod.scan_alpha_conflict("results/x/evidence/prereg_x.md", lines)
    capsys.readouterr()
    assert n == 0, "整改记录被判为活跃引入 ⇒ 过度报警"


# ── 负结果身份类（2026-09-23 新增；违纪事件 = 把负结果包装成主张/headline）─────────
def test_negative_result_packaged_as_contribution_red(capsys):
    """把负结果写成"可讲的贡献/否定链/headline" ⇒ 必须变红（DISCIPLINE.md「论文叙事纪律」）。"""
    _, unmarked, _, _ = _scan('三条通路的完整否定链本身是可讲的贡献。', capsys)
    assert unmarked > 0
    _, unmarked2, _, _ = _scan('**一句话**：包括三条退场通路的完整否定链。', capsys)
    assert unmarked2 > 0


def test_negative_result_boundary_subsection_allowed(capsys):
    """负结果以"边界小节/如实报告"身份出现 ⇒ 不得变红；更正块/放行语境 ⇒ 不判红。"""
    _, unmarked, _, _ = _scan('人群族读数只以 §6 边界小节身份如实报告，不计入贡献。', capsys)
    assert unmarked == 0
    # 更正块引用被撤回的旧措辞（含禁用词"否定链"）⇒ MARKED（有"已撤回"标记）⇒ 不判红
    _, unmarked2, _, _ = _scan('2026-09-23 更正：原写"完整否定链本身是可讲的贡献"，已撤回。', capsys)
    assert unmarked2 == 0
    # 无撤回标记、但属放行语境（"原写"=更正块引用）⇒ ALLOWED 而非 UNMARKED
    _, unmarked3, allowed3, _ = _scan('（原写"否定链"一词）', capsys)
    assert unmarked3 == 0 and allowed3 > 0, (unmarked3, allowed3)
    # 纪律原文引用行本身不含包装性措辞 ⇒ 自然不命中
    _, unmarked4, _, _ = _scan('负结果不得作论文叙事主角（不进贡献栏、不作 headline）。', capsys)
    assert unmarked4 == 0


def test_positive_control_retracted_commit_caught():
    """阳性对照：被撤回的旧版本（fb231fc7 的骨架）必须被新类命中（真能变红）。"""
    import subprocess
    old = subprocess.check_output(
        ["git", "show", "fb231fc7:results/lifecycle_paper2/evidence/paper2_skeleton.md"],
        text=True, cwd=str(SCRIPT.parents[2])).splitlines()
    _, unmarked, _, _ = sweep_mod.scan_lines("OLD_paper2_skeleton.md", old)
    assert unmarked > 0, "阳性对照失败：旧版违纪文本未被捕获"


# ── 归档镜像解析 + 缺件不静默（2026-10-11 新增）─────────────────────────────────
def test_archived_family_files_are_resolved_not_skipped():
    """已归档族（四件套移入 archive/closed_families/）的受检文件必须仍被解析到。

    回归：2026-10-10 Step3c 归档后，swba_lifecycle/mope_layer 两族 prereg 从活区消失，
    旧实现走 `[skip]` ⇒ VOIDREF/ALPHA-CONFLICT 两类检查空转且不报错。
    """
    for rel in ("results/swba_lifecycle/evidence/prereg_swba_lifecycle.md",
                "results/mope_layer/evidence/prereg_mope_layer.md"):
        p = sweep_mod.resolve(rel)
        assert p is not None and p.is_file(), f"归档镜像未解析到受检文件: {rel}"


def test_missing_file_turns_gate_red(monkeypatch, capsys):
    """受检文件活区与归档皆无 ⇒ 门禁必须变红（不得静默 [skip]）。"""
    monkeypatch.setattr(sweep_mod, "FILES", ["results/__no_such_family__/evidence/x.md"])
    rc = sweep_mod.sweep(quiet=True)
    capsys.readouterr()
    assert rc == 1, "缺件未使门禁变红 ⇒ 又退回静默空转"


def test_archive_resolution_keeps_live_files_priority(tmp_path):
    """活区存在时必须优先返回活区路径（归档只是兜底）。"""
    rel = "results/lifecycle_paper2/evidence/verdict_L1.md"
    p = sweep_mod.resolve(rel)
    assert p == sweep_mod.REPO / rel, "活区文件未被优先解析"


# ── 集成：当前仓库文本必须为绿（用户改动文档时该测试会变红 = 门禁生效）────────────
def test_repo_texts_currently_green():
    assert sweep_mod.sweep(quiet=True) == 0, "仓库文本存在未标记残留或非规范轮次写法"


if __name__ == "__main__":  # 便于直接跑
    raise SystemExit(pytest.main([__file__, "-q"]))
