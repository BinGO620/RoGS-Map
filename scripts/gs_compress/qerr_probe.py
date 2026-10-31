#!/usr/bin/env python
"""qerr_probe.py — 零 GPU 量化误差探针（S0.5，G1 整改：直接测机制核心主张）。

G1 致命-1 指出：range 膨胀 (infl) 不等于 PSNR 会升——必须直接测"量化误差"。
本探针不渲染，直接在 PLY 上算每属性组的**均方量化误差 (MSE)** 与**加权 MSE**：

  对每个属性组 g、位宽 b：
    v1 (global)  : lo,hi = min,max;  e = dequant(quant(a)) - a
    v2robust     : lo,hi = p_q,p_{100-q}; 尾 clip 到边界;  e 同上
    v2escape     : 同 v2robust 但尾部用**更细的专属位宽**（模拟 escape 后残差通道）
   线性对照     : 直接用 (span_full/(2^b-1))^2/12 的均匀量化理论方差

  指标：
    mse_g        : 该组全体基元的 MSE（所有通道平均）
    mse_bulk     : 稳健范围内 (1-2q) 基元的 MSE（机制"声称变细"的那部分）
    mse_ratio    : mse_v2 / mse_v1（<1 = 变好）
    weighted     : 按 attribute 对渲染的敏感度加权（用 L1 实测敏感度序，见下）

结论判读（先锁）：
  * 若 bulk mse_ratio 在**全组**显著 <1（如 ≤0.8）⇒ 范围机制有真实误差收益 ⇒ 机制前提成立，可续。
  * 若仅个别组 <1，或 ratio ≈1 ⇒ infl 是诊断假象 ⇒ 机制前提不成立，**击杀**（G1 致命-1 属实证）。

敏感度权重（来自 l1_readout §3 实测，单组粗化 ΔPSNR）：
  opacity 最不敏感(0.003) < f_dc(0.008) < xyz(0.037) < rot(0.095) < scale(0.111)
  ⇒ 权重 ∝ 该序（归一到 scale=1）。
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np
from plyfile import PlyData

REPO = Path(__file__).resolve().parents[2]
GROUPS = {
    "xyz": ["x", "y", "z"],
    "f_dc": ["f_dc_0", "f_dc_1", "f_dc_2"],
    "opacity": ["opacity"],
    "scale": ["scale_0", "scale_1", "scale_2"],
    "rot3": ["rot_1", "rot_2", "rot_3"],
}
BITS = {"xyz": 16, "f_dc": 8, "opacity": 8, "scale": 8, "rot3": 8}
W = {"opacity": 0.003, "f_dc": 0.008, "xyz": 0.037, "rot3": 0.095, "scale": 0.111}


def _q(a, bits, lo, hi):
    lv = (1 << bits) - 1
    if hi <= lo:
        return np.zeros_like(a)
    return np.clip(np.round((a - lo) / (hi - lo) * lv), 0, lv)


def _dq(q, bits, lo, hi):
    lv = (1 << bits) - 1
    return q / lv * (hi - lo) + lo


def mse(a, bits, lo, hi):
    return float(np.mean((_dq(_q(a, bits, lo, hi), bits, lo, hi) - a) ** 2))


def probe_group(a_flat, bits, q, esc_bits_lo=0.5):
    """返回 v1/v2robust/v2escape 的（全组 mse, 稳健主体 mse）。"""
    lo_f, hi_f = float(a_flat.min()), float(a_flat.max())
    plo, phi = np.percentile(a_flat, q), np.percentile(a_flat, 100 - q)
    bulk = (a_flat >= plo) & (a_flat <= phi)
    out = {"span_full": hi_f - lo_f, "span_robust": float(phi - plo),
           "tail_frac": float((~bulk).mean())}
    # v1
    out["mse_v1"] = mse(a_flat, bits, lo_f, hi_f)
    out["mse_v1_bulk"] = mse(a_flat[bulk], bits, lo_f, hi_f)
    # v2 robust（尾部 clip 到边界 —— 误差含 clip 误差）
    out["mse_v2"] = mse(a_flat, bits, plo, phi)
    out["mse_v2_bulk"] = mse(a_flat[bulk], bits, plo, phi)
    # v2 escape：尾部单独用更细位宽（模拟 escape 残差），主体同 v2robust
    qe = max(1, int(round(bits * esc_bits_lo)) + bits)  # 尾部专属位宽 ≈ 1.5×b
    if (~bulk).any():
        tail_mse = mse(a_flat[~bulk], qe, lo_f, hi_f)
    else:
        tail_mse = 0.0
    out["mse_v2esc"] = float(bulk.mean() * out["mse_v2_bulk"] + (~bulk).mean() * tail_mse)
    out["mse_v2esc_tailbits"] = int(qe)
    # ratios
    out["ratio_bulk"] = out["mse_v2_bulk"] / out["mse_v1_bulk"] if out["mse_v1_bulk"] > 0 else None
    out["ratio_full"] = out["mse_v2"] / out["mse_v1"] if out["mse_v1"] > 0 else None
    out["ratio_esc"] = out["mse_v2esc"] / out["mse_v1"] if out["mse_v1"] > 0 else None
    return out


def find_ply(seq, arm, seed=0):
    pat = (f"results/paper2_fulltable/{seq}_{arm}_seed{seed}/datasets_bonn/*/"
           f"seed_{seed}/*/point_cloud/final/point_cloud.ply")
    g = glob.glob(str(REPO / pat))
    return g[0] if g else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", type=float, default=0.1)
    ap.add_argument("--out", default="results/gs_compress/evidence/qerr_probe.json")
    ap.add_argument("--out-md", default="results/gs_compress/evidence/qerr_probe_2026-10-04.md")
    args = ap.parse_args()

    targets = [("balloon", "baseline"), ("crowd2", "baseline"),
               ("person_tracking", "baseline"), ("crowd3", "final"),
               ("person_tracking2", "final")]
    res = {"q": args.q, "maps": []}
    for seq, arm in targets:
        p = find_ply(seq, arm)
        if not p:
            print("MISS", seq, arm); continue
        v = PlyData.read(p)["vertex"]
        names = {x.name for x in v.properties}
        rec = {"seq": seq, "arm": arm, "n": len(v), "groups": {}}
        for g, comps in GROUPS.items():
            if any(c not in names for c in comps):
                continue
            a = np.stack([np.asarray(v[c], dtype=np.float64) for c in comps], 1).ravel()
            rec["groups"][g] = probe_group(a, BITS[g], args.q)
        # 加权（用 ratio_esc，机制真实形态）
        num = den = 0.0
        for g, r in rec["groups"].items():
            if r["ratio_esc"] is None:
                continue
            num += W[g] * r["ratio_full"]; den += W[g]
        rec["weighted_ratio_full"] = num / den if den else None
        res["maps"].append(rec)
        gg = rec["groups"]
        print(f"[qerr] {seq:16s} {arm:8s} " + " ".join(
            f"{g}:{gg[g]['ratio_full']:.3f}" for g in GROUPS if g in gg))

    (REPO / args.out).parent.mkdir(parents=True, exist_ok=True)
    (REPO / args.out).write_text(json.dumps(res, indent=2))

    L = [f"# S0.5 量化误差探针（G1 整改：直测机制核心主张，q={args.q}%）", "",
         "> 零 GPU，直接在 PLY 上算 quantize→dequantize 的 MSE（不渲染）。",
         "> `ratio_full = mse_v2 / mse_v1`（<1 = 稳健范围降低量化误差）。", "",
         "| seq | arm | 组 | span_full | span_robust | tail% | mse_v1 | ratio_full | ratio_esc |",
         "|---|---|---|---|---|---|---|---|---|"]
    for m in res["maps"]:
        for g, r in m["groups"].items():
            L.append(f"| {m['seq']} | {m['arm']} | {g} | {r['span_full']:.4f} | "
                     f"{r['span_robust']:.4f} | {r['tail_frac']*100:.3f} | {r['mse_v1']:.3e} | "
                     f"{r['ratio_full']:.4f} | {r['ratio_esc']:.4f} |")
    L += ["", "| seq | arm | 加权 ratio_full |", "|---|---|---|"]
    for m in res["maps"]:
        L.append(f"| {m['seq']} | {m['arm']} | {m['weighted_ratio_full']:.4f} |")
    (REPO / args.out_md).write_text("\n".join(L))
    print(f"[qerr] wrote {args.out} + {args.out_md}")


if __name__ == "__main__":
    main()
