#!/usr/bin/env python
"""collect_L1.py — 汇总 DynPort L1 批：跑判据机（双仪器）+ 落 verdict/manifest（数字零手抄）。

用法（远程/本地，需 GPU：判据机要渲染）：
  python scripts/dynport/collect_L1.py --root results/dynport/L1 \
      --out-dir results/dynport/evidence [--seq crowd2 balloon2]

做：
  1. 对每个序列，定位 E/D/Cneg 三臂最新 run 目录（`<root>/<seq>_<arm>/datasets_*/**/seed_*/<ts>/`）；
  2. 取各臂 console 的评估帧日程（`derive_eval_frames`）；
  3. 跑判据机**两次**：`--causal`（动态区 J1/J2/J7）与默认 final-map（静态区 J3）；
  4. 汇总逐序列出口 + manifest（HEAD/时间/工件路径/SHA，全部机写）。
"""
import argparse
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


def latest_run(root: Path, seq: str, arm: str, before=None, after=None):
    """`<root>/<seq>_<arm>/datasets_*/**/seed_*/<ts>/` 里按 mtime 取最新；可加时间窗过滤
    （v1/v2 两批 run 目录并存，靠窗口区分）。"""
    import datetime as _dt
    cands = sorted(root.glob(f"{seq}_{arm}/datasets_*/**/seed_*/[0-9]*/"), key=lambda p: p.stat().st_mtime)
    if after is not None:
        cands = [c for c in cands if c.stat().st_mtime >= after]
    if before is not None:
        cands = [c for c in cands if c.stat().st_mtime <= before]
    return cands[-1] if cands else None


def _parse_ts(s):
    import datetime as _dt
    return _dt.datetime.strptime(s, "%Y-%m-%d %H:%M").timestamp() if s else None


def _read_counters(run_dir):
    """J5：active run 的 dynport_counters.csv 计数（case1/cond1/cond2 最大值）。"""
    import csv
    f = Path(run_dir) / "dynport_counters.csv"
    if not f.exists():
        return {}
    rows = list(csv.DictReader(open(f)))
    if not rows:
        return {}
    return {k: max(int(r[k]) for r in rows) for k in ("case1_hits", "cond2_deleted", "cond1_deleted")}


def _read_timing(run_dir):
    """J4②：backend_timing.json 的 dynport_time_s / mapping_time_s。"""
    f = Path(run_dir) / "backend_timing.json"
    if not f.exists():
        return {}
    j = json.load(open(f))
    dt, mt = float(j.get("dynport_time_s") or 0.0), float(j.get("mapping_time_s") or 0.0)
    return {"dynport_time_s": dt, "mapping_time_s": mt,
            "overhead_frac": (dt / mt if mt > 0 else 0.0), "frames": int(j.get("dynport_frames") or 0)}


def _read_ate(root: Path, seq: str, arm: str, run_dir):
    """J8：tracking_raw.csv 的 ate_rmse_cm —— **按 run_dir 的 run_id 匹配行**（表可能含多批 run，
    取首行会混引 v1/v2；D1-027 教训）。"""
    import csv
    f = root / f"{seq}_{arm}" / "tables" / "tracking_raw.csv"
    if not f.exists() or run_dir is None:
        return None
    rid = Path(run_dir).name                     # 时间戳目录名 = run_id
    rows = list(csv.DictReader(open(f)))
    for r in rows:
        if str(r.get("run_id", "")) == rid:
            try:
                return float(r.get("ate_rmse_cm"))
            except (TypeError, ValueError):
                return None
    return None


def compute_locked_exit(seq_data, seq_ate, seq_timing, seq_ctr):
    """prereg §4 锁定出口的机械应用（J1∧J2∧J3∧J5∧J9 ⇒ PASS；[1.0,2.5) 或单序列 ⇒ 边界；
    <1.0 ⇒ FAIL；J4 不过 ⇒ FAIL 在线不可负担）。J8 只报数（硬门在 L2）。J9 结构性由 wiring 单测守。
    """
    j1 = seq_data.get("J1"); j2 = seq_data.get("J2"); j3 = seq_data.get("J3_final")
    ok = lambda c: bool(c)
    j1_ok = j1 is not None and j1 >= 2.5
    j1_bound = j1 is not None and 1.0 <= j1 < 2.5
    j1_fail = j1 is not None and j1 < 1.0
    j2_ok = j2 is not None and j2 <= 0.70
    j3_ok = j3 is not None and abs(j3) <= 0.25
    ctr = seq_ctr.get("D", {})
    j5_ok = ctr.get("case1_hits", 0) > 0 and ctr.get("cond2_deleted", 0) > 0
    t = seq_timing.get("D", {})
    j4_ok = t.get("overhead_frac") is not None and t.get("mapping_time_s", 0) > 0 and \
        t.get("overhead_frac", 1.0) <= 0.15
    return {"J1": j1, "J2": j2, "J3": j3, "J5": j5_ok, "J4_ok": j4_ok,
            "J4_overhead": round(t.get("overhead_frac", 0.0), 3),
            "J8_ate_delta_cm": (round(seq_ate["D"] - seq_ate["E"], 3)
                                if seq_ate.get("D") is not None and seq_ate.get("E") is not None else None),
            "render_ok": j1_ok and j2_ok and j3_ok,
            "checks": {"J1": j1_ok, "J1_bound": j1_bound, "J1_fail": j1_fail,
                       "J2": j2_ok, "J3": j3_ok, "J5": j5_ok, "J4": j4_ok}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="results/dynport/L1")
    ap.add_argument("--out-dir", default="results/dynport/evidence")
    ap.add_argument("--seq", nargs="+", default=["crowd2", "balloon2"])
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--tag", default="", help="批次标签（v1/v2）；写入输出文件名并记 manifest")
    ap.add_argument("--before", default="", help="只取 mtime ≤ 该时刻（YYYY-MM-DD HH:MM）的 run")
    ap.add_argument("--after", default="", help="只取 mtime ≥ 该时刻的 run")
    args = ap.parse_args()
    root = Path(args.root)
    od = Path(args.out_dir)
    od.mkdir(parents=True, exist_ok=True)
    t_before, t_after = _parse_ts(args.before), _parse_ts(args.after)
    sfx = f"_{args.tag}" if args.tag else ""

    summary, per_seq = {}, {}
    for seq in args.seq:
        arms = {}
        for arm in ("E", "D", "Cneg"):
            r = latest_run(root, seq, arm, before=t_before, after=t_after)
            if r is None:
                print(f"[collect] {seq}/{arm}: 无 run 目录，跳过")
                continue
            arms[arm] = str(r)
        if len(arms) < 3:
            print(f"[collect] {seq}: 臂不全（{list(arms)}），跳过")
            continue
        frames = jd.derive_eval_frames(arms["E"])
        if not frames:
            print(f"[collect] {seq}: 无法解析评估帧，跳过")
            continue
        # 动态区（causal）+ 静态区（final-map）
        out_c = str(od / f"dynport_L1_{seq}{sfx}_causal.json")
        out_f = str(od / f"dynport_L1_{seq}{sfx}_final.json")
        for causal, out in ((True, out_c), (False, out_f)):
            cmd = [sys.executable, str(REPO / "scripts/dynport/judge_dynport.py"),
                   "--arms", *[f"{k}={v}" for k, v in arms.items()],
                   "--seq", seq, "--frames", ",".join(map(str, frames)),
                   "--device", args.device, "--out", out]
            if causal:
                cmd.append("--causal")
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"[collect] {seq} judge({'causal' if causal else 'final'}) rc={r.returncode}\n{r.stderr[-500:]}")
        per_seq[seq] = {"arms": arms, "frames": frames,
                        "causal": out_c, "final": out_f}
        try:
            cj = json.load(open(out_c)); fj = json.load(open(out_f))
            render = {"J1": cj["J1_bad_psnr_delta"]["median"],
                      "J2": cj["J2_bad_dl1_ratio"]["median"],
                      "J3_final": fj["J3_static_delta"]["median"],
                      "J7": cj.get("J7_neg_control_dl1_ratio", {}).get("median")}
            seq_ate = {a: _read_ate(root, seq, a, arms.get(a)) for a in ("E", "D")}
            seq_timing = {a: _read_timing(arms[a]) for a in arms}
            seq_ctr = {a: _read_counters(arms[a]) for a in arms}
            locked = compute_locked_exit(render, seq_ate, seq_timing, seq_ctr)
            summary[seq] = {**render, **locked}
        except Exception as e:
            summary[seq] = {"error": str(e)}

    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    except Exception:
        head = None
    manifest = {"experiment": "dynport_L1", "tag": args.tag or None,
                "prereg": "results/dynport/evidence/prereg_dynport_L1.md",
                "date": datetime.now().strftime("%Y-%m-%d"), "head": head,
                "judge": "scripts/dynport/judge_dynport.py",
                "instrument_note": "动态区 J1/J2 用 causal；静态区 J3 用 final-map（禁混引）",
                "per_seq": per_seq, "summary": summary}
    (od / f"manifest_L1{sfx}.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"→ {od}/manifest_L1{sfx}.json")


if __name__ == "__main__":
    main()
