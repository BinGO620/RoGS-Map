"""test_l1e_seam.py — L1e 缝隙带救援（D2-008）单元门禁。

覆盖（prereg_L1e_seam.md §1/§7 的实装契约）：
① 四合取选择器：三信号齐 ⇒ 删；缺任一 ⇒ 不删（逐信号负对照）；
② 安全性：α≥seam_tau / 区域外 / 深度差出带 ⇒ 永不删；净静态 α≈1 不可达；
③ 参数契约：seam_carve 默认 False；仅 exit_fill 臂启用（exit 臂 seam=True = config
   错误，选择器拒绝——删除必须配 fill，crowd3 挖洞形态的机制级防线）；
④ L1e config 两态实例化（seam 臂双 flag + param 臂两常数落进 params）；
⑤ default-off 逐位一致（off 臂不写 seam 键 ⇒ params 与既有默认逐键相同）。
"""
import sys
from pathlib import Path

import torch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils import alpha_lifecycle as al  # noqa: E402

CONFIGS = Path(__file__).resolve().parents[2] / "configs/experiments/lifecycle_paper2"


def _t(*vals):
    return torch.tensor(vals, dtype=torch.float32)


def _sel(alpha=0.2, z=1.0, obs_at=1.07, obs_count=5.0, vacated=True, valid=True):
    return al.select_seam_carve_mask(
        z=_t(z), obs_at_gauss=_t(obs_at), alpha=_t(alpha),
        obs_count=_t(obs_count), sem_vacated_at_gauss=torch.tensor([vacated]),
        valid=torch.tensor([valid]),
        seam_tau=0.25, seam_delta_m=0.05, seam_hi_m=0.10, min_obs_count=3.0,
    )


# ── ① 四合取：正例 + 逐信号负对照 ─────────────────────────────────

def test_seam_fires_when_all_four_agree():
    # z=1.0, obs=1.07 ⇒ 深度差 0.07 ∈ 缝隙带 [0.05, 0.10)；α=0.2<0.25；obs=5≥3；区域 vacated
    assert bool(_sel()[0])


def test_seam_negative_per_conjunct():
    assert not bool(_sel(vacated=False)[0])       # 缺掩码区域证据（crowd3 反例）
    assert not bool(_sel(alpha=0.30)[0])          # α 高于 seam_tau（净静态防护）
    assert not bool(_sel(z=1.0, obs_at=1.20)[0])  # 深度差 0.20 ≥ 0.10：归原 carve 管，非缝隙
    assert not bool(_sel(z=1.0, obs_at=1.03)[0])  # 深度差 0.03 < 0.05：贴面结构，reset 域
    assert not bool(_sel(obs_count=2.0)[0])       # 持续性不足（单帧证据永不硬删）
    assert not bool(_sel(valid=False)[0])         # 投影无效


# ── ② 安全性：边界值形态 ─────────────────────────────────────────

def test_seam_band_edges():
    # 带边界（半开 [0.05, 0.10)）。注意 f32 精度：恰在边界的差值有表示误差
    # （f32 下 1.05-1.0 = 0.04999995），用离边界 1e-3 的值测语义。
    assert not bool(_sel(z=1.0, obs_at=1.049)[0])   # 差 0.049 < 下限：reset 域
    assert bool(_sel(z=1.0, obs_at=1.051)[0])       # 差 0.051：带内下端
    assert bool(_sel(z=1.0, obs_at=1.099)[0])       # 差 0.099：带内上端
    assert not bool(_sel(z=1.0, obs_at=1.101)[0])   # 差 0.101 ≥ 上限：原 carve 域


def test_seam_cannot_touch_net_static():
    """净静态 α≈1 被多帧 FP 盖住：α 门(seam_tau=0.25)永不可达。"""
    alpha = _t(0.95)
    for _ in range(10):
        ema = al.ema_alpha_update(alpha, _t(0.0), _t(0.0),
                                  torch.ones(1, dtype=torch.bool), beta=0.9)[0]
        # 假设掩码 FP 且几何 FP（最坏情况）：只有 α 门能救
        hit = al.select_seam_carve_mask(
            z=_t(1.0), obs_at_gauss=_t(1.10), alpha=alpha,
            obs_count=_t(10.0), sem_vacated_at_gauss=torch.tensor([True]),
            valid=torch.ones(1, dtype=torch.bool),
            seam_tau=0.25, seam_delta_m=0.05, seam_hi_m=0.10, min_obs_count=3.0,
        )
        assert not bool(hit[0])
        alpha = ema.clone()
    assert float(alpha[0]) > 0.8


# ── ③ 参数契约：门控与模式绑定 ───────────────────────────────────

def test_seam_default_off_and_exitfill_only():
    p = al.AlphaLifecycleParams()
    assert p.seam_carve is False and p.does_seam_carve is False
    # exit 臂写 True = config 错误：删除必须配 fill（crowd3 防线），拒绝启用
    p_exit = al.AlphaLifecycleParams(mode=al.MODE_EXIT, seam_carve=True)
    assert p_exit.does_seam_carve is False
    p_fill = al.AlphaLifecycleParams(mode=al.MODE_EXIT_FILL, seam_carve=True)
    assert p_fill.does_seam_carve is True
    # observe（安慰剂臂）同拒
    p_obs = al.AlphaLifecycleParams(mode=al.MODE_OBSERVE, seam_carve=True)
    assert p_obs.does_seam_carve is False


# ── ④ 两个 L1e config 的两态实例化 ───────────────────────────────

def test_l1e_seam_config_fires():
    with open(CONFIGS / "l1e_person_tracking_seam.yaml") as f:
        cfg = yaml.safe_load(f)
    p = al.read_alpha_lifecycle_params(cfg)
    assert p.mode == "exit_fill"
    assert p.does_seam_carve is True and p.does_fill is True
    assert p.seam_warm_kfs == 8 and abs(p.seam_delta_m - 0.05) < 1e-9
    assert abs(p.seam_hi_m - 0.10) < 1e-9
    assert abs(p.seam_tau - 0.25) < 1e-9


def test_l1e_param_config_carries_constants():
    with open(CONFIGS / "l1e_person_tracking_paramrescue.yaml") as f:
        cfg = yaml.safe_load(f)
    p = al.read_alpha_lifecycle_params(cfg)
    assert p.mode == "exit_fill"
    assert p.does_seam_carve is False                    # 零新代码臂：seam 关
    assert abs(p.tau_carve - 0.25) < 1e-9                # 抬 α 阈
    assert abs(p.delta_free_m - 0.05) < 1e-9             # 降几何带
    assert p.does_fill is True


# ── ⑤ default-off 逐位一致 ──────────────────────────────────────

def test_default_off_bitwise_identity():
    """不写 seam 键的 config（含完整 L1d 栈）解析后 seam 相关键 = 类默认。"""
    with open(CONFIGS / "l1d_person_tracking_stacked.yaml") as f:
        cfg = yaml.safe_load(f)
    p = al.read_alpha_lifecycle_params(cfg)
    d = al.AlphaLifecycleParams(mode="exit", evidence_gate=True,
                                occupancy_memory=True,
                                occupancy_voxel_size=0.05, occupancy_warm_kfs=10,
                                occupancy_decay=0.9, occupancy_alpha_guard=0.35)
    for k in ("seam_carve", "seam_warm_kfs", "seam_delta_m", "seam_tau"):
        assert getattr(p, k) == getattr(d, k), k
