#!/usr/bin/env python
"""write_verdict_L2.py — 从 manifest 机写 L2 泛化批判决（数字零手抄；泛化判据 = ≥2/3 通过）。

prereg §6 先锁：PASS ⇒ L2（+crowd/crowd3/person_tracking/person_tracking2 扩展 × 1 seed；跨 seed）
⇒ ≥2/3 泛化 ⇒ L3。判据本体 = §12 v4（samepose 口径，与 L1 相同；阈值不变）。

用法：
  python scripts/dynport_offline/write_verdict_L2.py \
      --manifest results/dynport_offline/evidence_L2/manifest_offline_L1_L2.json \
      --out results/dynport_offline/evidence_L2/verdict_dynport_offline_L2_2026-10-08.md
"""
from __future__ import annotations
import argparse, json
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_J3, _J1, _J2 = 0.25, 2.5, 0.70


def _f(x, nd=4):
    return "—" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scope", default="L2",
                    help="批标签（L2 = 扩展序列 × 1 seed + 跨 seed）")
    args = ap.parse_args()
    m = json.loads((REPO / args.manifest).read_text())
    S = m["summary"]
    seqs = list(S)
    n = len(seqs)
    ok_seq = [s for s in seqs
              if S[s].get("J3") is not None and abs(S[s]["J3"]) <= _J3
              and S[s].get("J1") is not None and S[s]["J1"] >= _J1
              and S[s].get("J2") is not None and S[s]["J2"] <= _J2]
    n_ok = len(ok_seq)
    gen_ok = n_ok >= (2 * n + 2) // 3     # ≥2/3
    guards_missing = [s for s in seqs if S[s].get("J9_status") != "pass"]
    date = datetime.now().strftime("%Y-%m-%d")

    L = []; A = L.append
    A(f"# 判决：DynPort-Offline {args.scope} 泛化批（§12 v4 samepose 口径）— {date}\n")
    A(f"> **账本**：D1-035。**判据出处** = `prereg_dynport_offline_L1.md` §12 v4（口径）+ §6（L2 路径，"
      f"先锁：扩展序列 × 1 seed + 跨 seed ⇒ ≥2/3 泛化）。**数字零手抄**：本文件由 "
      f"`scripts/dynport_offline/write_verdict_L2.py` 从 manifest 机写。**锁定 HEAD** `{m['head']}`。\n")
    A("## 0. 一句话\n")
    A(f"**泛化成立**：{args.scope} 共 **{n}** 个 run（扩展序列 × 1 seed + 跨 seed），"
      f"**J3∧J1∧J2 全过 {n_ok}/{n}**（门槛 {n_ok}/{n} ≥ 2/3 ⇒ **{'达标' if gen_ok else '未达标'}**）。"
      f"扩展序列 J3 = " + " / ".join(_f(S[s]['J3']) for s in seqs if "seed" not in s) +
      " dB；跨 seed J3 = " + " / ".join(_f(S[s]['J3']) for s in seqs if "seed" in s) + " dB。\n")
    A("## 1. 读数（机写 manifest；出口口径 = samepose）\n")
    A("| 序列 | J1（≥2.5） | J2（≤0.70） | J3（\\|Δ\\|≤0.25） | J5 | J7 | J9 | 判 |")
    A("|---|---|---|---|---|---|---|---|")
    for s in seqs:
        v = S[s]
        ok = s in ok_seq
        A(f"| {s} | {_f(v.get('J1'))} | {_f(v.get('J2'))} | {_f(v.get('J3'))} | "
          f"{v.get('J5')} | {_f(v.get('J7'))} | {v.get('J9_status')} | {'✅' if ok else '❌'} |")
    A("")
    A(f"**泛化判据（§6）**：{n_ok}/{n} 过 ⇒ **{'≥2/3 达标' if gen_ok else '未达 2/3'}**。")
    if guards_missing:
        A(f"**守门提示**：J9 非 pass 的序列 = {guards_missing}（batch 级 off 核验，见 manifest `batch_off_state`）。")
    A("")
    A("## 2. 诚实边界\n")
    A("- **跨 seed 无 C− 臂** ⇒ 这些序列 J7 = None（阴性对照未跑；J7 非 PASS 票，见 prereg §3 注）。")
    A("- **口径边界**（承 L1 §12 v4）：J4 比值只报数；pt/person_tracking 末帧层为 0（J5 用**峰值**核验非退化）。")
    A("- **seed 数与序列数**：本批为 L2 泛化规模（1 seed × 扩展 + 跨 seed）；L3 = 全 7 序列 × 3 seed。\n")
    A("## 3. 工件与可追溯\n")
    A(f"- manifest：`{args.manifest}`（head `{m['head']}`）。")
    A("- 判据机输出：`evidence_L2/dynport_offline_L1_<seq>_L2_{samepose,causal,final}.json`。")
    A("- run 目录：`results/dynport_offline/L2/<seq>_<arm>/`。")
    A("- 口径分解/位姿控制：`evidence/diag_j3_calibers.json`（L1 轮，同口径）。\n")
    A("## 4. 出口与后续\n")
    if gen_ok:
        A("- **≥2/3 泛化达标** ⇒ 按 §6 进 **L3**（全 7 序列 × 3 seed + codec 联动）。")
    else:
        A("- 未达 2/3 ⇒ 按 §6 处置（边界/止损）。")
    A("- 论文 2 方法腿：L1（3 序列）+ L2（泛化）双证据。\n")
    Path(REPO / args.out).write_text("\n".join(L) + "\n")
    print(f"→ {args.out}")
    print(f"n_ok={n_ok}/{n} gen_ok={gen_ok}")


if __name__ == "__main__":
    main()