#!/usr/bin/env python3
"""l3b_mask_recall_audit.py — 阶段 0 预检：运行期 MaskRCNN 掩码 vs gtmc 冻结人物区域的逐帧召回审计。

为什么有这个脚本
----------------
证据门控（evidence gate，L1b）在运行期动态掩码内阻止 alpha 回升（治"续命"）。
gate 的功效上界 = 运行期掩码对**真实人物区域**的召回：掩码盖不住人在哪，
gate 就拦不住"人回来再占据 -> 深度自洽 -> alpha 回升"那条通路。
本审计在 person_tracking 的 KF 网格上逐帧测这个召回，产出 = prereg_L1b_gate
分层失败分支的输入（"召回上界 <50% => 方法边界，非仪器背锅"）。

口径（与运行期逐位同源的三个保证）
--------------------------------
1. 运行期掩码 = `utils/semantic_mask.compute_semantic_dynamic_mask`（同一函数），
   SemanticMask 块逐字段取自 `configs/experiments/combined_prune/method.yaml`
   （L3 栈同款：maskrcnn / person=1 / dilate 7 / max_ratio 0.95；conf 与 mask
   阈值走函数默认 0.5），仅 device 覆写为 --device（渲染坑后一律钉单卡）。
2. 输入帧 = `utils.dataset.load_dataset`（TUMDataset：undistort + [0,1] 归一化，
   即运行期 `viewpoint.original_image` 的同一加载路径）。
3. 参照 = `dynamic_mask_gtmc/<depth_stem>.png`（gtmc 冻结件，方法无关）。
   **gtmc 是评估件，gate 不消费它**；这里仅作"真实人物区域"的独立参照。

帧集 = evidence/l1b_audit_kf_grid.json 的 union（L3 person_tracking exit 三 seed
alpha-ledger KF 并集；gate 臂的最近代理——gate 只改 alpha 不改跟踪，KF 选择
与 exit 臂同分布）。跨 GPU 的 FP 噪声不除障（掩码阈值 0.5 的二值化对之不敏感）。

用法
----
    python scripts/02_analysis/l3b_mask_recall_audit.py [--device cuda:0]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
os.chdir(REPO)  # dataset_path 相对路径与 run 时一致

import yaml  # noqa: E402
from munch import munchify  # noqa: E402

from utils.dataset import load_dataset  # noqa: E402
from utils.gtmc_mask import frozen_mask_index, load_frozen_mask  # noqa: E402
from utils.semantic_mask import compute_semantic_dynamic_mask  # noqa: E402


def summarize(rows: list) -> dict:
    """rows = 逐帧记录（本函数只聚合，不判定——判定在 prereg）。"""
    ok = [r for r in rows if r.get("recall") is not None]
    n_none = sum(1 for r in rows if r["runtime_mask_px"] is None)
    n_nogt = sum(1 for r in rows if r["gtmc_px"] is None)
    rec = [r["recall"] for r in ok]
    prec = [r["precision"] for r in ok if r["precision"] is not None]
    pooled_inter = sum(r["inter_px"] for r in ok)
    pooled_gt = sum(r["gtmc_px"] for r in ok)
    pooled_rt = sum(r["runtime_mask_px"] for r in ok)
    return {
        "n_frames": len(rows),
        "n_recall_valid": len(ok),
        "n_runtime_mask_none": n_none,
        "n_gtmc_missing": n_nogt,
        "mean_recall": statistics.mean(rec) if rec else None,
        "median_recall": statistics.median(rec) if rec else None,
        "pooled_recall": (pooled_inter / pooled_gt) if pooled_gt else None,
        "pooled_precision": (pooled_inter / pooled_rt) if pooled_rt else None,
        "mean_precision": statistics.mean(prec) if prec else None,
        "frac_recall_ge_0.5": (sum(1 for x in rec if x >= 0.5) / len(rec)) if rec else None,
        "frac_recall_ge_0.7": (sum(1 for x in rec if x >= 0.7) / len(rec)) if rec else None,
        "min_recall": min(rec) if rec else None,
        "max_recall": max(rec) if rec else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kf-grid", default="results/lifecycle_paper2/evidence/l1b_audit_kf_grid.json")
    ap.add_argument("--dataset", default="datasets/bonn/rgbd_bonn_person_tracking")
    ap.add_argument("--method-yaml", default="configs/experiments/combined_prune/method.yaml")
    ap.add_argument("--base-config", default="configs/rgbd/bonn/base_config.yaml")
    ap.add_argument("--gtmc-dir", default=None, help="缺省 <dataset>/dynamic_mask_gtmc")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--out", default="results/lifecycle_paper2/evidence/l1b_mask_recall_audit.json")
    args = ap.parse_args()

    grid = json.load(open(args.kf_grid))
    cfg = yaml.safe_load(open(args.base_config))
    cfg["Dataset"]["dataset_path"] = args.dataset
    sem = dict(yaml.safe_load(open(args.method_yaml))["SemanticMask"])
    sem["device"] = args.device  # 仅覆写设备；其余字段逐字段 = L3 栈
    cfg["SemanticMask"] = sem

    ds = load_dataset(munchify({"input_folder": args.dataset}), args.dataset, config=cfg)
    ds.device = args.device
    gtmc_dir = args.gtmc_dir or os.path.join(args.dataset, "dynamic_mask_gtmc")
    index = frozen_mask_index(gtmc_dir)
    print(f"[audit] frames={len(grid['union'])} gtmc_masks={len(index)} "
          f"sem={ {k: sem[k] for k in ('model', 'dynamic_classes', 'dilate_px')} } "
          f"device={args.device}", flush=True)

    rows = []
    for i in grid["union"]:
        image, _, _ = ds[i]  # (3,H,W) [0,1] on device —— 运行期 original_image 同源
        rt = compute_semantic_dynamic_mask(cfg, image)  # (1,H,W) bool 或 None（>max_ratio）
        stem = os.path.splitext(os.path.basename(ds.depth_paths[i]))[0]
        gpath = index.get(stem)
        gt = load_frozen_mask(gpath) if gpath else None
        row = {
            "frame": i,
            "depth_stem": stem,
            "runtime_mask_px": None if rt is None else int(rt.sum()),
            "gtmc_px": None if gt is None else int(gt.sum()),
        }
        if rt is not None and gt is not None and gt.any():
            rtb = rt.squeeze().cpu().numpy().astype(bool)
            inter = int((rtb & gt).sum())
            row["inter_px"] = inter
            row["recall"] = inter / float(gt.sum())
            row["precision"] = (inter / float(rtb.sum())) if rtb.any() else None
        rows.append(row)
        print(f"[audit] frame {i}: recall={row.get('recall')} "
              f"rt_px={row['runtime_mask_px']} gt_px={row['gtmc_px']}", flush=True)

    per_seed = {s: summarize([r for r in rows if r["frame"] in set(kfs)])
                for s, kfs in grid["seeds"].items()}
    out = {
        "generated": "2026-09-21",
        "purpose": "L1b evidence-gate 功效上界（运行期掩码召回 vs gtmc 冻结人物区域）",
        "sequence": grid["sequence"],
        "kf_grid_source": grid["source"],
        "sem_mask_source": args.method_yaml,
        "device": args.device,
        "union": summarize(rows),
        "per_seed": per_seed,
        "frames": rows,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"[audit] written {args.out}")
    print(json.dumps({"union": out["union"], "per_seed": per_seed}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
