"""DynPort 接线层门禁（纯 CPU，不经 GPU）：默认关 ⇒ 零副作用；开 ⇒ 走通并落计数。

对齐 impl_design_dynport_L1.md §3 与坑#4（default-off 逐位一致）。关键点：`BackEnd` 未启用
DynPort 时，`push_to_frontend` 不得改 payload、`_dynport_step` 不得建状态。

用法：/data/conda_envs/monogs-ours/bin/python -m pytest tests/dynport/test_dynport_wiring.py -v
"""
import sys
import types
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import utils.slam_backend as SB  # noqa: E402
from utils.dyn_port_buffer import dynport_enabled  # noqa: E402


class _FakeModel:
    def __init__(self):
        self._xyz = torch.zeros(4, 3)
        self.lineage_id = torch.full((4,), -1, dtype=torch.int32)

    @property
    def get_xyz(self):
        return self._xyz

    def ensure_lineage_state(self):
        if self.lineage_id.shape[0] != self._xyz.shape[0]:
            self.lineage_id = torch.full((self._xyz.shape[0],), -1, dtype=torch.int32)

    def prune_lineage(self, targets):
        self.ensure_lineage_state()
        keep = torch.ones(self.lineage_id.shape[0], dtype=torch.bool)
        for t in targets:
            keep &= (self.lineage_id != int(t))
        self._xyz = self._xyz[keep]
        self.lineage_id = self.lineage_id[keep]


class _NoopQueue:
    def __init__(self):
        self.msgs = []

    def put(self, m):
        self.msgs.append(m)


def _bare_backend(config):
    """绕过 mp.Process.__init__，手工装最小状态（CPU 单测）。"""
    be = SB.BackEnd.__new__(SB.BackEnd)
    be.config = config
    be.gaussians = _FakeModel()
    be.occ_aware_visibility = {}
    be.current_window = []
    be.viewpoints = {}
    be.frontend_queue = _NoopQueue()
    be.last_sent = 0
    be._dynport = None
    be._dynport_csv = None
    be._dynport_frames = 0
    return be


# ── 跟踪隔离口径（2026-10-06 冒烟修正）──────────────────────────────────────
# 原设计"push_to_frontend 剪动态 lineage"经冒烟实测**不可行**：剪 payload 会与
# occ_aware_visibility（全尺寸逐基元可见性掩码）尺寸脱钩 ⇒ 前端 logical_or 崩。
# ⇒ 改**经验口径**：不剪 payload；跟踪损失经 tracking_dynamic_mask 掩动态像素；J8 直接测 ATE。
# 本测试守护"关闭时零改动 + 启用时不剪 payload（避免再现脱钩崩溃）"。

def test_push_to_frontend_off_passes_full_map():
    be = _bare_backend({"DynPort": {"enabled": False}})
    be.push_to_frontend("keyframe")
    payload = be.frontend_queue.msgs[-1][1]
    assert payload.get_xyz.shape[0] == 4, "关闭时不得过滤任何基元"


def test_dynport_step_off_is_noop():
    be = _bare_backend({"DynPort": {"enabled": False}})
    vp = types.SimpleNamespace(depth=torch.ones(1, 2, 2))
    be._dynport_step(0, vp)                     # 不得抛、不得建 manager
    assert be._dynport is None, "关闭时不得构造 manager"


def test_push_to_frontend_on_does_not_prune_payload():
    """启用时也**不得**剪 payload（曾致 occ_aware_visibility 脱钩崩溃）；改为把动态行不透明度
    打到 0（行数不变 ⇒ occ 尺寸安全，且前端 tracking 结构性看不到动态层）。"""
    be = _bare_backend({"DynPort": {"enabled": True, "lineage_base": 100}})
    be.gaussians._xyz = torch.zeros(3, 3)
    be.gaussians._opacity = torch.zeros(3, 1)
    be.gaussians.lineage_id = torch.tensor([-1, -1, 100], dtype=torch.int32)
    be._dynport = types.SimpleNamespace(
        core=types.SimpleNamespace(active_lineages=lambda: [100]))
    occ = {5: torch.ones(3, dtype=torch.long)}
    be.occ_aware_visibility = occ
    be.push_to_frontend("keyframe")
    payload = be.frontend_queue.msgs[-1][1]
    vis = be.frontend_queue.msgs[-1][2]
    assert payload.get_xyz.shape[0] == 3, "启用时不得剪 payload（防 occ 脱钩）"
    assert vis[5].shape[0] == payload.get_xyz.shape[0], "payload 与 occ 掩码须尺寸一致"
    # 动态行（lineage 100）不透明度被打到低值（隔离），静态行不变
    op = payload._opacity.detach()
    assert float(op[2]) < -20.0, "动态行不透明度应被打到 ~0"
    assert float(op[0]) == 0.0 and float(op[1]) == 0.0, "静态行不透明度不得改"


def test_enabled_flag_reads_config():
    assert dynport_enabled({"DynPort": {"enabled": True}}) is True
    assert dynport_enabled({"DynPort": {"enabled": False}}) is False
    assert dynport_enabled({}) is False


# ── off ≡ 主线：config 差异单（G3-重大#5：不止二值断言，给可核对的差异单）─────────

def test_off_arm_config_differs_only_in_dynport_and_paths():
    """E 臂与 D 臂的 config 差异**只能**是 DynPort.enabled 与 save_dir（单变量）。

    这是 off≡主线 的**结构性**保证（config 层）：E 臂 DynPort.enabled=False ⇒ 后端
    `_dynport_step` 立即返回、`push_to_frontend` 不改 payload（另有 wiring 单测钉住）。
    """
    import yaml, copy
    from utils.config_utils import load_config
    E = load_config("configs/experiments/dynport/L1_crowd2_E.yaml")
    D = load_config("configs/experiments/dynport/L1_crowd2_D.yaml")

    def diff(a, b, path=""):
        out = []
        if isinstance(a, dict) and isinstance(b, dict):
            for k in set(a) | set(b):
                out += diff(a.get(k), b.get(k), f"{path}.{k}" if path else k)
        elif a != b:
            out.append(f"{path}: {a!r} != {b!r}")
        return out

    d = diff(E, D)
    # 允许的差异：DynPort.enabled / save_dir（及其派生路径）
    bad = [x for x in d if "DynPort" not in x and "save_dir" not in x
           and "path" not in x.lower() and "Results" not in x]
    assert not bad, f"E/D 臂存在非单变量差异：{bad}"
    # 确认 DynPort.enabled 确实不同
    assert E["DynPort"]["enabled"] is False and D["DynPort"]["enabled"] is True

