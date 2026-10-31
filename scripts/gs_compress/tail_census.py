#!/usr/bin/env python
"""tail_census.py — S0 重尾普查（零 GPU，go/no-go）D2-025 乙线。

动机：codec v1 每属性组用**全局 min/max** 范围做均匀标量量化（`gs_codec.py` encode：
`lo, hi = arr.min(), arr.max()`）。SLAM 生长地图运行期**无尺度护栏**
（`gaussian_model.py:982` 只剔 Inf/NaN），可能长出少量"巨基元/浮子"把整组范围撑大 ⇒
所有基元的量化步长被拖粗。本普查量化该"范围膨胀"：

对每张地图、每个属性组（xyz/f_dc/opacity/scale/rot3）：
  * span_full = max - min（codec 现用范围）
  * span_pXX  = p(100-q) - p(q)（稳健范围，q=0.1/0.01）
  * inflation = span_full / span_pXX   （>1 表示尾部把范围撑大）
  * headroom_dB = 20*log10(inflation)  （若尾部可"免费"处理的 PSNR 上限）
  * tail_frac = 落在稳健范围外的基元占比
  * 尾部成员与 opacity / scale 的关系（是否=巨基元）

输出：evidence/tail_census.json + evidence/tail_census_2026-10-04.md（数字机写，禁手抄）。
零 GPU、只读 PLY。放 GPU 之前先提交本脚本。
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np
from plyfile import PlyData

REPO = Path(__file__).resolve().parents[2]

GROUPS = {
    "xyz": ["x", "y", "z"],
    "f_dc": ["f_dc_0", "f_dc_1", "f_dc_2"],
    "opacity": ["opacity"],
    "scale": ["scale_0", "scale_1", "scale_2"],
    "rot3": ["rot_1", "rot_2", "rot_3"],
}
# 每属性组的量化位宽（L1/L2 近无损工作点 16/8/8/8/8）
BITS = {"xyz": 16, "f_dc": 8, "opacity": 8, "scale": 8, "rot3": 8}

SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2"]


def find_ply(seq: str, arm: str, seed: int) -> str | None:
    pat = (f"results/paper2_fulltable/{seq}_{arm}_seed{seed}/datasets_bonn/*/"
           f"seed_{seed}/*/point_cloud/final/point_cloud.ply")
    g = glob.glob(str(REPO / pat))
    return g[0] if g else None


def group_array(arrs: dict, comps: list[str]) -> np.ndarray:
    return np.stack([arrs[c] for c in comps], 1).astype(np.float64)  # (N, k)


def census_one(ply: str) -> dict:
    v = PlyData.read(ply)["vertex"]
    names = {p.name for p in v.properties}
    arrs = {c: np.asarray(v[c], dtype=np.float64) for c in
            [x for comps in GROUPS.values() for x in comps] if c in names}
    s = np.stack([arrs["scale_0"], arrs["scale_1"], arrs["scale_2"]], 1)
    smax = s.max(1)                      # log 域最大轴
    op = 1.0 / (1.0 + np.exp(-arrs["opacity"]))  # sigmoid ⇒ 渲染不透明度

    out = {"ply": str(Path(ply).relative_to(REPO)), "n": int(len(v)), "groups": {}}
    for gname, comps in GROUPS.items():
        if any(c not in arrs for c in comps):
            continue
        a = group_array(arrs, comps).ravel()
        lo_f, hi_f = float(a.min()), float(a.max())
        span_full = hi_f - lo_f
        rec = {"bits": BITS[gname], "span_full": span_full,
               "min": lo_f, "max": hi_f}
        for q in (0.1, 0.01, 0.001):
            plo, phi = np.percentile(a, q), np.percentile(a, 100 - q)
            span_r = float(phi - plo)
            infl = span_full / span_r if span_r > 0 else float("inf")
            tail = a < plo
            tail |= a > phi
            rec[f"q{q}"] = {
                "span_robust": span_r, "inflation": infl,
                "headroom_dB": (20 * np.log10(infl)) if infl > 0 else 0.0,
                "tail_frac": float(tail.mean()),
                "step_full": span_full / (2 ** BITS[gname] - 1),
                "step_robust": span_r / (2 ** BITS[gname] - 1),
            }
        out["groups"][gname] = rec

    # 最极端基元（按 scale 最大轴）与尾部重合度：尾部是否 = 巨基元
    a_xyz = group_array(arrs, GROUPS["xyz"])
    plo, phi = np.percentile(a_xyz, 0.1), np.percentile(a_xyz, 99.9)
    xyz_tail = ((a_xyz < plo) | (a_xyz > phi)).any(1)
    top_sc = np.argsort(smax)[-100:]
    out["tail_vs_giant"] = {
        "n_xyz_tail": int(xyz_tail.sum()),
        "median_smax_tail": float(np.median(smax[xyz_tail])) if xyz_tail.any() else None,
        "median_smax_non": float(np.median(smax[~xyz_tail])) if (~xyz_tail).any() else None,
        "median_opa_tail": float(np.median(op[xyz_tail])) if xyz_tail.any() else None,
        "median_opa_non": float(np.median(op[~xyz_tail])) if (~xyz_tail).any() else None,
        "top100_scale_overlap_tail": int(xyz_tail[top_sc].sum()),
        "max_smax_m": float(np.exp(smax.max())),
        "p999_smax_m": float(np.exp(np.percentile(smax, 99.9))),
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--out-json", default="results/gs_compress/evidence/tail_census.json")
    ap.add_argument("--out-md", default="results/gs_compress/evidence/tail_census_2026-10-04.md")
    args = ap.parse_args()
    seeds = [int(x) for x in args.seeds.split(",")]

    maps = []
    for seq in SEQS:
        for arm in ["baseline", "final"]:
            for seed in seeds:
                p = find_ply(seq, arm, seed)
                if p is None:
                    print(f"[tail_census] MISS {seq}/{arm}/s{seed}")
                    continue
                r = census_one(p)
                r.update({"seq": seq, "arm": arm, "seed": seed})
                maps.append(r)
                g = r["groups"]
                print(f"[tail_census] {seq:16s} {arm:8s} n={r['n']:6d} "
                      f"xyz.infl(q0.1)={g['xyz']['q0.1']['inflation']:.4f} "
                      f"scale.infl={g['scale']['q0.1']['inflation']:.4f}")

    res = {"n_maps": len(maps), "seeds": seeds, "maps": maps}
    (REPO / args.out_json).parent.mkdir(parents=True, exist_ok=True)
    (REPO / args.out_json).write_text(json.dumps(res, indent=2))

    # ---- markdown（机写）----
    L = ["# S0 重尾普查（tail census）— D2-025 乙线（零 GPU，2026-10-04）", "",
         "> **性质**：零 GPU 工件普查（逐 PLY 实测）；数字机写、禁手抄。",
         "> **问题**：codec v1 用全局 min/max 范围量化；若 SLAM 地图有重尾（巨基元/浮子），",
         "> 尾部撑大 span ⇒ 全体量化步长变粗。本表量化该膨胀。", "",
         f"seeds={seeds}｜maps={len(maps)}", "",
         "## 1. 逐图范围膨胀（q=0.1% 稳健范围 vs 全局范围）", "",
         "| seq | arm | n | xyz infl | f_dc | opacity | scale | rot3 |",
         "|---|---|---|---|---|---|---|---|"]
    for m in maps:
        g = m["groups"]
        def v(k):
            return f"{g[k]['q0.1']['inflation']:.3f}" if k in g else "-"
        L.append(f"| {m['seq']} | {m['arm']} | {m['n']} | {v('xyz')} | {v('f_dc')} | "
                 f"{v('opacity')} | {v('scale')} | {v('rot3')} |")
    L += ["", "**infl** = `span_full / span_p0.1`（1.00 = 无膨胀；>1 表示尾部把范围撑大）。", "",
          "## 2. 上限收益（headroom_dB = 20·log10(infl)；若尾部可免费处理）", "",
          "| seq | arm | xyz | f_dc | opacity | scale | rot3 |",
          "|---|---|---|---|---|---|---|"]
    for m in maps:
        g = m["groups"]
        def d(k):
            return f"{g[k]['q0.1']['headroom_dB']:.3f}" if k in g else "-"
        L.append(f"| {m['seq']} | {m['arm']} | {d('xyz')} | {d('f_dc')} | "
                 f"{d('opacity')} | {d('scale')} | {d('rot3')} |")
    L += ["", "## 3. 尾部 vs 巨基元（xyz 尾 vs scale 最大轴）", "",
          "| seq | arm | n_tail | s_max(tail) | s_max(non) | opa(tail) | opa(non) | top100∩tail | max m | p99.9 m |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for m in maps:
        t = m["tail_vs_giant"]
        L.append(f"| {m['seq']} | {m['arm']} | {t['n_xyz_tail']} | "
                 f"{t['median_smax_tail']} | {t['median_smax_non']} | "
                 f"{t['median_opa_tail']} | {t['median_opa_non']} | "
                 f"{t['top100_scale_overlap_tail']} | {t['max_smax_m']:.3f} | "
                 f"{t['p999_smax_m']:.4f} |")
    L += ["", "> `s_max` = 最大轴 log-scale（**log 域**，越大=基元越大）；`max m`/`p99.9 m` 为 exp 后（米）。",
          "> `top100∩tail` = 最大 100 个基元落在 xyz 尾部内的个数（>0 ⇒ 尾部含巨基元）。", ""]
    (REPO / args.out_md).write_text("\n".join(L))
    print(f"[tail_census] wrote {args.out_json} + {args.out_md}")


if __name__ == "__main__":
    main()
