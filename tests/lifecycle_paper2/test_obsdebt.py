"""prereg_L1f_obsdebt 的单元测试：账本 + 分配律 + 两态默认值。

判据权威 = prereg §3/§4；代码不重新定义判据。
安全判据（DISCIPLINE 代码保护节）：obsdebt 默认 False ⇒ 行为与主线逐位一致。
"""
import numpy as np
import torch
import yaml
from pathlib import Path

from utils import obsdebt
from utils.alpha_lifecycle import AlphaLifecycleParams, read_alpha_lifecycle_params


# ---------------------------------------------------------------- 账本
def test_ledger_accumulates_per_kf():
    """每 KF 每 voxel 至多 +1；重复观测累计；未观测 = 0；查询纯函数（不改表）。"""
    l = obsdebt.ObsDebtLedger(0.05)
    k = torch.tensor([100, 200], dtype=torch.int64)
    l.observe(k)                       # KF1: +1 each
    l.observe(torch.tensor([100], dtype=torch.int64))  # KF2: 100 再 +1
    before = (l._keys.clone(), l._debt.clone())
    d = l.debt_at(torch.tensor([100, 200, 999], dtype=torch.int64))
    assert d.tolist() == [2, 1, 0]
    assert (l._keys == before[0]).all() and (l._debt == before[1]).all()


def test_ledger_debt_never_decays():
    """欠账语义：账本无衰减/淘汰接口（与 L1c OccupancyMemory 的本质区别）。"""
    l = obsdebt.ObsDebtLedger(0.05)
    l.observe(torch.tensor([7], dtype=torch.int64))
    for _ in range(50):
        pass  # 时间流逝
    assert l.debt_at(torch.tensor([7], dtype=torch.int64)).item() == 1
    assert not hasattr(l, "_evict") and not hasattr(l, "warm_kfs")


def test_unproject_flatidx_matches_occupancy_convention():
    """体素键哈希与 occupancy_memory 同约定（同一点 → 同键）。"""
    from utils import occupancy_memory
    class V:  # 最小 viewpoint stub
        R = torch.eye(3); T = torch.zeros(3)
        fx = fy = 500.0; cx = 320.0; cy = 240.0
    v = V()
    depth = torch.full((480, 640), 2.0)
    idx = torch.tensor([240 * 640 + 320])  # 中心像素
    k1 = obsdebt.unproject_flatidx_to_voxels(idx, depth, v, 0.05)
    k2 = occupancy_memory.unproject_mask_to_voxels(idx, depth, v, 0.05)
    assert k1.numel() == 1 and k2.numel() == 1 and k1.item() == k2.item()


# ---------------------------------------------------------------- 分配律
def test_fill_budget_under_budget_is_identity():
    """vacated ≤ 预算 ⇒ 原样返回（不重排——保序与旧管线一致）。"""
    l = obsdebt.ObsDebtLedger(0.05)
    uu = np.arange(10); vv = np.arange(10) * 2
    vk = torch.zeros(10, dtype=torch.int64)
    u2, v2, st = obsdebt.fill_budget_by_debt(uu, vv, vk, l, 20)
    assert (u2 == uu).all() and (v2 == vv).all() and st["dropped"] == 0


def test_fill_budget_prefers_high_debt():
    """超预算 ⇒ 债务降序保留（负对照：注入已知债务分布必须读出对应保留集）。"""
    l = obsdebt.ObsDebtLedger(0.05)
    # 10 个 voxel，债务 = [0,1,2,...,9]（键即 1000*i 便于区分）
    keys = torch.tensor([1000 * i for i in range(10)], dtype=torch.int64)
    for i in range(10):
        l.observe(keys[i:i + 1].repeat(i))   # key_i 债务 = i
    uu = np.arange(10); vv = np.arange(10)
    u2, v2, st = obsdebt.fill_budget_by_debt(uu, vv, keys, l, 5)
    assert st["kept"] == 5 and st["dropped"] == 5
    # 债务 9..5 的索引（5,6,7,8,9）应全部保留
    assert set(u2.tolist()) == {5, 6, 7, 8, 9}


def test_fill_budget_stable_within_equal_debt():
    """同债内保持原相对顺序（确定性）。"""
    l = obsdebt.ObsDebtLedger(0.05)
    keys = torch.tensor([1, 2, 3, 4], dtype=torch.int64)
    l.observe(keys)   # 全部债 1
    uu = np.array([10, 20, 30, 40]); vv = np.zeros(4, dtype=int)
    u2, _, _ = obsdebt.fill_budget_by_debt(uu, vv, keys, l, 2)
    assert u2.tolist() == [10, 20]


# ---------------------------------------------------------------- 两态默认
def test_default_off():
    """默认参数 obsdebt=False（代码安全判据：default-off 与主线逐位一致）。"""
    p = AlphaLifecycleParams()
    assert p.obsdebt is False
    assert p.obsdebt_voxel_size > 0 and p.obsdebt_iter_boost >= 0


def test_config_reader_reads_obsdebt_keys(tmp_path):
    """config reader 透传 obsdebt 三键；缺省走默认（False）。"""
    cfg_off = {"AlphaLifecycle": {"mode": "exit_fill"}}
    p = read_alpha_lifecycle_params(cfg_off)
    assert p.obsdebt is False
    cfg_on = {"AlphaLifecycle": {"mode": "exit_fill", "obsdebt": True,
                                 "obsdebt_voxel_size": 0.1,
                                 "obsdebt_iter_boost": 0.3}}
    p2 = read_alpha_lifecycle_params(cfg_on)
    assert p2.obsdebt is True
    assert abs(p2.obsdebt_voxel_size - 0.1) < 1e-9
    assert abs(p2.obsdebt_iter_boost - 0.3) < 1e-9


# ---------------------------------------------------------------- 关卡① 整改
def test_boost_grad_mask_old_prims_bitwise_frozen():
    """关卡① 致命-1 负对照：独立 Adam + grad 掩码 ⇒ 老基元逐位不动。

    构造 6 行参数（前 4 老 / 后 2 新），非选择行梯度清零后 step 多次：
    Adam 对 grad≡0 且 m/v≡0（全新优化器）的行步长恒为精确 0。
    共享优化器版本（陈旧 exp_avg）会推动老基元——此测试钉死独立优化器形态。
    """
    from utils.slam_backend import transient_fit_build_optimizer, transient_fit_mask_grads
    from munch import Munch

    class G:
        pass
    g = G()
    base = torch.zeros(6, 3)
    base[:, 0] = 1.0   # 老基元特征值 1（非零，便于检测任何位移）
    g._xyz = base.clone().requires_grad_(True)
    g._scaling = torch.full((6, 3), 0.1).requires_grad_(True)
    g._rotation = torch.zeros(6, 4).requires_grad_(True)
    g._opacity = torch.full((6, 1), 0.5).requires_grad_(True)
    g._features_dc = torch.randn(6, 1, 3).requires_grad_(True)
    opt, groups = transient_fit_build_optimizer(g)
    sel = torch.tensor([False, False, False, False, True, True])
    before = {name: p.detach().clone() for name, p in
              (("xyz", g._xyz), ("scale", g._scaling), ("opa", g._opacity))}
    for _ in range(5):
        # 伪造梯度：全行非零（模拟整图反传），再掩码掉老基元
        for p, _lr in groups:
            p.grad = torch.randn_like(p)
        transient_fit_mask_grads(groups, sel)
        opt.step()
    assert torch.equal(g._xyz.detach()[:4], before["xyz"][:4]), "老基元 xyz 被推动"
    assert torch.equal(g._scaling.detach()[:4], before["scale"][:4]), "老基元 scale 被推动"
    assert torch.equal(g._opacity.detach()[:4], before["opa"][:4]), "老基元 opacity 被推动"
    # 新基元必须动过
    assert not torch.equal(g._xyz.detach()[4:], before["xyz"][4:])


def test_boost_grad_enabled_inside_no_grad_scope():
    """2026-09-24 点火验证缺陷回归：boost 段须能在 no_grad 作用域内反传。

    复现原 bug：在 `with torch.no_grad():` 里直接 backward ⇒
    "element 0 of tensors does not require grad"（实测日志）。修法 = 局部
    `torch.enable_grad()`。本测试钉死"局部重开梯度可行"这一前提。
    """
    from utils.slam_backend import transient_fit_build_optimizer, transient_fit_mask_grads
    import torch as _t

    class G:
        pass
    g = G()
    g._xyz = _t.zeros(4, 3).requires_grad_(True)
    g._scaling = _t.full((4, 3), 0.1).requires_grad_(True)
    g._rotation = _t.zeros(4, 4).requires_grad_(True)
    g._opacity = _t.full((4, 1), 0.5).requires_grad_(True)
    g._features_dc = _t.randn(4, 1, 3).requires_grad_(True)
    opt, groups = transient_fit_build_optimizer(g)
    sel = _t.tensor([False, False, True, True])

    with _t.no_grad():
        with _t.enable_grad():
            loss = (g._xyz * 2.0).sum()
            opt.zero_grad(set_to_none=True)
            loss.backward()                      # 不许可抛异常
            transient_fit_mask_grads(groups, sel)
            opt.step()
    # sel=[F,F,T,T] ⇒ 索引 2,3 是"被选中的新基元"（应被推动），0,1 不动
    assert not _t.equal(g._xyz.detach()[2:], _t.zeros(2, 3))
    assert _t.equal(g._xyz.detach()[:2], _t.zeros(2, 3))
