#!/usr/bin/env python
"""diag_j3_instrument.py — J3（静态区无伤）仪器语义诊断（机写 JSON）。

背景（2026-10-06 L1 批）：manifest 的 J3 出现仪器依赖分裂（crowd2 −0.06 / balloon2 −3.21 /
pt2 0.0）。本脚本把"静态区 ΔPSNR"在**同一批 run**上分解为四种口径，定位差异来源：

  A. base            : 原底图 @ 帧 e 位姿（基准 λ_base）
  B. merged_final    : 合并图（底图 + **末帧**动态层）@ 帧 e 位姿（= 现 J3 final-map 所测）
  C. causal_samepose : 合并图（底图 + **最近 ≤e 快照**动态层）@ **帧 e** 位姿（同位姿 ⇒ 隔离层效应）
  D. fresh_oracle    : 底图 + **逐帧现插**动态层 @ 帧 e 位姿（oracle；无累积幽灵）

读法：B−A = 现 J3；C−A = 层的"时刻正确"下的静态代价；D−A = 静态本体代价（oracle）。
B/C/D 均用**同一帧位姿**（消位姿混杂），故差异纯由"动态层取哪一时刻/是否累积"决定。

用法（需 GPU、快照在盘）：
  python scripts/dynport_offline/diag_j3_instrument.py --seq crowd2 balloon2 person_tracking2 \
      --out results/dynport_offline/evidence/diag_j3_instrument.json
"""
from __future__ import annotations
import argparse, glob, importlib.util, json, sys
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
_spec = importlib.util.spec_from_file_location("dyn_probe", REPO / "scripts/02_analysis/dyn_probe.py")
probe = importlib.util.module_from_spec(_spec); sys.modules["dyn_probe"] = probe
_spec.loader.exec_module(probe)
sys.path.insert(0, str(REPO / "scripts" / "dynport"))
import judge_dynport as jd  # noqa: E402


def _med(x):
    x = [v for v in x if v is not None]
    return round(float(np.median(x)), 4) if x else None


def run_seq(seq, root, device):
    base = sorted(glob.glob(str(REPO / f"results/paper2_fulltable/r33_rebase_baseline_{seq}_seed0"
                                     f"/datasets_bonn/r33_rebase_baseline_{seq}/seed_0/*/")))[0]
    R1 = str(REPO / f"results/dynport_offline/L1/{seq}_R1")
    run_b = probe.Run(base, device=device); run_m = probe.Run(R1, device=device)
    drow = Path(R1) / "dynport_causal" / "dynamic_rows.npy"
    is_dyn = np.load(drow); keep = ~is_dyn
    snaps = sorted((Path(R1) / "dynport_causal").glob("frame_*.npz"))
    ids = [int(p.stem.split("_")[1]) for p in snaps]
    dA, dB, dC, dD = [], [], [], []
    for e in jd.derive_eval_frames(base):
        fd = run_b.frame_data(e)
        if fd is None:
            continue
        gt_i, gt_d, w2c = fd; dyn = run_b.frame_mask(e); cam = run_b.camera(e, w2c)
        lam = lambda pkg: probe.frame_metrics(run_b, e, pkg, gt_i, gt_d, dyn)["static_psnr"]
        a = lam(probe.render_once(run_b, cam, probe.PackedPC(run_b.gaussians)))
        dA.append(a)
        if snaps:
            pc = jd._StaticPlusDynPC(run_m.gaussians, keep, jd.load_snapshot(snaps[-1]))
            dB.append(lam(probe.render_once(run_m, cam, pc)) - a)
        cv = [i for i, f in enumerate(ids) if f <= e]
        if cv:
            pc = jd._StaticPlusDynPC(run_m.gaussians, keep, jd.load_snapshot(snaps[max(cv)]))
            dC.append(lam(probe.render_once(run_m, cam, pc)) - a)
        pts, cols = probe.unproject_mask(run_b, e, gt_i, gt_d, w2c, stride=3)
        if pts is not None:
            d2 = probe.make_dynamic(run_b, run_b.gaussians, pts, cols)
            pcF = probe.PackedPC(run_b.gaussians); pcF.set_dynamic(probe.dyn_tensors(d2))
            dD.append(lam(probe.render_once(run_b, cam, pcF)) - a)
    return {"seq": seq, "n_frames": len(dA), "base_static_psnr_median": _med(dA),
            "B_minus_A_merged_final": _med(dB), "C_minus_A_causal_samepose": _med(dC),
            "D_minus_A_fresh_oracle": _med(dD),
            "n_dyn_final": int(is_dyn.sum()), "n_snaps": len(snaps)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", nargs="+", default=["crowd2", "balloon2", "person_tracking2"])
    ap.add_argument("--out", default="results/dynport_offline/evidence/diag_j3_instrument.json")
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()
    rows = [run_seq(s, None, args.device) for s in args.seq]
    out = {"experiment": "dynport_offline_j3_instrument_diag", "rows": rows,
           "note": "B=现 J3(final-map, 合并图末帧层)；C=同位姿因果层；D=oracle 逐帧层；"
                   "全部同一帧位姿 ⇒ 差异纯由层时刻/累积决定"}
    Path(REPO / args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
