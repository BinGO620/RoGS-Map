#!/usr/bin/env python3
"""gen_rescore_manifest_mover.py — 由冻结主清单派生 **mover 掩码** 的重评分清单。

做法（不重新 glob、口径一致）
------------------------------
冻结主清单 `instrument_v2/rescore_batch_manifest.json` 记录的是 canonical 渲染臂的
`{run_dir, frames}`。**同一批 run** 换掩码重渲后，`run_dir` 与 `frames` 完全相同
（只是评测掩码不同）⇒ 只需把键名 `render_<tag>_canon` 复制为 `render_<tag>_mover`。

选取范围（与 `rerender_L3_mover.sh` 的 30 个 job 严格一致）
----------------------------------------------------------
- `L3_{balloon,balloon2,mvnobox,mvnobox2}_{off,exit}_s{0,1,2}` = 24
- `L3_{mvnobox,balloon2}_exit_fill_s{0,1,2}` = 6

用法
----
    python scripts/02_analysis/gen_rescore_manifest_mover.py --write
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.join(REPO, "results", "lifecycle_paper2")
SRC = os.path.join(ROOT, "instrument_v2", "rescore_batch_manifest.json")
DEFAULT_OUT = os.path.join(ROOT, "instrument_v2", "rescore_batch_manifest_mover.json")

PATS = [
    re.compile(r"^render_L3_(balloon|balloon2|mvnobox|mvnobox2)_(off|exit)_s[0-2]_canon$"),
    re.compile(r"^render_L3_(mvnobox|balloon2)_exit_fill_s[0-2]_canon$"),
]
N_EXPECT = 30


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    if not os.path.isfile(SRC):
        print(f"ERROR: 缺冻结主清单 {SRC}", file=sys.stderr)
        return 2
    src = json.load(open(SRC))

    man = {}
    for name, v in sorted(src.items()):
        if not any(p.match(name) for p in PATS):
            continue
        mover = name.replace("_canon", "_mover")
        man[mover] = dict(v)
        man[mover]["mask_subdir"] = "dynamic_mask_mover"

    for k in sorted(man):
        print(f"  {k}  <- {man[k]['run_dir']}")
    print(f"\nmanifest entries = {len(man)} (expect {N_EXPECT})")
    if len(man) != N_EXPECT:
        print(f"ABORT: {len(man)} != {N_EXPECT}", file=sys.stderr)
        return 2
    if args.write:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(man, f, indent=1, ensure_ascii=False)
        print(f"已落盘: {args.out}")
    else:
        print("(dry-run；加 --write 落盘)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
