#!/usr/bin/env python
"""artifact_sha256_L3.py — L3 批工件 SHA256 provenance（PLY/trj/dynamic_rows/timing）。

prereg §7（G1-M5）：快照/修复地图默认被 .gitignore 忽略 ⇒ 须以 SHA256 落库（远程丢失仍可核验）。
本脚本机写 `evidence_L3/artifact_sha256_L3.json`（数字零手抄；对齐 L2 结构 + 本批复用根）。

用法：
  python scripts/dynport_offline/artifact_sha256_L3.py \
      --roots results/dynport_offline/L3 results/dynport_offline/L1_v4 results/dynport_offline/L2 \
      --out results/dynport_offline/evidence_L3/artifact_sha256_L3.json
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FILES = ["point_cloud/final_after_opt/point_cloud.ply",
         "plot/trj_full_final.json",
         "dynport_causal/dynamic_rows.npy",
         "repair_timing.json"]


def _sha16(p: Path):
    if not p.exists():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+",
                    default=["results/dynport_offline/L3", "results/dynport_offline/L1_v4",
                             "results/dynport_offline/L2"])
    ap.add_argument("--out", default="results/dynport_offline/evidence_L3/artifact_sha256_L3.json")
    args = ap.parse_args()
    out = {}
    for r in args.roots:
        for d in sorted(Path(r).glob("*_R1")) + sorted(Path(r).glob("*_Cneg")) + \
                 sorted(Path(r).glob("*_OFF")):
            if not d.is_dir() or not (d / "repair_timing.json").exists():
                continue
            entry = {f: _sha16(d / f) for f in FILES}
            try:
                entry["n_snapshots"] = len(list((d / "dynport_causal").glob("frame_*.npz")))
            except Exception:
                entry["n_snapshots"] = None
            out[d.name] = entry
    Path(REPO / args.out).write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"→ {args.out} ({len(out)} runs)")


if __name__ == "__main__":
    main()
