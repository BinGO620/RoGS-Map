#!/usr/bin/env python
"""probe_4d_decode.py — 4D 层序列压缩解码器（排除被抑制基元 + 绝对量化）。

**机制**（probe_4d_compress_2026-10-12.md 定稿）：
  动态层 4D 快照序列中 35.9% 基元是 opa=−30 的"被抑制"基元（S5 投影掩码剪枝
  产物，sigmoid 后不可见），撑爆量化范围。编码/解码时**先排除被抑制基元
  （1 bit/基元 标记），只对可见基元做绝对量化 + zlib**。

**工作点**（crowd2_R1，判据机 samepose）：
  - 10bit（近无损）：3.78×，J1 7.91 ≈ 原始 7.95
  - 8bit（中）：6.85×，J1 6.86、J3 −0.08
  - 6bit 破线（J3 −1.20），不可用

**用法**：
  python scripts/dynport_offline/probe_4d_decode.py \
      --snap-root results/dynport_offline/L1_v4/crowd2_R1 \
      --out /tmp/probe_4d_supp_b8 --bits 8
  输出解码快照 → 判据机 samepose 验证。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

_ATTRS = ["xyz", "log_scale", "rot", "opa", "f_dc"]
SUPPRESSED_OPA = -10.0  # opa 低于此值视为被抑制（sigmoid 后不可见）


def quantize(v, bits, lo, hi):
    level = (1 << bits) - 1
    span = max(hi - lo, 1e-9)
    return np.round(np.clip((v - lo) / span, 0, 1) * level).astype(np.uint16)


def unquantize(q, bits, lo, hi):
    level = (1 << bits) - 1
    span = max(hi - lo, 1e-9)
    return (q.astype(np.float64) / level) * span + lo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap-root", required=True, help="现有 R1 算子输出（含 dynport_causal/）")
    ap.add_argument("--out", required=True, help="解码输出目录")
    ap.add_argument("--bits", type=int, default=8)
    ap.add_argument("--opa-thr", type=float, default=SUPPRESSED_OPA)
    args = ap.parse_args()

    cdir = Path(args.snap_root) / "dynport_causal"
    snaps = sorted(cdir.glob("frame_*.npz"))
    if not snaps:
        raise SystemExit(f"无快照: {cdir}")

    out_cdir = Path(args.out) / "dynport_causal"
    out_cdir.mkdir(parents=True, exist_ok=True)
    # 复制 run 结构（config/trj/PLY/dynamic_rows）
    for sub in ("config.yml", "point_cloud", "plot"):
        src = Path(args.snap_root) / sub
        if src.exists():
            dst = Path(args.out) / sub
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
    shutil.copy2(cdir / "dynamic_rows.npy", out_cdir / "dynamic_rows.npy")

    n_suppressed, n_visible = 0, 0
    for p in snaps:
        d = np.load(p)
        snap = {k: d[k] for k in _ATTRS}
        dec = {k: snap[k].copy() for k in _ATTRS}
        opa = snap["opa"].reshape(-1)
        alive = opa > args.opa_thr
        n_suppressed += int((~alive).sum())
        n_visible += int(alive.sum())
        if alive.sum():
            for attr in _ATTRS:
                v = snap[attr][alive].astype(np.float64)
                lo, hi = np.percentile(v, [1, 99])
                q = quantize(v, args.bits, lo, hi)
                dec[attr][alive] = unquantize(q, args.bits, lo, hi).astype(np.float32)
        np.savez(out_cdir / Path(p).name, frame_idx=d["frame_idx"], c2w=d["c2w"], **dec)

    print(f"[probe4d-decode] {len(snaps)} 快照 → {out_cdir}（bits={args.bits}，"
          f"抑制 {n_suppressed} / 可见 {n_visible}，抑制占比 {n_suppressed/(n_suppressed+n_visible)*100:.1f}%）")


if __name__ == "__main__":
    main()
