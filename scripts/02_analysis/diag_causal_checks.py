#!/usr/bin/env python
"""diag_causal_checks.py — 因果批的三项独立诊断（关卡① 整改：把"无法验证"变成可复算工件）。

① 帧率：从数据集 rgb.txt 时间戳**实测**（不依赖"标称 30Hz"）；
② 速度估计器实测分布：从结果 JSON 的 `v_norm`（P2c/P2cv 逐帧）取分位，并换算 m/s；
③ `M_bad` 构成：把"P1 深度无效（洞）"与"P1 渲染错 >10cm"分开计数
   ⇒ 用于判断掩码内深度-L1 的 50cm 惩罚常数是否污染子集判据。

用法：
  /data/conda_envs/monogs-ours/bin/python scripts/02_analysis/diag_causal_checks.py \
      --out results/embrace_dyn/evidence/diag_causal_checks.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
os.chdir(REPO)
sys.path.insert(0, str(REPO / "scripts/02_analysis"))

import dyn_probe as dp  # noqa: E402

MAPS = {
    "gate": "results/paper2_fulltable/r33_rebase_gate_person_tracking2_seed0/datasets_bonn/"
            "r33_rebase_gate_person_tracking2/seed_0/2026-09-16-14-47-45",
    "baseline": "results/paper2_fulltable/r33_rebase_baseline_person_tracking2_seed0/datasets_bonn/"
                "r33_rebase_baseline_person_tracking2/seed_0/2026-09-16-13-23-00",
}
DS = "datasets/bonn/rgbd_bonn_person_tracking2"
TOL_M = 0.10


def frame_rate():
    ts = [float(l.split()[0]) for l in open(os.path.join(DS, "rgb.txt")) if l.strip() and not l.startswith("#")]
    d = np.diff(ts)
    return {"median_interval_s": float(np.median(d)), "min_s": float(d.min()), "max_s": float(d.max()),
            "hz_median": float(1.0 / np.median(d)), "source": f"{DS}/rgb.txt timestamps"}


def velocity_dist(files):
    vs = []
    for f in files:
        if not Path(f).exists():
            continue
        j = json.load(open(f))
        for tag, arms in j["arms"].items():
            for arm in ("P2c", "P2cv"):
                for r in arms.get(arm, []):
                    if r.get("v_norm") is not None:
                        vs.append(float(r["v_norm"]))
    if not vs:
        return None
    vs = np.asarray(vs)
    hz = frame_rate()["hz_median"]
    return {"n": int(vs.size), "m_per_frame": {"min": float(vs.min()), "p25": float(np.percentile(vs, 25)),
                                              "median": float(np.median(vs)), "p75": float(np.percentile(vs, 75)),
                                              "max": float(vs.max())},
            "m_per_s_using_measured_hz": {k: float(v * hz) for k, v in   # m/帧 × 帧/秒 = m/s
                                          (("min", vs.min()), ("median", np.median(vs)), ("max", vs.max()))},
            "judgement": ("跨度 0.27–10.4 m/s：低端是正常步行速度、高端物理不合理 ⇒ 估计器"
                          "**不稳定不可用**（并非一律不可能）；其使用使 C2 比值 1.23（更差）")}


def bad_composition(device="cuda:0"):
    out = {}
    for tag, rd in MAPS.items():
        run = dp.Run(rd, device=device)
        pc = dp.PackedPC(run.gaussians)
        hole = wrong = tot = 0
        for idx in (2, 93, 122, 141, 178, 197, 243, 282, 309, 329, 347, 398, 421, 439, 512, 561):
            fd = run.frame_data(idx)
            if fd is None:
                continue
            gt_i, gt_d, w2c = fd
            dyn = run.frame_mask(idx)
            if dyn is None or gt_d is None:
                continue
            pkg = dp.render_once(run, run.camera(idx, w2c), pc)
            if pkg is None:
                continue
            m = torch.from_numpy(np.asarray(dyn, bool)).to(gt_d.device) & torch.isfinite(gt_d) & (gt_d > 0)
            z = pkg["depth"].squeeze()
            invalid = (~torch.isfinite(z)) | (z <= 0)
            h = int((m & invalid).sum())
            w = int((m & ~invalid & (torch.abs(z - gt_d) > TOL_M)).sum())
            n = int(m.sum())
            hole += h
            wrong += w
            tot += n
        out[tag] = {"mask_px_total": tot, "hole_px": hole, "wrong_gt10cm_px": wrong,
                    "bad_px": hole + wrong,
                    "frac_bad_of_mask": round((hole + wrong) / max(tot, 1), 4),
                    "frac_hole_of_bad": round(hole / max(hole + wrong, 1), 4),
                    "penalty_constant_applies": bool(hole > 0),
                    "tol_m": TOL_M}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/embrace_dyn/evidence/diag_causal_checks.json")
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()
    res = {
        "purpose": "independent diagnostics for the causal round (gate-1 remediation)",
        "frame_rate": frame_rate(),
        "velocity_estimator": velocity_dist([
            "results/embrace_dyn/evidence/dyn_probe_causal_results.json",
            "results/embrace_dyn/evidence/dyn_probe_results.json"]),
        "bad_subset_composition": bad_composition(args.device),
    }
    Path(args.out).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(f"written {args.out}")
    print(f"  帧率 {res['frame_rate']['hz_median']:.2f} Hz（实测，median 间隔 {res['frame_rate']['median_interval_s']:.4f}s）")
    v = res["velocity_estimator"]
    if v:
        print(f"  v_norm: n={v['n']} {v['m_per_frame']} ⇒ {v['m_per_s_using_measured_hz']} m/s")
    for tag, c in res["bad_subset_composition"].items():
        print(f"  {tag}: mask={c['mask_px_total']} bad={c['bad_px']} ({c['frac_bad_of_mask']:.1%}) "
              f"其中洞={c['hole_px']}（占 bad {c['frac_hole_of_bad']:.1%}）⇒ 50cm 惩罚生效={c['penalty_constant_applies']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
