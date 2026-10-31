#!/usr/bin/env python
"""paper2_codec_tables.py — 生成论文2 §5.2/§5.3 的表（R-D 主表 + 存储账）。

读已过工件：
  * R-D 主表：results/gs_compress/evidence/rd/l2_summary.json（L2 42 图）
              + rd/L3_*.json 聚合（泛化 36 图）
              + rd/raw_zlib_baseline.json（朴素无损基线，独立审稿 P0-1）
              + rd/L2_*_baseline.json / L3_*_baseline.json（源地图渲染 PSNR 上界）
  * 存储账：results/gs_compress/evidence/storage_census.json（权威口径）

输出：results/paper2_fulltable/evidence/latex/tab_rd.tex, tab_storage.tex
（\input 解锁前须过关卡②；本脚本产物随 evidence/latex 入库。）
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
RD = REPO / "results/gs_compress/evidence/rd"
EV = REPO / "results/paper2_fulltable/evidence"
OUT = EV / "latex"
OUT.mkdir(parents=True, exist_ok=True)

WP = [("16,8,8,8,8", "near_lossless"), ("10,6,6,6,6", "mid"), ("8,4,4,4,4", "aggressive")]
WP_LABEL = {"near_lossless": "near-lossless", "mid": "mid", "aggressive": "aggressive"}


def _wp_tag(bits_csv):
    return "b" + "-".join(bits_csv.split(","))


def l2_row(name):
    """从 l2_summary.json 聚合该工作点（键 = near_lossless/mid/aggressive）。"""
    d = json.loads((RD / "l2_summary.json").read_text())
    ratios, psnrs = [], []
    for k, v in d.items():
        w = v.get(name) if isinstance(v, dict) else None
        if w:
            ratios.append(w.get("ratio_full")); psnrs.append(w.get("psnr"))
    return ratios, psnrs


def l3_row(bits_csv):
    """从 L3_*_rd_table.json 聚合泛化工作点。"""
    tag = _wp_tag(bits_csv)
    ratios, psnrs = [], []
    for f in RD.glob("L3_*_rd_table.json"):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for r in d.get("rows", []):
            if not r.get("render"):
                continue
            if r.get("bits") == [int(x) for x in bits_csv.split(",")]:
                ratios.append(r.get("ratio_full")); psnrs.append(r["render"].get("mean_psnr"))
    return ratios, psnrs


def src_psnr(split):
    """源（未压缩）地图的渲染 PSNR 上界，用于给 codec 行定位。"""
    pat = "L2_*_baseline.json" if split == "L2" else "L3_*_baseline.json"
    ps = []
    for f in RD.glob(pat):
        try:
            r = json.loads(f.read_text()).get("render")
        except Exception:
            r = None
        if r and r.get("mean_psnr"):
            ps.append(r["mean_psnr"])
    return float(np.mean(ps)) if ps else float("nan")


def rawzlib_row(split):
    """朴素无损基线（raw zlib）。split ∈ {L2, L3}。"""
    d = json.loads((RD / "raw_zlib_baseline.json").read_text())
    s = d.get(split, {})
    return s.get("ratio_soa_mean", float("nan")), s.get("ratio_aos_mean", float("nan"))


def l2s_row(name):
    """体素合并消融行（L2S 批，verdict_struct_codec_2026-10-05.md：C1 半过 ⇒ 消融非主表）。"""
    d = json.loads((RD / "l2s_summary.json").read_text())
    ratios, psnrs = [], []
    for k, v in d.items():
        w = v.get(name) if isinstance(v, dict) else None
        if w:
            ratios.append(w.get("ratio_full")); psnrs.append(w.get("psnr"))
    return (float(np.mean(ratios)) if ratios else float("nan"),
            float(np.mean(psnrs)) if psnrs else float("nan"))


def _src_static():
    ps = []
    for f in RD.glob("L2_*_baseline.json"):
        r = json.loads(f.read_text()).get("render", {})
        if r.get("mean_static_psnr"):
            ps.append(r["mean_static_psnr"])
    return float(np.mean(ps)) if ps else float("nan")


def _posthoc(split):
    """后处理通用基线（posthoc_baselines.json）。返回 {key: mean ratio}。"""
    p = RD / "posthoc_baselines.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text())["splits"].get(split, {}).get("summary", {})
    return {k: v["mean"] for k, v in d.items() if isinstance(v, dict)}


def _learned(fname):
    """learned 压缩器基线聚合（方案 A′）：读 rd/<fname>（learned_sog_L2.json 等）。
    返回 {row_key: {ratio, psnr, static, n}}；文件缺失 ⇒ {}（表中该组自动省略）。"""
    p = RD / fname
    if not p.exists():
        return {}
    rows = json.loads(p.read_text())["rows"]
    out = {}
    for r in rows:
        key = r.get("config") or f"iters{r.get('finetune_iters')}"
        e = out.setdefault(key, {"ratio": [], "psnr": [], "static": []})
        e["ratio"].append(r["ratio_full"])
        if r.get("render"):
            if r["render"].get("mean_psnr") is not None:
                e["psnr"].append(r["render"]["mean_psnr"])
            if r["render"].get("mean_static_psnr") is not None:
                e["static"].append(r["render"]["mean_static_psnr"])
    return {k: {"ratio": float(np.mean(v["ratio"])),
                "psnr": float(np.mean(v["psnr"])) if v["psnr"] else float("nan"),
                "static": float(np.mean(v["static"])) if v["static"] else float("nan"),
                "n": len(v["ratio"])} for k, v in out.items()}


def _l2_rate(name):
    rates = [v[name]["rate"] for v in json.loads((RD / "l2_summary.json").read_text()).values()
             if name in v]
    return float(np.mean(rates)) if rates else float("nan")


def build_tab_rd():
    src2, src3 = src_psnr("L2"), src_psnr("L3")
    src_static = _src_static()
    ph2, ph3 = _posthoc("L2"), _posthoc("L3")
    BPP_SRC = 80.0  # 20 fields x f32
    PB = {  # 每工作点的量化位宽标签
        "near_lossless": "16/8/8/8/8", "mid": "10/6/6/6/6", "aggressive": "8/4/4/4/4",
    }
    HDR = ("Method & quant. & comp. & B/prim & full PSNR & $\\Delta$ & static PSNR & held-out $\\Delta$ \\\\")
    L = ["% generated by scripts/gs_compress/paper2_codec_tables.py -- do not edit by hand",
         "% provenance: rd/{l2_summary.json, l2s_summary.json, L3_*, L2_*_baseline.json,"
         " posthoc_baselines.json, learned_sog_L*.json, learned_nied_L*.json}; D2-025 L1/L2/L3"
         " + P0-1 + post-hoc generic + learned baselines",
         "\\begin{table*}",
         "\\begin{center}",
         "\\footnotesize",
         "% 行距压紧：14 页硬顶由本 float 高度支配（2026-10-16 加 Niedermayr 行后实测 15 页 ⇒ 压回 14）",
         "\\renewcommand{\\arraystretch}{0.87}",
         "\\setlength{\\tabcolsep}{4pt}",
         "\\begin{tabular}{@{}lcccrccr@{}}",
         "\\toprule",
         HDR,
         "\\midrule",
         "\\multicolumn{8}{@{}l}{\\emph{Source and lossless generic compressors}} \\\\",
         f"\\quad source (uncompressed, 20-field f32) & -- & 1.00$\\times$ & {BPP_SRC:.0f} & "
         f"{src2:.2f} & $0.00$ & {src_static:.2f} & $0.00$ \\\\"]
    # lossless 带（同分母 n*20*4；渲染逐位不变 ⇒ PSNR = 源值）
    for label, key, split_key in (("\\quad zlib", "zlib", None),
                                  ("\\quad zstd", "zstd", None),
                                  ("\\quad lzma", "lzma", None),
                                  ("\\quad blosc2 (shuffle+delta)", "blosc2", None)):
        r2 = ph2.get(f"ratio_{key}")
        if r2 is None:
            continue
        L.append(f"{label} (lossless) & -- & {r2:.2f}$\\times$ & {BPP_SRC/r2:.1f} & "
                 f"{src2:.2f} & $0.00$ & {src_static:.2f} & $0.00$ \\\\")
    # 通用「数值感知有损」+ learned 基线带（2026-10-15/16，审稿 R4-P3）：
    # blosc2 TRUNC 两档 rate-only（质量未测 ⇒ '--'）；SOG（ECCV'24，§2 已引）为 post-hoc
    # learned 对照（官方非排序通路、无训练、同分母含记账 6 字段 lzma 旁路）。
    # 页码硬顶 14：learned 行并入本组以控制 table* 高度（独立组头会顶破一页，2026-10-16 实测）。
    L.append("\\midrule")
    L.append("\\multicolumn{8}{@{}l}{\\emph{Lossy baselines: generic (rate only) and post-hoc learned}} \\\\")
    for label, key in (("\\quad blosc2 TRUNC\\_PREC=16", "blosc2_trunc16"),
                       ("\\quad blosc2 TRUNC\\_PREC=8", "blosc2_trunc8")):
        r2 = ph2.get(f"ratio_{key}")
        if r2 is None:
            continue
        L.append(f"{label} (lossy) & -- & {r2:.2f}$\\times$ & {BPP_SRC/r2:.1f} & "
                 f"-- & -- & -- & -- \\\\")
    sog2, sog3 = _learned("learned_sog_L2.json"), _learned("learned_sog_L3.json")
    learned_note = ""
    e2 = sog2.get("jxl_quant")
    if e2:
        p3 = (sog3.get("jxl_quant") or {}).get("psnr", float("nan"))
        L.append(f"\\quad SOG (JXL, quantised) & -- & {e2['ratio']:.2f}$\\times$ & "
                 f"{BPP_SRC/e2['ratio']:.1f} & {e2['psnr']:.2f} & ${e2['psnr']-src2:+.2f}$ & "
                 f"{e2['static']:.2f} & ${p3-src3:+.2f}$ \\\\")
        learned_note = ("SOG shares the denominator and instrument, its bookkeeping fields "
                        "carried losslessly (\\S\\ref{sec:codec}). ")
    # Niedermayr c3dgs（CVPR'24）第二 learned 基线（2026-10-16，exp52）：其链路 = 以冻结地图为
    # 初始化 + 5000 步 QAT 渲染监督微调 ⇒ 属「重训再压」，解码图会再拟合（Δ 可为正）。同分母、同仪器。
    # 门禁：**行数必须覆盖整个 split**，否则不入表——部分结果（本机/远程中断的中间产物）的均值有偏。
    nied2, nied3 = _learned("learned_nied_L2.json"), _learned("learned_nied_L3.json")
    n2 = nied2.get("iters5000")
    if n2:
        exp2 = len(list(RD.glob("L2_*_rd_table.json")))
        exp3 = len(list(RD.glob("L3_*_rd_table.json")))
        n3 = nied3.get("iters5000") or {}
        if n2["n"] != exp2 or n3.get("n") != exp3:
            print(f"WARN: learned_nied 不完整（L2 {n2['n']}/{exp2}，L3 {n3.get('n')}/{exp3}）"
                  f" ⇒ 该行不入表（部分结果不得进 Table 4）", file=sys.stderr)
        else:
            p3 = n3.get("psnr", float("nan"))
            L.append(f"\\quad Niedermayr c3dgs (QAT 5k) & -- & {n2['ratio']:.2f}$\\times$ & "
                     f"{BPP_SRC/n2['ratio']:.1f} & {n2['psnr']:.2f} & ${n2['psnr']-src2:+.2f}$ & "
                     f"{n2['static']:.2f} & ${p3-src3:+.2f}$ \\\\")
            learned_note += ("The Niedermayr row is refit, not post-hoc; its reference "
                             "implementation seeds nothing, so per-map values are not reproducible "
                             "beyond $\\approx$0.1\\,dB (\\S\\ref{sec:codec}). ")
    L += ["\\midrule",
          "\\multicolumn{8}{@{}l}{\\emph{This paper: uniform quantisation + zlib codec (lossy)}} \\\\"]
    for bits, name in WP:
        r2, p2 = l2_row(name)
        r3, p3 = l3_row(bits)
        ratio = float(np.mean(r2)) if r2 else float("nan")
        pn2 = float(np.mean(p2)) if p2 else float("nan")
        pn3 = float(np.mean(p3)) if p3 else float("nan")
        rate = _l2_rate(name)
        L.append(f"\\quad \\textbf{{{WP_LABEL[name]}}} & {PB[name]} & {ratio:.2f}$\\times$ & {rate:.1f} & "
                 f"{pn2:.2f} & ${pn2-src2:+.2f}$ & {_wp_static(name):.2f} & ${pn3-src3:+.2f}$ \\\\")
    L.append("\\midrule")
    L.append("\\multicolumn{8}{@{}l}{\\emph{Ablation: + voxel merge (not an operating point)}} \\\\")
    for name in ("near_lossless", "mid", "aggressive"):
        r2, p2 = l2s_row(name)
        if not np.isnan(r2):
            L.append(f"\\quad {WP_LABEL[name]} + voxel merge & {PB[name]} & {r2:.2f}$\\times$ & "
                     f"{BPP_SRC/r2:.1f} & {p2:.2f} & ${p2-src2:+.2f}$ & -- & -- \\\\")
    L += ["\\bottomrule", "\\end{tabular}", "\\end{center}",
          "\\caption{Rate--distortion on the frozen dynamic-scene maps (seven Bonn sequences, "
          "baseline and final arms, three seeds) and an unseen held-out panel (five TUM "
          "sequences, one Bonn). Compression ratio is the mean over per-map ratios "
          "in each group; compression is the source 20-field f32 map size over the "
          "stored bitstream; B/prim is bytes per primitive; PSNR is rendered full-image "
          "(static = static region); $\\Delta$ is the change from the source (negative = "
          "loss), held-out $\\Delta$ on the held-out panel. Lossless compressors render "
          "identically to the source, bounding only the free ratio ($\\approx1.4$--"
          "$1.6\\times$); the gain above them is from quantisation, not entropy coding. The "
          "codec is lossy and parameter-free. The blosc2 rows are rate-only (rendered "
          "quality not measured). "
          + learned_note
          + "Voxel-merge rows are an ablation, not operating points "
          "(+26--31\\% ratio at 0.02--0.07\\,dB mean loss).}",
          "\\label{tab:rd}", "\\end{table*}"]
    (OUT / "tab_rd.tex").write_text("\n".join(L))


def _wp_static(name):
    ss = [v[name]["static_psnr"] for v in json.loads((RD / "l2_summary.json").read_text()).values()
          if name in v and "static_psnr" in v[name]]
    return float(np.mean(ss)) if ss else float("nan")


def build_tab_storage():
    d = json.loads((REPO / "results/gs_compress/evidence/storage_census.json").read_text())
    rows = d["rows"]
    L = ["% generated by scripts/gs_compress/paper2_codec_tables.py -- do not edit by hand",
         "% provenance: results/gs_compress/evidence/storage_census.json (same-batch r33_rebase)",
         "\\begin{table}",
         "\\begin{center}",
         "\\footnotesize",
         "\\begin{tabular}{@{}lccc@{}}",
         "\\toprule",
         "Sequence & Base (MB) & Gate (MB) & Gate/Base \\\\",
         "\\midrule"]
    gbs = []
    for r in rows:
        m = r["mb"]
        if "baseline" in m and "gate" in m:
            gb = m["gate"] / m["baseline"] * 100 - 100
            gbs.append(gb)
            L.append(f"{r['seq'].replace('_', chr(92)+'_')} & {m['baseline']:.2f} & "
                     f"{m['gate']:.2f} & {gb:+.1f}\\% \\\\")
    L += ["\\bottomrule", "\\end{tabular}", "\\end{center}",
          f"\\caption{{Map size per sequence across the same-batch arms (20-field f32, "
          f"80\\,B/primitive). The gate/base ratio is sign-ambiguous across sequences "
          f"({min(gbs):+.1f}\\% to {max(gbs):+.1f}\\%); we report the interval, not a mean "
          f"over a sign-mixed distribution.}}",
          "\\label{tab:storage}", "\\end{table}"]
    (OUT / "tab_storage.tex").write_text("\n".join(L))


if __name__ == "__main__":
    build_tab_rd()
    build_tab_storage()
    print("wrote", OUT / "tab_rd.tex", "and", OUT / "tab_storage.tex")
    print(open(OUT / "tab_rd.tex").read())
    print(open(OUT / "tab_storage.tex").read())
