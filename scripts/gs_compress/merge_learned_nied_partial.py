#!/usr/bin/env python
"""merge_learned_nied_partial.py — 把 Niedermayr 基线的两段结果合并成最终 rd json。

背景：2026-10-16 远程 3090（jiangwenheng）跑到 48/78 时 GPU0 物理掉卡，剩余 30 张由本机 2060 续跑
（见 run_learned_nied_local_resume.sh）。两段结果必须合并成一个完整、同口径的 json 才能进 Table 4。

输入（两段都必须是 --iters 5000 的同一代码产出）：
  远程部分：results/gs_compress/evidence/rd/partial_remote3090/learned_nied_<split>.json
  本机续跑：.tmp/learned_nied_resume/learned_nied_<split>.json
输出：
  results/gs_compress/evidence/rd/learned_nied_<split>.json（rows 按 tag 排序）

护栏（缺一即报错退出，不允许静默产出有偏的均值）：
  - 两段 tag 不得重叠；
  - 合并后必须**恰好覆盖** rd/<split>_*_rd_table.json 的全部 tag（无缺失、无多余）；
  - finetune_iters 必须一致；
  - 每行必须有非空 render 与 psnr_delta。

用法：/data/conda_envs/monogs-ours/bin/python scripts/gs_compress/merge_learned_nied_partial.py
"""
from __future__ import annotations

import glob
import json
import os
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RD = REPO / "results/gs_compress/evidence/rd"
PART = RD / "partial_remote3090"
LOCAL = REPO / ".tmp/learned_nied_resume"


def load_rows(p: Path):
    d = json.loads(p.read_text())
    return d, d["rows"]


def main():
    ok = True
    for split in ("L2", "L3"):
        part_p = PART / f"learned_nied_{split}.json"
        loc_p = LOCAL / f"learned_nied_{split}.json"
        for p in (part_p, loc_p):
            if not p.exists():
                print(f"ERROR 缺输入: {p}")
                ok = False
        if not ok:
            continue

        meta, rp = load_rows(part_p)
        _, rl = load_rows(loc_p)
        tp = {r["tag"] for r in rp}
        tl = {r["tag"] for r in rl}
        overlap = tp & tl
        if overlap:
            print(f"ERROR {split}: 两段 tag 重叠 {sorted(overlap)}")
            ok = False
            continue

        allt = {os.path.basename(p).replace("_rd_table.json", "")
                for p in glob.glob(str(RD / f"{split}_*_rd_table.json"))}
        got = tp | tl
        if got != allt:
            print(f"ERROR {split}: 覆盖不全 缺={sorted(allt - got)} 多={sorted(got - allt)}")
            ok = False
            continue

        rows = sorted(rp + rl, key=lambda r: r["tag"])
        iters = {r.get("finetune_iters") for r in rows}
        if iters != {5000}:
            print(f"ERROR {split}: finetune_iters 不一致 {iters}")
            ok = False
            continue
        bad = [r["tag"] for r in rows if not r.get("render") or r.get("psnr_delta") is None]
        if bad:
            print(f"ERROR {split}: 行不完整（无 render/Δ）: {bad}")
            ok = False
            continue

        out = RD / f"learned_nied_{split}.json"
        out.write_text(json.dumps({
            "method": meta["method"],
            "denominator": meta["denominator"],
            "finetune_iters": meta["finetune_iters"],
            "provenance": ("remote3090 partial (34/14 rows) + local2060 resume (8/22 rows); "
                           "merged by scripts/gs_compress/merge_learned_nied_partial.py"),
            "rows": rows,
        }, indent=2))

        rr = [r["ratio_full"] for r in rows]
        pp = [r["render"]["mean_psnr"] for r in rows]
        dd = [r["psnr_delta"] for r in rows]
        print(f"{split}: n={len(rows)} (remote {len(rp)} + local {len(rl)}) -> {out}")
        print(f"    ratio={st.mean(rr):.3f}x  psnr={st.mean(pp):.3f}  "
              f"delta={st.mean(dd):+.3f} dB (min {min(dd):+.2f}, max {max(dd):+.2f})")

    if not ok:
        sys.exit(1)
    print("MERGE-OK")


if __name__ == "__main__":
    main()
