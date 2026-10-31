"""insertion_cost_model 的门禁（P0 踩坑补丁的工具；纯逻辑合成数，不需 GPU/工件）。

守护的事实（NOTES 踩坑 2026-09-25「prereg 成本线与插入策略自相矛盾」）：
  ① online 走帧日志的摘要计算（速率/触顶帧/churn）正确；
  ② 稳态拟合 buf_ss = a + b·rate 在合成线性数据上恢复系数，且钉顶图被排除；
  ③ 钉顶预测 = cap/rate；
  ④ classic 臂的 mean_n_dyn / cost_frac 正确。
"""
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "insertion_cost_model", REPO / "scripts/02_analysis/insertion_cost_model.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


mod = _load()


# ── ① online 摘要 ─────────────────────────────────────────────────────────────
def test_online_summary_rate_pinning_churn():
    log = [{"frame": 10 + i, "inserted": 100, "buf": min(100 * (i + 1), 1000),
            "evicted_total": max(100 * (i + 1) - 1000, 0)} for i in range(20)]
    s = mod.summarize_online(log, cap=1000)
    assert s["inserted_per_frame"] == 100.0
    assert s["pinning_frame"] == 19, "buf 第 10 项达 1000 ⇒ 走帧 frame=19 触顶"
    assert s["pinned"] is True and s["buf_final"] == 1000 and s["buf_max"] == 1000
    # 累计插入 2000、缓冲持 1000 ⇒ 累计逐出 1000 ⇒ churn = 0.5（短程）
    assert s["churn"] == 0.5
    assert s["n_walked_frames"] == 20


def test_online_summary_long_run_churn_approaches_one():
    """长程稳态：插入 20000、缓冲持 1000 ⇒ 逐出 19000 ⇒ churn=0.95 → 1。"""
    n = 200
    log = [{"frame": i, "inserted": 100, "buf": min(100 * (i + 1), 1000),
            "evicted_total": max(100 * (i + 1) - 1000, 0)} for i in range(n)]
    s = mod.summarize_online(log, cap=1000)
    assert s["churn"] == 0.95 and s["pinned"] is True


def test_online_summary_unpinned():
    log = [{"frame": i, "inserted": 50, "buf": 50 * (i + 1), "evicted_total": 0}
           for i in range(8)]
    s = mod.summarize_online(log, cap=60000)
    assert s["pinned"] is False and s["pinning_frame"] is None
    assert s["buf_final"] == 400 and s["churn"] == 0.0


# ── ② 稳态拟合 ────────────────────────────────────────────────────────────────
def test_fit_recovers_linear_coefficients_and_excludes_pinned():
    points = [(100.0, 500.0), (200.0, 1000.0), (150.0, 750.0)]
    fit = mod.fit_steady_buffer(points)
    assert fit is not None
    assert abs(fit["b_frames"] - 5.0) < 1e-6 and abs(fit["a"]) < 1e-6
    assert fit["n_points"] == 3 and fit["r2"] == 1.0


def test_fit_skipped_below_two_points():
    assert mod.fit_steady_buffer([(100.0, 500.0)]) is None
    assert mod.fit_steady_buffer([]) is None


def test_analyze_excludes_pinned_maps_from_fit():
    """钉顶图的 buf_final 是护栏值 ⇒ 不得进拟合点（P0 的核心教训）。"""
    online_log_pinned = [{"frame": i, "inserted": 3000, "buf": min(3000 * (i + 1), 60000),
                          "evicted_total": max(3000 * (i + 1) - 60000, 0)} for i in range(40)]
    online_log_free = [{"frame": i, "inserted": 100, "buf": 100 * (i + 1), "evicted_total": 0}
                       for i in range(20)]
    data = {"meta": {
        "gate": {"n_static": 55000, "online_vitality": {"P0o": {"log": online_log_pinned}}},
        "free": {"n_static": 55000, "online_vitality": {"P0o": {"log": online_log_free}}},
    }, "arms": {}}
    tmp = Path(__file__).parent / "debug_icm_fixture.json"
    tmp.write_text(json.dumps(data))
    try:
        out = mod.analyze([tmp], cap=60000)
        assert out["fit"] is None, "仅 1 个未钉顶图 ⇒ 拟合跳过（不得混入钉顶点）"
        assert any("已钉顶" in n for n in out["notes"])
        assert out["maps"][f"{tmp.stem}:gate"]["online"]["pinned"] is True
        assert out["maps"][f"{tmp.stem}:free"]["online"]["pinned"] is False
    finally:
        tmp.unlink()


# ── ③ 钉顶预测 ────────────────────────────────────────────────────────────────
def test_predict_pinning_frame():
    assert mod.predict_pinning_frame(60000, 2400) == 25.0
    assert mod.predict_pinning_frame(60000, 0) is None


# ── ④ classic 臂 ──────────────────────────────────────────────────────────────
def test_classic_arm_summary():
    recs = [{"n_dyn": 100}, {"n_dyn": 200}, {"n_dyn": 300}, {"cold_start": True}]
    s = mod.summarize_classic(recs, n_static=10000)
    assert s["n_frames"] == 3 and s["mean_n_dyn"] == 200.0 and s["cost_frac"] == 0.02
    assert mod.summarize_classic([{"cold_start": True}], n_static=10000) is None
    assert mod.summarize_classic(recs, n_static=None) is None
