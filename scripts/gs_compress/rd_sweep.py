#!/usr/bin/env python
"""rd_sweep.py — 单图 R-D 扫描驱动（L1 标定用）。

对一张图的源 run：
  * baseline（原始地图）渲染；
  * 一组 uniform 位宽点渲染；
  * 一组 partition 位宽点渲染（动态支撑组更粗）；
把所有 render_metrics 聚合为 R-D 表（JSON + Markdown）。

约束：所有点用同一 `--frames`（跨点逐帧同网格）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HARNESS = REPO / "scripts" / "gs_compress" / "rd_harness.py"


def call(args: list[str]) -> int:
    cmd = [sys.executable, str(HARNESS)] + args
    print("[rd_sweep] $", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=str(REPO)).returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--frames", required=True, help="逗号分隔帧（所有点共用）")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--py", default=sys.executable)
    ap.add_argument("--out", default=None)
    ap.add_argument("--uniform", default="16,8,8,8,8;12,8,8,8,8;10,6,6,6,6;10,5,5,5,5;8,4,4,4,4;6,4,4,4,4",
                    help="分号分隔的 uniform 位宽配置")
    ap.add_argument("--partition", default=None,
                    help="分号分隔 'fine|dyn' 配置（coarsen=dyn：动态组更粗）")
    ap.add_argument("--partition-static", default=None,
                    help="分号分隔 'static_coarse|dyn_fine' 配置（coarsen=static）")
    ap.add_argument("--no-static", action="store_true", help="跳过静态指标（无掩码序列）")
    ap.add_argument("--robust-q", default=None,
                    help="v2 乙线：稳健百分位（如 '0.1'）；启用则加 robust+escape 与 robust+clip 臂")
    ap.add_argument("--robust-bits", default="16,8,8,8,8;10,6,6,6,6;8,4,4,4,4",
                    help="robust 臂的位宽点（分号分隔）")
    args = ap.parse_args()
    extra = ["--no-static"] if args.no_static else []

    rd_dir = REPO / "results" / "gs_compress" / "evidence" / "rd"
    rd_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    def collect(path: Path):
        if path.exists():
            rows.append(json.loads(path.read_text()))

    # baseline
    call(["--run-dir", args.run_dir, "--tag", args.tag, "--baseline",
          "--frames", args.frames, "--device", args.device] + extra)
    collect(rd_dir / f"{args.tag}_baseline.json")

    for cfg in args.uniform.split(";"):
        cfg = cfg.strip()
        if not cfg:
            continue
        call(["--run-dir", args.run_dir, "--tag", args.tag, "--bits", cfg,
              "--frames", args.frames, "--device", args.device] + extra)
        collect(rd_dir / f"{args.tag}_b{'-'.join(cfg.split(','))}.json")

    if args.partition:
        for spec in args.partition.split(";"):
            spec = spec.strip()
            if not spec:
                continue
            fine, dyn = spec.split("|")
            call(["--run-dir", args.run_dir, "--tag", args.tag, "--bits", fine,
                  "--bits-dyn", dyn, "--coarsen", "dyn",
                  "--frames", args.frames, "--device", args.device] + extra)
            collect(rd_dir / f"{args.tag}_b{'-'.join(fine.split(','))}_pdyn{'-'.join(dyn.split(','))}.json")

    if args.partition_static:
        for spec in args.partition_static.split(";"):
            spec = spec.strip()
            if not spec:
                continue
            sc, df = spec.split("|")
            call(["--run-dir", args.run_dir, "--tag", args.tag, "--bits", sc,
                  "--bits-dyn", df, "--coarsen", "static",
                  "--frames", args.frames, "--device", args.device] + extra)
            collect(rd_dir / f"{args.tag}_b{'-'.join(sc.split(','))}_pstaticdyn{'-'.join(df.split(','))}.json")

    if args.robust_q:
        for cfg in args.robust_bits.split(";"):
            cfg = cfg.strip()
            if not cfg:
                continue
            for esc_flag, esc_tag in ((["--escape"], "_esc"), ([], "_clip")):
                call(["--run-dir", args.run_dir, "--tag", args.tag, "--bits", cfg,
                      "--range-mode", "robust", "--range-q", args.robust_q,
                      "--frames", args.frames, "--device", args.device] + esc_flag + extra)
                # rd_harness 命名：{tag}_b{b}_rb{q}_{esc|clip}
                qt = ("%g" % float(args.robust_q)).replace(".", "")
                collect(rd_dir / f"{args.tag}_b{'-'.join(cfg.split(','))}_rb{qt}{esc_tag}.json")

    # aggregate
    def psnr(r):
        return (r.get("render") or {}).get("mean_psnr")

    out = {"tag": args.tag, "run_dir": args.run_dir, "frames": args.frames, "rows": rows}
    out_path = Path(args.out) if args.out else (rd_dir / f"{args.tag}_rd_table.json")
    out_path.write_text(json.dumps(out, indent=2))

    md = [f"# R-D sweep: {args.tag}", "", f"frames={args.frames}", "",
          "| alloc | bits | bits_dyn | B/prim | ratio_full | PSNR | static_psnr | ghost_dl1 |",
          "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        rm = r.get("render") or {}
        md.append("| {} | {} | {} | {:.2f} | {:.2f}x | {} | {} | {} |".format(
            r.get("kind", r.get("alloc", "?")), r.get("bits"),
            r.get("bits_dyn") or "-", r.get("rate_bytes_per_prim", 0),
            r.get("ratio_full", 0), rm.get("mean_psnr"), rm.get("mean_static_psnr"),
            rm.get("mean_ghost_excess_depth_l1_cm")))
    (rd_dir / f"{args.tag}_rd_table.md").write_text("\n".join(md))
    print("\n".join(md))
    print(f"\n[rd_sweep] wrote {out_path}")


if __name__ == "__main__":
    main()
