"""负/正对照：prereg 声明键 ↔ 判据机产出的机械门（类登记，2026-10-06 DynPort-Offline G1-M1/M2）。

门本体 = scripts/02_analysis/prereg_criterion_keys.py；本文件只测它的纯函数与登记表两态，
防止日后门被摘除或退化为恒绿。
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "prereg_criterion_keys", REPO / "scripts/02_analysis/prereg_criterion_keys.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def test_selftest_passes():
    assert mod.selftest() == 0


def test_missing_key_is_red():
    declared = {"Jx": (["key_a", "key_b"], ["prod.py"])}
    assert mod.missing_keys(declared, {"prod.py": 'res["key_a"]'}) == {"Jx": ["key_b"]}


def test_all_present_is_green():
    declared = {"Jx": (["key_a"], ["prod.py"])}
    assert mod.missing_keys(declared, {"prod.py": 'res["key_a"]'}) == {}


def test_empty_corpus_is_red():
    declared = {"Jx": (["key_a"], ["prod.py"])}
    assert mod.missing_keys(declared, {}) == {"Jx": ["key_a"]}


def test_registry_not_empty():
    assert mod.KEY_REGISTRY, "族登记表为空 ⇒ 机制被摘除"


def test_registry_covers_offline_prereg():
    key = "results/dynport_offline/evidence/prereg_dynport_offline_L1.md"
    assert key in mod.KEY_REGISTRY, "DynPort-Offline prereg 未登记进键门"
    crits = mod.KEY_REGISTRY[key]
    # M1（Δfull）与 J6（bad_px）落点是本轮整改的核心，必须在册
    assert "J3_full" in crits, "Δfull 落点未登记（G1-M1 会复发）"
    assert "J6_judgeable" in crits, "J6 bad_px 落点未登记（G1-次要会复发）"
