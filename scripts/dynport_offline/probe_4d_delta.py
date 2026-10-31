#!/usr/bin/env python
"""probe_4d_delta.py — 4D 层序列压缩探针（L1 最小验证，数据级）。

**目标**：验证"时间维 delta 编码"对修复算子 4D 快照序列的压缩潜力。
对照 = 逐帧独立量化+zlib（baseline，~1.14×）。

**方法**（复用 §5 codec 的量化思想，新增时间维）：
  逐对相邻 KF 快照 (KF_a, KF_b)：
    1. KF_a 基元在 KF_b 最近邻匹配（≤5cm）→ 持续基元（~77%）
    2. 持续基元：只编码残差 (KF_b − KF_a)，均匀量化（位宽可调）→ 残差熵低
    3. 新出生基元：全量绝对参数量化
    4. 消失基元：KF_a 记末帧
  输出：压缩字节 vs 原始字节 → 压缩比（含/不含量化后 zlib 两级）

**用法**：
  python scripts/dynport_offline/probe_4d_delta.py \
      --snap-root results/dynport_offline/L1_v4/crowd2_R1
"""
from __future__ import annotations

import argparse
import glob
import re
import sys
import zlib
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

_ATTRS = ["xyz", "log_scale", "rot", "opa", "f_dc"]


def quantize(v, bits, lo, hi):
    """均匀量化到 [lo,hi] → uint 编码。返回 (q_int, level)。"""
    level = (1 << bits) - 1
    q = np.clip((v - lo) / (hi - lo), 0, 1)
    return np.round(q * level).astype(np.uint16), level


def unquantize(q, bits, lo, hi):
    level = (1 << bits) - 1
    return (q.astype(np.float64) / level) * (hi - lo) + lo


def delta_encode_pair(snap_a, snap_b, match_thr=0.05, bits=8):
    """对相邻两帧做时间 delta 编码。返回 (bytes_len, n_persist, n_birth, n_death)。"""
    xa, xb = snap_a["xyz"].astype(np.float64), snap_b["xyz"].astype(np.float64)
    if len(xa) == 0 or len(xb) == 0:
        return b"", 0, 0, 0
    # 匹配：KF_a 每基元 → KF_b 最近邻
    dd, ii = cKDTree(xb).query(xa, k=1)
    matched = dd < match_thr
    n_persist = int(matched.sum())
    n_death = int((~matched).sum())  # KF_a 有、KF_b 无
    n_birth = int(len(xb) - n_persist)  # KF_b 有、KF_a 无

    # 持续基元：残差编码（KF_b[ii[m]] - KF_a[m]）
    raw = bytearray()
    if n_persist > 0:
        mi = np.nonzero(matched)[0]
        for attr in _ATTRS:
            va = snap_a[attr].astype(np.float64)[mi]
            vb = snap_b[attr][ii[mi]].astype(np.float64)
            resid = vb - va
            lo, hi = np.percentile(resid, [1, 99])
            span = max(hi - lo, 1e-9)
            # 残差量化（bit 宽）+ 每属性组存 (lo,hi) header（2×f32，可忽略）
            q, _ = quantize(resid, bits, lo, hi)
            raw += q.astype(np.uint8).tobytes() if bits <= 8 else q.tobytes()
    # 新出生：绝对参数全量
    if n_birth > 0:
        # 找 KF_b 未匹配基元
        matched_b = np.zeros(len(xb), bool)
        matched_b[ii[matched]] = True
        birth_idx = np.nonzero(~matched_b)[0]
        for attr in _ATTRS:
            vb = snap_b[attr].astype(np.float64)[birth_idx]
            lo, hi = np.percentile(vb, [1, 99])
            span = max(hi - lo, 1e-9)
            q, _ = quantize(vb, bits, lo, hi)
            raw += q.astype(np.uint8).tobytes() if bits <= 8 else q.tobytes()
    return bytes(raw), n_persist, n_birth, n_death


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap-root", required=True)
    ap.add_argument("--match-thr", type=float, default=0.05)
    ap.add_argument("--bits", type=int, default=8)
    args = ap.parse_args()

    cdir = Path(args.snap_root) / "dynport_causal"
    snaps = sorted(cdir.glob("frame_*.npz"))
    if not snaps:
        raise SystemExit(f"无快照: {cdir}")
    print(f"[probe4d] 快照 {len(snaps)} 个")

    # baseline：逐帧原始 + 逐帧独立 zlib
    total_raw, total_zip = 0, 0
    for s in snaps:
        d = np.load(s)
        raw = b"".join(d[a].tobytes() for a in _ATTRS)
        total_raw += len(raw)
        total_zip += len(zlib.compress(raw, 6))
    print(f"[probe4d] 逐帧独立: raw={total_raw/1e6:.2f}MB zlib={total_zip/1e6:.2f}MB ratio={total_raw/total_zip:.2f}x")

    # delta 编码（成对）+ 真实 zlib（量化后残差多聚集 0 附近，应有额外增益）
    total_delta, total_delta_zip = 0, 0
    n_p, n_b, n_d = 0, 0, 0
    for i in range(len(snaps) - 1):
        a, b = np.load(snaps[i]), np.load(snaps[i + 1])
        bbytes, np_, nb, nd = delta_encode_pair(a, b, args.match_thr, args.bits)
        total_delta += len(bbytes)
        total_delta_zip += len(zlib.compress(bbytes, 6)) if bbytes else 0
        n_p += np_; n_b += nb; n_d += nd
    print(f"[probe4d] delta编码(量化后): {total_delta/1e6:.2f}MB ratio={total_raw/total_delta:.2f}x")
    print(f"[probe4d] delta+zlib: {total_delta_zip/1e6:.2f}MB ratio={total_raw/total_delta_zip:.2f}x")
    print(f"[probe4d] 持续/新生/消失: {n_p}/{n_b}/{n_d} "
          f"({n_p/(n_p+n_b+n_d)*100:.1f}% / {n_b/(n_p+n_b+n_d)*100:.1f}% / {n_d/(n_p+n_b+n_d)*100:.1f}%)")
    print(f"[probe4d] delta vs 逐帧zlib: {total_zip/total_delta_zip:.2f}x 更小")
    # 位宽扫描
    for b in (4, 6, 8, 10, 12):
        td, tdz = 0, 0
        for i in range(len(snaps) - 1):
            a, b_ = np.load(snaps[i]), np.load(snaps[i + 1])
            bb, *_ = delta_encode_pair(a, b_, args.match_thr, b)
            td += len(bb)
            tdz += len(zlib.compress(bb, 6)) if bb else 0
        print(f"  bits={b:2d}: ratio={total_raw/td:.2f}x  +zlib={total_raw/tdz:.2f}x")


if __name__ == "__main__":
    main()
