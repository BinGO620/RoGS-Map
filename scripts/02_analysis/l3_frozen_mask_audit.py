#!/usr/bin/env python3
"""l3_frozen_mask_audit.py — 阶段 0 预检（追加）：L3 批所用**冻结评估掩码**的逐序列质量审计。

为什么有这个脚本
----------------
l1b 召回审计（l3b_mask_recall_audit.py）本想量"运行期掩码 vs gtmc 人物区域"的召回，
结果 person_tracking 上得到病态低值（mean 0.11、median 0）。三方交叉仲裁
（MaskRCNN person@0.995 / shipped seg_mask cls12 / 深度突出体）证明：
**错的是 gtmc 参照，不是运行期掩码**——运行期掩码对真实人物区域召回 0.995。
gtmc 在 pt 上：0-140 帧漏检人物（只标小 FP）、~300/500 帧半幅炸裂（49%/22% 画面）。
同时发现：shipped `seg_mask/`（2026-06-28 已存在于 /data/Datasets/Bonn，生成方
早于本仓，非本仓脚本产物——build_person_seg_mask.py 只建过 crowd3）是
**ADE20K 式 150 类 0 起**语义分割：**person = cls12**（非 VOC 15）。
crowd3 的 seg_mask 是本仓 MaskRCNN 生成（只有 0/15 两值，15=person 正确）。

本审计量化两件事（逐序列，纯 CPU，只读冻结 PNG）：
1. **gtmc 对人物区域的召回**（gtmc ∩ seg12 / seg12）——gtmc 质量地图；
   L3 用 gtmc 的序列 = balloon, balloon2, mvnobox, mvnobox2, person_tracking,
   person_tracking2（crowd 族无 gtmc，用 seg_mask cls15——对 crowd/crowd2 是错类）。
2. **gtmc 炸裂率**（面积 > 25% 画面）与空掩码率——参照失效的两种形态。

判定读数方向：gtmc 召回高（≥0.7）⇒ 该序列 L3 freshvac/static 读数可信；
召回低或炸裂 ⇒ 该序列 L3 读数存疑，L1b 判据仪器须换 seg_mask cls12。

用法
----
    python scripts/02_analysis/l3_frozen_mask_audit.py [--step 10]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
os.chdir(REPO)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from utils.gtmc_mask import frozen_mask_index, load_frozen_mask  # noqa: E402

# (序列目录名, L3 用过的 mask_source, 该序列 seg_mask 的 person 类)
# person 类按三方交叉验证钉死：crowd/crowd2/pt/pt2/balloon*/mvnobox* = 12（ADE20K 0 起），
# crowd3 = 15（本仓 MaskRCNN 生成）。
SEQS = [
    ("balloon", "dynamic_mask_gtmc", 12),
    ("balloon2", "dynamic_mask_gtmc", 12),
    ("moving_nonobstructing_box", "dynamic_mask_gtmc", 12),
    ("moving_nonobstructing_box2", "dynamic_mask_gtmc", 12),
    ("person_tracking", "dynamic_mask_gtmc", 12),
    ("person_tracking2", "dynamic_mask_gtmc", 12),
    ("crowd", "seg_mask(cls15, 错类)", 12),
    ("crowd2", "seg_mask(cls15, 错类)", 12),
    ("crowd3", "seg_mask(cls15, 正确)", 15),
]
FRAME_PX = 480 * 640


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, default=10, help="抽样帧步长（默认 10）")
    ap.add_argument("--out", default="results/lifecycle_paper2/evidence/l3_frozen_mask_audit.json")
    args = ap.parse_args()

    out = {"generated": "2026-09-21", "purpose": "L3 冻结评估掩码质量地图（gtmc vs seg12 person）",
           "cross_validation": "person=cls12 经 MaskRCNN(0.98-1.00 重叠)/深度突出体/退场一致性三方验证；"
                               "crowd3 例外（本仓生成，15=person）",
           "sequences": {}}
    for dirname, used, pcls in SEQS:
        d = f"datasets/bonn/rgbd_bonn_{dirname}"
        gidx = frozen_mask_index(os.path.join(d, "dynamic_mask_gtmc"))
        seg_files = {os.path.basename(p)[:-4]: p for p in glob.glob(os.path.join(d, "seg_mask", "*.png"))}
        # 帧集 = gtmc 键（depth stem）与 seg 键（rgb stem）按时间排序后的配对抽样
        gkeys = sorted(gidx.keys(), key=float)
        skeys = sorted(seg_files.keys(), key=float)
        rows = []
        n = min(len(gkeys), len(skeys)) if (gkeys and skeys) else 0
        for i in range(0, n, args.step):
            gmask = load_frozen_mask(gidx[gkeys[i]])
            seg = np.asarray(Image.open(seg_files[skeys[i]]).convert("L"))
            person = seg == pcls
            row = {
                "gtmc_px": int(gmask.sum()),
                "gtmc_frac": round(float(gmask.sum()) / FRAME_PX, 4),
                "person_px": int(person.sum()),
            }
            if person.any():
                row["gtmc_recall_person"] = round(float((gmask & person).sum()) / float(person.sum()), 4)
            rows.append(row)
        present = [r for r in rows if r["person_px"] >= 1500]
        rec = [r["gtmc_recall_person"] for r in present if "gtmc_recall_person" in r]
        seq_out = {
            "l3_mask_source": used,
            "n_sampled": len(rows),
            "n_person_present": len(present),
            "gtmc_recall_person_mean": round(statistics.mean(rec), 4) if rec else None,
            "gtmc_recall_person_median": round(statistics.median(rec), 4) if rec else None,
            "gtmc_blowup_frames(gt_frac>0.25)": sum(1 for r in rows if r["gtmc_frac"] > 0.25),
            "gtmc_empty_frames": sum(1 for r in rows if r["gtmc_px"] == 0),
        }
        out["sequences"][dirname] = {"summary": seq_out, "frames": rows}
        print(f"{dirname:32s} {used:24s} present={len(present):3d}/{len(rows):3d} "
              f"recall={seq_out['gtmc_recall_person_mean']} blowup={seq_out['gtmc_blowup_frames(gt_frac>0.25)']} "
              f"empty={seq_out['gtmc_empty_frames']}", flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"written {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
