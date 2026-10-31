#!/usr/bin/env python
"""l1f_figures.py — L1f 三件套之③「渲染图 vs 原图」（GT │ obsdebt │ exit_fill_ctrl 三行）。

镜像 `l3_figures.py` 的两条纪律（该脚本因"内联生成图注与工件符号相反"事故而立）：
  ① 图注数值**直接从 rescore/render_metrics JSON 取**（与判据机同源），不手写、不抄；
  ② **断言帧号一致**（源图文件名里的帧号 == JSON 记录的帧号），防"图与数不同帧"。

取值帧 = 主参照 m3 上 |Δ| 最大的帧（Δ = obsdebt − exit_fill_ctrl，**可复算，非手挑**）。

输入：
  results/lifecycle_paper2/render_L1f2_balloon2_obsdebt_s{seed}_canon/render_metrics.json
  results/lifecycle_paper2/render_L1f_balloon2_exitfill_ctrl_s{seed}_canon/render_metrics.json
  results/lifecycle_paper2/instrument_v2/rescore/rescore_L1f*_canon.json（m3 逐帧）
  results/lifecycle_paper2/figs_src_l1f/{obsdebt,ctrl}_s<seed>_f<NNNNN>.png（源拼图 GT│render）

输出：results/lifecycle_paper2/figs/L1f_balloon2_GT_obsdebt_ctrl_s<seed>.png

用法：
  /data/conda_envs/monogs-ours/bin/python scripts/02_analysis/l1f_figures.py [--seed 0] [--check]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "results/lifecycle_paper2"
SRC = OUT / "figs_src_l1f"
FIG = OUT / "figs"
RESCORE = OUT / "instrument_v2" / "rescore"

MAIN_RTAG = "L1f2_balloon2_obsdebt_s{seed}"
CTRL_RTAG = "L1f_balloon2_exitfill_ctrl_s{seed}"
BAR = 26
ARM_LABEL = {"obsdebt": "obsdebt (ours)", "ctrl": "exit_fill (control)"}


def _rescore(rtag: str) -> dict | None:
    p = RESCORE / f"rescore_{rtag}_canon.json"
    if not os.path.isfile(p):
        return None
    d = json.load(open(p))
    return {f["frame"]: f for f in d.get("per_frame", [])}


def _metrics(rtag: str) -> dict | None:
    p = OUT / f"render_{rtag}_canon" / "render_metrics.json"
    return json.load(open(p)) if os.path.isfile(p) else None


def pick_frame(seed: int):
    """m3 上 |Δ| 最大的帧（两臂按**帧号**配对，不靠列表位置）。"""
    a, b = _rescore(MAIN_RTAG.format(seed=seed)), _rescore(CTRL_RTAG.format(seed=seed))
    if not a or not b:
        return None
    best = None
    for fr in sorted(set(a) & set(b)):
        va, vb = a[fr].get("exc_m3_cm"), b[fr].get("exc_m3_cm")
        if va is None or vb is None:
            continue
        if best is None or abs(va - vb) > best[0]:
            best = (abs(va - vb), fr, va, vb)
    return best


def src_image(seed: int, arm: str, frame: int):
    p = SRC / f"{arm}_s{seed}_f{frame:05d}.png"
    return p if os.path.isfile(p) else None


def check(seed: int) -> bool:
    best = pick_frame(seed)
    if best is None:
        print(f"  s{seed}: NO DATA")
        return False
    _, frame, va, vb = best
    ok = True
    for arm in ("obsdebt", "ctrl"):
        if src_image(seed, arm, frame) is None:
            print(f"  s{seed}/{arm}: 缺源图 f{frame:05d}")
            ok = False
    print(f"  s{seed}: frame={frame}  obsdebt(m3)={va:+.4f}  ctrl(m3)={vb:+.4f}  (Δ={va - vb:+.4f})")
    return ok


def build(seed: int) -> bool:
    best = pick_frame(seed)
    if best is None:
        print(f"[skip] s{seed}: 无 rescore 数据")
        return False
    _, frame, va, vb = best
    imgs = {}
    for arm in ("obsdebt", "ctrl"):
        p = src_image(seed, arm, frame)
        if p is None:
            print(f"[skip] s{seed}: 缺源图 {SRC.name}/{arm}_s{seed}_f{frame:05d}.png")
            return False
        # 纪律②：源图文件名帧号 == JSON 帧号
        m = re.search(r"_f(\d{5})\.png$", p.name)
        assert m and int(m.group(1)) == frame, f"帧号不一致: {p.name} vs JSON {frame}"
        imgs[arm] = Image.open(p).convert("RGB")

    W = max(imgs["obsdebt"].width, imgs["ctrl"].width)
    H = imgs["obsdebt"].height
    canvas = Image.new("RGB", (W, H * 2 + BAR * 2), (0, 0, 0))
    d = ImageDraw.Draw(canvas)
    # 纪律①：数值直接来自 rescore JSON（%.3f 保留符号），不手写、不抄
    d.text((8, 6), f"{ARM_LABEL['ctrl']}   m3={vb:+.3f} cm   frame={frame}   s{seed}",
           fill=(255, 255, 255))
    canvas.paste(imgs["ctrl"], (0, BAR))
    d.text((8, BAR + H + 6), f"{ARM_LABEL['obsdebt']}   m3={va:+.3f} cm   frame={frame}   "
                            f"Δ(obsdebt−ctrl)={va - vb:+.3f} cm", fill=(255, 255, 255))
    canvas.paste(imgs["obsdebt"], (0, BAR + H + BAR))

    FIG.mkdir(parents=True, exist_ok=True)
    outp = FIG / f"L1f_balloon2_GT_obsdebt_ctrl_s{seed}.png"
    canvas.save(outp)
    print(f"  s{seed}  frame={frame:4d}  obsdebt={va:+.3f}  ctrl={vb:+.3f}  -> {outp.name}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--check", action="store_true", help="只核对数值/帧号，不写图")
    args = ap.parse_args()
    seeds = [args.seed] if args.seed is not None else [0, 1, 2]
    if args.check:
        ok = all(check(s) for s in seeds)
        print("\nCHECK " + ("通过 ✓" if ok else "**未通过**"))
        return 0 if ok else 1
    n = sum(1 for s in seeds if build(s))
    print(f"\nwrote {n}/{len(seeds)} figures -> {FIG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
