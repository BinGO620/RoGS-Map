#!/usr/bin/env python3
"""compare_mask_coverage_3ref.py — 两种掩码下的 instrument_v2 **三参照**并陈（判效级读数）。

与 `compare_mask_coverage.py`（单参照、render_compare 自带 freshvac/ghost）的区别：
本脚本用仓库现行判阅参照 = instrument_v2 三参照（全域静态 / 邻域环 / **深度分层匹配 m3**），
逐帧配对 Δ = exit − off，报 **median + IQR**，并给三参照同号与"稀薄（可判性）"标记
（复用 `instrument_v2_judge` 的函数，**同源防漂移**）。

跨掩码**只并陈、禁混引**（DISCIPLINE「比较前提」6）：canonical 与 mover 是两台仪器。

用法
----
    python scripts/02_analysis/compare_mask_coverage_3ref.py [--out <md>]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import instrument_v2_judge as IV2  # noqa: E402

RESCORE = REPO / "results" / "lifecycle_paper2" / "instrument_v2" / "rescore"
SEQS = ["balloon", "balloon2", "mvnobox", "mvnobox2"]
REFS = IV2.REFS


def load(name: str) -> dict | None:
    p = RESCORE / f"rescore_{name}.json"
    if not p.is_file():
        return None
    try:
        return json.load(open(p))
    except json.JSONDecodeError:
        return None


def row(seq: str, seed: int, mask: str):
    su = f"_{mask}"
    off = load(f"L3_{seq}_off_s{seed}{su}")
    ex = load(f"L3_{seq}_exit_s{seed}{su}")
    if off is None or ex is None:
        return None
    d = IV2.paired_delta(ex, off)
    if not d:
        return None
    same, signs, mabs = IV2.triple_sign(d)
    thin = IV2.is_thin({0: ex, 1: off}, 0, 1, d)
    return {"d": d, "same": same, "signs": signs, "thin": thin,
            "full": d[REFS[0]]["median"] if d.get(REFS[0]) else None,
            "ring": d[REFS[1]]["median"] if d.get(REFS[1]) else None,
            "m3": d[REFS[2]]["median"] if d.get(REFS[2]) else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    L = []
    L.append("# 掩码覆盖并陈（**instrument_v2 三参照**；Δ = exit − off，负 = exit 改善）\n")
    L.append("三列 = 全域静态 / 邻域环 / 深度分层匹配(m3)。**跨掩码仅并陈，禁混引**。")
    L.append("`⚠稀薄` = 任一参照可用帧 < 50% 两臂共同帧（对照区结构性缺失）⇒ 判效不可用。\n")
    L.append("| 序列 | seed | 掩码 | Δ 全域静态 | Δ 邻域环 | Δ m3 | 读数 |")
    L.append("|---|---|---|---|---|---|---|")

    agg = {}
    for seq in SEQS:
        for seed in (0, 1, 2):
            for mask in ("canon", "mover"):
                r = row(seq, seed, mask)
                if r is None:
                    L.append(f"| {seq} | s{seed} | {mask} | 缺工件 | — | — | — |")
                    continue
                if r["thin"]:
                    tag = "⚠稀薄(对照区缺)"
                elif r["same"]:
                    tag = "同号"
                elif r["signs"]:
                    tag = "混号"
                else:
                    tag = "参照不足"
                L.append(f"| {seq} | s{seed} | {mask} | "
                         f"{r['full']:+.2f} | {r['ring']:+.2f} | {r['m3']:+.2f} | {tag} |")
                agg.setdefault((seq, mask), {"full": [], "ring": [], "m3": [], "neg": 0, "n": 0})
                a = agg[(seq, mask)]
                for k in ("full", "ring", "m3"):
                    if r[k] is not None:
                        a[k].append(r[k])
                if r["m3"] is not None:
                    a["n"] += 1
                    a["neg"] += int(r["m3"] < 0)

    L.append("\n## 跨 seed 汇总（逐 seed median 的 median；描述性）\n")
    L.append("| 序列 | 掩码 | mom 全域静态 | mom 邻域环 | **mom m3** | m3 负 seed |")
    L.append("|---|---|---|---|---|---|")
    for seq in SEQS:
        for mask in ("canon", "mover"):
            a = agg.get((seq, mask))
            if not a or not a["m3"]:
                continue
            f = lambda k: statistics.median(a[k]) if a[k] else float("nan")  # noqa: E731
            L.append(f"| {seq} | {mask} | {f('full'):+.2f} | {f('ring'):+.2f} | "
                     f"**{f('m3'):+.2f}** | {a['neg']}/{a['n']} |")

    text = "\n".join(L) + "\n"
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text)
        print(f"written {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
