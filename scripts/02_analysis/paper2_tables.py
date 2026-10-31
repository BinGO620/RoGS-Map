#!/usr/bin/env python
"""paper2_tables.py — 论文 2 表格机器生成器（Markdown / JSON / **CVM LaTeX**）。

数据源（唯一口径，全部 R33 同批同码）：
  ATE:   results/paper2_fulltable/r33_rebase_{arm}_{seq}_seed{k}/tables/tracking_raw.csv
         col 8  `ate_rmse_cm`（全帧，主表口径）
         col 14 `keyframe_ate_rmse_cm`（关键帧，附表口径）
  效率:  同 run 的 tables/efficiency_raw.csv（online_fps / online_num_gaussians /
         online_peak_gpu_memory_gb）
  渲染:  results/paper2_fulltable/render_compare/*/render_metrics.json
         （离线渲染协议，含 mean_psnr/ssim/lpips/depth_l1；若该 run 已跑静态指标批
           另含 mean_static_psnr/ssim/coverage/ghost_excess_depth_l1_cm）
  静态:  优先运行期 P-A（同 run 的 tables/mapping_raw.csv 的 mask_type=='static' 行）
  Sim3:  同 run 的 plot/trj_full_final.json（自带 trj_est + trj_gt）——
         与 `utils/eval_utils.py:96` 同协议（evo trajectory.align_trajectory；
         主线为 RGB-D ⇒ 主表 ATE 用 SE3 对齐，本文件额外给 Sim3 尺度与 Sim3-ATE）

输出：
  results/paper2_fulltable/evidence/tables_paper2_preview.md（人读）
  results/paper2_fulltable/evidence/tables_paper2_preview.json（机读）
  results/paper2_fulltable/evidence/latex/tab*.tex（CVM 模板风格，见 --latex-dir）

口径纪律（DISCIPLINE #12）：
  - col8/col14 **分文件、分列、分标题声明**，禁止混引；
  - 渲染 / 静态 / Sim3 三类数字均标注协议来源与帧数；
  - 本脚本**不重算** ATE/渲染/静态（只读既有产物），Sim3 为唯一新增计算，
    并以"自算 SE3-ATE == tracking_raw col8"作阳性对照自检（见 --selfcheck）。

用法：
  /data/conda_envs/monogs-ours/bin/python scripts/02_analysis/paper2_tables.py
  ... [--latex-dir DIR] [--no-latex] [--selfcheck]
"""
import argparse
import csv
import json
import os
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
os.chdir(REPO)

SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3", "person_tracking", "person_tracking2"]
ARMS = ["baseline", "swbaonly", "final", "gate"]
ARMS_LABEL = {"baseline": "baseline", "swbaonly": "+SWBA", "final": "+SWBA+LC", "gate": "gate (deployed)"}
ARMS_TEX = {"baseline": "Base (MonoGS)", "swbaonly": "+SWBA", "final": "+SWBA+LC", "gate": "+SWBA+LC+Gate"}
# 主表臂（2026-10-10，方案 A）：论文的系统 = Base 栈（论文 1 方法沿用）；+Gate = 部署形态。
# 论文 2 的系统 = 前作栈（Base）本身（§3.2：「the base stack ... used as-is」）——系统表
# 只报**这一列**（背景指标，非贡献）。论文 2 相对前作**没有新系统配置**：deployed 形态
# （+SWBA+LC+Gate）含前作 SWBA/LC 与本门，是多组件复合、非单变量对照，且 SWBA 已被
# D2-027 排除 ⇒ **不进主表**。完整四梯全部保留在附表 Table~\ref{tab:ladder}（供审计；
# 数字仍由本生成器机写、数据层仍按 4 臂构建）。
# （G2-M1 修订 2026-10-10：原两列 "Base / +Gate (deployed)" 把含 SWBA 的复合臂标成
#  "只加 gate"，题注不实 ⇒ 降为单列 Base。）
MAIN_ARMS = ["baseline"]
MAIN_ARMS_TEX = {"baseline": "Base (prior stack)"}
# 单栏窄表用的短列头（tab1/tab2r 为单栏 `table`，长标签会 overfull）
MAIN_ARMS_TEX_SHORT = {"baseline": "Base"}
SEQ_TEX = {"balloon": "balloon", "balloon2": "balloon2", "crowd": "crowd", "crowd2": "crowd2",
           "crowd3": "crowd3", "person_tracking": "person\\_tracking",
           "person_tracking2": "person\\_tracking2"}
PT_SEQS = ["person_tracking", "person_tracking2"]
SEEDS = (0, 1, 2)
ROOT = Path("results/paper2_fulltable")
GEN = "scripts/02_analysis/paper2_tables.py"
PROV = ("R33 same-batch (baseline/swbaonly/final/gate x 7 Bonn seqs x 3 seeds, "
        "all runs 2026-09-16, identical code)")


# ────────────────────────── 读取层 ──────────────────────────

def _csv_rows(p):
    if not Path(p).exists():
        return []
    return list(csv.DictReader(open(p)))


def _f(v):
    try:
        return float(v) if v not in (None, "", "N/A", "nan", "MISSING") else None
    except (TypeError, ValueError):
        return None


def run_dir_of(arm, seq, seed):
    """run 的时间戳目录（tables/ 的上一级）。"""
    exp = ROOT / f"r33_rebase_{arm}_{seq}_seed{seed}" / "datasets_bonn" / f"r33_rebase_{arm}_{seq}"
    hits = sorted((exp / f"seed_{seed}").glob("*/tables/tracking_raw.csv"))
    return hits[-1].parent.parent if hits else None


def ate_of(arm, seq, seed, col="ate_rmse_cm"):
    """tracking_raw.csv 的最后一行（col 8 全帧 / col 14 关键帧）。"""
    p = ROOT / f"r33_rebase_{arm}_{seq}_seed{seed}" / "tables" / "tracking_raw.csv"
    rows = [r for r in _csv_rows(p) if r.get("status") == "OK"]
    if not rows:
        return None
    return _f(rows[-1].get(col))


def efficiency_of(arm, seq, seed):
    p = ROOT / f"r33_rebase_{arm}_{seq}_seed{seed}" / "tables" / "efficiency_raw.csv"
    rows = [r for r in _csv_rows(p) if r.get("status") == "OK"]
    if not rows:
        return None
    r = rows[-1]
    return {
        "fps": _f(r.get("online_fps")),
        "n_gauss": _f(r.get("online_num_gaussians")),
        "peak_mem_gb": _f(r.get("online_peak_gpu_memory_gb")),
        "n_frames": _f(r.get("num_frames")),
    }


def sim3_of(arm, seq, seed):
    """同批 Sim3 尺度 + Sim3 对齐 ATE（协议同 utils/eval_utils.py:96 的 evo 路径）。

    trj_full_final.json 自带 trj_est/trj_gt（逐帧配对）⇒ 直接用 evo 对齐。
    返回 None 表示轨迹文件缺失/长度不符。
    """
    p = ROOT / f"r33_rebase_{arm}_{seq}_seed{seed}" / "datasets_bonn" / f"r33_rebase_{arm}_{seq}"
    hits = sorted((p / f"seed_{seed}").glob("*/plot/trj_full_final.json"))
    if not hits:
        return None
    try:
        import numpy as np
        from evo.core import metrics, trajectory
        from evo.core.trajectory import PosePath3D
    except ImportError:
        return None
    d = json.load(open(hits[-1]))
    est, gt = d.get("trj_est"), d.get("trj_gt")
    if not est or not gt or len(est) != len(gt) or len(est) < 3:
        return None
    try:
        te = PosePath3D(poses_se3=[np.asarray(m, dtype=float) for m in est])
        tr = PosePath3D(poses_se3=[np.asarray(m, dtype=float) for m in gt])
        # evo: align_trajectory(..., return_parameters=True) -> (aligned, R, t, scale)
        aligned, _r, _t, scale = trajectory.align_trajectory(
            te, tr, correct_scale=True, return_parameters=True)
        ape = metrics.APE(metrics.PoseRelation.translation_part)
        ape.process_data((tr, aligned))
        ape_se3 = metrics.APE(metrics.PoseRelation.translation_part)
        ape_se3.process_data((tr, trajectory.align_trajectory(te, tr, correct_scale=False)))
        return {
            "sim3_scale": float(scale),
            "ate_sim3_cm": float(ape.get_statistic(metrics.StatisticsType.rmse)) * 100.0,
            # 阳性对照用：应与 tracking_raw col8（全帧 SE3 ATE）逐位吻合
            "ate_se3_cm": float(ape_se3.get_statistic(metrics.StatisticsType.rmse)) * 100.0,
            "n_poses": len(est),
        }
    except Exception as e:  # noqa: BLE001 - 单 run 失败不应中断整表
        print(f"  [warn] sim3 {arm}/{seq}/seed{seed}: {type(e).__name__}: {e}", flush=True)
        return None


def _find_render(sub, tag):
    base = ROOT / sub
    hits = sorted(base.glob(f"{tag}_*/render_metrics.json")) + sorted(base.glob(f"{tag}/render_metrics.json"))
    return json.load(open(hits[-1])) if hits else None


def runtime_static_of(arm, seq, seed):
    """运行期 P-A 静态/残影指标（最强口径：~88 帧 @every5，gtmc 冻结掩码）。

    来源 = 该 run 的 `tables/mapping_raw.csv` 中 `mask_type=='static'` 行
    （与主表同批同码；仅在序列有 dynamic_mask_gtmc 时产出）。
    """
    p = ROOT / f"r33_rebase_{arm}_{seq}_seed{seed}" / "tables" / "mapping_raw.csv"
    for r in _csv_rows(p):
        if r.get("mask_type") != "static":
            continue
        if _f(r.get("static_psnr")) is None:
            return None
        return {
            "mean_static_psnr": _f(r.get("static_psnr")),
            "mean_static_ssim": _f(r.get("static_ssim")),
            "mean_static_lpips": _f(r.get("static_lpips")),
            "mean_static_coverage": _f(r.get("static_coverage")),
            "mean_static_depth_l1_pen_cm": _f(r.get("static_depth_l1_pen_cm")),
            "mean_ghost_excess_depth_l1_cm": _f(r.get("static_ghost_excess_depth_l1_cm")),
            "mean_ghost_excess_psnr_db": _f(r.get("static_ghost_excess_psnr_db")),
            "mean_freshvac_ghost_excess_depth_l1_cm": _f(r.get("static_freshvac_ghost_excess_depth_l1_cm")),
            "mask_source": "runtime_pa:" + str(r.get("static_mask_subdir")),
            "static_protocol": "runtime P-A (~88 frames @5, frozen gtmc)",
        }
    return None


def render_of(arm, seq, seed):
    """每 seed 合并来源，**避免协议混算**：
    - 渲染主源 = `render_compare/{tag}_*`（批协议 8 帧）
    - 静态字段优先级（2026-09-24 D1-014 F1 整改）：**canonical 离线
      `render_compare_static_canon/{tag}*`（6 帧，D1-007 重算口径）** >
      主源自带静态（批协议 8 帧）> 早期 `render_compare_static/{tag}*`（旧掩码，仅回退）。
      运行期 P-A（gtmc 冻结掩码）已废弃为静态源（D1-004/D1-006：掩码召回 0.10–0.39，
      D1-006 已删该掩码目录）——`runtime_static_of` 保留但不再参与优先级。
    """
    tag = f"r33_rebase_{arm}_{seq}_seed{seed}"
    main = _find_render("render_compare", tag)
    alt = _find_render("render_compare_static_canon", tag)   # D1-007 canonical 重算
    legacy_alt = _find_render("render_compare_static", tag)  # 旧掩码早期信号，仅回退
    merged = dict(main) if main else (dict(alt) if alt else None)
    if merged is None and alt is None and legacy_alt is None:
        return None
    if merged is None:
        merged = {}
    static_keys = ("mean_static_psnr", "mean_static_ssim", "mean_static_lpips",
                   "mean_static_coverage", "mean_static_depth_l1_pen_cm",
                   "mean_static_support_px", "mean_ghost_excess_depth_l1_cm",
                   "mean_ghost_excess_psnr_db", "mean_freshvac_ghost_excess_depth_l1_cm",
                   "mean_vacated_support_px")
    if alt is not None and alt.get("mean_static_psnr") is not None:
        src = alt          # canonical 优先
    elif merged.get("mean_static_psnr") is not None:
        src = None  # 主源已是批协议静态，不降级
    else:
        src = legacy_alt   # 旧掩码回退（标注历史口径）
    if src is not None:
        for k in static_keys:
            if src.get(k) is not None:
                merged[k] = src[k]
        merged["mask_source"] = src.get("mask_source")
        if src is alt:
            merged["static_source"] = src.get("static_protocol") or (
                "offline canon 6f: " + str(src.get("mask_source")))
        elif src is legacy_alt:
            merged["static_source"] = "LEGACY(旧掩码) offline 6f: " + str(src.get("mask_source"))
    return merged


# ────────────────────────── 组装层 ──────────────────────────

def build_table():
    table = {}
    for arm in ARMS:
        for seq in SEQS:
            ate_v = [ate_of(arm, seq, k) for k in SEEDS]
            kf_v = [ate_of(arm, seq, k, col="keyframe_ate_rmse_cm") for k in SEEDS]
            ren = [render_of(arm, seq, k) for k in SEEDS]
            eff = [efficiency_of(arm, seq, k) for k in SEEDS]
            s3 = [sim3_of(arm, seq, k) for k in SEEDS]
            ate_ok = [v for v in ate_v if v is not None]
            kf_ok = [v for v in kf_v if v is not None]

            def rmean(key):
                vs = [r[key] for r in ren if r and r.get(key) is not None]
                return round(statistics.mean(vs), 4) if vs else None

            def emean(key):
                vs = [e[key] for e in eff if e and e.get(key) is not None]
                return round(statistics.mean(vs), 4) if vs else None

            s3v = [x["sim3_scale"] for x in s3 if x]
            table[(arm, seq)] = {
                "ate_mean": round(statistics.mean(ate_ok), 4) if ate_ok else None,
                "ate_sd": round(statistics.stdev(ate_ok), 4) if len(ate_ok) > 1 else None,
                "ate_n": len(ate_ok),
                "ate_seeds": [None if v is None else round(v, 4) for v in ate_v],
                "kf_ate_mean": round(statistics.mean(kf_ok), 4) if kf_ok else None,
                "kf_ate_sd": round(statistics.stdev(kf_ok), 4) if len(kf_ok) > 1 else None,
                "kf_ate_seeds": [None if v is None else round(v, 4) for v in kf_v],
                "psnr": rmean("mean_psnr"),
                "ssim": rmean("mean_ssim"),
                "lpips": rmean("mean_lpips"),
                "depth_l1": rmean("mean_depth_l1_cm"),
                "static_psnr": rmean("mean_static_psnr"),
                "static_ssim": rmean("mean_static_ssim"),
                "static_cov": rmean("mean_static_coverage"),
                "ghost_excess": rmean("mean_ghost_excess_depth_l1_cm"),
                "render_n": sum(1 for r in ren if r),
                "mask_source": next((r.get("mask_source") for r in ren if r and r.get("mask_source")), None),
                "n_gauss": emean("n_gauss"),
                "peak_mem_gb": max([e["peak_mem_gb"] for e in eff if e and e.get("peak_mem_gb")] or [None]) if any(e and e.get("peak_mem_gb") for e in eff) else None,
                # 关卡② 抓到的真 bug（2026-09-19）：round(x) 到整数会把 ~0.3-0.5 的 fps 压成 0，
                # 而下游用 `if fps_med` 真值过滤又把 0 当缺失剔除 ⇒ 该列退化为 "1.000" 与 "--"。
                # 两处都已修：这里保留 3 位小数，下游改成 `is not None`。
                "fps_med": round(statistics.median([e["fps"] for e in eff if e and e.get("fps")]), 3) if any(e and e.get("fps") for e in eff) else None,
                "sim3_scale": round(statistics.mean(s3v), 5) if s3v else None,
                "sim3_scale_seeds": [None if x is None else round(x["sim3_scale"], 5) for x in s3],
                "sim3_ate_seeds": [None if x is None else round(x["ate_sim3_cm"], 4) for x in s3],
                "sim3_ate_se3_seeds": [None if x is None else round(x["ate_se3_cm"], 4) for x in s3],
                "sim3_n": len(s3v),
            }
    return table


# ────────────────────────── Markdown / JSON 输出 ──────────────────────────

def write_markdown(table):
    L = []
    L.append("# 论文 2 表格（ATE + 渲染 + 静态 + 效率）— 机器生成（2026-09-19）\n")
    L.append(f"> 生成器 `{GEN}`；来源 = **{PROV}**。")
    L.append("> ATE=col8 全帧 3-seed mean±sd（主表口径）；Tab.5 为 col14 关键帧口径（**禁止混引**）；")
    L.append("> 渲染=离线协议 8 帧采样（与 run 内 eval 同源函数）。")
    L.append("> **静态列口径优先级**：① **运行期 P-A**（`mapping_raw.csv` 的 `mask_type=static` 行，")
    L.append("> ~88 帧 @every5，与主表同批同码）；② 离线 6 帧早期信号（其余序列回退）。**两源不混算**。")
    L.append("> Sim3 列 = 本生成器按 `utils/eval_utils.py:96` 同协议（evo align_trajectory）自算，")
    L.append("> 自检：自算 SE3-ATE 应等于 col8。数字入论文前须过**关卡②**。\n")

    def hdr(title, cols):
        L.append(f"## {title}\n")
        L.append("| " + " | ".join(cols) + " |")
        L.append("|---|" + "---|" * (len(cols) - 1))

    hdr("Tab.1 主表 — ATE（cm, col8 全帧, seed0-2）", ["seq"] + [ARMS_LABEL[a] for a in ARMS])
    for seq in SEQS:
        row = [seq]
        for a in ARMS:
            v = table[(a, seq)]
            row.append(f"{v['ate_mean']:.2f}±{v['ate_sd']:.2f}" if v["ate_mean"] is not None else "--")
        L.append("| " + " | ".join(row) + " |")
    L.append("")

    hdr("Tab.5 附表 — ATE（cm, col14 关键帧）。**与 Tab.1 不同口径，禁止混引**",
        ["seq"] + [ARMS_LABEL[a] for a in ARMS])
    for seq in SEQS:
        row = [seq]
        for a in ARMS:
            v = table[(a, seq)]
            row.append(f"{v['kf_ate_mean']:.2f}±{v['kf_ate_sd']:.2f}" if v["kf_ate_mean"] is not None else "--")
        L.append("| " + " | ".join(row) + " |")
    L.append("")

    hdr("Tab.2r 渲染 — 全图 PSNR / SSIM（离线协议）", ["seq"] + [ARMS_LABEL[a] for a in ARMS])
    for seq in SEQS:
        row = [seq]
        for a in ARMS:
            v = table[(a, seq)]
            row.append(f"{v['psnr']:.2f} / {v['ssim']:.3f}" if v["psnr"] is not None else "--")
        L.append("| " + " | ".join(row) + " |")
    L.append("")

    L.append("## Tab.3s 静态区分区指标（`M_static = valid-depth ∧ ¬dynamic`，冻结掩码）\n")
    L.append("| seq | arm | static PSNR | static SSIM | coverage | ghost_excess (cm) | 掩码源 |")
    L.append("|---|---|---|---|---|---|---|")
    for seq in SEQS:
        for a in ARMS:
            v = table[(a, seq)]
            if v["static_psnr"] is None:
                continue
            ge = "--" if v["ghost_excess"] is None else f"{v['ghost_excess']:.2f}"
            L.append(f"| {seq} | {ARMS_LABEL[a]} | {v['static_psnr']:.2f} | "
                     f"{v['static_ssim']:.3f} | {v['static_cov']:.3f} | {ge} | {v['mask_source']} |")
    L.append("")

    L.append("## Tab.4 效率（在线阶段；fps 受并发混杂，只作旁证）\n")
    L.append("| arm | 高斯数 mean（7 序列 × 3 seed） | 峰值显存 max (GB) | online_fps median |")
    L.append("|---|---|---|---|")
    for a in ARMS:
        g = [table[(a, s)]["n_gauss"] for s in SEQS if table[(a, s)]["n_gauss"] is not None]
        m = [table[(a, s)]["peak_mem_gb"] for s in SEQS if table[(a, s)]["peak_mem_gb"] is not None]
        f = [table[(a, s)]["fps_med"] for s in SEQS if table[(a, s)]["fps_med"] is not None]
        L.append(f"| {ARMS_LABEL[a]} | "
                 f"{('%.0f' % statistics.mean(g)) if g else '--'} | "
                 f"{('%.2f' % max(m)) if m else '--'} | "
                 f"{('%.3f' % statistics.median(f)) if f else '--'} |")
    L.append("")

    L.append("## Tab.2 pt 逐 seed（col8）+ 同批自算 Sim3\n")
    L.append("| seq | arm | seed0/1/2 ATE | Sim3 尺度 seed0/1/2 | Sim3-ATE seed0/1/2 |")
    L.append("|---|---|---|---|---|")
    for seq in PT_SEQS:
        for a in ARMS:
            v = table[(a, seq)]
            at = "/".join("--" if x is None else f"{x:.2f}" for x in v["ate_seeds"])
            sc = "/".join("--" if x is None else f"{x:.3f}" for x in v["sim3_scale_seeds"])
            sa = "/".join("--" if x is None else f"{x:.2f}" for x in v["sim3_ate_seeds"])
            L.append(f"| {seq} | {ARMS_LABEL[a]} | {at} | {sc} | {sa} |")
    L.append("")

    L.append("## 覆盖状态\n")
    for a in ARMS:
        n_ate = sum(1 for s in SEQS if table[(a, s)]["ate_mean"] is not None)
        n_ren = sum(1 for s in SEQS if table[(a, s)]["psnr"] is not None)
        n_st = sum(1 for s in SEQS if table[(a, s)]["static_psnr"] is not None)
        n_e = sum(1 for s in SEQS if table[(a, s)]["n_gauss"] is not None)
        L.append(f"- {ARMS_LABEL[a]}: ATE {n_ate}/7 | 渲染 {n_ren}/7 | 静态 {n_st}/7 | 效率 {n_e}/7")
    L.append("")
    out = ROOT / "evidence" / "tables_paper2_preview.md"
    out.write_text("\n".join(L))
    return out


def write_json(table):
    out = ROOT / "evidence" / "tables_paper2_preview.json"
    json.dump({f"{a}|{s}": v for (a, s), v in table.items()}, open(out, "w"), indent=1)
    return out


# ────────────────────────── LaTeX 输出（CVM 模板风格） ──────────────────────────

def tex_escape(s):
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
                 ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                 ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")):
        s = s.replace(a, b)
    return s


def _cell(v, nd=2, plusminus=True, sd=None):
    if v is None:
        return "--"
    if sd is not None:
        return f"{v:.{nd}f}$\\pm${sd:.{nd}f}" if plusminus else f"{v:.{nd}f}"
    return f"{v:.{nd}f}"


def _table(env, colspec, header, rows, caption, label, note=None, size=None):
    """三线表（booktabs）：\\toprule 表头 \\midrule 数据 \\bottomrule。

    2026-10-09 改版：由 \\hline/\\hline\\hline 密线风格改为 booktabs 三线（更清晰、去竖线），
    colspec 里的竖线 ``|`` 由调用方去除（emit 时统一 strip ``|``）。
    size：可选字号命令，包在 center 内、tabular 外（消 overfull）。
    """
    spec = colspec.replace("|", "")   # booktabs 不用竖线
    L = [f"% generated by {GEN} -- do not edit by hand",
         f"% provenance: {PROV}",
         "% 口径提醒：本表数字全部来自 results/ 既有产物；入论文前须过 slam-critic 关卡②",
         f"\\begin{{{env}}}", "\\begin{center}"]
    if size:
        L.append(size)
    L += [f"\\begin{{tabular}}{{{spec}}}", "\\toprule"]
    L.append(" & ".join(header) + " \\\\")
    L.append("\\midrule")
    for r in rows:
        L.append(" & ".join(r) + " \\\\")
    L.append("\\bottomrule")
    L.append("\\end{tabular}")
    L.append("\\end{center}")
    if note:
        L.append(f"\\caption{{{caption} {note}}}")
    else:
        L.append(f"\\caption{{{caption}}}")
    L.append(f"\\label{{{label}}}")
    L.append(f"\\end{{{env}}}")
    return "\n".join(L) + "\n"


def write_latex(table, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    written = []

    # Tab.1 系统表 ATE（col8）—— 论文 2 的系统 = 前作栈（Base）单列（G2-M1 修订）
    # 单配置 ⇒ 列头即指标名（非配置名）。
    rows = [[SEQ_TEX[s], _cell(table[MAIN_ARMS[0], s]["ate_mean"], 2,
                               sd=table[MAIN_ARMS[0], s]["ate_sd"])] for s in SEQS]
    written.append(("tab1_main.tex", _table(
        "table", "|l|c|",
        ["Sequence", "ATE (cm)"], rows,
        "Absolute trajectory error of the base stack (RMSE, cm, mean$\\pm$sd over 3 seeds; "
        "all-frames protocol, column \\texttt{ate\\_rmse\\_cm}).",
        "tab:main",
        "The system that grows the maps is the prior base stack reused as-is; this table "
        "reports its tracking as background, not a claim. Lower is better; single same-batch "
        "evaluation.")))

    # Tab.5 阶梯消融表（col8）—— 原主表四梯移出为审计用附表
    rows = [[SEQ_TEX[s]] + [_cell(table[(a, s)]["ate_mean"], 2, sd=table[(a, s)]["ate_sd"]) for a in ARMS]
            for s in SEQS]
    written.append(("tab5_ladder.tex", _table(
        "table*", "|l|" + "c|" * len(ARMS),
        ["Sequence"] + [ARMS_TEX[a] for a in ARMS], rows,
        "Component-ladder ablation of the prior stack (ATE RMSE, cm, mean$\\pm$sd over 3 "
        "seeds; all-frames protocol).",
        "tab:ladder",
        "Column two adds the prior stack's sliding-window photometric bundle adjustment "
        "(+SWBA), three an optional loop-closure step (+LC), four the static-confidence gate. "
        "The ladder is carried as an ablation, not a system we propose: its aggregate effect "
        "is a wash, the full stack degrades 5 of 7 sequences relative to Base, and the set of "
        "sequences under 5\\,cm is unchanged. Single same-batch evaluation.")))

    # Tab.2r 渲染 —— 全图三指标（PSNR / SSIM / LPIPS，CVM 渲染三件套）
    rows = []
    for s in SEQS:
        v = table[MAIN_ARMS[0], s]
        rows.append([
            SEQ_TEX[s],
            "--" if v["psnr"] is None else f"{v['psnr']:.2f}",
            "--" if v["ssim"] is None else f"{v['ssim']:.3f}",
            "--" if v["lpips"] is None else f"{v['lpips']:.3f}",
        ])
    written.append(("tab2r_render.tex", _table(
        "table", "|l|c|c|c|",
        ["Sequence", "PSNR (dB)", "SSIM", "LPIPS"], rows,
        "Full-image rendering quality of the prior stack, offline rendering protocol "
        "sampled away from the keyframe grid.",
        "tab:render",
        "This is the full-image protocol; partitioned static-region numbers are in "
        "Table~\\ref{tab:static}. LPIPS uses the standard AlexNet backbone; lower is better.")))

    # Tab.3s 静态区（7 序列 × 1 配置 = 7 行）—— 论文 2 的系统 = Base 单列
    # 掩码源列必须保留：本表跨序列**混用两种静态协议**（运行期 P-A vs 离线 seg_mask），
    # 去掉该列等于让读者以为全表同协议（关卡② 抓到的致命项，2026-09-19）。
    rows = []
    for s in SEQS:
        for a in MAIN_ARMS:
            v = table[(a, s)]
            if v["static_psnr"] is None:
                continue
            rows.append([SEQ_TEX[s], f"{v['static_psnr']:.2f}", f"{v['static_ssim']:.3f}",
                         "--" if v["ghost_excess"] is None else f"${v['ghost_excess']:.2f}$",
                         tex_escape(v["mask_source"] or "--")])
    written.append(("tab3s_static.tex", _table(
        "table*", "|l|c|c|c|l|",
        ["Sequence", "static PSNR", "static SSIM",
         "ghost excess (cm)", "mask source"], rows,
        "Partitioned metrics on the static support of the prior stack "
        "($M_{\\mathrm{static}} = $ valid GT depth $\\wedge$ $\\neg$dynamic, "
        "frozen method-independent masks). All rows use the same canonical static "
        "protocol: offline 6-frame rendering with the \\texttt{dynamic\\_mask} "
        "canonical masks (single-source masks, 84 runs).",
        "tab:static",
        "Ghost excess is the depth-L1 contrast between newly vacated regions and "
        "the static background; lower is better. A negative value means the newly "
        "vacated region renders slightly closer to the static background than the "
        "surrounding support does.",
        size="\\footnotesize\\renewcommand{\\arraystretch}{0.94}")))

    # Tab.4 效率（逐序列 + 中位）；独占/并发 FPS 均为**同码**子集（effctl/effctlconc，3 序列 × seed0）
    # 2026-10-15（审稿 R4-P6）：原表只有中位一行，题注的 1.0--1.8 区间在表内无出处 ⇒ 展开为逐序列。
    EFF_SEQS = ["balloon", "crowd2", "person_tracking"]

    def fps_of(prefix, arm, seq):
        p = ROOT / f"{prefix}_{arm}_{seq}_seed0" / "tables" / "efficiency_raw.csv"
        try:
            return float(list(csv.DictReader(p.open()))[0]["online_fps"])
        except Exception:
            return None

    rows, eff_ratios = [], []
    for a in MAIN_ARMS:
        exs, ccs = [], []
        for s in EFF_SEQS:
            ex, cc = fps_of("effctl", a, s), fps_of("effctlconc", a, s)
            if ex is None or cc is None:
                continue
            exs.append(ex)
            ccs.append(cc)
            eff_ratios.append(ex / cc)
            rows.append([SEQ_TEX[s], f"{ex:.3f}", f"{cc:.3f}", f"{ex/cc:.2f}$\\times$"])
        if exs:
            mex, mcc = statistics.median(exs), statistics.median(ccs)
            rows.append(["\\emph{median}", f"{mex:.3f}", f"{mcc:.3f}", f"{mex/mcc:.2f}$\\times$"])
    lo, hi = (f"{min(eff_ratios):.2f}", f"{max(eff_ratios):.2f}") if eff_ratios else ("--", "--")
    written.append(("tab4_efficiency.tex", _table(
        "table", "|l|c|c|c|",
        ["Sequence", "FPS excl.", "FPS conc.", "excl./conc."], rows,
        "Online-phase efficiency of the prior stack (baseline arm). The two FPS columns "
        "are a single-variable comparison: the same code revision and the same three "
        f"sequences, differing only in processes per GPU (one vs.\\ two); the "
        f"per-sequence ratio spans {lo}--{hi}, so concurrency is real but modest, not "
        "the several-fold penalty a cross-revision comparison would suggest.",
        "tab:eff",
        "FPS = frames / online time, one seed per sequence; the median row is over "
        "the three sequences.", size="\\footnotesize")))

    # Tab.2 pt 逐 seed + Sim3
    # Tab.2 pt 逐 seed + Sim3 —— **已删除（2026-10-09，用户指令）**：正文零 \input、\label{tab:pt}
    # 零引用（死件），且 Sim(3) 列已判负（verdict_sim3_scale.md）带 WITHDRAWN 警告 ⇒ 撤下。
    # 逐 seed/Sim3 读数仍在 write_markdown 的 "Tab.2 pt 逐 seed" 段与 JSON 里保留（供审计）。

    for name, text in written:
        (outdir / name).write_text(text)
    return outdir, [n for n, _ in written]


# ────────────────────────── 自检 ──────────────────────────

def selfcheck(table, latex_dir):
    """返回问题列表（空 = 通过）。阳性对照 + 口径隔离 + LaTeX 结构。"""
    problems = []
    # ① 阳性对照：本文件自算的 SE3-ATE 必须等于 tracking_raw col8（同产物、两条独立路径）
    ctl, bad = 0, []
    for arm in ARMS:
        for seq in SEQS:
            v = table[(arm, seq)]
            for k in SEEDS:
                a, b = v["ate_seeds"][k], v["sim3_ate_se3_seeds"][k]
                if a is None or b is None:
                    continue
                ctl += 1
                if abs(a - b) > 0.01:
                    bad.append((arm, seq, k, a, b))
    if bad:
        problems.append(f"阳性对照失败：自算 SE3-ATE 与 col8 不符 {len(bad)}/{ctl} 处（前 3：{bad[:3]}）")
    else:
        print(f"  [ctl] 阳性对照通过：{ctl} 个 run 自算 SE3-ATE == tracking_raw col8（≤0.01cm）")
    # ①b Sim3 不应劣于 SE3（更多自由度）
    worse = [(a, s, k) for a in ARMS for s in SEQS for k in SEEDS
             if table[(a, s)]["sim3_ate_seeds"][k] is not None
             and table[(a, s)]["sim3_ate_seeds"][k] > table[(a, s)]["sim3_ate_se3_seeds"][k] + 0.01]
    if worse:
        problems.append(f"Sim3-ATE 高于 SE3-ATE 的异常 run {len(worse)} 个（前 3：{worse[:3]}）")

    # ② 口径隔离：col8 与 col14 必须不同（若全同说明取错列）
    same = [f"{a}/{s}" for a in ARMS for s in SEQS
            if table[(a, s)]["ate_mean"] is not None
            and table[(a, s)]["ate_mean"] == table[(a, s)]["kf_ate_mean"]]
    if len(same) > 3:
        problems.append(f"col8 与 col14 数值完全相同 {len(same)} 处（疑取错列）：{same[:3]}")

    # ③ LaTeX 结构：环境配对 + 每行列数一致
    # 只检查本生成器产出的 6 张表（tab_rd/tab_storage/tab_dynport 由别的生成器产，含
    # \multicolumn 分组标题行，不适用本规则）。
    own = {"tab1_main.tex", "tab2r_render.tex",
           "tab3s_static.tex", "tab4_efficiency.tex", "tab5_ladder.tex"}
    for f in sorted(Path(latex_dir).glob("tab*.tex")):
        if f.name not in own:
            continue
        t = f.read_text()
        for env in ("table*", "table", "tabular", "center"):
            if t.count(f"\\begin{{{env}}}") != t.count(f"\\end{{{env}}}"):
                problems.append(f"{f.name}: {env} 环境不配对")
        body = t.split("\\midrule")[-1].split("\\bottomrule")[0].strip().splitlines()
        ncol = None
        for line in body:
            if not line.strip():
                continue
            c = line.count("&") + 1
            ncol = ncol or c
            if c != ncol:
                problems.append(f"{f.name}: 行列数不一致（{c} vs {ncol}）")
                break

    # ④ 覆盖：每个臂 7/7
    for a in ARMS:
        for key, name in (("ate_mean", "ATE"), ("psnr", "渲染"), ("static_psnr", "静态")):
            n = sum(1 for s in SEQS if table[(a, s)][key] is not None)
            if n != 7:
                problems.append(f"{a}: {name} 覆盖 {n}/7")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--latex-dir", default=str(ROOT / "evidence" / "latex"))
    ap.add_argument("--no-latex", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="打印自检并以其退出码结束")
    args = ap.parse_args()

    table = build_table()
    md = write_markdown(table)
    js = write_json(table)
    print(f"written {md} + {js}")
    if not args.no_latex:
        d, names = write_latex(table, args.latex_dir)
        print(f"written {d}/: {', '.join(names)}")

    problems = selfcheck(table, args.latex_dir if not args.no_latex else ".")
    print("\n── 自检 ──")
    if problems:
        for p in problems:
            print(f"  [FAIL] {p}")
    else:
        print("  [ok] 全部通过")
    # Sim3 与历史值对拍（pt1 gate 曾报 1.10-1.12；不一致须人工确认口径）
    for seq in PT_SEQS:
        v = table[("gate", seq)]
        if v["sim3_scale"] is not None:
            print(f"  Sim3 scale (gate/{seq}) = {v['sim3_scale']:.4f}  seeds={v['sim3_scale_seeds']}")
    if args.selfcheck and problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
