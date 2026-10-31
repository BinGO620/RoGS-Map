#!/usr/bin/env python
"""analyze_r33.py — 论文主表/消融臂重基线（R33）判据核验与重建。

对应《prereg_rebase_arms.md》锁定的 G1–G6。确定性：同一结果树重现同一输出。

用法:
  python scripts/02_analysis/analyze_r33.py [--root results/paper2_fulltable]
"""
import argparse
import csv
import re
import statistics
from pathlib import Path

SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2"]
SEEDS = [0, 1, 2]
COL_FULL, COL_KF = 7, 13
EASY = ["balloon", "crowd", "crowd2", "crowd3"]

# 批间噪声地板（%）：0.30/0.45 臂 seed2 vs seed0/1 的跨批残差，取两臂较大者
NOISE = {"balloon": 8.7, "balloon2": 3.2, "crowd": 10.6, "crowd2": 14.6,
         "crowd3": 1.2, "person_tracking": 12.5, "person_tracking2": 10.5}

ARMS = {"baseline": "r33_rebase_baseline_{s}_seed{k}",
        "swbaonly": "r33_rebase_swbaonly_{s}_seed{k}",
        "final": "r33_rebase_final_{s}_seed{k}",
        "gate": "r33_rebase_gate_{s}_seed{k}"}
PAT_A = re.compile(r"edges free=")
PAT_S = re.compile(r"SWBA kf=[0-9]+: +static_conf=.*>")
PAT_G = re.compile(r"SWBA gate kf=")
PAT_SUB = re.compile(r"^MonoGS: SWBA")

_ap = argparse.ArgumentParser()
_ap.add_argument("--root", default="results/paper2_fulltable")
args = _ap.parse_args()
ROOT = Path(args.root)


def val(d, col=COL_FULL):
    p = ROOT / d / "tables" / "tracking_raw.csv"
    if not p.exists():
        return None
    rows = list(csv.reader(open(p)))
    try:
        return float(rows[-1][col])
    except Exception:
        return None


def stat(pat, s, col=COL_FULL):
    v = [val(pat.format(s=s, k=k), col) for k in SEEDS]
    v = [x for x in v if x is not None]
    return (statistics.mean(v), statistics.stdev(v), v) if len(v) > 1 else (None, None, v)


def counts(tag):
    p = ROOT / f"{tag}.consolelog"
    if not p.exists():
        return None
    a = s = g = sub = 0
    for line in open(p, errors="ignore"):
        if PAT_A.search(line):
            a += 1
        if PAT_S.search(line):
            s += 1
        if PAT_G.search(line):
            g += 1
        if PAT_SUB.match(line):
            sub += 1
    return a, s, g, sub


print("=" * 100)
print("G1 执行判据")
print("=" * 100)
rc0 = set()
bad = []
complete = False
queued = 0
for line in open(ROOT / "r33.done", errors="ignore"):
    m = re.match(r"^(\S+_seed\d+) GPU=\d+ finished rc=0\b", line)
    if m:
        rc0.add(m.group(1))
    m2 = re.match(r"^(\S+_seed\d+) GPU=\d+ finished rc=(\d+)", line)
    if m2 and m2.group(2) != "0":
        bad.append((m2.group(1), m2.group(2)))
    mm = re.search(r": (\d+) jobs queued", line)
    if mm:
        queued = int(mm.group(1))
    if "batch all done" in line:
        complete = True
exp = {f"r33_rebase_{a}_{s}_seed{k}" for a in ARMS for s in SEQS for k in SEEDS}
print(f"  queued={queued}  rc0={len(rc0)}  nonzero={len(bad)}  batch_all_done={complete}")
print(f"  缺失: {sorted(exp - rc0) if exp - rc0 else '无'}   非零退出: {bad if bad else '无'}")

print()
print("=" * 100)
print("G3 生效验证（按臂实例化；四臂判据不同）")
print("=" * 100)
print(f"  {'run':44s} {'applied':>8s} {'skip':>6s} {'gate':>6s} {'^MonoGS: SWBA':>14s}  判定")
g3ok = True
n_checked = 0
for arm in ARMS:
    for s in SEQS:
        for k in SEEDS:
            tag = ARMS[arm].format(s=s, k=k)
            c = counts(tag)
            if c is None:
                print(f"  {tag:44s} (no log)")
                g3ok = False
                continue
            a, sk, g, sub = c
            if arm == "baseline":
                ok = (a == 0 and sk == 0 and g == 0 and sub == 0)
            elif arm in ("final", "swbaonly"):
                ok = (a > 0 and sk == 0 and g > 0 and g >= a)
            else:
                ok = (a > 0 and sk > 0 and (a + sk) <= g <= (a + sk) + 1)
            g3ok = g3ok and ok
            n_checked += 1
            if not ok or n_checked <= 8:   # 打印前 8 个作样例 + 任何不合格
                print(f"  {tag:44s} {a:8d} {sk:6d} {g:6d} {sub:14d}  {'OK' if ok else 'CHECK'}")
print(f"  G3 全过 = {g3ok}  （覆盖 {n_checked}/84 run，逐 run 判定，非抽样）")

print()
print("=" * 100)
print("G5 归因触发器：baseline 臂（SWBA 关 ⇒ 代码惰性）r33 vs 旧批")
print("=" * 100)
print(f"  {'seq':20s} {'Δ(cm)':>8s} {'相对地板→cm':>12s} {'seed内极差':>11s} {'阈值':>8s}  判定")
trig = []
for s in SEQS:
    o = [val(f"{s}_baseline_seed{k}") for k in SEEDS]
    n = [val(ARMS["baseline"].format(s=s, k=k)) for k in SEEDS]
    if any(x is None for x in o + n):
        print(f"  {s:20s} (数据不全)")
        continue
    om, nm = statistics.mean(o), statistics.mean(n)
    d = nm - om
    fc = NOISE[s] / 100 * om
    sp = max(max(o) - min(o), max(n) - min(n))
    th = max(fc, sp)
    ok = abs(d) <= th
    if not ok:
        trig.append(s)
    print(f"  {s:20s} {d:+8.3f} {fc:12.3f} {sp:11.3f} {th:8.3f}  {'在噪声内' if ok else '*** 超出 ***'}")
print(f"  触发: {trig if trig else '无 ⇒ 归因触发器未触发，core-diff 惰性清单无漏判'}")

print()
print("=" * 100)
print("Tab.1 / Tab.3 重建（四臂同批，col8 全帧，3-seed mean±sd）")
print("=" * 100)
T = {}
print(f"  {'seq':20s} {'baseline':>14s} {'swbaonly':>14s} {'final':>14s} {'gate':>14s} {'g/f':>8s} {'g/b':>8s}")
for s in SEQS:
    T[s] = {}
    for a in ARMS:
        T[s][a] = stat(ARMS[a], s)
    f = lambda a: f"{T[s][a][0]:.2f}±{T[s][a][1]:.2f}"
    gf = 100 * (T[s]["gate"][0] - T[s]["final"][0]) / T[s]["final"][0]
    gb = 100 * (T[s]["gate"][0] - T[s]["baseline"][0]) / T[s]["baseline"][0]
    print(f"  {s:20s} {f('baseline'):>14s} {f('swbaonly'):>14s} {f('final'):>14s} {f('gate'):>14s} {gf:+7.1f}% {gb:+7.1f}%")

print()
print("=" * 100)
print("gate 臂同 config 双批复制：r32(09-15) vs r33(09-16) —— 跨批偏移实测")
print("=" * 100)
ds = []
for s in SEQS:

    av = [val(f"r32_regate038_{s}_seed{k}") for k in SEEDS]
    bv = [val(ARMS["gate"].format(s=s, k=k)) for k in SEEDS]
    am, bm = statistics.mean(av), statistics.mean(bv)
    d = bm - am
    ds.append(abs(d))
    print(f"  {s:20s} r32={am:8.4f} r33={bm:8.4f} Δ={d:+8.4f} ({100*d/am:+6.2f}%)")
print(f"  平均|Δ|={statistics.mean(ds):.4f}cm  最大|Δ|={max(ds):.4f}cm")
print("  对照：实验 F 各臂间差 0.05–0.62cm；R32 实测同码散度 0.18–0.62cm")

print()
print("=" * 100)
print("G6 不变量（数字阈值）")
print("=" * 100)
gb = T["person_tracking"]["gate"][0]
bb = T["person_tracking"]["baseline"][0]
print(f"  [pt1 降幅] baseline={bb:.3f} -> gate={gb:.3f} : {100*(bb-gb)/bb:+.1f}%  (阈值 ≥30%)  "
      f"{'PASS' if 100*(bb-gb)/bb >= 30 else 'FAIL'}")
b = [val(f"person_tracking_baseline_seed{k}") for k in SEEDS]
n = [val(ARMS['baseline'].format(s='person_tracking', k=k)) for k in SEEDS]
allb = b + n
print(f"     注意：baseline pt1 6 seed = {sorted(round(x,2) for x in allb)}"
      f"  mean={statistics.mean(allb):.2f} sd={statistics.stdev(allb):.2f}")
print(f"     => 降幅随 baseline 取值: 旧批 {100*(statistics.mean(b)-gb)/statistics.mean(b):+.1f}% / "
      f"新批 {100*(statistics.mean(n)-gb)/statistics.mean(n):+.1f}% / "
      f"合并6seed {100*(statistics.mean(allb)-gb)/statistics.mean(allb):+.1f}%")
bad_easy = [(s, T[s]["gate"][0]) for s in EASY if T[s]["gate"][0] > 5.0]
print(f"  [易序列 ≤5cm] {[(s, round(T[s]['gate'][0],3)) for s in EASY]}")
print(f"     >5cm 的: {bad_easy if bad_easy else '无 -> PASS'}")
print(f"  [易序列单调 0.30<0.38<0.45 同批] —— 见 analyze_r32.py（0.30/0.45 与 r32 同批可比性说明）")
print()
print("=" * 100)
print("pt1 baseline 的批间差 = 抽样噪声还是批次效应？（精确置换检验）")
print("=" * 100)
import itertools
for seq in ("person_tracking", "person_tracking2"):
    o = [val(f"{seq}_baseline_seed{k}") for k in SEEDS]
    n = [val(ARMS["baseline"].format(s=seq, k=k)) for k in SEEDS]
    pool = o + n
    obs = abs(statistics.mean(n) - statistics.mean(o))
    diffs = [abs(statistics.mean([pool[i] for i in c]) -
                 statistics.mean([pool[i] for i in range(6) if i not in c]))
             for c in itertools.combinations(range(6), 3)]
    p = sum(1 for d in diffs if d >= obs - 1e-9) / len(diffs)
    print(f"  {seq}: 旧批 mean={statistics.mean(o):.3f} 新批 mean={statistics.mean(n):.3f} "
          f"差={obs:.3f}cm")
    print(f"    6 seed = {sorted(round(x,2) for x in pool)}  (全部 SWBA-OFF ⇒ 代码同一，可交换)")
    print(f"    精确置换 (C(6,3)=20): p = {p:.2f}  ->  "
          f"{'批间差与抽样噪声不可区分' if p >= 0.05 else '超抽样噪声'}")
    gm = T[seq]["gate"][0]
    print(f"    pt1 降幅随 baseline 取值: 旧批 {100*(statistics.mean(o)-gm)/statistics.mean(o):+.1f}% / "
          f"新批 {100*(statistics.mean(n)-gm)/statistics.mean(n):+.1f}% / "
          f"6-seed 合并 {100*(statistics.mean(pool)-gm)/statistics.mean(pool):+.1f}%")

print()
print("=" * 100)
print("同批 baseline -> swbaonly 跳变 = SWBA 净代价（纯同批，最强证据）")
print("=" * 100)
for s in SEQS:
    b = [val(ARMS["baseline"].format(s=s, k=k)) for k in SEEDS]
    w = [val(ARMS["swbaonly"].format(s=s, k=k)) for k in SEEDS]
    g = [val(ARMS["gate"].format(s=s, k=k)) for k in SEEDS]
    bm, wm, gm = statistics.mean(b), statistics.mean(w), statistics.mean(g)
    rec = 100 * (wm - gm) / (wm - bm) if wm != bm else float("nan")
    print(f"  {s:20s} base {bm:6.2f} -> swbaonly {wm:6.2f} ({100*(wm-bm)/bm:+6.1f}%)  "
          f"逐seed分离={str(max(b) < min(w)):5s}  门控收回 {rec:+6.1f}%")

print()
print("=" * 100)
print("OVERALL: G1 rc0 = %d/%d, G3 = %s, G5 触发 = %s" % (len(rc0), len(exp), g3ok, trig or "无"))
