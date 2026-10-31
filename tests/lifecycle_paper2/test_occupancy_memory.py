"""test_occupancy_memory.py — L1c 时序先验（区域占据记忆）单元门禁。

覆盖（prereg_L1c_occupancy.md §机制规格 的实装契约）：
① 衰减语义：warm ∧ α<guard 才动（乘法，非覆写/冻结）；warm 外 / α≥guard 不动；
② 安全性回归：α≈1 净静态结构永不触碰（FP 天花板伤害 = 0）；单帧 FP 累计有界（γ^K）；
③ pt 钉死数值回归（postmortem 正面复现）：无温暖区 ⇒ gate 下 α 钉死 0.2199、不穿
   tau_carve；有温暖区 ⇒ occupancy decay 让 α 穿 0.20（carve 可达）；
④ 参数契约：occupancy_memory 默认 false；仅 EXIT 臂启用；mode 开关优先；config 键可读。
"""
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils import alpha_lifecycle as al  # noqa: E402
from utils import occupancy_memory as om  # noqa: E402


def _t(*vals):
    return torch.tensor(vals, dtype=torch.float32)


# ── ① 衰减语义 ────────────────────────────────────────────────────────

def test_decay_only_inside_warm_and_below_guard():
    alpha = _t(0.30, 0.40, 0.30, 0.40)
    warm = torch.tensor([True, True, False, False])
    out, hit = om.apply_occupancy_decay(alpha, warm, guard=0.35, decay=0.9)
    # 0: warm 且 < guard ⇒ 衰减；1: warm 但 ≥ guard ⇒ 不动；2/3: warm 外 ⇒ 不动
    assert torch.allclose(out, _t(0.27, 0.40, 0.30, 0.40))
    assert hit.tolist() == [True, False, False, False]
    # 纯性：入参不被改（float32 精度内）
    assert abs(alpha[0].item() - 0.30) < 1e-6


def test_decay_is_multiplicative_not_overwrite():
    alpha = _t(0.10)
    out, _ = om.apply_occupancy_decay(alpha, torch.ones(1, dtype=torch.bool), 0.35, 0.9)
    assert abs(out[0].item() - 0.09) < 1e-6


# ── ② 安全性回归 ──────────────────────────────────────────────────────

def test_static_structure_never_touched():
    # 净静态结构 α≈1（以及一切 α≥guard）⇒ warm FP 的天花板伤害 = 0
    alpha = _t(1.0, 0.99, 0.5, 0.35)
    warm = torch.ones(4, dtype=torch.bool)   # 假设掩码/体素全 FP
    out, hit = om.apply_occupancy_decay(alpha, warm, guard=0.35, decay=0.9)
    assert hit.sum() == 0 and torch.allclose(out, alpha)


def test_single_frame_fp_bounded_by_gamma_pow_k():
    # 单帧 FP 的最大累计效应 = γ^K 上界：K 窗口内每次至多乘 γ
    K, gamma = om.OccupancyMemory(0.05, warm_kfs=10).warm_kfs, 0.9
    alpha = _t(0.34)
    for _ in range(K):
        alpha, _ = om.apply_occupancy_decay(alpha, torch.ones(1, dtype=torch.bool), 0.35, gamma)
    assert alpha[0].item() > 0.34 * gamma ** K - 1e-6
    assert alpha[0].item() < 0.34 * gamma ** (K - 3)   # 远低于"归零"形态


# ── ③ pt 钉死数值回归（postmortem 正面复现）────────────────────────────

def _simulate_pt(alpha0=0.30, warm=False, gate=True, n_kf=8, beta=0.9,
                 guard=0.35, decay=0.9):
    """pt 续命场景的多步模拟：占据者观测被当静态证据（evidence≈0）⇒ EMA 想抬升；
    gate 只减不升 ⇒ α 钉死；occupancy decay（warm=True）⇒ 穿 tau_carve。"""
    a = torch.tensor([alpha0], dtype=torch.float32)
    for _ in range(n_kf):
        pre = a.clone()
        evidence = torch.zeros(1)                     # 深度一致 ⇒ evidence≈0
        a, _ = al.ema_alpha_update(a, torch.zeros(1, 1), evidence, torch.ones(1, dtype=torch.bool), beta)
        if gate:
            a, _, _ = al.apply_evidence_gate(pre, a, torch.ones(1, dtype=torch.bool),
                                             torch.ones(1, dtype=torch.bool))
        if warm:
            a, _ = om.apply_occupancy_decay(a, torch.ones(1, dtype=torch.bool), guard, decay)
    return a[0].item()


def test_pt_pin_reproduced_without_occupancy():
    # 无温暖区（机制关）⇒ 钉死（不升过 pre，也不降到 tau_carve 之下）
    a = _simulate_pt(alpha0=0.30, warm=False, gate=True)
    assert 0.28 < a <= 0.30 + 1e-6      # 钉在 pre 附近（gate 压回）
    assert a > 0.20                      # carve 不可达（postmortem 的 0.2199 形态）


def test_pt_reaches_carve_with_occupancy():
    # 有温暖区 ⇒ α 每步再乘 γ ⇒ 跨过 tau_carve=0.20（carve 可达）
    # 注：EMA 每步把 α 拉向 (1−evidence)=1 的方向，但 gate 封顶压回 pre；
    # occupancy decay 在 EMA 之前作用于上一步结果，γ=0.9 ⇒ 0.30→0.27→0.243→0.219
    # 3 步仍在 0.20 上方 ⇒ 用 5 步（0.219×0.9=0.197 < 0.20）
    a = _simulate_pt(alpha0=0.30, warm=True, gate=True, n_kf=5)
    assert a < 0.20


# ── ④ 参数契约 ────────────────────────────────────────────────────────

def test_occupancy_defaults_off_and_mode_gated():
    d = al.AlphaLifecycleParams()
    assert d.occupancy_memory is False
    # 默认（无 config）⇒ 不启用
    p = al.read_alpha_lifecycle_params({})
    assert p.does_occupancy_memory is False
    # off 模式下即使开了 occupancy_memory 也不启用（mode 才是真开关）
    p = al.read_alpha_lifecycle_params(
        {"AlphaLifecycle": {"occupancy_memory": True}})
    assert p.occupancy_memory is True and p.does_occupancy_memory is False
    # EXIT 臂 + 开关 ⇒ 启用
    p = al.read_alpha_lifecycle_params(
        {"AlphaLifecycle": {"mode": "exit", "occupancy_memory": True}})
    assert p.does_occupancy_memory is True
    # 自定义键可读
    p = al.read_alpha_lifecycle_params({
        "AlphaLifecycle": {"mode": "exit", "occupancy_memory": True,
                           "occupancy_voxel_size": 0.1, "occupancy_warm_kfs": 5,
                           "occupancy_decay": 0.8, "occupancy_alpha_guard": 0.3}})
    assert (p.occupancy_voxel_size, p.occupancy_warm_kfs,
            p.occupancy_decay, p.occupancy_alpha_guard) == (0.1, 5, 0.8, 0.3)


# ── OccupancyMemory 表行为 ────────────────────────────────────────────

def test_ledger_observe_warm_evict():
    mem = om.OccupancyMemory(voxel_size=0.05, warm_kfs=3)
    keys = torch.tensor([100, 200], dtype=torch.int64)
    mem.observe(keys, kf_uid=10)
    assert mem._keys.tolist() == [100, 200] and mem._last.tolist() == [10, 10]
    mem.observe(torch.tensor([200], dtype=torch.int64), kf_uid=12)   # 重观察 ⇒ max
    assert mem._last.tolist() == [10, 12]
    # 键 = x·4194304 + y·2048 + z ⇒ key100/200 = vox (0,0,100)/(0,0,200)
    # ⇒ xyz = (0,0,100·vs)/(0,0,200·vs) = (0,0,5.0)/(0,0,10.0)
    xyz = torch.tensor([[0.0, 0.0, 5.0], [0.0, 0.0, 10.0]])
    w = mem.warm_mask(xyz, kf_uid=14)
    assert w.tolist() == [False, True]     # key100: 14-10=4 > 3 过期；key200: 2 ≤ 3
    assert mem.n_evictions == 0 and mem._keys.numel() == 2
    mem.observe(torch.tensor([300], dtype=torch.int64), kf_uid=20)   # 触发清理
    assert mem.n_evictions >= 2 and mem._keys.tolist() == [300]
