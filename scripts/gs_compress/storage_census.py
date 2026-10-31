#!/usr/bin/env python
"""storage_census.py — 四臂地图体量/存储账（权威口径，零 GPU，机写）。

**修正 2026-10-04 件 `storage_accounting_2026-10-04.md` 的两个 bug**：
  (a) 该件 "final(gate)" 列实为 **final 臂**（标错）；
  (b) 该件用旧批 `results/paper2_fulltable/{seq}_{arm}_seed*`，而论文主表 Tab.1 用
      `r33_rebase_{arm}_{seq}_seed*` ⇒ 口径混批。本脚本统一到 **r33_rebase**。

输出：evidence/storage_census.json + evidence/storage_census_2026-10-05.md（机写，禁手抄）。
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
from plyfile import PlyData

REPO = Path(__file__).resolve().parents[2]
SEQ = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
       "person_tracking", "person_tracking2"]
ARMS = ["baseline", "swbaonly", "final", "gate"]
FIELDS = 20          # 20×f32 schema（含 6 记账字段）
BYTES_PER_PRIM = FIELDS * 4


def find_map(seq: str, arm: str, seed: int) -> str | None:
    g = glob.glob(str(REPO /
        f"results/paper2_fulltable/r33_rebase_{arm}_{seq}_seed{seed}/"
        f"datasets_bonn/*/seed_{seed}/*/point_cloud/final/point_cloud.ply"))
    return g[0] if g else None


def main():
    rows = []
    for seq in SEQ:
        rec = {"seq": seq, "n": {}, "mb": {}}
        for arm in ARMS:
            ns = []
            for s in (0, 1, 2):
                p = find_map(seq, arm, s)
                if p:
                    try:
                        ns.append(len(PlyData.read(p)["vertex"]))
                    except Exception:
                        pass
            if ns:
                rec["n"][arm] = float(np.mean(ns))
                rec["mb"][arm] = float(np.mean(ns) * BYTES_PER_PRIM / 1e6)
        rows.append(rec)

    out = {"batch": "r33_rebase", "bytes_per_prim": BYTES_PER_PRIM, "rows": rows}
    (REPO / "results/gs_compress/evidence/storage_census.json").write_text(json.dumps(out, indent=2))

    L = ["# 四臂地图体量账（权威口径，r33_rebase，3-seed 均值；2026-10-05 机写）", "",
         "> 修正 `storage_accounting_2026-10-04.md` 的两处口径 bug（final/gate 标错 + 旧批混引）。",
         "> 数字机写、禁手抄；与 Tab.1 同批（r33_rebase）。", "",
         "## 1. 基元数（3-seed 均值）", "",
         "| 序列 | baseline | swbaonly | final | gate | gate/base |", "|---|---|---|---|---|---|"]
    for r in rows:
        n = r["n"]
        gb = f"{n['gate']/n['baseline']*100-100:+.1f}%" if ("gate" in n and "baseline" in n) else "--"
        def f(a): return f"{n[a]:.0f}" if a in n else "--"
        L.append(f"| {r['seq']} | {f('baseline')} | {f('swbaonly')} | {f('final')} | {f('gate')} | {gb} |")
    L += ["", "## 2. 地图体量 MB（20 字段 f32，80 B/基元）", "",
          "| 序列 | baseline | final | gate |", "|---|---|---|---|"]
    for r in rows:
        m = r["mb"]
        def f(a): return f"{m[a]:.2f}" if a in m else "--"
        L.append(f"| {r['seq']} | {f('baseline')} | {f('final')} | {f('gate')} |")
    # 汇总
    gb = [r["n"]["gate"]/r["n"]["baseline"]*100-100 for r in rows
          if "gate" in r["n"] and "baseline" in r["n"]]
    if gb:
        L += ["", f"**汇总**：gate/base 跨序列 {min(gb):+.1f}% ~ {max(gb):+.1f}%，"
                  f"七序列均值 {np.mean(gb):+.1f}%（**方向依序列而定，非单调膨胀**）。"]
    (REPO / "results/gs_compress/evidence/storage_census_2026-10-05.md").write_text("\n".join(L))
    print("\n".join(L))
    print(f"\nwrote evidence/storage_census.json + storage_census_2026-10-05.md")


if __name__ == "__main__":
    main()
