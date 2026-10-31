#!/usr/bin/env python3
"""rerender_r33_static_canon.py — 用 canonical 掩码重算 R33 静态/残影证据线。

为什么
------
R33 的静态区/残影读数（`static_psnr` / `ghost_excess_depth_l1_cm`，44 run，位于
`results/paper2_fulltable/render_compare_static/`）用的是 `dynamic_mask_gtmc`
（`mask_source=dynamic_mask_gtmc`）——该掩码 2026-09-21 被证伪（移动者召回 0.10–0.39）。
故"static PSNR 全中性"、"ghost_excess 方向一致更优"、"地图面不退化"三条结论须重算。
详见 `results/lifecycle_paper2/evidence/mask_incident_impact_2026-09-22.md` §3.2。

做法（只换掩码源，其余一字不差）
--------------------------------
从原 `render_metrics.json` 恢复**逐帧帧集**（`per_frame[].frame`）与 PLY 变体，
用 canonical `dynamic_mask/`（render_compare 的 auto 默认）重渲染到
`render_compare_static_canon/<tag>/`，**不覆盖**原目录（审计痕迹）。

机器
----
44 个 run 分布在两台机（原样保留，不新增跨机混比）：32 个 PLY 在本地、12 个在远程。
用 `--side local|remote` 各跑一次。

用法
----
    PY=/data/conda_envs/monogs-ours/bin/python
    $PY scripts/02_analysis/rerender_r33_static_canon.py --side local --dry-run
    $PY scripts/02_analysis/rerender_r33_static_canon.py --side local
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "results", "paper2_fulltable", "render_compare_static")
DST = os.path.join(REPO, "results", "paper2_fulltable", "render_compare_static_canon")
RENDER = os.path.join(REPO, "scripts", "02_analysis", "render_compare.py")


def side_of(path: str) -> str:
    return "local" if path.startswith("/data/") else "remote"


def collect(side: str):
    jobs = []
    for p in sorted(glob.glob(os.path.join(SRC, "*", "render_metrics.json"))):
        d = json.load(open(p))
        run_dir = d.get("run_dir", "")
        if side_of(run_dir) != side:
            continue
        frames = [r["frame"] for r in d.get("per_frame", []) if "frame" in r]
        ply = d.get("ply", "")
        ply_variant = "final_after_opt" if "final_after_opt" in ply else "final"
        tag = os.path.basename(os.path.dirname(p))
        jobs.append({"tag": tag, "run_dir": run_dir, "frames": frames,
                     "ply": ply_variant, "n_frames": d.get("n_frames")})
    return jobs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["local", "remote"], required=True)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    jobs = collect(args.side)
    print(f"[r33-canon] side={args.side} jobs={len(jobs)}", flush=True)
    os.makedirs(DST, exist_ok=True)
    bad = 0
    for j in jobs:
        ply = os.path.join(j["run_dir"], "point_cloud", j["ply"], "point_cloud.ply")
        out = os.path.join(DST, j["tag"])
        mjson = os.path.join(out, "render_metrics.json")
        if not os.path.isfile(ply):
            print(f"  SKIP {j['tag']} (缺 PLY: {ply[:70]})", flush=True); bad += 1; continue
        if os.path.isfile(mjson) and json.load(open(mjson)).get("n_frames") == len(j["frames"]):
            print(f"  SKIP {j['tag']} (已完成)", flush=True); continue
        cmd = [sys.executable, RENDER, "--run-dir", j["run_dir"],
               "--frames", ",".join(str(f) for f in j["frames"]),
               "--vacated-window-frames", "30",
               "--ply", j["ply"], "--device", args.device,
               "--out-dir", out]
        if args.dry_run:
            print("  DRY", " ".join(cmd[:3]), "...", f"frames={len(j['frames'])}", j["tag"], flush=True)
            continue
        print(f"  render {j['tag']} (frames={len(j['frames'])})", flush=True)
        # 允许渲染失败（个别 PLY/相机组合可能撞栅格化器）——失败留痕、不中断，盘点时如实计
        proc = subprocess.run(cmd, capture_output=True, text=True)
        ok = os.path.isfile(mjson) and json.load(open(mjson)).get("n_frames") == len(j["frames"])
        if proc.returncode != 0 or not ok:
            bad += 1
            print(f"    FAIL rc={proc.returncode} :: {proc.stderr.strip().splitlines()[-1][:120] if proc.stderr.strip() else ''}", flush=True)
    print(f"[r33-canon] done side={args.side} bad={bad}/{len(jobs)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
