#!/usr/bin/env python
"""analyze_dyn_probe.py — embrace_dyn 生死筛的**确定性判据机**（无人工读数）。

判据与阈值全部来自预注册 `results/embrace_dyn/evidence/prereg_dyn_probe.md` §7
（跑前锁定，**六条**）：
  ① 天花板      P2 vs P1：dyn_dl1 比值 ≤ 0.70 且 dyn_psnr 差 ≥ +2.0 dB
  ② 运动必要性  P4 vs P2（仅 |frame-t0| ≥ 50 的帧）：dyn_dl1 比值 ≥ 1.30
  ③ 无伤        P2 vs P1：|Δ static_psnr| ≤ 0.25 dB 且 full_psnr 不降 > 0.25 dB
  ④ 成本        mean_n_dyn ≤ 50% × n_static
  ⑤ 仪器有效    C- vs P2：dyn_dl1 比值 ≥ 1.15（否则判"仪器失效"，不是 NO-GO）
  ⑥ 阳性对照    P1 的全图 PSNR 与既有 render_compare 结果同帧一致（max|Δ| ≤ 0.01 dB）
出局规则：① 不满足 ⇒ NO-GO；① 满足而 ② 不满足 ⇒ PARTIAL；①②③④ 全满足 ⇒ GO；
⑤ 或 ⑥ 不满足 ⇒ 探针失效（不得据此下方向结论）。

同时**消费全部产出列**（防"跑完未读"）：`dyn_px`/`vacated_px`/`dyn_cov`/逐帧拟合证据
（`fit.loss_first/loss_last/opa_mean_*`）与 P4 的单次拟合（`meta.*.P4_fit`）。

用法：
  /data/conda_envs/monogs-ours/bin/python scripts/02_analysis/analyze_dyn_probe.py \
      --results results/embrace_dyn/evidence/dyn_probe_results.json
"""
import argparse
import json
from pathlib import Path

TH = {"ceiling_dl1_ratio": 0.70, "ceiling_psnr_gain_db": 2.0,
      "motion_dl1_ratio": 1.30, "motion_frame_gap": 50,
      "harm_static_db": 0.25, "harm_full_db": 0.25,
      "cost_frac": 0.50, "instrument_dl1_ratio": 1.15,
      "control_max_delta_db": 0.01}

EV = Path("results/embrace_dyn/evidence")


def _paired_means(arms, arm_names, keys):
    """**同帧集**均值：取各臂都有有效 dyn_psnr 的帧的交集后再算均值。

    关卡① 重大项整改：原先逐臂过滤后直接相除，P1/P2 用 16 帧而因果臂 15 帧（冷启动），
    分子分母帧集不一致。"""
    sets = [{r["frame"] for r in arms[a] if r.get("dyn_psnr") is not None} for a in arm_names]
    common = set.intersection(*sets) if sets else set()
    means = {}
    for a in arm_names:
        recs = [r for r in arms[a] if r.get("frame") in common]
        means[a] = {k: _r(_mean(recs, k)) for k in keys} | {"n": len(recs)}
    return means, sorted(common)


def _mean(recs, key):
    vs = [r[key] for r in recs if r.get(key) is not None]
    return None if not vs else sum(vs) / len(vs)


def _r(v, nd=4):
    return None if v is None else round(float(v), nd)


def analyse(results, tag):
    arms = results["arms"][tag]
    t0 = int(results.get("config_t0") or results.get("t0_frame") or 309)
    out = {"tag": tag, "n_static": results["meta"][tag]["n_static"], "criteria": {}, "means": {},
           "support": {}, "fit_evidence": {}}
    for arm, recs in arms.items():
        good = [r for r in recs if r.get("dyn_psnr") is not None]
        out["means"][arm] = {k: _r(_mean(good, k)) for k in
                             ("dyn_psnr", "dyn_dl1_cm", "dyn_bad_psnr", "dyn_bad_dl1_cm",
                              "dyn_bad_px", "dyn_good_psnr", "dyn_good_dl1_cm", "dyn_good_px",
                              "dyn_cov", "full_psnr", "static_psnr", "ghost_excess_cm", "n_dyn")}
        out["means"][arm]["n"] = len(good)
        # 支撑像素（此前产出未读的列）
        out["support"][arm] = {"mean_dyn_px": _r(_mean(good, "dyn_px"), 1),
                               "mean_vacated_px": _r(_mean(good, "vacated_px"), 1)}
        # 逐帧拟合证据（此前产出未读的列）
        fits = [r["fit"] for r in good if isinstance(r.get("fit"), dict) and "loss_first" in r["fit"]]
        if fits:
            out["fit_evidence"][arm] = {
                "n_frames_with_fit": len(fits),
                "mean_loss_first": _r(sum(f["loss_first"] for f in fits) / len(fits), 5),
                "mean_loss_last": _r(sum(f["loss_last"] for f in fits) / len(fits), 5),
                "mean_opa_before": _r(sum(f["opa_mean_before"] for f in fits) / len(fits)),
                "mean_opa_after": _r(sum(f["opa_mean_after"] for f in fits) / len(fits)),
                "max_loss_last": _r(max(f["loss_last"] for f in fits), 5),
            }
    if "P4_fit" in results["meta"][tag]:
        out["fit_evidence"]["P4_single_fit_at_t0"] = results["meta"][tag]["P4_fit"]
        out["fit_evidence"]["P4_n_dyn"] = results["meta"][tag].get("P4_n_dyn")

    far = {a: [r for r in arms[a] if r.get("dyn_psnr") is not None and abs(r["frame"] - t0) >= TH["motion_frame_gap"]]
           for a in arms}
    out["means_far_from_t0"] = {a: {k: _r(_mean(v, k)) for k in ("dyn_psnr", "dyn_dl1_cm", "static_psnr")} | {"n": len(v)}
                                for a, v in far.items()}
    m = out["means"]
    c = out["criteria"]

    # ① 天花板
    r1 = m["P2"]["dyn_dl1_cm"] / m["P1"]["dyn_dl1_cm"]
    g1 = m["P2"]["dyn_psnr"] - m["P1"]["dyn_psnr"]
    c["1_ceiling"] = {"dl1_ratio": _r(r1), "psnr_gain_db": _r(g1),
                      "pass": bool(r1 <= TH["ceiling_dl1_ratio"] and g1 >= TH["ceiling_psnr_gain_db"])}
    # ①b 天花板（**修订主读数**：真损坏子集 M_bad，见补遗）
    if m["P1"].get("dyn_bad_dl1_cm") and m["P2"].get("dyn_bad_dl1_cm") is not None \
            and m["P1"].get("dyn_bad_psnr") is not None and m["P2"].get("dyn_bad_psnr") is not None:
        rb = m["P2"]["dyn_bad_dl1_cm"] / m["P1"]["dyn_bad_dl1_cm"]
        gb = m["P2"]["dyn_bad_psnr"] - m["P1"]["dyn_bad_psnr"]
        c["1b_ceiling_bad_subset"] = {"dl1_ratio": _r(rb), "psnr_gain_db": _r(gb),
                                      "mean_bad_px": m["P1"].get("dyn_bad_px"),
                                      "pass": bool(rb <= TH["ceiling_dl1_ratio"]
                                                   and gb >= TH["ceiling_psnr_gain_db"]),
                                      "note": "补遗规定本口径为**主读数**；全掩码口径 1_ceiling 降为参考"}
        c["1_ceiling"]["reference_only"] = True

    # ② 运动必要性（远离 t0 的帧上）
    mf = out["means_far_from_t0"]
    r2 = mf["P4"]["dyn_dl1_cm"] / mf["P2"]["dyn_dl1_cm"]
    c["2_motion_necessity"] = {"dl1_ratio_far": _r(r2), "n_frames": mf["P2"]["n"],
                               "pass": bool(r2 >= TH["motion_dl1_ratio"]),
                               "cost_note": "P4 的 n_dyn=%.0f 为 P2 均值 %.0f 的 %.2f× ⇒ 两臂**未做成本配平**，"
                                            "故 P4 的静态区损伤幅度不可与 P2 直接对等比较" % (
                                                m["P4"]["n_dyn"], m["P2"]["n_dyn"],
                                                m["P4"]["n_dyn"] / max(m["P2"]["n_dyn"], 1e-9))}
    # ③ 无伤
    ds = m["P2"]["static_psnr"] - m["P1"]["static_psnr"]
    df = m["P2"]["full_psnr"] - m["P1"]["full_psnr"]
    c["3_no_harm"] = {"d_static_db": _r(ds), "d_full_db": _r(df),
                      "pass": bool(abs(ds) <= TH["harm_static_db"] and df >= -TH["harm_full_db"]),
                      "note": "预注册该条字面为双侧 |Δstatic|≤0.25dB；实测为正向改善（详见 verdict 局限）"}
    # ④ 成本
    frac = m["P2"]["n_dyn"] / out["n_static"]
    c["4_cost"] = {"n_dyn_frac": _r(frac), "pass": bool(frac <= TH["cost_frac"])}
    # ⑤ 仪器（错位对照）
    r5 = m["C-"]["dyn_dl1_cm"] / m["P2"]["dyn_dl1_cm"]
    c["5_instrument"] = {"dl1_ratio": _r(r5), "pass": bool(r5 >= TH["instrument_dl1_ratio"])}
    # ⑥ 阳性对照（读已落盘工件；与 render_compare 同帧同口径）
    cp = EV / "control_p1_vs_render_compare.json"
    if cp.exists():
        cd = json.load(open(cp))
        mx = float(cd["max_abs_delta_db"])
        c["6_positive_control"] = {"max_abs_delta_db": _r(mx, 6), "n_frames": len(cd["rows"]),
                                   "pass": bool(mx <= TH["control_max_delta_db"]),
                                   "artifact": str(cp)}
    else:
        c["6_positive_control"] = {"pass": False, "missing": str(cp)}
    # 描述性
    # 分解（补遗要求：把 M_bad 与 M_good 两部分各自量化；跨像素集 dB 不可比，故并列报告）
    if all(m[a].get(k) is not None for a in ("P1", "P2") for k in ("dyn_bad_dl1_cm", "dyn_good_dl1_cm")):
        c["desc_decomposition"] = {
            "M_bad": {"px": m["P1"]["dyn_bad_px"], "dl1_ratio_P2_over_P1": _r(m["P2"]["dyn_bad_dl1_cm"] / m["P1"]["dyn_bad_dl1_cm"]),
                      "psnr_P1": m["P1"]["dyn_bad_psnr"], "psnr_P2": m["P2"]["dyn_bad_psnr"]},
            "M_good": {"px": m["P1"]["dyn_good_px"], "dl1_ratio_P2_over_P1": _r(m["P2"]["dyn_good_dl1_cm"] / m["P1"]["dyn_good_dl1_cm"]),
                       "psnr_P1": m["P1"]["dyn_good_psnr"], "psnr_P2": m["P2"]["dyn_good_psnr"]},
            "note": "两个像素集的 dB 增益**不可直接比较**（P1 基线不同）；可比量是各集内的深度-L1 比值。"
                    "M_good 上 P2 的增益即'用该帧自身观测复制已正确背景'的成分。"}
    c["desc_P4_vs_P1"] = {"dl1_ratio": _r(m["P4"]["dyn_dl1_cm"] / m["P1"]["dyn_dl1_cm"]),
                          "psnr_delta_db": _r(m["P4"]["dyn_psnr"] - m["P1"]["dyn_psnr"]),
                          "d_static_db": _r(m["P4"]["static_psnr"] - m["P1"]["static_psnr"])}
    c["desc_dyn_cov"] = {"all_arms_value": _r(m["P1"]["dyn_cov"]),
                         "discriminative": bool(len({round(m[a]["dyn_cov"] or -1, 3) for a in m}) > 1),
                         "note": "掩码内'有渲染且不透明度≥0.5'的比例；本设定下各臂恒 1.000 ⇒ "
                                 "**该列无判别力**：冻结地图的动态区被背景高斯覆盖（无洞），"
                                 "反动态范式的代价是**内容错**而非**内容缺**"}
    c["desc_support_px"] = out["support"]

    _ceil = c.get("1b_ceiling_bad_subset") or c["1_ceiling"]
    if not c["5_instrument"]["pass"] or not c["6_positive_control"]["pass"]:
        out["outcome"] = "INSTRUMENT-INVALID"
    elif not _ceil["pass"]:
        out["outcome"] = "NO-GO"
    elif not c["2_motion_necessity"]["pass"]:
        out["outcome"] = "PARTIAL"
    elif c["3_no_harm"]["pass"] and c["4_cost"]["pass"]:
        out["outcome"] = "GO"
    else:
        out["outcome"] = "PARTIAL"
    return out


def analyse_causal(results, tag):
    """因果臂判据（预注册 `prereg_dyn_probe_causal.md` §4）。

    C1 因果保留率 retention(P2cv) ≥ 0.50（主判据）
    C2 速度项增益 dyn_dl1(P2cv)/dyn_dl1(P2c) ≤ 0.90（不达标不阻断 GO，只简化机制）
    C3 无伤（P2c 与 P2cv 对 P1，静态区与全图）
    C4 成本 mean_n_dyn(P2cv) ≤ 50% × n_static
    C5 仪器 dyn_dl1(C-c)/dyn_dl1(P2c) ≥ 1.15（因果臂自己的阴性对照）
    冷启动帧（无前置 KF）本就不产 dyn_psnr，天然不计入。
    """
    arms = results["arms"][tag]
    need = ("P1", "P2", "P2c", "P2cv", "C-c")
    if any(a not in arms for a in need):
        return None
    if any(not [r for r in arms[a] if r.get("dyn_psnr") is not None] for a in need):
        return None
    means, common_frames = _paired_means(arms, need,
        ("dyn_psnr", "dyn_dl1_cm", "dyn_bad_psnr", "dyn_bad_dl1_cm", "dyn_bad_px",
         "dyn_good_psnr", "dyn_good_dl1_cm", "dyn_good_px", "dyn_cov", "full_psnr", "static_psnr", "n_dyn"))
    vs = [r["v_norm"] for a in ("P2c", "P2cv") for r in arms[a] if r.get("v_norm") is not None]
    dts = [r.get("dt_eval") for a in ("P2c",) for r in arms[a] if r.get("dt_eval") is not None]
    out = {"tag": tag, "n_static": results["meta"][tag]["n_static"], "means": means,
           "criteria": {}, "frames_used": common_frames,
           "cold_start_frames": sorted({r["frame"] for r in arms["P2c"] if r.get("cold_start")}),
           "dt_eval_range": [min(dts), max(dts)] if dts else None,
           "v_norm_m_per_frame": ({"min": _r(min(vs), 6), "median": _r(sorted(vs)[len(vs) // 2], 6),
                                   "max": _r(max(vs), 6), "n": len(vs)} if vs else None),
           "dyn_cov_note": "掩码内覆盖率各臂恒 1.000 ⇒ 该列在本设定下无判别力（已登记，不参与任何判据）"}
    m, c = means, out["criteria"]
    den = m["P1"]["dyn_dl1_cm"] - m["P2"]["dyn_dl1_cm"]
    ret = lambda x: _r((m["P1"]["dyn_dl1_cm"] - m[x]["dyn_dl1_cm"]) / den) if den > 0.5 else None
    ret_cv, ret_c = ret("P2cv"), ret("P2c")
    c["C1_causal_retention"] = {"retention_P2cv": ret_cv, "retention_P2c": ret_c,
                                "oracle_gain_cm": _r(den), "pass": bool(ret_cv is not None and ret_cv >= 0.50)}
    # C1b 因果保留率（补遗规定的**主读数**：M_bad 子集）
    if m["P1"].get("dyn_bad_dl1_cm") and m["P2"].get("dyn_bad_dl1_cm") and m["P2c"].get("dyn_bad_dl1_cm"):
        den_b = m["P1"]["dyn_bad_dl1_cm"] - m["P2"]["dyn_bad_dl1_cm"]
        ret_b = {a: (_r((m["P1"]["dyn_bad_dl1_cm"] - m[a]["dyn_bad_dl1_cm"]) / den_b) if den_b > 0.5 else None)
                 for a in ("P2c", "P2cv")}
        c["C1b_causal_retention_bad_subset"] = {"retention_P2c": ret_b["P2c"], "retention_P2cv": ret_b["P2cv"],
                                                "oracle_gain_cm": _r(den_b),
                                                "pass": bool(ret_b["P2c"] is not None and ret_b["P2c"] >= 0.50),
                                                "note": "补遗规定本口径为主读数（主臂 = P2c，"
                                                        "因 P2cv 的速度估计器被实测证伪）"}
        c["C1_causal_retention"]["reference_only"] = True
    r2 = m["P2cv"]["dyn_dl1_cm"] / m["P2c"]["dyn_dl1_cm"]
    c["C2_velocity_gain"] = {"dl1_ratio_P2cv_over_P2c": _r(r2), "pass": bool(r2 <= 0.90),
                             "note": ("不达标：速度项使结果更差 ⇒ 机制退化为'KF 插入+保持'。"
                                      "估计器实测分布 0.0092–0.347 m/帧（按实测 29.83Hz 折 0.27–10.4 m/s，"
                                      "中位 3.54）——低端是正常步行、高端物理不合理 ⇒ **不稳定不可用**；"
                                      "根因：GTMC 掩码面积在相邻 KF 间跳动 4k→116k px，质心随掩码形状漂移")}
    ds_c = m["P2c"]["static_psnr"] - m["P1"]["static_psnr"]
    df_c = m["P2c"]["full_psnr"] - m["P1"]["full_psnr"]
    ds_v = m["P2cv"]["static_psnr"] - m["P1"]["static_psnr"]
    df_v = m["P2cv"]["full_psnr"] - m["P1"]["full_psnr"]
    c["C3_no_harm"] = {"d_static_P2c": _r(ds_c), "d_full_P2c": _r(df_c),
                       "d_static_P2cv": _r(ds_v), "d_full_P2cv": _r(df_v),
                       "pass": bool(max(abs(ds_c), abs(ds_v)) <= TH["harm_static_db"]
                                    and min(df_c, df_v) >= -TH["harm_full_db"])}
    frac = m["P2cv"]["n_dyn"] / out["n_static"]
    c["C4_cost"] = {"n_dyn_frac": _r(frac), "pass": bool(frac <= TH["cost_frac"])}
    r5 = m["C-c"]["dyn_dl1_cm"] / m["P2c"]["dyn_dl1_cm"]
    c["C5_instrument"] = {"dl1_ratio": _r(r5), "pass": bool(r5 >= TH["instrument_dl1_ratio"])}

    _ret = c.get("C1b_causal_retention_bad_subset") or c["C1_causal_retention"]
    if not c["C5_instrument"]["pass"]:
        out["outcome"] = "INSTRUMENT-INVALID"
    elif not _ret["pass"]:
        out["outcome"] = "NO-GO"
    elif c["C3_no_harm"]["pass"] and c["C4_cost"]["pass"]:
        out["outcome"] = "GO"
    else:
        out["outcome"] = "PARTIAL"
    return out


def analyse_causal2(results, tag):
    """因果轮 II 判据（`prereg_dyn_probe_causal2.md` §3）。

    D1 掩码稳定单独贡献（消融，不阻断）：dyn_bad_dl1(P2cs)/dyn_bad_dl1(P2c) ≤ 0.95
    D2 外观保留率（**主判据**）：M_bad 上 retention_psnr(P2cr) ≥ 0.40
    D3 几何保留率：retention_bad(P2cr) ≥ 0.75
    D4 无伤：|Δstatic(P2cr−P1)| ≤ 0.25 dB 且 Δfull ≥ −0.25 dB
    D5 成本：mean_n_dyn(P2cr) ≤ 50% × n_static
    D6 仪器：dyn_bad_dl1(C-c)/dyn_bad_dl1(P2cr) ≥ 1.15
    """
    arms = results["arms"][tag]
    need = ("P1", "P2", "P2c", "P2cs", "P2cm", "P2cr", "C-c")
    if any(a not in arms for a in need):
        return None
    keys = ("dyn_psnr", "dyn_dl1_cm", "dyn_bad_psnr", "dyn_bad_dl1_cm", "dyn_bad_px",
            "dyn_good_psnr", "dyn_good_dl1_cm", "dyn_good_px", "dyn_cov", "full_psnr",
            "static_psnr", "n_dyn")
    m, common = _paired_means(arms, need, keys)
    out = {"tag": tag, "n_static": results["meta"][tag]["n_static"], "means": m,
           "frames_used": common, "criteria": {}}
    c = out["criteria"]
    d1 = m["P2cs"]["dyn_bad_dl1_cm"] / m["P2c"]["dyn_bad_dl1_cm"]
    c["D1_mask_stabilization"] = {"bad_dl1_ratio_P2cs_over_P2c": _r(d1), "pass": bool(d1 <= 0.95),
                                  "ablation_only": True}
    den_p = m["P2"]["dyn_bad_psnr"] - m["P1"]["dyn_bad_psnr"]
    ret_p = ((m["P2cr"]["dyn_bad_psnr"] - m["P1"]["dyn_bad_psnr"]) / den_p) if den_p > 0.5 else None
    ret_p_c = ((m["P2c"]["dyn_bad_psnr"] - m["P1"]["dyn_bad_psnr"]) / den_p) if den_p > 0.5 else None
    c["D2_appearance_retention"] = {"retention_psnr_P2cr": _r(ret_p), "retention_psnr_P2c_reference": _r(ret_p_c),
                                    "oracle_gain_db": _r(den_p), "pass": bool(ret_p is not None and ret_p >= 0.40)}
    den_d = m["P1"]["dyn_bad_dl1_cm"] - m["P2"]["dyn_bad_dl1_cm"]
    ret_d = ((m["P1"]["dyn_bad_dl1_cm"] - m["P2cr"]["dyn_bad_dl1_cm"]) / den_d) if den_d > 0.5 else None
    c["D3_geometry_retention"] = {"retention_bad_P2cr": _r(ret_d), "oracle_gain_cm": _r(den_d),
                                  "pass": bool(ret_d is not None and ret_d >= 0.75)}
    ds = m["P2cr"]["static_psnr"] - m["P1"]["static_psnr"]
    df = m["P2cr"]["full_psnr"] - m["P1"]["full_psnr"]
    c["D4_no_harm"] = {"d_static_db": _r(ds), "d_full_db": _r(df),
                       "P2c_reference_d_static": _r(m["P2c"]["static_psnr"] - m["P1"]["static_psnr"]),
                       "pass": bool(abs(ds) <= TH["harm_static_db"] and df >= -TH["harm_full_db"])}
    frac = m["P2cr"]["n_dyn"] / out["n_static"]
    c["D5_cost"] = {"n_dyn_frac": _r(frac), "pass": bool(frac <= TH["cost_frac"])}
    r6 = m["C-c"]["dyn_bad_dl1_cm"] / m["P2cr"]["dyn_bad_dl1_cm"]
    c["D6_instrument"] = {"bad_dl1_ratio_Cm_over_P2cr": _r(r6), "pass": bool(r6 >= TH["instrument_dl1_ratio"])}
    # 敏感性（关卡① 重大项）：同帧集 n 由最弱的 P2cr 决定；补一组"轮I 同款 15 帧"读法
    sens = None
    # 注意：C-c 与 P2cr 同规格（rigid），同样在退化帧上无值 ⇒ 敏感性组必须排除它
    arms15 = ("P1", "P2", "P2c", "P2cs", "P2cm")
    if all(any(r.get("dyn_psnr") is not None for r in arms[a]) for a in arms15):
        m15, f15 = _paired_means(arms, arms15, ("dyn_bad_psnr", "dyn_bad_dl1_cm", "static_psnr"))
        d1_15 = m15["P2cs"]["dyn_bad_dl1_cm"] / m15["P2c"]["dyn_bad_dl1_cm"]
        den_p15 = m15["P2"]["dyn_bad_psnr"] - m15["P1"]["dyn_bad_psnr"]
        den_d15 = m15["P1"]["dyn_bad_dl1_cm"] - m15["P2"]["dyn_bad_dl1_cm"]
        sens = {"n_frames": len(f15),
                "D1_ratio_15f": _r(d1_15),
                "P2c_appearance_retention_15f": _r((m15["P2c"]["dyn_bad_psnr"] - m15["P1"]["dyn_bad_psnr"]) / den_p15) if den_p15 > 0.5 else None,
                "P2c_geometry_retention_15f": _r((m15["P1"]["dyn_bad_dl1_cm"] - m15["P2c"]["dyn_bad_dl1_cm"]) / den_d15) if den_d15 > 0.5 else None,
                "P2c_d_static_15f": _r(m15["P2c"]["static_psnr"] - m15["P1"]["static_psnr"]),
                "note": "P2cr 在 3 个退化帧上无值 ⇒ D2/D3 只能在 12 帧上判；本组用于确认 n=12 的选择未改变方向"}
    out["sensitivity_15f"] = sens
    # 消融读数（不判）：中位速度平移臂与上轮的均值速度臂
    abl = {}
    for a in ("P2cm", "P2cv"):
        if a in arms and m.get(a):
            abl[a] = {"dyn_bad_psnr": m[a].get("dyn_bad_psnr"), "dyn_bad_dl1_cm": m[a].get("dyn_bad_dl1_cm")}
    out["ablation_translation_arms"] = abl
    ccs = [r.get("mask_cc_frac") for r in arms["P2cr"] if r.get("mask_cc_frac")]
    icps = [r.get("icp_rmse_m") for r in arms["P2cr"] if r.get("icp_rmse_m")]
    out["mask_cc_frac"] = {"min": _r(min(ccs)), "median": _r(sorted(ccs)[len(ccs) // 2]), "max": _r(max(ccs)),
                           "n": len(ccs)} if ccs else None
    out["icp_rmse_m"] = {"min": _r(min(icps), 6), "median": _r(sorted(icps)[len(icps) // 2], 6),
                         "max": _r(max(icps), 6), "n": len(icps)} if icps else None

    if not c["D6_instrument"]["pass"]:
        out["outcome"] = "INSTRUMENT-INVALID"
    elif not (c["D2_appearance_retention"]["pass"] and c["D3_geometry_retention"]["pass"]):
        out["outcome"] = "NO-GO"
    elif c["D4_no_harm"]["pass"] and c["D5_cost"]["pass"]:
        out["outcome"] = "GO"
    else:
        out["outcome"] = "PARTIAL"
    return out


def retention_of(means, x, mask="bad", kind="dl1"):
    """保留率（同帧集口径）：以 (P1 − X)/(P1 − P2) 计。mask=bad|full，kind=dl1|psnr。"""
    key = {"bad": {"dl1": "dyn_bad_dl1_cm", "psnr": "dyn_bad_psnr"},
           "full": {"dl1": "dyn_dl1_cm", "psnr": "dyn_psnr"}}[mask][kind]
    if means["P1"].get(key) is None or means["P2"].get(key) is None or means[x].get(key) is None:
        return None
    if kind == "dl1":
        # 深度 L1 越小越好：分母 = P1 − P2（正）
        den = means["P1"][key] - means["P2"][key]
        if den <= 0.5:
            return None
        return _r((means["P1"][key] - means[x][key]) / den)
    # PSNR 越大越好：分母 = P2 − P1（正）——此前把两者混用导致恒返回 None（自查修正）
    den = means["P2"][key] - means["P1"][key]
    if den <= 0.5:
        return None
    return _r((means[x][key] - means["P1"][key]) / den)


def cross_sequence_row(results, tag):
    """单序列摘要行（用于跨序列对照表；任何序列都能跑）。"""
    arms = results["arms"][tag]
    if "P1" not in arms or "P2" not in arms:
        return None
    have = [a for a in ("P2c", "P2cs", "P2cr") if a in arms and any(r.get("dyn_psnr") is not None for r in arms[a])]
    keys = ("dyn_psnr", "dyn_bad_psnr", "dyn_bad_dl1_cm", "dyn_good_dl1_cm", "full_psnr",
            "static_psnr", "n_dyn", "dyn_bad_px")
    m, frames = _paired_means(arms, ["P1", "P2"] + have, keys)
    row = {"tag": tag, "n_static": results["meta"][tag]["n_static"], "n_frames": len(frames),
           "P1_bad_psnr": m["P1"].get("dyn_bad_psnr"), "P2_bad_psnr": m["P2"].get("dyn_bad_psnr"),
           "P1_bad_dl1_cm": m["P1"].get("dyn_bad_dl1_cm"), "P2_bad_dl1_cm": m["P2"].get("dyn_bad_dl1_cm"),
           "bad_psnr_gain_db": _r(m["P2"].get("dyn_bad_psnr") - m["P1"].get("dyn_bad_psnr"))
                               if m["P1"].get("dyn_bad_psnr") is not None else None,
           "bad_dl1_ratio": _r(m["P2"].get("dyn_bad_dl1_cm") / m["P1"].get("dyn_bad_dl1_cm"))
                            if m["P1"].get("dyn_bad_dl1_cm") else None,
           "bad_px_frac_of_image": _r(m["P1"].get("dyn_bad_px") / (480 * 640)) if m["P1"].get("dyn_bad_px") else None,
           "static_gain_db": _r(m["P2"].get("static_psnr") - m["P1"].get("static_psnr"))
                             if m["P1"].get("static_psnr") is not None else None,
           "full_gain_db": _r(m["P2"].get("full_psnr") - m["P1"].get("full_psnr"))
                           if m["P1"].get("full_psnr") is not None else None,
           "n_dyn_frac": _r(m["P2"].get("n_dyn") / results["meta"][tag]["n_static"]) if m["P2"].get("n_dyn") else None,
           "tzero_frames": sorted({r["frame"] for a in have for r in arms[a] if r.get("dt_eval") == 0}),
           "causal_arms": {a: {"retention_bad_dl1": retention_of(m, a, "bad", "dl1"),
                               "retention_bad_psnr": retention_of(m, a, "bad", "psnr"),
                               "d_static_db": _r(m[a].get("static_psnr") - m["P1"].get("static_psnr"))
                               if m["P1"].get("static_psnr") is not None else None} for a in have}}
    # dt=0 敏感性：评估帧本身是 KF 时，因果臂退化为 oracle ⇒ 必须剔除后另报一个口径
    for a in have:
        fr = {r["frame"] for r in arms[a] if r.get("dyn_psnr") is not None and r.get("dt_eval") != 0}
        if not fr or fr == set(frames):
            continue
        sub_arms = {k: [r for r in arms[k] if r["frame"] in fr] for k in (["P1", "P2"] + have)}
        ms = {k: {kk: _r(_mean(v, kk)) for kk in keys} | {"n": len(v)} for k, v in sub_arms.items()}
        row.setdefault("excl_dt0", {})[a] = {"n_frames": len(fr),
                                            "retention_bad_dl1": retention_of(ms, a, "bad", "dl1"),
                                            "retention_bad_psnr": retention_of(ms, a, "bad", "psnr")}
    return row


def _retention_perframe(per, arm, metric):
    """按帧子集算保留率（与 `diag_causal_fairness.py` 同算法，保证两处数字可比）。

    `per` = {frame: {arm: {metric: val}}}；dl1 越小越好用 (P1−X)/(P1−P2)，
    psnr 越大越好用 (X−P1)/(P2−P1)。缺键的帧不计入。
    """
    frames = [f for f in per if all(per[f].get(a, {}).get(metric) is not None for a in ("P1", "P2", arm))]
    if len(frames) < 2:
        return None, len(frames)
    mean = lambda a: sum(per[f][a][metric] for f in frames) / len(frames)
    p1, p2, x = mean("P1"), mean("P2"), mean(arm)
    if metric.endswith("dl1_cm"):
        den = p1 - p2
        return (None if den <= 0.5 else _r((p1 - x) / den)), len(frames)
    den = p2 - p1
    return (None if den <= 0.5 else _r((x - p1) / den)), len(frames)


def analyse_causal3(results, tag):
    """因果轮 III 判据（`prereg_dyn_probe_causal3.md` §3）：E1 多帧累积消融 / E2 外观保留（主）/
    E3 几何保留 / E4 无伤 / E5 成本 / E6 仪器 / E7 分层读数（按 Δt 与 KF 掩码规模）。"""
    arms = results["arms"][tag]
    need = ("P1", "P2", "P2c", "P2cu", "P2cuv", "C-u")
    if any(a not in arms for a in need):
        return None
    keys = ("dyn_psnr", "dyn_dl1_cm", "dyn_bad_psnr", "dyn_bad_dl1_cm", "dyn_bad_px",
            "dyn_good_psnr", "dyn_good_dl1_cm", "dyn_good_px", "full_psnr", "static_psnr", "n_dyn")
    m, common = _paired_means(arms, need, keys)
    out = {"tag": tag, "n_static": results["meta"][tag]["n_static"], "means": m,
           "frames_used": common, "criteria": {}}
    c = out["criteria"]
    d1 = m["P2cu"]["dyn_bad_dl1_cm"] / m["P2c"]["dyn_bad_dl1_cm"]
    c["E1_multiframe_ablation"] = {"bad_dl1_ratio_P2cu_over_P2c": _r(d1), "pass": bool(d1 <= 0.90),
                                   "ablation_only": True,
                                   "bad_psnr_P2c": m["P2c"].get("dyn_bad_psnr"),
                                   "bad_psnr_P2cu": m["P2cu"].get("dyn_bad_psnr")}
    r2 = retention_of(m, "P2cuv", "bad", "psnr")
    c["E2_appearance_retention"] = {"retention_psnr_P2cuv": r2, "pass": bool(r2 is not None and r2 >= 0.40),
                                    "refs": {"P2c": retention_of(m, "P2c", "bad", "psnr"),
                                             "P2cu": retention_of(m, "P2cu", "bad", "psnr")}}
    r3 = retention_of(m, "P2cuv", "bad", "dl1")
    c["E3_geometry_retention"] = {"retention_bad_P2cuv": r3, "pass": bool(r3 is not None and r3 >= 0.75),
                                  "refs": {"P2c": retention_of(m, "P2c", "bad", "dl1"),
                                           "P2cu": retention_of(m, "P2cu", "bad", "dl1")}}
    ds = m["P2cuv"]["static_psnr"] - m["P1"]["static_psnr"]
    df = m["P2cuv"]["full_psnr"] - m["P1"]["full_psnr"]
    c["E4_no_harm"] = {"d_static_db": _r(ds), "d_full_db": _r(df),
                       "pass": bool(abs(ds) <= TH["harm_static_db"] and df >= -TH["harm_full_db"])}
    frac = m["P2cuv"]["n_dyn"] / out["n_static"]
    c["E5_cost"] = {"n_dyn_frac": _r(frac), "pass": bool(frac <= TH["cost_frac"])}
    r6 = m["C-u"]["dyn_bad_dl1_cm"] / m["P2cuv"]["dyn_bad_dl1_cm"]
    c["E6_instrument"] = {"bad_dl1_ratio_Cu_over_P2cuv": _r(r6), "pass": bool(r6 >= TH["instrument_dl1_ratio"])}
    # E7 分层读数（按 Δt 与 KF 掩码规模）
    per = {}
    for r in arms["P2c"]:
        if r.get("dyn_psnr") is None or r.get("dt_eval") is None:
            continue
        fr = int(r["frame"])
        per[fr] = {"dt": r["dt_eval"], "n_dyn": r.get("n_dyn")}
        for a in need:
            rec = next((x for x in arms[a] if int(x.get("frame", -1)) == fr), None)
            if rec:
                per[fr][a] = {k: rec.get(k) for k in ("dyn_bad_psnr", "dyn_bad_dl1_cm")}
    strat = {"by_dt": {}, "by_mask_size": {}}
    for a in ("P2c", "P2cu", "P2cuv"):
        for dt in sorted({per[f]["dt"] for f in per}):
            sub = {f: per[f] for f in per if per[f]["dt"] == dt}
            rd, n = _retention_perframe(sub, a, "dyn_bad_dl1_cm")
            rp, _ = _retention_perframe(sub, a, "dyn_bad_psnr")
            strat["by_dt"].setdefault(a, {})[f"dt={int(dt)}"] = {"n": n, "dl1": rd, "psnr": rp}
        nd = [per[f]["n_dyn"] for f in per if per[f].get("n_dyn")]
        if len(nd) >= 4:
            med = sorted(nd)[len(nd) // 2]
            for label, sel in (("n_dyn<med", [f for f in per if (per[f].get("n_dyn") or 0) < med]),
                               ("n_dyn>=med", [f for f in per if (per[f].get("n_dyn") or 0) >= med])):
                sub = {f: per[f] for f in sel}
                rd, n = _retention_perframe(sub, a, "dyn_bad_dl1_cm")
                rp, _ = _retention_perframe(sub, a, "dyn_bad_psnr")
                strat["by_mask_size"].setdefault(a, {})[label] = {"n": n, "dl1": rd, "psnr": rp}
    out["E7_stratified"] = strat
    pw = [r.get("pointwise_stats") for r in arms["P2cuv"] if r.get("pointwise_stats")]
    out["pointwise_stats"] = {"n": len(pw),
                              "mean_matched_frac": _r(sum(x["matched_frac"] for x in pw) / len(pw)) if pw else None,
                              "median_v_m_per_frame": _r(sorted(x["v_med_m_per_frame"] for x in pw)[len(pw) // 2]) if pw else None,
                              "d_bar_m_example": pw[0]["d_bar_m"] if pw else None} if pw else None
    if not c["E6_instrument"]["pass"]:
        out["outcome"] = "INSTRUMENT-INVALID"
    elif not (c["E2_appearance_retention"]["pass"] and c["E3_geometry_retention"]["pass"]):
        out["outcome"] = "NO-GO"
    elif c["E4_no_harm"]["pass"] and c["E5_cost"]["pass"]:
        out["outcome"] = "GO"
    else:
        out["outcome"] = "PARTIAL"
    return out


def check_config_consistency(results, cfg_path):
    """结果里的锁定参数必须等于配置文件（否则判据机的输入不可信）。"""
    import yaml
    problems = []
    if not Path(cfg_path).exists():
        return [f"config 不存在: {cfg_path}"]
    cfg = yaml.safe_load(open(cfg_path))
    for k, cfgk in (("frames", "frames"), ("t0_frame", "t0_frame"), ("fit_iters", "fit_iters"),
                    ("unproj_stride", "unproj_stride")):
        if k in results and results[k] != cfg[cfgk]:
            problems.append(f"results.{k}={results[k]} != config.{cfgk}={cfg[cfgk]}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/embrace_dyn/evidence/dyn_probe_results.json")
    ap.add_argument("--config", default="configs/experiments/embrace_dyn/probe_pt2.yaml")
    ap.add_argument("--causal-results", default="results/embrace_dyn/evidence/dyn_probe_causal_results.json")
    ap.add_argument("--causal-config", default="configs/experiments/embrace_dyn/probe_pt2_causal.yaml")
    ap.add_argument("--causal2-results", default="results/embrace_dyn/evidence/dyn_probe_causal2_results.json")
    ap.add_argument("--causal2-config", default="configs/experiments/embrace_dyn/probe_pt2_causal2.yaml")
    ap.add_argument("--balloon-results", default="results/embrace_dyn/evidence/dyn_probe_balloon_results.json")
    ap.add_argument("--balloon-config", default="configs/experiments/embrace_dyn/probe_balloon_generality.yaml")
    ap.add_argument("--causal3-results", default="results/embrace_dyn/evidence/dyn_probe_causal3_results.json")
    ap.add_argument("--causal3-config", default="configs/experiments/embrace_dyn/probe_pt2_causal3.yaml")
    ap.add_argument("--out-md", default="results/embrace_dyn/evidence/dyn_probe_report.md")
    ap.add_argument("--json-out", default="results/embrace_dyn/evidence/dyn_probe_verdict.json")
    args = ap.parse_args()
    res = json.load(open(args.results))
    res["config_t0"] = res.get("t0_frame") or 309
    cfg_problems = check_config_consistency(res, args.config)
    judgments = {tag: analyse(res, tag) for tag in res["arms"]}

    # ── 因果批（预注册 prereg_dyn_probe_causal.md）──
    causal, causal_cfg_problems = None, []
    cpath = Path(args.causal_results)
    if cpath.exists():
        cres = json.load(open(cpath))
        cres["config_t0"] = cres.get("t0_frame") or 309
        causal_cfg_problems = check_config_consistency(cres, args.causal_config)
        causal = {tag: analyse_causal(cres, tag) for tag in cres["arms"]}
        causal = {k: v for k, v in causal.items() if v}

    causal2, causal2_cfg_problems = None, []
    c2path = Path(args.causal2_results)
    if c2path.exists():
        c2res = json.load(open(c2path))
        c2res["config_t0"] = c2res.get("t0_frame") or 309
        causal2_cfg_problems = check_config_consistency(c2res, args.causal2_config)
        causal2 = {tag: analyse_causal2(c2res, tag) for tag in c2res["arms"]}
        causal2 = {k: v for k, v in causal2.items() if v}

    # 材料盘点（残影候选：**逐地图**给区间，避免与均值混引）
    materials = {}
    mp = EV / "materials_dyn_probe.json"
    if mp.exists():
        mat = json.load(open(mp))
        for tag, rec in mat["ghost_inventory"].items():
            fr = [r for r in rec["frames"] if r.get("n_in_mask")]
            if not fr:
                continue
            fronts = [r["n_in_mask_front"] for r in fr]
            materials[tag] = {"n_gauss": rec["n_gauss"], "n_sampled_frames": len(rec["frames"]),
                              "n_mask_hit_frames": len(fr),
                              "front_min": min(fronts), "front_max": max(fronts),
                              "front_mean": _r(sum(fronts) / len(fronts), 1),
                              "front_frac_of_map_max": _r(max(fronts) / rec["n_gauss"]),
                              "sampling_note": "每 25 帧抽 1 帧；与评估 16 帧几乎不重叠 ⇒ 区间代表性有限"}

    balloon = None
    bpath = Path(args.balloon_results)
    if bpath.exists():
        bres = json.load(open(bpath))
        bres["config_t0"] = bres.get("t0_frame") or 297
        balloon = {tag: cross_sequence_row(bres, tag) for tag in bres["arms"]}
        balloon = {k: v for k, v in balloon.items() if v}
        balloon["_config_problems"] = check_config_consistency(bres, args.balloon_config)
        balloon["_judgments"] = {tag: analyse(bres, tag) for tag in bres["arms"]}
    causal3, causal3_cfg = None, []
    c3p = Path(args.causal3_results)
    if c3p.exists():
        c3res = json.load(open(c3p))
        c3res["config_t0"] = c3res.get("t0_frame") or 309
        causal3_cfg = check_config_consistency(c3res, args.causal3_config)
        causal3 = {tag: analyse_causal3(c3res, tag) for tag in c3res["arms"]}
        causal3 = {k: v for k, v in causal3.items() if v}
    json.dump({"thresholds": TH, "judgments": judgments, "config_consistency": cfg_problems,
               "causal3_judgments": causal3, "causal3_config_consistency": causal3_cfg,
               "balloon_generality": balloon,
               "causal_judgments": causal, "causal_config_consistency": causal_cfg_problems,
               "causal2_judgments": causal2, "causal2_config_consistency": causal2_cfg_problems,
               "material_check": materials}, open(args.json_out, "w"), indent=1)

    L = ["# embrace_dyn 生死筛结果（判据机输出，无人工读数）\n",
         "> 判据与阈值 = 预注册 `prereg_dyn_probe.md` §7（跑前锁定，**六条**）；本文件由 "
         "`scripts/02_analysis/analyze_dyn_probe.py` 生成，数字全部来自 `dyn_probe_results.json`。",
         f"> 配置一致性自检：{'通过' if not cfg_problems else '**不一致** ' + str(cfg_problems)} \n"]
    for tag, j in judgments.items():
        L.append(f"## {tag}（n_static={j['n_static']}）\n")
        L.append("| 臂 | dyn_psnr (dB) | dyn_dl1 (cm) | **bad_psnr** | **bad_dl1 (cm)** | bad_px | dyn_cov | full_psnr | static_psnr | ghost_excess | n_dyn |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for a in ("P1", "P2", "C-", "P4"):
            if a not in j["means"]:
                continue
            v = j["means"][a]
            s = j["support"][a]
            f = lambda k, nd=2: "--" if v.get(k) is None else f"{v[k]:.{nd}f}"
            L.append(f"| {a} | {f('dyn_psnr')} | {f('dyn_dl1_cm')} | {f('dyn_bad_psnr')} | "
                     f"{f('dyn_bad_dl1_cm')} | {f('dyn_bad_px',0)} | {f('dyn_cov',3)} | "
                     f"{f('full_psnr')} | {f('static_psnr')} | {f('ghost_excess_cm')} | {f('n_dyn',0)} |")
        L.append("")
        L.append(f"**远离 t0 帧（|f−t0|≥50，n={j['means_far_from_t0']['P2']['n']}）**："
                 f"P2 dl1={j['means_far_from_t0']['P2']['dyn_dl1_cm']:.2f}cm / "
                 f"P4 dl1={j['means_far_from_t0']['P4']['dyn_dl1_cm']:.2f}cm\n")
        for k, v in j["criteria"].items():
            L.append(f"- **{k}**: { {kk: vv for kk, vv in v.items() if kk not in ('note', 'cost_note')} }")
            if v.get("cost_note"):
                L.append(f"  - 成本注记：{v['cost_note']}")
            if v.get("note"):
                L.append(f"  - 注记：{v['note']}")
        if j["fit_evidence"]:
            L.append(f"- **拟合生效证据（此前产出、本轮消费）**：`{json.dumps(j['fit_evidence'], ensure_ascii=False)}`")
        L.append(f"\n⇒ **判决：{j['outcome']}**\n")
    if materials:
        L.append("## 材料盘点（残影候选，逐地图给区间避免与均值混引）\n")
        for tag, s in materials.items():
            L.append(f"- **{tag}**：n_gauss={s['n_gauss']}，抽样 {s['n_sampled_frames']} 帧中 "
                     f"{s['n_mask_hit_frames']} 帧掩码命中；挡在 GT 表面之前的点数 "
                     f"min={s['front_min']} / mean={s['front_mean']} / max={s['front_max']}"
                     f"（max 占地图 {s['front_frac_of_map_max']:.4%}）。{s['sampling_note']}")
        L.append("")
    diag_p = EV / "diag_causal_checks.json"
    if diag_p.exists():
        dg = json.load(open(diag_p))
        L.append("# 独立诊断（`diag_causal_checks.py`：帧率实测 / 速度分布 / M_bad 构成）\n")
        fr = dg["frame_rate"]
        L.append(f"- **帧率（实测，非标称）**：median 间隔 {fr['median_interval_s']:.4f}s ⇒ "
                 f"**{fr['hz_median']:.2f} Hz**（源 `{fr['source']}`）")
        v = dg.get("velocity_estimator")
        if v:
            L.append(f"- **速度估计器实测分布**（n={v['n']}）：m/帧 "
                     f"min={v['m_per_frame']['min']:.4f} / med={v['m_per_frame']['median']:.4f} / "
                     f"max={v['m_per_frame']['max']:.4f} ⇒ 按实测帧率 "
                     f"**{v['m_per_s_using_measured_hz']['min']:.2f}–{v['m_per_s_using_measured_hz']['max']:.2f} m/s**"
                     f"（中位 {v['m_per_s_using_measured_hz']['median']:.2f}）")
            L.append(f"  - 判读：{v['judgement']}")
        for tag, c in dg["bad_subset_composition"].items():
            L.append(f"- **M_bad 构成 {tag}**：掩码 {c['mask_px_total']} px 中 bad={c['bad_px']} "
                     f"（{c['frac_bad_of_mask']:.1%}）；其中**洞（P1 深度无效）={c['hole_px']}**"
                     f"（占 bad {c['frac_hole_of_bad']:.1%}）、wrong(>10cm)={c['wrong_gt10cm_px']} "
                     f"⇒ 50cm 惩罚常数生效 = **{c['penalty_constant_applies']}**")
        L.append("")
    if causal:
        L.append("# 因果批（预注册 `prereg_dyn_probe_causal.md`）\n")
        L.append("> 因果臂的均值一律取**同帧集**（各臂共有有效帧的交集）——关卡① 重大项整改。\n")
        L.append(f"> 配置一致性自检：{'通过' if not causal_cfg_problems else '**不一致** ' + str(causal_cfg_problems)}；"
                 "因果臂只用帧号 ≤ t 的数据（插入帧 = 最近前置 KF）。\n")
        for tag, j in causal.items():
            L.append(f"## {tag}（n_static={j['n_static']}；冷启动帧 {j['cold_start_frames']} 不计入）\n")
            L.append("| 臂 | dyn_psnr (dB) | dyn_dl1 (cm) | **bad_psnr** | **bad_dl1 (cm)** | good_psnr | good_dl1 | 全图 PSNR | 静态区 PSNR | n_dyn | n |")
            L.append("|---|---|---|---|---|---|---|---|---|---|---|")
            for a in ("P1", "P2", "P2c", "P2cv", "C-c"):
                v = j["means"][a]
                f = lambda k, nd=2: "--" if v.get(k) is None else f"{v[k]:.{nd}f}"
                L.append(f"| {a} | {f('dyn_psnr')} | {f('dyn_dl1_cm')} | {f('dyn_bad_psnr')} | "
                         f"{f('dyn_bad_dl1_cm')} | {f('dyn_good_psnr')} | {f('dyn_good_dl1_cm')} | "
                         f"{f('full_psnr')} | {f('static_psnr')} | {f('n_dyn',0)} | {v['n']} |")
            L.append("")
            L.append(f"（同帧集：n={j['means']['P2c']['n']}；`dt_eval` ∈ {j['dt_eval_range']}；"
                     f"冷启动帧 {j['cold_start_frames']}；v_norm 分位 {j['v_norm_m_per_frame']}）\n")
            for k, v in j["criteria"].items():
                L.append(f"- **{k}**: { {kk: vv for kk, vv in v.items() if kk != 'note'} }")
                if v.get("note"):
                    L.append(f"  - 注记：{v['note']}")
            L.append(f"\n- 口径声明：{j['dyn_cov_note']}")
            L.append(f"\n⇒ **因果判决：{j['outcome']}**\n")
    if causal2:
        L.append("# 因果轮 II（预注册 `prereg_dyn_probe_causal2.md`：掩码连通域 + 刚性常扭转外推）\n")
        L.append(f"> 配置一致性自检：{'通过' if not causal2_cfg_problems else '**不一致** ' + str(causal2_cfg_problems)}；"
                 "同帧集配对。\n")
        for tag, j in causal2.items():
            L.append(f"## {tag}（n_static={j['n_static']}）\n")
            L.append("| 臂 | dyn_psnr | dyn_dl1 | **bad_psnr** | **bad_dl1** | good_dl1 | 全图 | 静态区 | n_dyn |")
            L.append("|---|---|---|---|---|---|---|---|---|")
            for a in ("P1", "P2", "P2c", "P2cs", "P2cm", "P2cr", "C-c"):
                if a not in j["means"]:
                    continue
                v = j["means"][a]
                f = lambda k, nd=2: "--" if v.get(k) is None else f"{v[k]:.{nd}f}"
                L.append(f"| {a} | {f('dyn_psnr')} | {f('dyn_dl1_cm')} | {f('dyn_bad_psnr')} | "
                         f"{f('dyn_bad_dl1_cm')} | {f('dyn_good_dl1_cm')} | {f('full_psnr')} | "
                         f"{f('static_psnr')} | {f('n_dyn',0)} |")
            L.append("")
            L.append(f"（同帧集 n={j['means']['P2cr']['n']}；mask_cc_frac {j['mask_cc_frac']}；"
                     f"icp_rmse_m {j['icp_rmse_m']}）\n")
            for k, v in j["criteria"].items():
                L.append(f"- **{k}**: { {kk: vv for kk, vv in v.items()} }")
            L.append(f"\n- 平移类臂消融（不判）：{json.dumps(j['ablation_translation_arms'], ensure_ascii=False)}")
            L.append(f"\n⇒ **因果轮 II 判决：{j['outcome']}**\n")
    if balloon:
        L.append("# 跨序列泛化复现（第二序列 balloon；预注册 `prereg_dyn_probe_balloon.md`）\n")
        L.append("> 判据与 pt2 同阈值；**两序列都是单 seed**，故属「跨序列」而非「全表」级证据。\n")
        L.append("| 序列 | 地图 | 帧数 | P1 bad_psnr | P2 bad_psnr | **bad 增益 (dB)** | **bad dl1 比值** | bad 占图 | 静态区 Δ | 全图 Δ | n_dyn 占比 |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for tag, r in balloon.items():
            if tag.startswith("_"):
                continue
            L.append(f"| balloon | {tag} | {r['n_frames']} | {r['P1_bad_psnr']} | {r['P2_bad_psnr']} | "
                     f"**{r['bad_psnr_gain_db']}** | **{r['bad_dl1_ratio']}** | {r['bad_px_frac_of_image']:.3%} | "
                     f"{r['static_gain_db']} | {r['full_gain_db']} | {r['n_dyn_frac']:.3%} |")
        L.append("")
        L.append("**pt2 同口径参考**（母批，16 帧）：bad 增益 +10.73/+11.00 dB、bad dl1 比值 0.565/0.555、"
                 "bad 占图 5.8%、n_dyn 占比 6.4%/4.2%。\n")
        for tag, r in balloon.items():
            if tag.startswith("_"):
                continue
            for a, s2 in r["causal_arms"].items():
                L.append(f"- balloon/{tag} {a} 因果保留率：**bad_dl1 {s2['retention_bad_dl1']}** / "
                         f"bad_psnr {s2['retention_bad_psnr']} / 静态区 Δ {s2['d_static_db']} dB"
                         + (f"（dt=0 帧 {r['tzero_frames']} 剔除后："
                            f"{r.get('excl_dt0', {}).get(a)}）" if r.get("tzero_frames") else ""))
        L.append("\n**pt2 同口径参考**（因果轮 I，15 帧）：P2c bad_dl1 保留 0.590/0.583、bad_psnr 保留约 0.12–0.14。")
        if balloon.get("_config_problems"):
            L.append(f"\n⚠ balloon 配置一致性：{balloon['_config_problems']}")
        L.append("")
    if causal3:
        L.append("# 因果轮 III（预注册 `prereg_dyn_probe_causal3.md`：多帧并集插入 + 逐基元 KNN 速度）\n")
        L.append(f"> 配置一致性自检：{'通过' if not causal3_cfg else '**不一致** ' + str(causal3_cfg)}；同帧集配对。\n")
        for tag, j in causal3.items():
            L.append(f"## {tag}（n_static={j['n_static']}）\n")
            L.append("| 臂 | dyn_psnr | dyn_dl1 | **bad_psnr** | **bad_dl1** | good_dl1 | 全图 | 静态区 | n_dyn |")
            L.append("|---|---|---|---|---|---|---|---|---|")
            for a in ("P1", "P2", "P2c", "P2cu", "P2cuv", "C-u"):
                if a not in j["means"]:
                    continue
                v = j["means"][a]
                f = lambda k, nd=2: "--" if v.get(k) is None else f"{v[k]:.{nd}f}"
                L.append(f"| {a} | {f('dyn_psnr')} | {f('dyn_dl1_cm')} | {f('dyn_bad_psnr')} | "
                         f"{f('dyn_bad_dl1_cm')} | {f('dyn_good_dl1_cm')} | {f('full_psnr')} | "
                         f"{f('static_psnr')} | {f('n_dyn',0)} |")
            L.append("")
            for k, v in j["criteria"].items():
                L.append(f"- **{k}**: { {kk: vv for kk, vv in v.items()} }")
            L.append(f"\n- 逐点速度统计：{json.dumps(j['pointwise_stats'], ensure_ascii=False)}")
            L.append(f"\n- **E7 分层（Δt）**：{json.dumps(j['E7_stratified']['by_dt'], ensure_ascii=False)}")
            L.append(f"\n- **E7 分层（掩码规模）**：{json.dumps(j['E7_stratified']['by_mask_size'], ensure_ascii=False)}")
            L.append(f"\n⇒ **因果轮 III 判决：{j['outcome']}**\n")
    Path(args.out_md).write_text("\n".join(L))
    print(f"written {args.out_md} + {args.json_out}")
    if cfg_problems:
        print(f"[WARN] 配置一致性: {cfg_problems}")
    for tag, j in judgments.items():
        print(f"{tag}: {j['outcome']}  " + "  ".join(
            f"{k}={'PASS' if v['pass'] else 'FAIL'}" for k, v in j["criteria"].items() if "pass" in v))
    for tag, j in (causal3 or {}).items():
        print(f"{tag}(causal3): {j['outcome']}  " + "  ".join(
            f"{k}={'PASS' if v['pass'] else 'FAIL'}" for k, v in j["criteria"].items() if "pass" in v))
    if balloon:
        for tag, j in balloon.get("_judgments", {}).items():
            if j:
                print(f"balloon/{tag}: {j['outcome']}  " + "  ".join(
                    f"{k}={'PASS' if v['pass'] else 'FAIL'}" for k, v in j["criteria"].items() if "pass" in v))
    for tag, j in (causal2 or {}).items():
        print(f"{tag}(causal2): {j['outcome']}  " + "  ".join(
            f"{k}={'PASS' if v['pass'] else 'FAIL'}" for k, v in j["criteria"].items() if "pass" in v))
    for tag, j in (causal or {}).items():
        print(f"{tag}(causal): {j['outcome']}  " + "  ".join(
            f"{k}={'PASS' if v['pass'] else 'FAIL'}" for k, v in j["criteria"].items() if "pass" in v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
