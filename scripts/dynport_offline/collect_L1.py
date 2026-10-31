#!/usr/bin/env python
"""collect_L1.py — DynPort-Offline L1 汇总器（跑判据机双仪器 + 落 manifest；数字零手抄）。

与在线版 `scripts/dynport/collect_L1.py` 的差异（prereg §7）：
  - 臂 = R0（底图，映射 judge 的 `E`）/ R1（修复，`D`）/ C−（`Cneg`）；
  - J4 = 离线预算报数（读各臂 `repair_timing.json` 的 `repair_wall_s`）；
  - J5 = 算子计数 + 两态差（`repair_timing.json` 的 `vitality`）；
  - J8 = 构造核验（R1/C− 的 `plot/trj_full_final.json` 与 R0 逐位一致）；
  - J9 = default-off 字节核验（`repair_timing.json.bit_identical`）。

用法：
  python scripts/dynport_offline/collect_L1.py \
      --root results/dynport_offline/L1 --seq crowd2 balloon2 person_tracking2 \
      --base-root results/paper2_fulltable --out-dir results/dynport_offline/evidence
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts" / "dynport"))
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("judge_dynport", REPO / "scripts/dynport/judge_dynport.py")
jd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jd)


def latest_run(root, seq: str, arm: str):
    """在单个 root（或 root 列表，L3 跨批复用）下定位 <seq>_<arm> 算子输出目录。"""
    roots = root if isinstance(root, (list, tuple)) else [root]
    cands = []
    for r in roots:
        cands += list(Path(r).glob(f"{seq}_{arm}/datasets_*/**/seed_*/[0-9]*/"))
    cands = sorted(cands, key=lambda p: p.stat().st_mtime)
    if not cands:  # 也接受直接落 <root>/<seq>_<arm>/ 的算子输出目录
        for r in roots:
            cands += list(Path(r).glob(f"{seq}_{arm}"))
        cands = sorted(cands, key=lambda p: p.stat().st_mtime)
    return cands[-1] if cands else None


def _rel(p):
    """manifest 指针用 repo 相对路径（可移植；G2：原为远程绝对路径）。"""
    try:
        return str(Path(p).resolve().relative_to(REPO.resolve()))
    except ValueError:
        return str(p)


def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_timing(run_dir):
    f = Path(run_dir) / "repair_timing.json"
    return json.load(open(f)) if f.exists() else {}


def _read_counters(run_dir):
    import csv
    f = Path(run_dir) / "dynport_counters.csv"
    if not f.exists():
        return {}
    rows = list(csv.DictReader(open(f)))
    if not rows:
        return {}
    out = {k: max(int(r[k]) for r in rows) for k in ("case1_hits", "cond1_deleted", "cond2_deleted")}
    # 动态层**峰值**规模（n_buf 逐帧）：J5 非退化核验用峰值，不用末值——
    # Cond2 寿命删在运行末清空旧 lineage ⇒ 末值（timing.n_dyn）是残量，非"机制产生过多少动态"。
    try:
        out["n_buf_peak"] = max(int(r.get("n_buf", 0) or 0) for r in rows)
    except (KeyError, ValueError):
        out["n_buf_peak"] = 0
    return out


def _trj_identical(r1_dir, r0_dir):
    """J8 构造核验：R1 的 trj 与 R0 逐位一致（SHA256）。"""
    a = Path(r1_dir) / "plot" / "trj_full_final.json"
    b = Path(r0_dir) / "plot" / "trj_full_final.json"
    if not (a.exists() and b.exists()):
        return None
    return _sha256(a) == _sha256(b)


def _base_ply_bytes(run_dir):
    p = Path(run_dir) / "point_cloud" / "final_after_opt" / "point_cloud.ply"
    if not p.exists():
        p = Path(run_dir) / "point_cloud" / "final" / "point_cloud.ply"
    return p


def compute_locked_exit(render, timing_r1, ctr_r1, j8_ok, j4_ratio, j9_off=None, j5_off_eq_base=None):
    """prereg §4 锁定出口（离线语义，§12 v4 口径）：PASS 实质 = J3∧J1∧J2；J5/J6/J9 守门。

    2026-10-07 §12 v4：J1/J2/J3 一律取 **samepose** 键（同帧位姿 4D 因果口径）；旧 `causal`
    （快照位姿）与 `final_map`（合并图末帧层）为诊断口径，**不进出口**。
    G2 整改（2026-10-07）：J5 补全三计数 + 非退化（峰值）；J9 **batch 级** fail-loud（键缺 ⇒ not_run）。
    `j9_off`/`j5_off_eq_base` = **批次级**停用态核验（prereg G4-C8：crowd2 单次即证接线，全批共享）。
    """
    j1, j2, j3 = render.get("J1"), render.get("J2"), render.get("J3")
    j1_ok = j1 is not None and j1 >= 2.5
    j1_bound = j1 is not None and 1.0 <= j1 < 2.5
    j1_fail = j1 is not None and j1 < 1.0
    j2_ok = j2 is not None and j2 <= 0.70
    # J3（prereg §3/§4）：**双边带**静态 ∈ ±0.25 **且** Δfull ≥ −0.25（G2 L3 major#2：原只消费
    # static 子句，Δfull 子句（judge 产 `J3_samepose_full_delta`）未回接作用路径）。
    j3_full = render.get("J3_full")
    j3_full_ok = j3_full is not None and j3_full >= -0.25
    j3_static_ok = j3 is not None and abs(j3) <= 0.25
    j3_ok = j3_static_ok and j3_full_ok
    # J5（prereg §3）：三计数全 >0 **且** 动态层**峰值**规模落 [1e3, cap]（非退化）**且**
    # 两态 PSNR max|Δ| > 0.01 dB（机制真起作用；G2 L3 major#1：原用逐位 off≡底图替代，非 PSNR 两态）。
    n_dyn_peak = int(ctr_r1.get("n_buf_peak", 0) or 0)
    cap = int(timing_r1.get("cap", 50000) or 50000)
    counters_ok = all(int(ctr_r1.get(k, 0) or 0) > 0
                      for k in ("case1_hits", "cond1_deleted", "cond2_deleted"))
    two_state = render.get("J5_two_state_full_psnr_maxabs")
    two_state_ok = two_state is not None and two_state > 0.01
    j5_ok = counters_ok and (1000 <= n_dyn_peak <= cap) and two_state_ok
    # J9（prereg §3 守门）：**停用态核验 run**（`--disable` 输出 ≡ 底图逐位）。
    # **batch 级**（G4-C8：crowd2 单次 off run 即证接线真通，全批共享）——证据 = off run 的
    # `repair_timing.json.bit_identical`，**不是** enabled 臂 timing（后者无该键）。
    # G2 整改：键缺 ⇒ `None`（not_run），**不默认 True**。
    j9_ok = (j9_off is True)
    j9_status = ("pass" if j9_off is True else ("fail" if j9_off is False else "not_run"))
    j6_ok = render.get("J6", True)
    return {"J1": j1, "J2": j2, "J3": j3,
            "J3_full": j3_full, "J3_full_ok": j3_full_ok, "J3_static_ok": j3_static_ok,
            "J3_samepose_basis": render.get("J3_samepose_basis"),
            "J4_ratio": round(j4_ratio, 3) if j4_ratio is not None else None,
            "J5": j5_ok, "J5_counters_ok": counters_ok,
            "J5_n_dyn_peak": n_dyn_peak, "J5_n_dyn_final": int(timing_r1.get("n_dyn", 0) or 0),
            "J5_two_state_full_psnr_maxabs": two_state, "J5_two_state_ok": two_state_ok,
            "J5_two_state_off_eq_base": j5_off_eq_base,
            "J6": j6_ok, "J8_trj_identical": j8_ok, "J9": j9_ok, "J9_status": j9_status,
            "pass_substantive": bool(j3_ok and j1_ok and j2_ok),
            "checks": {"J1": j1_ok, "J1_bound": j1_bound, "J1_fail": j1_fail,
                       "J2": j2_ok, "J3": j3_ok, "J3_static": j3_static_ok,
                       "J3_full": j3_full_ok, "J5": j5_ok, "J6": j6_ok, "J9": j9_ok}}


def _resolve_base(base_root, seq):
    """序列名 → R0 底图 run 目录。

    L1：`seq` = 序列名（底图 `r33_rebase_baseline_<seq>_seed0`，seed_0）。
    L2 跨 seed：`seq` = `<name>_seed<N>`（底图 `r33_rebase_baseline_<name>_seed<N>`，seed_<N>）。
    """
    import re
    m = re.match(r"^(.*)_seed(\d+)$", seq)
    if m:
        base_name, sd = f"{m.group(1)}_seed{m.group(2)}", m.group(2)
    else:
        base_name, sd = f"{seq}_seed0", "0"
    cands = sorted((Path(base_root) / f"r33_rebase_baseline_{base_name}").glob(
        f"datasets_bonn/*/seed_{sd}/*/"))
    return cands[-1] if cands else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", nargs="+", default=["results/dynport_offline/L1"],
                    help="算子输出根（可多根，L3 跨批复用 L1_v4+L2+L3）")
    ap.add_argument("--base-root", default="results/paper2_fulltable")
    ap.add_argument("--out-dir", default="results/dynport_offline/evidence")
    ap.add_argument("--seq", nargs="+", default=["crowd2", "balloon2", "person_tracking2"])
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--tag", default="")
    ap.add_argument("--off-seq", default="crowd2",
                    help="批次级停用态核验序列（prereg G4-C8：单次 off run 即证接线，全批共享；默认 crowd2）")
    args = ap.parse_args()
    roots = [Path(r) for r in args.root]
    root = roots[0]  # 兼容：单根语义（OFF 探测等）用首根
    od = Path(args.out_dir)
    od.mkdir(parents=True, exist_ok=True)
    sfx = f"_{args.tag}" if args.tag else ""

    summary, per_seq = {}, {}
    # ── 批次级停用态核验（prereg G4-C8：crowd2 单次 off run 即证接线，全批共享）──────────
    # 证据 = off run 的 bit_identical 与 off PLY ≡ 底图 PLY（逐位）。缺 ⇒ None（not_run，不默认过）。
    off_seq = args.off_seq
    off_dir = None
    for r in roots:
        for cand in (r / f"{off_seq}_OFF", r / f"{off_seq}_off"):
            if cand.exists():
                off_dir = cand
                break
        if off_dir is not None:
            break
    if off_dir is None:
        off_dir = root / f"{off_seq}_OFF"
    batch_j9_off, batch_j5_two_state = None, None
    if off_dir.exists():
        oj = off_dir / "repair_timing.json"
        if oj.exists():
            try:
                batch_j9_off = bool(json.load(open(oj)).get("bit_identical"))
            except Exception:
                batch_j9_off = None
        off_ply = off_dir / "point_cloud" / "final_after_opt" / "point_cloud.ply"
        r0_off = _resolve_base(args.base_root, off_seq)
        if off_ply.exists() and r0_off is not None:
            base_ply = r0_off / "point_cloud" / "final_after_opt" / "point_cloud.ply"
            if base_ply.exists():
                batch_j5_two_state = (_sha256(off_ply) == _sha256(base_ply))

    for seq in args.seq:
        r1 = latest_run(roots, seq, "R1")
        cneg = latest_run(roots, seq, "Cneg")
        r0 = _resolve_base(args.base_root, seq)
        if r1 is None or r0 is None:
            print(f"[collect] {seq}: R0/R1 缺（r0={r0}, r1={r1}）→ 跳过")
            continue
        arms = {"E": str(r0), "D": str(r1)}
        if cneg is not None:
            arms["Cneg"] = str(cneg)
        if len(arms) < 2:
            print(f"[collect] {seq}: 臂不全，跳过")
            continue
        frames = jd.derive_eval_frames(arms["E"])
        if not frames:
            print(f"[collect] {seq}: 无评估帧，跳过")
            continue
        out_c = str(od / f"dynport_offline_L1_{seq}{sfx}_causal.json")
        out_f = str(od / f"dynport_offline_L1_{seq}{sfx}_final.json")
        out_s = str(od / f"dynport_offline_L1_{seq}{sfx}_samepose.json")
        for causal, out in ((True, out_c), (False, out_f)):
            cmd = [sys.executable, str(REPO / "scripts/dynport/judge_dynport.py"),
                   "--arms", *[f"{k}={v}" for k, v in arms.items()],
                   "--seq", seq, "--frames", ",".join(map(str, frames)),
                   "--device", args.device, "--out", out]
            if causal:
                cmd.append("--causal")
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"[collect] {seq} judge({'causal' if causal else 'final'}) rc={r.returncode}\n{r.stderr[-600:]}")
        # §12 v4 出口口径：samepose（全臂帧 e 位姿 + 最近 ≤e 快照层）
        cmd_s = [sys.executable, str(REPO / "scripts/dynport/judge_dynport.py"),
                 "--arms", *[f"{k}={v}" for k, v in arms.items()],
                 "--seq", seq, "--frames", ",".join(map(str, frames)),
                 "--device", args.device, "--samepose", "--out", out_s]
        r = subprocess.run(cmd_s, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[collect] {seq} judge(samepose) rc={r.returncode}\n{r.stderr[-600:]}")
        per_seq[seq] = {"arms": {k: _rel(v) for k, v in arms.items()}, "frames": frames,
                        "causal": _rel(out_c), "final": _rel(out_f), "samepose": _rel(out_s)}
        try:
            cj = json.load(open(out_c)); fj = json.load(open(out_f)); sj = json.load(open(out_s))
            render = {"J1": sj["J1_samepose_bad_psnr_delta"]["median"],
                      "J2": sj["J2_samepose_bad_dl1_ratio"]["median"],
                      "J3": sj["J3_samepose_static_delta"]["median"],
                      # §4 J3 的 Δfull 子句（同帧口径落点；G2 L3 major#2 回接出口）
                      "J3_full": sj.get("J3_samepose_full_delta", {}).get("median"),
                      # §3 J5 两态 PSNR max|Δ|（启用 vs 底图；G2 L3 major#1 回接出口）
                      "J5_two_state_full_psnr_maxabs": sj.get("J5_two_state_full_psnr_maxabs"),
                      "J3_samepose_basis": "samepose_causal(§12 v4)",
                      # 构造诊断（不进出口）：D 仅静态行 vs E 底图（冻结静态核验）
                      "diag_J3_static_body": sj.get("J3_samepose_static_body_delta", {}).get("median"),
                      # 诊断口径（不进出口；仅登记）
                      "diag_J3_final_map": fj["J3_static_delta"]["median"],
                      "diag_J1_causal_snapshotpose": cj["J1_bad_psnr_delta"]["median"],
                      "diag_J2_causal_snapshotpose": cj["J2_bad_dl1_ratio"]["median"],
                      # J6/J7 与出口**同口径**（均取 samepose judge 输出；G2 整改：原 J7 误取 causal）。
                      "J6": sj.get("J6_judgeable"),
                      "J7": sj.get("J7_neg_control_dl1_ratio", {}).get("median"),
                      "n_common_frames": sj.get("n_common_frames"),
                      "n_eval_frames": len(frames),
                      "batch_off_run": str(off_dir) if off_dir.exists() else None}
            t_r1, t_r0 = _read_timing(r1), _read_timing(r0)
            ctr_r1 = _read_counters(r1)
            j8 = _trj_identical(r1, r0)
            # J4 参照线 = 底图 SLAM 全程墙钟；R0 无 repair_timing.json ⇒ 回退读 R1 timing 携带的
            # online_time_s（repair_map 写入，来源同底图 efficiency_raw.csv）。
            online_s = t_r0.get("online_time_s") or t_r1.get("online_time_s")
            j4_ratio = (t_r1.get("repair_wall_s", 0.0) / online_s if online_s else None)
            locked = compute_locked_exit(render, t_r1, ctr_r1, j8, j4_ratio,
                                         j9_off=batch_j9_off, j5_off_eq_base=batch_j5_two_state)
            summary[seq] = {**render, **locked,
                            "repair_wall_s": t_r1.get("repair_wall_s"),
                            "n_dyn": t_r1.get("n_dyn")}
        except Exception as e:
            summary[seq] = {"error": str(e)}

    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        head = None
    manifest = {"experiment": "dynport_offline_L1", "tag": args.tag or None,
                "prereg": "results/dynport_offline/evidence/prereg_dynport_offline_L1.md",
                "date": datetime.now().strftime("%Y-%m-%d"), "head": head,
                "judge": "scripts/dynport/judge_dynport.py",
                "instrument_note": "出口口径 = samepose（全臂帧 e 位姿 + 最近 ≤e 快照层）；"
                                   "causal（快照位姿）与 final-map（合并图末帧层）为诊断口径，禁进出口/禁混引（§12 v4）",
                "arm_map": {"E": "R0 底图（修复前）", "D": "R1 修复后", "Cneg": "C− 错位对照"},
                "batch_off_state": {"off_seq": off_seq,
                                    "off_dir": _rel(off_dir) if off_dir.exists() else None,
                                    "J9_off_bit_identical": batch_j9_off,
                                    "J5_two_state_off_eq_base": batch_j5_two_state,
                                    "note": "J9/J5 两态核验为 batch 级（G4-C8）"},
                "per_seq": per_seq, "summary": summary}
    (od / f"manifest_offline_L1{sfx}.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"→ {od}/manifest_offline_L1{sfx}.json")


if __name__ == "__main__":
    main()
