#!/usr/bin/env python
"""judge_dynport.py — DynPort L1 判据机（prereg_dynport_L1.md §3；数字零手抄，仿 judge_p0.py）。

输入：E/D/C− 三臂的 run 目录（各含 config.yml + point_cloud/final + plot/trj）。
做法（复用 dyn_probe 的渲染与 frame_metrics，与 B 线同口径）：
  1. 用 `dyn_probe.Run` 载入各臂最终地图（**同帧、同位姿外参、canonical 掩码**）；
  2. 逐帧渲染 → `frame_metrics` 产 dyn_bad_psnr / dyn_bad_dl1 / static_psnr；
  3. **M_bad 由 E 臂（erase 基线）定义**（中性参照；与 B 线一致），三臂共用同一 M_bad ⇒ 配对；
  4. 逐帧配对 D−E / C−−D 求差/比，取 median+IQR；机械应用 J1–J9。

**口径（prereg §3 逐条对应）**：
- 方法输入（运行期掩码）与评估分区（canonical）**两源分离**（G1-M2）；本判据机只用 canonical 划分区。
- 主读数 = M_bad 子集（dyn_bad_psnr/dyn_bad_dl1）；J3 静态区用 static_psnr。
- 每序列独立判定；禁全局均值一把过。

用法：
  python scripts/dynport/judge_dynport.py \
    --arms E=<runD_dir> D=<runD_dir> Cneg=<run_dir> \
    --seq crowd2 --out results/dynport/evidence/dynport_L1_judgments.json
"""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from utils.dynport_causal_log import load_snapshot  # noqa: E402
_spec = importlib.util.spec_from_file_location("dyn_probe", REPO / "scripts/02_analysis/dyn_probe.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

# ── 先锁阈值（prereg §3）──
J1_MAIN_DB = 2.5        # J1 动态区 bad-PSNR 增益
J1_BOUND_LO = 1.0       # 边界下界 = 40%
J2_DL1_RATIO = 0.70     # J2 深度误差比
J3_STATIC_DB = 0.25     # J3 静态区双边带
J7_CTRL_MIN = 1.15      # J7 阴性对照判别力
J8_ATE_MARK_CM = 1.0    # J8 L1 标记线（硬门在 L2）


def _med_iqr(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    if not xs:
        return None, None, 0
    a = np.asarray(xs, dtype=float)
    return (round(float(np.median(a)), 4),
            round(float(np.percentile(a, 75) - np.percentile(a, 25)), 4), len(a))


def _load_arm(run_dir, frames, device):
    run = probe.Run(run_dir, device=device)
    pc = probe.PackedPC(run.gaussians)          # 只读渲染视图（在线最终地图，无动态层附加）
    recs = {}
    for e in frames:
        fd = run.frame_data(e)
        if fd is None:
            continue
        gt_i, gt_d, w2c = fd
        cam = run.camera(e, w2c)
        pkg = probe.render_once(run, cam, pc)
        if pkg is None or pkg.get("render") is None:
            continue
        dyn = run.frame_mask(e)
        recs[e] = (run, pkg, gt_i, gt_d, dyn)
    return run, recs


class _StaticPlusDynPC:
    """静态底图 + 快照动态层 的只读渲染视图（因果仪器；等价 PackedPC 但静态集可切片）。"""

    def __init__(self, base_model, keep_mask, snapshot):
        m = base_model
        km = np.asarray(keep_mask, dtype=bool)
        self.max_sh_degree = m.max_sh_degree
        self.active_sh_degree = m.active_sh_degree
        _xyz = m.get_xyz.detach(); _op = m.get_opacity.detach()
        _sc = m.get_scaling.detach(); _ro = m.get_rotation.detach(); _ft = m.get_features.detach()
        kt = torch.as_tensor(km, device=_xyz.device)
        self.static = (_xyz[kt], _op[kt], _sc[kt], _ro[kt], _ft[kt])
        self.n_static = int(self.static[0].shape[0])
        self.set_dynamic(_snap_to_dyn(snapshot))

    def set_dynamic(self, dyn):
        if dyn is None:
            (self.get_xyz, self.get_opacity, self.get_scaling,
             self.get_rotation, self.get_features) = self.static
            self.n_dyn = 0
            return
        self.get_xyz = torch.cat([self.static[0], dyn["xyz"]], 0)
        self.get_opacity = torch.cat([self.static[1], dyn["opacity"]], 0)
        self.get_scaling = torch.cat([self.static[2], dyn["scaling"]], 0)
        self.get_rotation = torch.cat([self.static[3], dyn["rotation"]], 0)
        self.get_features = torch.cat([self.static[4], dyn["features"]], 0)
        self.n_dyn = int(dyn["xyz"].shape[0])


def _snap_to_dyn(snapshot):
    """快照（raw 参数）→ 渲染用激活值 dict。"""
    if snapshot is None or int(snapshot["xyz"].shape[0]) == 0:
        return None
    dev = "cuda"
    xyz = torch.as_tensor(snapshot["xyz"], dtype=torch.float32, device=dev)
    opa = torch.sigmoid(torch.as_tensor(snapshot["opa"], dtype=torch.float32, device=dev))
    sc = torch.exp(torch.as_tensor(snapshot["log_scale"], dtype=torch.float32, device=dev))
    ro = torch.nn.functional.normalize(
        torch.as_tensor(snapshot["rot"], dtype=torch.float32, device=dev), dim=1)
    fd = torch.as_tensor(snapshot["f_dc"], dtype=torch.float32, device=dev)   # (N,1,3)
    return {"xyz": xyz, "opacity": opa, "scaling": sc, "rotation": ro, "features": fd}


def _load_arm_causal(run_dir, frames, device, snapshot_pose=True):
    """因果仪器：静态底图（最终 PLY 去动态行）+ 每评估帧最近 ≤e 快照动态层。

    `snapshot_pose=True`（旧 `--causal`）：用**快照位姿**渲染。实测该口径对**所有**臂施加
    与帧 e 位姿的偏差（底图本身换位姿 −4.0/−3.3/−8.3 dB，2026-10-07 位姿控制）⇒ 测的是位姿误差。
    `snapshot_pose=False`（新 `--samepose`，2026-10-07 amend）：用**帧 e 最终轨迹位姿**渲染
    （= 离线算子 4D 交付的真实消费口径）。两者**禁混引**。
    """
    run = probe.Run(run_dir, device=device)
    cdir = Path(run_dir) / "dynport_causal"
    drow = cdir / "dynamic_rows.npy"
    if not drow.exists():
        # E 臂（erase 基线）无动态层 ⇒ 最终地图即静态底图，直接走普通渲染
        return _load_arm(run_dir, frames, device)
    is_dyn = np.load(drow)
    keep = ~is_dyn
    snaps = sorted(cdir.glob("frame_*.npz"))
    snap_ids = [int(p.stem.split("_")[1]) for p in snaps]
    recs = {}
    for e in frames:
        fd = run.frame_data(e)
        if fd is None:
            continue
        gt_i, gt_d, w2c = fd
        dyn = run.frame_mask(e)
        # 最近 ≤ e 的快照（严格因果）
        cand = [i for i, fid in enumerate(snap_ids) if fid <= e]
        if not cand:
            continue
        snap = load_snapshot(snaps[max(cand)])
        pc = _StaticPlusDynPC(run.gaussians, keep, snap)      # 静态底图 + 快照动态层
        if snapshot_pose:
            # 旧口径（`--causal`）：用快照位姿渲染
            c2w = np.asarray(snap["c2w"], dtype=np.float64)
            w2c_s = np.linalg.inv(c2w)
            cam = run.camera(e, w2c_s)
        else:
            # 新口径（`--samepose`）：用帧 e 最终轨迹位姿（消位姿混杂）
            cam = run.camera(e, w2c)
        pkg = probe.render_once(run, cam, pc)
        if pkg is None or pkg.get("render") is None:
            continue
        recs[e] = (run, pkg, gt_i, gt_d, dyn)
    return run, recs



def _frame_metrics_with_bad(run, pkg, gt_i, gt_d, dyn, bad_depth):
    """单帧：有 bad_depth（E 臂渲染深度）时算 M_bad 子集指标。"""
    bm = probe.bad_mask_of(bad_depth, gt_d, dyn, tol_m=0.10) if bad_depth is not None else None
    return probe.frame_metrics(run, 0, pkg, gt_i, gt_d, dyn, bad_mask=bm)


def derive_eval_frames(run_dir):
    """从 run 的 console.log 解析该 run 的评估帧（`Evaluating ATE at frame: N`）。

    **不是**"看结果指标选帧"——这是 run 自身的协议帧（由 save_trj_kf_intv 与关键帧日程决定，
    与任务无关）；用它避免手抄帧号（判据先锁：帧集须来自 run 自带日程，非人工挑）。
    """
    import re
    c = Path(run_dir) / "console.log"
    if not c.exists():
        return []
    ids = sorted(set(int(m) for m in re.findall(r"Evaluating ATE at frame:\s*(\d+)", c.read_text())))
    return ids


def _static_body_delta(d_run_dir, e_run_dir, common_frames, device):
    """D 臂**仅静态行**（去动态层）vs E 臂底图 的逐帧 static PSNR Δ（构造诊断，G1 v4 major#5）。

    E 臂底图即"全静态"参照；D 臂静态行逐位冻结 ⇒ Δ≡0 证明算子不改静态本体。诊断键，不入出口。
    """
    d_run = probe.Run(d_run_dir, device=device)
    e_run = probe.Run(e_run_dir, device=device)
    cdir = Path(d_run_dir) / "dynport_causal"
    drow = cdir / "dynamic_rows.npy"
    if not drow.exists():
        return []
    keep = ~np.load(drow)
    out = []
    for e in common_frames:
        fd = d_run.frame_data(e)
        if fd is None:
            continue
        gt_i, gt_d, w2c = fd
        dyn = d_run.frame_mask(e)
        cam = d_run.camera(e, w2c)
        pcD = _StaticPlusDynPC(d_run.gaussians, keep, None)     # D 仅静态行
        pcE = probe.PackedPC(e_run.gaussians)                   # E 全静态（= R0 底图）
        pkgD = probe.render_once(d_run, cam, pcD)
        pkgE = probe.render_once(e_run, cam, pcE)
        if pkgD is None or pkgE is None:
            continue
        sD = probe.frame_metrics(d_run, e, pkgD, gt_i, gt_d, dyn).get("static_psnr")
        sE = probe.frame_metrics(e_run, e, pkgE, gt_i, gt_d, dyn).get("static_psnr")
        if sD is not None and sE is not None:
            out.append(sD - sE)
    return out


def judge(arms, frames, device="cuda:0", causal=False, samepose=False):
    loaded, metrics = {}, {}
    if samepose:
        loader = lambda rd, fr, dv: _load_arm_causal(rd, fr, dv, snapshot_pose=False)
    elif causal:
        loader = lambda rd, fr, dv: _load_arm_causal(rd, fr, dv, snapshot_pose=True)
    else:
        loader = _load_arm
    for name, rd in arms.items():
        run, recs = loader(rd, frames, device)
        loaded[name] = recs
    # E 臂渲染深度（定义 M_bad 的中性参照）。**fail-loud**（G4-C6）：缺 E 臂 ⇒ M_bad 会静默变
    # None（口径漂移）⇒ 直接报错，不静默降级。
    if "E" not in arms:
        raise SystemExit("[judge_dynport] 缺 E 臂（= M_bad 的中性参照，映射 R0）；"
                         "禁止静默无参照运行")
    if not loaded.get("E"):
        raise SystemExit(f"[judge_dynport] E 臂无可用帧（run={arms['E']}）⇒ M_bad 参照缺失，"
                         "疑似路径/数据错误")
    e_depth = {e: loaded["E"][e][1]["depth"] for e in loaded["E"]}
    for name, recs in loaded.items():
        metrics[name] = {}
        for e, (run, pkg, gt_i, gt_d, dyn) in recs.items():
            bm = probe.bad_mask_of(e_depth.get(e), gt_d, dyn, tol_m=0.10) if e in e_depth else None
            metrics[name][e] = probe.frame_metrics(run, e, pkg, gt_i, gt_d, dyn, bad_mask=bm)
    common = sorted(set.intersection(*[set(metrics[n]) for n in metrics])) if metrics else []

    def paired(a, b, key):
        out = []
        for e in common:
            va, vb = metrics[a][e].get(key), metrics[b][e].get(key)
            if va is not None and vb is not None:
                out.append((va, vb))
        return out

    res = {"seq": None, "n_common_frames": len(common), "n_eval_frames": len(frames), "arms": list(arms)}
    d_psnr = [va - vb for va, vb in paired("D", "E", "dyn_bad_psnr")]
    dl1_ratio = [va / vb for va, vb in paired("D", "E", "dyn_bad_dl1_cm") if vb]
    d_stat = [va - vb for va, vb in paired("D", "E", "static_psnr")]
    d_full = [va - vb for va, vb in paired("D", "E", "full_psnr")]   # J3 的 Δfull 子句落点（G1-M1）
    j1m, j1i, _ = _med_iqr(d_psnr)
    j2m, j2i, _ = _med_iqr(dl1_ratio)
    j3m, j3i, _ = _med_iqr(d_stat)
    j3fm, j3fi, _ = _med_iqr(d_full)
    bad_px = [metrics["E"][e].get("dyn_bad_px") for e in common
              if metrics["E"][e].get("dyn_bad_px") is not None]
    j6m, _j6i, _ = _med_iqr(bad_px)
    res["J1_bad_psnr_delta"] = {"median": j1m, "iqr": j1i}
    res["J2_bad_dl1_ratio"] = {"median": j2m, "iqr": j2i}
    res["J3_static_delta"] = {"median": j3m, "iqr": j3i}
    res["J3_full_delta"] = {"median": j3fm, "iqr": j3fi}   # Δfull（G1-M1 机械落点）
    # J5 两态核验（prereg §3）：算子**启用/停用**两态 PSNR max|Δ|。停用态输出 ≡ 底图（逐位，J9）
    # ⇒ 两态差 = D（启用 R1）vs E（底图）的逐帧 full_psnr 最大绝对差。>0.01 dB ⇒ 机制真起作用
    # （G2 L3 major#1：原 `J5_two_state_off_eq_base` 键实为 J9 的逐位 claims，未做 PSNR 两态核验）。
    res["J5_two_state_full_psnr_maxabs"] = max(
        (abs(va - vb) for va, vb in paired("D", "E", "full_psnr")), default=None)
    res["J6_bad_px_median"] = j6m                          # J6 的 bad_px 落点（G1-次要）
    # ── samepose 仪器（2026-10-07 amend，§12 v4）：全臂帧 e 位姿 + 最近 ≤e 快照层 ──
    # 与上列同源（同一 metrics）但**仅在 samepose 模式下**作为**出口键**；非 samepose 时勿引。
    res["instrument_samepose"] = bool(samepose)
    if samepose:
        res["J1_samepose_bad_psnr_delta"] = {"median": j1m, "iqr": j1i}
        res["J2_samepose_bad_dl1_ratio"] = {"median": j2m, "iqr": j2i}
        res["J3_samepose_static_delta"] = {"median": j3m, "iqr": j3i}
        # §4 J3 的 Δfull 子句（`static ∈ ±0.25 ∧ Δfull ≥ −0.25`）在同帧口径下的落点
        # （G2 L3 major：原出口 `j3_ok` 只消费 static 子句，Δfull 子句未回接；此处补键）。
        res["J3_samepose_full_delta"] = {"median": j3fm, "iqr": j3fi}
        # 静态本体诊断（G1 v4 major#5）：D 臂**仅静态行**（去动态层）的 static Δ —— 直接测
        # "冻结静态"构造。Δ≡0 ⇒ 静态行未动；**诊断键**（构造恒真倾向，不入出口/不作 PASS 票）。
        if "D" in arms:
            d_body = _static_body_delta(arms["D"], arms["E"], common, device)
            res["J3_samepose_static_body_delta"] = {"median": _med_iqr(d_body)[0],
                                                    "note": "only-static-rows render; construct-diagnostic"}
    # J7 阴性对照：C− vs D 的 bad dl1 比
    if "Cneg" in metrics:
        c_ratio = [va / vb for va, vb in paired("Cneg", "D", "dyn_bad_dl1_cm") if vb]
        cm, ci, _ = _med_iqr(c_ratio)
        res["J7_neg_control_dl1_ratio"] = {"median": cm, "iqr": ci}
    else:
        res["J7_neg_control_dl1_ratio"] = {"median": None}
    # J6（prereg §3）：配对可用帧 ≥50% **且** bad_px 中位 >0。G2 整改：原仅 `>=1` 帧，改 ≥50%（帧覆盖）。
    _cov = (len(common) / len(frames)) if frames else 0.0
    res["J6_frame_coverage"] = round(float(_cov), 4)
    res["J6_judgeable"] = bool(_cov >= 0.5 and j6m is not None and j6m > 0)
    # ⚠ 本判据机只算**渲染类**判据（J1/J2/J3/J6/J7）。**完整出口**（prereg §4：J1∧J2∧J3∧J5∧J9）
    #   还须 J4（计时，工件 backend_timing.json）/J5（计数，dynport_counters.csv）/J8（ATE，
    #   tables/tracking_raw.csv）/J9（off≡主线）——由 `collect_L1.py` 汇总。此处 `render_exit`
    #   仅为**渲染子集**指示，**不是**最终出口；判决不得据它单独下 PASS（避免与锁定规则漂移）。
    res["render_exit"] = ("render_subset_ok" if (j1m is not None and j1m >= J1_MAIN_DB
                          and j2m is not None and j2m <= J2_DL1_RATIO
                          and j3m is not None and abs(j3m) <= J3_STATIC_DB
                          and j3fm is not None and j3fm >= -J3_STATIC_DB) else "render_subset_not_ok")
    res["locked_thresholds"] = {"j1_main_db": J1_MAIN_DB, "j2_dl1_ratio": J2_DL1_RATIO,
                                "j3_static_db": J3_STATIC_DB, "j7_ctrl_min": J7_CTRL_MIN}
    res["J3_in_locked_exit"] = True      # J3 **在** prereg §4 锁定出口内（J1∧J2∧J3∧J5∧J9）
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", required=True, help="name=run_dir ...")
    ap.add_argument("--seq", required=True)
    ap.add_argument("--frames", default=None, help="逗号分隔；缺省用 E 臂 config 的评估帧")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--causal", action="store_true",
                    help="旧因果仪器（静态底图 + 每帧快照动态层 + **快照位姿**）；位姿混杂，仅诊断")
    ap.add_argument("--samepose", action="store_true",
                    help="同帧位姿仪器（全臂帧 e 最终轨迹位姿 + 最近 ≤e 快照层）= §12 v4 出口口径")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    arms = dict(a.split("=", 1) for a in args.arms)
    if args.frames:
        frames = [int(x) for x in args.frames.split(",")]
    else:
        # 缺省：从 E 臂 run 自带日程取评估帧（禁人工挑帧；须有 E 臂）
        if "E" not in arms:
            raise SystemExit("须给 --frames 或含 E 臂（从 run console 取日程帧）")
        frames = derive_eval_frames(arms["E"])
        if not frames:
            raise SystemExit(f"无法从 {arms['E']}/console.log 解析评估帧；请显式 --frames")
    print(f"[judge_dynport] frames = {frames}")
    out = judge(arms, frames, args.device, causal=args.causal, samepose=args.samepose)
    out["seq"] = args.seq
    if args.samepose:
        out["instrument"] = "samepose_causal"
    elif args.causal:
        out["instrument"] = "causal_snapshot_poseconfounded"
    else:
        out["instrument"] = "final_map"
    # 方法学注记（§12 v4）：**出口口径 = samepose**（全臂帧 e 位姿 + 最近 ≤e 快照层）；
    # 旧 `--causal`（快照位姿）与 `final_map`（合并图末帧层）均为**诊断**口径，禁进出口/禁混引。
    out["instrument_note"] = {
        "samepose_causal": "出口口径（§12 v4）：全臂帧 e 位姿 + 最近 ≤e 快照层；J1/J2/J3 同源",
        "causal_snapshot_poseconfounded": "诊断口径：快照位姿（位姿混杂 −4~−8 dB），禁进出口",
        "final_map": "诊断口径：合并图 + 末帧动态层（时切片伪影），禁进出口",
    }[out["instrument"]]
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"[judge_dynport] {args.seq}: instrument={out['instrument']} render_exit={out['render_exit']} "
          f"J1={out['J1_bad_psnr_delta']['median']} "
          f"J2={out['J2_bad_dl1_ratio']['median']} J3={out['J3_static_delta']['median']}")
    print(f"  → {args.out}")


if __name__ == "__main__":
    main()
