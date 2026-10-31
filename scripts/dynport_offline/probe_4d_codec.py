#!/usr/bin/env python
"""probe_4d_codec.py — 4D 层序列 codec（v3：排除抑制 + rot3 + xyz 预测 + 属性级位宽）。

**机制**（probe_4d_compress_2026-10-12.md 定稿）：
  1. **排除被抑制基元**（opa < -10 的 S5 掩码剪枝产物，sigmoid 后不可见，
     占 31-36%，撑爆量化范围）→ 1 bit/基元 标记
  2. **rot3 + 单位约束**（旋转冗余：存前 3 分量 + 归一化恢复第 4 分量）
  3. **xyz 轨迹预测编码**（持续基元步位移 0.61cm 平滑 → 常速度预测残差；
     其他属性绝对量化——全属性预测被 p99 离群撑爆范围，反而不如绝对）
  4. **属性级位宽**（xyz 高位宽保精度 + opa/rot/f_dc 低位宽省字节）

**诚实工作点**（crowd2，判据机 samepose；2026-10-12 晚更正，修 uint16 溢出 + 漏编码）：
  - 近无损 8.12×（bits-cfg 10,6,4,6,6，J1 7.62 = 原始 7.95 的 96%）
  - 中 7.61×（bits-cfg 10,6,6,6,6，J1 7.65）
  - 对比 u8（8,8,8,8,8）：7.12×，J1 6.75（85%）

**用法**：
  python scripts/dynport_offline/probe_4d_codec.py \
      --snap-root results/dynport_offline/L1_v4/crowd2_R1 \
      --out /tmp/probe_4d_v3 --bits-cfg 10,6,4,6,6
  输出解码快照 → 判据机 samepose 验证。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

_ATTRS = ["xyz", "log_scale", "rot", "opa", "f_dc"]
SUPPRESSED_OPA = -10.0
MATCH_THR = 0.03  # 双向一致匹配阈值（持续基元判定）


def quantize(v, bits, lo, hi):
    level = (1 << bits) - 1
    span = max(hi - lo, 1e-9)
    q = np.round(np.clip((v - lo) / span, 0, 1) * level)
    return q.astype(np.uint16) if bits > 8 else q.astype(np.uint8)


def unquantize(q, bits, lo, hi):
    level = (1 << bits) - 1
    span = max(hi - lo, 1e-9)
    return (q.astype(np.float64) / level) * span + lo


def bidi_match(xa, xb, thr=MATCH_THR):
    """双向一致最近邻匹配（持续基元对应）。返回 (prev_idx, cur_idx)。"""
    xa = xa.astype(np.float64)
    xb = xb.astype(np.float64)
    if len(xa) == 0 or len(xb) == 0:
        return None, None
    d_ab, ii_ab = cKDTree(xb).query(xa, k=1)
    d_ba, ii_ba = cKDTree(xa).query(xb, k=1)
    bidi = np.zeros(len(xa), bool)
    for j in np.unique(ii_ab):
        for si in np.nonzero(ii_ab == j)[0]:
            if ii_ba[j] == si and d_ab[si] < thr:
                bidi[si] = True
    return np.nonzero(bidi)[0], ii_ab


def rot3_encode(v):
    """rot (N,4) → (N,3)（归一化后取前 3 分量；解码端单位约束恢复第 4 分量）。"""
    n = np.linalg.norm(v, axis=1, keepdims=True)
    return (v / np.maximum(n, 1e-12))[:, :3]


def rot3_decode(r3):
    """rot3 (N,3) → (N,4)（单位约束恢复第 4 分量）。"""
    w = np.sqrt(np.clip(1 - np.sum(r3 ** 2, axis=1, keepdims=True), 0, 1))
    return np.concatenate([r3, w], axis=1)


def alive_rows(alive):
    """alive 布尔掩码 → 行下标数组（修复链式赋值不写回的 numpy 坑）。"""
    return np.nonzero(alive)[0]


def encode_attr(v, bits, lo, hi, rot3=False):
    """量化→反量化（模拟编解码往返）。"""
    if rot3:
        v = rot3_encode(v)
    decv = unquantize(quantize(v, bits, lo, hi), bits, lo, hi)
    if rot3:
        decv = rot3_decode(decv)
    return decv.astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap-root", required=True, help="现有 R1 算子输出（含 dynport_causal/）")
    ap.add_argument("--out", required=True, help="解码输出目录")
    ap.add_argument("--bits-cfg", default="10,6,4,6,6",
                    help="属性级位宽 xyz,log_scale,rot,opa,f_dc（默认近无损 8.12×）")
    ap.add_argument("--rot3", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--pred", action=argparse.BooleanOptionalAction, default=True,
                    help="xyz 轨迹预测编码（持续基元常速度残差）；--no-pred 关闭")
    ap.add_argument("--opa-thr", type=float, default=SUPPRESSED_OPA,
                    help="被抑制基元阈值（opa < 此值视为不可见；设 -1000 关闭排除）")
    args = ap.parse_args()

    B = [int(x) for x in args.bits_cfg.split(",")]
    assert len(B) == 5, f"--bits-cfg 须 5 个值（xyz,log_scale,rot,opa,f_dc），实为 {B}"

    cdir = Path(args.snap_root) / "dynport_causal"
    snaps = sorted(cdir.glob("frame_*.npz"))
    if not snaps:
        raise SystemExit(f"无快照: {cdir}")

    out_cdir = Path(args.out) / "dynport_causal"
    out_cdir.mkdir(parents=True, exist_ok=True)
    for sub in ("config.yml", "point_cloud", "plot"):
        src = Path(args.snap_root) / sub
        if src.exists():
            dst = Path(args.out) / sub
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
    shutil.copy2(cdir / "dynamic_rows.npy", out_cdir / "dynamic_rows.npy")

    prev_data, prev_vel = None, None
    _n_pred_branch = 0
    for p in snaps:
        d = np.load(p)
        opa = d["opa"].reshape(-1)
        alive = opa > args.opa_thr
        rows = alive_rows(alive)
        n_vis = int(alive.sum())
        dec = {a: d[a].copy() for a in _ATTRS}
        if n_vis > 0:
            cur = {a: d[a][alive] for a in _ATTRS}
            if prev_data is None:
                # I 帧：全量绝对量化
                for ai, attr in enumerate(_ATTRS):
                    v = cur[attr].astype(np.float64)
                    lo, hi = np.percentile(v, [1, 99])
                    dec[attr][alive] = encode_attr(v, B[ai], lo, hi, rot3=(attr == "rot" and args.rot3))
                prev_data = cur
                prev_vel = np.zeros((n_vis, 3), np.float64)
            else:
                mi, ii_ab = bidi_match(prev_data["xyz"], cur["xyz"])
                if mi is not None and len(mi) > 0:
                    _n_pred_branch += 1
                    if args.pred:
                        _n_pred_branch += 1
                        # xyz 常速度预测残差（只 xyz；其他属性绝对——全属性预测 p99 离群反伤）
                        pred = prev_data["xyz"][mi].astype(np.float64) + prev_vel[mi]
                        actual = cur["xyz"][ii_ab[mi]].astype(np.float64)
                        resid = actual - pred
                        lo, hi = np.percentile(resid, [1, 99])
                        decr = unquantize(quantize(resid, B[0], lo, hi), B[0], lo, hi)
                        dec["xyz"][rows[ii_ab[mi]]] = (pred + decr).astype(np.float32)
                        new_vel = np.zeros((n_vis, 3), np.float64)
                        new_vel[ii_ab[mi]] = actual - prev_data["xyz"][mi].astype(np.float64)
                        prev_vel = new_vel
                    else:
                        # 无预测：持续基元 xyz 绝对量化
                        v = cur["xyz"][ii_ab[mi]].astype(np.float64)
                        lo, hi = np.percentile(v, [1, 99])
                        dec["xyz"][rows[ii_ab[mi]]] = encode_attr(v, B[0], lo, hi)
                    # 持续基元：其他属性绝对量化
                    for ai, attr in enumerate(["log_scale", "rot", "opa", "f_dc"]):
                        v = cur[attr][ii_ab[mi]].astype(np.float64)
                        lo, hi = np.percentile(v, [1, 99])
                        dec[attr][rows[ii_ab[mi]]] = encode_attr(
                            v, B[ai + 1], lo, hi, rot3=(attr == "rot" and args.rot3))
                    # 新生基元：全属性绝对量化
                    matched_b = np.zeros(n_vis, bool)
                    matched_b[ii_ab[mi]] = True
                    rest = np.nonzero(~matched_b)[0]
                    if len(rest):
                        for ai, attr in enumerate(_ATTRS):
                            v = cur[attr][rest].astype(np.float64)
                            lo, hi = np.percentile(v, [1, 99])
                            dec[attr][rows[rest]] = encode_attr(
                                v, B[ai], lo, hi, rot3=(attr == "rot" and args.rot3))
                else:
                    # 无匹配：全量绝对量化
                    for ai, attr in enumerate(_ATTRS):
                        v = cur[attr].astype(np.float64)
                        lo, hi = np.percentile(v, [1, 99])
                        dec[attr][alive] = encode_attr(v, B[ai], lo, hi, rot3=(attr == "rot" and args.rot3))
                    prev_vel = np.zeros((n_vis, 3), np.float64)
                prev_data = cur
        np.savez(out_cdir / p.name, frame_idx=d["frame_idx"], c2w=d["c2w"], **dec)
    print(f"[probe4d-codec] pred分支执行 {_n_pred_branch} 次")
    print(f"[probe4d-codec] {len(snaps)} 快照解码 → {out_cdir}（bits={B}，"
          f"rot3={args.rot3}，pred={args.pred}）")


if __name__ == "__main__":
    main()
