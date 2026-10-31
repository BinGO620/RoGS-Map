#!/usr/bin/env python
"""diag_causal_fairness.py — 负结果的公平性审计（**纯重分析，无新渲染**）。

动机（用户 2026-09-19 指示："失败的线也要看看实验配置是否对等，是否真的失败"）：
因果轮 I/II 判 NO-GO，但四条臂都用**整团点云的全局运动估计**（质心/刚性），
而文献（DynaGSLAM，见 `resources/lit_dyn_mapping/mechanisms.md` V2）用的是
**逐基元 KNN 复用/搬移 + 逐基元速度**。故须先回答："失败"是机制的，还是被
(a) KF 间隔 Δt、(b) KF 时刻的掩码质量、(c) 臂设计（每帧重新拟合、不累积）拉下来的。

本脚本只读已落盘的结果 JSON，输出：
  ① 因果保留率 **按 Δt 分桶**（若随 Δt 陡降 ⇒ 限制来自 KF 间隔）；
  ② 因果保留率 **按插入帧掩码规模分桶**（n_dyn 分位；若掩码大的帧保留率高 ⇒ 掩码驱动）；
  ③ 各臂**拟合改善比**（loss_first→last）——检查"因果臂的拟合是否比 oracle 更差"（配置对等性）；
  ④ 每帧明细（frame, dt, n_dyn, 各臂 bad_dl1/bad_psnr）供人工核对。

用法：
  /data/conda_envs/monogs-ours/bin/python scripts/02_analysis/diag_causal_fairness.py \
     --out results/embrace_dyn/evidence/diag_causal_fairness.json
"""
import argparse
import json
import statistics
from pathlib import Path

FILES = {
    "pt2_round2": ("results/embrace_dyn/evidence/dyn_probe_causal2_results.json",
                   ["P1", "P2", "P2c", "P2cs", "P2cm", "P2cr"]),
    "pt2_round1": ("results/embrace_dyn/evidence/dyn_probe_causal_results.json",
                   ["P1", "P2", "P2c", "P2cv"]),
    "balloon": ("results/embrace_dyn/evidence/dyn_probe_balloon_results.json",
                ["P1", "P2", "P2c"]),
}


def _m(recs, key):
    vs = [r[key] for r in recs if r.get(key) is not None]
    return statistics.mean(vs) if vs else None


def retention(per_frame, arm, metric):
    """同帧集保留率：dl1 用 (P1−X)/(P1−P2)；psnr 用 (X−P1)/(P2−P1)。"""
    fr = [k for k in per_frame if all(per_frame[k].get(a, {}).get(metric) is not None
                                      for a in ("P1", "P2", arm))]
    if len(fr) < 2:
        return None, 0
    def mean(a):
        return statistics.mean(per_frame[k][a][metric] for k in fr)
    p1, p2, x = mean("P1"), mean("P2"), mean(arm)
    if metric.endswith("dl1_cm"):
        den = p1 - p2
        return (None if den <= 0.5 else round((p1 - x) / den, 4)), len(fr)
    den = p2 - p1
    return (None if den <= 0.5 else round((x - p1) / den, 4)), len(fr)


def audit(path, arms):
    if not Path(path).exists():
        return None
    d = json.load(open(path))
    out = {}
    for tag, ad in d["arms"].items():
        # 逐帧表（以 P2c 的元数据为准：dt_eval / n_dyn / kf）
        ref = ad.get("P2c") or ad.get("P2cs") or []
        per = {}
        for r in ref:
            if r.get("dyn_psnr") is None or r.get("dt_eval") is None:
                continue
            fr = int(r["frame"])
            per[fr] = {"dt": r["dt_eval"], "n_dyn": r.get("n_dyn"), "kf": r.get("kf"),
                       "mask_cc_frac": r.get("mask_cc_frac"), "icp_rmse_m": r.get("icp_rmse_m")}
            for a in arms:
                rec = next((x for x in ad.get(a, []) if int(x["frame"]) == fr), None)
                if rec:
                    per[fr][a] = {k: rec.get(k) for k in ("dyn_bad_psnr", "dyn_bad_dl1_cm",
                                                          "dyn_psnr", "dyn_dl1_cm", "static_psnr", "full_psnr")}
        frames = sorted(per)
        if not frames:
            continue
        rec = {"n_frames": len(frames),
               "by_dt": {}, "by_mask_size": {}, "fit_improve": {}, "per_frame": {}}
        # ① 按 Δt 分桶
        for arm in [a for a in arms if a not in ("P1", "P2")]:
            for dt in sorted({per[f]["dt"] for f in frames}):
                sub = {f: per[f] for f in frames if per[f]["dt"] == dt}
                # P1/P2 也限制到该桶（同帧集）
                r_dl1, n = retention(sub, arm, "dyn_bad_dl1_cm")
                r_psnr, _ = retention(sub, arm, "dyn_bad_psnr")
                rec["by_dt"].setdefault(f"{arm}", {})[f"dt={int(dt)}"] = {
                    "n": n, "retention_bad_dl1": r_dl1, "retention_bad_psnr": r_psnr}
        # ② 按插入帧掩码规模 n_dyn 分桶（中位数切两半）
        for arm in [a for a in arms if a not in ("P1", "P2")]:
            nd = [per[f]["n_dyn"] for f in frames if per[f].get("n_dyn")]
            if len(nd) < 4:
                continue
            med = statistics.median(nd)
            for label, sel in (("n_dyn<median", [f for f in frames if (per[f].get("n_dyn") or 0) < med]),
                               ("n_dyn>=median", [f for f in frames if (per[f].get("n_dyn") or 0) >= med])):
                sub = {f: per[f] for f in sel}
                r_dl1, n = retention(sub, arm, "dyn_bad_dl1_cm")
                r_psnr, _ = retention(sub, arm, "dyn_bad_psnr")
                rec["by_mask_size"].setdefault(arm, {})[label] = {
                    "n": n, "retention_bad_dl1": r_dl1, "retention_bad_psnr": r_psnr,
                    "median_n_dyn_threshold": med}
        # ③ 拟合改善比（配置对等性检查）
        for arm in arms:
            fits = [r["fit"] for r in ad.get(arm, [])
                    if isinstance(r.get("fit"), dict) and r["fit"].get("loss_first")]
            if fits:
                rec["fit_improve"][arm] = {
                    "n": len(fits),
                    "mean_loss_first": round(statistics.mean(f["loss_first"] for f in fits), 5),
                    "mean_loss_last": round(statistics.mean(f["loss_last"] for f in fits), 5),
                    "mean_reduction_ratio": round(statistics.mean(
                        f["loss_last"] / f["loss_first"] for f in fits), 4),
                    "mean_opa_after": round(statistics.mean(f["opa_mean_after"] for f in fits), 4)}
        rec["per_frame"] = per
        out[tag] = rec
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/embrace_dyn/evidence/diag_causal_fairness.json")
    args = ap.parse_args()
    res = {"purpose": "fairness audit of the NO-GO: is the failure mechanism-caused, or Δt / KF-mask-quality / arm-design caused?",
           "note": "pure re-analysis of landed result JSONs; no new rendering",
           "sources": {k: v[0] for k, v in FILES.items()}}
    for name, (path, arms) in FILES.items():
        a = audit(path, arms)
        if a:
            res[name] = a
    Path(args.out).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(f"written {args.out}\n")
    for name in FILES:
        if name not in res:
            continue
        for tag, rec in res[name].items():
            print(f"== {name}/{tag} (n={rec['n_frames']})")
            for arm, buckets in rec["by_dt"].items():
                s = "  ".join(f"{k}: dl1={v['retention_bad_dl1']} psnr={v['retention_bad_psnr']} (n={v['n']})"
                              for k, v in buckets.items())
                print(f"   {arm} by Δt → {s}")
            for arm, buckets in rec["by_mask_size"].items():
                s = "  ".join(f"{k}: dl1={v['retention_bad_dl1']} psnr={v['retention_bad_psnr']} (n={v['n']})"
                              for k, v in buckets.items())
                print(f"   {arm} by mask size → {s}")
            for arm, f in rec["fit_improve"].items():
                print(f"   fit[{arm}]: n={f['n']} {f['mean_loss_first']}→{f['mean_loss_last']} "
                      f"(ratio {f['mean_reduction_ratio']}, opa→{f['mean_opa_after']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
