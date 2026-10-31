"""DynPort 因果快照门禁（纯 CPU）：默认关零副作用；开则逐帧落盘动态层 + 收尾静态掩码。

对齐 utils/dynport_causal_log.py 与 E2 先例（causal_render_log.py）。理由：final-map 仪器对
瞬态层结构性有偏（动态基元停在末帧位置，渲染早期帧=错位），须因果快照修正。

用法：/data/conda_envs/monogs-ours/bin/python -m pytest tests/dynport/test_dynport_causal.py -v
"""
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from utils.dynport_causal_log import (  # noqa: E402
    DynPortCausalWriter, dynport_causal_cfg, load_snapshot,
)


class _FakeModel:
    def __init__(self, n, dyn_rows):
        self._xyz = torch.zeros(n, 3)
        self._scaling = torch.zeros(n, 3)
        self._rotation = torch.zeros(n, 4); self._rotation[:, 0] = 1.0
        self._opacity = torch.zeros(n, 1)
        self._features_dc = torch.zeros(n, 1, 3)
        self.lineage_id = torch.full((n,), -1, dtype=torch.int32)
        for i in dyn_rows:
            self.lineage_id[i] = 100
        self.dyn_lineage_base = 100

    def ensure_lineage_state(self):
        pass


def test_default_off_zero_side_effects(tmp_path):
    cfg = {"DynPort": {"causal_log": {"enabled": False}}, "Results": {"save_dir": str(tmp_path)}}
    w = DynPortCausalWriter(cfg)
    assert w.enabled is False
    m = _FakeModel(5, [2, 3])
    assert w.log_frame(0, np.eye(4), m, [100]) is False
    assert w.save_static_mask(m) is False
    assert not (tmp_path / "dynport_causal").exists(), "关闭时不得建目录"


def test_on_writes_dynamic_rows_only(tmp_path):
    cfg = {"DynPort": {"causal_log": {"enabled": True, "out_dir": str(tmp_path / "causal")}},
           "Results": {}}
    w = DynPortCausalWriter(cfg)
    m = _FakeModel(5, [2, 3])
    assert w.log_frame(0, np.eye(4), m, [100]) is True
    fp = tmp_path / "causal" / "frame_000000.npz"
    assert fp.exists()
    snap = load_snapshot(fp)
    assert snap["xyz"].shape[0] == 2, "只存动态行"
    assert snap["c2w"].shape == (4, 4)
    assert int(snap["frame_idx"]) == 0


def test_static_mask_marks_dynamic_rows(tmp_path):
    cfg = {"DynPort": {"causal_log": {"enabled": True, "out_dir": str(tmp_path / "causal")}},
           "Results": {}}
    w = DynPortCausalWriter(cfg)
    m = _FakeModel(5, [2, 3])
    assert w.save_static_mask(m) is True
    mask = np.load(tmp_path / "causal" / "dynamic_rows.npy")
    assert mask.tolist() == [False, False, True, True, False]


def test_every_n_subsample(tmp_path):
    cfg = {"DynPort": {"causal_log": {"enabled": True, "every_n": 3, "out_dir": str(tmp_path / "c")}},
           "Results": {}}
    w = DynPortCausalWriter(cfg)
    m = _FakeModel(4, [1])
    assert w.log_frame(0, np.eye(4), m, [100]) is True
    assert w.log_frame(1, np.eye(4), m, [100]) is False
    assert w.log_frame(3, np.eye(4), m, [100]) is True


def test_no_dynamic_no_snapshot(tmp_path):
    cfg = {"DynPort": {"causal_log": {"enabled": True, "out_dir": str(tmp_path / "c")}}, "Results": {}}
    w = DynPortCausalWriter(cfg)
    m = _FakeModel(4, [])
    assert w.log_frame(0, np.eye(4), m, []) is False
    assert w.log_frame(0, np.eye(4), m, [100]) is False, "无匹配行 ⇒ 不写"


def test_cfg_validation():
    assert dynport_causal_cfg({"DynPort": {}})["enabled"] is False
    try:
        dynport_causal_cfg({"DynPort": {"causal_log": {"enabled": "yes"}}})
        assert False
    except ValueError:
        pass
