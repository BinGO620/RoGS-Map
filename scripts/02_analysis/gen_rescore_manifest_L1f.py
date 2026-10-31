#!/usr/bin/env python3
"""gen_rescore_manifest_L1f.py — 生成 L1f 批的 instrument_v2 重评分清单（程序化，禁手抄）。

为什么需要它
------------
L1f 判决的**指标**由 prereg 锁定为「instrument_v2 三参照（m3 主读数参照；全域静态/邻域环
并陈）+ per-frame median/IQR」（prereg_L1f_obsdebt.md §3；DISCIPLINE「测量口径」1 禁单参照
mean 作判据）。而 instrument_v2 的冻结清单 `rescore_batch_manifest.json` 只覆盖
"全部**已有**臂"（prereg_instrument_v2 §2b，109 run 硬断言），**不含 L1f**。故本批的
9 run 走**独立清单**：不修改冻结清单（避免 run_instrument_v2_batch.sh 的 `!=109` 断言被破）。

口径单源
--------
- run_dir：在 `<runtag>/datasets_bonn/*/seed_<N>/*` 下 glob 定位（不硬编码时间戳）；
- frames：读**已落盘**的 `evidence/l3_framesets.json`（与渲染驱动同源，两臂同字面列表）；
- 输出键名 = `render_<rtag>_canon`（与 instrument_v2 批一致 ⇒ 下游 `rescore_*` 命名同构）。

用法
----
    python scripts/02_analysis/gen_rescore_manifest_L1f.py --write   # 落盘
    python scripts/02_analysis/gen_rescore_manifest_L1f.py           # dry-run 只打印
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.join(REPO, "results", "lifecycle_paper2")
FRAMESETS = os.path.join(ROOT, "evidence", "l3_framesets.json")
DEFAULT_OUT = os.path.join(ROOT, "instrument_v2", "rescore_batch_manifest_L1f.json")

# (渲染 tag 前缀, run 目录 tag, seq, seeds)  —— 与 render_L1f_canon.sh 的清单一一对应
# stage-1 = seeds 0-2（9 run）；--confirm（击杀分支）= 追加 seeds 3-5（+6 run，共 15）
JOBS_STAGE1 = [
    ("L1f2_balloon2_obsdebt", "L1f2_balloon2_obsdebt", "balloon2", (0, 1, 2)),
    ("L1f_balloon2_exitfill_ctrl", "L1f_balloon2_balloon2_exitfill_ctrl", "balloon2", (0, 1, 2)),
    ("L1f_person_tracking_obsdebt", "L1f_person_tracking_person_tracking_obsdebt",
     "person_tracking", (0, 1, 2)),
]
JOBS_CONFIRM = [
    ("L1f2_balloon2_obsdebt", "L1f2_balloon2_obsdebt", "balloon2", (3, 4, 5)),
    ("L1f_balloon2_exitfill_ctrl", "L1f_balloon2_balloon2_exitfill_ctrl", "balloon2", (3, 4, 5)),
]
JOBS = JOBS_STAGE1  # 默认 stage-1；main() 按 --confirm 切换
N_EXPECT = 9


def find_run(runtag: str, seed: int) -> str | None:
    pat = os.path.join(ROOT, runtag, "datasets_bonn", "*", f"seed_{seed}", "*")
    hits = sorted(p for p in glob.glob(pat) if os.path.isdir(p))
    return hits[-1] if hits else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="落盘 JSON（缺省仅打印）")
    ap.add_argument("--confirm", action="store_true",
                    help="击杀分支 stage-2：追加 balloon2 两臂 s3-5（+6 run，共 15）")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    jobs = JOBS_STAGE1 + (JOBS_CONFIRM if args.confirm else [])
    n_expect = 9 + (6 if args.confirm else 0)

    if not os.path.isfile(FRAMESETS):
        print(f"ERROR: 缺 {FRAMESETS}（先跑 l3_framesets.py --write）", file=sys.stderr)
        return 2
    fs = json.load(open(FRAMESETS))["sequences"]

    man: dict[str, dict] = {}
    problems = []
    for rtag_prefix, runtag, seq, seeds in jobs:
        frames = ",".join(str(i) for i in fs[seq]["frames"])
        n_frames = fs[seq]["n_frames"]
        for sd in seeds:
            key = f"render_{rtag_prefix}_s{sd}_canon"
            run = find_run(runtag, sd)
            if run is None:
                problems.append(f"{key}: no run dir under {runtag} seed_{sd}")
                continue
            man[key] = {
                "run_dir": os.path.relpath(run, REPO),
                "frames": frames,
                "n_frames": n_frames,
            }

    for k, v in sorted(man.items()):
        print(f"  {k}\n      run_dir={v['run_dir']}  n_frames={v['n_frames']}")
    print(f"\nmanifest entries = {len(man)} (expect {n_expect})")

    if problems:
        print("自检失败：", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return 2
    if len(man) != n_expect:
        print(f"ABORT: entries={len(man)} != {n_expect}", file=sys.stderr)
        return 2

    if args.write:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(man, f, indent=1, ensure_ascii=False)
        print(f"\n已落盘: {args.out}")
    else:
        print("\n(dry-run；加 --write 落盘)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
