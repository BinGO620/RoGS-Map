#!/usr/bin/env python
"""paper2_fig1_export_assets.py — fig1 总览图真实工件导出（fig1 链路第一步）。

导出 /tmp/fig1_assets/*.npy（paper2_fig1_overview.py 的唯一输入）：
  上带（crowd2 f621）：gt / dyn（run 内 canonical 掩码）/ online（R0 在线渲染）
  下带 repair（crowd2 f621，samepose）：erased（R0）/ repaired（R1 修复态）
  地图：map_xyz/map_scale（R0 PLY）→ map_top（俯视散点图 buffer）

真实来源（全部已落盘工件，不重演实验）：
  R0 = results/paper2_fulltable/r33_rebase_baseline_crowd2_seed0（抹除态=在线栈交付形态）
  R1 = results/dynport_offline/L1_v4/crowd2_R1（修复态；samepose §12 v4 口径）
  加载器 = scripts/dynport/judge_dynport.py::_load_arm / _load_arm_causal（snapshot_pose=False）

用法：python scripts/02_analysis/paper2_fig1_export_assets.py [--out /tmp/fig1_assets]
"""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("judge", REPO / "scripts/dynport/judge_dynport.py")
judge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)

SEQ = "crowd2"
FRAMES = [621]


def r0_dir():
    hits = sorted((REPO / "results/paper2_fulltable/r33_rebase_baseline_crowd2_seed0")
                  .glob("datasets_bonn/*/seed_0/*/"))
    assert hits, "找不到 R0 run"
    return hits[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/fig1_assets")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    r0 = r0_dir()
    r1 = REPO / f"results/dynport_offline/L1_v4/{SEQ}_R1"
    assert r1.exists(), f"缺 R1 run {r1}"

    run, e_recs = judge._load_arm(r0, FRAMES, "cuda:0")
    _, d_recs = judge._load_arm_causal(r1, FRAMES, "cuda:0", snapshot_pose=False)

    for e in FRAMES:
        er, dr = e_recs.get(e), d_recs.get(e)
        assert er is not None and dr is not None, f"帧 {e} 缺读数"
        _, pkg, gt_i, _, dyn = er
        np.save(out / f"gt_{e}.npy", gt_i.cpu().numpy().transpose(1, 2, 0))
        np.save(out / f"online_{e}.npy", pkg["render"].detach().cpu().numpy().transpose(1, 2, 0))
        np.save(out / f"erased_{e}.npy", pkg["render"].detach().cpu().numpy().transpose(1, 2, 0))
        np.save(out / f"repair_{e}.npy", dr[1]["render"].detach().cpu().numpy().transpose(1, 2, 0))
        import torch as _t
        d = dyn.cpu().numpy() if _t.is_tensor(dyn) else np.asarray(dyn)
        np.save(out / f"dyn_{e}.npy", d)
        print(f"[export] f{e}: dyn frac {d.mean():.3f}")

    # 地图本体（R0 PLY 顶点 + 尺度）
    from plyfile import PlyData
    ply = r0 / "point_cloud/final/point_cloud.ply"
    v = PlyData.read(str(ply))["vertex"]
    xyz = np.stack([v["x"], v["y"], v["z"]], 1).astype(np.float32)
    sc = np.exp(np.stack([v["scale_0"], v["scale_1"], v["scale_2"]], 1)).max(1).astype(np.float32)
    np.save(out / "map_xyz.npy", xyz)
    np.save(out / "map_scale.npy", sc)
    print(f"[export] map: {len(xyz)} prims from {ply.name}")

    # 俯视散点 buffer（overview 直接消费）
    x, y = xyz[:, 0], xyz[:, 2]
    s = np.clip(sc, None, np.percentile(sc, 99))
    s = 0.2 + 2.8 * (s / s.max())
    fig = plt.figure(figsize=(2.0, 1.5), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.scatter(x, y, s=s, c=xyz[:, 1], cmap="viridis", rasterized=True, linewidths=0)
    ax.set_aspect("equal"); ax.invert_yaxis()
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    plt.close(fig)
    np.save(out / "map_top.npy", buf)
    print(f"[export] map_top {buf.shape} → {out}")


if __name__ == "__main__":
    main()
