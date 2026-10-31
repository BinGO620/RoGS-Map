#!/usr/bin/env python3
"""l3_framesets.py — 生成并落盘 L3 正式批的**锁定帧集**（跑前预注册工件）。

背景（为什么需要本脚本）
------------------------
`prereg_L3.md` §4 把主仪器锁定为「离线密帧 17 帧（50..850 步长 50）」。实测帧数后
发现该**绝对网格**对 4/9 序列不成立——短序列在 850 之前就结束了：

    序列          N(帧)   绝对网格可取值
    balloon        441        8
    balloon2       471        9
    person_tracking2 569     11
    person_tracking  582     11
    mvnobox        780       15
    crowd3         856       17
    crowd2         897       17
    crowd          930       17
    mvnobox2       939       17

修正（见 `prereg_L3_amendment_1_frameset.md`，**判据不变**）：改为

    frames = 唯一化(round(linspace(50, min(850, N-5), 17)))

该式对 4 条最长序列（N>=855）与已锁绝对网格**逐点完全一致**（crowd2 的 C 步
读数因此原样保留），短序列则补足到 17 帧并覆盖序列尾部。

本脚本把结果落盘为 `l3_framesets.json`，渲染阶段只读该文件 ⇒ 同一序列的
off/exit 两臂**使用同一字面帧列表**，配对严格对称且可审计。

用法
----
    python scripts/02_analysis/l3_framesets.py [--write] [--json OUT]

不带 --write 只打印（dry-run）；带 --write 才落盘。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# L3 序列登记表：别名 -> Bonn 数据集目录（与 configs/rgbd/bonn/<...>.yaml 的 Dataset.dataset_path 一致）
SEQ_DATASET = {
    "balloon": "datasets/bonn/rgbd_bonn_balloon",
    "balloon2": "datasets/bonn/rgbd_bonn_balloon2",
    "crowd": "datasets/bonn/rgbd_bonn_crowd",
    "crowd2": "datasets/bonn/rgbd_bonn_crowd2",
    "crowd3": "datasets/bonn/rgbd_bonn_crowd3",
    "person_tracking": "datasets/bonn/rgbd_bonn_person_tracking",
    "person_tracking2": "datasets/bonn/rgbd_bonn_person_tracking2",
    "mvnobox": "datasets/bonn/rgbd_bonn_moving_nonobstructing_box",
    "mvnobox2": "datasets/bonn/rgbd_bonn_moving_nonobstructing_box2",
    # TUM（D2-009 夜间新域移植；prereg_L2_tum_wk.md）——写入独立工件 l2_tum_framesets.json，
    # 不改动冻结的 L3 帧集 JSON。公式与 L3 同源。
    "tum_wk_rpy": "datasets/tum/rgbd_dataset_freiburg3_walking_rpy",
}

N_FRAMES = 17        # 预注册锁定的帧数
GRID_LO = 50         # 预注册锁定的起始帧号
GRID_HI_MAX = 850    # 预注册锁定的上限帧号
# 末帧留白 2：避开序列最后两帧（轨迹收尾段），同时保证 N>=852 的序列仍能取满 850。
# 取 2 而非 0 的理由 = 末帧未必有估计位姿（render_compare 对无位姿 id 静默跳过，
# 会造成 n_frames<17 而不报错）；取 2 而非 5 的理由 = N=854 的 crowd3 在留白 5 时
# 上界降为 849，会丢掉与已锁绝对网格（顶端 850）的逐点一致性。
TAIL_MARGIN = 2

ABS_GRID = list(range(GRID_LO, GRID_HI_MAX + 1, 50))  # 旧绝对网格（对照用）


def count_frames(ds_dir: str) -> int:
    """序列帧数 = rgb.txt 行数（与 dataset.num_imgs 同源）。"""
    rgb_txt = os.path.join(REPO, ds_dir, "rgb.txt")
    if not os.path.exists(rgb_txt):
        raise FileNotFoundError(rgb_txt)
    with open(rgb_txt) as f:
        n = sum(1 for line in f if line.strip() and not line.lstrip().startswith("#"))
    if n <= 0:
        raise ValueError(f"empty rgb.txt: {rgb_txt}")
    return n


def frameset(N: int) -> tuple[list[int], int]:
    """返回 (17 个帧 id, 上界 hi)。"""
    hi = min(GRID_HI_MAX, N - TAIL_MARGIN)
    raw = np.linspace(GRID_LO, hi, N_FRAMES)
    ids = sorted({int(round(float(x))) for x in raw})
    return ids, hi


def abs_grid_valid(N: int) -> list[int]:
    """旧绝对网格在该序列上实际可取到的帧（idx <= N-1）。"""
    return [i for i in ABS_GRID if i <= N - 1]


def build() -> dict:
    out = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "authority": "results/lifecycle_paper2/evidence/prereg_L3_amendment_1_frameset.md",
        "formula": f"sorted({{round(x) for x in linspace({GRID_LO}, min({GRID_HI_MAX}, N-{TAIL_MARGIN}), {N_FRAMES})}})",
        "n_frames_target": N_FRAMES,
        "tail_margin": TAIL_MARGIN,
        "abs_grid_reference": ABS_GRID,
        "note": ("渲染阶段只读本文件；同一序列 off/exit 两臂必须使用同一 id 列表（配对对称）。"
                 "overlap_vs_abs_grid 是本修正的口径连续性证据。"),
        "sequences": {},
    }
    problems = []
    for seq, ds in SEQ_DATASET.items():
        N = count_frames(ds)
        ids, hi = frameset(N)
        grid = abs_grid_valid(N)
        overlap = sorted(set(grid) & set(ids))
        identical = set(grid) == set(ids)
        if len(ids) != N_FRAMES:
            problems.append(f"{seq}: got {len(ids)} ids, expected {N_FRAMES}")
        if ids[-1] > N - 1:
            problems.append(f"{seq}: max id {ids[-1]} >= N({N})")
        if ids[0] != GRID_LO:
            problems.append(f"{seq}: first id {ids[0]} != {GRID_LO}")
        out["sequences"][seq] = {
            "dataset": ds,
            "N": N,
            "hi": hi,
            "n_frames": len(ids),
            "frames": ids,
            "abs_grid_valid_n": len(grid),
            "abs_grid_valid": grid,
            "overlap_vs_abs_grid": len(overlap),
            "overlap_ids": overlap,
            "identical_to_abs_grid": identical,
        }
    if problems:
        raise AssertionError("frameset 自检失败:\n  " + "\n  ".join(problems))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="落盘 JSON（缺省仅打印）")
    ap.add_argument("--json", default=os.path.join(REPO, "results/lifecycle_paper2/evidence/l3_framesets.json"))
    ap.add_argument("--frames-for", default=None, metavar="SEQ",
                    help="打印该序列的锁定帧集（逗号分隔，供渲染脚本 --frames 使用）")
    args = ap.parse_args()

    # 渲染脚本路径：只读已落盘的 JSON，保证两臂读到同一份锁定帧集
    if args.frames_for:
        if not os.path.exists(args.json):
            print(f"ERROR: 缺 {args.json}（先跑 --write）", file=sys.stderr)
            return 2
        with open(args.json) as f:
            data = json.load(f)
        seq = args.frames_for
        if seq not in data["sequences"]:
            print(f"ERROR: 未知序列 {seq}；可选: {', '.join(data['sequences'])}", file=sys.stderr)
            return 2
        print(",".join(str(i) for i in data["sequences"][seq]["frames"]))
        return 0

    data = build()

    print(f"formula: {data['formula']}")
    print(f"{'sequence':18s} {'N':>5s} {'hi':>5s} {'n':>3s} {'abs_n':>6s} {'overlap':>8s}  identical")
    for seq, v in data["sequences"].items():
        print(f"{seq:18s} {v['N']:5d} {v['hi']:5d} {v['n_frames']:3d} "
              f"{v['abs_grid_valid_n']:6d} {v['overlap_vs_abs_grid']:5d}/17  "
              f"{'YES' if v['identical_to_abs_grid'] else 'no'}")
    n_id = sum(1 for v in data["sequences"].values() if v["identical_to_abs_grid"])
    print(f"\n与已锁绝对网格逐点一致的序列: {n_id}/9")

    if args.write:
        os.makedirs(os.path.dirname(args.json), exist_ok=True)
        with open(args.json, "w") as f:
            json.dump(data, f, indent=1, ensure_ascii=False)
        print(f"\n已落盘: {args.json}")
    else:
        print("\n(dry-run；加 --write 落盘)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
