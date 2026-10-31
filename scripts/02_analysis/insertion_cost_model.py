#!/usr/bin/env python
"""插入成本模型（P0 踩坑「prereg 成本线与插入策略自相矛盾」的补丁；零 GPU、纯读工件）。

输入：dyn_probe 格式的 results JSON（一或多个）。自动识别两类数据：
  - online 图：meta[tag].online_vitality.P0o.log 的逐走帧 {inserted, buf, evicted_total}
    （P0 embrace_online 批）；
  - classic 臂：arms[tag][arm] 逐帧 rec["n_dyn"]（单帧插入口径，历史 dyn_probe 批）。

输出（JSON + stdout 表）：
  1. 每图 online 摘要：插入速率/帧、稳态缓冲 buf_final/buf_max、触顶帧（buf 首次 ≥ cap）、
     churn（evicted/inserted）；
  2. 每图 classic 臂摘要：mean_n_dyn 与 cost_frac = mean_n_dyn / n_static；
  3. 稳态缓冲拟合 buf_ss = a + b·inserted_per_frame（**只用未钉顶的 online 图**；<2 点则
     跳过并如实说明）——b 的解释 = 无护栏时基元的"有效驻留帧数"；
  4. 预测：给定 cap 与速率 ⇒ 预测钉顶帧 = cap / rate；
  5. prereg 必填成本项模板（供后续"逐帧/持续"类策略的 prereg 引用）。

用法：
  python scripts/02_analysis/insertion_cost_model.py \
      --results results/embrace_online/evidence/p0_probe_pt2_results.json \
                results/embrace_online/evidence/p0_probe_balloon_results.json \
      --out results/embrace_online/evidence/insertion_cost_model.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

DEFAULT_CAP = 60000


def summarize_online(log, cap):
    """走帧日志 → online 摘要。log 项 = {frame, inserted, buf, evicted_total, ...}。"""
    if not log:
        return None
    inserted = np.asarray([int(e.get("inserted", 0)) for e in log], dtype=float)
    bufs = np.asarray([int(e.get("buf", 0)) for e in log], dtype=float)
    ev_total = int(log[-1].get("evicted_total", 0)) if log else 0
    ins_total = int(inserted.sum())
    pin = None
    for i, b in enumerate(bufs):
        if b >= cap:
            pin = int(log[i].get("frame", i))
            break
    return {
        "n_walked_frames": int(len(log)),
        "inserted_per_frame": round(float(inserted.mean()), 2) if len(inserted) else 0.0,
        "buf_final": int(bufs[-1]) if len(bufs) else 0,
        "buf_max": int(bufs.max()) if len(bufs) else 0,
        "pinning_frame": pin,
        "pinned": bool(pin is not None),
        "cap": int(cap),
        "inserted_total": ins_total,
        "evicted_total": ev_total,
        "churn": (round(ev_total / ins_total, 4) if ins_total > 0 else None),
    }


def summarize_classic(records, n_static):
    """classic 臂（逐帧 rec["n_dyn"]，单帧插入口径）→ 摘要。"""
    vals = [int(r["n_dyn"]) for r in records
            if isinstance(r, dict) and r.get("n_dyn") is not None]
    if not vals or not n_static:
        return None
    mean_n = float(np.mean(vals))
    return {"n_frames": len(vals), "mean_n_dyn": round(mean_n, 1),
            "cost_frac": round(mean_n / float(n_static), 4)}


def fit_steady_buffer(points):
    """points = [(rate, buf_ss), ...]（仅未钉顶图）→ (a, b)；<2 点返回 None。

    模型 buf_ss = a + b·rate（最小二乘）；b 的解释 = 无护栏时基元的有效驻留帧数。
    """
    if len(points) < 2:
        return None
    x = np.asarray([p[0] for p in points], dtype=float)
    y = np.asarray([p[1] for p in points], dtype=float)
    b, a = np.polyfit(x, y, 1)
    resid = y - (a + b * x)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = (1.0 - float((resid ** 2).sum()) / ss_tot) if ss_tot > 0 else None
    return {"a": round(float(a), 2), "b_frames": round(float(b), 2),
            "r2": (None if r2 is None else round(r2, 4)), "n_points": len(points)}


def predict_pinning_frame(cap, rate):
    """给定护栏与每帧插入量 ⇒ 预测钉顶帧（走帧数）。"""
    if rate <= 0:
        return None
    return round(float(cap) / float(rate), 1)


def analyze(results_paths, cap=DEFAULT_CAP):
    out = {"sources": [str(p) for p in results_paths], "cap": int(cap), "maps": {}, "fit": None,
           "predictions": [], "notes": []}
    fit_points, fit_labels = [], []
    for rp in results_paths:
        data = json.load(open(rp))
        for tag, meta in data.get("meta", {}).items():
            entry = {"source": str(rp), "n_static": meta.get("n_static"),
                     "online": None, "classic_arms": {}}
            vit = (meta.get("online_vitality") or {}).get("P0o") or {}
            log = vit.get("log") or []
            if log:
                s = summarize_online(log, cap)
                entry["online"] = s
                if s and not s["pinned"]:
                    fit_points.append((s["inserted_per_frame"], float(s["buf_final"])))
                    fit_labels.append(f"{Path(rp).name}:{tag}")
                elif s:
                    out["notes"].append(
                        f"{Path(rp).name}:{tag} 已钉顶（触顶帧 {s['pinning_frame']}）⇒ "
                        f"buf_final={s['buf_final']} 是护栏值，不进稳态拟合")
            for arm, recs in (data.get("arms", {}).get(tag) or {}).items():
                cs = summarize_classic(recs, meta.get("n_static"))
                if cs:
                    entry["classic_arms"][arm] = cs
            out["maps"][f"{Path(rp).stem}:{tag}"] = entry
    out["fit"] = fit_steady_buffer(fit_points)
    if out["fit"]:
        out["fit"]["points"] = [{"map": lbl, "rate": round(p[0], 2), "buf_ss": p[1]}
                                for lbl, p in zip(fit_labels, fit_points)]
    # 预测：对每个 online 图，若未钉顶，给出"在 cap 下预测钉顶帧"
    for key, entry in out["maps"].items():
        s = entry.get("online")
        if s and not s["pinned"] and s["inserted_per_frame"] > 0:
            out["predictions"].append({
                "map": key, "rate": s["inserted_per_frame"],
                "predicted_pinning_frame": predict_pinning_frame(cap, s["inserted_per_frame"])})
    out["prereg_cost_template"] = (
        "prereg 必填成本项（逐帧/持续类策略）：若 stride=S、每帧掩码均面积 A px、体素/差集去重保率 r "
        "⇒ 每帧插入 ≈ A/S²·r 基元；无护栏稳态缓冲 ≈ rate × b 帧（b = 有效驻留帧数，本工具拟合）；"
        "护栏 cap ⇒ 预测钉顶帧 ≈ cap/rate，**触顶后机制被旁路、判据不再回答机制问题**（须预声明）。")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP)
    args = ap.parse_args()
    out = analyze([Path(p) for p in args.results], cap=args.cap)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=1, ensure_ascii=False)
    print(f"[insertion_cost_model] {len(out['maps'])} maps; fit = "
          f"{('a=%.1f b=%.2f frames (r2=%s, n=%d)' % (out['fit']['a'], out['fit']['b_frames'], out['fit']['r2'], out['fit']['n_points'])) if out['fit'] else 'skipped (<2 unpinned points)'}")
    for key, e in out["maps"].items():
        s = e.get("online")
        if s:
            print(f"  {key}: rate={s['inserted_per_frame']}/frame buf_final={s['buf_final']} "
                  f"pinned={s['pinned']}@{s['pinning_frame']} churn={s['churn']}")
        for arm, cs in e["classic_arms"].items():
            print(f"  {key} [{arm}]: mean_n_dyn={cs['mean_n_dyn']} cost_frac={cs['cost_frac']}")
    for p in out["predictions"]:
        print(f"  prediction {p['map']}: pinning @ frame ~{p['predicted_pinning_frame']} (cap={out['cap']})")
    print(f"[insertion_cost_model] written {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
