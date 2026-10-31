"""prereg_instrument_v2 §2 口径的单元测试：三对照构造 + 负对照。"""
import numpy as np
import torch

from utils.instrument_v2_core import (
    compute_matched_control_mask,
)


def _scene(H=120, W=160, vac_box=(30, 50, 60, 90), z_vac=2.0, z_bg=2.0):
    """合成一帧：GT 深度全场 z_bg，vacated 矩形内 z_vac。返回 (gt_depth, dyn, past)。"""
    gt = np.full((H, W), z_bg, dtype=np.float32)
    dyn = np.zeros((H, W), dtype=bool)
    past = np.zeros((H, W), dtype=bool)
    r0, r1, c0, c1 = vac_box
    gt[r0:r1, c0:c1] = z_vac
    past[r0:r1, c0:c1] = True
    return torch.from_numpy(gt), torch.from_numpy(dyn), torch.from_numpy(past)


def test_m3_matches_same_depth_band():
    """同深度对照构造：背景 = vac 同深度 ⇒ m3 全场可作对照（≠ ring/全域里含异深度）。"""
    gt, dyn, past = _scene(z_vac=2.0, z_bg=2.0)
    m = compute_matched_control_mask(gt, dyn, past, valid_gt=torch.ones_like(gt, dtype=torch.bool),
                                     band=0.15, edge_margin_px=5, support_min_px=200)
    assert m is not None and int(m.sum()) >= 200


def test_m3_excludes_different_depth():
    """背景深度与 vac 带不匹配 ⇒ m3 排除之（若全部被排除 ⇒ None）。"""
    gt, dyn, past = _scene(z_vac=2.0, z_bg=4.0)
    m = compute_matched_control_mask(gt, dyn, past, valid_gt=torch.ones_like(gt, dtype=torch.bool),
                                     band=0.15, edge_margin_px=5, support_min_px=200)
    assert m is None  # 全场无同深度静态像素


def test_m3_excludes_edge_margin():
    """边缘 15px 排除：细窄场景无法提供远离边缘的同深度像素 ⇒ None。"""
    gt, dyn, past = _scene(H=20, W=20, vac_box=(5, 10, 5, 10), z_vac=2.0, z_bg=2.0)
    m = compute_matched_control_mask(gt, dyn, past, valid_gt=torch.ones_like(gt, dtype=torch.bool),
                                     band=0.15, edge_margin_px=15, support_min_px=200)
    assert m is None


def test_m3_support_floor():
    """支撑下限：同深度像素仅 100 px < 200 ⇒ None（仪器参数，prereg §2）。"""
    gt = np.full((120, 160), 2.0, dtype=np.float32)
    gt[30:50, 60:90] = 2.0
    dyn = np.zeros((120, 160), dtype=bool)
    past = np.zeros((120, 160), dtype=bool)
    past[30:50, 60:90] = True
    gt[(dyn | past).astype(bool)] = np.nan
    # 只留 100 个有效同深度像素
    valid = np.zeros((120, 160), dtype=bool)
    valid[60:70, 60:70] = True
    m = compute_matched_control_mask(torch.from_numpy(gt), dyn, past,
                                     valid_gt=torch.from_numpy(valid),
                                     band=0.15, edge_margin_px=5, support_min_px=200)
    assert m is None


def test_negative_control_known_effect_readable():
    """负对照（prereg §3 精神：尺子必须能读出已知效应）：
    渲染深度在 vac 区注入 +8cm 幽灵偏移 ⇒ exc_m3 ≈ +8cm（同深度带对照不含该偏移）。"""
    gt, dyn, past = _scene(z_vac=2.0, z_bg=2.0)
    valid = torch.ones_like(gt, dtype=torch.bool)
    m3 = compute_matched_control_mask(gt, dyn, past, valid_gt=valid,
                                      band=0.15, edge_margin_px=5, support_min_px=200)
    assert m3 is not None
    rend = gt.clone()
    rend[past.bool()] = rend[past.bool()] + 0.08   # 幽灵 = 被拉到身后 8cm
    l1 = (rend - gt).abs()
    exc_m3 = float((l1[past.bool()].mean() - l1[m3.bool()].mean()) * 100.0)
    assert abs(exc_m3 - 8.0) < 1.0, exc_m3
