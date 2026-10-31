#!/usr/bin/env python
"""probe_temporal_interp.py — B2 时间一致性探针（L1 最小验证，事后插值）。

**目的**：验证"对评估帧 e 用时间插值层（而非最近 ≤e 快照）渲染"在 samepose 判据
口径下是否有真实增益（J1 动态区提升 / J3 静态区不破）。**不碰生产 repair_map.py**，
只在已有 L1_v4 快照上做 post-hoc 插值。

**背景**（2026-10-12 核实）：评估帧 = `Evaluating ATE at frame`（crowd2 为 stride 25，
35 帧，全部不在 KF 快照 stride 5 上）；判据机 samepose = 静态底图 + "最近 ≤e 快照"
动态层 + 帧 e 最终轨迹位姿。⇒ 中间帧动态层停留在上一个 KF 的位置（时间错位），
这是现有修复的隐藏瓶颈假设。

**插值方案**（无 lineage 追踪的轻量版）：
  对 e ∈ (KF_a, KF_b)：
    1. KF_a 基元在 KF_b 中最近邻匹配（KDTree）→ 对应基元对
    2. α = (e-a)/(b-a)；位置/尺度/颜色线性插值，旋转 slerp（朴素四元数 slerp）
    3. 未匹配基元：保留 KF_a 原值（保守，不引入虚构基元）
  输出：`frame_<e>.npz`（判据机 `frame_*.npz` 同款格式）。

**用法**：
  python scripts/dynport_offline/probe_temporal_interp.py \
      --snap-root results/dynport_offline/L1_v4/crowd2_R1 \
      --base-run results/paper2_fulltable/r33_rebase_baseline_crowd2_seed0/datasets_bonn/r33_rebase_baseline_crowd2/seed_0/2026-09-16-06-54-45 \
      --out /tmp/probe_ti_crowd2 --device cuda:0
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def load_snap(path):
    d = np.load(path)
    return {k: d[k] for k in ("xyz", "log_scale", "rot", "opa", "f_dc")}


def slerp(q0, q1, t):
    """朴素四元数 slerp（numpy，逐行）。q0/q1: (N,4) 单位化后。"""
    q0 = q0 / np.maximum(np.linalg.norm(q0, axis=1, keepdims=True), 1e-12)
    q1 = q1 / np.maximum(np.linalg.norm(q1, axis=1, keepdims=True), 1e-12)
    dot = np.sum(q0 * q1, axis=1)
    flip = dot < 0
    q1 = q1.copy()
    q1[flip] = -q1[flip]
    dot[flip] = -dot[flip]
    dot = np.clip(dot, -1, 1)
    theta = np.arccos(dot)
    sin_t = np.sin(theta)
    # 近平行：线性插值
    safe = sin_t < 1e-6
    out = np.empty_like(q0)
    out[safe] = q0[safe] * (1 - t) + q1[safe] * t
    ns = ~safe
    if ns.any():
        w0 = np.sin((1 - t) * theta[ns]) / sin_t[ns]
        w1 = np.sin(t * theta[ns]) / sin_t[ns]
        out[ns] = w0[:, None] * q0[ns] + w1[:, None] * q1[ns]
    return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-12)


def interpolate(snap_a, snap_b, alpha):
    """KF_a/KF_b 两层间插值。返回同构 dict。

    匹配：KF_a 每基元 → KF_b 最近邻（KDTree）。未匹配基元保留 KF_a 原值。
    """
    from scipy.spatial import cKDTree
    xa, xb = snap_a["xyz"].astype(np.float64), snap_b["xyz"].astype(np.float64)
    tree = cKDTree(xb)
    dd, ii = tree.query(xa, k=1)
    matched = dd < 0.10  # 10cm 匹配阈值（动态物体逐 KF 位移量级）
    out = {}
    for k in ("xyz", "log_scale", "opa", "f_dc"):
        a = snap_a[k].astype(np.float64)
        if matched.any():
            b = snap_b[k][ii[matched]].astype(np.float64)
            av = a[matched] * (1 - alpha) + b * alpha
        else:
            av = a[matched]
        o = a.copy()
        o[matched] = av
        out[k] = o.astype(np.float32)
    # 旋转 slerp
    ra = snap_a["rot"].astype(np.float64)
    rb = snap_b["rot"][ii[matched]].astype(np.float64) if matched.any() else ra[:0]
    ro = ra.copy()
    if matched.any():
        ro[matched] = slerp(ra[matched], rb, alpha)
    out["rot"] = ro.astype(np.float32)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap-root", required=True, help="现有 R1 算子输出（含 dynport_causal/）")
    ap.add_argument("--base-run", required=True, help="底图 run 目录（取评估帧集）")
    ap.add_argument("--out", required=True, help="探针输出目录（含 dynport_causal/）")
    ap.add_argument("--seq", default="crowd2")
    ap.add_argument("--match-thr", type=float, default=0.10)
    args = ap.parse_args()

    snap_root = Path(args.snap_root)
    cdir = snap_root / "dynport_causal"
    snaps = sorted(cdir.glob("frame_*.npz"))
    snap_ids = [int(p.stem.split("_")[1]) for p in snaps]
    if not snaps:
        raise SystemExit(f"无快照: {cdir}")
    print(f"[probe] 源快照 {len(snaps)} 个（{snap_ids[0]}..{snap_ids[-1]}）")

    # 评估帧集（derive_eval_frames 同源）
    console = Path(args.base_run) / "console.log"
    txt = console.read_text(errors="ignore")
    eval_ids = sorted(set(int(m) for m in re.findall(r"Evaluating ATE at frame:\s*(\d+)", txt)))
    print(f"[probe] 评估帧 {len(eval_ids)} 个: {eval_ids[:5]}..{eval_ids[-3:]}")

    out_cdir = Path(args.out) / "dynport_causal"
    out_cdir.mkdir(parents=True, exist_ok=True)

    # 1) 原 KF 快照直接复制（判据机"最近 ≤e"兜底）
    import shutil
    n_copied = 0
    for p in snaps:
        shutil.copy2(p, out_cdir / p.name)
        n_copied += 1

    # 2) 对每个评估帧插值
    n_written = 0
    stats = {"matched_mean": [], "unmatched_mean": [], "n_eval": len(eval_ids)}
    for e in eval_ids:
        # 严格因果：前后 KF
        a = max((i for i, fid in enumerate(snap_ids) if fid <= e), default=None)
        b = min((i for i, fid in enumerate(snap_ids) if fid > e), default=None)
        if a is None:
            continue  # e < 首个 KF：无前驱，跳过（判据机用首个 KF 快照）
        if b is None:
            continue  # e >= 末 KF：无后继，跳过（保守）
        fa, fb = snap_ids[a], snap_ids[b]
        alpha = (e - fa) / (fb - fa)
        sa, sb = load_snap(snaps[a]), load_snap(snaps[b])
        interp = interpolate(sa, sb, alpha)
        # 匹配统计
        from scipy.spatial import cKDTree
        xa = sa["xyz"].astype(np.float64)
        dd, _ = cKDTree(sb["xyz"].astype(np.float64)).query(xa, k=1)
        m = dd < args.match_thr
        stats["matched_mean"].append(float(m.mean()))
        stats["unmatched_mean"].append(float((~m).mean()))
        c2w = np.eye(4)  # 判据机 samepose 不用快照位姿（用帧 e 位姿），占位即可
        np.savez(out_cdir / f"frame_{int(e):06d}.npz",
                 frame_idx=np.int64(e), c2w=c2w.astype(np.float64),
                 xyz=interp["xyz"], log_scale=interp["log_scale"],
                 rot=interp["rot"], opa=interp["opa"], f_dc=interp["f_dc"])
        n_written += 1

    print(f"[probe] 复制 {n_copied} KF 快照 + 写 {n_written} 插值帧快照 → {out_cdir}")
    print(f"[probe] 匹配率 mean={np.mean(stats['matched_mean']):.3f} "
          f"unmatched={np.mean(stats['unmatched_mean']):.3f}")
    (Path(args.out) / "probe_meta.json").write_text(
        json.dumps({**stats, "match_thr": args.match_thr, "n_snap": len(snaps)}, indent=2))


if __name__ == "__main__":
    main()
