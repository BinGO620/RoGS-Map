#!/usr/bin/env python
"""rd_harness.py — 率失真渲染 harness（复用 canonical render_compare）。

流程（prereg §4.0 口径）：
  1. 读源 run 地图 PLY -> codec 编码（指定位宽）-> 解码 -> 重建 PLY；
  2. 造临时 run 目录（软链 config.yml / plot/trj_full_final.json，写重建 PLY 到
     `point_cloud/final/point_cloud.ply`）；
  3. 调 `scripts/02_analysis/render_compare.py`（--ply final）渲染 + 分区指标；
  4. 收集 render_metrics.json，写一条 R-D 记录（rate = codec bytes + recon PLY bytes）。

零 SLAM 重跑；不改主代码；输出全部落 results/gs_compress/。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts" / "gs_compress"))
os.chdir(REPO)  # dataset_path 是相对路径
from gs_codec import (  # noqa: E402
    read_map, encode, decode, write_recon_ply, roundtrip_stats, Bits, Meta,
)

PY = os.environ.get("PY", sys.executable)


def q_tag(q: float) -> str:
    """百分位→文件名安全标签（0.1 → 01，0.01 → 001）。"""
    s = f"{q:.4f}".rstrip("0").rstrip(".")
    return s.replace(".", "") or "0"


def find_ply(run_dir: str, which: str = "final") -> str | None:
    for cand in (f"point_cloud/{which}/point_cloud.ply",
                 "point_cloud/final_after_opt/point_cloud.ply",
                 "point_cloud/final/point_cloud.ply"):
        p = Path(run_dir) / cand
        if p.exists():
            return str(p)
    return None


def make_recon_run(src_run: Path, recon_ply: str, tag: str, ts: str = "2026-10-04-00-00-00") -> Path:
    dst = REPO / "results" / "gs_compress" / "recon" / tag / ts
    (dst / "point_cloud" / "final").mkdir(parents=True, exist_ok=True)
    (dst / "plot").mkdir(parents=True, exist_ok=True)
    # config.yml 必须真拷贝（render_compare 直接 open），trj 可软链
    shutil.copy2(src_run / "config.yml", dst / "config.yml")
    trj = src_run / "plot" / "trj_full_final.json"
    if not trj.exists():
        raise FileNotFoundError(f"no trj_full_final.json in {src_run}/plot")
    shutil.copy2(trj, dst / "plot" / "trj_full_final.json")
    shutil.copy2(recon_ply, dst / "point_cloud" / "final" / "point_cloud.ply")
    return dst


def run_render(run_dir: Path, out_dir: Path, frames: str | None, device: str,
               max_scale_m: float = 0.0, ply_tag: str = "final", no_static: bool = False) -> dict | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [PY, str(REPO / "scripts" / "02_analysis" / "render_compare.py"),
           "--run-dir", str(run_dir), "--ply", ply_tag, "--out-dir", str(out_dir),
           "--device", device]
    if frames:
        cmd += ["--frames", frames]
    if no_static:
        cmd += ["--no-static", "--no-vacated"]
    if max_scale_m > 0:
        cmd += ["--max-scale-m", str(max_scale_m)]
    print("[rd_harness] $", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=str(REPO))
    mpath = out_dir / "render_metrics.json"
    if r.returncode != 0 or not mpath.exists():
        print(f"[rd_harness] render FAILED rc={r.returncode}", flush=True)
        return None
    return json.loads(mpath.read_text())


def run_baseline(src_run: Path, tag: str, frames: str | None, device: str,
                 max_scale_m: float = 0.0, out_json: Path | None = None,
                 no_static: bool = False) -> dict | None:
    """渲染原始（未压缩）地图，作 R-D 参照。"""
    out_dir = REPO / "results" / "gs_compress" / "render" / f"{tag}_baseline"
    metrics = run_render(src_run, out_dir, frames, device, max_scale_m, ply_tag="final",
                         no_static=no_static)
    rec = {"tag": tag, "run_dir": str(src_run), "kind": "baseline", "render": metrics}
    out_json = out_json or (REPO / "results" / "gs_compress" / "evidence" / "rd" / f"{tag}_baseline.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(rec, indent=2))
    if metrics:
        print(f"[rd_harness] BASELINE {tag} psnr={metrics.get('mean_psnr')} "
              f"static_psnr={metrics.get('mean_static_psnr')} "
              f"ghost_dl1={metrics.get('mean_ghost_excess_depth_l1_cm')}")
    return metrics


def compute_labels(src_run: Path, ply_path: str, frames: list[int], max_frames_label: int = 12) -> dict:
    """零 GPU 计算基元分区标签（GT 深度可见性门控投票）。返回 {labels, meta}。"""
    import yaml
    from partition import load_trj, label_primitives, build_mask_paths
    cfg = yaml.safe_load(open(src_run / "config.yml"))
    cal = cfg["Dataset"]["Calibration"]
    K = np.array([[cal["fx"], 0.0, cal["cx"]], [0.0, cal["fy"], cal["cy"]], [0.0, 0.0, 1.0]])
    W, H = int(cal["width"]), int(cal["height"])
    depth_scale = float(cal.get("depth_scale", 5000.0))
    trj = load_trj(str(src_run / "plot" / "trj_full_final.json"))
    ds_path = cfg["Dataset"].get("dataset_path", "")
    from utils.dynamic_mask_spec import resolve_eval_mask_dir
    mdir, src, legacy = resolve_eval_mask_dir(ds_path)
    assert mdir and not legacy, f"canonical mask required, got {mdir} legacy={legacy}"
    depth_paths = sorted(str(p) for p in (Path(ds_path) / "depth").glob("*.png"))
    # 去畸变映射（与渲染像素空间一致）
    map1x = map1y = None
    if cal.get("distorted", False):
        import cv2
        D = np.array([cal.get("k1", 0.0), cal.get("k2", 0.0),
                      cal.get("p1", 0.0), cal.get("p2", 0.0), cal.get("k3", 0.0)],
                     dtype=np.float64)
        map1x, map1y = cv2.initUndistortRectifyMap(K, D, np.eye(3), K, (W, H), cv2.CV_32FC1)
    all_ids = sorted(trj.keys())
    use = frames if frames else all_ids
    if len(use) > max_frames_label:
        sel = np.linspace(0, len(use) - 1, max_frames_label).round().astype(int)
        use = [use[i] for i in sorted(set(sel.tolist()))]
    mask_paths = build_mask_paths(mdir, use, depth_paths)
    m = read_map(ply_path)
    xyz = np.stack([m["x"], m["y"], m["z"]], 1)
    res = label_primitives(xyz, trj, mask_paths, K, W, H, use,
                           depth_paths=depth_paths, depth_scale=depth_scale,
                           map1x=map1x, map1y=map1y)
    n = m["_n"]
    print(f"[rd_harness] labels: n={n} dyn_support={int(res['labels'].sum())} "
          f"({res['labels'].mean()*100:.1f}%) over {len(use)} frames gt_depth={res['used_gt_depth']}",
          flush=True)
    return res


def compute_visibility(src_run: Path, ply_path: str, nframes: int = 60) -> np.ndarray:
    """稳健"从不可见"掩码（GT 深度门控 + 空洞排除；SLAM 特有结构）。返回 bool(N,)（True=从不可见）。"""
    import yaml
    from partition import load_trj, compute_visibility_counts, robust_never_visible
    cfg = yaml.safe_load(open(src_run / "config.yml"))
    cal = cfg["Dataset"]["Calibration"]
    K = np.array([[cal["fx"], 0.0, cal["cx"]], [0.0, cal["fy"], cal["cy"]], [0.0, 0.0, 1.0]])
    W, H = int(cal["width"]), int(cal["height"])
    depth_scale = float(cal.get("depth_scale", 5000.0))
    trj = load_trj(str(src_run / "plot" / "trj_full_final.json"))
    ds_path = cfg["Dataset"].get("dataset_path", "")
    depth_paths = sorted(str(p) for p in (Path(ds_path) / "depth").glob("*.png"))
    map1x = map1y = None
    if cal.get("distorted", False):
        import cv2
        D = np.array([cal.get("k1", 0.0), cal.get("k2", 0.0), cal.get("p1", 0.0),
                      cal.get("p2", 0.0), cal.get("k3", 0.0)], dtype=np.float64)
        map1x, map1y = cv2.initUndistortRectifyMap(K, D, np.eye(3), K, (W, H), cv2.CV_32FC1)
    all_ids = sorted(trj.keys())
    sel = np.linspace(0, len(all_ids) - 1, min(nframes, len(all_ids))).round().astype(int)
    use = [all_ids[i] for i in sorted(set(sel.tolist()))]
    m = read_map(ply_path)
    xyz = np.stack([m["x"], m["y"], m["z"]], 1)
    info = compute_visibility_counts(xyz, trj, K, W, H, use,
                                     depth_paths=depth_paths, depth_scale=depth_scale,
                                     map1x=map1x, map1y=map1y)
    never = robust_never_visible(info)
    print(f"[rd_harness] visibility: {len(use)} frames, never-visible(robust)="
          f"{int(never.sum())}/{len(never)} ({never.mean()*100:.1f}%) "
          f"[holes={int((info['hit_hole']>0).sum())}]", flush=True)
    return never


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, help="源 run 时间戳目录")
    ap.add_argument("--tag", required=True, help="本记录 tag（如 balloon_base_s0）")
    ap.add_argument("--bits", default="16,8,8,8,8", help="xyz,f_dc,opacity,scale,rot 位宽")
    ap.add_argument("--bits-dyn", default=None, help="分区臂：动态支撑组位宽（缺省=uniform）")
    ap.add_argument("--coarsen", default="dyn", choices=["dyn", "static"],
                    help="分区臂分配方向：dyn=动态组粗（bits 归静态组）；"
                         "static=静态组粗（bits 归动态支撑组、bits-dyn 为静态位宽）")
    ap.add_argument("--importance", default=None,
                    help="重要度分配：给最低 X%% 重要度的基元用 bits_dyn（粗）。"
                         "信号 = opacity_sigmoid × exp(max_scale)（渲染贡献度）。"
                         "例：--importance 0.5 ⇒ 粗化最低贡献的 50%%. 与 --bits-dyn 联用。")
    ap.add_argument("--labels-npz", default=None, help="外部标签文件（.npz, key=labels）")
    ap.add_argument("--alloc-visibility", type=float, default=None,
                    help="轨迹可见性分配：粗化轨迹下可见次数最低的 X%% 基元（SLAM 特有信号）。"
                         "与 --bits-dyn 联用（bits 给高频可见组、bits-dyn 给低频粗化组）。")
    ap.add_argument("--prune-opacity-below", type=float, default=None,
                    help="剪枝：删 opacity(logit) < X 的基元（近不可见；有损端操作点）")
    ap.add_argument("--prune-scale-above", type=float, default=None,
                    help="剪枝：删最大轴 log-scale > X 的巨基元（X 用 log 域；exp 后为米）")
    ap.add_argument("--prune-ghost", action="store_true",
                    help="剪枝：删分区标签==1（动态/残影支撑）的基元（需 GT 深度投票）")
    ap.add_argument("--prune-never-visible", action="store_true",
                    help="剪枝：删**轨迹下从不可见**的基元（GT 深度可见性，SLAM 特有杠杆）")
    ap.add_argument("--dedup-voxel-m", type=float, default=None,
                    help="合并：按体素边长（米）合并近重复基元（保留每体素最高不透明度者）")
    ap.add_argument("--visibility-frames", type=int, default=60,
                    help="可见性投票帧数（--prune-never-visible 用；越多越保守）")
    ap.add_argument("--frames", default=None, help="逗号分隔帧（缺省 render_compare 默认采样）")
    ap.add_argument("--label-frames", default=None, help="标签投票帧（缺省=渲染帧）")
    ap.add_argument("--range-mode", default="full", choices=["full", "robust"],
                    help="v2 乙线：full=v1 逐属性 min/max；robust=重尾感知稳健百分位范围")
    ap.add_argument("--range-q", type=float, default=0.1,
                    help="robust 的尾部百分位（p_q / p_{100-q}）")
    ap.add_argument("--escape", action="store_true",
                    help="robust 下：尾部走外溢通道（全范围同位宽另存）；缺省=clip")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--max-scale-m", type=float, default=0.0)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--keep-recon", action="store_true", help="保留重建 PLY（默认删以省盘）")
    ap.add_argument("--baseline", action="store_true", help="只渲染原始地图（R-D 参照），不压缩")
    ap.add_argument("--no-static", action="store_true",
                    help="跳过静态/残影指标（序列无 dynamic_mask 时，如 TUM held-out）")
    args = ap.parse_args()

    src_run = Path(args.run_dir).resolve()
    if args.baseline:
        run_baseline(src_run, args.tag, args.frames, args.device, args.max_scale_m,
                     no_static=args.no_static)
        return

    bx = [int(x) for x in args.bits.split(",")]
    bits = Bits(xyz=bx[0], f_dc=bx[1], opacity=bx[2], scale=bx[3], rot=bx[4])
    bits_dyn = None
    labels = None
    if args.bits_dyn:
        by = [int(x) for x in args.bits_dyn.split(",")]
        bits_dyn = Bits(xyz=by[0], f_dc=by[1], opacity=by[2], scale=by[3], rot=by[4])

    src_run = Path(args.run_dir).resolve()
    ply = find_ply(str(src_run), "final")
    assert ply, f"no PLY in {src_run}"
    m = read_map(ply)
    n_orig = m["_n"]
    orig_full_bytes = n_orig * 20 * 4   # 20 fields × f32（源 PLY 实际体量）

    # ── 剪枝（有损端操作点）：在编码前删基元 ──
    keep = np.ones(m["_n"], dtype=bool)
    if args.prune_opacity_below is not None:
        keep &= m["opacity"] >= args.prune_opacity_below
    if args.prune_scale_above is not None:
        smax = np.stack([m["scale_0"], m["scale_1"], m["scale_2"]], 1).max(1)
        keep &= smax <= args.prune_scale_above
    if args.prune_ghost:
        lf = [int(x) for x in args.frames.split(",")] if args.frames else None
        lab = compute_labels(src_run, ply, lf)
        keep &= lab["labels"] == 0
    if args.prune_never_visible:
        never = compute_visibility(src_run, ply, args.visibility_frames)
        keep &= ~never
    if args.dedup_voxel_m is not None and args.dedup_voxel_m > 0:
        xyz = np.stack([m["x"], m["y"], m["z"]], 1)
        key = np.floor(xyz / args.dedup_voxel_m).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        nvox = int(inv.max()) + 1
        order = np.argsort(m["opacity"])  # 升序；倒序保留最高不透明度
        seen = np.zeros(nvox, bool)
        ded = np.ones(m["_n"], bool)
        for i in order[::-1]:
            v = inv[i]
            if seen[v]:
                ded[i] = False
            else:
                seen[v] = True
        keep &= ded
    if not keep.all():
        dropped = int((~keep).sum())
        print(f"[rd_harness] prune: dropping {dropped}/{m['_n']} ({dropped/m['_n']*100:.1f}%)", flush=True)
        for k in list(m.keys()):
            if k.startswith("_"):
                continue
            m[k] = m[k][keep]
        m["_n"] = int(keep.sum())

    if bits_dyn is not None:
        if args.alloc_visibility is not None:
            # 轨迹可见性分配：粗化"可见次数最低 X%"的基元 ⇒ labels=1 = 低频组
            import yaml
            from partition import load_trj, compute_visibility_counts
            cfgv = yaml.safe_load(open(src_run / "config.yml"))
            calv = cfgv["Dataset"]["Calibration"]
            Kv = np.array([[calv["fx"], 0.0, calv["cx"]], [0.0, calv["fy"], calv["cy"]], [0.0, 0.0, 1.0]])
            Wv, Hv = int(calv["width"]), int(calv["height"])
            trjv = load_trj(str(src_run / "plot" / "trj_full_final.json"))
            dsv = cfgv["Dataset"].get("dataset_path", "")
            dpv = sorted(str(p) for p in (Path(dsv) / "depth").glob("*.png"))
            m1x = m1y = None
            if calv.get("distorted", False):
                import cv2
                Dv = np.array([calv.get("k1", 0.0), calv.get("k2", 0.0), calv.get("p1", 0.0),
                               calv.get("p2", 0.0), calv.get("k3", 0.0)], dtype=np.float64)
                m1x, m1y = cv2.initUndistortRectifyMap(Kv, Dv, np.eye(3), Kv, (Wv, Hv), cv2.CV_32FC1)
            allv = sorted(trjv.keys())
            nfr = args.visibility_frames
            selv = np.linspace(0, len(allv) - 1, min(nfr, len(allv))).round().astype(int)
            usev = [allv[i] for i in sorted(set(selv.tolist()))]
            mfull = read_map(ply)
            xyzv = np.stack([mfull["x"], mfull["y"], mfull["z"]], 1)
            info = compute_visibility_counts(xyzv, trjv, Kv, Wv, Hv, usev,
                                             depth_paths=dpv, depth_scale=float(calv.get("depth_scale", 5000.0)),
                                             map1x=m1x, map1y=m1y)
            vis = info["hit_vis"].astype(float)
            if not keep.all():
                vis = vis[keep]
            thr = np.quantile(vis, float(args.alloc_visibility))
            labels = (vis <= thr).astype(np.int8)
            print(f"[rd_harness] visibility alloc: coarsen lowest {float(args.alloc_visibility):.0%} "
                  f"visible (n={int(labels.sum())}/{vis.size}, vis median={np.median(vis):.0f})", flush=True)
        elif args.importance is not None:
            # 重要度分配：labels=1 标"最低 X% 重要度"的基元 ⇒ 用 bits_dyn（粗）
            bo = 1.0 / (1.0 + np.exp(-m["opacity"][:, None]))
            scl = np.stack([m["scale_0"], m["scale_1"], m["scale_2"]], 1).max(1, keepdims=True)
            imp = (bo * np.exp(scl)).ravel()
            thr = np.quantile(imp, float(args.importance))
            labels = (imp < thr).astype(np.int8)
            print(f"[rd_harness] importance labels: coarsen lowest {float(args.importance):.0%} "
                  f"(n={int(labels.sum())}/{m['_n']})", flush=True)
        elif args.labels_npz:
            labels = np.load(args.labels_npz)["labels"].astype(np.int8)
        else:
            lf = None
            if args.label_frames:
                lf = [int(x) for x in args.label_frames.split(",")]
            else:
                lf = [int(x) for x in args.frames.split(",")] if args.frames else None
            lab = compute_labels(src_run, ply, lf)
            labels = lab["labels"]

    blob, meta = encode(m, bits, labels=labels, bits_dyn=bits_dyn,
                        alloc="partition" if bits_dyn is not None else "uniform",
                        range_mode=args.range_mode, range_q=args.range_q,
                        escape=args.escape)
    st = roundtrip_stats(blob, meta)
    rec = decode(blob, meta)

    name_core = f"{args.tag}_b{'-'.join(map(str,bx))}"
    if args.range_mode == "robust":
        name_core += f"_rb{q_tag(args.range_q)}" + ("_esc" if args.escape else "_clip")
    if args.dedup_voxel_m:
        name_core += f"_ded{int(round(args.dedup_voxel_m*1000))}mm"
    if args.prune_never_visible:
        name_core += "_pnev"
    if args.prune_ghost:
        name_core += "_pghost"
    if args.prune_opacity_below is not None:
        name_core += f"_popa{args.prune_opacity_below}"
    if args.prune_scale_above is not None:
        name_core += f"_pscl{args.prune_scale_above}"
    if bits_dyn is not None:
        if args.alloc_visibility is not None:
            name_core += f"_pvis{int(float(args.alloc_visibility)*100)}dyn{'-'.join(map(str,by))}"
        elif args.importance is not None:
            name_core += f"_pimp{int(float(args.importance)*100)}dyn{'-'.join(map(str,by))}"
        else:
            name_core += f"_p{args.coarsen}dyn{'-'.join(map(str,by))}"

    rec_ply = REPO / "results" / "gs_compress" / "recon" / f"{name_core}.ply"
    rec_ply.parent.mkdir(parents=True, exist_ok=True)
    write_recon_ply(str(rec_ply), rec, m["_n"])
    recon_bytes = rec_ply.stat().st_size

    ts = "2026-10-04-00-00-%02d" % (abs(hash(name_core)) % 60)
    rundst = make_recon_run(src_run, str(rec_ply), args.tag, ts)
    out_dir = REPO / "results" / "gs_compress" / "render" / name_core
    metrics = run_render(rundst, out_dir, args.frames, args.device, args.max_scale_m,
                         no_static=args.no_static)

    rec_out = {
        "tag": args.tag, "run_dir": str(src_run), "ply": ply,
        "bits": bx, "bits_dyn": by if bits_dyn is not None else None,
        "coarsen": args.coarsen if bits_dyn is not None else None,
        "n": m["_n"], "n_orig": n_orig,
        "prune": {"opacity_below": args.prune_opacity_below, "scale_above": args.prune_scale_above,
                  "ghost": args.prune_ghost, "dropped": int(n_orig - m["_n"])},
        "alloc": meta.alloc,
        "partition_meta": meta.partition_meta,
        "range_mode": args.range_mode, "range_q": args.range_q,
        "escape": bool(args.escape),
        # rate = 压缩码流（解码后 PLY 是渲染输入形态，不是压缩成本；单列记录供审计）
        "codec_bytes": len(blob),
        "codec_bytes_per_prim": len(blob) / max(1, m["_n"]),
        "rate_bytes_per_prim": len(blob) / max(1, m["_n"]),
        "recon_ply_bytes": recon_bytes,
        "orig_full_bytes": orig_full_bytes,
        "orig_render_bytes": n_orig * 14 * 4,
        "ratio_full": orig_full_bytes / max(1, len(blob)),
        "ratio_render14": (n_orig * 14 * 4) / max(1, len(blob)),
        "render": metrics,
    }
    out_json = Path(args.out_json) if args.out_json else (
        REPO / "results" / "gs_compress" / "evidence" / "rd" / f"{name_core}.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(rec_out, indent=2))

    if not args.keep_recon:
        try:
            rec_ply.unlink()
        except OSError:
            pass

    if metrics:
        print(f"[rd_harness] OK {args.tag} bits={bx} "
              f"rate={rec_out['rate_bytes_per_prim']:.2f} B/prim ratio_full={st['ratio_full']:.2f}x "
              f"psnr={metrics.get('mean_psnr')} static_psnr={metrics.get('mean_static_psnr')} "
              f"ghost_dl1={metrics.get('mean_ghost_excess_depth_l1_cm')}")
    print(f"[rd_harness] wrote {out_json}")


if __name__ == "__main__":
    main()
