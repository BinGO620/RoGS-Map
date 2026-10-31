#!/usr/bin/env python3
"""analyze_r34.py — R34 拉通批同批复核的确定性分析器。

判据定义见 results/paper2_rollout/evidence/prereg_r34.md（K1–K7）。
本脚本**只读** run 目录与 consolelog，确定性输出（无随机、无时间依赖），
供 verdict 落盘前复核。

用法：
  python3 scripts/02_analysis/analyze_r34.py [--root results/paper2_rollout]

输出（stdout，人类可读）：
  §A 执行与完整性（K1 / K1-b / K1-c）
  §B 生效验证（K3，按臂实例化 + 整行形状 + 正控 + delta 上界）
  §C 回环自证（§2.1：gate 臂逐 run 的 med/max，去折行）
  §D 主表（K2：col 8 逐 seed）+ K5 复现性 + K6 不变量
  §E K5 归因（rb → sw → gate 三步）

计数模式（两道已知 rich Console 坑，见 prereg K3）：
  - skip 行须用 \\s+ 而非字面双空格（rich 插入额外空格）
  - 禁用 [rel-gate skip] 字面量（该标记被 rich 吞掉）
"""
import argparse
import csv
import glob
import os
import re
import sys

SEQS = ["f1_room", "f1_desk2", "f3_st_rpy", "f3_office",
        "moving_obstructing_box", "f3_wk_rpy"]
ARMS = ["rb", "sw", "gate"]

# 冻结参照（prereg §一 / §1.2；col 8 全精度，来源 run_id 见括号）
FROZEN = {
    "f1_room":                (8.2384, 18.1034, 1315),
    "f1_desk2":               (7.1966, 3.5267, 643),
    "f3_st_rpy":              (2.6851, 5.8459, 823),
    "f3_office":              (1.6438, 3.6579, 2588),
    "moving_obstructing_box": (18.7758, 20.7368, 592),
    "f3_wk_rpy":              (4.2924, 5.8689, 913),
}

# K5 tolerance source: PRIOR (other-batch) observations of the all-off condition.
# MUST be prior data, not this batch (using the new batch = circular, any batch
# passes itself).
#
# 2026-09-18 补全（远程审计发现 x_rows_seeds12 批次 30 个先验 run 从未拉回本地）：
#   + rollbase seed1/seed2 (col8, 复算核对 3/3 精确一致)：
#     f1_room 6.4318/4.7338 | f3_st_rpy 2.7578/4.5114 |
#     mob 37.5449/20.9375 | f3_wk_rpy 4.4823/4.2109
#   + diag_f1r_b s0/s1 (f1_room, SWBA-off/LC-on; LC 在该序列零修正、行为等价)：
#     7.0213/9.3311 (col8; 9.14 是 col14 防混引)
# legacy 子集读数（首轮=仅本地可见先验）已在 verdict 草稿 §三 留痕；
# 完整先验读为准：4/6->3/6 EXCEEDS，mob 1.0->18.77 改判 PASS。
PRIOR_ALL_OFF = {
    "f1_room": [8.2384, 6.4318, 4.7338, 7.0213, 9.3311],
    "f1_desk2": [7.1966],
    "f3_st_rpy": [2.6851, 2.7578, 4.5114],
    "f3_office": [1.6438],
    "moving_obstructing_box": [18.7758, 37.5449, 20.9375],
    "f3_wk_rpy": [4.2924, 4.4823, 4.2109],
}

# ---------------------------------------------------------------- log patterns
# anchored to whole line shape (NOTES: 禁裸模式 SWBA kf=)
RE_GATE = re.compile(r"^MonoGS: SWBA gate kf=\d+: static_conf=[\d.]+ \(max [\d.]+\)", re.M)
RE_EXEC = re.compile(r"^MonoGS: SWBA kf=\d+: \d+ edges free=", re.M)
RE_SKIP = re.compile(r"^MonoGS: SWBA kf=\d+:\s+static_conf=[\d.]+ > [\d.]+", re.M)
RE_ANY_SWBA = re.compile(r"^MonoGS: SWBA", re.M)
RE_LOOP = re.compile(r"^MonoGS: LoopClosure", re.M)
RE_DONE = re.compile(r"^MonoGS: Done", re.M)
# loop summary needs wrap-rejoin; the file wraps long lines without prefix.
# NOTE: rich wraps mid-token too (e.g. "seed_0/2026-0" | "9-09-..."), so the
# rejoined text must be built with NO separator and the patterns must tolerate
# either zero or one space where the break occurred.
# Third form (实测 R34 f3_wk_rpy s0): break exactly BETWEEN "corrections" and
# "|dt|" with zero retained space -> joined as "corrections|dt|". Hence \s*.
RE_LOOP_SUM = re.compile(r"corrections\s*\|dt\|\s*med ([\d.]+)cm\s*max ([\d.]+)cm\s*applied to (\d+) KFs")
RE_LOOP_SKIP = re.compile(r"LoopClosure: \d+ candidates, 0 verified, skip")
RE_RUNDIR = re.compile(r"seed_\d+/(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})")


def read_log(path):
    """Rejoin rich Console hard-wrapping.

    Joins with NO separator: rich breaks both at spaces (where the space is
    retained before the newline) and mid-token (where any inserted separator
    would corrupt the token). Patterns therefore use \\s* at break points.
    """
    with open(path, errors="replace") as fh:
        return fh.read().replace("\n", "")


def tally(path):
    """Whole-line-shape counts + wrap-joined loop counters."""
    with open(path, errors="replace") as fh:
        raw = fh.read()
    flat = read_log(path)
    loop_ms = RE_LOOP_SUM.findall(flat)
    return {
        "gate": len(RE_GATE.findall(raw)),
        "exec": len(RE_EXEC.findall(raw)),
        "skip": len(RE_SKIP.findall(raw)),
        "any_swba": len(RE_ANY_SWBA.findall(raw)),
        "loop": len(RE_LOOP.findall(raw)),
        "done": len(RE_DONE.findall(raw)),
        "loop_sum": loop_ms[-1] if loop_ms else None,
        "loop_skip": bool(RE_LOOP_SKIP.search(flat)),
        "rundirs": sorted(set(RE_RUNDIR.findall(flat))),
    }


def track(path):
    """col 8 (ate_rmse_cm) + run_id for the final OK row."""
    with open(path) as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("status") == "OK"]
    if not rows:
        return None
    r = rows[-1]
    return {"col8": float(r["ate_rmse_cm"]),
            "col14": float(r["keyframe_ate_rmse_cm"]),
            "run_id": r.get("run_id", "")}


def run_dir(root, arm, seq, seed):
    return os.path.join(root, f"r34_{arm}_{seq}_seed{seed}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="results/paper2_rollout")
    args = ap.parse_args()
    root = args.root

    k1_fail, k3_fail = [], []
    table = {}

    print("=" * 78)
    print("§A 执行与完整性（K1 / K1-b / K1-c）")
    print("=" * 78)
    print(f"{'run':<32}{'rc':>6}{'Done':>6}{'log_rundir==track':>20}")
    for arm in ARMS:
        for seq in SEQS:
            for seed in (0, 1, 2):
                tag = f"r34_{arm}_{seq}_seed{seed}"
                d = run_dir(root, arm, seq, seed)
                log = os.path.join(root, tag + ".consolelog")
                trk = os.path.join(d, "tables", "tracking_raw.csv")
                if not os.path.exists(log) or not os.path.exists(trk):
                    print(f"{tag:<32}{'—':>6}{'—':>6}{'(missing)':>20}")
                    k1_fail.append((tag, "missing log or tracking_raw"))
                    continue
                t = tally(log)
                tk = track(trk)
                own = (tk["run_id"] in t["rundirs"]) if t["rundirs"] else None
                flag = ""
                if t["done"] != 1:
                    flag = "  <-- K1-b FAIL (consolelog incomplete)"
                    k1_fail.append((tag, f"Done={t['done']}"))
                elif own is False:
                    flag = "  <-- K1-c FAIL (log/tracking not same run)"
                    k1_fail.append((tag, "consolelog/tracking mismatch"))
                print(f"{tag:<32}{'ok':>6}{t['done']:>6}{str(own):>20}{flag}")
                table[(arm, seq, seed)] = (t, tk)

    print()
    print("=" * 78)
    print("§B 生效验证（K3；按臂实例化 + 整行形状 + 正控）")
    print("=" * 78)
    print(f"{'run':<32}{'exec':>6}{'skip':>6}{'gate':>6}{'delta':>7}{'anySWBA':>9}{'loop':>6}  verdict")
    deltas = []
    for arm in ARMS:
        for seq in SEQS:
            for seed in (0, 1, 2):
                key = (arm, seq, seed)
                if key not in table:
                    continue
                t, _ = table[key]
                a, b, c = t["exec"], t["skip"], t["gate"]
                delta = c - a - b
                if arm == "rb":
                    ok = (a == 0 and t["any_swba"] == 0 and t["loop"] == 0)
                    why = "正控(SWBA 子系统零输出)" if ok else f"rb 非零: exec={a} any={t['any_swba']} loop={t['loop']}"
                elif arm == "sw":
                    ok = (a > 0 and t["loop"] == 0)
                    why = "(a)>0 且无回环" if ok else f"(a)={a} loop={t['loop']}"
                else:
                    ok = (a > 0 and b > 0 and c >= a + b)
                    why = "(a)>0,(b)>0,(c)>=(a)+(b)" if ok else f"a={a} b={b} c={c}"
                    deltas.append(delta)
                if not ok:
                    k3_fail.append((f"r34_{arm}_{seq}_seed{seed}", why))
                print(f"r34_{arm}_{seq}_seed{seed:<18}{a:>6}{b:>6}{c:>6}{delta:>7}{t['any_swba']:>9}{t['loop']:>6}  {'OK' if ok else 'FAIL'} {why if not ok else ''}")
    if deltas:
        print(f"\ndelta=(c)-(a)-(b) 上界实测: min {min(deltas)} max {max(deltas)}"
              f"  （prereg: 预期 0–5，>5 须归因；判据为 (c)>=(a)+(b) 无上界）")

    print()
    print("=" * 78)
    print("§C 回环自证（§2.1；gate 臂逐 run，去折行）")
    print("=" * 78)
    for seq in SEQS:
        for seed in (0, 1, 2):
            key = ("gate", seq, seed)
            if key not in table:
                continue
            t, _ = table[key]
            if t["loop_sum"]:
                med, mx, nkf = t["loop_sum"]
                flag = ""
                if float(mx) > 0:
                    flag = "  <-- NONZERO: 触发 §2.1 补 final 臂"
            else:
                flag = "  (no correction line: %s)" % ("0 verified skip" if t["loop_skip"] else "无行")
                med = mx = nkf = "-"
            print(f"r34_gate_{seq}_seed{seed:<14} med={med} max={mx} KFs={nkf}{flag}")

    print()
    print("=" * 78)
    print("§D 主表（K2：col 8 全帧，3-seed）+ K5 复现性 + K6 不变量")
    print("=" * 78)
    print(f"{'seq':<24}{'rb':>9}{'sw':>9}{'gate':>9}{'| rb vs frozen':>16}{'tol':>7}  K5")
    k5_res = {}
    for seq in SEQS:
        row = {}
        for arm in ARMS:
            vals = [table[(arm, seq, s)][1]["col8"] for s in (0, 1, 2)
                    if (arm, seq, s) in table]
            row[arm] = sum(vals) / len(vals) if vals else float("nan")
        frz_rb, frz_gate, _n = FROZEN[seq]
        d_rb = row["rb"] - frz_rb
        # K5 tolerance = max(1.0cm, PRIOR-OBSERVATION seed spread) per prereg K5.
        # MUST use the prior observations, NOT this batch's own spread: using the
        # new batch would be circular (any batch would pass itself).
        prior = PRIOR_ALL_OFF.get(seq, [frz_rb])
        spread = (max(prior) - min(prior)) if len(prior) > 1 else None
        tol = max(1.0, spread) if spread is not None else 1.0
        k5 = "PASS" if abs(d_rb) <= tol else "EXCEEDS -> K5 归因触发器"
        tol_s = f"{tol:.2f}" if spread is not None else "1.00*"
        k5_res[seq] = (abs(d_rb) <= tol)
        print(f"{seq:<24}{row['rb']:>9.3f}{row['sw']:>9.3f}{row['gate']:>9.3f}{d_rb:>+16.3f}{tol_s:>7}  {k5}")
    print("  (* = 该序列无先验多抽样，退化为 1.0cm 地板)")

    print()
    print(f"{'seq':<24}{'Δ(rb→sw)':>11}{'Δ(rb→gate)':>12}{'归因':>22}")
    for seq in SEQS:
        vals = {}
        for arm in ARMS:
            v = [table[(arm, seq, s)][1]["col8"] for s in (0, 1, 2)
                 if (arm, seq, s) in table]
            vals[arm] = sum(v) / len(v) if v else float("nan")
        dsw = vals["sw"] - vals["rb"]
        dga = vals["gate"] - vals["rb"]
        if abs(dga) < 0.5:
            att = "无效应"
        elif abs(dsw) >= 0.5 * abs(dga):
            att = "SWBA 主导"
        else:
            att = "门控/回环贡献为主"
        print(f"{seq:<24}{dsw:>+11.3f}{dga:>+12.3f}{att:>22}")

    print()
    print("=" * 78)
    print("§E K6 不变量（方向与幅度；含 K5 剔除语义）")
    print("=" * 78)
    harm = ["f1_room", "f3_st_rpy", "f3_office", "moving_obstructing_box", "f3_wk_rpy"]
    harm_kept = [s for s in harm if k5_res.get(s, True)]
    harm_dropped = [s for s in harm if not k5_res.get(s, True)]
    print(f"  K5 剔除后保留的有害序列: {harm_kept}")
    print(f"  K5 剔除的序列（不计入分子/分母）: {harm_dropped}")
    n_harm_ok = 0
    for seq in harm_kept:
        v = {}
        for arm in ARMS:
            x = [table[(arm, seq, s)][1]["col8"] for s in (0, 1, 2)
                 if (arm, seq, s) in table]
            v[arm] = sum(x) / len(x) if x else float("nan")
        d = v["gate"] - v["rb"]
        ok = (d > 0 and abs(d) > 1.0)
        n_harm_ok += 1 if ok else 0
        print(f"  {seq:<26} Δ(rb→gate)={d:>+7.3f}  {'PASS' if ok else 'FAIL'} (需为正且 >1.0cm)")
    n_kept = len(harm_kept)
    v = {}
    for arm in ("rb", "gate"):
        x = [table[(arm, "f1_desk2", s)][1]["col8"] for s in (0, 1, 2)
             if (arm, "f1_desk2", s) in table]
        v[arm] = sum(x) / len(x) if x else float("nan")
    d_ctl = v["gate"] - v["rb"]
    print(f"  {'f1_desk2 (方向对照)':<26} Δ(rb→gate)={d_ctl:>+7.3f}  "
          f"{'PASS' if d_ctl < 0 else 'FAIL'} (需为负)")
    print(f"\n  K6 有害序列达标: {n_harm_ok}/{n_kept} （阈值 ≥3 **且** 分母=未被K5剔除者）")
    if n_kept < 3:
        print(f"  ** K5 剔除 ≥3 条 => 按预注册 K6 该主张自动降级为「不可复现」**")
    elif n_harm_ok >= 3:
        print(f"  判定: 主张维持（方向与幅度复现）")
    else:
        print(f"  ** K6 未达标 => 结论行改「部分不成立」+ 止损项（预注册 K6）**")

    print()
    print("=" * 78)
    print("汇总")
    print("=" * 78)
    print(f"K1/K1-b/K1-c 失败: {len(k1_fail)}")
    for tag, why in k1_fail:
        print(f"    {tag}: {why}")
    print(f"K3 失败: {len(k3_fail)}")
    for tag, why in k3_fail:
        print(f"    {tag}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
