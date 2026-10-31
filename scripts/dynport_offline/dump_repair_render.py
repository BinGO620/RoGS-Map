#!/usr/bin/env python
"""dump_repair_render.py — 论文2 §7（贡献③）定性对比图：GT | erased | repaired（动态区放大）。

复用现成加载路径（**不重演优化**；离线修复态已烘焙在盘）：
  * 修复态（R1）：`judge_dynport._load_arm_causal(r1_dir, frames, device, snapshot_pose=False)`
      —— `snapshot_pose=False` = samepose 出口口径（prereg §12 v4）：全臂用帧 e 最终轨迹位姿
      + 最近 ≤e 的快照动态层。即"修复算子 4D 交付（output①）"的真实消费口径。
  * 抹除态（R0）：`judge_dynport._load_arm(r0_dir, frames, device)` —— 反动态范式静态底图。
  * GT：任一 run 的 `frame_data(e)[0]`（同数据集，[0,1] C,H,W）。
  * 动态区：`run.frame_mask(e)` 的 nonzero bbox（canonical 掩码，评估分区用）。

帧选择 = **确定性**（每序列取该 run 评估帧清单的 30%/70% 分位帧；禁"看结果挑最佳帧"）。
渲染 = CUDA（diff rasterizer 无 CPU 路径）；本机 2060 亚秒/帧。

输出：results/paper2_fulltable/evidence/figs/fig6_dynport_repair.{pdf,png}
（后由调用方镜像到 papers/paper2/figs/，并由 tests/paper2_fulltable/test_paper2_figures_committed.py 守护。）

用法：
  python scripts/dynport_offline/dump_repair_render.py            # 默认 crowd2+balloon2，中位帧
  python scripts/dynport_offline/dump_repair_render.py --seq crowd2 --frames 446,571
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]

# 复用 judge_dynport 的加载器（同判据机同一路径，口径零漂移）
_spec = importlib.util.spec_from_file_location("judge_dynport", REPO / "scripts/dynport/judge_dynport.py")
judge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(judge)

OUT_DIR = REPO / "results/paper2_fulltable/evidence/figs"

# 基线（R0）run 根：按序列定位
R0_ROOT = REPO / "results/paper2_fulltable"
R1_ROOT = REPO / "results/dynport_offline/L1_v4"


def _r0_dir(seq):
    hits = sorted((R0_ROOT / f"r33_rebase_baseline_{seq}_seed0").glob("datasets_bonn/*/seed_0/*/"))
    assert hits, f"找不到 {seq} 的 R0 底图 run 目录"
    return hits[-1]


def _r1_dir(seq):
    d = R1_ROOT / f"{seq}_R1"
    assert d.exists(), f"找不到 {seq} 的 R1 修复 run 目录 {d}"
    return d


def _quantile_frames(run_dir, qs=(0.30, 0.70)):
    """确定性帧集：评估帧清单（run 自带日程）的分位帧；禁"看结果挑帧"。"""
    fr = sorted(judge.derive_eval_frames(run_dir))
    if not fr:
        return []
    return [fr[min(len(fr) - 1, int(round(q * (len(fr) - 1))))] for q in qs]


def _dyn_bbox(dyn, H, W, pad=40):
    vs, us = np.nonzero(np.asarray(dyn, dtype=bool))
    if len(vs) == 0:
        return 0, H, 0, W
    return (max(int(vs.min()) - pad, 0), min(int(vs.max()) + pad, H),
            max(int(us.min()) - pad, 0), min(int(us.max()) + pad, W))


def render_pair(seq, frames, device="cuda:0"):
    """返回 {frame: (gt, erase, repair, bbox)}。"""
    r0, r1 = _r0_dir(seq), _r1_dir(seq)
    _, e_recs = judge._load_arm(r0, frames, device)                       # 抹除态
    _, d_recs = judge._load_arm_causal(r1, frames, device, snapshot_pose=False)  # 修复态（samepose）
    out = {}
    for e in frames:
        if e not in e_recs or e not in d_recs:
            print(f"  [{seq}] f{e} 缺读数，跳过"); continue
        run, _, gt_i, _, dyn = e_recs[e]
        gt = gt_i.detach().cpu().numpy().transpose(1, 2, 0)
        erase = e_recs[e][1]["render"].detach().cpu().numpy().transpose(1, 2, 0)
        repair = d_recs[e][1]["render"].detach().cpu().numpy().transpose(1, 2, 0)
        H, W = gt.shape[:2]
        out[e] = (gt, erase, repair, _dyn_bbox(dyn, H, W))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", default="crowd2,balloon2")
    ap.add_argument("--frames", default="", help="逗号分隔；空则每序列取分位帧（30%/70%）")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--out", default="fig6_dynport_repair")
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import sys as _sys
    _sys.path.insert(0, str(REPO / "scripts" / "02_analysis"))
    import paper2_figstyle as fs
    fs.apply()   # 统一出图样式（无衬线 + Okabe-Ito；caption 不进图面）

    seqs = [s.strip() for s in args.seq.split(",") if s.strip()]
    manual = [int(x) for x in args.frames.split(",") if x.strip()]

    # rows = (seq, frame)，每序列 2 帧（确定性分位帧）；禁人工挑帧
    rows = []
    for seq in seqs:
        frames = manual if manual else _quantile_frames(_r0_dir(seq))
        if not frames:
            print(f"[{seq}] 无可用帧，跳过"); continue
        res = render_pair(seq, frames, args.device)
        for e in sorted(res):
            rows.append((seq, e, res[e]))
        print(f"[{seq}] frames={list(res)}")

    assert rows, "无可渲染行"
    # 布局：行=(序列,帧)，列=[GT, erased, repaired]；erased/repaired 带动态区 inset，GT 标框
    from matplotlib.patches import Rectangle
    COLS = ["Ground truth", "Erased (base map)", "Repaired (offline)"]
    nrow = len(rows)
    fig, axes = plt.subplots(nrow, 3, figsize=(6.9, 1.42 * nrow), squeeze=False)
    for r, (seq, e, (gt, erase, repair, (v0, v1, u0, u1))) in enumerate(rows):
        for c, img in enumerate([gt, erase, repair]):
            ax = axes[r][c]
            ax.imshow(np.clip(img, 0, 1))
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_linewidth(0.6)
            if r == 0:
                ax.set_title(COLS[c], fontsize=7.5)
            if c == 0:
                ax.add_patch(Rectangle((u0, v0), u1 - u0, v1 - v0,
                                       fill=False, edgecolor=fs.ACCENT, lw=1.0))
                ax.set_ylabel(f"{seq}\nf{e}", fontsize=7, rotation=0,
                              ha="right", va="center", labelpad=14)
            else:
                ia = ax.inset_axes([0.63, 0.02, 0.35, 0.46])
                ia.imshow(np.clip(img[v0:v1, u0:u1], 0, 1))
                ia.set_xticks([]); ia.set_yticks([])
                for s in ia.spines.values():
                    s.set_color(fs.ACCENT); s.set_linewidth(0.8)
    fig.subplots_adjust(wspace=0.04, hspace=0.06)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"{args.out}.{ext}", dpi=300)
    plt.close(fig)
    print(f"wrote {OUT_DIR}/{args.out}.pdf/.png")
    meta = {}
    for seq, e, _ in rows:
        meta.setdefault(seq, []).append(e)
    (OUT_DIR / f"{args.out}_frames.json").write_text(json.dumps(meta, indent=2))
    print("frames:", meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
