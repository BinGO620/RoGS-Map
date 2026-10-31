"""DynPort 核心决策核门禁（纯 CPU，不经 GPU）：MapAccess 协议 + Case1/Case2 + Cond1/Cond2 + cap + J5。

对齐 impl_design_dynport_L1.md §3（单测 ①⑤ + ②③）。默认关 ≠ 主线在接线层另有守护。
核心设计（2026-10-05 实装期修正）：决策核只依赖 `MapAccess` 协议（在线 = GaussianModel adapter；
测试 = FakeMap），不 import 探针/不持有 run。

用法：/data/conda_envs/monogs-ours/bin/python -m pytest tests/dynport/test_dynport_buffer.py -v
"""
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from utils.dyn_port_buffer import (  # noqa: E402
    DynPortBuffer, dynport_cfg, dynport_enabled, get_dynport_config,
)


class FakeMap:
    """MapAccess 的内存实现：全局下标稳定，删除用 tombstone（不重排 ⇒ 下标不漂移）。"""

    def __init__(self):
        self.xyz = []            # list[np.ndarray(3,)]
        self.lin = []            # list[int] 与 xyz 平行
        self.col = []

    def dyn_indices(self, lineage_ids):
        want = set(int(x) for x in lineage_ids)
        out = [i for i, l in enumerate(self.lin) if l in want]
        return np.asarray(out, dtype=np.int64)

    def world_points(self, idx):
        idx = np.asarray(idx, dtype=np.int64)
        return np.asarray([self.xyz[i] for i in idx], dtype=np.float32).reshape(-1, 3)

    def lineage_of(self, idx):
        idx = np.asarray(idx, dtype=np.int64)
        return np.asarray([self.lin[i] for i in idx], dtype=np.int32)

    def move(self, idx, new_xyz):
        for k, i in enumerate(np.asarray(idx, dtype=np.int64)):
            self.xyz[int(i)] = np.asarray(new_xyz, dtype=np.float32)[k]

    def insert(self, world, colors, lineage_id):
        world = np.asarray(world, dtype=np.float32).reshape(-1, 3)
        cols = np.asarray(colors, dtype=np.float32).reshape(-1, 3)
        out = []
        for k in range(world.shape[0]):
            self.xyz.append(world[k]); self.lin.append(int(lineage_id))
            self.col.append(cols[k] if k < cols.shape[0] else np.zeros(3, np.float32))
            out.append(len(self.xyz) - 1)
        return np.asarray(out, dtype=np.int64)

    def delete(self, idx):
        for i in np.asarray(idx, dtype=np.int64):
            self.lin[int(i)] = None          # tombstone 出 dyn 域


CFG = {"lam_d": 0.05, "cap": 100, "lmax": 3, "unproj_stride": 3,
       "fit_iters": 0, "lineage_base": 100}


def _mk(cfg=None):
    return DynPortBuffer(dict(CFG, **(cfg or {})), FakeMap())


# ── ① config 三件套 / default-off ────────────────────────────────────────────

def test_default_off_when_absent():
    assert dynport_enabled({}) is False
    assert dynport_enabled({"DynPort": {}}) is False
    assert dynport_enabled({"DynPort": {"enabled": False}}) is False
    assert dynport_enabled({"DynPort": {"enabled": True}}) is True
    assert get_dynport_config({"DynPort": {"lam_d": 0.05}}) == {"lam_d": 0.05}


def test_cfg_fills_locked_defaults():
    c = dynport_cfg({"DynPort": {"enabled": True}})
    assert c["lam_d"] == 0.05 and c["cap"] == 50000 and c["lmax"] == 45
    assert c["unproj_stride"] == 3 and c["fit_iters"] == 300
    assert dynport_cfg({"DynPort": {"cap": 100}})["cap"] == 100


# ── ⑤ 空帧：不崩、计数不变 ───────────────────────────────────────────────────

def test_empty_frame_is_noop():
    buf = _mk()
    rec = buf.step(0, np.empty((0, 3)), np.empty((0, 3)), dbar=1.0)
    assert rec["inserted"] == 0 and buf.n == 0
    assert buf.case1_hits == 0 and buf.case2_new == 0


# ── ② Case2 新建 → Case1 复用（均值替换）────────────────────────────────────

def test_case2_then_case1_reuse_moves_mean():
    buf = _mk()
    pts = np.array([[0.0, 0, 1], [0.1, 0, 1], [0.2, 0, 1]], dtype=np.float32)
    cols = np.ones((3, 3), dtype=np.float32) * 0.5
    buf.step(0, pts, cols, dbar=1.0)
    assert buf.case2_new == 3 and buf.n == 3 and buf.case1_hits == 0
    pts2 = pts + 0.01                        # 近邻（< lam_d*dbar=0.05m）⇒ 全命中
    buf.step(1, pts2, cols, dbar=1.0)
    assert buf.case1_hits == 3, "近邻应命中 Case1"
    assert buf.case2_new == 3, "命中者不应新建"
    assert buf.n == 3, "复用不增基元"
    got = buf.map.world_points(buf.map.dyn_indices(buf.active_lineages()))
    assert np.allclose(got, pts2, atol=1e-5), "均值应被替换为当前观测点"


# ── ③ Cond2 寿命删除 ────────────────────────────────────────────────────────

def test_cond2_longevity_delete():
    buf = _mk({"lmax": 2})
    pts = np.array([[0.0, 0, 1], [5.0, 0, 1]], dtype=np.float32)  # 第二个远，防 Cond1 误删
    cols = np.ones((2, 3), dtype=np.float32) * 0.5
    buf.step(0, pts, cols, dbar=1.0)
    assert buf.n == 2
    buf.step(3, pts, cols, dbar=1.0)         # 帧 3：> lmax=2 ⇒ 首帧 lineage 过期
    assert buf.cond2_deleted >= 2, "超寿命基元应被 Cond2 删除"


# ── Cond1 可观测删除 ────────────────────────────────────────────────────────

def test_cond1_observability_delete():
    buf = _mk()
    a = np.array([[0.0, 0, 1], [10.0, 0, 1]], dtype=np.float32)
    cols = np.ones((2, 3), dtype=np.float32) * 0.5
    buf.step(0, a, cols, dbar=1.0)
    assert buf.n == 2
    b = np.array([[0.01, 0, 1]], dtype=np.float32)   # 只观测 a[0] 附近
    buf.step(1, b, np.ones((1, 3), dtype=np.float32) * 0.5, dbar=1.0)
    assert buf.cond1_deleted >= 1, "无观测近邻的旧基元应被 Cond1 删除"
    assert buf.n == 1, "删掉 10m 外的那个后应只剩 1"


# ── cap 驱逐（FIFO）─────────────────────────────────────────────────────────

def test_cap_evicts_fifo():
    """cap 驱逐：直接建 5 个 lineage（各 1 基元）再驱逐，验 FIFO 保新 + 封顶。"""
    buf = _mk({"cap": 3, "lmax": 100000})
    for j in range(5):
        buf.map.insert(np.array([[float(j), 0, 1]], np.float32),
                       np.ones((1, 3), np.float32), buf._issue(j))
    assert buf.n == 5
    buf._evict_to_cap()
    assert buf.n <= 3, "cap 应封顶"
    assert buf.cap_hits == 1, "应记录一次 cap 触顶"
    kept_x = buf.map.world_points(buf.map.dyn_indices(buf.active_lineages()))[:, 0]
    assert kept_x.min() >= 2.0 - 1e-6, f"FIFO 应保留最新基元，实得 x={kept_x}"


# ── J5：vitality 暴露五计数 ─────────────────────────────────────────────────

def test_vitality_exposes_counters():
    buf = _mk()
    pts = np.array([[0.0, 0, 1]], dtype=np.float32)
    buf.step(0, pts, np.ones((1, 3), dtype=np.float32) * 0.5, dbar=1.0)
    v = buf.vitality()
    for k in ("case1_hits", "case2_new", "cond1_deleted", "cond2_deleted",
              "evicted_total", "cap_hits", "buf_final"):
        assert k in v
    assert v["case2_new"] == 1 and v["buf_final"] == 1


def test_counters_csv_roundtrip(tmp_path):
    from utils.dyn_port_buffer import write_counters_csv
    buf = _mk()
    buf.step(0, np.array([[0.0, 0, 1]], dtype=np.float32),
             np.ones((1, 3), dtype=np.float32) * 0.5, dbar=1.0)
    p = tmp_path / "counters.csv"
    write_counters_csv(buf, str(p))
    text = p.read_text()
    assert "frame,inserted,case1_hits,n_buf,cond1_deleted,cond2_deleted,cap_hits" in text
    assert len(text.strip().splitlines()) == 2   # header + 1 行
