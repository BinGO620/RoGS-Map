#!/usr/bin/env python
"""l1b_readout.py — S3/S4 判读：稳健范围量化的同码率对照（零手抄）。

读 results/gs_compress/evidence/rd/L1B_*.json，按 prereg §10.2 判据机写读表：
  * 每图每码率点：v1（uniform）vs v2（robust+escape / robust+clip）的 rate/PSNR/static/ghost。
  * **同码率匹配**：对每个 v2 点，在 v1 的码率点上做线性内插（rate→PSNR），
    取 |Δrate| ≤ 2% 的最近 v1 点（超 2% 记 unmatched）。
  * 出口判据 R2（先锁）：ΔPSNR = PSNR_v2 − PSNR_v1@matched > 0 ∧ static Δ ≥ −0.3 dB。

输出 evidence/l1b_readout_2026-10-04.md + l1b_readout.json（数字机写）。
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
RD = REPO / "results" / "gs_compress" / "evidence" / "rd"
TAGS = ["L1B_balloon_baseline", "L1B_crowd2_baseline", "L1B_person_tracking2_final"]


def load(tag):
    rows = {}
    for f in sorted(RD.glob(f"{tag}_b*.json")):
        d = json.loads(f.read_text())
        if not d.get("render"):
            continue
        alloc = d.get("alloc")
        esc = d.get("escape")
        if alloc == "uniform":
            key = "v1"
        elif alloc == "robust":
            # 校验 range_mode（否则 alloc=robust 可能来自未预期的路径）
            assert d.get("range_mode") == "robust", f"{f.name}: alloc=robust but range_mode={d.get('range_mode')}"
            key = "v2_esc" if esc else "v2_clip"
        else:
            continue
        rows.setdefault(key, []).append({
            "bits": d.get("bits"), "rate": d["rate_bytes_per_prim"],
            "psnr": d["render"].get("mean_psnr"),
            "static": d["render"].get("mean_static_psnr"),
            "ghost": d["render"].get("mean_ghost_excess_depth_l1_cm"),
        })
    for k in rows:
        rows[k].sort(key=lambda r: r["rate"])
    return rows


def interp_psnr(v1rows, rate):
    """在 v1 的 (rate→psnr) 上线性内插；超出范围返回 None。"""
    xs = np.array([r["rate"] for r in v1rows])
    ys = np.array([r["psnr"] for r in v1rows])
    if rate < xs.min() - 1e-9 or rate > xs.max() + 1e-9:
        return None
    return float(np.interp(rate, xs, ys))


def main():
    out = {"tags": {}, "criteria": {}}
    L = ["# S4 L1B 判读：重尾感知范围量化同码率对照（D2-025 §10，2026-10-04）", "",
         "> **性质**：判据机写（数字来自 `evidence/rd/L1B_*.json`，零手抄）。",
         "> **口径**：同码率对照 = 在每个 v2 点的码率上，对 v1 的 R-D 折线线性内插取 PSNR。",
         "> **判据 R2（prereg §10.2）**：ΔPSNR > 0 且 static Δ ≥ −0.3 dB ⇒ 帕累托。", ""]
    for tag in TAGS:
        rows = load(tag)
        if "v1" not in rows:
            continue
        v1 = rows["v1"]
        out["tags"][tag] = {"v1": v1, "v2_esc": rows.get("v2_esc"), "v2_clip": rows.get("v2_clip")}
        L += [f"## {tag}", "", "### 原始点", "",
              "| arm | bits | rate B/prim | PSNR | static | ghost |", "|---|---|---|---|---|---|"]
        for k in ("v1", "v2_esc", "v2_clip"):
            for r in rows.get(k, []):
                L.append(f"| {k} | {r['bits']} | {r['rate']:.3f} | {r['psnr']:.4f} | "
                         f"{r['static']} | {r['ghost']} |")
        L += ["", "### 同码率匹配（对 v1 折线内插）", "",
              "| arm | bits | rate_v2 | rate_v1@match | Δrate% | PSNR_v1 | PSNR_v2 | **ΔPSNR** | Δstatic |",
              "|---|---|---|---|---|---|---|---|---|"]
        crit = {}
        for k in ("v2_esc", "v2_clip"):
            ds = []
            for r in rows.get(k, []):
                p1 = interp_psnr(v1, r["rate"])
                inside = (r["rate"] <= max(x["rate"] for x in v1) * 1.02 and
                          r["rate"] >= min(x["rate"] for x in v1) * 0.98)
                if p1 is None or not inside:
                    L.append(f"| {k} | {r['bits']} | {r['rate']:.3f} | — | — | — | "
                             f"{r['psnr']:.4f} | **unmatched** | — |")
                    continue
                # 最近 v1 点的 static
                near = min(v1, key=lambda x: abs(x["rate"] - r["rate"]))
                dstat = (r["static"] - near["static"]) if (r["static"] is not None and near["static"] is not None) else None
                d = r["psnr"] - p1
                ds.append(d)
                L.append(f"| {k} | {r['bits']} | {r['rate']:.3f} | {near['rate']:.3f} | "
                         f"{(r['rate']/near['rate']-1)*100:+.1f} | {p1:.4f} | {r['psnr']:.4f} | "
                         f"**{d:+.4f}** | {dstat if dstat is None else f'{dstat:+.3f}'} |")
            if ds:
                crit[k] = {"n_matched": len(ds), "median_dpsnr": float(np.median(ds)),
                           "min_dpsnr": float(min(ds)), "max_dpsnr": float(max(ds)),
                           "all_positive": bool(all(d > 0 for d in ds))}
        out["criteria"][tag] = crit
        L.append("")
        if crit:
            L.append("**小结**：" + "；".join(
                f"{k}: n={v['n_matched']} 中位 ΔPSNR={v['median_dpsnr']:+.4f} "
                f"[{v['min_dpsnr']:+.4f},{v['max_dpsnr']:+.4f}] 全正={v['all_positive']}"
                for k, v in crit.items()))
            L.append("")

    (REPO / "results/gs_compress/evidence/l1b_readout.json").write_text(json.dumps(out, indent=2))
    (REPO / "results/gs_compress/evidence/l1b_readout_2026-10-04.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
