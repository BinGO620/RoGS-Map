#!/usr/bin/env python
"""gen_probe_5seq_configs.py — 由 coverage 工件生成 5 序列 × 2 臂的探针 config。

判据先锁：帧列表/t0 全部来自 `evidence/coverage_b1/<seq>.json`（先于任何结果指标生成）。
用法：python scripts/embrace_dyn/gen_probe_5seq_configs.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COV = REPO / "results/embrace_dyn/evidence/coverage_b1"
CFG = REPO / "configs/experiments/embrace_dyn"
EV = REPO / "results/embrace_dyn/evidence"

SEQS = ["crowd", "crowd2", "crowd3", "balloon2", "person_tracking"]
ARMS = ["baseline", "gate"]
PREREG = "results/embrace_dyn/evidence/prereg_dyn_probe_5seq_2026-10-05.md"


def find_run(seq, arm):
    base = REPO / f"results/paper2_fulltable/r33_rebase_{arm}_{seq}_seed0/datasets_bonn"
    hits = sorted(base.glob(f"*/seed_0/*/"))
    return str(hits[0].relative_to(REPO)).rstrip("/") if hits else None


def main():
    CFG.mkdir(parents=True, exist_ok=True)
    for seq in SEQS:
        cov = json.loads((COV / f"{seq}.json").read_text())
        maps = []
        for arm in ARMS:
            rd = find_run(seq, arm)
            if not rd:
                print(f"  MISS {seq}/{arm}")
                continue
            maps.append({"tag": arm, "run_dir": rd,
                         "kf_log": f"results/paper2_fulltable/r33_rebase_{arm}_{seq}_seed0.consolelog"})
        cfg = {
            "prereg": PREREG,
            "sequence": seq,
            "device": "cuda:0",
            "ply": "final_after_opt",
            "mask_subdir": "auto",           # canonical dynamic_mask（不回退 legacy）
            "mask_class": 15,
            "unproj_stride": 3,
            "fit_iters": 300,
            "lrs": {"xyz": 5.0e-4, "scale": 5.0e-3, "rot": 1.0e-3, "opa": 5.0e-2, "dc": 5.0e-3},
            "control_shift_cam_m": [0.30, 0.0, 0.0],
            "t0_frame": cov["t0_frame"],
            "frames": cov["selected_frames"],
            "arms": ["P1", "P2", "C-", "P4", "P2c"],
            "maps": maps,
            "out": f"results/embrace_dyn/evidence/dyn_probe_5seq_{seq}_results.json",
        }
        # 手写 YAML（避免依赖 pyyaml 排序问题）
        L = [f"# 由 gen_probe_5seq_configs.py 生成；帧/t0 锁自 coverage_b1/{seq}.json（判据先锁）",
             f"prereg: {cfg['prereg']}",
             f"sequence: {seq}",
             f"device: {cfg['device']}",
             f"ply: {cfg['ply']}",
             f"mask_subdir: {cfg['mask_subdir']}",
             f"mask_class: {cfg['mask_class']}",
             f"unproj_stride: {cfg['unproj_stride']}",
             f"fit_iters: {cfg['fit_iters']}",
             "lrs: {xyz: 5.0e-4, scale: 5.0e-3, rot: 1.0e-3, opa: 5.0e-2, dc: 5.0e-3}",
             "control_shift_cam_m: [0.30, 0.0, 0.0]",
             f"t0_frame: {cfg['t0_frame']}",
             f"frames: [{', '.join(str(x) for x in cfg['frames'])}]",
             f"arms: [{', '.join(cfg['arms'])}]",
             "maps:"]
        for m in maps:
            L.append(f"  - tag: {m['tag']}")
            L.append(f"    run_dir: {m['run_dir']}")
            L.append(f"    kf_log: {m['kf_log']}")
        L.append(f"out: {cfg['out']}")
        (CFG / f"probe_5seq_{seq}.yaml").write_text("\n".join(L) + "\n")
        print(f"  wrote probe_5seq_{seq}.yaml ({len(maps)} maps, t0={cfg['t0_frame']})")


if __name__ == "__main__":
    main()
