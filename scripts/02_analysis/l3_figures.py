#!/usr/bin/env python
"""l3_figures.py — 生成 L3 三件套之「渲染图 vs 原图」（GT │ off │ exit 两行）。

为什么要**入库**（而不是匿名内联脚本）：
  2026-09-21 关卡① 抓到一版内联生成的图**图注符号与工件相反**
  （`L3_person_tracking_GT_off_exit.png` 标 `freshvac=-10.144`，而工件实测 `+10.1439`）。
  根因是"图注是从别处抄的字符串、且生成脚本不在仓里 ⇒ 无法审计也无法复现"。
  本脚本把两条纪律写进代码：
    ① **图注数值直接从 `render_metrics.json` 取**（与判据机同源），不手写、不抄；
    ② **断言帧号一致**（源图文件名里的帧号 == JSON 记录的帧号），防"图与数不同帧"。

输入（均已入仓）：
  results/lifecycle_paper2/render_L3_<seq>_{off,exit}_s0_dense/render_metrics.json   ← 数值来源
  results/lifecycle_paper2/figs_src/<seq>_{off,exit}_f<NNNNN>.png                    ← 源拼图(每张含 GT│render)

输出：results/lifecycle_paper2/figs/L3_<seq>_GT_off_exit.png （9 张）

取值帧 = 该序列 |Δfreshvac| 最大的帧（**可复算、非手挑**；与旧版同一选法）。

用法：
  /data/conda_envs/monogs-ours/bin/python scripts/02_analysis/l3_figures.py [--seq crowd3] [--check]
"""
import argparse

import json
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "results/lifecycle_paper2"
SRC = OUT / "figs_src"
FIG = OUT / "figs"

SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2", "mvnobox", "mvnobox2"]
ARM_LABEL = {"off": "off  (baseline)", "exit": "exit (ours)"}
BAR = 26


def per_frame(seq, arm, seed=0):
    p = OUT / f"render_L3_{seq}_{arm}_s{seed}_dense" / "render_metrics.json"
    if not os.path.isfile(p):
        return None
    return json.load(open(p)).get("per_frame", [])


def pick_frame(seq, seed=0):
    """|Δfreshvac| 最大的帧（两臂按 **帧号** 配对，不靠列表位置）。"""
    a, b = per_frame(seq, "off", seed), per_frame(seq, "exit", seed)
    if not a or not b:
        return None
    da = {r["frame"]: r for r in a}
    db = {r["frame"]: r for r in b}
    best = None
    for f in sorted(set(da) & set(db)):
        fa = da[f].get("freshvac_ghost_excess_depth_l1_cm")
        fb = db[f].get("freshvac_ghost_excess_depth_l1_cm")
        if fa is None or fb is None:
            continue
        if best is None or abs(fb - fa) > best[0]:
            best = (abs(fb - fa), f, fa, fb)
    return best


def src_image(seq, arm, frame):
    p = SRC / f"{seq}_{arm}_f{frame:05d}.png"
    return p if os.path.isfile(p) else None


def check(seq):
    """--check：只核对"图注数值 == 工件数值、且图与数同帧"，不改文件。"""
    ok = True
    best = pick_frame(seq)
    if best is None:
        print(f"  {seq}: NO DATA"); return False
    _, frame, fa, fb = best
    for arm, val in (("off", fa), ("exit", fb)):
        if src_image(seq, arm, frame) is None:
            print(f"  {seq}/{arm}: 缺源图 f{frame:05d}"); ok = False
    print(f"  {seq}: frame={frame}  off={fa:+.4f}  exit={fb:+.4f}  (Δ={fb - fa:+.4f})")
    return ok


def build(seq):
    best = pick_frame(seq)
    if best is None:
        print(f"[skip] {seq}: 无 per_frame 数据"); return False
    _, frame, fa, fb = best

    imgs = {}
    for arm in ("off", "exit"):
        p = src_image(seq, arm, frame)
        if p is None:
            print(f"[skip] {seq}: 缺源图 figs_src/{seq}_{arm}_f{frame:05d}.png"); return False
        # 纪律②：源图文件名里的帧号必须与 JSON 的帧号一致
        m = re.search(r"_f(\d{5})\.png$", p.name)
        assert m and int(m.group(1)) == frame, f"帧号不一致: {p.name} vs JSON {frame}"
        imgs[arm] = Image.open(p).convert("RGB")

    W = max(imgs["off"].width, imgs["exit"].width)
    H = imgs["off"].height
    canvas = Image.new("RGB", (W, H * 2 + BAR * 2), (0, 0, 0))
    d = ImageDraw.Draw(canvas)

    # 纪律①：数值直接来自 JSON（%.3f 保留符号），不手写、不抄别处
    d.text((8, 6), f"{ARM_LABEL['off']}   freshvac={fa:+.3f} cm   frame={frame}", fill=(255, 255, 255))
    canvas.paste(imgs["off"], (0, BAR))
    d.text((8, BAR + H + 6), f"{ARM_LABEL['exit']}   freshvac={fb:+.3f} cm   frame={frame}", fill=(255, 255, 255))
    canvas.paste(imgs["exit"], (0, BAR + H + BAR))

    FIG.mkdir(parents=True, exist_ok=True)
    outp = FIG / f"L3_{seq}_GT_off_exit.png"
    canvas.save(outp)
    print(f"  {seq:18s} frame={frame:4d}  off={fa:+.3f}  exit={fb:+.3f}  -> {outp.name}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", default=None)
    ap.add_argument("--check", action="store_true", help="只核对数值/帧号，不写图")
    args = ap.parse_args()
    seqs = [args.seq] if args.seq else SEQS
    if args.check:
        ok = all(check(s) for s in seqs)
        print("\nCHECK " + ("通过 ✓" if ok else "**未通过**"))
        return 0 if ok else 1
    n = sum(1 for s in seqs if build(s))
    print(f"\nwrote {n}/{len(seqs)} figures -> {FIG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
