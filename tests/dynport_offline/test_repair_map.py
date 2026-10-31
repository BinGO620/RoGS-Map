"""tests/dynport_offline — 离线修复算子单测（prereg §9 坑清单 + G4 条件 C1/C6）。

全部 CPU 可跑（不依赖 GPU）：OfflineDynMap 用注入的 CPU 桩 new_gaussian_fn；
判据机的新增落点键用静态文本核对（避免 import torch 渲染路径）。
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from utils.dyn_port_buffer import DynPortBuffer, dynport_cfg  # noqa: E402
from utils.dyn_port_offline import OfflineDynMap, make_core, repair_enabled  # noqa: E402


def _cpu_new_gaussian(points, colors):
    """CPU 桩：形状与 make_dynamic 同（键齐 + K），值无所谓。"""
    n = int(np.asarray(points).shape[0])
    return {
        "xyz": torch.nn.Parameter(torch.as_tensor(points, dtype=torch.float32)),
        "log_scale": torch.nn.Parameter(torch.full((n, 3), -3.0)),
        "rot": torch.nn.Parameter(torch.tensor([[1.0, 0.0, 0.0, 0.0]] * n)),
        "opa": torch.nn.Parameter(torch.zeros(n, 1)),
        "dc": torch.nn.Parameter(torch.zeros(n, 1, 3)),
        "rest": torch.zeros(n, 0, 3),
        "K": 1,
    }


def _map():
    return OfflineDynMap(_cpu_new_gaussian, lineage_base=100)


def test_default_off_no_repair():
    """J9 语义：default-off ⇒ repair_enabled False（驱动层不做修复）。"""
    assert repair_enabled({}) is False
    assert repair_enabled({"DynPort": {"enabled": False}}) is False
    assert repair_enabled({"DynPort": {"enabled": True}}) is True


def test_map_insert_and_lineage():
    m = _map()
    idx = m.insert(np.zeros((5, 3), np.float32), np.zeros((5, 3), np.float32), 100)
    assert m.n == 5 and idx.tolist() == [0, 1, 2, 3, 4]
    assert (m.lineage_of(idx) == 100).all()
    assert m.dyn_indices([100]).tolist() == [0, 1, 2, 3, 4]


def test_map_move_replaces_not_duplicates():
    """Case1 语义：move 替换坐标、不新增基元。"""
    m = _map()
    idx = m.insert(np.zeros((3, 3), np.float32), np.zeros((3, 3), np.float32), 100)
    m.move(idx[:2], np.ones((2, 3), np.float32))
    assert m.n == 3
    wp = m.world_points(idx)
    assert np.allclose(wp[:2], 1.0) and np.allclose(wp[2], 0.0)


def test_map_delete_removes_rows():
    m = _map()
    idx = m.insert(np.zeros((4, 3), np.float32), np.zeros((4, 3), np.float32), 100)
    m.delete(idx[:1])
    assert m.n == 3
    assert m.lineage_of(m.dyn_indices([100])).tolist() == [100, 100, 100]


def test_core_runs_on_offline_map():
    """决策核（与在线同型）能绑定离线 MapAccess 并产生非零计数（J5 接线）。"""
    cfg = dynport_cfg({"DynPort": {"enabled": True, "lam_d": 0.20, "lineage_base": 100,
                                   "cap": 50000, "lmax": 45, "unproj_stride": 3}})
    m = _map()
    core = make_core(cfg, m)
    # 帧 1：插入（Case2）
    r1 = core.step(1, np.zeros((10, 3), np.float32), np.zeros((10, 3), np.float32), 2.0)
    assert r1["inserted"] == 10 and core.case2_new == 10
    # 帧 2：同点观测 ⇒ Case1 复用命中（move）
    r2 = core.step(2, np.zeros((10, 3), np.float32), np.zeros((10, 3), np.float32), 2.0)
    assert core.case1_hits > 0
    # 帧 200：远超 lmax ⇒ Cond2 寿命删除
    core.step(200, np.zeros((5, 3), np.float32), np.zeros((5, 3), np.float32), 2.0)
    assert core.cond2_deleted > 0 or core.cond1_deleted > 0


def test_judge_has_required_mechanical_keys():
    """G4-C1：判据机须产出 prereg 声明的机械键（Δfull / bad_px 落点）。"""
    src = (REPO / "scripts/dynport/judge_dynport.py").read_text()
    assert "J3_full_delta" in src, "缺 J3_full_delta（Δfull 落点，G1-M1）"
    assert "J3_samepose_full_delta" in src, "缺 J3_samepose_full_delta（Δfull 同帧落点，G2 L3 major#2）"
    assert "J5_two_state_full_psnr_maxabs" in src, "缺 J5 两态 PSNR 键（G2 L3 major#1）"
    assert "J6_bad_px_median" in src, "缺 J6 bad_px 落点"
    assert "缺 E 臂" in src or "fail" in src.lower(), "缺 E 臂 fail-loud（G4-C6）"


def test_exit_consumes_declared_subclauses():
    """G2 L3 major#1/#2：出口计算须真消费 Δfull 与 J5 两态 PSNR 子句（非只产键、不判）。"""
    src = (REPO / "scripts/dynport_offline/collect_L1.py").read_text()
    assert "j3_full_ok" in src and "j3_ok = j3_static_ok and j3_full_ok" in src, \
        "J3 出口未消费 Δfull 子句（G2 L3 major#2）"
    assert "two_state_ok" in src and "J5_two_state_full_psnr_maxabs" in src, \
        "J5 出口未消费两态 PSNR 子句（G2 L3 major#1）"


def test_exit_logic_behaves_on_synthetic_inputs():
    """G2 L3：左/右边界的合成输入下，出口判据真起作用（防"接了但算错"）。"""
    spec = importlib.util.spec_from_file_location(
        "collect_L1_exit", REPO / "scripts/dynport_offline/collect_L1.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    base = {"J1": 8.0, "J2": 0.4, "J3": 0.03, "J3_full": 2.5,
            "J5_two_state_full_psnr_maxabs": 5.0, "J6": True}
    ctr = {"case1_hits": 100, "cond1_deleted": 5, "cond2_deleted": 3, "n_buf_peak": 3000}
    t = {"cap": 50000}
    ok = mod.compute_locked_exit(base, t, ctr, True, 0.2, j9_off=True, j5_off_eq_base=True)
    assert ok["pass_substantive"] and ok["J3_full_ok"] and ok["J5"], "全过输入应 PASS"
    # Δfull 破线 ⇒ J3 必红（G2 L3 major#2 的靶）
    bad_full = dict(base, J3_full=-0.4)
    o2 = mod.compute_locked_exit(bad_full, t, ctr, True, 0.2, j9_off=True)
    assert not o2["checks"]["J3"] and not o2["pass_substantive"], "Δfull < −0.25 未令 J3 红"
    # 两态 PSNR ≤0.01 dB ⇒ J5 必红（G2 L3 major#1 的靶）
    bad_ts = dict(base, J5_two_state_full_psnr_maxabs=0.005)
    assert not mod.compute_locked_exit(bad_ts, t, ctr, True, 0.2, j9_off=True)["J5"]
    # 键缺 ⇒ fail-loud（不静默过）
    miss = {k: v for k, v in base.items() if k != "J3_full"}
    assert not mod.compute_locked_exit(miss, t, ctr, True, 0.2, j9_off=True)["checks"]["J3"], \
        "缺 J3_full 键未 fail-loud（静默过风险）"


def test_offline_collect_has_required_keys():
    """G4-C1：离线汇总器须产出 J4 报数键（repair_wall_s）。"""
    p = REPO / "scripts/dynport_offline/collect_L1.py"
    assert p.exists(), "离线 collect_L1.py 不存在"
    src = p.read_text()
    assert "repair_wall_s" in src and "bit_identical" in src


def _load_collector():
    spec = importlib.util.spec_from_file_location(
        "collect_L1_off", REPO / "scripts/dynport_offline/collect_L1.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_collector_multi_root_cross_batch_resolution():
    """L3：汇总器支持多根（L1_v4+L2+L3）跨批复用，且单根字符串仍向后兼容。"""
    m = _load_collector()
    roots = ["results/dynport_offline/L1_v4", "results/dynport_offline/L2",
             "results/dynport_offline/L3"]
    # 多根：seed0 从 L1_v4/L2 解析出既有 R1
    r1 = m.latest_run(roots, "crowd2", "R1")
    assert r1 is not None and r1.name == "crowd2_R1"
    # 单根（字符串）向后兼容
    r1s = m.latest_run("results/dynport_offline/L2", "crowd", "R1")
    assert r1s is not None and r1s.name == "crowd_R1"
    # 缺臂 ⇒ None（不伪造）
    assert m.latest_run(roots, "crowd2_seed1", "Cneg") is None


def test_resolve_base_l3_labels():
    """L3 标签 <name>_seed<N> 解析到底图 r33_rebase_baseline_<name>_seed<N>/seed_<N>。"""
    m = _load_collector()
    b = m._resolve_base("results/paper2_fulltable", "balloon")
    assert b is not None and b.parts[-2] == "seed_0"
    b1 = m._resolve_base("results/paper2_fulltable", "balloon_seed1")
    assert b1 is not None and b1.parts[-2] == "seed_1"
    b2 = m._resolve_base("results/paper2_fulltable", "crowd_seed2")
    assert b2 is not None and b2.parts[-2] == "seed_2"


def test_prereg_criterion_key_gate_green_after_impl():
    """G4-C1 验收：键门在本轮实装后应转绿（MISSING_TOTAL == 0）。"""
    spec = importlib.util.spec_from_file_location(
        "prereg_criterion_keys", REPO / "scripts/02_analysis/prereg_criterion_keys.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    corpus = {}
    for prereg, declared in mod.KEY_REGISTRY.items():
        for _k, (_ks, ps) in declared.items():
            for pf in ps:
                f = REPO / pf
                corpus[pf] = f.read_text(errors="ignore") if f.exists() else ""
    miss = mod.missing_keys(mod.KEY_REGISTRY[
        "results/dynport_offline/evidence/prereg_dynport_offline_L1.md"], corpus)
    assert not miss, f"键门未转绿（S3 未补齐落点）: {miss}"


def test_repair_map_naive_flag_wired():
    """NaiveCtrl（prereg_naive_ctrl_2026-10-13）：`--naive` 开关须接入 repair() 并关闭生命周期+S5。

    守护事实：朴素对照臂 = 单变量于生命周期+S5（掩码/深度/stride/fit 与 R1 同口径）；
    开关缺接线 ⇒ 该对照静默退化为完整算子（结论作废）。
    """
    src = (REPO / "scripts/dynport_offline/repair_map.py").read_text()
    assert "naive=False" in src and "--naive" in src, "repair() 未接 naive 参数/CLI"
    assert "core.step(kf, pts, cols, dbar)" in src, "完整算子路径（决策核）仍须在"
    assert "omap.insert(np.asarray(pts" in src, "朴素臂须逐 KF 全量插入新基元"
    assert "if not naive:" in src, "S5（夹回+剪枝）须在朴素臂下跳过"
    assert '"naive": bool(naive)' in src, "timing 须显式落盘 naive 身份（provenance 可机检）"


def test_judge_naive_ctrl_reads_samepose_keys():
    """NaiveCtrl 判读器：只读 samepose 出口键（§12 v4），禁 causal/final 键混引。"""
    p = REPO / "scripts/dynport_offline/judge_naive_ctrl.py"
    assert p.exists(), "judge_naive_ctrl.py 不存在"
    src = p.read_text()
    assert "J1_samepose_bad_psnr_delta" in src
    assert "J2_samepose_bad_dl1_ratio" in src
    assert "J3_samepose_static_delta" in src
    assert "C1_operator_gain" in src and "C3_S5_protects_static" in src
    assert "J1_bad_psnr_delta" not in src.replace("J1_samepose_bad_psnr_delta", ""), \
        "判读器误引非 samepose 键（口径混引）"


def test_prereg_naive_ctrl_locked_before_impl():
    """NaiveCtrl 判据先锁：预注册文件须落盘且含先锁判据（C1/C3 + 规模 3 序列）。"""
    p = REPO / "results/dynport_offline/evidence/prereg_naive_ctrl_2026-10-13.md"
    assert p.exists(), "预注册文件缺（判据未先锁）"
    txt = p.read_text()
    assert "C1（算子的增量）" in txt and "C3（J3 保护）" in txt
    assert "3 序列" in txt and "single" in txt or "单变量" in txt
