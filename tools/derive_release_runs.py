#!/usr/bin/env python
"""derive_release_runs.py — 从论文2证据 json 反推离线轨底图 run 清单。

来源：
  * RD 腿：results/gs_compress/evidence/rd/*.json 的 run_dir（legacy baseline runs）；
  * 修复腿：results/dynport_offline/evidence*/manifest*.json 里的 r33 baseline run 引用。

输出 tools/release_asset_runs.txt：每行一个 run 根目录
（相对 monogs-ours 的路径；打包脚本按此裁 {config.yml, plot/trj_full_final.json,
point_cloud/final/*.ply} 三个判据件）。
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "/data/monogs-ours"


def run_root(ref: str) -> str | None:
    """取 run 根（…/results/paper2_fulltable/<rundir>，截到 datasets_bonn 前）。"""
    ref = ref.replace("/home/jiangwenheng/cron/monogs-ours", SRC)
    m = re.search(r"(results/paper2_fulltable/[^/]+)", ref)
    if m:
        return m.group(1)
    m = re.search(r"(results/paper2_fulltable/[^/]+/datasets_[a-z]+/[^/]+/seed_\d+/[\d-]+)", ref)
    return m.group(1) if m else None


def main():
    refs = set()
    for f in glob.glob(os.path.join(ROOT, "results/gs_compress/evidence/rd/*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        for k in ("run_dir", "run"):
            v = d.get(k)
            if isinstance(v, str):
                refs.add(v)
    for f in glob.glob(os.path.join(ROOT, "results/dynport_offline/evidence*/manifest*.json")):
        s = open(f).read()
        for m in re.findall(r'"([^"]*r33_rebase_baseline[^"]*)"', s):
            if "/" in m:
                refs.add(m)
    roots = sorted({r for r in (run_root(x) for x in refs) if r})
    out, missing = [], []
    for r in roots:
        local = os.path.join(SRC, r)
        (out if os.path.isdir(local) else missing).append(r)
    with open(os.path.join(ROOT, "tools/release_asset_runs.txt"), "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"runs={len(out)} missing_on_disk={len(missing)}")
    for r in missing[:10]:
        print("  MISSING:", r)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
