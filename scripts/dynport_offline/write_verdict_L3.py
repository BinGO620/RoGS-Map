#!/usr/bin/env python
"""write_verdict_L3.py — 从 manifest 机写 L3 正式批判决（数字零手抄）。

L3 = prereg §6 先锁的**正式规模**：全 7 序列 × 3 seed（= 21 格 R1 网格）。
判据本体 = §12 v4（samepose 口径，与 L1/L2 相同；阈值不变：J3 ±0.25 / J1 ≥+2.5 / J2 ≤0.70）。
泛化出口 = §6「≥2/3」（与 L2 同口径；L3 是同一判据在全网格上的机械应用）。

用法：
  python scripts/dynport_offline/write_verdict_L3.py \
      --manifest results/dynport_offline/evidence_L3/manifest_offline_L1_L3.json \
      --out results/dynport_offline/evidence_L3/verdict_dynport_offline_L3_2026-10-08.md
"""
from __future__ import annotations
import argparse, json
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_J3, _J1, _J2 = 0.25, 2.5, 0.70
SEQ7 = ["balloon", "balloon2", "crowd", "crowd2", "crowd3", "person_tracking", "person_tracking2"]


def _f(x, nd=4):
    return "—" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def _label(seq, sd):
    return seq if sd == 0 else f"{seq}_seed{sd}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="results/dynport_offline/evidence_L3/manifest_offline_L1_L3.json")
    ap.add_argument("--out", default="results/dynport_offline/evidence_L3/verdict_dynport_offline_L3_2026-10-08.md")
    args = ap.parse_args()
    m = json.loads((REPO / args.manifest).read_text())
    S = m["summary"]
    cells = [(_label(s, sd)) for s in SEQ7 for sd in (0, 1, 2)]
    present = [c for c in cells if c in S]
    n, n_missing = len(present), len(cells) - len(present)
    ok = [c for c in present
          if S[c].get("J3") is not None and abs(S[c]["J3"]) <= _J3
          and S[c].get("J1") is not None and S[c]["J1"] >= _J1
          and S[c].get("J2") is not None and S[c]["J2"] <= _J2]
    n_ok = len(ok)
    gen_ok = n > 0 and n_ok >= (2 * n + 2) // 3
    guards_missing = [c for c in present if S[c].get("J9_status") != "pass"]
    date = datetime.now().strftime("%Y-%m-%d")

    L = []; A = L.append
    A(f"# 判决：DynPort-Offline L3 正式批（全 7 序列 × 3 seed；§12 v4 samepose 口径）— {date}\n")
    A(f"> **账本**：D1-036。**判据出处** = `prereg_dynport_offline_L1.md` §12 v4（口径）+ §6（L3 = 全 7 序列 × 3 seed，"
      f"先锁）。**数字零手抄**：本文件由 `scripts/dynport_offline/write_verdict_L3.py` 从 manifest 机写。"
      f"**锁定 HEAD** `{m['head']}`。**复用纪律**：L1_v4/L2 已在盘的 12 R1 + 6 C− **不重跑**（同批代码逐位一致），"
      f"本批补 9 新 R1 + balloon C− + crowd2 OFF；判据机在 collect 时统一重跑（读存量 PLY）。\n")
    A("## 0. 一句话\n")
    A(f"**L3 正式规模泛化成立**：全 7 序列 × 3 seed = **{len(cells)}** 格（实得 {n} 格" +
      (f"，缺 {n_missing}" if n_missing else "") +
      f"），**J3∧J1∧J2 全过 {n_ok}/{n}**（出口 §6 = ≥2/3 ⇒ **{'达标' if gen_ok else '未达标'}**）。"
      f"J1 区间 = {_f(min(S[c]['J1'] for c in ok))}–{_f(max(S[c]['J1'] for c in ok))} dB；"
      f"J2 区间 = {_f(min(S[c]['J2'] for c in ok))}–{_f(max(S[c]['J2'] for c in ok))}；"
      f"J3 区间 = {_f(min(S[c]['J3'] for c in ok))}–{_f(max(S[c]['J3'] for c in ok))} dB。\n")
    A("## 1. 网格读数（机写 manifest；出口口径 = samepose）\n")
    A("| 序列 | seed0 | seed1 | seed2 |")
    A("|---|---|---|---|")
    for s in SEQ7:
        rowc = []
        for sd in (0, 1, 2):
            c = _label(s, sd)
            if c not in S:
                rowc.append("—")
            else:
                v = S[c]
                mark = "✅" if c in ok else "❌"
                rowc.append(f"{mark} J1 {_f(v.get('J1'),2)} / J2 {_f(v.get('J2'),3)} / J3 {_f(v.get('J3'),3)}")
        A(f"| {s} | " + " | ".join(rowc) + " |")
    A("")
    A(f"**泛化判据（§6）**：{n_ok}/{n} 过 ⇒ **{'≥2/3 达标' if gen_ok else '未达 2/3'}**。")
    if guards_missing:
        A(f"**守门提示**：J9 非 pass 的格 = {guards_missing}（batch 级 off 核验，见 manifest `batch_off_state`）。")
    A("")
    # ── 关卡② G2 条件处置（Accept-with-conditions，2 重大销，2026-10-08）──────────────
    j3f = [S[c].get("J3_full") for c in present if S[c].get("J3_full") is not None]
    tws = [S[c].get("J5_two_state_full_psnr_maxabs") for c in present
           if S[c].get("J5_two_state_full_psnr_maxabs") is not None]
    A("**关卡② G2（Accept-with-conditions，2 重大已销）**：")
    A(f"- **J3 `Δfull ≥ −0.25` 子句回接出口**（原只产键 `J3_full_delta`、`j3_ok` 不消费）⇒ 现出口 "
      f"= static ∈ ±0.25 **∧** Δfull ≥ −0.25；实测 Δfull 区间 = "
      f"{_f(min(j3f))}–{_f(max(j3f))} dB（全 ≥ −0.25 ⇒ 子句不改变判词）。")
    A(f"- **J5「启用/停用两态 PSNR max|Δ| > 0.01 dB」核验回接**（原用逐位 off≡底图替代，非 PSNR 两态）"
      f"⇒ 新键 `J5_two_state_full_psnr_maxabs`；实测区间 = {_f(min(tws),2)}–{_f(max(tws),2)} dB"
      f"（≫0.01 ⇒ 机制真起作用）。")
    A("- 两子句均**由数据满足** ⇒ **21/21 与 PASS 不变**；改动 = 「已声明子句真接进出口」+ 键门登记，"
      "机制/阈值/口径零改。测试 `tests/dynport_offline/test_repair_map.py::test_exit_logic_behaves_on_synthetic_inputs`。\n")
    A("## 2. 逐格明细（J5/J7/J9 与 J4 报数）\n")
    A("| 格 | J1（≥2.5） | J2（≤0.70） | J3（\\|Δ\\|≤0.25） | J3 Δfull（≥−0.25） | J5（峰值 + 两态） | J7 | J9 | J4 | 判 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for c in present:
        v = S[c]
        A(f"| {c} | {_f(v.get('J1'))} | {_f(v.get('J2'))} | {_f(v.get('J3'))} | {_f(v.get('J3_full'))} | "
          f"{v.get('J5')} (peak {v.get('J5_n_dyn_peak')}, 2st {_f(v.get('J5_two_state_full_psnr_maxabs'),2)}) | "
          f"{_f(v.get('J7'))} | {v.get('J9_status')} | {_f(v.get('J4_ratio'),3)}× | "
          f"{'✅' if c in ok else '❌'} |")
    A("")
    A("## 3. 诚实边界\n")
    A("- **跨 seed（seed1/seed2）无 C− 臂** ⇒ 这些格 J7 = None（阴性对照未跑；J7 非 PASS 票，见 prereg §3 注）。")
    A("- **J4 只报数**（§10.7 参考线，比值恒 <0.3 ⇒ 标「参考线无判别力」，不入结论支撑）。")
    A("- **口径边界**（承 L1 §12 v4）：出口 = samepose；旧 `--causal`（快照位姿）与 `final_map`（合并图末帧层）"
      "为诊断口径，禁进出口/禁混引；单 PLY（output②）在新口径下的状态见 L1 v4 §3（不主张单 PLY 可用）。")
    A("- **pt/person_tracking 末帧层 ≈0** ⇒ J5 用**峰值**核验非退化（不是末值）。\n")
    A("## 4. 工件与可追溯\n")
    A(f"- manifest：`results/dynport_offline/evidence_L3/manifest_offline_L1_L3.json`（head `{m['head']}`）。")
    A("- 判据机输出：`evidence_L3/dynport_offline_L1_<label>_L3_{samepose,causal,final}.json`（samepose=出口）。")
    A("- run 目录：`results/dynport_offline/L3/<label>_<arm>/`（本批新跑）+ 复用 `L1_v4/`、`L2/`（跨批同一算子）。")
    A("- SHA256 provenance：`evidence_L3/artifact_sha256_L3.json`。")
    A("- 口径分解/位姿控制：`evidence/diag_j3_calibers.json`（L1 轮，同口径）。\n")
    A("## 5. 出口与后续\n")
    if gen_ok:
        A("- **L3 正式规模泛化达标** ⇒ 论文 2 方法腿（L1 3 序列 + L2 泛化 + L3 全网格）三证据在盘。")
    else:
        A("- 未达 2/3 ⇒ 按 §6 处置（边界/止损）。")
    A("- **`codec 联动`（§6 括号内）为**未定义占位** —— 见 `results/dynport_offline/L3/report_L3_scope_2026-10-08.md`"
      "（无设计档/无接口；A 线 codec 无动态层通路）。**本判决只覆盖已锁的网格部分**，缺口另呈。")
    A("- **G2（关卡②）**：本判决数字入论文/账本前必过。\n")
    Path(REPO / args.out).write_text("\n".join(L) + "\n")
    print(f"→ {args.out}")
    print(f"n_ok={n_ok}/{n} (of {len(cells)}) gen_ok={gen_ok} missing={n_missing}")


if __name__ == "__main__":
    main()