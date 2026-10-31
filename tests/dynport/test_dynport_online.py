"""DynPort 在线 adapter/管理器门禁（纯 CPU）：world↔pixel 桥接 + 反投影 + 管理器 step。

对齐 impl_design_dynport_L1.md §2.2/§3。用 fake viewpoint + fake model（CPU）验证：
- `_unproject`：掩码∧深度 → 世界点（相机系正确）；
- `GaussianModelMap.insert`：world→pixel 投影回投，落到 model 插入 API 的像素参数；
- `DynPortManager.step`：默认关不建状态；开则走通并落计数器。

用法：/data/conda_envs/monogs-ours/bin/python -m pytest tests/dynport/test_dynport_online.py -v
"""
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from utils.dyn_port_buffer import dynport_cfg, dynport_enabled  # noqa: E402
from utils.dyn_port_online import DynPortManager, GaussianModelMap  # noqa: E402

H = W = 16
FX = FY = 100.0
CX = CY = 8.0


class _FakeModel:
    """最小 GaussianModel 替身：像素级 insert_candidate_gaussians + lineage + prune_points。

    ⚠ 复制真实接口语义：`get_xyz` 是 **property**（D1-021 坑）。
    """
    def __init__(self):
        self._xyz = torch.zeros(0, 3)
        self.lineage_id = torch.empty(0).int()
        self.inserted_px = []

    @property
    def get_xyz(self):
        return self._xyz

    def ensure_lineage_state(self):
        if self.lineage_id.shape[0] != self._xyz.shape[0]:
            self.lineage_id = torch.full((self._xyz.shape[0],), -1, dtype=torch.int32)

    def insert_candidate_gaussians(self, cam, pixels_x, pixels_y, depth, color, kf_id,
                                   lineage_ids, min_gaussian_scale=None, max_gaussian_scale=None):
        n = int(len(pixels_x))
        if n == 0:
            return 0
        self.inserted_px.append(np.stack([np.asarray(pixels_x), np.asarray(pixels_y),
                                          np.asarray(depth)], 1))
        # 用像素反投影造世界坐标（与真实模型同约定），使后续 move/delete 有据
        R = np.asarray(cam.R, dtype=np.float64); T = np.asarray(cam.T, dtype=np.float64).reshape(3)
        xc = (np.asarray(pixels_x) - cam.cx) / cam.fx * np.asarray(depth)
        yc = (np.asarray(pixels_y) - cam.cy) / cam.fy * np.asarray(depth)
        pc = np.stack([xc, yc, np.asarray(depth)], 1)
        world = (R.T @ (pc - T).T).T
        self._xyz = torch.cat([self._xyz, torch.as_tensor(world, dtype=torch.float32)], 0)
        self.lineage_id = torch.cat([self.lineage_id,
                                     torch.as_tensor(np.asarray(lineage_ids), dtype=torch.int32)], 0)
        return n
    def prune_points(self, mask):
        keep = ~mask
        self._xyz = self._xyz[keep]
        self.lineage_id = self.lineage_id[keep]


class _Cam:
    def __init__(self, R, T):
        self.R, self.T = R, T
        self.fx, self.fy, self.cx, self.cy = FX, FY, CX, CY


class _Viewpoint:
    def __init__(self, depth, rgb, R, T):
        self.depth = torch.as_tensor(depth)
        self.original_image = torch.as_tensor(rgb)
        self.R = torch.as_tensor(R)
        self.T = torch.as_tensor(T)
        self.fx, self.fy, self.cx, self.cy = FX, FY, CX, CY


def _cam_eye():
    return np.eye(3), np.zeros(3)


# ── 反投影：掩码∧深度 → 相机系世界点（恒等位姿 ⇒ 相机系 = 世界系）────────────

def test_unproject_identity_pose():
    mgr = DynPortManager(_FakeModel(), {"DynPort": {"enabled": True}})
    depth = np.full((H, W), 1.0, np.float32)
    rgb = np.zeros((3, H, W), np.float32)
    mask = np.zeros((H, W), bool); mask[8, 8] = True
    R, T = _cam_eye()
    vp = _Viewpoint(depth, rgb, R, T)
    c2w = mgr._c2w(R, T)
    cam = {"fx": FX, "fy": FY, "cx": CX, "cy": CY, "R": R, "T": T}
    pts, cols, dbar = mgr._unproject(mask, depth, rgb, c2w, cam, stride=1)
    assert pts.shape[0] == 1 and abs(dbar - 1.0) < 1e-6
    # 恒等位姿：中心像素 (8,8) ⇒ 世界 (0,0,1)
    assert np.allclose(pts[0], [0.0, 0.0, 1.0], atol=1e-5), pts[0]


def test_unproject_empty_mask():
    mgr = DynPortManager(_FakeModel(), {"DynPort": {"enabled": True}})
    depth = np.full((H, W), 1.0, np.float32)
    rgb = np.zeros((3, H, W), np.float32)
    R, T = _cam_eye()
    pts, cols, dbar = mgr._unproject(np.zeros((H, W), bool), depth, rgb,
                                     np.eye(4), {"fx": FX, "fy": FY, "cx": CX, "cy": CY}, 1)
    assert pts.shape[0] == 0 and dbar is None


# ── world→pixel 桥接：投影回投（恒等位姿 ⇒ 原像素）──────────────────────────

def test_world_to_pixel_roundtrip():
    m = _FakeModel()
    gmap = GaussianModelMap(m, lineage_base=100)
    R, T = _cam_eye()
    gmap.set_camera({"fx": FX, "fy": FY, "cx": CX, "cy": CY, "R": R, "T": T})
    # 世界点 = 中心像素在 z=1 处的反投影
    world = np.array([[0.0, 0.0, 1.0], [0.2, 0.0, 1.0]], np.float32)
    idx = gmap.insert(world, np.ones((2, 3), np.float32) * 0.5, lineage_id=100)
    assert idx.shape[0] == 2
    px = m.inserted_px[-1]
    assert np.allclose(px[0, :2], [CX, CY], atol=1e-4), px[0]
    assert np.allclose(px[0, 2], 1.0, atol=1e-5)


# ── lineage 过滤 / move / delete ────────────────────────────────────────────

def test_dyn_indices_and_delete():
    m = _FakeModel()
    gmap = GaussianModelMap(m, lineage_base=100)
    R, T = _cam_eye()
    gmap.set_camera({"fx": FX, "fy": FY, "cx": CX, "cy": CY, "R": R, "T": T})
    gmap.insert(np.array([[0., 0, 1], [0.2, 0, 1]], np.float32), np.ones((2, 3), np.float32), 100)
    gmap.insert(np.array([[0.4, 0, 1]], np.float32), np.ones((1, 3), np.float32), 101)
    assert gmap.dyn_indices([100]).shape[0] == 2
    assert gmap.dyn_indices([100, 101]).shape[0] == 3
    assert gmap.dyn_indices([999]).shape[0] == 0
    gmap.delete(gmap.dyn_indices([100]))
    assert gmap.dyn_indices([100]).shape[0] == 0
    assert gmap.dyn_indices([101]).shape[0] == 1


# ── 管理器 step：关闭不建状态；开则走通 ─────────────────────────────────────

def test_manager_step_disabled_returns_none_or_noop():
    m = _FakeModel()
    mgr = DynPortManager(m, {"DynPort": {"enabled": False}})
    assert dynport_enabled({"DynPort": {"enabled": False}}) is False
    # step 本身不做 enable 判断（接线层判）；此处验证无掩码/深度 ⇒ None
    R, T = _cam_eye()
    vp = _Viewpoint(np.full((H, W), 1.0, np.float32), np.zeros((3, H, W), np.float32), R, T)
    vp.depth = None
    assert mgr.step(0, vp, np.zeros((H, W), bool)) is None


def test_manager_step_inserts_and_counts():
    m = _FakeModel()
    cfg = {"DynPort": {"enabled": True, "lineage_base": 100, "lam_d": 0.05, "cap": 100, "lmax": 1000,
                       "unproj_stride": 1}}
    mgr = DynPortManager(m, cfg)
    depth = np.full((H, W), 1.0, np.float32)
    rgb = np.zeros((3, H, W), np.float32)
    mask = np.zeros((H, W), bool); mask[8, 8] = True
    R, T = _cam_eye()
    vp = _Viewpoint(depth, rgb, R, T)
    rec = mgr.step(0, vp, mask)
    assert rec is not None and rec["inserted"] == 1
    assert mgr.core.case2_new == 1 and mgr.core.n == 1
    # 第二帧同位置 ⇒ Case1 复用
    rec2 = mgr.step(1, vp, mask)
    assert mgr.core.case1_hits == 1 and mgr.core.n == 1
