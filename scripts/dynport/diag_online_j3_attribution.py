#!/usr/bin/env python
"""diag_online_j3_attribution.py — 在线 DynPort J3 归因复核（D1-032 的「建图侧未隔离」是否含遮挡）。

背景：离线轮（D1-034）证 J3(final-map) 混淆「静态被改」与「动态层遮挡」。在线 D1-032 把 J3
−0.49/−1.02 归因于"建图侧未隔离"（静态被联合优化伤）。本脚本用**同一分解法**复核在线：

  在线 D 臂的最终 PLY **含动态行**（`dynport_causal/dynamic_rows.npy` 标记；动态基元插进共享模型
  ⇒ 与静态同图）。故：
    A. E 臂（erase 基线，全静态）= 静态参照
    B. D 臂**全图**（静态 + 动态行）= 现 J3 所测
    C. D 臂**仅静态行**（按 dynamic_rows 去动态）= 静态本体（隔离层的贡献）
  则：
    B − A = 现 J3（静态伤 + 遮挡）
    C − A = **静态本体伤**（建图侧未隔离的直接证据）
    B − C = **动态层遮挡**（非静态伤）

注：在线与离线不同——离线的静态行**逐位冻结**（C−A≡0），在线的静态行**可能被联合优化改动**
（C−A≠0 即"建图侧确实未隔离"）。另外在线用**在线位姿**（非最终轨迹）⇒ 位姿介于 E/D 间，此处以
D 的 trj 作 E 的同位姿参考，两个已知边界见文末。

用法（GPU）：
  python scripts/dynport/diag_online_j3_attribution.py \
      --e-run <E run dir> --d-run <D run dir> --seq crowd2 \
      --out results/dynport/evidence/diag_online_j3_attribution.json
"""
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
_spec = importlib.util.spec_from_file_location("dyn_probe", REPO / "scripts/02_analysis/dyn_probe.py")
probe = importlib.util.module_from_spec(_spec)
sys.modules["dyn_probe"] = probe
_spec.loader.exec_module(probe)


def _med(xs):
    xs = [x for x in xs if x is not None and np.isfinite(x)]
    return round(float(np.median(xs)), 4) if xs else None


def _load_ply_minus_rows(run, drop_mask):
    """返回一个 PackedPC 风格的只读视图（去掉 drop_mask=True 的行）。"""
    import torch
    m = run.gaussians
    keep = ~np.asarray(drop_mask, dtype=bool)
    kt = torch.as_tensor(keep, device=m.get_xyz.device)
    pc = probe.PackedPC(m)

    class _Sub:
        pass
    sub = _Sub()
    sub.max_sh_degree = m.max_sh_degree
    sub.active_sh_degree = m.active_sh_degree
    sub.get_xyz = m.get_xyz.detach()[kt]
    sub.get_opacity = m.get_opacity.detach()[kt]
    sub.get_scaling = m.get_scaling.detach()[kt]
    sub.get_rotation = m.get_rotation.detach()[kt]
    sub.get_features = m.get_features.detach()[kt]
    return sub


def _eval_frames(run_dir):
    """该 run 的评估帧（console `Evaluating ATE at frame: N`）。"""
    import re
    c = Path(run_dir) / "console.log"
    if not c.exists():
        return []
    return sorted(set(int(m) for m in re.findall(r"Evaluating ATE at frame:\s*(\d+)", c.read_text(errors="ignore"))))


def run_seq(e_run_dir, d_run_dir, device):
    e_run = probe.Run(e_run_dir, device=device)
    d_run = probe.Run(d_run_dir, device=device)
    drow = Path(d_run_dir) / "dynport_causal" / "dynamic_rows.npy"
    if not drow.exists():
        return {"error": f"no dynamic_rows.npy in {d_run_dir}"}
    is_dyn = np.load(drow)
    d_static = _load_ply_minus_rows(d_run, is_dyn)

    dBA, dCA, dBC = [], [], []
    # 在线 E/D 的 KF 日程不同（E 与 D 各自 stride 不同）⇒ 不能用"各臂自己的评估帧交集"。
    # 采用**位姿受控**分解（同离线 samepose 思路）：全部在 **D 臂的帧/位姿/GT/掩码**上渲染，
    # 只有地图不同 —— A=E 图（erase 基线）、B=D 全图、C=D 仅静态行。位姿固定 ⇒ B−C 即**动态层遮挡**，
    # C−A 即**静态本体伤**（D 的静态行相对 E 底图的改动 = "建图侧未隔离"的直接证据）。
    for e in _eval_frames(d_run_dir):
        fd = d_run.frame_data(e)
        if fd is None:
            continue
        gt_i, gt_d, w2c = fd
        dyn = d_run.frame_mask(e)
        cam = d_run.camera(e, w2c)
        pkgE = probe.render_once(e_run, cam, probe.PackedPC(e_run.gaussians))   # E 图 @ D 位姿
        pkgB = probe.render_once(d_run, cam, probe.PackedPC(d_run.gaussians))
        pkgC = probe.render_once(d_run, cam, d_static)
        if pkgE is None or pkgB is None or pkgC is None:
            continue
        a = probe.frame_metrics(d_run, e, pkgE, gt_i, gt_d, dyn).get("static_psnr")
        b = probe.frame_metrics(d_run, e, pkgB, gt_i, gt_d, dyn).get("static_psnr")
        c = probe.frame_metrics(d_run, e, pkgC, gt_i, gt_d, dyn).get("static_psnr")
        if None in (a, b, c):
            continue
        dBA.append(b - a); dCA.append(c - a); dBC.append(b - c)
    return {"seq": None, "n_frames": len(dBA), "n_total_rows": int(len(is_dyn)),
            "n_dynamic_rows": int(is_dyn.sum()),
            "B_full_minus_A_erase": _med(dBA),          # 现 J3（D 位姿下，图差 + 遮挡）
            "C_staticrows_minus_A": _med(dCA),          # 静态本体伤（建图侧未隔离）
            "B_minus_C_occlusion": _med(dBC)}           # 动态层遮挡（位姿受控）


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--e-run", required=True)
    ap.add_argument("--d-run", required=True)
    ap.add_argument("--seq", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()
    r = run_seq(args.e_run, args.d_run, args.device)
    r["seq"] = args.seq
    r["e_run"] = args.e_run; r["d_run"] = args.d_run
    r["note"] = ("B−A = 现 J3（伤+遮挡）；C−A = 静态本体伤（建图侧未隔离的直接证据）；"
                 "B−C = 动态层遮挡。在线静态行**非**逐位冻结（与离线不同）。")
    Path(REPO / args.out).write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
