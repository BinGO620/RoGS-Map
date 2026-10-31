#!/usr/bin/env python
"""analyze_r32.py — 实验 F 重基线（R32）判据核验与分析。

用途：在 r32_regate038_* 批跑完后，机械核验《prereg_f_rebase.md》锁定的判据，
并重出 static_conf 阈值敏感度曲线（0.38 列换成同代码版本的新臂）。

核验项（对应预注册各节）：
  §4.1 执行判据   —— r32.done 中全部 run 的 done 行为 "finished rc=0"
  §4.2 口径判据   —— 主读数取 tracking_raw.csv col 8（ate_rmse_cm，全帧）
  §4.3 生效验证   —— 逐 run 核 (a) 执行 `edges free=` > 0
                     (b) 拦截 `SWBA kf=N:  static_conf=... > ...` > 0
                     (c) gate 数 == (a)+(b)
                     （禁用裸模式 `SWBA kf=`：在恒 skip 的 r25 上仍为 177，
                       恒真，NOTES P23）
  §4.4 判读判据   —— 数字触发条件（pt1 甜点 / 易序列单调 / 定性保证）
                     + 批间噪声地板（0.30/0.45 臂 seed2 跨批残差）
  §4.5 单变量     —— r32 与 r29 的 (a)(b)(c) 计数同量级比照

用法:
  python scripts/02_analysis/analyze_r32.py [--root results/paper2_fulltable]
"""
import argparse
import csv
import re
from pathlib import Path

SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2"]
SEEDS = [0, 1, 2]

# 主表读数列（0-based）：col 7 = ate_rmse_cm（全帧），col 13 = keyframe
COL_FULL = 7
COL_KF = 13

ARMS = {
    "baseline": "r33_rebase_baseline_{s}_seed{k}",
    "gate0.30": "r30_conf030_{s}_seed{k}",
    "gate0.38_OLD": "r29_framegate_{s}_seed{k}",      # 09-07 代码，已作废
    "gate0.38": "r32_regate038_{s}_seed{k}",          # 本批，重建基线
    "gate0.45": "r30_conf045_{s}_seed{k}",
}

# 日志计数模式：必须锚定整行形状（NOTES P22/P23）
PAT_APPLIED = re.compile(r"edges free=")
PAT_SKIP = re.compile(r"SWBA kf=[0-9]+: +static_conf=.*>")
PAT_GATE = re.compile(r"SWBA gate kf=")

# 批间噪声地板（%）：同臂 seed2 vs seed0/1 的跨批残差，取 0.30/0.45 两臂较大者。
# 用途：判定重基线后的臂间差是否超出可复现范围（prereg_f_rebase.md §4.4）。
NOISE_FLOOR = {
    "balloon": 8.7, "balloon2": 3.2, "crowd": 10.6, "crowd2": 14.6,
    "crowd3": 1.2, "person_tracking": 12.5, "person_tracking2": 10.5,
}


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


def count_patterns(root, dirname):
    """返回 (applied, skipped, gate)；consolelog 缺失时返回 None。"""
    p = root / f"{dirname}.consolelog"
    if not p.exists():
        return None
    a = s = g = 0
    for line in open(p, errors="ignore"):
        if PAT_APPLIED.search(line):
            a += 1
        if PAT_SKIP.search(line):
            s += 1
        if PAT_GATE.search(line):
            g += 1
    return a, s, g


def check_done(root, done_name="r32.done"):
    """§G1：done 行须为 finished rc=0。返回 (rc0_tags, bad_tags, queued, complete)。

    行格式为 `<tag> GPU=<n> finished rc=<rc> <ts>`（注意 tag 与 finished 之间有
    GPU= 字段）——只锚定 "finished" 会放过 rc=137，故匹配到 rc 全串。
    """
    p = root / done_name
    rc0, bad, queued, complete = set(), [], 0, False
    if not p.exists():
        return rc0, bad, queued, complete
    for line in open(p, errors="ignore"):
        m = re.match(r"^(\S+_seed\d+) GPU=\d+ finished rc=0\b", line)
        if m:
            rc0.add(m.group(1))
        m2 = re.match(r"^(\S+_seed\d+) GPU=\d+ finished rc=(\d+)", line)
        if m2 and m2.group(2) != "0":
            bad.append((m2.group(1), m2.group(2)))
        if " jobs queued" in line:
            mm = re.search(r": (\d+) jobs queued", line)
            if mm:
                queued = int(mm.group(1))
        if "batch all done" in line:
            complete = True
    return rc0, bad, queued, complete


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="results/paper2_fulltable")
    args = ap.parse_args()
    root = Path(args.root)

    print("=" * 78)
    print("§4.1 执行判据：done 行 finished rc=0")
    print("=" * 78)
    rc0, bad, queued, complete = check_done(root)
    print(f"queued={queued}  rc0={len(rc0)}  nonzero_rc={len(bad)}  batch_all_done={complete}")
    if bad:
        for t, rc in bad:
            print(f"  !! 非零退出: {t} rc={rc}")
    expected = {f"r32_regate038_{s}_seed{k}" for s in SEQS for k in SEEDS}
    missing = sorted(expected - rc0)
    print(f"缺失/未 rc=0 的 run（{len(missing)}）: {missing if missing else '无'}")

    print()
    print("=" * 78)
    print("§4.2 主读数（col 8 全帧 ate_rmse_cm）逐 seed + 均值")
    print("=" * 78)
    table = {}
    for arm, pat in ARMS.items():
        table[arm] = {}
        for s in SEQS:
            per = []
            for k in SEEDS:
                r = read_ate(root, pat.format(s=s, k=k))
                if r:
                    per.append((k, r[0], r[1]))
            if per:
                table[arm][s] = per
    for s in SEQS:
        row = [f"{s:20s}"]
        for arm in ["baseline", "gate0.30", "gate0.38_OLD", "gate0.38", "gate0.45"]:
            per = table.get(arm, {}).get(s)
            if per:
                mean = sum(x[1] for x in per) / len(per)
                row.append(f"{arm}={mean:.4f}(n{len(per)})")
            else:
                row.append(f"{arm}=MISSING")
        print("  ".join(row))

    print()
    print("=" * 78)
    print("§4.3 生效验证（按门实例化 + 整行形状 + 合流等式）")
    print("=" * 78)

    # P23 自检：计数模式必须在"已知退化 run"上返回 applied=0，且在正常 run 上
    # 非零 —— 否则判据恒真（裸模式 `SWBA kf=` 在恒 skip 的 r25 上仍为 177）。
    self_ok = True
    for tag, want_applied in (("r29_framegate_crowd2_seed0", ">0"),
                              ("r25_gate_crowd2_seed0", "=0")):
        c = count_patterns(root, tag)
        naive = None
        p = root / f"{tag}.consolelog"
        if p.exists():
            naive = sum(1 for line in open(p, errors="ignore") if "SWBA kf=" in line)
        if c is None:
            print(f"  [P23 self-test] {tag}: 日志缺失，跳过")
            continue
        passed = (c[0] > 0) if want_applied == ">0" else (c[0] == 0)
        self_ok = self_ok and passed
        print(f"  [P23 self-test] {tag:34s} applied={c[0]:4d} (期望{want_applied}) "
              f"naive 'SWBA kf='={naive} -> {'PASS' if passed else 'FAIL'}")
    print(f"  [P23 self-test] 判据判别力 = {'OK（非恒真）' if self_ok else 'FAIL（恒真，不可用）'}")
    print()
    print(f"{'run':42s} {'applied':>8s} {'skipped':>8s} {'gate':>6s} {'gate-a-s':>9s} {'composite':>10s}")
    print("  (composite = applied>0 AND skipped>0 AND 0 <= gate-(applied+skipped) <= 1；"
          "退化 run 的等式因 0==0+0 而平凡成立，故必须叠加前两项)")
    print("  注：delta 允许 0/1 —— 首个 gate 检查可能已 armed 但窗口未就绪，"
          "既不产生执行行也不产生 skip 行（实测 21 个 run：delta 全为 0 或 1）")
    counts_ok = True
    for s in SEQS:
        for k in SEEDS:
            tag = f"r32_regate038_{s}_seed{k}"
            c = count_patterns(root, tag)
            if c is None:
                print(f"{tag:42s} {'(no log)':>8s}")
                continue
            a, sk, g = c
            delta = g - a - sk
            ok = (a > 0) and (sk > 0) and (0 <= delta <= 1)
            counts_ok = counts_ok and ok
            print(f"{tag:42s} {a:8d} {sk:8d} {g:6d} {delta:9d} "
                  f"{'OK' if ok else 'CHECK':>10s}")
    # 与 r29 同序列同 seed 比照（同阈值同门，放行率应可复现）
    print()
    print("-- 与 r29_framegate 同序列同 seed 比照（applied / skipped） --")
    for s in SEQS:
        for k in SEEDS:
            new = count_patterns(root, f"r32_regate038_{s}_seed{k}")
            old = count_patterns(root, f"r29_framegate_{s}_seed{k}")
            if new and old:
                print(f"{s:20s} s{k}  r32={new[0]:4d}/{new[1]:4d}  r29={old[0]:4d}/{old[1]:4d}")

    print()
    print("=" * 78)
    print("§4.4 判读判据（数字触发条件）")
    print("=" * 78)

    def mean_of(arm, s):
        per = table.get(arm, {}).get(s)
        return sum(x[1] for x in per) / len(per) if per else None

    def seeds_of(arm, s):
        per = table.get(arm, {}).get(s)
        return [x[1] for x in per] if per else []

    print("[pt1 0.38 甜点] 条件: mean(r32) < min(mean(0.30), mean(0.45)) 且**与两侧**逐 seed 不重叠")
    pt = "person_tracking"
    m38, m30, m45 = mean_of("gate0.38", pt), mean_of("gate0.30", pt), mean_of("gate0.45", pt)
    if None in (m38, m30, m45):
        print(f"  {pt}: 数据不全")
    else:
        s38, s30, s45 = (sorted(seeds_of(a, pt)) for a in ("gate0.38", "gate0.30", "gate0.45"))
        cond = m38 < min(m30, m45)
        ov30 = not (max(s38) < min(s30) or max(s30) < min(s38))
        ov45 = not (max(s38) < min(s45) or max(s45) < min(s38))
        floor = NOISE_FLOOR[pt]
        d30 = 100 * (m30 - m38) / m30
        d45 = 100 * (m45 - m38) / m45
        print(f"  {pt}: 0.30={m30:.4f} 0.38={m38:.4f} 0.45={m45:.4f}")
        print(f"    均值层甜点(r32 最小)={cond}")
        print(f"    与 0.30 逐seed重叠={ov30}   与 0.45 逐seed重叠={ov45}   (锁定判据要求两侧都不重叠)")
        print(f"    r32 seeds={['%.4f' % x for x in s38]}")
        print(f"    0.30 seeds={['%.4f' % x for x in s30]}")
        print(f"    0.45 seeds={['%.4f' % x for x in s45]}")
        print(f"    差距: vs 0.30 = {d30:.1f}%, vs 0.45 = {d45:.1f}%; 该序列批间噪声地板 = {floor:.1f}%")
        print(f"    => 显著性: {'两个差距都超地板' if min(d30, d45) > floor else '至少一个差距落在批间噪声内 -> 须标注'}")
        print(f"    (旧 0.38 臂 r29 = {mean_of('gate0.38_OLD', pt):.4f})")

    print()
    print("[易序列单调] 条件: crowd2/crowd3 上同时 mean(0.30) < mean(0.38) < mean(0.45)")
    print("  注: 0.30 与 0.45 两臂**同批**（r30 批, 09-14/15）→ 该步比较不受跨批噪声影响；")
    print("      0.38 列来自 R32 批（09-15）→ 含 0.38 的两步是跨批比较，须对照噪声地板。")
    for s in ("crowd2", "crowd3", "balloon"):
        m30, m38, m45 = mean_of("gate0.30", s), mean_of("gate0.38", s), mean_of("gate0.45", s)
        if None in (m30, m38, m45):
            print(f"  {s}: 数据不全")
            continue
        v30, v38, v45 = (sorted(seeds_of(a, s)) for a in ("gate0.30", "gate0.38", "gate0.45"))
        sep_all = max(v30) < min(v38) and max(v38) < min(v45)
        sep_30_45 = max(v30) < min(v45)          # 同批比较
        floor = NOISE_FLOOR[s]
        d_30_38 = 100 * (m38 - m30) / m30
        d_38_45 = 100 * (m45 - m38) / m38
        d_30_45 = 100 * (m45 - m30) / m30
        print(f"  {s}: 0.30={m30:.4f} 0.38={m38:.4f} 0.45={m45:.4f} -> 均值单调={m30 < m38 < m45}")
        print(f"      逐seed三元全分离={sep_all} | **0.30<0.45 逐seed分离(同批)={sep_30_45}** (地板 {floor:.1f}%)")
        print(f"      步长: 0.30->0.38 {d_30_38:+.1f}% (跨批), 0.38->0.45 {d_38_45:+.1f}% (跨批), "
              f"0.30->0.45 {d_30_45:+.1f}% (同批)")
        print(f"      seeds 0.30={['%.4f' % x for x in v30]} 0.38={['%.4f' % x for x in v38]} 0.45={['%.4f' % x for x in v45]}")
        print(f"      (旧 0.38={mean_of('gate0.38_OLD', s):.4f})")

    print()
    print("[定性保证] 条件: **易序列**(balloon/crowd/crowd2/crowd3) 全部 <=5cm；pt1 降幅 >=30%")
    print("  (balloon2 不在易序列硬门内 —— 其 baseline 本就 >5cm；pt 家族从未 <=5cm，是已知未达的 5cm 红线)")
    easy = ["balloon", "crowd", "crowd2", "crowd3"]
    bad = [(s, mean_of("gate0.38", s)) for s in easy
           if mean_of("gate0.38", s) is not None and mean_of("gate0.38", s) > 5.0]
    print(f"  易序列 0.38 臂值: {[(s, round(mean_of('gate0.38', s), 4)) for s in easy]}")
    print(f"  易序列 >5cm 的: {bad if bad else '无 -> PASS'}")
    for s in ("balloon2", "person_tracking", "person_tracking2"):
        print(f"  (参考, 非硬门) {s} = {mean_of('gate0.38', s):.4f}  baseline={mean_of('baseline', s):.4f}")
    b, p = mean_of("baseline", "person_tracking"), mean_of("gate0.38", "person_tracking")
    if b and p:
        print(f"  pt1: baseline={b:.4f} -> 0.38={p:.4f}  降幅={100 * (b - p) / b:.1f}%  (阈值 30%)"
              f"  {'PASS' if 100 * (b - p) / b >= 30 else 'FAIL'}")

    print()
    print("[批间噪声地板] 0.30/0.45 臂 seed2(09-15 01:08 批) vs seed0/1(09-14 批) 残差")
    for arm in ("gate0.30", "gate0.45"):
        for s in SEQS:
            per = {k: v for k, v, _ in table.get(arm, {}).get(s, [])}
            if len(per) == 3:
                base = (per[0] + per[1]) / 2
                print(f"  {arm:10s} {s:20s} seed2={per[2]:7.4f} seed01mean={base:7.4f} "
                      f"residual={100 * (per[2] - base) / base:+6.1f}%")

    print()
    print("=" * 78)
    print("§4.5 单变量：r32 vs r29 逐字段 config diff（应仅限 save_dir）")
    print("=" * 78)
    print("  由 tests/paper2_fulltable/test_fulltable_configs.py::"
          "test_r32_regate038_configs 断言（本地 pytest 7 passed + 变异测试）。")

    print()
    print("=" * 78)
    print("§七 跨裁决依赖：R31 判据参照臂即 0.38 列 —— 按新参照重算")
    print("=" * 78)
    print("  R31 预注册判据: MAIN = 自校验臂 <= 参照*1.03 (crowd2/crowd3/balloon)")
    print("                  SUB  = pt1 自校验臂 <= 参照 + 5% (即 7.83*1.05 = 8.2)")
    print("  参照 = 0.38 臂；重基线后参照应由 r29_framegate 换成 r32_regate038。")
    R31_ARMS = {"r31_selfcheck_0p5": 0.005, "r31_selfcheck_1": 0.01,
                "r31_selfcheck_2": 0.02}
    r31table = {}
    for arm in R31_ARMS:
        for s in SEQS:
            per = []
            for k in (0, 1):
                r = read_ate(root, f"{arm}_{s}_seed{k}")
                if r:
                    per.append(r[0])
            if per:
                r31table.setdefault(arm, {})[s] = sum(per) / len(per)

    def r31_verdict(arm, ref_getter, label):
        vals = r31table.get(arm, {})
        if not vals:
            print(f"    {arm} @ {label}: 数据缺失")
            return
        main_detail, main_ok = [], True
        for s in ("crowd2", "crowd3", "balloon"):
            v, ref = vals.get(s), ref_getter(s)
            if v is None or ref is None:
                main_ok = False
                continue
            good = v <= ref * 1.03
            main_ok = main_ok and good
            main_detail.append(f"{s} {v:.4f}vs{ref:.4f}{'' if good else '!'}")
        ref_pt = ref_getter("person_tracking")
        sub_v = vals.get("person_tracking")
        sub_ok = (sub_v is not None and ref_pt is not None and sub_v <= ref_pt * 1.05)
        print(f"    {arm} @ {label}: MAIN={'PASS' if main_ok else 'FAIL'} "
              f"SUB={'PASS' if sub_ok else 'FAIL'} (pt1 {sub_v:.4f} vs 阈值 {ref_pt * 1.05 if ref_pt else float('nan'):.4f})")
        print(f"        {', '.join(main_detail)}")

    print("  -- 参照 = 旧 r29_framegate（R31 当初所用，已作废） --")
    for arm in R31_ARMS:
        r31_verdict(arm, lambda s: mean_of("gate0.38_OLD", s), "ref=r29")
    print("  -- 参照 = 新 r32_regate038（重基线后应改用） --")
    for arm in R31_ARMS:
        r31_verdict(arm, lambda s: mean_of("gate0.38", s), "ref=r32")
    print("  -- MECH 门（**与参照臂无关**，直接取自 R31 自身日志，故换参照后不变） --")
    for arm, (ap, sk) in {"r31_selfcheck_0p5": (691, 385),
                          "r31_selfcheck_1": (380, 681),
                          "r31_selfcheck_2": (90, 989)}.items():
        print(f"    {arm}: applied={ap} skipped={sk} -> 两态共存 = "
              f"{'PASS' if ap > 0 and sk > 0 else 'FAIL'}（不随参照移动）")
    print("  注: R31 总判 'no arm passes all three gates' 由三档 SUB 全 FAIL 支撑，")
    print("      换参照后 SUB 全 FAIL 不变 ⇒ 总判不变。2% 臂 MAIN 由 PASS 翻 FAIL，")
    print("      但 verdict_r31.md §四.5 已自述该臂 crowd2 两 seed 极差 0.941cm > ±3% 带 0.081cm，")
    print("      属噪声级判定 ⇒ **不构成'结论被加强'**（勿用该翻转做正面论据）。")

    print()
    print("OVERALL: counts_ok =", counts_ok, "| done rc0 =",
          f"{len(rc0)}/{len(expected)}", "| batch_all_done =", complete)


if __name__ == "__main__":
    main()
