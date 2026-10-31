#!/usr/bin/env python
"""learned_nied_c3dgs_baseline.py — Niedermayr et al.（Compressed 3DGS, CVPR 2024）冻结地图基线。

方案 A′ 第二基线。口径与 Table 4 同源（同分母 n_src*20*4、同渲染仪器 render_compare、同帧集）。

与 SOG 基线的关键差异（照实登记进证据报告与正文）：
  - 该方法的压缩链路 = **以冻结地图为初始化 + 其标准 QAT 微调**（finetune_iterations=5000，
    渲染监督、用 SLAM 数据集图像）→ R-VQ + 量化 + 熵编码的 npz ⇒ 属"重训再压"，
    解码图会轻微再拟合（等 PSNR 口径下仍可比较，但须标注）；
  - 输入格式：其 Scene 只认 COLMAP(PINHOLE/无畸变)；本驱动先用 slam_run_to_colmap.py 转换
    （去畸变 + C2W→W2C）；points3D 留空（高斯从冻结 PLY 载入，不走 COLMAP 初始化）；
  - 记账 6 字段同样走 lzma 旁路；分子 = npz 文件字节（其 "--store_npz 反映实际存储" 口径）+ 旁路；
  - 解码：其 npz2ply.py 硬编码 GaussianModel(3)，与 DC-only npz 不匹配 ⇒ 本驱动内联
    GaussianModel(0) + load_npz + save_ply（同语义、仅 sh_degree 对齐）。

用法（须用 nied-c3dgs 环境；转换/渲染子进程自动切回 monogs-ours 环境）：
  PY=/data/conda_envs/nied-c3dgs/bin/python
  $PY scripts/gs_compress/learned_nied_c3dgs_baseline.py --tag L2_balloon2_baseline_s0 --iters 200   # 接线冒烟
  $PY scripts/gs_compress/learned_nied_c3dgs_baseline.py --split L2 --iters 5000

输出：results/gs_compress/evidence/rd/learned_nied_<split|tag>.json（增量落盘）；工作件在 .tmp/learned_nied/
"""
from __future__ import annotations

import argparse
import json
import lzma
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
from plyfile import PlyData

REPO = Path(__file__).resolve().parents[2]
RD = REPO / "results/gs_compress/evidence/rd"
WORK = REPO / ".tmp/learned_nied"
# 三处外部依赖路径：默认本机（cb）口径；远程 3090 用环境变量覆盖
# （NIED_REPO / PY_MONOGS / PY_NIED），脚本本身两机通用。
NIED_REPO = Path(os.environ.get("NIED_REPO", str(REPO / "submodules/compressed-3dgs-niedermayr")))
PY_MONOGS = os.environ.get("PY_MONOGS", "/data/conda_envs/monogs-ours/bin/python")
PY_NIED = os.environ.get("PY_NIED", "/data/conda_envs/nied-c3dgs/bin/python")

AUX_FIELDS = ["nx", "ny", "nz", "static_prob", "static_obs_count", "unmapped_score"]


def local_run_dir(run_dir: str) -> Path:
    return Path(run_dir.replace("/home/jiangwenheng/cron/monogs-ours/", "").rstrip("/"))


def aux_bytes(src_ply: Path):
    v = PlyData.read(str(src_ply))["vertex"]
    names = {p.name for p in v.properties}
    n = len(v)
    cols = [np.asarray(v[f], dtype=np.float32) if f in names
            else np.zeros(n, dtype=np.float32) for f in AUX_FIELDS]
    mat = np.stack(cols, axis=1)
    return len(lzma.compress(mat.tobytes(order="C"), preset=9)), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default=None, choices=["L2", "L3"])
    ap.add_argument("--tag", default=None)
    ap.add_argument("--tags", default=None,
                    help="逗号分隔的 tag 白名单（只跑这些地图）。用于续跑：远程/前轮已完成的"
                         "地图若不在白名单内，就不会被重压一遍。")
    ap.add_argument("--iters", type=int, default=5000, help="QAT 微调迭代数（其默认 5000）")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--data-device", default="cuda", choices=["cuda", "cpu"],
                    help="写进 cfg_args 的 data_device。其 Scene 会把**每张训练图**都放到该设备上"
                         "（scene/cameras.py:39），长序列在 6GB 卡上必 OOM（实测 f3_office 2515 帧、"
                         "约 9.3GB）。'cpu' 只改图像驻留位置：finetune.py:51 每步仍 .cuda()，"
                         "灵敏度扫描与 eval 都不读 GT 图 ⇒ 数学不变。")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()
    assert args.split or args.tag, "须给 --split 或 --tag"

    if args.tag:
        jpath = RD / f"{args.tag}_rd_table.json"
        assert jpath.exists(), jpath
        entries = [(args.tag, jpath)]
    else:
        entries = [(p.name.replace("_rd_table.json", ""), p)
                   for p in sorted(RD.glob(f"{args.split}_*_rd_table.json"))]
    if args.tags:
        keep = [t.strip() for t in args.tags.split(",") if t.strip()]
        have = {t for t, _ in entries}
        missing = [t for t in keep if t not in have]
        assert not missing, f"白名单里有 {args.split} 之外/不存在的 tag: {missing}"
        entries = [(t, p) for t, p in entries if t in set(keep)]
    print(f"[nied] {len(entries)} maps", flush=True)

    def dump() -> Path:
        out = Path(args.out_json) if args.out_json else RD / f"learned_nied_{args.split or args.tag}.json"
        out.write_text(json.dumps({
            "method": "Niedermayr et al., Compressed 3DGS (CVPR 2024); QAT finetune from frozen map",
            "denominator": "n_src * 20 * 4", "finetune_iters": args.iters, "rows": rows}, indent=2))
        return out

    rows = []
    for tag, jpath in entries:
        d = json.loads(jpath.read_text())
        run_dir = local_run_dir(d["run_dir"])
        frames = d.get("frames")
        src_ply = run_dir / "point_cloud/final/point_cloud.ply"
        assert src_ply.exists(), src_ply
        aux_b, n_src = aux_bytes(src_ply)
        base = next((r["render"] for r in d["rows"] if r.get("kind") == "baseline"), None)
        base_psnr = base.get("mean_psnr") if base else None
        no_static = bool(base) and ("mean_static_psnr" not in base)

        tagdir = WORK / tag
        colmap_ds = tagdir / "colmap_ds"
        model = tagdir / "model"
        out_vq = tagdir / "out_vq"

        # 1) SLAM run → COLMAP 数据集（去畸变；幂等）
        if not (colmap_ds / "sparse/0/images.txt").exists():
            r = subprocess.run([PY_MONOGS, str(REPO / "scripts/gs_compress/slam_run_to_colmap.py"),
                                "--run-dir", str(run_dir), "--out", str(colmap_ds)],
                               cwd=str(REPO))
            assert r.returncode == 0, "colmap 转换失败"

        # 2) 模型目录：冻结地图 @ iteration_1 + cfg_args（graphdeco 风格；sh_degree=0）
        (model / "point_cloud/iteration_1").mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_ply, model / "point_cloud/iteration_1/point_cloud.ply")
        (model / "cfg_args").write_text(
            f"Namespace(sh_degree=0, source_path='{colmap_ds}', model_path='{model}', "
            f"images='images', resolution=-1, white_background=False, "
            f"data_device='{args.data_device}', eval=False)")

        # 3) 其压缩链路：敏感度 → VQ → QAT 微调 → save_npz（npz 已存在则复用，支持断点续跑）
        out_vq.mkdir(parents=True, exist_ok=True)
        iter_final = 1 + args.iters
        npz = out_vq / "point_cloud" / f"iteration_{iter_final}" / "point_cloud.npz"
        if npz.exists():
            print(f"[nied] {tag}: 复用已有 npz", flush=True)
        else:
            log = tagdir / "compress.log"
            with open(log, "w") as lf:
                r = subprocess.run(
                    [PY_NIED, str(NIED_REPO / "compress.py"),
                     "--model_path", str(model), "--source_path", str(colmap_ds),
                     "--output_vq", str(out_vq), "--load_iteration", "1",
                     "--finetune_iterations", str(args.iters)],
                    cwd=str(NIED_REPO), stdout=lf, stderr=subprocess.STDOUT)
            if r.returncode != 0:
                print(f"[nied] {tag}: compress.py 失败 rc={r.returncode}，日志尾：", flush=True)
                print("\n".join(log.read_text().splitlines()[-25:]), flush=True)
                continue
            if not npz.exists():
                print(f"[nied] {tag}: 缺 {npz}（日志尾见 {log}）", flush=True)
                continue
        npz_bytes = npz.stat().st_size

        # 4) 解码（内联 sh_degree=0 版本）
        dec_ply = tagdir / "decoded.ply"
        r = subprocess.run(
            [PY_NIED, "-c",
             "import sys; from scene import GaussianModel; "
             "g = GaussianModel(0); g.load_npz(sys.argv[1]); g.save_ply(sys.argv[2])",
             str(npz), str(dec_ply)], cwd=str(NIED_REPO))
        if r.returncode != 0 or not dec_ply.exists():
            print(f"[nied] {tag}: 解码失败 rc={r.returncode}", flush=True)
            continue

        # 5) 本文仪器渲染
        ts = "2026-10-16-00-00-08"
        dst = REPO / "results/gs_compress/recon" / f"{tag}_nied_{args.iters}" / ts
        (dst / "point_cloud/final").mkdir(parents=True, exist_ok=True)
        (dst / "plot").mkdir(exist_ok=True)
        shutil.copy2(run_dir / "config.yml", dst / "config.yml")
        shutil.copy2(run_dir / "plot/trj_full_final.json", dst / "plot/trj_full_final.json")
        shutil.copy2(dec_ply, dst / "point_cloud/final/point_cloud.ply")
        out_render = REPO / "results/gs_compress/render" / f"{tag}_nied_{args.iters}"
        cmd = [PY_MONOGS, str(REPO / "scripts/02_analysis/render_compare.py"),
               "--run-dir", str(dst), "--ply", "final", "--out-dir", str(out_render),
               "--device", args.device]
        if frames:
            cmd += ["--frames", frames]
        if no_static:
            cmd += ["--no-static", "--no-vacated"]
        print("[nied] $", " ".join(cmd), flush=True)
        rr = subprocess.run(cmd, cwd=str(REPO))
        mpath = out_render / "render_metrics.json"
        metrics = json.loads(mpath.read_text()) if (rr.returncode == 0 and mpath.exists()) else None

        total = npz_bytes + aux_b
        row = {
            "tag": tag, "run_dir": str(run_dir), "kind": "learned_nied_c3dgs",
            "finetune_iters": args.iters, "n_src": n_src,
            "npz_bytes": npz_bytes, "aux_bytes": aux_b, "total_bytes": total,
            "ratio_full": (n_src * 20 * 4) / max(1, total),
            "rate_bytes_per_prim": total / max(1, n_src),
            "render": metrics,
            "psnr_delta": (metrics["mean_psnr"] - base_psnr)
                          if (metrics and base_psnr is not None) else None,
        }
        rows.append(row)
        print(f"[nied] {tag}: ratio={row['ratio_full']:.2f}x psnr="
              f"{metrics.get('mean_psnr') if metrics else None} d={row['psnr_delta']}", flush=True)
        dump()
        print(f"[nied] progress {len(rows)} rows -> {dump()}", flush=True)

    print(f"[nied] wrote {dump()}", flush=True)


if __name__ == "__main__":
    main()
