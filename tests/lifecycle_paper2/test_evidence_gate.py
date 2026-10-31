"""test_evidence_gate.py — L1b evidence gate（治续命）单元门禁。

覆盖（prereg_L1b_gate.md §1/§10 的实装契约）：
① 封顶语义：掩码内 EMA 抬升被压回 pre 值（只减不升，不是冻结/改写）；
② 掩码外 / 未更新 / 下降的基元不受影响；
③ prevented_rise_sum 的算术；
④ ema_alpha_update 纯性（不改动入参——slam_backend 的 alpha_pre 引用依赖它）；
⑤ 参数契约：evidence_gate 默认 false；仅 EXIT 臂启用（observe 安慰剂臂不启用）；
⑥ mask None ⇒ slam_backend 侧 fail-open（计数器路径，此处测 does_evidence_gate 的门控）。
"""
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils import alpha_lifecycle as al  # noqa: E402


def _t(*vals):
    return torch.tensor(vals, dtype=torch.float32)


# ── apply_evidence_gate：纯函数三分支 ──────────────────────────────

def test_rise_inside_mask_capped_to_pre():
    pre = _t(0.2, 0.5, 0.8)
    post = _t(0.9, 0.4, 0.95)  # 0: 升(掩码内) 1: 降 2: 升(掩码外)
    upd = torch.ones(3, dtype=torch.bool)
    hit = torch.tensor([True, True, False])
    out, capped, prevented = al.apply_evidence_gate(pre, post, upd, hit)
    assert torch.allclose(out, _t(0.2, 0.4, 0.95))
    assert capped.tolist() == [True, False, False]
    assert abs(prevented - (0.9 - 0.2)) < 1e-6


def test_fall_inside_mask_kept():
    # 下降不受影响：只减不升 = EMA 的衰减方向照常通过
    pre = _t(0.8)
    post = _t(0.3)
    out, capped, prevented = al.apply_evidence_gate(
        pre, post, torch.ones(1, dtype=torch.bool), torch.ones(1, dtype=torch.bool)
    )
    assert torch.allclose(out, _t(0.3))
    assert capped.tolist() == [False]
    assert prevented == 0.0


def test_not_updated_or_outside_mask_untouched():
    pre = _t(0.2, 0.2)
    post = _t(0.9, 0.9)
    upd = torch.tensor([False, True])
    hit = torch.tensor([True, False])
    out, capped, _ = al.apply_evidence_gate(pre, post, upd, hit)
    assert torch.allclose(out, post)
    assert not capped.any()


def test_empty_mask_noop():
    pre = _t(0.5)
    post = _t(0.9)
    out, capped, prevented = al.apply_evidence_gate(
        pre, post, torch.ones(1, dtype=torch.bool), torch.zeros(1, dtype=torch.bool)
    )
    assert torch.allclose(out, post)
    assert prevented == 0.0


def test_inputs_not_mutated():
    pre = _t(0.2)
    post = _t(0.9)
    pre_c, post_c = pre.clone(), post.clone()
    al.apply_evidence_gate(
        pre, post, torch.ones(1, dtype=torch.bool), torch.ones(1, dtype=torch.bool)
    )
    assert torch.allclose(pre, pre_c) and torch.allclose(post, post_c)


# ── ema_alpha_update 纯性（slam_backend 的 alpha_pre 引用依赖） ─────────

def test_ema_alpha_update_is_pure():
    alpha = _t(0.5, 0.5)
    obs = _t(3.0, 3.0)
    ev = _t(0.0, 0.9)
    upd = torch.ones(2, dtype=torch.bool)
    a_out, o_out = al.ema_alpha_update(alpha, obs, ev, upd, beta=0.9)
    # 入参未被改动
    assert torch.allclose(alpha, _t(0.5, 0.5))
    assert torch.allclose(obs, _t(3.0, 3.0))
    # 静态证据(ev=0)拉向 1、动态证据(ev=0.9)拉向 0.1
    assert a_out[0] > alpha[0] and a_out[1] < alpha[1]
    assert torch.allclose(o_out, _t(4.0, 4.0))


# ── 参数契约 ─────────────────────────────────────────────────────

def test_evidence_gate_default_off_and_exit_only():
    assert al.AlphaLifecycleParams().evidence_gate is False
    # observe（安慰剂臂）不启用：改 α 而无 pass 消费 = 无声混杂
    p_obs = al.AlphaLifecycleParams(mode=al.MODE_OBSERVE, evidence_gate=True)
    assert p_obs.does_evidence_gate is False
    for mode in (al.MODE_EXIT, al.MODE_EXIT_FILL):
        p = al.AlphaLifecycleParams(mode=mode, evidence_gate=True)
        assert p.does_evidence_gate is True
    # 默认关 = does_evidence_gate False
    p_off = al.AlphaLifecycleParams(mode=al.MODE_EXIT)
    assert p_off.does_evidence_gate is False


def test_read_params_evidence_gate_key():
    cfg = {"AlphaLifecycle": {"mode": "exit", "evidence_gate": True}}
    assert al.read_alpha_lifecycle_params(cfg).does_evidence_gate is True
    cfg2 = {"AlphaLifecycle": {"mode": "exit"}}
    assert al.read_alpha_lifecycle_params(cfg2).does_evidence_gate is False
    # off 臂写了 true 也不启用（mode 优先）
    cfg3 = {"AlphaLifecycle": {"mode": "off", "evidence_gate": True}}
    assert al.read_alpha_lifecycle_params(cfg3).does_evidence_gate is False


# ── 安全性论证的数值化（T3 前科降级论证的回归测试） ─────────────────────

def test_mask_false_positive_cannot_reach_carve():
    """静态结构 α≈1 被掩码 FP 盖住多帧：封顶只减不升 ⇒ α 停在高位 ⇒
    carve 合取门(α<tau_carve)不可达。多步模拟（EMA 每步想把 α 拉回 1）。"""
    alpha = _t(0.95)
    hit = torch.ones(1, dtype=torch.bool)
    upd = torch.ones(1, dtype=torch.bool)
    for _ in range(10):
        ema = al.ema_alpha_update(
            alpha, _t(0.0), _t(0.0), upd, beta=0.9
        )[0]  # 静态证据 => 想拉向 1
        alpha, _, _ = al.apply_evidence_gate(alpha, ema, upd, hit)
    assert float(alpha[0]) >= 0.95 - 1e-6  # 封顶后纹丝不动（float32 表示容差）
    assert not al.select_carve_mask(
        z=_t(1.0), obs_at_gauss=_t(1.5), alpha=alpha,
        obs_count=_t(10.0), valid=torch.ones(1, dtype=torch.bool),
        tau_carve=0.20, delta_free_m=0.10, min_obs_count=3.0,
    ).any()

def test_gate_lets_alpha_walk_below_tau_carve():
    """续命场景：掩码内 α 本就在衰减路上（EMA ev 高），gate 不挡下降 ⇒
    跨过 tau_carve ⇒ carve 可触发（gate 的目的）。"""
    alpha = _t(0.24)
    hit = torch.ones(1, dtype=torch.bool)
    upd = torch.ones(1, dtype=torch.bool)
    for _ in range(6):
        ema = al.ema_alpha_update(alpha, _t(0.0), _t(0.9), upd, beta=0.9)[0]
        alpha, capped, _ = al.apply_evidence_gate(alpha, ema, upd, hit)
        assert not capped.any()  # 下降路径不触发封顶
    assert float(alpha[0]) < 0.20
    assert al.select_carve_mask(
        z=_t(1.0), obs_at_gauss=_t(1.5), alpha=alpha,
        obs_count=_t(10.0), valid=torch.ones(1, dtype=torch.bool),
        tau_carve=0.20, delta_free_m=0.10, min_obs_count=3.0,
    ).any()
