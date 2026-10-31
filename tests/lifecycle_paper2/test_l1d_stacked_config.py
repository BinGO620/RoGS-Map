"""test_l1d_stacked_config.py — L1d gate×occupancy 叠加（D2-007）配置生效验证。

prereg_L1d_stacked.md §7 层 2（两态实例化）+ 层 3（组合棘轮序列）。
背景 = NOTES 踩坑"配置文件根本没有生效"事故族：本测试证明的不是"开关写了 true"，
而是"写了 true 之后叠加出的行为就是一页纸 §1 的棘轮"——组合顺序若退回 occ 单开
不动点 0.47，这批 run 白跑（R2 的一次机会），必须在派发前拦住。
"""
import sys
from pathlib import Path

import torch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils import alpha_lifecycle as al  # noqa: E402
from utils.occupancy_memory import apply_occupancy_decay  # noqa: E402

CONFIG_PATH = Path(
    __file__).resolve().parents[2] / "configs/experiments/lifecycle_paper2/l1d_person_tracking_stacked.yaml"
L1C_PATH = Path(
    __file__).resolve().parents[2] / "configs/experiments/lifecycle_paper2/l1c_person_tracking_occ.yaml"


# ── 层 2：两态实例化（防静默失效；已知陷阱 = 两 flag 均被 mode=="exit" 门控） ──

def _load_l1d_params():
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    return al.read_alpha_lifecycle_params(cfg)


def test_l1d_config_both_flags_fire():
    """L1d 臂的核心承诺：两个机制同时激活（L1b/L1c 各自只激活其一）。"""
    p = _load_l1d_params()
    assert p.does_evidence_gate is True, "evidence_gate 未生效（检查 mode 与键名）"
    assert p.does_occupancy_memory is True, "occupancy_memory 未生效（检查 mode 与键名）"


def test_l1d_occupancy_params_match_l1c_exactly():
    """occupancy 四参数逐键 = L1c（叠加以 L1c 已验证形态为底，不得漂移）。"""
    with open(L1C_PATH) as f:
        p_l1c = al.read_alpha_lifecycle_params(yaml.safe_load(f))
    p_l1d = _load_l1d_params()
    for key in ("occupancy_voxel_size", "occupancy_warm_kfs",
                "occupancy_decay", "occupancy_alpha_guard"):
        assert getattr(p_l1d, key) == getattr(p_l1c, key), key


def test_l1d_mode_is_exit_and_lifecycle_enabled():
    p = _load_l1d_params()
    assert p.mode == "exit"
    assert p.updates_alpha and p.does_exit
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    assert cfg["AlphaLifecycle"]["enabled"] is True
    assert cfg["AlphaLifecycle"]["evidence_gate"] is True
    assert cfg["AlphaLifecycle"]["occupancy_memory"] is True


def test_placebo_mode_still_does_not_fire_both():
    """mode 门控契约回归：observe 臂双 flag 全 false（无声混杂防线不因叠加松动）。"""
    p = al.AlphaLifecycleParams(mode=al.MODE_OBSERVE,
                                evidence_gate=True, occupancy_memory=True)
    assert p.does_evidence_gate is False
    assert p.does_occupancy_memory is False


# ── 层 3：组合棘轮序列（一页纸 §1 从"假设"升级为"已验证前置条件"） ─────────

def _sim_kf_step(alpha, warm, guard=0.35, decay=0.9, beta=0.9):
    """slam_backend 执行序的合成：EMA → gate 封顶 → occupancy 衰减（:956-1022）。

    场景 = 续命占优（掩码内持续出现静态度观测但被 gate 拦抬升）+ warm 区。
    返回 (alpha_new, capped_any, decayed_any)。
    """
    upd = torch.ones_like(alpha, dtype=torch.bool)
    gate_hit = torch.ones_like(alpha, dtype=torch.bool)   # 投影落在当前人物掩码内
    ema = al.ema_alpha_update(alpha, torch.zeros_like(alpha),
                              torch.zeros_like(alpha), upd, beta=beta)[0]
    gated, capped, _ = al.apply_evidence_gate(alpha, ema, upd, gate_hit)
    out, decayed = apply_occupancy_decay(gated, warm, guard, decay)
    return out, bool(capped.any()), bool(decayed.any())


def test_stacked_is_monotonic_ratchet_not_047_fixed_point():
    """核心组合测试：warm∩gate_hit 基元的 α 必须按 ~0.9ⁿ 单调下行穿 tau_carve，
    而非收敛到 occ 单开不动点 0.47。若本测试失败 = 组合未实现棘轮 ⇒ 停派发。"""
    alpha = torch.tensor([0.22])            # gate 单开实测钉死值（pt 0.2199）
    warm = torch.ones(1, dtype=torch.bool)
    trajectory = [float(alpha[0])]
    for _ in range(4):
        alpha, capped, decayed = _sim_kf_step(alpha, warm)
        assert capped and decayed            # 两机制每 KF 都在干活
        trajectory.append(float(alpha[0]))
    # 棘轮指纹：严格单调下行 + 穿阈 + 远离 0.47 不动点
    assert all(b < a for a, b in zip(trajectory, trajectory[1:])), trajectory
    assert trajectory[-1] < 0.20, trajectory  # 4 KF 穿 tau_carve（一页纸 §1）
    assert trajectory[-1] < 0.25, trajectory  # 明确不是 0.47 不动点


def test_stacked_ratchet_safety_alpha_above_guard_untouched():
    """D③ 安全性在组合下保持：α≥guard 净静态结构永不被 occ 衰减触碰。"""
    alpha = torch.tensor([0.9])
    warm = torch.ones(1, dtype=torch.bool)
    for _ in range(10):
        alpha, _, decayed = _sim_kf_step(alpha, warm)
        assert not decayed
    assert float(alpha[0]) >= 0.9 - 1e-6
