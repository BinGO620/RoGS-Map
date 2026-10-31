#!/usr/bin/env python
"""diag_j3_calibers.py — J3 仪器口径**完备分解**（机写 JSON；2026-10-06 甲轮 recon）。

起因：用户批准「甲 = amend J3 仪器口径」。`diag_j3_instrument.py` 已证现 J3（合并图末帧层）混淆
「静态被改」与「动态层遮挡」，但其三口径不足以判定**改口径后机制是否成立**——尤其
「4D 快照逐帧静态」这一候选口径在 `diag_j3_instrument.json` 的 C 列**也是负的**。本脚本把口径
补全到 6 个，全部**机写**，使"哪个口径能过"这件事可判、可复算：

  A. base            : R0 底图（全静态）@ 帧 e 位姿（基准）
  B. merged_final    : R1 合并图（底图 + 末帧动态层）@ 帧 e 位姿（= 现 J3 final-map）
  C. causal_perframe : R1 静态行 + **最近 ≤e 快照**层 @ 帧 e 位姿（= **output① 4D 层序列**消费口径）
  D. fresh_oracle    : 底图 + **逐帧现插**层（GT 深度 oracle，无累积）@ 帧 e 位姿（范式天花板）
  E. static_body     : R1 **仅静态行**（去动态层）@ 帧 e 位姿（**静态本体** = 冻结静态构造核验）
  F. merged_band_r{2,5,10} : B 但**排除 canonical 动态掩码膨胀 r px 的环带**（检验"受损像素落边界"假设）

另有空间签名：受损像素（err1 > err0 + 1e-3，静态掩码内）到 canonical 动态掩码的**距离分布**
（frac≤5/≤10/≤20px），用于核验/更正 verdict §3 的「100% 落 ≤5px」断言。

读法：
  - **E = 静态本体口径**：δ==0 且静态行逐位一致 ⇒ 算子不改静态（构造核验，可证否）。
  - **C = output① 交付口径**：4D 层序列的真静态代价（若非零 ⇒ "改输出形态"并不能消除遮挡）。
  - **D = 范式天花板**：理想逐帧层下静态代价（≈0 ⇒ 范式本身不伤静态）。

用法（需 GPU）：
  python scripts/dynport_offline/diag_j3_calibers.py \
      --seq crowd2 balloon2 person_tracking2 \
      --out results/dynport_offline/evidence/diag_j3_calibers.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch
from scipy import ndimage

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
_spec = importlib.util.spec_from_file_location("dyn_probe", REPO / "scripts/02_analysis/dyn_probe.py")
probe = importlib.util.module_from_spec(_spec)
sys.modules["dyn_probe"] = probe
_spec.loader.exec_module(probe)
sys.path.insert(0, str(REPO / "scripts" / "dynport"))
import judge_dynport as jd  # noqa: E402
from utils.static_eval import static_support_mask, masked_psnr  # noqa: E402


def _med(x):
    x = [v for v in x if v is not None and np.isfinite(v)]
    return round(float(np.median(x)), 4) if x else None


def _static_psnr(run, e, pkg, gt_i, gt_d, dyn):
    return probe.frame_metrics(run, e, pkg, gt_i, gt_d, dyn)["static_psnr"]


def run_seq(seq, device):
    base = str(sorted(Path(REPO).glob(
        f"results/paper2_fulltable/r33_rebase_baseline_{seq}_seed0/datasets_bonn/*/seed_0/*/"))[0])
    R1 = str(REPO / f"results/dynport_offline/L1/{seq}_R1")
    run_b = probe.Run(base, device=device)
    run_m = probe.Run(R1, device=device)
    cdir = Path(R1) / "dynport_causal"
    is_dyn = np.load(cdir / "dynamic_rows.npy")
    keep = ~is_dyn
    snaps = sorted(cdir.glob("frame_*.npz"))
    ids = [int(p.stem.split("_")[1]) for p in snaps]

    dA, dB, dC, dD, dE = [], [], [], [], []
    dF = {2: [], 5: [], 10: []}
    frac = {5: [], 10: [], 20: []}
    fracC = {5: [], 10: [], 20: []}   # C 口径（output① 4D 因果层）的受损像素距离分布
    pose_ctl = []                     # 位姿控制：底图本身 @快照位姿 − @帧 e 位姿（无动态层）
    n_damaged = []
    dmed = []                         # 受损像素到当前帧 canonical 动态掩码的中位距离（px）
    for e in jd.derive_eval_frames(base):
        fd = run_b.frame_data(e)
        if fd is None:
            continue
        gt_i, gt_d, w2c = fd
        dyn = run_b.frame_mask(e)
        cam = run_b.camera(e, w2c)
        pkgA = probe.render_once(run_b, cam, probe.PackedPC(run_b.gaussians))
        pkgB = probe.render_once(run_m, cam, probe.PackedPC(run_m.gaussians))
        if pkgA is None or pkgB is None:
            continue
        a = _static_psnr(run_b, e, pkgA, gt_i, gt_d, dyn)
        b = _static_psnr(run_b, e, pkgB, gt_i, gt_d, dyn)
        dA.append(a)
        dB.append(b - a)

        # 位姿控制：底图本身 @最近 ≤e 快照位姿（无动态层）vs @帧 e 位姿 ⇒ 纯位姿效应
        cv0 = [i for i, f in enumerate(ids) if f <= e]
        if cv0:
            c2w0 = np.asarray(jd.load_snapshot(snaps[max(cv0)])["c2w"], dtype=np.float64)
            cam_s0 = run_b.camera(e, np.linalg.inv(c2w0))
            pkgS0 = probe.render_once(run_b, cam_s0, probe.PackedPC(run_b.gaussians))
            if pkgS0 is not None:
                pose_ctl.append(_static_psnr(run_b, e, pkgS0, gt_i, gt_d, dyn) - a)

        # E: R1 仅静态行（静态本体）
        pcE = jd._StaticPlusDynPC(run_m.gaussians, keep, None)
        pkgE = probe.render_once(run_m, cam, pcE)
        if pkgE is not None:
            dE.append(_static_psnr(run_b, e, pkgE, gt_i, gt_d, dyn) - a)

        # C: output① 因果层（最近 ≤e 快照）
        cv = [i for i, f in enumerate(ids) if f <= e]
        pkgC = None
        if cv:
            pcC = jd._StaticPlusDynPC(run_m.gaussians, keep, jd.load_snapshot(snaps[max(cv)]))
            pkgC = probe.render_once(run_m, cam, pcC)
            if pkgC is not None:
                dC.append(_static_psnr(run_b, e, pkgC, gt_i, gt_d, dyn) - a)

        # D: 范式天花板（逐帧现插 oracle）
        pts, cols = probe.unproject_mask(run_b, e, gt_i, gt_d, w2c, stride=3)
        if pts is not None:
            d2 = probe.make_dynamic(run_b, run_b.gaussians, pts, cols)
            pcD = probe.PackedPC(run_b.gaussians)
            pcD.set_dynamic(probe.dyn_tensors(d2))
            pkgD = probe.render_once(run_b, cam, pcD)
            if pkgD is not None:
                dD.append(_static_psnr(run_b, e, pkgD, gt_i, gt_d, dyn) - a)

        # F: 排除 canonical 动态掩码膨胀环带后的合并 ΔPSNR
        sm = static_support_mask(gt_d, dyn)
        dev = sm.device
        rA = torch.clamp(pkgA["render"], 0, 1)
        rB = torch.clamp(pkgB["render"], 0, 1)
        dyn_np = np.asarray(dyn, dtype=bool)
        for r in (2, 5, 10):
            band = sm & (~torch.from_numpy(ndimage.binary_dilation(dyn_np, iterations=r)).to(dev))
            va = masked_psnr(rA, gt_i, band)
            vb = masked_psnr(rB, gt_i, band)
            if np.isfinite(va) and np.isfinite(vb):
                dF[r].append(vb - va)

        # 空间签名：受损像素到 canonical 动态掩码的距离分布
        err0 = ((rA - gt_i) ** 2).mean(0)
        err1 = ((rB - gt_i) ** 2).mean(0)
        damaged = sm & (err1 > err0 + 1e-3)
        nd = int(damaged.sum())
        n_damaged.append(nd)
        dist = ndimage.distance_transform_edt(~dyn_np)
        dt = torch.from_numpy(dist).to(dev)
        if nd:
            dmed.append(float(np.median(dist[damaged.cpu().numpy()])))
        for r in (5, 10, 20):
            frac[r].append(float((damaged & (dt <= r)).sum().item()) / max(nd, 1))
        # C 口径的受损像素分布（若 C 层可用）
        if pkgC is not None:
            rC = torch.clamp(pkgC["render"], 0, 1)
            errC = ((rC - gt_i) ** 2).mean(0)
            damagedC = sm & (errC > err0 + 1e-3)
            ndC = int(damagedC.sum())
            for r in (5, 10, 20):
                fracC[r].append(float((damagedC & (dt <= r)).sum().item()) / max(ndC, 1))

    return {
        "seq": seq, "n_frames": len(dA), "n_dyn_final": int(is_dyn.sum()), "n_snaps": len(snaps),
        "A_base_static_psnr_median": _med(dA),
        "B_merged_final_delta": _med(dB),
        "C_causal_perframe_delta": _med(dC),
        "D_fresh_oracle_delta": _med(dD),
        "E_static_body_delta": _med(dE),
        "F_merged_band_r2_delta": _med(dF[2]),
        "F_merged_band_r5_delta": _med(dF[5]),
        "F_merged_band_r10_delta": _med(dF[10]),
        "damaged_px_median": _med(n_damaged),
        "damaged_frac_within_r5": _med(frac[5]),
        "damaged_frac_within_r10": _med(frac[10]),
        "damaged_frac_within_r20": _med(frac[20]),
        "C_damaged_frac_within_r5": _med(fracC[5]),
        "C_damaged_frac_within_r10": _med(fracC[10]),
        "C_damaged_frac_within_r20": _med(fracC[20]),
        "pose_control_snapPose_minus_frameE_pose": _med(pose_ctl),
        "n_static_rows": int(keep.sum()),
        "damaged_median_dist_px": _med(dmed),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", nargs="+", default=["crowd2", "balloon2", "person_tracking2"])
    ap.add_argument("--out", default="results/dynport_offline/evidence/diag_j3_calibers.json")
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()
    rows = [run_seq(s, args.device) for s in args.seq]
    out = {
        "experiment": "dynport_offline_j3_caliber_decomposition",
        "note": ("A=底图；B=现 J3(合并图末帧层)；C=output① 4D 因果层；D=范式天花板(oracle)；"
                 "E=静态本体(仅静态行)；F=B 排动态环带；damaged_frac_* = 受损像素落 canonical 动态掩码"
                 " r px 内的比例。全部同一帧位姿 ⇒ 差异纯由层/口径决定。"),
        "rows": rows,
    }
    Path(REPO / args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
