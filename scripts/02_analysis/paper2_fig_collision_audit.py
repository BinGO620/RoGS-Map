#!/usr/bin/env python
"""paper2_fig_collision_audit.py — 论文 2 全图碰撞审计门（可复跑，G4 固化）。

存在理由（2026-10-09 G4）：此前"8/8 碰撞审计 PASS"只在会话内以 /tmp 技能脚本自报，
无可复跑工件（与字号门同类）。本脚本把 9 图逐一跑碰撞审计并给统一退出码。

审计器 = `vendor/audit_figure_collisions.py`（取自本机 nature-figure 技能，随仓入库保
可复跑；几何核心用 PyMuPDF 读 PDF，不重绘、不改图）。

用法：python scripts/02_analysis/paper2_fig_collision_audit.py
退出码：0 = 全 PASS；1 = 有 FIX BEFORE DELIVERY / NOT AUDITABLE。
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AUDIT = REPO / "scripts/02_analysis/vendor/audit_figure_collisions.py"
PAPER_FIGS = REPO / "papers/paper2/figs"
GSC_FIGS = REPO / "results/gs_compress/figs"

FIGS = [
    (PAPER_FIGS, n) for n in (
        "fig1_pipeline.pdf", "fig2_render_crowd2.pdf", "fig2b_render_person_tracking.pdf",
        "fig3_trajectory_crowd2.pdf", "fig4_tail.pdf", "fig5_accounting.pdf",
        "fig6_dynport_repair.pdf", "fig_rd_curves.pdf", "fig_storage_accounting.pdf",
        "fig_teaser.pdf",
    )
]


def main():
    if not AUDIT.exists():
        print(f"审计器缺失：{AUDIT}", file=sys.stderr)
        return 2
    fails = []
    for d, name in FIGS:
        pdf = d / name
        if not pdf.exists():
            print(f"  {name}: 缺文件（跳过）")
            continue
        r = subprocess.run([sys.executable, str(AUDIT), str(pdf)],
                           capture_output=True, text=True)
        verdict = next((l for l in r.stdout.split("\n") if l.startswith("verdict:")), "verdict: ?")
        print(f"  {name:34s} {verdict.strip()}")
        if "PASS" not in verdict:
            fails.append((name, verdict.strip()))
    print(f"\nfails: {len(fails)}")
    for name, v in fails:
        print(f"  FAIL {name}: {v}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
