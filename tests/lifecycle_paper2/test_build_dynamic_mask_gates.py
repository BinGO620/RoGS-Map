"""test_build_dynamic_mask_gates.py — 评估掩码构建器验证门的单测。

钉住 2026-09-21 实测踩过的两类**判据本身**的坑（掩码内容没问题，是门在误判）：
  ① 微参照帧（ref_px 很小）做除法 ⇒ area/ref 假比值 29x/419x（pt2/balloon 被误杀）；
  ② 绝对面积上限 0.5 对**密集人群**场景错标定（crowd/crowd2 参照本身占 57% 画面、precision 0.84-0.90）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from build_dynamic_mask import REF_MIN_PX, evaluate_gates  # noqa: E402

DEFAULTS = dict(min_recall=0.80, max_area_frac=0.90, max_area_ratio_vs_ref=3.0,
                max_empty_rate=0.50, ref_min_px=REF_MIN_PX)


def _row(stem, frac, ref_px=None, recall=None):
    r = {"depth_stem": stem, "area_frac": frac}
    if ref_px is not None:
        r["ref_px"] = ref_px
        r["recall_vs_ref"] = recall if recall is not None else 1.0
        r["precision_vs_ref"] = 1.0
    return r


def test_micro_reference_frames_excluded_from_ratio():
    """ref_px < REF_MIN_PX 的帧不参与比值判据（曾产生 29x/419x 假警报）。"""
    rows = [_row("a", 0.02, ref_px=100, recall=1.0),      # micro-ref：6.6k px 掩码 / 100 px 参照
            _row("b", 0.15, ref_px=40000, recall=0.99)]
    fails, stats = evaluate_gates(rows, **DEFAULTS)
    assert fails == [], fails
    assert stats["n_frames_with_reference"] == 1          # 只有 b 计入


def test_dense_crowd_not_falsely_killed():
    """密集人群：参照本身占 57% 画面、掩码 65%（比值 1.14）⇒ 必须通过（绝对上限 0.9 也放行）。"""
    rows = [_row(f"f{i}", 0.65, ref_px=int(0.57 * 480 * 640), recall=0.99) for i in range(20)]
    fails, stats = evaluate_gates(rows, **DEFAULTS)
    assert fails == [], fails
    assert stats["max_area_ratio_vs_ref"] < 1.5


def test_ratio_uses_morphology_matched_reference():
    """比值判据用 ref_px_matched（同膨胀）——参照紧/松不应改变判定（2026-09-22 自伤修复）。"""
    tight = {"depth_stem": "a", "area_frac": 0.10, "ref_px": 8000,       # 裸参照很小
             "ref_px_matched": 40000, "recall_vs_ref": 0.99}              # 同膨胀后相当
    fails, stats = evaluate_gates([tight], **DEFAULTS)
    assert fails == [], fails
    assert stats["max_area_ratio_vs_ref"] < 1.5
    # 缺失 matched 字段时回落到 ref_px（向后兼容）
    legacy = {"depth_stem": "b", "area_frac": 0.10, "ref_px": 8000, "recall_vs_ref": 0.99}
    fails2, _ = evaluate_gates([legacy], **DEFAULTS)
    assert any("远超独立参照" in f for f in fails2), fails2


def test_single_outlier_frame_does_not_fail():
    """离群帧宽容：500 帧里 1 帧超界（=0.2% <= 2%）⇒ 通过（2026-09-22：过渡帧参照塌陷误杀）。"""
    rows = [_row(f"f{i}", 0.15, ref_px=40000, recall=0.99) for i in range(499)]
    rows.append({"depth_stem": "outlier", "area_frac": 0.15, "ref_px": 3000,
                 "ref_px_matched": 3000, "recall_vs_ref": 1.0})
    fails, stats = evaluate_gates(rows, **DEFAULTS)
    assert fails == [], fails
    assert stats["n_frames_area_over_ref"] == 1


def test_real_over_firing_caught():
    """真过喷：绝大多数帧的掩码面积是参照的 6 倍 ⇒ 必须拒绝。"""
    rows = [_row(f"f{i}", 0.60, ref_px=int(0.10 * 480 * 640), recall=1.0) for i in range(20)]
    fails, _ = evaluate_gates(rows, **DEFAULTS)
    assert any("远超独立参照" in f for f in fails), fails


def test_low_recall_caught():
    rows = [_row(f"f{i}", 0.20, ref_px=40000, recall=0.5) for i in range(10)]
    fails, stats = evaluate_gates(rows, **DEFAULTS)
    assert any("独立参照一致性" in f for f in fails), fails
    assert stats["mean_recall"] == 0.5


def test_empty_but_person_present_caught():
    rows = [_row(f"f{i}", 0.0, ref_px=40000, recall=0.0) for i in range(10)]
    fails, stats = evaluate_gates(rows, **DEFAULTS)
    assert any("空掩码率" in f for f in fails), fails
    assert stats["empty_but_person_present_rate"] == 1.0


def test_no_reference_falls_back_to_absolute_bound():
    """无参照序列（如 crowd3 的旧掩码被本仓覆盖）⇒ 用绝对退化界；0.95 画面必须拒。"""
    rows = [_row("a", 0.95), _row("b", 0.30)]
    fails, _ = evaluate_gates(rows, **DEFAULTS)
    assert any("无参照帧" in f for f in fails), fails
    ok, _ = evaluate_gates([_row("b", 0.30)], **DEFAULTS)
    assert ok == []
