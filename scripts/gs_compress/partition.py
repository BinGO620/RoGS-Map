#!/usr/bin/env python
"""partition.py — 基元分区标签（自有点 A 的前置件）。

给定地图 PLY + 采样帧位姿 + 冻结动态掩码，把每个基元分为：
  * DYNAMIC_SUPPORT：投影落在"动态/残影区"内的基元（像素证据：动态掩码命中）
  * STATIC_SUPPORT ：只落在静态区的基元

方法（零 GPU、纯几何投票）：
  对每帧 f：把基元 xyz 用 W2C 投影到像素，采该帧 dynamic_mask。
  逐基元累计 hit_dyn / hit_static；赋标签。
**只用 GT 掩码 + 位姿（不用渲染、不用 GT 深度）**——掩码是评测仪器，不作贡献主张（五点裁定），
只作分配信号。

分区口径与 `utils/static_eval.py` 同源：M_dynamic = 动态掩码；其余为静态。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def load_trj(trj_path: str) -> dict:
    d = json.load(open(trj_path))
    ids = [int(v) for v in d["trj_id"]]
    est = [np.asarray(v, dtype=np.float64) for v in d["trj_est"]]  # C2W
    return {i: p for i, p in zip(ids, est)}


def label_primitives(
    xyz: np.ndarray,
    trj: dict,
    mask_paths: dict,          # frame_id -> bool(H,W) dynamic mask
    K: np.ndarray,             # 3x3 intrinsics
    W: int, H: int,
    frame_ids: list[int],
    dyn_ratio_thresh: float = 0.05,
    occl_tol_m: float = 0.05,
    depth_paths: list[str] | None = None,
    depth_scale: float = 5000.0,
    map1x=None, map1y=None,
) -> dict:
    """GT 深度可见性门控的投票分类（推荐路径）。

    对每帧：把 GT 深度去畸变到渲染像素空间，做 z-buffer；基元仅在
    **它确实是该像素最前**（|z − z_gt| ≤ tol，或比 z_gt 更前）时投票。
    ⇒ 被动态物体**遮挡的背景基元不投票**（旧版的误标根因）。
    若 depth_paths 缺失 ⇒ 回退到基元自建 z-buffer（退化路径，登记）。
    """
    n = xyz.shape[0]
    hit_dyn = np.zeros(n, dtype=np.int32)
    hit_vis = np.zeros(n, dtype=np.int32)
    use_gt = depth_paths is not None

    pts_h = np.concatenate([xyz.astype(np.float64), np.ones((n, 1))], axis=1)  # (N,4)
    for fid in frame_ids:
        c2w = trj.get(fid)
        if c2w is None:
            continue
        mask = mask_paths.get(fid)
        if mask is None:
            continue
        w2c = np.linalg.inv(c2w)
        cam = (w2c @ pts_h.T).T
        z = cam[:, 2]
        valid = z > 1e-3
        zi = np.where(valid, z, 1.0)
        u = K[0, 0] * cam[:, 0] / zi + K[0, 2]
        v = K[1, 1] * cam[:, 1] / zi + K[1, 2]
        ui = np.round(u).astype(np.int64)
        vi = np.round(v).astype(np.int64)
        inb = valid & (ui >= 0) & (ui < W) & (vi >= 0) & (vi < H)
        idx = np.where(inb)[0]
        if idx.size == 0:
            continue

        if use_gt and fid < len(depth_paths):
            z_gt = _load_gt_depth_m(depth_paths[fid], depth_scale, map1x, map1y)
            if z_gt is None:
                continue
            zg = z_gt[vi[idx], ui[idx]]
            ok = np.isfinite(zg) & (zg > 1e-3)
            vis = z[idx] <= zg + occl_tol_m
            vidx = idx[ok & vis]
        else:
            pix = vi[idx] * W + ui[idx]
            zbuf = np.full(W * H, np.inf)
            np.minimum.at(zbuf, pix, z[idx])
            vidx = idx[z[idx] <= zbuf[pix] + occl_tol_m]

        hit_vis[vidx] += 1
        dm = mask[vi[vidx], ui[vidx]]
        hit_dyn[vidx] += dm.astype(np.int32)

    ratio = np.where(hit_vis > 0, hit_dyn / np.maximum(1, hit_vis), 0.0)
    labels = (ratio >= dyn_ratio_thresh).astype(np.int8)
    return {"labels": labels, "hit_dyn": hit_dyn, "hit_vis": hit_vis,
            "hit_tot": hit_vis, "dyn_ratio": ratio, "used_gt_depth": use_gt}


def _load_gt_depth_m(path: str, scale: float, map1x, map1y) -> np.ndarray | None:
    import cv2
    from PIL import Image
    a = np.asarray(Image.open(path))
    d = a.astype(np.float32) / float(scale)
    if map1x is not None and map1y is not None:
        d = cv2.remap(d, map1x, map1y, cv2.INTER_NEAREST)
    return d


def compute_visibility_counts(
    xyz: np.ndarray,
    trj: dict,
    K: np.ndarray,
    W: int, H: int,
    frame_ids: list[int],
    depth_paths: list[str] | None = None,
    depth_scale: float = 5000.0,
    map1x=None, map1y=None,
    occl_tol_m: float = 0.05,
) -> dict:
    """逐基元可见性计数（**保守**：只在有有效 GT 深度证据时判"可见"或"不可见"）。

    返回 hit_fov（投影入界 + z>0）、hit_vis（GT 深度门控可见）、hit_evidence
    （FOV 内且该像素有有效 GT 深度 = 有判据）、hit_hole（FOV 内但深度空洞）。
    **"从不可见"的稳健定义 = hit_evidence>0 ∧ hit_vis==0**（有判据且从没通过）
    —— 排除深度空洞导致的假阴性（本仓 crowd2 实测：空洞贡献了 87% 的假"不可见"）。
    """
    n = xyz.shape[0]
    hit_fov = np.zeros(n, np.int32)
    hit_vis = np.zeros(n, np.int32)
    hit_evidence = np.zeros(n, np.int32)
    hit_hole = np.zeros(n, np.int32)
    pts = np.concatenate([xyz.astype(np.float64), np.ones((n, 1))], 1)
    for fid in frame_ids:
        c2w = trj.get(fid)
        if c2w is None:
            continue
        w2c = np.linalg.inv(c2w)
        cam = (w2c @ pts.T).T
        z = cam[:, 2]
        zi = np.where(z > 1e-3, z, 1.0)
        u = K[0, 0] * cam[:, 0] / zi + K[0, 2]
        v = K[1, 1] * cam[:, 1] / zi + K[1, 2]
        ui = np.round(u).astype(np.int64)
        vi = np.round(v).astype(np.int64)
        inb = (z > 1e-3) & (ui >= 0) & (ui < W) & (vi >= 0) & (vi < H)
        idx = np.where(inb)[0]
        hit_fov[idx] += 1
        if depth_paths is None or fid >= len(depth_paths):
            continue
        z_gt = _load_gt_depth_m(depth_paths[fid], depth_scale, map1x, map1y)
        if z_gt is None:
            continue
        zg = z_gt[vi[idx], ui[idx]]
        good = np.isfinite(zg) & (zg > 1e-3)
        hit_evidence[idx[good]] += 1
        hit_hole[idx[~good]] += 1
        gi = idx[good]
        vis = z[gi] <= zg[good] + occl_tol_m
        hit_vis[gi[vis]] += 1
    return {"hit_fov": hit_fov, "hit_vis": hit_vis, "hit_evidence": hit_evidence,
            "hit_hole": hit_hole}


def robust_never_visible(visinfo: dict) -> np.ndarray:
    """稳健"从不可见"：有有效深度判据但从未通过门控（排除空洞假阴性）。"""
    return (visinfo["hit_evidence"] > 0) & (visinfo["hit_vis"] == 0)


def load_frozen_mask(path: str) -> np.ndarray:
    from PIL import Image
    a = np.asarray(Image.open(path).convert("L"))
    return a > 127


def build_mask_paths(mask_dir: str, frame_ids: list[int], depth_paths: list[str]) -> dict:
    """按 depth 文件 stem 关联掩码（与 render_compare 同口径）。"""
    md = Path(mask_dir)
    idx = {}
    for p in sorted(md.glob("*.png")):
        idx[p.stem] = str(p)
    out = {}
    for fid in frame_ids:
        if fid >= len(depth_paths):
            continue
        stem = Path(depth_paths[fid]).stem
        if stem in idx:
            out[fid] = load_frozen_mask(idx[stem])
    return out
