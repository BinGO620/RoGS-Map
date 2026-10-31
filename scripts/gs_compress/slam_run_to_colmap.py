#!/usr/bin/env python
"""slam_run_to_colmap.py — 把 SLAM run 转成 graphdeco/COLMAP 格式数据集。

用途：Niedermayr c3dgs（`compress.py` / `finetune.py`，方案 A′ 第二基线）的 Scene 只认
COLMAP(PINHOLE/SIMPLE_PINHOLE，不许带畸变) 或 Blender 两种格式；本脚本从 run 目录
（config.yml + plot/trj_full_final.json + 数据集 rgb/）生成 COLMAP text 格式。

映射与几何约定（与 render_compare 口径一致）：
  - frame_id（trj_id 列表第 i 项） ↔ sorted(rgb/*.png)[i]；映射写入 frame_map.json 备审；
  - trj_est = C2W（4×4）；images.txt 写 W2C = inv(C2W) 的 qvec/tvec（COLMAP 约定）；
  - Calibration.distorted=True 时按 render_compare 同配方去畸变
    （cv2.initUndistortRectifyMap(K, D, I, K, (W,H)) + remap），落盘为无畸变 RGB；
  - points3D.txt 留空：高斯从冻结 PLY 载入，不用 COLMAP 点云初始化。

用法：
  PY=/data/conda_envs/monogs-ours/bin/python
  $PY scripts/gs_compress/slam_run_to_colmap.py --run-dir <run ts 目录> --out <输出目录> [--max-frames N]
输出：<out>/{images/, sparse/0/{cameras.txt,images.txt,points3D.txt}, frame_map.json}
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from munch import munchify  # noqa: E402
from utils.dataset import load_dataset  # noqa: E402


def rotmat2qvec(R: np.ndarray) -> np.ndarray:
    """旋转矩阵 → COLMAP 四元数 (w, x, y, z)（与 colmap_loader 互逆）。"""
    Rxx, Ryx, Rzx, Rxy, Ryy, Rzy, Rxz, Ryz, Rzz = R.flat
    K = np.array([
        [Rxx - Ryy - Rzz, 0, 0, 0],
        [Ryx + Rxy, Ryy - Rxx - Rzz, 0, 0],
        [Rzx + Rxz, Rzy + Ryz, Rzz - Rxx - Ryy, 0],
        [Ryz - Rzy, Rzx - Rxz, Rxy - Ryx, Rxx + Ryy + Rzz]]) / 3.0
    eigvals, eigvecs = np.linalg.eigh(K)
    qvec = eigvecs[[3, 0, 1, 2], np.argmax(eigvals)]
    if qvec[0] < 0:
        qvec *= -1
    return qvec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-frames", type=int, default=0, help=">0 时只取前 N 帧（冒烟）")
    args = ap.parse_args()

    run = Path(args.run_dir).resolve()
    out = Path(args.out).resolve()
    cfg = yaml.safe_load(open(run / "config.yml"))
    cal = cfg["Dataset"]["Calibration"]
    W, H = int(cal["width"]), int(cal["height"])
    K = np.array([[cal["fx"], 0.0, cal["cx"]],
                  [0.0, cal["fy"], cal["cy"]],
                  [0.0, 0.0, 1.0]], np.float64)
    ds_path = Path(cfg["Dataset"]["dataset_path"])
    if not ds_path.is_absolute():
        ds_path = REPO / ds_path
    # 帧集口径必须与 SLAM run / render_compare 同源：走 TUMParser 的 rgb↔depth↔pose
    # **关联后**序列，不能用 `rgb/*.png` 原始 glob——TUM 序列有未关联帧
    # （如 f1_desk2 原始 640 vs 关联 635），Bonn 两口径相同（已验证）。
    cfg_abs = copy.deepcopy(cfg)
    cfg_abs["Dataset"]["dataset_path"] = str(ds_path)
    model_params = munchify(cfg_abs["model_params"])
    dataset = load_dataset(model_params, model_params.source_path, config=cfg_abs)
    rgbs = [Path(p) for p in dataset.color_paths]
    trj = json.load(open(run / "plot/trj_full_final.json"))
    ids = [int(v) for v in trj["trj_id"]]
    est = [np.asarray(v, np.float64) for v in trj["trj_est"]]
    n = len(ids)
    assert len(rgbs) == n, f"关联帧数 {len(rgbs)} != trj 帧数 {n}"
    if args.max_frames > 0:
        n = min(n, args.max_frames)

    distorted = bool(cal.get("distorted", False))
    map1x = map1y = None
    if distorted:
        D = np.array([cal.get("k1", 0.0), cal.get("k2", 0.0), cal.get("p1", 0.0),
                      cal.get("p2", 0.0), cal.get("k3", 0.0)], np.float64)
        map1x, map1y = cv2.initUndistortRectifyMap(K, D, np.eye(3), K, (W, H), cv2.CV_32FC1)

    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "sparse/0").mkdir(parents=True, exist_ok=True)
    (out / "sparse/0/cameras.txt").write_text(
        f"1 PINHOLE {W} {H} {cal['fx']} {cal['fy']} {cal['cx']} {cal['cy']}\n")

    lines, fmap = [], {}
    for j in range(n):
        img = cv2.imread(str(rgbs[j]), cv2.IMREAD_COLOR)
        assert img is not None, rgbs[j]
        if map1x is not None:
            img = cv2.remap(img, map1x, map1y, cv2.INTER_LINEAR)
        name = rgbs[j].name
        cv2.imwrite(str(out / "images" / name), img)
        w2c = np.linalg.inv(est[j])
        q = rotmat2qvec(w2c[:3, :3])
        t = w2c[:3, 3]
        lines.append(f"{j + 1} {q[0]} {q[1]} {q[2]} {q[3]} {t[0]} {t[1]} {t[2]} 1 {name}\n\n")
        fmap[str(ids[j])] = name
    (out / "sparse/0/images.txt").write_text("".join(lines))
    (out / "sparse/0/points3D.txt").write_text("")
    (out / "frame_map.json").write_text(json.dumps(fmap, indent=1))
    print(f"[colmap] {n} frames -> {out} (distorted={distorted}, W={W} H={H})")


if __name__ == "__main__":
    main()
