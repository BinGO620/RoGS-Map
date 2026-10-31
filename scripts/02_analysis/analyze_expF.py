#!/usr/bin/env python
"""analyze_expF.py — 实验 F：0.38 阈值敏感度扫描分析（K8）。

读取 paper2_fulltable 下 r30_conf030 / r30_conf045 / r32_regate038(0.38)
/ baseline 四臂的 tracking_raw.csv，输出逐序列逐 seed 的 ATE（全帧
col 8 与 keyframe col 14），并汇总阈值敏感度表。

0.38 列 = `r32_regate038_*`：2026-09-15 在同代码版本上重建的基线
（原 `r29_framegate_*` 跑于 09-07，早于 SWBA 雅可比修复 a21e0773/
1150fb25，其数字已被 joint_correct/README.md 2.5c 宣布作废）。
详见 `evidence/prereg_f_rebase.md` 与 `analyze_r32.py`。

判据（预注册，见 `evidence/prereg_f_rebase.md` §4.4）：
  门控增益不依赖阈值精确值 —— 若 0.30/0.38/0.45 三档在易序列上的
  gate ATE 差异 < 噪声带（同一序列跨 seed 波动），且 pt1 增益保留，
  则敏感度主张成立。

用法:
  python scripts/02_analysis/analyze_expF.py [--root results/paper2_fulltable]
"""
import argparse
import csv
from pathlib import Path

SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2"]
ARMS = {
    "baseline": "{s}_baseline_seed{k}",
    "gate0.30": "r30_conf030_{s}_seed{k}",
    "gate0.38": "r32_regate038_{s}_seed{k}",
    "gate0.45": "r30_conf045_{s}_seed{k}",
    # void: pre-fix code (2026-09-07); provenance only, do not cite
    "gate0.38_OLD(void)": "r29_framegate_{s}_seed{k}",
}
COL_FULL = 7      # ate_rmse_cm
COL_KF = 13       # keyframe_ate_rmse_cm


def read_ate(root, dirname):
    p = root / dirname / "tables" / "tracking_raw.csv"
    if not p.exists():
        return None
    with open(p) as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        return None
    last = rows[-1]
    try:
        return float(last[COL_FULL]), float(last[COL_KF])
    except (ValueError, IndexError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="results/paper2_fulltable")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.root)

    lines = []
    print(f"{'seq':16s} {'arm':10s} {'n':>2s}  "
          f"{'full_mean':>9s} {'kf_mean':>9s}  per-seed(full)")
    for s in SEQS:
        for arm, pat in ARMS.items():
            full, kf = [], []
            for k in (0, 1, 2):
                r = read_ate(root, pat.format(s=s, k=k))
                if r:
                    full.append(r[0])
                    kf.append(r[1])
            if not full:
                continue
            fm = sum(full) / len(full)
            km = sum(kf) / len(kf)
            print(f"{s:16s} {arm:10s} {len(full):>2d}  "
                  f"{fm:9.3f} {km:9.3f}  "
                  f"{'/'.join(f'{v:.2f}' for v in full)}")
            lines.append([s, arm, len(full), f"{fm:.4f}", f"{km:.4f}",
                          "/".join(f"{v:.4f}" for v in full)])
        print()

    # 敏感度汇总：仅门控三档（易序列 + pt1）
    print("== 阈值敏感度（gate 三档全帧均值，cm）==")
    print(f"{'seq':16s} {'0.30':>7s} {'0.38':>7s} {'0.45':>7s} {'spread':>7s}")
    for s in SEQS:
        vals = {}
        for arm in ("gate0.30", "gate0.38", "gate0.45"):
            full = [read_ate(root, ARMS[arm].format(s=s, k=k))
                    for k in (0, 1, 2)]
            full = [v[0] for v in full if v]
            if full:
                vals[arm] = sum(full) / len(full)
        if len(vals) == 3:
            spread = max(vals.values()) - min(vals.values())
            print(f"{s:16s} {vals['gate0.30']:7.3f} {vals['gate0.38']:7.3f} "
                  f"{vals['gate0.45']:7.3f} {spread:7.3f}")
            lines.append([s, "sensitivity", 3, f"{vals['gate0.30']:.4f}",
                          f"{vals['gate0.38']:.4f}", f"{vals['gate0.45']:.4f}"])

    if args.out:
        with open(args.out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["seq", "arm", "n", "full_mean_cm", "kf_mean_cm", "detail"])
            w.writerows(lines)
        print(f"\nwritten: {args.out}")


if __name__ == "__main__":
    main()
