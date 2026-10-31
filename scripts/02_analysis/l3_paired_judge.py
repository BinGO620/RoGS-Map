#!/usr/bin/env python3
"""l3_paired_judge.py — L3 正式批判据机（**程序化，禁手抄**）。

判据权威（**不得在本文件中重新定义**）
--------------------------------------
* 形状 = `results/lifecycle_paper2/evidence/prereg_L3.md` §5
* 帧集/仪器/来源列 = `results/lifecycle_paper2/evidence/prereg_L3_amendment_1_frameset.md` §4–§6

主判据（逐序列，3-seed 配对）
    Δᵢ = exitᵢ − offᵢ                      （主读数 = 离线 freshvac；负 = 残影更小）
    PASS ⟺ (≥2/3 同号，且为负) ∧ |mean(Δ)| > 门槛
    门槛 = max(1.19cm, 该序列 off 臂 3 seed 的组内 sd)
批级：≥6/9 序列 PASS 且无序列越约束门 ⇒ 机制按"限定域"成立
约束门（逐序列）：ATE Δ ≤ +0.5cm 且 ≤ +5%；static PSNR Δ ≥ −0.25dB
描述性分层（**不覆盖主判据**）：Tier1 = |mean(Δ)|/门槛 > 2；Tier2 = 1–2；Tier3 = 其余

数据来源列绑定（见修正案 §6.0）
    freshvac / ghost_excess / static_psnr ← render_metrics.json
    ATE                                  ← tables/tracking_raw.csv:ate_rmse_cm

用法
----
    python scripts/02_analysis/l3_paired_judge.py                 # 判 L3 批（缺数据则报缺）
    python scripts/02_analysis/l3_paired_judge.py --selftest      # 用 C 步 crowd2 数据自测解析逻辑
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2", "mvnobox", "mvnobox2"]
SEEDS = [0, 1, 2]
FILL_SEQS = ["mvnobox", "balloon2"]

THRESHOLD_FLOOR_CM = 1.19      # 预注册固定项（prereg_L3 §5.1）
ATE_GATE_ABS_CM = 0.5          # 约束门：绝对
ATE_GATE_REL = 0.05            # 约束门：相对
PSNR_GATE_DB = -0.25           # 约束门：static PSNR
TIER1_MULT, TIER2_MULT = 2.0, 1.0


# ────────────────────────────── 读数 ──────────────────────────────
def load_ate(root: str, tag: str):
    """ATE（全帧口径）← tables/tracking_raw.csv:ate_rmse_cm"""
    p = os.path.join(root, tag, "tables", "tracking_raw.csv")
    if not os.path.isfile(p):
        return None
    with open(p, newline="") as f:
        rows = list(csv.DictReader(f))
    vals = [float(r["ate_rmse_cm"]) for r in rows
            if r.get("ate_rmse_cm") not in (None, "", "nan")]
    return vals[-1] if vals else None


def load_render(root: str, tag: str, render_tpl: str):
    """freshvac 主读数等 ← render_metrics.json（离线密帧仪器产物）"""
    d = os.path.join(root, render_tpl.format(tag=tag))
    p = os.path.join(d, "render_metrics.json")
    if not os.path.isfile(p):
        return None
    m = json.load(open(p))
    return {
        "freshvac": m.get("mean_freshvac_ghost_excess_depth_l1_cm"),
        "ghost_excess": m.get("mean_ghost_excess_depth_l1_cm"),
        "static_psnr": m.get("mean_static_psnr"),
        "n_frames": m.get("n_frames"),
        "skipped": m.get("frames_render_skipped"),
        "dir": d,
    }


def tag_of(seq: str, arm: str, seed: int) -> str:
    return f"L3_{seq}_{arm}_s{seed}"


# ────────────────────────────── 判据 ──────────────────────────────
def judge_sequence(off: list, ex: list) -> dict:
    """off/ex = 每 seed 的主读数（None 表示缺）。返回该序列判定。"""
    ds = [(e - o) for o, e in zip(off, ex) if o is not None and e is not None]
    n_ok = len(ds)
    if n_ok < 3:
        return {"n_pairs": n_ok, "judgeable": False, "reason": f"配对不足（{n_ok}/3）"}
    n_neg = sum(1 for d in ds if d < 0)
    mean_d = statistics.mean(ds)
    off_ok = [o for o in off if o is not None]
    sd = statistics.stdev(off_ok) if len(off_ok) >= 2 else 0.0
    thr = max(THRESHOLD_FLOOR_CM, sd)
    # 方向为负是**判据的一部分**，不只是期望：prereg_L3 §5「≥2/3 同号（预期为负）」。
    # 若只要求"同号"而不要求"为负"，则"机制让残影一致性地更差"也会被判 PASS。
    # （该缺陷由本文件的负对照自测捕获；预注册澄清已登记于修正案 §5。）
    mean_neg = mean_d < 0
    sign_ok = (n_neg >= 2) and mean_neg
    mag_ok = abs(mean_d) > thr
    ratio = abs(mean_d) / thr if thr > 0 else float("inf")
    tier = 1 if ratio > TIER1_MULT else (2 if ratio >= TIER2_MULT else 3)
    return {
        "n_pairs": n_ok, "judgeable": True, "deltas": ds, "n_neg": n_neg,
        "mean_delta": mean_d, "off_sd": sd, "threshold": thr,
        "sign_ok": sign_ok, "mag_ok": mag_ok, "PASS": bool(sign_ok and mag_ok),
        "ratio": ratio, "tier": tier,
    }


def gate_ate(off: list, ex: list) -> dict:
    pairs = [(o, e) for o, e in zip(off, ex) if o is not None and e is not None]
    if not pairs:
        return {"ok": None, "reason": "无 ATE 读数"}
    d = statistics.mean(e - o for o, e in pairs)
    base = statistics.mean(o for o, _ in pairs)
    rel = (d / base) if base else float("nan")
    ok = (d <= ATE_GATE_ABS_CM) and (rel <= ATE_GATE_REL)
    return {"ok": ok, "delta_cm": d, "rel": rel}


def gate_psnr(off: list, ex: list) -> dict:
    """static PSNR 约束门。

    ⚠ 2026-09-21：本函数曾被**误传入 freshvac 列表**，导致 PSNR 列与 freshvac 列数字完全相同
    （判据机首轮输出即暴露：两列逐行相等）。加量纲护栏后，此类"喂错指标"会直接报错而非静默出错。
    """
    pairs = [(o, e) for o, e in zip(off, ex) if o is not None and e is not None]
    if not pairs:
        return {"ok": None, "reason": "无 static PSNR 读数"}
    base = statistics.mean(o for o, _ in pairs)
    if not (8.0 <= base <= 60.0):
        raise AssertionError(
            f"static PSNR 基值 {base:.3f} dB 不在合理区间 [8,60] —— "
            f"大概率是把 freshvac/ghost_excess 之类的**其他指标**传进了 PSNR 门（本函数只接受 dB 量纲）")
    d = statistics.mean(e - o for o, e in pairs)
    return {"ok": d >= PSNR_GATE_DB, "delta_db": d}


# ────────────────────────────── L3 批 ──────────────────────────────
def run_batch(root: str, render_tpl: str) -> int:
    print(f"# L3 判据机输出（root={root}）\n")
    print(f"render_tpl = {render_tpl}\n")

    per_seq, integrity = {}, []
    for seq in SEQS:
        off_r, ex_r, off_a, ex_a, off_p, ex_p = [], [], [], [], [], []
        for s in SEEDS:
            ro = load_render(root, tag_of(seq, "off", s), render_tpl)
            re_ = load_render(root, tag_of(seq, "exit", s), render_tpl)
            off_r.append(ro["freshvac"] if ro else None)
            ex_r.append(re_["freshvac"] if re_ else None)
            off_p.append(ro["static_psnr"] if ro else None)   # ← 约束门用的是 static PSNR，不是 freshvac
            ex_p.append(re_["static_psnr"] if re_ else None)
            off_a.append(load_ate(root, tag_of(seq, "off", s)))
            ex_a.append(load_ate(root, tag_of(seq, "exit", s)))
            for nm, r, t in (("off", ro, tag_of(seq, "off", s)),
                             ("exit", re_, tag_of(seq, "exit", s))):
                if r is None:
                    integrity.append(f"MISSING render {t}")
                elif r["n_frames"] != 17:
                    integrity.append(f"n_frames={r['n_frames']} != 17 : {t}")
        per_seq[seq] = {"off_r": off_r, "exit_r": ex_r, "off_a": off_a, "exit_a": ex_a,
                        "off_p": off_p, "exit_p": ex_p}

    # 逐序列
    print("## 1. 逐序列（主判据：freshvac，3-seed 配对）\n")
    print("| 序列 | off (3 seed) | exit (3 seed) | Δᵢ | mean Δ | 同号 | off sd | 门槛 | PASS | Tier |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    n_pass = 0
    for seq in SEQS:
        v = per_seq[seq]
        j = judge_sequence(v["off_r"], v["exit_r"])
        if not j["judgeable"]:
            print(f"| {seq} | — | — | — | — | — | — | — | **不可判**({j['reason']}) | — |")
            continue
        if j["PASS"]:
            n_pass += 1
        offs = " / ".join("—" if x is None else f"{x:.3f}" for x in v["off_r"])
        exs = " / ".join("—" if x is None else f"{x:.3f}" for x in v["exit_r"])
        ds = " / ".join(f"{d:+.3f}" for d in j["deltas"])
        print(f"| {seq} | {offs} | {exs} | {ds} | **{j['mean_delta']:+.3f}** | "
              f"{j['n_neg']}/{j['n_pairs']} 负 | {j['off_sd']:.3f} | {j['threshold']:.3f} | "
              f"{'✅' if j['PASS'] else '❌'} | {j['tier']} |")

    # 批级
    print(f"\n## 2. 批级判定\n")
    print(f"**PASS 序列数 = {n_pass}/9**（预注册门：≥6/9）")

    print("\n## 3. 约束门（逐序列）\n")
    print("| 序列 | ATE Δ (cm) | ATE 相对 | ATE 门 | static PSNR Δ (dB) | PSNR 门 |")
    print("|---|---|---|---|---|---|")
    gate_viol = []
    for seq in SEQS:
        v = per_seq[seq]
        ga = gate_ate(v["off_a"], v["exit_a"])
        gp = gate_psnr(v["off_p"], v["exit_p"])
        da = "—" if ga.get("delta_cm") is None else f"{ga['delta_cm']:+.3f}"
        rel = "—" if ga.get("rel") is None or ga["rel"] != ga["rel"] else f"{ga['rel'] * 100:+.2f}%"
        dp = "—" if gp.get("delta_db") is None else f"{gp['delta_db']:+.3f}"
        m_a = "—" if ga["ok"] is None else ("✅" if ga["ok"] else "❌越门")
        m_p = "—" if gp["ok"] is None else ("✅" if gp["ok"] else "❌越门")
        if ga["ok"] is False or gp["ok"] is False:
            gate_viol.append(seq)
        print(f"| {seq} | {da} | {rel} | {m_a} | {dp} | {m_p} |")
    print(f"\n越门序列：{gate_viol if gate_viol else '无'}")

    # Tier 分布
    print("\n## 4. Tier 分层（**描述性；不覆盖主判据**）\n")
    tiers = {1: [], 2: [], 3: []}
    for seq in SEQS:
        v = per_seq[seq]
        j = judge_sequence(v["off_r"], v["exit_r"])
        if j["judgeable"]:
            tiers[j["tier"]].append(f"{seq}({j['ratio']:.2f}×)")
    for t in (1, 2, 3):
        print(f"- Tier {t}: {', '.join(tiers[t]) if tiers[t] else '（无）'}")

    # 数据完整性
    print("\n## 5. 数据完整性\n")
    if integrity:
        for x in integrity[:40]:
            print(f"- {x}")
        if len(integrity) > 40:
            print(f"- ...共 {len(integrity)} 条")
    else:
        print("- 全部渲染 n_frames=17、无缺失")

    # fill 臂（并陈，不作主判据）
    print("\n## 6. fill 定向臂（并陈；**不作主判据**）\n")
    for seq in FILL_SEQS:
        fs, base = [], []
        for s in SEEDS:
            rf = load_render(root, tag_of(seq, "exit_fill", s), render_tpl)
            fs.append(rf["freshvac"] if rf else None)
            base.append(per_seq[seq]["exit_r"][s])
        pairs = [(b, f) for b, f in zip(base, fs) if b is not None and f is not None]
        if pairs:
            d = statistics.mean(f - b for b, f in pairs)
            print(f"- {seq}: mean(exit_fill − exit) = {d:+.3f}cm （n={len(pairs)}）")
        else:
            print(f"- {seq}: 无读数")

    return 0


# ────────────────────────────── 自测 ──────────────────────────────
def selftest(root: str) -> int:
    """用 **C 步 crowd2** 数据自测解析逻辑（唯一带锁定仪器产物的既有数据）。

    为何不用 L1：L1 的离线读数是 interval-60 / 6 帧 / 仅 ghost_excess 的**旧仪器**产物，
    结构上不含 freshvac 键（见修正案 §2）⇒ 与 L3 判据机不兼容。
    """
    print("# 自测：C 步 crowd2（预期 mean Δ = −3.738cm，3/3 负）\n")
    off_tags = ["crowd2_off", "crowd2_off_rep", "crowd2_off_r2"]
    ex_tags = ["crowd2_exit", "crowd2_exit_r2", "crowd2_exit_r3"]
    ok = True

    off_r, ex_r = [], []
    for t in off_tags + ex_tags:
        r = load_render(root, t, "render_cj_{tag}_dense")
        if r is None:
            print(f"FAIL 缺渲染 {t}"); ok = False; continue
        if r["n_frames"] != 17:
            print(f"FAIL {t} n_frames={r['n_frames']} != 17"); ok = False
        if r["freshvac"] is None:
            print(f"FAIL {t} 无 freshvac 键"); ok = False
        (off_r if t in off_tags else ex_r).append(r["freshvac"])

    if len(off_r) == 3 and len(ex_r) == 3:
        j = judge_sequence(off_r, ex_r)
        print(f"逐序列判定: mean Δ={j['mean_delta']:+.3f}  同号={j['n_neg']}/3 负  "
              f"门槛={j['threshold']:.3f}  PASS={j['PASS']}  Tier={j['tier']}")
        if abs(j["mean_delta"] - (-3.738)) > 0.01:
            print(f"FAIL mean Δ 与 C 步裁决不符（期望 −3.738，得 {j['mean_delta']:.3f}）"); ok = False
        if j["n_neg"] != 3:
            print("FAIL 同号数应为 3/3 负"); ok = False
        if not j["PASS"]:
            print("FAIL 该序列应 PASS（C 步已验证可判且为负）"); ok = False
    else:
        print("FAIL 配对不足"); ok = False

    # 负对照：把两臂对调（Δ 符号反转 ⇒ 机制"更差"）应导致不 PASS。
    # 注意用**对调**而非"取负 exit"：Δ = exit − off 中 off 是大项，
    # 取负 exit 只会得到更负的 Δ，检验不到方向分支。
    if len(off_r) == 3 and len(ex_r) == 3:
        jf = judge_sequence(ex_r, off_r)
        if jf["PASS"]:
            print(f"FAIL 负对照：对调两臂后仍 PASS（mean Δ={jf['mean_delta']:+.3f}）⇒ 判据无方向判别力")
            ok = False
        else:
            print(f"负对照: 对调两臂后 PASS=False ✓（mean Δ={jf['mean_delta']:+.3f}，方向分支有效）")

    print("\n自测" + ("通过 ✓" if ok else "**未通过**"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(REPO, "results/lifecycle_paper2"))
    ap.add_argument("--render-tpl", default="render_{tag}_dense")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest(args.root)
    return run_batch(args.root, args.render_tpl)


if __name__ == "__main__":
    sys.exit(main())
