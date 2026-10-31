#!/usr/bin/env python
"""paper2_baseline_text_summary.py — §3 正文用 PSNR/FPS 机写摘要（零手抄）。

消费 results/paper2_fulltable/evidence/baseline_compare.json（由 paper2_baseline_table.py 生成，
同批同机）。输出 evidence 工件，供 §3 正文与审稿人复核引用；正文数字一律从本文件抄（仍带工件键注释）。

口径：公共 BONN 6 序列（balloon/balloon2/crowd/crowd2/person_tracking/person_tracking2）；
PSNR 全图（mask_type=full）；FPS = fps_end_to_end；mean±sd over 3 seeds；-- = 未覆盖（N/A）。
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
JSON = REPO / "results/paper2_fulltable/evidence/baseline_compare.json"
OUT_MD = REPO / "results/paper2_fulltable/evidence/psnr_fps_text_summary_2026-10-11.md"

COMMON = ["balloon", "balloon2", "crowd", "crowd2", "person_t", "person_t2"]
SEQ_LABEL = {"balloon": "balloon", "balloon2": "balloon2", "crowd": "crowd",
             "crowd2": "crowd2", "person_t": "person_tracking", "person_t2": "person_tracking2"}
LABEL = {
    "MonoGS": "MonoGS", "SplaTAM": "SplaTAM", "Co-SLAM": "Co-SLAM", "ORB_SLAM3": "ORB-SLAM3",
    "DG-SLAM": "DG-SLAM", "RGD-SLAM": "RGD-SLAM", "WildGS-SLAM": "WildGS-SLAM",
    "DynaGSLAM": "DynaGSLAM", "DynaSLAM": "DynaSLAM", "NGD-SLAM": "NGD-SLAM",
    "RoDyn-SLAM": "RoDyn-SLAM", "Prior RGB-D stack": "Prior RGB-D stack",
}
GROUP = {
    "MonoGS": "static", "SplaTAM": "static", "Co-SLAM": "static", "ORB_SLAM3": "static",
    "DG-SLAM": "dynamic", "RGD-SLAM": "dynamic", "WildGS-SLAM": "dynamic", "DynaGSLAM": "dynamic",
    "DynaSLAM": "dynamic", "NGD-SLAM": "dynamic", "RoDyn-SLAM": "dynamic", "Prior RGB-D stack": "prior",
}


def fmt(v):
    if not v:
        return "--"
    return f"{v[0]:.2f}±{v[1]:.2f}" if v[1] else f"{v[0]:.2f}"


def main():
    rows = {r["method"]: r for r in json.load(open(JSON))}
    md = ["# §3 正文 PSNR/FPS 机写摘要（2026-10-11）",
          "",
          "> 生成：`scripts/02_analysis/paper2_baseline_text_summary.py`（机写，零手抄）",
          f"> 来源：`baseline_compare.json`（`paper2_baseline_table.py` 输出，同批同机同协议）。",
          "> 口径：公共 BONN 6 序列；PSNR 全图 mean±sd（3 seed）；FPS = end-to-end mean±sd；`--` = 未覆盖。",
          "",
          "## 1. PSNR（全图，dB）",
          "",
          "| 方法 | balloon | balloon2 | crowd | crowd2 | person_tracking | person_tracking2 |",
          "|---|---|---|---|---|---|---|"]
    for m, lab in LABEL.items():
        c = rows[m]["cells"]
        md.append(f"| {lab} | " + " | ".join(fmt(c[b]["psnr"]) for b in COMMON) + " |")
    md += ["",
           "## 2. FPS（end-to-end）",
           "",
           "| 方法 | balloon | balloon2 | crowd | crowd2 | person_t | person_t2 |",
           "|---|---|---|---|---|---|---|"]
    for m, lab in LABEL.items():
        c = rows[m]["cells"]
        md.append(f"| {lab} | " + " | ".join(fmt(c[b]["fps"]) for b in COMMON) + " |")
    md += ["",
           "## 3. 正文口径提示",
           "",
           "- PSNR 未覆盖：DynaSLAM / NGD-SLAM / ORB-SLAM3（`--`，方法无渲染通路/未复现渲染）——正文只报有覆盖的方法。",
           "- FPS 全方法有覆盖；ORB-SLAM3 为传统特征法（~65–72 FPS），与 GS/NeRF 类不同量级，正文可注明。",
           "- 前作栈 PSNR/FPS 来自 r33_rebase preview（全图离线渲染 / 并发批中位数），与基线套件口径同源不同批，正文须注明（同 §3 讨论稿 §6）。"]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(f"wrote {OUT_MD.relative_to(REPO)}")


if __name__ == "__main__":
    main()
