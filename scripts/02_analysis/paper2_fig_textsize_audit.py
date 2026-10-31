#!/usr/bin/env python
"""paper2_fig_textsize_audit.py — 论文 2 图内字号门（可复跑，G2-C1/M3 固化）。

存在理由（2026-10-09 G2-C1）：曾以**错栏宽**声称"全图字号 ≥5pt"，实测单栏图
（fig3/4/5，`figure` 环境，栏宽 3.28in）native 远大于栏宽 ⇒ 被缩小打印，fig4 字实印
仅 2.71–4.64pt。本脚本按**真实排版栏宽**复算每图的有效印刷字号。

口径：
  - 双栏图 = `figure*` ⇒ 槽宽 = textwidth(6.875in) × width 系数；
  - 单栏图 = `figure`  ⇒ 槽宽 = (textwidth − columnsep) / 2 = 3.28125in × 系数；
  - 缩放 = 槽宽 / native 宽；有效字号 = PDF 内嵌最小字号 × 缩放；
  - README 规约：图内正文 ≥ 5pt（保守下限；Nature 常用 5–7pt）。

用法：python scripts/02_analysis/paper2_fig_textsize_audit.py [--min-pt 5.0]
输出：逐图 (环境, native, 槽宽, 缩放, 内嵌最小, 有效最小) + PASS/FAIL；退出码 0/1。
"""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# 2026-10-10 重写重构：v0 tex 已归档；活副本优先，否则用归档副本（重写期守护不空转）。
_TEX_LIVE = REPO / "papers/paper2/paper2_cvm.tex"
TEX = _TEX_LIVE if _TEX_LIVE.exists() else REPO / "papers/paper2/archive/v0_2026-10-10/paper2_cvm.tex"
PAPER_FIGS = REPO / "papers/paper2/figs"

TEXTWIDTH_IN = 6.875
COLUMNSEP_IN = 0.3125
IN_TO_PT = 72.0


def figure_envs():
    """从 tex 解析 {includegraphics_name: (env, width_coeff)}。"""
    s = TEX.read_text()
    out = {}
    for m in re.finditer(r"\\begin\{(figure\*?)\}\[t\](.*?)\\end\{\1\}", s, re.S):
        env, body = m.group(1), m.group(2)
        inc = re.search(r"\\includegraphics(?:\[(.*?)\])?\{([^}]+)\}", body)
        if not inc:
            continue
        opts, name = inc.group(1) or "", inc.group(2)
        wm = re.search(r"width\s*=\s*([\d.]+)\\(?:line)?width", opts or "")
        coeff = float(wm.group(1)) if wm else 1.0
        out[name] = (env, coeff)
    return out


def slot_pt(env, coeff):
    col = (TEXTWIDTH_IN - COLUMNSEP_IN) / 2
    base = TEXTWIDTH_IN if env == "figure*" else col
    return base * coeff * IN_TO_PT


def native_pt(pdf):
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    line = [l for l in info.split("\n") if "Page size" in l][0]
    return float(line.split()[2])


def min_text_pt(pdf):
    """PDF 内嵌最小字号（PyMuPDF spans）。"""
    import pymupdf
    doc = pymupdf.open(str(pdf))
    sizes = []
    for page in doc:
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for sp in l.get("spans", []):
                    if sp.get("text", "").strip():
                        sizes.append(round(sp["size"], 2))
    doc.close()
    return min(sizes) if sizes else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-pt", type=float, default=5.0)
    args = ap.parse_args()
    envs = figure_envs()
    rows, fails = [], []
    for name, (env, coeff) in sorted(envs.items()):
        pdf = PAPER_FIGS / name
        if not pdf.exists():
            continue
        nat = native_pt(pdf)
        slot = slot_pt(env, coeff)
        scale = slot / nat
        emb = min_text_pt(pdf)
        eff = None if emb is None else emb * min(scale, 1.0)
        status = "-"
        if eff is not None:
            status = "PASS" if eff >= args.min_pt else "FAIL"
            if status == "FAIL":
                fails.append((name, eff))
        rows.append((name, env, nat, slot, scale, emb, eff, status))
    print(f"{'figure':32s} {'env':9s} {'native':>7s} {'slot':>7s} {'scale':>6s} "
          f"{'emb':>5s} {'eff':>5s}  status")
    for name, env, nat, slot, scale, emb, eff, status in rows:
        e = f"{eff:.2f}" if eff is not None else "  - "
        b = f"{emb:.2f}" if emb is not None else "  - "
        print(f"{name:32s} {env:9s} {nat:7.1f} {slot:7.1f} {scale:6.2f} "
              f"{b:>5s} {e:>5s}  {status}")
    print(f"\nmin effective = {args.min_pt} pt | fails: {len(fails)}")
    for name, eff in fails:
        print(f"  FAIL {name}: effective {eff:.2f} pt")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
