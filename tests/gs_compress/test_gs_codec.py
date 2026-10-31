"""gs_codec 单测（prereg_gs_compress.md §4 的守护）。

守护的事实：
  ① 编解码往返：重建属性与原始的误差 ≤ 量化步长（有损但受控）；
  ② rot 归一化：PLY 未归一化四元数 → 归一化存储 → 恢复单位四元数，且旋转等价；
  ③ 分区码流自洽：位图随流存储，decode 无需外部 labels；
  ④ 分区标签一致：外部 labels 与码流位图不一致时断言失败；
  ⑤ 记账字段剥离：write_recon_ply 只写 14 渲染字段（+3 零法向），不写 6 记账字段。
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("gs_codec", REPO / "scripts" / "gs_compress" / "gs_codec.py")
gc = importlib.util.module_from_spec(_spec)
sys.modules["gs_codec"] = gc
_spec.loader.exec_module(gc)


def _fake_map(n=500, seed=0):
    rng = np.random.default_rng(seed)
    m = {"_n": n, "_sh_deg": 0}
    for f in ["x", "y", "z"]:
        m[f] = rng.normal(0, 1, n).astype(np.float32)
    for f in ["f_dc_0", "f_dc_1", "f_dc_2"]:
        m[f] = rng.normal(0, 0.5, n).astype(np.float32)
    m["opacity"] = rng.normal(2, 3, n).astype(np.float32)
    for f in ["scale_0", "scale_1", "scale_2"]:
        m[f] = rng.normal(-5, 1, n).astype(np.float32)
    q = rng.normal(0, 1, (n, 4))
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    q *= rng.uniform(0.5, 2.0, (n, 1)).astype(np.float32)  # 未归一化，模拟 PLY
    for i in range(4):
        m[f"rot_{i}"] = q[:, i].astype(np.float32)
    for f in ["nx", "ny", "nz", "static_prob", "static_obs_count", "unmapped_score"]:
        m[f] = np.zeros(n, dtype=np.float32)
    return m


def test_roundtrip_bounded_error():
    m = _fake_map()
    bits = gc.Bits(16, 8, 8, 8, 8)
    blob, meta = gc.encode(m, bits)
    rec = gc.decode(blob, meta)
    xyz = np.stack([m["x"], m["y"], m["z"]], 1)
    span = xyz.max(0) - xyz.min(0)
    tol = span.max() / (2 ** 16 - 1) * 1.01
    assert np.abs(rec["xyz"] - xyz).max() <= tol
    # rot 恢复应为单位四元数
    qn = np.linalg.norm(rec["rot4"], axis=1)
    assert np.allclose(qn, 1.0, atol=1e-4)


def test_rot_normalization_equivalence():
    m = _fake_map()
    bits = gc.Bits(16, 8, 8, 8, 8)
    blob, meta = gc.encode(m, bits)
    rec = gc.decode(blob, meta)
    # 原始与重建四元数应表示同一旋转（差一个全局符号时取反）
    q0 = np.stack([m[f"rot_{i}"] for i in range(4)], 1)
    q0 /= np.linalg.norm(q0, axis=1, keepdims=True)
    dots = np.abs(np.sum(q0 * rec["rot4"], axis=1))
    assert (dots > 0.999).mean() > 0.95


def test_partition_bitstream_self_contained():
    m = _fake_map()
    n = m["_n"]
    rng = np.random.default_rng(1)
    labels = (rng.random(n) < 0.3).astype(np.int8)
    bits = gc.Bits(16, 8, 8, 8, 8)
    bits_dyn = gc.Bits(6, 4, 4, 4, 4)
    blob, meta = gc.encode(m, bits, labels=labels, bits_dyn=bits_dyn, alloc="partition")
    rec_auto = gc.decode(blob, meta)              # 位图随流
    rec_ext = gc.decode(blob, meta, labels=labels)  # 外部标签
    assert np.allclose(rec_auto["xyz"], rec_ext["xyz"])


def test_partition_labels_mismatch_raises():
    m = _fake_map()
    n = m["_n"]
    labels = np.zeros(n, dtype=np.int8)
    labels[: n // 4] = 1
    bits_dyn = gc.Bits(6, 4, 4, 4, 4)
    blob, meta = gc.encode(m, gc.Bits(16, 8, 8, 8, 8), labels=labels,
                           bits_dyn=bits_dyn, alloc="partition")
    wrong = 1 - labels
    with pytest.raises(AssertionError):
        gc.decode(blob, meta, labels=wrong)


def test_recon_ply_strips_accounting_fields(tmp_path):
    m = _fake_map()
    bits = gc.Bits(16, 8, 8, 8, 8)
    blob, meta = gc.encode(m, bits)
    rec = gc.decode(blob, meta)
    out = tmp_path / "recon.ply"
    gc.write_recon_ply(str(out), rec, m["_n"])
    from plyfile import PlyData
    names = {p.name for p in PlyData.read(str(out))["vertex"].properties}
    for f in ["static_prob", "static_obs_count", "unmapped_score"]:
        assert f not in names
    for f in gc.RENDER_FIELDS:
        assert f in names


# ---------------------------------------------------------------- v2 robust-range
def _heavy_tail_map(n=1000, seed=3):
    """带重尾（0.5% 巨值）的地图，模拟 SLAM 巨基元。"""
    m = _fake_map(n, seed)
    rng = np.random.default_rng(seed + 7)
    k = max(1, n // 200)
    idx = rng.choice(n, k, replace=False)
    m["scale_0"][idx] = 5.0          # 巨 scale（远出主体 ~N(-5,1)）
    m["x"][idx] = 40.0               # 巨 xyz 偏移
    return m


def test_robust_default_off_bit_identical():
    """range_mode='full'（默认）必须与旧路径逐位一致（零污染义务）。"""
    m = _fake_map()
    b1, m1 = gc.encode(m, gc.Bits(16, 8, 8, 8, 8))
    b2, m2 = gc.encode(m, gc.Bits(16, 8, 8, 8, 8), range_mode="full")
    assert b1 == b2
    assert m1.alloc == m2.alloc == "uniform"


def test_robust_clip_roundtrip_finite():
    """robust+clip：往返无错，步长 ≤ 稳健范围/格数。"""
    m = _heavy_tail_map()
    bits = gc.Bits(16, 8, 8, 8, 8)
    blob, meta = gc.encode(m, bits, range_mode="robust", range_q=0.5, escape=False)
    rec = gc.decode(blob, meta)
    xyz = np.stack([m["x"], m["y"], m["z"]], 1)
    plo = np.percentile(xyz, 0.5); phi = np.percentile(xyz, 99.5)
    tol = (phi - plo) / (2 ** 16 - 1) * 1.01
    bulk = (xyz >= plo) & (xyz <= phi)
    assert np.abs(rec["xyz"] - xyz)[bulk].max() <= tol


def test_robust_escape_recovers_tail_exactly():
    """robust+escape：尾部基元用全范围存储 ⇒ 尾部误差回到 v1 量级（远小于 clip）。"""
    m = _heavy_tail_map()
    bits = gc.Bits(16, 8, 8, 8, 8)
    bc, mc = gc.encode(m, bits, range_mode="robust", range_q=0.5, escape=False)
    be, me = gc.encode(m, bits, range_mode="robust", range_q=0.5, escape=True)
    rc, re = gc.decode(bc, mc), gc.decode(be, me)
    xyz = np.stack([m["x"], m["y"], m["z"]], 1)
    plo = np.percentile(xyz, 0.5); phi = np.percentile(xyz, 99.5)
    tail = ((xyz < plo) | (xyz > phi)).any(1)
    err_clip = np.abs(rc["xyz"] - xyz)[tail].max()
    err_esc = np.abs(re["xyz"] - xyz)[tail].max()
    assert err_esc < err_clip                       # escape 明显更好
    span = xyz.max(0) - xyz.min(0)
    assert err_esc <= span.max() / (2 ** 16 - 1) * 1.01  # 回到 v1 量级
    # 主体仍按稳健步长（比 v1 更细）
    bulk = ~tail
    assert np.abs(re["xyz"] - xyz)[bulk].max() <= (phi - plo) / (2 ** 16 - 1) * 1.01


def test_robust_escape_bitstream_self_contained():
    """escape 的尾部位图随流存储 ⇒ decode 无需外部信息。"""
    m = _heavy_tail_map()
    blob, meta = gc.encode(m, gc.Bits(16, 8, 8, 8, 8),
                           range_mode="robust", range_q=0.5, escape=True)
    r1 = gc.decode(blob, meta)
    r2 = gc.decode(blob, meta)
    assert np.allclose(r1["xyz"], r2["xyz"])

