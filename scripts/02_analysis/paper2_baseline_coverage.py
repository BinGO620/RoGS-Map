#!/usr/bin/env python
"""paper2_baseline_coverage.py — 盘点 resources/baselines/ 复现基线的覆盖与缺口。

用途：论文 2 重写（v1）要引入"系统横向对比"表，本脚本先机写一份**覆盖/缺口报告**，
让叙事与表设计建立在硬事实上（数字零手抄）。

输入：resources/baselines/baselines_result/<method>/{tracking,mapping,efficiency}_raw.csv
输出：resources/baselines/05-coverage_report_2026-10-10.md

口径（依 resources/baselines/03-metrics_checklist.md）：
  * ATE = ate_rmse_cm（所有帧 ATE RMSE，Horn alignment，cm）
  * PSNR/SSIM/Depth-L1 = mapping_raw（全图口径，mask_type=full）
  * FPS = fps_end_to_end，GPU = gpu_memory_gb（peak）
  * 每格 = 该序列 3 seed 的 mean±std（样本标准差 ddof=1）

本脚本只读，不改任何 raw 结果；消费方 = 论文 v1 §3 系统对比（待叙事锁定）。
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "resources/baselines/baselines_result"
OUT = REPO / "resources/baselines/05-coverage_report_2026-10-10.md"

# 方法能力（取自 01-baselines_method.md）
CAP = {
    "ORB_SLAM3": "static/keypoint", "DynaSLAM": "dynamic/keypoint", "NGD-SLAM": "dynamic/keypoint",
    "Co-SLAM": "static/nerf", "RoDyn-SLAM": "dynamic/nerf",
    "SplaTAM": "static/3dgs", "MonoGS": "static/3dgs", "DG-SLAM": "dynamic/3dgs",
    "WildGS-SLAM": "dynamic/3dgs", "RGD-SLAM": "dynamic/3dgs", "DynaGSLAM": "dynamic/3dgs",
}
# 序列名映射：baseline 用缩写；本仓 stack 用全名
BONN_MAP = {"person_t": "person_tracking", "person_t2": "person_tracking2",
            "mv_no_box": "mvnobox", "mv_no_box2": "mvnobox2"}
# 论文 v0 的 BONN 七序列（tab1_main）
OUR_BONN = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
            "person_tracking", "person_tracking2"]


def _read(method, kind):
    f = BASE / method / f"{kind}_raw.csv"
    if not f.exists():
        return None
    return pd.read_csv(f, encoding="utf-8-sig")


def main():
    methods = sorted(d for d in os.listdir(BASE) if (BASE / d).is_dir())
    L = []
    L.append("# 复现基线覆盖报告（机写）")
    L.append("")
    L.append(f"> **生成**：`scripts/02_analysis/paper2_baseline_coverage.py`（{date.today().isoformat()}）")
    L.append("> **来源**：`resources/baselines/baselines_result/<method>/{tracking,mapping,efficiency}_raw.csv`")
    L.append("> **性质**：论文 v1 §3 系统横向对比的**事实基础**；只读盘点，不改任何 raw 结果。")
    L.append("")
    L.append("## 1. 方法清单（11）与能力")
    L.append("")
    L.append("| 方法 | 类别 |")
    L.append("|---|---|")
    for m in methods:
        L.append(f"| {m} | {CAP.get(m, '?')} |")
    L.append("")

    # 覆盖矩阵
    L.append("## 2. 覆盖矩阵（BONN 8 序列 × 3 seed 应有的行数 = 24）")
    L.append("")
    L.append("| 方法 | tracking OK | mapping 指标 | efficiency OK | BONN 序列 |")
    L.append("|---|---|---|---|---|")
    per_method = {}
    for m in methods:
        t, g, e = _read(m, "tracking"), _read(m, "mapping"), _read(m, "efficiency")
        tb = t[t.dataset == "BONN"] if t is not None else pd.DataFrame()
        gb = g[g.dataset == "BONN"] if g is not None else pd.DataFrame()
        eb = e[e.dataset == "BONN"] if e is not None else pd.DataFrame()
        tok = int((tb.status == "OK").sum()) if "status" in tb else 0
        eok = int((eb.status == "OK").sum()) if "status" in eb else 0
        gm = int(gb["psnr"].notna().sum()) if "psnr" in gb else 0
        seqs = sorted(tb.sequence.dropna().unique()) if "sequence" in tb else []
        per_method[m] = {"t_ok": tok, "g_psnr": gm, "e_ok": eok, "seqs": seqs}
        L.append(f"| {m} | {tok}/24 | PSNR {gm}/24 | {eok}/24 | {len(seqs)} |")
    L.append("")

    # 序列集对齐
    L.append("## 3. 序列集对齐（BONN，本文 stack vs 复现套件）")
    L.append("")
    any_seqs = sorted({s for v in per_method.values() for s in v["seqs"]})
    L.append(f"- 复现套件 BONN 序列（缩写）：{', '.join(any_seqs)}")
    mapped = [BONN_MAP.get(s, s) for s in any_seqs]
    L.append(f"- 映射到本仓全名：{', '.join(mapped)}")
    L.append(f"- **本文 stack 的 BONN 七序列**：{', '.join(OUR_BONN)}")
    common = sorted(set(mapped) & set(OUR_BONN))
    base_only = sorted(set(mapped) - set(OUR_BONN))
    ours_only = sorted(set(OUR_BONN) - set(mapped))
    L.append(f"- **交集（可同表对比）**：{', '.join(common)}  → 共 {len(common)} 条")
    L.append(f"- 仅基线有（本文 stack 无 run）：{', '.join(base_only) or '无'}")
    L.append(f"- 仅本文有（基线无，如 crowd3）：{', '.join(ours_only) or '无'}")
    L.append("")

    # 缺口
    L.append("## 4. 指标缺口（BONN）")
    L.append("")
    L.append("| 方法 | ATE | PSNR/SSIM/LPIPS | Depth-L1 | Accuracy | FPS | GPU | #Gaussians |")
    L.append("|---|---|---|---|---|---|---|---|")
    for m in methods:
        t, g, e = _read(m, "tracking"), _read(m, "mapping"), _read(m, "efficiency")
        tb = t[t.dataset == "BONN"] if t is not None else pd.DataFrame()
        gb = g[g.dataset == "BONN"] if g is not None else pd.DataFrame()
        eb = e[e.dataset == "BONN"] if e is not None else pd.DataFrame()
        def nz(df, c):
            return "✓" if (c in df and df[c].notna().sum() > 0) else "—"
        L.append(f"| {m} | {nz(tb,'ate_rmse_cm')} | {nz(gb,'psnr')} | {nz(gb,'depth_l1_cm')} "
                 f"| {nz(gb,'accuracy_cm')} | {nz(eb,'fps_end_to_end')} | {nz(eb,'gpu_memory_gb')} "
                 f"| {nz(eb,'num_gaussians')} |")
    L.append("")
    L.append("> 非 3DGS 方法（ORB_SLAM3/DynaSLAM/NGD-SLAM/RoDyn-SLAM 部分列）无 mapping/GPU/Gaussians 字段，属 N/A（方法不支持）。")
    L.append("")

    # 口径提醒
    L.append("## 5. 口径提醒（入表前必须处理）")
    L.append("")
    L.append("1. **序列集不一致**：基线含 `mv_no_box/mv_no_box2`（本文 stack 无 run），"
             "本文含 `crowd3`（基线无）。可同表对比的公共集见 §3。")
    L.append("2. **mask 口径**：基线 mapping 全图（`mask_type=full`，`mask_source=flow_motion_precomputed`）；"
             "本文 stack 渲染另有 static/dynamic 分区口径 —— 跨口径禁混引。")
    L.append("3. **对齐**：baseline 统一 Horn SE(3)（`03-metrics_checklist.md`）；"
             "本文 stack 亦 SE(3)。单目方法若需 Sim(3) 须单独声明（不混入主表）。")
    L.append("4. **静态方法在动态 BONN 上 tracking 崩**（如 Co-SLAM/SplaTAM 的 ATE 可达 10²–10⁴ cm）"
             "——如实呈现，不裁剪；这本身是反动态范式的动机证据。")
    OUT.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT.relative_to(REPO)} ({len(L)} lines)")
    # 摘要打印
    print(f"methods={len(methods)} common_BONN={common} base_only={base_only} ours_only={ours_only}")


if __name__ == "__main__":
    main()
