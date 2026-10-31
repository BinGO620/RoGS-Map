#!/usr/bin/env python3
"""audit_mover_mask.py — 新评测掩码（类无关"移动体"）的**质量门**（可复跑工件）。

背景（掩码事故的教训）
----------------------
2026-09-22 的掩码事故本质是：**一张失效的掩码被当成有效仪器用了很久**，而当时没有任何
可复跑的"掩码质量门"。本脚本把门做成程序化、可复跑、带阈值的工件，用于任何**新**评测掩码
（这里是 `dynamic_mask_mover/`：person → 人+箱/气球等所有移动体）。

门（先锁；不通过则该掩码不得用于判效）
--------------------------------------
- **G1 超集召回**：新掩码必须覆盖住旧 canonical 人掩码——
  `mean(|canon ∩ new| / |canon|)` over frames with `|canon|>0` **≥ 0.90**。
  理由：类无关管线的核心主张是"同时抓到人和非人行体"；抓不住人即管线在本序列失效。
- **G2 空掩码率**：旧掩码有人而新掩码全空的帧占比 **≤ 0.02**。
- **G3 确有增量**：新增面积 `|new \\ canon|` 的中位（占整帧像素）**> 0.002**（确有非人行体被加入；
  否则本掩码只是旧掩码的复制品，整条"扩覆盖"路线无意义）。
- **G4 面积护栏**：新掩码面积中位占整帧像素 **≤ 0.50**（对照管线已知的"保守过排除"边界；
  若过半帧被标为移动，说明管线在本序列失控，读数不可用）。
- **G5 对照区存活（最要紧的一条；2026-09-25 实测后补）**：新掩码**逐帧**面积可以很小，但
  残影指标消费的是**历史积累区**（past-union），而构型对照（全域静态 / 邻域环）需要
  当前帧**未被标为动态**的像素。运动残差在手持视频上会把相机运动/模糊帧**大面积过判**，
  积累后腾空区可吞掉 75–79% 画面 ⇒ **对照区塌陷 ⇒ 不可判**（实测 mvnobox2：
  static_bg 1103 px、ring 226 px；且 G1–G4 **全部通过**——说明只看逐帧面积的 G4 不足以拦截）。
  故 G5 直接读仪器产出（`rescore_L3_<alias>_off_s0_mover.json` 的 `support_px_median`）：
  **static_bg ≥ 5000 px 且 ring ≥ 1000 px**（依据：repo 自身把 balloon2 的 ring 2882 px 记为
  "薄环带"、static_bg 10010 记为"稀薄"，故 5000/1000 是"薄带"之下再降一档的底线）。
  缺该 JSON 时 G5 记 SKIP（不阻塞），但**判效前必须补齐**。

用法
----
    python scripts/02_analysis/audit_mover_mask.py \
        --seq-dir datasets/bonn/rgbd_bonn_mvnobox --new-subdir dynamic_mask_mover \
        --out results/lifecycle_paper2/mover_mask_audit_<seq>.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

G1_MIN_RECALL = 0.90     # 超集召回
G2_MAX_EMPTY = 0.02      # 空掩码率
G3_MIN_ADDED = 0.002     # 增量下界（占整帧）
G4_MAX_AREA = 0.50       # 面积护栏
G5_MIN_STATIC_BG = 5000  # 构型对照（全域静态）支撑像素底线
G5_MIN_RING = 1000       # 构型对照（邻域环）支撑像素底线

# rgbd 目录名 -> 实验别名（instrument_v2 rescore tag 用别名）
ALIAS = {
    "rgbd_bonn_balloon": "balloon",
    "rgbd_bonn_balloon2": "balloon2",
    "rgbd_bonn_moving_nonobstructing_box": "mvnobox",
    "rgbd_bonn_moving_nonobstructing_box2": "mvnobox2",
}


def _load_mask(p: str) -> np.ndarray:
    return np.asarray(Image.open(p).convert("L")) > 127


def _index(d: str) -> dict[str, str]:
    if not os.path.isdir(d):
        return {}
    return {os.path.splitext(f)[0]: os.path.join(d, f)
            for f in os.listdir(d) if f.endswith(".png")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq-dir", required=True, help="datasets/bonn/rgbd_bonn_<seq>")
    ap.add_argument("--new-subdir", default="dynamic_mask_mover")
    ap.add_argument("--canon-subdir", default="dynamic_mask")
    ap.add_argument("--out", default=None)
    ap.add_argument("--rescore-dir", default=None,
                    help="仪器产出目录（找 rescore_L3_<alias>_off_s0<rescore-suffix>.json 做 G5）")
    ap.add_argument("--rescore-suffix", default="_mover",
                    help="仪器产物文件名后缀（渲染/重评分 tag 后缀，默认 _mover）")
    args = ap.parse_args()

    seq = os.path.basename(args.seq_dir.rstrip("/"))
    new_dir = os.path.join(args.seq_dir, args.new_subdir)
    can_dir = os.path.join(args.seq_dir, args.canon_subdir)
    ni, ci = _index(new_dir), _index(can_dir)
    if not ni:
        print(f"ERROR: 缺新掩码目录 {new_dir}", file=sys.stderr)
        return 2
    if not ci:
        print(f"ERROR: 缺参照人掩码目录 {can_dir}", file=sys.stderr)
        return 2

    common = sorted(set(ni) & set(ci))
    if not common:
        print("ERROR: 两目录无同名 stem（命名口径不一致？）", file=sys.stderr)
        return 2

    recalls, new_area, added, empty_when_person, per_frame = [], [], [], 0, []
    for stem in common:
        c = _load_mask(ci[stem])
        m = _load_mask(ni[stem])
        px = c.size
        nc, nm = int(c.sum()), int(m.sum())
        inter = int((c & m).sum())
        add = int((m & ~c).sum())
        if nc > 0:
            recalls.append(inter / nc)
            if nm == 0:
                empty_when_person += 1
        new_area.append(nm / px)
        added.append(add / px)
        per_frame.append({"stem": stem, "px": px, "n_canon": nc, "n_new": nm,
                          "recall_canon_by_new": round(inter / nc, 4) if nc else None,
                          "added_frac": round(add / px, 6)})

    n_person = sum(1 for f in per_frame if f["n_canon"] > 0)
    g1 = float(np.mean(recalls)) if recalls else 0.0
    g2 = (empty_when_person / n_person) if n_person else 0.0
    g3 = float(np.median(added)) if added else 0.0
    g4 = float(np.median(new_area)) if new_area else 0.0

    gates = {
        "G1_superset_recall": {"value": round(g1, 4), "min": G1_MIN_RECALL, "pass": g1 >= G1_MIN_RECALL},
        "G2_empty_rate": {"value": round(g2, 4), "max": G2_MAX_EMPTY, "pass": g2 <= G2_MAX_EMPTY},
        "G3_added_frac_median": {"value": round(g3, 6), "min": G3_MIN_ADDED, "pass": g3 > G3_MIN_ADDED},
        "G4_new_area_median": {"value": round(g4, 6), "max": G4_MAX_AREA, "pass": g4 <= G4_MAX_AREA},
    }

    # ---- G5 对照区存活（读仪器产出；缺则 SKIP，不阻塞但须补齐）----
    alias = ALIAS.get(seq)
    g5, g5_note = None, "SKIP: 缺 alias 或 rescore 件"
    if alias and args.rescore_dir:
        rp = os.path.join(args.rescore_dir,
                          f"rescore_L3_{alias}_off_s0{args.rescore_suffix}.json")
        if os.path.isfile(rp):
            sup = (json.load(open(rp)).get("support_px_median") or {})
            sb, rg = sup.get("static_bg"), sup.get("ring")
            ok5 = (sb is not None and rg is not None
                   and sb >= G5_MIN_STATIC_BG and rg >= G5_MIN_RING)
            g5 = {"static_bg": sb, "ring": rg,
                  "min_static_bg": G5_MIN_STATIC_BG, "min_ring": G5_MIN_RING, "pass": bool(ok5)}
            g5_note = f"static_bg={sb} (需≥{G5_MIN_STATIC_BG}), ring={rg} (需≥{G5_MIN_RING})"
        else:
            g5_note = f"SKIP: 缺 {rp}"
    if g5 is not None:
        gates["G5_control_survival"] = g5

    ok = all(v["pass"] for v in gates.values() if isinstance(v, dict) and "pass" in v)

    doc = {
        "sequence": seq, "new_subdir": args.new_subdir, "canon_subdir": args.canon_subdir,
        "n_common_frames": len(common), "n_frames_with_person": n_person,
        "gates": gates, "G5_note": g5_note, "PASS": ok,
        "note": ("G1 召回 = |canon∩new|/|canon|（类无关管线必须覆盖住人）；"
                 "G3 增量 = |new\\canon| 占整帧中位（>0 才说明确有非人行体被加入）；"
                 "分母口径 = 整帧像素（非 valid-depth 像素），与 builder 的 coverage 字段口径不同。"),
        "per_frame_head": per_frame[:5],
    }
    print(json.dumps({k: doc[k] for k in
                      ("sequence", "n_common_frames", "n_frames_with_person", "gates", "PASS")},
                     indent=1, ensure_ascii=False))
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
        print(f"written {args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
