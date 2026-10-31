"""test_dynamic_mask_spec.py — 评估掩码解析入口（v2）单测。

v2 的核心：**消费方不再有类号**。eval 掩码一律 `<seq>/dynamic_mask/`（0/255 布尔）。
历史来源（seg_mask 的类号口径 / gtmc）只能显式放行。
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.dynamic_mask_spec import (  # noqa: E402
    EVAL_MASK_SUBDIR, LEGACY_SOURCES, resolve_eval_mask_dir,
)


def _mk(tmp_path, seq, subdir, n_png=2):
    d = tmp_path / f"rgbd_bonn_{seq}" / subdir
    d.mkdir(parents=True)
    for i in range(n_png):
        (d / f"1{i}.png").write_bytes(b"\x00")
    return str(tmp_path / f"rgbd_bonn_{seq}")


def test_canonical_resolution(tmp_path):
    seq = _mk(tmp_path, "person_tracking", EVAL_MASK_SUBDIR)
    d, src, legacy = resolve_eval_mask_dir(seq)
    assert d.endswith(EVAL_MASK_SUBDIR) and src == EVAL_MASK_SUBDIR and legacy is False


def test_missing_canonical_refuses_and_does_not_fall_back(tmp_path):
    """缺 dynamic_mask ⇒ 报错；**关键**：即使同序列有 seg_mask/gtmc 也不回落。"""
    seq = _mk(tmp_path, "person_tracking", "seg_mask")
    _mk(tmp_path, "person_tracking", "dynamic_mask_gtmc")
    with pytest.raises(ValueError, match="不回落到"):
        resolve_eval_mask_dir(seq)


def test_legacy_requires_explicit_optin(tmp_path):
    seq = _mk(tmp_path, "crowd2", "seg_mask")
    with pytest.raises(ValueError):
        resolve_eval_mask_dir(seq, mask_subdir="seg_mask")
    d, src, legacy = resolve_eval_mask_dir(seq, mask_subdir="seg_mask", allow_legacy=True)
    assert src == "seg_mask" and legacy is True
    assert "seg_mask" in LEGACY_SOURCES


def test_unknown_subdir_refused_when_absent(tmp_path):
    seq = _mk(tmp_path, "crowd2", "dynamic_mask")
    with pytest.raises(ValueError):
        resolve_eval_mask_dir(seq, mask_subdir="no_such_dir")


def test_canonical_preferred_even_when_legacy_present(tmp_path):
    """canonical 存在时默认一律走 canonical（legacy 目录存在也不影响）。"""
    seq = _mk(tmp_path, "person_tracking", EVAL_MASK_SUBDIR)
    _mk(tmp_path, "person_tracking", "seg_mask")
    d, src, legacy = resolve_eval_mask_dir(seq)
    assert src == EVAL_MASK_SUBDIR and legacy is False
    assert os.path.isdir(d)
