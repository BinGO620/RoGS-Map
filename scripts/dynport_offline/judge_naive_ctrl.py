#!/usr/bin/env python
"""judge_naive_ctrl.py — 朴素插入对照臂（NaiveCtrl）判读器（数字零手抄）。

prereg = results/dynport_offline/evidence/prereg_naive_ctrl_2026-10-13.md。

输入：对同一序列、同一底图、seed0 的
  - R1（完整算子）samepose 判据 JSON（evidence_L3 / evidence_v4 存量，**复用不重跑**）；
  - Naive（本对照）samepose 判据 JSON（本批新跑 judge --samepose）。

读法（先锁，prereg §3）：
  - C1 算子的增量：ΔJ2 = J2(R1) − J2(Naive)（J2 越小越好）；ΔJ2 < −0.05 且
    J1(R1) ≥ J1(Naive) − 0.5 ⇒ 生命周期+S5 带来可测增益（算子必要）；
    |ΔJ2| ≤ 0.05 ⇒ 算子 ≈ 朴素。
  - C2 代价面：Naive vs R1 的 n_dyn（峰值/末值）报数。
  - C3 J3 保护：J3(Naive) vs J3(R1)；Naive 破 ±0.25 而 R1 过 ⇒ S5 的保护作用。

⚠ 坑①（历史）：禁 `arr[mask][idx]` 双层链式赋值（本脚本只读不写，无此风险）。
⚠ 坑③：一律 samepose 键（`J1_samepose_bad_psnr_delta` / `J2_samepose_bad_dl1_ratio` /
  `J3_samepose_static_delta`），禁 `--causal` / final 键。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "dynport"))
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("judge_dynport", REPO / "scripts/dynport/judge_dynport.py")
jd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jd)

J1_MIN = 2.5
J2_MAX = 0.70
J3_BAND = 0.25
C1_DJ2 = 0.05       # ΔJ2 显著线（J2 越小越好；ΔJ2<−0.05 ⇒ 算子更优）
C1_J1_TOL = 0.5     # J1 容忍线


def _med(d, key):
    v = (d or {}).get(key, {})
    return v.get("median") if isinstance(v, dict) else v


def _resolve_base(base_root, seq):
    cands = sorted((Path(base_root) / f"r33_rebase_baseline_{seq}_seed0").glob(
        "datasets_bonn/*/seed_0/*/"))
    return str(cands[-1]) if cands else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="本批 Naive 算子输出根（results/dynport_offline/NaiveCtrl）")
    ap.add_argument("--base-root", default="results/paper2_fulltable")
    ap.add_argument("--seq", nargs="+", default=["crowd2", "balloon2", "person_tracking2"])
    ap.add_argument("--r1-root", nargs="+", default=["results/dynport_offline/L1_v4"],
                    help="存量 R1 算子输出根（复用，不重跑）")
    ap.add_argument("--out-dir", default="results/dynport_offline/evidence_naivectrl")
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()

    root = Path(args.root)
    od = Path(args.out_dir)
    od.mkdir(parents=True, exist_ok=True)

    summary, per_seq = {}, {}
    for seq in args.seq:
        naive_dir = root / f"{seq}_Naive"
        if not (naive_dir / "repair_timing.json").exists():
            print(f"[naivectrl] {seq}: Naive 目录缺 {naive_dir} → 跳过")
            continue
        r0 = _resolve_base(args.base_root, seq)
        if r0 is None:
            print(f"[naivectrl] {seq}: 底图缺 → 跳过")
            continue
        # R1 存量（跨根复用）
        r1 = None
        for rr in args.r1_root:
            cands = sorted((Path(rr) / f"{seq}_R1").glob("**/seed_0/[0-9]*/")) if (Path(rr) / f"{seq}_R1").exists() else []
            if not cands:
                cands = [Path(rr) / f"{seq}_R1"] if (Path(rr) / f"{seq}_R1" / "repair_timing.json").exists() else []
            cands = [c for c in cands if (c / "repair_timing.json").exists()]
            if cands:
                r1 = cands[-1]
                break
        if r1 is None:
            print(f"[naivectrl] {seq}: R1 存量缺（{args.r1_root}）→ 跳过")
            continue
        frames = jd.derive_eval_frames(r0)
        if not frames:
            print(f"[naivectrl] {seq}: 无评估帧 → 跳过")
            continue
        arms = {"E": r0, "D": str(naive_dir)}
        out_j = od / f"naive_ctrl_{seq}_samepose.json"
        cmd = [sys.executable, str(REPO / "scripts/dynport/judge_dynport.py"),
               "--arms", *[f"{k}={v}" for k, v in arms.items()],
               "--seq", seq, "--frames", ",".join(map(str, frames)),
               "--device", args.device, "--samepose", "--out", str(out_j)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[naivectrl] {seq} judge(samepose) rc={r.returncode}\n{r.stderr[-600:]}")
            continue
        nj = json.load(open(out_j))
        # R1 的 samepose 判据（从存量 manifest / verdict JSON 读，零手抄）
        r1_j = None
        for cand in (od.parent / "evidence_L3" / f"dynport_offline_L1_{seq}_L3_samepose.json",
                     od.parent / "evidence_v4" / f"dynport_offline_L1_{seq}_samepose.json",
                     od.parent / "evidence" / f"dynport_offline_L1_{seq}_samepose.json"):
            if Path(cand).exists():
                r1_j = json.load(open(cand))
                break
        if r1_j is None:
            print(f"[naivectrl] {seq}: R1 samepose 判据 JSON 缺 → 跳过")
            continue
        j1r = _med(r1_j, "J1_samepose_bad_psnr_delta"); j2r = _med(r1_j, "J2_samepose_bad_dl1_ratio")
        j3r = _med(r1_j, "J3_samepose_static_delta")
        j1n = _med(nj, "J1_samepose_bad_psnr_delta"); j2n = _med(nj, "J2_samepose_bad_dl1_ratio")
        j3n = _med(nj, "J3_samepose_static_delta")
        dj2 = (j2r - j2n) if (j2r is not None and j2n is not None) else None
        c1 = (dj2 is not None and dj2 < -C1_DJ2
              and j1r is not None and j1n is not None and (j1r >= j1n - C1_J1_TOL))
        c3 = (j3r is not None and j3n is not None
              and abs(j3n) > J3_BAND and abs(j3r) <= J3_BAND)
        t_r = json.load(open(Path(r1) / "repair_timing.json")) if (Path(r1) / "repair_timing.json").exists() else {}
        t_n = json.load(open(naive_dir / "repair_timing.json"))
        per_seq[seq] = {
            "r0": r0, "r1": str(r1), "naive": str(naive_dir),
            "r1_judge": str(r1_j),
            "J1_R1": j1r, "J2_R1": j2r, "J3_R1": j3r,
            "J1_Naive": j1n, "J2_Naive": j2n, "J3_Naive": j3n,
            "deltaJ2_R1_minus_Naive": round(dj2, 4) if dj2 is not None else None,
            "C1_operator_gain": c1, "C3_S5_protects_static": c3,
            "n_dyn_R1": t_r.get("n_dyn"), "n_dyn_Naive": t_n.get("n_dyn"),
            "n_naive_inserted": t_n.get("n_naive_inserted"),
            "naive_s5": {"suppress": t_n.get("s5_suppress_out_mask"),
                         "clamp": t_n.get("s5_scale_clamp")},
            "naive_judge": str(out_j),
        }
        summary[seq] = {k: v for k, v in per_seq[seq].items() if k != "r0"}

    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        head = None
    manifest = {"experiment": "dynport_offline_naive_ctrl",
                "prereg": "results/dynport_offline/evidence/prereg_naive_ctrl_2026-10-13.md",
                "date": datetime.now().strftime("%Y-%m-%d"), "head": head,
                "judge": "scripts/dynport/judge_dynport.py --samepose",
                "instrument_note": "samepose（§12 v4）；Naive = 无生命周期/无S5；R1 = 完整算子（存量复用）",
                "per_seq": per_seq, "summary": summary}
    (od / "manifest_naive_ctrl.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"→ {od}/manifest_naive_ctrl.json")


if __name__ == "__main__":
    main()
