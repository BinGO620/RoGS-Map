#!/usr/bin/env python3
"""compose_mover_mask.py — 合成**新评测掩码** = 语义人掩码 ∪ 类无关运动残差掩码。

为什么是并集（而不是直接用运动掩码）
------------------------------------
`audit_mover_mask.py` 实测（balloon/balloon2）：纯运动残差掩码对**人**的召回只有
**0.25/0.26**——因为它检的是"**正在动**的像素"，而语义掩码标的是**整个人的轮廓**
（含站住不动的部分）。两者是不同语义：
  - 评测掩码要回答的是"**这个物体占过、会腾出的空间**"⇒ 人的**轮廓**才是正确口径；
  - 运动残差负责补的是**语义漏掉的非人行体**（箱/气球）。
故正确构造 = **并集**：`person_semantic ∪ motion_residual`。
  - 人那一侧沿用 canonical（保证 G1 超集召回 = 1.0，**不丢已有覆盖**）；
  - 非人那一侧由运动残差补入（G3 实测新增 ≈1.7% 整帧 ≈ 5.3k px/帧，与 mvnobox2 现有
    腾空区支撑中位 4.8k px 同量级 ⇒ 度量窗口**实质扩大**）。

纪律
----
- **不覆盖** `dynamic_mask/`（canonical 必须保持可复现）；输出独立目录 `dynamic_mask_mover/`。
- 本目录 = **新仪器** ⇒ 读数与 `_canon` **禁混引**；渲染产物用 `_mover` 后缀，判决头写明掩码源。
- 合成后**必须重跑** `audit_mover_mask.py`（此时 G1 应 ≈1.0；G3/G4 仍须过）。
- 写 manifest（含 sha256 与来源两目录），供可复跑与审计。

用法
----
    python scripts/02_analysis/compose_mover_mask.py \
        --seq-dir datasets/bonn/rgbd_bonn_mvnobox \
        --out results/lifecycle_paper2/mover_mask_compose_<seq>.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _index(d: str) -> dict[str, str]:
    if not os.path.isdir(d):
        return {}
    return {os.path.splitext(f)[0]: os.path.join(d, f)
            for f in os.listdir(d) if f.endswith(".png")}


def _load(p: str) -> np.ndarray:
    return np.asarray(Image.open(p).convert("L")) > 127


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq-dir", required=True)
    ap.add_argument("--person-subdir", default="dynamic_mask")
    ap.add_argument("--motion-subdir", default="dynamic_mask_motion")
    ap.add_argument("--out-subdir", default="dynamic_mask_mover")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    seq = os.path.basename(args.seq_dir.rstrip("/"))
    pdir = os.path.join(args.seq_dir, args.person_subdir)
    mdir = os.path.join(args.seq_dir, args.motion_subdir)
    odir = os.path.join(args.seq_dir, args.out_subdir)
    pi, mi = _index(pdir), _index(mdir)
    if not pi:
        print(f"ERROR: 缺语义人掩码 {pdir}", file=sys.stderr)
        return 2
    if not mi:
        print(f"ERROR: 缺运动残差掩码 {mdir}（先跑 build_mover_mask.sh）", file=sys.stderr)
        return 2
    if os.path.isdir(odir) and os.listdir(odir):
        print(f"REFUSE: {odir} 已存在且非空（不覆盖；如需重建请先手动删）", file=sys.stderr)
        return 2

    stems = sorted(set(pi) | set(mi))
    os.makedirs(odir, exist_ok=True)
    h = hashlib.sha256()
    stats = {"n_frames": len(stems), "n_person_only": 0, "n_motion_only": 0, "n_both": 0}
    added, union_area = [], []
    for stem in stems:
        p = _load(pi[stem]) if stem in pi else None
        m = _load(mi[stem]) if stem in mi else None
        u = (p if p is not None else False) | (m if m is not None else False)
        if p is not None and m is not None:
            stats["n_both"] += 1
        elif p is not None:
            stats["n_person_only"] += 1
        else:
            stats["n_motion_only"] += 1
        img = (np.asarray(u, dtype=np.uint8) * 255)
        Image.fromarray(img, mode="L").save(os.path.join(odir, f"{stem}.png"))
        h.update(stem.encode())
        h.update(np.asarray(u, dtype=np.uint8).tobytes())
        if p is not None:
            added.append(float((u & ~p).sum()) / u.size)
        union_area.append(float(u.sum()) / u.size)

    doc = {
        "sequence": seq,
        "method": "union(person_semantic, motion_residual)",
        "person_subdir": args.person_subdir, "motion_subdir": args.motion_subdir,
        "out_subdir": args.out_subdir,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stats": stats,
        "added_frac_median": round(float(np.median(added)), 6) if added else None,
        "union_area_frac_median": round(float(np.median(union_area)), 6) if union_area else None,
        "sha256": h.hexdigest(),
        "note": ("并集口径：人沿用语义掩码（保 G1=1.0），非人行体由运动残差补入。"
                 "新仪器，与 canonical 读数禁混引。"),
    }
    print(json.dumps(doc, indent=1, ensure_ascii=False))
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
        print(f"written {args.out}")
    print(f"wrote {len(stems)} masks -> {odir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
