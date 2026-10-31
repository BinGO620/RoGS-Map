#!/usr/bin/env python
"""learned_sog_baseline.py — SOG（Morgenstern et al., ECCV 2024）冻结地图后处理压缩基线。

R4-P3 / 门槛 3 整改（方案 A′ 第一基线）。口径与 Table 4 其余行严格同源（prereg §4.0）：
  - 输入 = 冻结地图源 PLY（`point_cloud/final/point_cloud.ply`，20 字段 f32）；
  - 分母 = n_src * 20 * 4；分子 = SOG 码流字节（其压缩目录内属性文件字节和，run_single_compression
    返回值）+ 旁路字节（SOG 不携带的 6 字段 nx,ny,nz,static_prob,static_obs_count,unmapped_score，
    lzma-9 无损；其解码 PLY 与本文 codec 重建 PLY 同构：17 字段）；
  - 质量 = 解码 PLY 经 canonical `render_compare.py` 渲染（同仪器、同帧集；**不使用**其自带 PSNR）；
  - rate = 分子字节 / n_src（B/prim）。

适配注记（写入证据报告与正文）：
  1. 官方代码明确支持压缩**未排序**高斯（train.py L202–206 注释 "enable compression of
     non-sorted gaussians without affecting results"）；本脚本按官方 train.py 同配方执行
     prune_to_square_shape → sort_into_grid → run_single_compression → run_single_decompression；
  2. **无** smoothness 正则训练（地图冻结、不重训）——官方非排序通路照实使用；
  3. 记账 6 字段旁路（同分母口径）；SOG 丢 0.1–0.4% 低不透明度基元（prune_to_square_shape，
     记录 n_after）；
  4. 配置取官方 `config/compression/umbrella.yaml` 默认实验，未在本文地图上调参；
  5. 依赖：SOG 源码 = /data/monogs-ours/submodules/Self-Organizing-Gaussians（tarball 快照 +
     子模块 PLAS/rasterizer/simple-knn 按 pin 组装）。

用法（须用 sogs 环境跑；渲染子进程自动切回 monogs-ours 环境）：
  PY=/data/conda_envs/sogs/bin/python
  $PY scripts/gs_compress/learned_sog_baseline.py --tag L2_balloon2_baseline_s0 --configs jxl_101   # 冒烟
  $PY scripts/gs_compress/learned_sog_baseline.py --split L2 --configs jxl_101,jxl_quant

输出：
  results/gs_compress/evidence/rd/learned_sog_<split|tag>.json（逐图逐配置行）
  工作件（压缩目录/解码 PLY）落 .tmp/learned_sog/（可复现，不入库）
"""
from __future__ import annotations

import argparse
import json
import lzma
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from plyfile import PlyData

REPO = Path(__file__).resolve().parents[2]
RD = REPO / "results/gs_compress/evidence/rd"
WORK = REPO / ".tmp/learned_sog"
SOG_REPO = Path("/data/monogs-ours/submodules/Self-Organizing-Gaussians")
PY_MONOGS = "/data/conda_envs/monogs-ours/bin/python"

AUX_FIELDS = ["nx", "ny", "nz", "static_prob", "static_obs_count", "unmapped_score"]


def local_run_dir(run_dir: str) -> Path:
    return Path(run_dir.replace("/home/jiangwenheng/cron/monogs-ours/", "").rstrip("/"))


def aux_bytes(src_ply: Path):
    """旁路 6 字段（SOG 不携带）的 lzma-9 字节数 + 源基元数。"""
    v = PlyData.read(str(src_ply))["vertex"]
    names = {p.name for p in v.properties}
    n = len(v)
    cols = [np.asarray(v[f], dtype=np.float32) if f in names
            else np.zeros(n, dtype=np.float32) for f in AUX_FIELDS]
    mat = np.stack(cols, axis=1)
    return len(lzma.compress(mat.tobytes(order="C"), preset=9)), n


def sog_imports():
    sys.path.insert(0, str(SOG_REPO))
    from omegaconf import OmegaConf
    from scene.gaussian_model import GaussianModel
    from compression.compression_exp import run_single_compression, run_single_decompression
    return OmegaConf, GaussianModel, run_single_compression, run_single_decompression


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default=None, choices=["L2", "L3"])
    ap.add_argument("--tag", default=None, help="单图 tag（冒烟用，如 L2_balloon2_baseline_s0）")
    ap.add_argument("--configs", default="jxl_101,jxl_quant")
    ap.add_argument("--sog-config", default="config/ours_q_sh_local_test.yaml")
    ap.add_argument("--device", default="cuda:0")
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
    print(f"[sog] {len(entries)} maps", flush=True)

    OmegaConf, GaussianModel, run_single_compression, run_single_decompression = sog_imports()
    sorting_cfg = OmegaConf.load(SOG_REPO / args.sog_config).sorting
    compr_cfg = OmegaConf.to_container(OmegaConf.load(SOG_REPO / "config/compression/umbrella.yaml"))
    exp_by_name = {e["name"]: e for e in compr_cfg["experiments"]}
    configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    for c in configs:
        assert c in exp_by_name, f"unknown SOG config {c}; available: {list(exp_by_name)}"

    import torch
    torch.manual_seed(0)          # sort_into_grid 的 shuffle 用 randperm，钉住可复现性
    torch.cuda.manual_seed_all(0)

    def dump() -> Path:
        out = Path(args.out_json) if args.out_json else RD / f"learned_sog_{args.split or args.tag}.json"
        out.write_text(json.dumps({
            "method": "SOG (Morgenstern et al., ECCV 2024) post-hoc on frozen maps; official non-sorted path",
            "denominator": "n_src * 20 * 4", "configs": configs, "rows": rows}, indent=2))
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

        # 官方配方（train.py L202-206 同款）：加载 → xyz 逆激活 → 方形剪枝 → 网格排序
        g = GaussianModel(0, False)
        g.load_ply(str(src_ply))
        # DC-only 适配：load_ply 对 sh_degree=0 给 _features_rest 空 1-D 张量，
        # prune_all_but_these_indices 会对其索引（IndexError）⇒ 重排为 (P, 0, 3) 可索引形。
        g._features_rest = torch.empty((g._xyz.shape[0], 0, 3),
                                       dtype=torch.float, device=g._xyz.device)
        g._xyz = g.inverse_xyz_activation(g._xyz.detach())
        g.prune_to_square_shape(verbose=False)
        g.sort_into_grid(sorting_cfg, verbose=False)
        n_after = int(g._xyz.shape[0])

        for cname in configs:
            exp = exp_by_name[cname]
            out_dir = WORK / tag / cname
            out_dir.mkdir(parents=True, exist_ok=True)
            sog_b = int(run_single_compression(g, str(out_dir), exp))
            dg = run_single_decompression(str(out_dir))
            dec_ply = out_dir / "decoded.ply"
            dg.save_ply(str(dec_ply))
            del dg

            # 解码 PLY 进 canonical 渲染仪器
            ts = "2026-10-15-00-00-07"
            dst = REPO / "results/gs_compress/recon" / f"{tag}_sog_{cname}" / ts
            (dst / "point_cloud/final").mkdir(parents=True, exist_ok=True)
            (dst / "plot").mkdir(exist_ok=True)
            shutil.copy2(run_dir / "config.yml", dst / "config.yml")
            shutil.copy2(run_dir / "plot/trj_full_final.json", dst / "plot/trj_full_final.json")
            shutil.copy2(dec_ply, dst / "point_cloud/final/point_cloud.ply")
            out_render = REPO / "results/gs_compress/render" / f"{tag}_sog_{cname}"
            cmd = [PY_MONOGS, str(REPO / "scripts/02_analysis/render_compare.py"),
                   "--run-dir", str(dst), "--ply", "final", "--out-dir", str(out_render),
                   "--device", args.device]
            if frames:
                cmd += ["--frames", frames]
            if no_static:
                cmd += ["--no-static", "--no-vacated"]
            print("[sog] $", " ".join(cmd), flush=True)
            r = subprocess.run(cmd, cwd=str(REPO))
            mpath = out_render / "render_metrics.json"
            metrics = json.loads(mpath.read_text()) if (r.returncode == 0 and mpath.exists()) else None

            total = sog_b + aux_b
            row = {
                "tag": tag, "run_dir": str(run_dir), "kind": "learned_sog", "config": cname,
                "n_src": n_src, "n_after": n_after,
                "sog_bytes": sog_b, "aux_bytes": aux_b, "total_bytes": total,
                "ratio_full": (n_src * 20 * 4) / max(1, total),
                "rate_bytes_per_prim": total / max(1, n_src),
                "render": metrics,
                "psnr_delta": (metrics["mean_psnr"] - base_psnr)
                              if (metrics and base_psnr is not None) else None,
            }
            rows.append(row)
            print(f"[sog] {tag} {cname}: ratio={row['ratio_full']:.2f}x n={n_src}->{n_after} "
                  f"psnr={metrics.get('mean_psnr') if metrics else None} d={row['psnr_delta']}",
                  flush=True)
        del g
        torch.cuda.empty_cache()
        dump()                    # 增量落盘：任一图完成后即持久化，防中途崩丢结果
        print(f"[sog] progress {len(rows)} rows -> {dump()}", flush=True)

    print(f"[sog] wrote {dump()}", flush=True)


if __name__ == "__main__":
    main()
