#!/usr/bin/env python
"""verify_base_identity.py — C2 前置核验（G4 条件）：`dyn_lineage_base==0` 路径逐位不变。

做什么：用**当前代码** load 底图 PLY → 立即 save 回 → 逐字节/逐字段比对。
目的 = 证 DynPort 实装期对 `gaussian_model.py` 的改动（`fd2a105cf`/`1e30d1c72`）
在 `dyn_lineage_base==0`（默认）下不改动几何（load_ply/save_ply 往返逐位一致）。

产物：results/dynport_offline/evidence/base_arm_identity.json
用法：python scripts/dynport_offline/verify_base_identity.py --base-run <R33 baseline run>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from plyfile import PlyData  # noqa: E402


def _vertex_bytes(ply_path, attrs):
    d = PlyData.read(str(ply_path))
    v = d.elements[0]
    return {a: np.asarray(v[a]) for a in attrs}


def _sha(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-run", required=True)
    ap.add_argument("--out", default="results/dynport_offline/evidence/base_arm_identity.json")
    args = ap.parse_args()

    import torch
    from gaussian_splatting.scene.gaussian_model import GaussianModel
    import yaml

    run = Path(args.base_run)
    cfg = yaml.safe_load(open(run / "config.yml"))
    src = run / "point_cloud" / "final_after_opt" / "point_cloud.ply"
    if not src.exists():
        src = run / "point_cloud" / "final" / "point_cloud.ply"

    attrs = ["x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity",
             "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]
    before = _vertex_bytes(src, attrs)

    # 当前代码：load → save（dyn_lineage_base 默认 0）
    g = GaussianModel(sh_degree=0, config=cfg)
    g.load_ply(str(src))
    assert int(g.dyn_lineage_base) == 0, f"dyn_lineage_base 非 0: {g.dyn_lineage_base}"
    tmp = Path("/tmp/_base_identity_roundtrip.ply")
    g.save_ply(str(tmp))
    after = _vertex_bytes(tmp, attrs)

    per_attr = {}
    all_ok = True
    for a in attrs:
        same = bool(before[a].shape == after[a].shape and _sha(before[a]) == _sha(after[a]))
        per_attr[a] = "identical" if same else "DIFF"
        all_ok &= same
    res = {"base_run": str(run), "src_ply": str(src),
           "n_vertex": int(before["x"].shape[0]),
           "dyn_lineage_base": int(g.dyn_lineage_base),
           "roundtrip_bit_identical": all_ok, "per_attr": per_attr,
           "note": "load_ply→save_ply 往返在 dyn_lineage_base==0 下逐字段 SHA256 一致 "
                   "⇒ DynPort 实装期改动不改几何（C2）"}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    try:
        tmp.unlink()
    except OSError:
        pass
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
