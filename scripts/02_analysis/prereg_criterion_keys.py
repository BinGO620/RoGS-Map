#!/usr/bin/env python
"""prereg_criterion_keys.py — 类登记：**prereg 声明的机械判据键，判据机必须真产出**（可复跑、可变红）。

起因（2026-10-06，DynPort-Offline G1/G4）：
  - G1 重大 M1：prereg 声明 J3 含 `Δfull ≥ −0.25 dB`，但 `judge_dynport.py` 不产出任何 full 键
    ⇒ 该子句**永远不可判**（判据是死的，却写成"第一硬门"）。
  - G1 重大 M2 / 次要：J5/J9 在离线场景构造恒真（失去守门力）、J6 的 `bad_px 中位>0` 无落点
    ⇒ 同族：**判据可判性 = 声明的键必须能在判据链路上找到生产者**。
  - G4 条件 C7：本类必须进类登记表（脚本 + 负对照），否则同类复发即触"两轮连发 ⇒ 致命"。

规则（机械化，非人工清单）：
  1. `KEY_REGISTRY` 逐族登记：prereg 文件 → {判据名: (要求的机械键, 生产者文件清单)}。
  2. `sweep()`：对每个要求的键，在任一生产者文件里搜 `"键名"` 字面出现（粗粒度，防过度解析）；
     全无 ⇒ MISSING（该判据不可判）。
  3. `missing_keys()` 是**纯函数**，供负对照测试（能变红）。
  4. 本脚本**预期在 S3 实装前为红**（键尚未落地）——它正是"S3 必须转绿"的护栏；不属于 pytest 常驻集，
     在 G2/判效前手动跑。

用法：
  python scripts/02_analysis/prereg_criterion_keys.py            # 扫 KEY_REGISTRY（红=有缺键）
  python scripts/02_analysis/prereg_criterion_keys.py --selftest  # 负对照（门可红）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# 生产者文件（判据链路上的实现，判据键须能在此找到）
_JUDGE = "scripts/dynport/judge_dynport.py"
_COLLECT_ONLINE = "scripts/dynport/collect_L1.py"
_COLLECT_OFFLINE = "scripts/dynport_offline/collect_L1.py"
# 论文3 / CGB 的判据机（2026-10-30）
_CGB_GATE = "scripts/paper3_bpw/check_cgb_gate.py"
_CGB_JUDGE = "scripts/paper3_bpw/judge_cgb_l1.py"
_FDOSE_GATE = "scripts/paper3_bpw/check_fdose_gate.py"
_FDOSE_JUDGE = "scripts/paper3_bpw/judge_fdose.py"

# 族登记表：prereg → {判据: (要求键列表, 允许的生产者文件列表)}
KEY_REGISTRY: dict[str, dict[str, tuple[list[str], list[str]]]] = {
    "results/dynport_offline/evidence/prereg_dynport_offline_L1.md": {
        # §12 v4（2026-10-07）：J1/J2/J3 出口口径 = samepose；旧键（B/final-map、快照位姿 causal）降为诊断。
        "J3_static": (["J3_samepose_static_delta"], [_JUDGE, _COLLECT_OFFLINE]),
        "J1_dynamic": (["J1_samepose_bad_psnr_delta"], [_JUDGE, _COLLECT_OFFLINE]),
        "J2_depth": (["J2_samepose_bad_dl1_ratio"], [_JUDGE, _COLLECT_OFFLINE]),
        # 诊断口径键（须仍可产，供对照；不进出口）
        "J3_diag_finalmap": (["J3_static_delta"], [_JUDGE]),
        # M1：Δfull 子句须有机械落点（生产者须吐该键）**且回接出口**（G2 L3 major#2：
        # 原只产键、`j3_ok` 不消费 ⇒ 现要求 judge 产同帧键 `J3_samepose_full_delta` + collect 消费）。
        "J3_full": (["J3_full_delta", "J3_samepose_full_delta"], [_JUDGE, _COLLECT_OFFLINE]),
        # 次要：J6 的 bad_px 中位 >0 须有落点（且须落帧覆盖 → J6_frame_coverage）
        "J6_judgeable": (["dyn_bad_px", "J6_frame_coverage"], [_JUDGE, _COLLECT_OFFLINE]),
        # M8/J4：离线预算报数键
        "J4_offline_budget": (["repair_wall_s"], [_COLLECT_OFFLINE]),
        # G2 类「prereg 声明 ⊃ 实装（守门弱化）」：以下键证明守门**真按 prereg 实装**（非静默弱化）。
        # J5 三计数 + 峰值非退化（非"跑完即>0"）；J9 batch 级 off≡底图（非 `.get(...,True)` 默认真）；
        # J5 两态差 = **PSNR max|Δ|**（prereg §3 字面；G2 L3 major#1：原用逐位 off≡底图替代，非 PSNR）。
        # 缺任一 ⇒ 该守门不可判（MISSING）。
        "J5_guard": (["J5_counters_ok", "J5_n_dyn_peak", "J5_two_state_full_psnr_maxabs"],
                     [_JUDGE, _COLLECT_OFFLINE]),
        "J9_guard": (["J9_status", "batch_off_state"], [_COLLECT_OFFLINE]),
    },
    # 2026-10-30 新增（slam-critic M6）：论文3 / CGB 族。登记后本门即可检出
    # "预注册声明了机械判据、判据机却不产出该键"这一类（§0.3 要求新族立案即登记）。
    "paper3/results/evidence/prereg_cgb_2026-10-30.md": {
        # R1 机制门的三个子键（check_cgb_gate.py 必须真产出）
        "R1_dose": (["g1_budget_err_max_abs"], [_CGB_GATE]),
        "R1_placement": (["g2_ratio_mean"], [_CGB_GATE]),
        "R1_disjoint": (["g3_ref_extra_overlap"], [_CGB_GATE]),
        # §4 R2 剂量：两列并陈键（2026-10-30 审查 F1 后新增）
        "R2_dose_columns": (["relative_gap_online", "relative_gap_refined",
                             "columns_agree_in_sign"], [_CGB_JUDGE]),
    },
    # 2026-10-31 新增（FDose = ② 的可构造形式；DISCIPLINE「类登记表」要求新族立案即登记）：
    # 机制门 F1–F5 的机械落点。F3 已按 Amendment A1 从「跨臂索引 Jaccard」拆成
    # F3a（臂内稀疏度比，硬门）/ F3b（索引 Jaccard，报告项）。
    # 键名用**判据机源码里的字面名**（本门是 substring 匹配，不解析 JSON 路径）。
    "paper3/results/evidence/prereg_fdose_2026-10-31.md": {
        "F1_dose": (["events_with_wrong_k"], [_FDOSE_GATE]),
        "F2_plan": (["f2_plan_faithful", "f2_overflow_flag_violations",
                     "f2_plan_events"], [_FDOSE_GATE]),
        # A1 把 F3 拆成 F3a（臂内稀疏度比，硬门）/ F3b（索引 Jaccard，报告项）
        "F3a_gamma_active": (["ratio_mean", "share_above"], [_FDOSE_GATE]),
        "F3b_index_jaccard_report": (["f3b_index_jaccard"], [_FDOSE_GATE]),
        "F4_pool": (["below_pool_total"], [_FDOSE_GATE]),
        "F5_activity": (["f5_activity", "sum_sel_G", "sum_sel_S"], [_FDOSE_GATE]),
        # §6 出口：三 seed 判定键（单 seed 时判据机落 SINGLE_SEED，仍产这些键）
        "R_outcome": (["rule_applied", "mde_cm", "S_minus_G"], [_FDOSE_JUDGE]),
    },
}


def missing_keys(declared: dict[str, tuple[list[str], list[str]]],
                 corpus: dict[str, str]) -> dict[str, list[str]]:
    """纯函数：返回 {判据: [缺的键...]}。corpus = {文件路径: 文本内容}。

    要求：每个键须在**该判据允许的任一生产者文件**里字面出现；全无 ⇒ 缺。
    """
    out: dict[str, list[str]] = {}
    for crit, (keys, producers) in declared.items():
        texts = [corpus.get(p, "") for p in producers]
        miss = [k for k in keys if not any(k in t for t in texts)]
        if miss:
            out[crit] = miss
    return out


def _load_corpus(files: set[str]) -> dict[str, str]:
    corpus = {}
    for rel in files:
        f = REPO / rel
        corpus[rel] = f.read_text(errors="ignore") if f.exists() else ""
    return corpus


def sweep() -> int:
    total_missing = 0
    for prereg, declared in KEY_REGISTRY.items():
        files = {p for _k, (_ks, ps) in declared.items() for p in ps}
        corpus = _load_corpus(files)
        miss = missing_keys(declared, corpus)
        print(f"[criterion-keys] {prereg}")
        for crit, (keys, producers) in declared.items():
            bad = miss.get(crit)
            status = "OK" if not bad else f"MISSING {bad}"
            print(f"    {crit}: {keys} via {producers} => {status}")
            total_missing += len(bad or [])
    print(f"MISSING_TOTAL = {total_missing}")
    return 1 if total_missing else 0


def selftest() -> int:
    """负对照：声明键但生产者不含 ⇒ 必红；生产者含 ⇒ 必绿。"""
    declared = {"Jx": (["key_a", "key_b"], ["prod.py"])}
    # 负对照：生产者缺 key_b ⇒ 必须报出 key_b
    red = missing_keys(declared, {"prod.py": 'res["key_a"] = 1'})
    assert red == {"Jx": ["key_b"]}, f"负对照失败：缺键未被抓到 ⇒ 门失效（{red}）"
    # 正对照：生产者含两键 ⇒ 不报
    green = missing_keys(declared, {"prod.py": 'res["key_a"]=1; res["key_b"]=2'})
    assert not green, f"正对照失败：键齐备仍报警 ⇒ 过度报警（{green}）"
    # 生产者文件不存在（空语料）⇒ 视为缺（防"路径写错导致假绿"）
    empty = missing_keys(declared, {})
    assert empty == {"Jx": ["key_a", "key_b"]}, f"空语料未判缺 ⇒ 假绿风险（{empty}）"
    assert KEY_REGISTRY, "族登记表为空 —— 机制被摘除"
    print("selftest OK（缺键变红 / 齐备放行 / 空语料判缺 / 登记表非空）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    return selftest() if args.selftest else sweep()


if __name__ == "__main__":
    sys.exit(main())
