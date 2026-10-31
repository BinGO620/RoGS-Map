#!/usr/bin/env python
"""fig_render_compare.py — 论文用「GT | render」定性对比图拼装（CPU，无 GPU）。

复用已有 `render_compare/<tag>_*/cmp_f*.png`（每张 = [GT | render] 横向拼图），
按 **行 = GT/baseline/gate 等臂、列 = 帧** 拼成一张论文级对比图。
不重渲染——只读现有产物。

输出：`results/paper2_fulltable/evidence/fig_render_compare_<seq>.png`

用法：
  /data/conda_envs/monogs-ours/bin/python scripts/02_analysis/fig_render_compare.py \
      --seq crowd2 --arms baseline gate --frames 3 --seed 0
"""
import argparse
import glob
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
os.chdir(REPO)
ROOT = Path("results/paper2_fulltable/render_compare")

ARM_LABEL = {"baseline": "baseline\n(base stack,\n2 layers off)",
             "swbaonly": "+SWBA", "final": "+SWBA+LC",
             "gate": "gate (ours)"}

DEFAULT_CAPTION = (
    "GT row = ground truth (dynamic objects present); render rows = reconstruction.  "
    "Dynamic objects are masked out in BOTH render arms:\n"
    "they either vanish or leave a ghost — a KNOWN limitation inherited from the base stack "
    "(present in baseline and ours alike), not a defect of the\n"
    "proposed components and not a claim of this paper.  "
    "baseline = the base stack (only the SWBA / gate layers OFF) — NOT a weak baseline; "
    "arms differ\nmainly in tracking (ATE); the render side is 'non-degradation' evidence (see §4.4)."
)


def find_cmp(arm, seq, seed):
    base = ROOT
    hits = []
    for ext in ("png", "jpg"):
        hits += sorted(base.glob(f"r33_rebase_{arm}_{seq}_seed{seed}_*/cmp_f*.{ext}"))
        hits += sorted(base.glob(f"r33_rebase_{arm}_{seq}_seed{seed}/cmp_f*.{ext}"))
    return hits


def split_gt_render(path):
    """cmp 图 = [GT | render] 横向拼图 -> 返回 (gt, render)。"""
    im = np.asarray(Image.open(path).convert("RGB"))
    h, w = im.shape[:2]
    return im[:, : w // 2], im[:, w // 2:]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seq", required=True)
    ap.add_argument("--arms", nargs="+", default=["baseline", "gate"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--frames", type=int, default=3, help="取几帧（均匀抽）")
    ap.add_argument("--caption", default=DEFAULT_CAPTION, help="底部说明（诚实标注局限）")
    ap.add_argument("--no-caption", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    per_arm = {a: find_cmp(a, args.seq, args.seed) for a in args.arms}
    for a, fs in per_arm.items():
        if not fs:
            raise SystemExit(f"no cmp images for arm={a} seq={args.seq} seed={args.seed}")
    n = min(len(fs) for fs in per_arm.values())
    idx = np.linspace(0, n - 1, min(args.frames, n), dtype=int)

    rows = ["GT"] + [ARM_LABEL.get(a, a) for a in args.arms]
    footer = 0.16 if (args.caption and not args.no_caption) else 0.0
    fig, axes = plt.subplots(len(rows), len(idx),
                             figsize=(3.2 * len(idx), 2.4 * len(rows) + 2.0 * footer))
    axes = np.atleast_2d(axes)
    for c, fi in enumerate(idx):
        gt, _ = split_gt_render(per_arm[args.arms[0]][fi])
        axes[0, c].imshow(gt); axes[0, c].set_axis_off()
        if c == 0:
            axes[0, c].set_title(f"{args.seq}", fontsize=9)
        frame_tag = os.path.splitext(os.path.basename(per_arm[args.arms[0]][fi]))[0].replace("cmp_f", "")
        axes[0, c].text(0.5, -0.06, f"frame {frame_tag}", transform=axes[0, c].transAxes,
                        ha="center", va="top", fontsize=7, color="0.35")
        for r, a in enumerate(args.arms, start=1):
            _, ren = split_gt_render(per_arm[a][fi])
            axes[r, c].imshow(ren); axes[r, c].set_axis_off()
    for r, lab in enumerate(rows):
        axes[r, 0].text(-0.05, 0.5, lab, transform=axes[r, 0].transAxes,
                        ha="right", va="center", fontsize=8.5)
    fig.suptitle(f"GT vs render — {args.seq} (seed {args.seed}, R33 same-batch, offline protocol)",
                 fontsize=10)
    if footer:
        fig.text(0.5, 0.01, args.caption, ha="center", va="bottom", fontsize=7.5,
                 color="0.25", linespacing=1.5)
    fig.tight_layout(rect=[0, footer, 1, 0.96])
    out = args.out or f"results/paper2_fulltable/evidence/fig_render_compare_{args.seq}.png"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"wrote {out}")


if __name__ == "__main__":
    sys.exit(main())
