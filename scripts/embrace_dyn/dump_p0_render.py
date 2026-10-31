#!/usr/bin/env python
"""P0 交付三件套之对比图：重演在线缓冲至指定评估帧，出 GT | P1(冻结地图) | P0o 三联图。

复用 dyn_probe.OnlineBuffer（与正式批同一确定性路径：同 config 同 seed ⇒ 同缓冲状态）。
仅交付层工具，不产生判据读数（判据一律出自 judge_p0.py）。

用法：
  python scripts/embrace_dyn/dump_p0_render.py --config <probe_yaml> \
      --map-tag gate --frames 259,321 --out-dir results/embrace_online/evidence
"""
import argparse
import importlib.util
from pathlib import Path

import numpy as np
import torch
import yaml

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("dyn_probe", REPO / "scripts/02_analysis/dyn_probe.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)


def render_p1(run, pc, idx):
    fd = run.frame_data(idx)
    cam = run.camera(idx, fd[2])
    pkg = probe.render_once(run, cam, pc)
    return torch.clamp(pkg["render"], 0.0, 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--map-tag", default="gate")
    ap.add_argument("--frames", required=True, help="逗号分隔评估帧（须 > t0）")
    ap.add_argument("--out-dir", default="results/embrace_online/evidence")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    mp = next(m for m in cfg["maps"] if m["tag"] == args.map_tag)
    run = probe.Run(mp["run_dir"], ply=cfg.get("ply", "final_after_opt"),
                    device=cfg.get("device", "cuda:0"), mask_subdir=cfg.get("mask_subdir", "auto"))
    pc = probe.PackedPC(run.gaussians)
    oc = cfg.get("online", {})
    t0 = int(cfg["t0_frame"])
    frames = [int(f) for f in args.frames.split(",")]
    assert all(f > t0 for f in frames), "评估帧必须 > t0（严格因果）"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    buf = probe.OnlineBuffer(run, pc, voxel=float(oc.get("voxel", 0.02)),
                             cap=int(oc.get("cap", 60000)), lam_rho=float(oc.get("lam_rho", 0.01)),
                             lr_rho=float(oc.get("lr_rho", 5e-2)), rho_init=float(oc.get("rho_init", 0.9)))
    lrs = cfg["lrs"]
    window = int(oc.get("window", 4))
    steps_pf = int(oc.get("steps_per_frame", 10))
    stride = int(cfg.get("unproj_stride", 3))
    torch.manual_seed(int(oc.get("seed", 0)))
    max_j = max(frames) - 1
    fd_cache = {}

    def fd_of(j):
        if j not in fd_cache:
            fd_cache[j] = run.frame_data(j)
            while len(fd_cache) > window + 2:
                fd_cache.pop(min(fd_cache))
        return fd_cache[j]

    for j in range(t0, max_j + 1):
        buf.insert_frame(j, stride)
        for s in range(steps_pf):
            wj = probe.rolling_window_frame(j, t0, window, steps_pf, s)
            if wj is None:
                break
            fdw = fd_of(wj)
            if fdw is None:
                continue
            buf.opt_steps(run.camera(wj, fdw[2]), fdw, steps=1, lrs=lrs)
        if (j + 1) in set(frames):
            e = j + 1
            fd_e = run.frame_data(e)
            gt_e = fd_e[0]
            cam_e = run.camera(e, fd_e[2])
            p1 = render_p1(run, pc, e)
            pc.set_dynamic(probe.dyn_tensors(buf.d))
            pkg = probe.render_once(run, cam_e, pc)
            p0o = torch.clamp(pkg["render"], 0.0, 1.0)
            dyn = run.frame_mask(e)
            # 三联 + dyn 区放大框（掩码 bbox 外扩 40px）
            gtc = gt_e.detach().cpu().numpy().transpose(1, 2, 0)
            p1c = p1.detach().cpu().numpy().transpose(1, 2, 0)
            p0c = p0o.detach().cpu().numpy().transpose(1, 2, 0)
            vs, us = np.nonzero(np.asarray(dyn, dtype=bool))
            if len(vs):
                v0, v1 = max(vs.min() - 40, 0), min(vs.max() + 40, gtc.shape[0])
                u0, u1 = max(us.min() - 40, 0), min(us.max() + 40, gtc.shape[1])
            else:
                v0, v1, u0, u1 = 0, gtc.shape[0], 0, gtc.shape[1]
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(2, 3, figsize=(13, 7))
            for col, (img, name) in enumerate([(gtc, "GT"), (p1c, "P1 erase (frozen map)"),
                                               (p0c, "P0o online buffer")]):
                axes[0, col].imshow(np.clip(img, 0, 1))
                axes[0, col].set_title(name, fontsize=11)
                axes[0, col].axis("off")
                axes[1, col].imshow(np.clip(img[v0:v1, u0:u1], 0, 1))
                axes[1, col].set_title(f"{name} (dyn crop)", fontsize=10)
                axes[1, col].axis("off")
            fig.suptitle(f"{cfg['sequence']} {args.map_tag} f{e}  "
                         f"(buf={buf.n}, cap_hits={buf.cap_hits}, rho_med="
                         f"{float(torch.sigmoid(buf.d['rho']).median()):.2f})", fontsize=12)
            fig.tight_layout()
            out = out_dir / f"fig_p0_compare_{cfg['sequence']}_{args.map_tag}_f{e}.png"
            fig.savefig(out, dpi=130)
            plt.close(fig)
            print(f"[dump_p0] written {out}  buf={buf.n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
