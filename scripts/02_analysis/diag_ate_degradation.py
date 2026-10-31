#!/usr/bin/env python3
"""diag_ate_degradation.py — R33 批 ATE 劣化的归因诊断（纯重分析，零 GPU，只读）。

预注册：results/paper2_fulltable/evidence/diag_ate_degradation_prereg.md（H1–H4 + 判定规则跑前锁定）。

输入（全部只读）：
  results/paper2_fulltable/r33_rebase_{arm}_{seq}_seed{k}.consolelog   （84 个）
  results/paper2_fulltable/evidence/tables_paper2_preview.json         （ATE，不重算）

提取（按已核实的行格式；注意 `|dt|` 行在 "max" 处被日志截断，只有 med 可用）：
  SWBA gate kf=N: static_conf=X (max Y)          → R26 门的信号轨迹（KF, conf）
  SWBA kf=N: [rel-gate skip] ...                 → 门关（SWBA 被拒）计数
  SWBA kf=N: N edges free=[a,b] anchors=M |dc| X% |dt| med Ycm → 边/修正量统计
  SWBA kf=N: [gate-skip] rel_improve=...%        → SWBA 内层门
  Semantic insertion gate frame N: X person px zeroed → 动态掩码像素轨迹
  LoopClosure verify(plain|icp) a->b: VERDICT    → LC 验证计数

分析：
  H1  masked-mean 代理（conf/(1−dyn_frac)，动态像素 reliability≈0 的下界修正）
      vs 现行全帧均值信号：哪个与“SWBA 实际效益方向”的序列级一致率更高。
  H2  |dt| med 修正量在有害/有益序列上的分布。
  H3  KF 数与效益方向的相关。
  H4  pt2 的通道构成（SWBA/LC/门的 skip 比例）。

输出：results/paper2_fulltable/evidence/diag_ate_degradation.json（+stdout 摘要表）。
用法：/data/conda_envs/monogs-ours/bin/python scripts/02_analysis/diag_ate_degradation.py
"""
from __future__ import annotations

import json
import re
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "results/paper2_fulltable"
PREVIEW = R / "evidence/tables_paper2_preview.json"
OUT = R / "evidence/diag_ate_degradation.json"

ARMS = ("baseline", "swbaonly", "final", "gate")
SEQS = ("balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2")
SEEDS = (0, 1, 2)
IMG_PX = 640 * 480          # Bonn；仅作 dyn_frac 分母，带越界保护
TH = 0.38                   # SWBA.swba_max_static_conf（gate 臂实测）

RE_GATE = re.compile(r"SWBA gate kf=(\d+): static_conf=([\d.]+) \(max ([\d.]+)\)")
# R33 批的 skip 行是 "SWBA kf=N:  static_conf=X > Y"（两个空格、无标签）；
# 当前代码已改为 "[rel-gate skip]"——两种都认
RE_SKIP = re.compile(r"SWBA kf=(\d+): (?:\[rel-gate skip\]| static_conf=[\d.]+ >)")
# consolelog 有行宽截断：长行会在 "|dt| med " 处被砍（balloon 的早期短行才完整）。
# 尾部字段全部设为可选；n_swba_ran 按 "edges free" 计数；dt/dc 统计只来自幸存行（有早 KF 偏置，已披露）
RE_EDGES = re.compile(r"SWBA kf=(\d+): (\d+) edges free=\[(\d+), (\d+)\]"
                      r"(?: anchors=(\d+))?(?: \|dc\| ([\d.]+)%?)?"
                      r"(?: \|dt\| med ([\d.]+)cm)?")
RE_INNER = re.compile(r"SWBA kf=(\d+): \[gate-skip\] rel_improve=([\d.]+)%")
RE_MASK = re.compile(r"Semantic insertion gate frame (\d+): (\d+) person px zeroed")
RE_LC = re.compile(r"LoopClosure verify\((plain|icp)\) \d+->\d+: (\w+)")


def parse_log(p: Path) -> dict:
    d = {"gate": [], "skip_kf": [], "edges": [], "inner_skip": [],
         "mask": [], "lc": {"plain": {"ACCEPT": 0, "REJECT": 0},
                            "icp": {"ACCEPT": 0, "REJECT": 0}},
         "swba_failed": 0}
    for line in p.read_text(errors="replace").splitlines():
        if m := RE_GATE.search(line):
            d["gate"].append((int(m.group(1)), float(m.group(2)), float(m.group(3))))
        elif m := RE_SKIP.search(line):
            d["skip_kf"].append(int(m.group(1)))
        elif m := RE_EDGES.search(line):
            d["edges"].append({
                "kf": int(m.group(1)), "n_edges": int(m.group(2)),
                "free": [int(m.group(3)), int(m.group(4))],
                "anchors": int(m.group(5)) if m.group(5) else None,
                "dc_pct": float(m.group(6)) if m.group(6) else None,
                "dt_med_cm": float(m.group(7)) if m.group(7) else None})
        elif m := RE_INNER.search(line):
            d["inner_skip"].append((int(m.group(1)), float(m.group(2))))
        elif m := RE_MASK.search(line):
            px = int(m.group(2))
            if px >= IMG_PX:            # 越界保护：分母不对时丢弃该帧
                continue
            d["mask"].append((int(m.group(1)), px))
        elif m := RE_LC.search(line):
            v = m.group(2)
            if v in d["lc"][m.group(1)]:
                d["lc"][m.group(1)][v] += 1
        elif "SWBA kf=" in line and "failed" in line:
            d["swba_failed"] += 1
    return d


def masked_proxy(gate: list, mask: list) -> list:
    """conf/(1−dyn_frac)：动态像素 reliability≈0 的下界修正（预注册 H1）。

    门行与掩码行都在 5 的倍数帧上；按帧精确匹配，缺失时取最近的前一条。
    """
    mi = {f: px for f, px in mask}
    sorted_f = sorted(mi)
    out = []
    for kf, conf, _mx in gate:
        if kf in mi:
            px = mi[kf]
        else:
            prev = [f for f in sorted_f if f <= kf]
            if not prev:
                continue
            px = mi[prev[-1]]
        dyn = px / IMG_PX
        if dyn >= 0.95:                # 掩码几乎全图 ⇒ 代理无意义
            continue
        out.append((kf, conf, conf / (1.0 - dyn), dyn))
    return out


def frac_le(vals, th=TH):
    return (sum(1 for v in vals if v <= th) / len(vals)) if vals else None


def run(arm: str, seq: str, seed: int) -> dict | None:
    p = R / f"r33_rebase_{arm}_{seq}_seed{seed}.consolelog"
    if not p.exists():
        return None
    d = parse_log(p)
    confs = [c for _, c, _ in d["gate"]]
    prox = masked_proxy(d["gate"], d["mask"])
    return {
        "n_gate_lines": len(d["gate"]),
        "n_skip": len(d["skip_kf"]),
        "n_inner_skip": len(d["inner_skip"]),
        "n_swba_ran": len(d["edges"]),
        "conf_mean": st.mean(confs) if confs else None,
        "conf_median": st.median(confs) if confs else None,
        "conf_min": min(confs) if confs else None,
        "conf_max": max(confs) if confs else None,
        "frac_conf_le_th": frac_le(confs),
        "frac_proxy_le_th": frac_le([c for _, _, c, _ in prox]),
        "proxy_mean": st.mean([c for _, _, c, _ in prox]) if prox else None,
        "dyn_frac_mean": st.mean([x for _, _, _, x in prox]) if prox else None,
        "mask_px_mean": st.mean([px for _, px in d["mask"]]) if d["mask"] else None,
        "dt_med_cm_mean": (st.mean([e["dt_med_cm"] for e in d["edges"] if e["dt_med_cm"] is not None])
                           if any(e["dt_med_cm"] is not None for e in d["edges"]) else None),
        "n_dt_survivors": sum(1 for e in d["edges"] if e["dt_med_cm"] is not None),
        "dt_med_cm_max": max((e["dt_med_cm"] for e in d["edges"] if e["dt_med_cm"] is not None), default=None),
        "dc_pct_mean": (st.mean([e["dc_pct"] for e in d["edges"] if e["dc_pct"] is not None])
                        if any(e["dc_pct"] is not None for e in d["edges"]) else None),
        "n_edges_sum": sum(e["n_edges"] for e in d["edges"]) or None,
        "lc": d["lc"],
        "swba_failed": d["swba_failed"],
    }


def main():
    ate = json.loads(PREVIEW.read_text())
    out = {"img_px": IMG_PX, "threshold": TH, "runs": {},
           "effects": {}, "note": "prereg: diag_ate_degradation_prereg.md"}

    for arm in ARMS:
        for seq in SEQS:
            for seed in SEEDS:
                r = run(arm, seq, seed)
                if r is not None:
                    out["runs"][f"{arm}|{seq}|{seed}"] = r

    # 序列级效应（ate_mean 均值差，负=改善/救回）
    for seq in SEQS:
        a = {arm: ate[f"{arm}|{seq}"]["ate_mean"] for arm in ARMS}
        out["effects"][seq] = {
            "ate": a,
            "E_SWBA": round(a["swbaonly"] - a["baseline"], 3),
            "E_LC": round(a["final"] - a["swbaonly"], 3),
            "E_gate": round(a["gate"] - a["final"], 3),
        }

    # H1：现行信号 vs masked 代理的“门开 ⇔ SWBA 有益”一致率（判定规则见预注册 §3）
    rows = []
    for seq in SEQS:
        g = [out["runs"][k] for k in out["runs"] if k.startswith(f"gate|{seq}|")]
        so = [out["runs"][k] for k in out["runs"] if k.startswith(f"swbaonly|{seq}|")]
        cur = st.mean([r["frac_conf_le_th"] for r in g if r["frac_conf_le_th"] is not None])
        pro = st.mean([r["frac_proxy_le_th"] for r in g if r["frac_proxy_le_th"] is not None])
        e = out["effects"][seq]["E_SWBA"]
        beneficial = e < 0 or abs(e) < 0.2
        rows.append({
            "seq": seq, "E_SWBA": e, "beneficial": beneficial,
            "frac_conf_le_th": round(cur, 3), "frac_proxy_le_th": round(pro, 3),
            "cur_open": cur > 0.5, "proxy_open": pro > 0.5,
            "cur_consistent": (cur > 0.5) == beneficial,
            "proxy_consistent": (pro > 0.5) == beneficial,
            "conf_mean": round(st.mean([r["conf_mean"] for r in g if r["conf_mean"] is not None]), 3),
            "proxy_mean": round(st.mean([r["proxy_mean"] for r in g if r["proxy_mean"] is not None]), 3),
            "dyn_frac_mean": round(st.mean([r["dyn_frac_mean"] for r in g if r["dyn_frac_mean"] is not None]), 3),
            "skip_frac_gate_arm": round(st.mean([r["n_skip"] / r["n_gate_lines"] for r in g if r["n_gate_lines"]]), 3),
            "dt_med_mean_swbaonly": round(st.mean([r["dt_med_cm_mean"] for r in so if r["dt_med_cm_mean"] is not None]), 3) if any(r["dt_med_cm_mean"] is not None for r in so) else None,
            "kf_count": round(st.mean([r["n_gate_lines"] for r in g]), 1),
        })
    out["h1_table"] = rows
    out["h1_consistency"] = {
        "current": sum(r["cur_consistent"] for r in rows),
        "proxy": sum(r["proxy_consistent"] for r in rows),
        "n": len(rows),
    }

    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))

    # stdout 摘要（dump-to-table，写报告直接抄这里）
    print(f"=== H1 门开(占比>50%的KF conf≤{TH}) ⇔ SWBA 有益(E_SWBA<0 或 |E|<0.2) ===")
    print(f"{'seq':14s} {'E_SWBA':>7s} {'benef':>5s} | {'conf均':>6s} {'代理均':>6s} {'dyn%':>5s} | {'现行开':>6s} {'代理开':>6s} | {'一致(现)':>7s} {'一致(代)':>7s}")
    for r in rows:
        print(f"{r['seq']:14s} {r['E_SWBA']:+7.2f} {str(r['beneficial']):>5s} | "
              f"{r['conf_mean']:6.3f} {r['proxy_mean']:6.3f} {r['dyn_frac_mean']:5.3f} | "
              f"{r['frac_conf_le_th']:6.3f} {r['frac_proxy_le_th']:6.3f} | "
              f"{str(r['cur_consistent']):>7s} {str(r['proxy_consistent']):>7s}")
    c = out["h1_consistency"]
    print(f"\n一致率：现行 {c['current']}/{c['n']}  vs  masked 代理 {c['proxy']}/{c['n']}")
    print("\n=== 效应分解（3-seed 均值；负=改善/救回）===")
    print(f"{'seq':14s} {'base':>7s} {'+SWBA':>7s} {'+LC':>7s} {'gate':>7s} | {'E_SWBA':>7s} {'E_LC':>7s} {'E_gate':>7s}")
    for seq in SEQS:
        e = out["effects"][seq]
        print(f"{seq:14s} {e['ate']['baseline']:7.2f} {e['ate']['swbaonly']:7.2f} "
              f"{e['ate']['final']:7.2f} {e['ate']['gate']:7.2f} | "
              f"{e['E_SWBA']:+7.2f} {e['E_LC']:+7.2f} {e['E_gate']:+7.2f}")
    print(f"\nJSON → {OUT}")


if __name__ == "__main__":
    main()
