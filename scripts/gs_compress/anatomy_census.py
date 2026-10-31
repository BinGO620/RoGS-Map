#!/usr/bin/env python
"""anatomy_census.py — §4 解剖统计的通用普查器（零 GPU，只读 PLY）。

**为什么需要本脚本（2026-10-22）**：论文 §4 的四项统计中，
* 范围膨胀 / 重尾   → 原由 `tail_census.py` 产出（硬编码 Bonn 路径）
* 各向同性占比、四元数偏离单位模 → **此前只有散文记载，无生成脚本、无 JSON 工件**

审稿复核时无法从仓库重建后两个数字。本脚本补齐可复现链，并把普查从
「14 张 Bonn 动态图」扩展到三类对照：

  --panel ours_dynamic   本栈 7 序列 × 2 臂 × seed0（= 论文 §4 的 14 张）
  --panel ours_heldout   L3 held-out 面板（TUM 静态/动态 + Bonn mv），42 张
  --panel dynagslam      DynaGSLAM 官方输出（跨系统对照，79 字段 schema）

口径与 `gs_codec.py` 一致：scale 为 log 域（仓库 PLY 直存 log-scale）；
rot 用 rot_0..3 原始四元数求范数（DynaGSLAM 为 rot_000_*）。

产出：results/gs_compress/evidence/anatomy_census.json
      results/gs_compress/evidence/anatomy_census_2026-10-22.md
"""
from __future__ import annotations

import argparse
import glob
import json

from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT_JSON = REPO / "results/gs_compress/evidence/anatomy_census.json"
OUT_MD = REPO / "results/gs_compress/evidence/anatomy_census_2026-10-22.md"

DYNAGSLAM_ROOT = Path("/data/baselines/DynaGSLAM_official/output/dynagslam_benchmark")

BONN_SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
             "person_tracking", "person_tracking2"]


# ---------------------------------------------------------------- PLY reading
def read_ply_header(path: str) -> tuple[int, list[str], int]:
    """读 header：返回 (顶点数, 全部 float 属性名, 数据起始偏移)。"""
    with open(path, "rb") as f:
        head = b""
        while b"end_header\n" not in head:
            chunk = f.read(4096)
            if not chunk:
                raise ValueError(f"{path}: 未找到 end_header")
            head += chunk
    off = head.find(b"end_header\n") + len(b"end_header\n")
    lines = head[:off].decode(errors="replace").split("\n")
    n = int([l for l in lines if l.startswith("element vertex")][0].split()[-1])
    names = [l.split()[-1] for l in lines if l.startswith("property float")]
    return n, names, off


def load_ply(path: str) -> tuple[dict, int]:
    n, names, off = read_ply_header(path)
    with open(path, "rb") as f:
        f.seek(off)
        buf = f.read(n * len(names) * 4)
    arr = np.frombuffer(buf, dtype="<f4").reshape(n, len(names))
    return dict(zip(names, arr.T)), n


# ---------------------------------------------------------------- anatomy
def _inflation(a: np.ndarray) -> float:
    """span_full / span_p0.1 —— 与 tail_census.py 的 q0.1 定义一致。"""
    full = float(a.max() - a.min())
    lo, hi = np.percentile(a, 0.1), np.percentile(a, 99.9)
    rob = float(hi - lo)
    return full / rob if rob > 0 else float("nan")


def anatomy(D: dict, n: int, xyz_fields: tuple[str, str, str],
            rot_fields: tuple[str, str, str, str]) -> dict:
    out: dict = {"n": n}

    xyz = np.stack([D[k] for k in xyz_fields], 1).astype(np.float64)
    out["infl_xyz"] = _inflation(xyz)

    sc = np.stack([D["scale_0"], D["scale_1"], D["scale_2"]], 1).astype(np.float64)
    out["infl_scale"] = _inflation(sc)

    aniso = sc.max(1) - sc.min(1)          # log 域 ⇒ log(s_max/s_min)
    out["iso_frac"] = float((aniso < 0.1).mean())
    out["aniso_median"] = float(np.median(aniso))
    out["aniso_mean"] = float(aniso.mean())

    q = np.stack([D[k] for k in rot_fields], 1).astype(np.float64)
    nrm = np.linalg.norm(q, axis=1)
    out["rot_dev_frac"] = float((np.abs(nrm - 1) > 0.01).mean())
    out["rot_norm_min"] = float(nrm.min())
    out["rot_norm_max"] = float(nrm.max())

    # 簿记字段常值性（仅本栈 schema 存在；DynaGSLAM 无此字段）
    consts = {}
    for f in ("static_prob", "static_obs_count", "unmapped_score", "nx", "ny", "nz"):
        if f in D:
            consts[f] = float(np.std(D[f]))
    out["bookkeeping_std"] = consts
    return out


OUR_XYZ = ("x", "y", "z")
OUR_ROT = ("rot_0", "rot_1", "rot_2", "rot_3")
DGS_XYZ = ("x000", "y000", "z000")          # 第 0 时刻（静态几何）
DGS_ROT = ("rot_000_0", "rot_000_1", "rot_000_2", "rot_000_3")


# ---------------------------------------------------------------- panels
def panel_ours_dynamic() -> list[dict]:
    rows = []
    for seq in BONN_SEQS:
        for arm in ("baseline", "final"):
            g = glob.glob(str(REPO / f"results/paper2_fulltable/{seq}_{arm}_seed0/"
                                      f"datasets_bonn/*/seed_0/*/point_cloud/final/point_cloud.ply"))
            if not g:
                continue
            D, n = load_ply(g[0])
            r = anatomy(D, n, OUR_XYZ, OUR_ROT)
            r.update(panel="ours_dynamic", seq=seq, arm=arm)
            rows.append(r)
    return rows


def panel_ours_heldout() -> list[dict]:
    """L3 held-out：run_dir 取自 rd_table，逐 (run_dir) 去重。"""
    rows, seen = [], set()
    for f in sorted(glob.glob(str(REPO / "results/gs_compress/evidence/rd/L3*_rd_table.json"))):
        d = json.loads(Path(f).read_text())
        rd = d["run_dir"]
        if rd in seen:
            continue
        seen.add(rd)
        ply = Path(rd) / "point_cloud/final/point_cloud.ply"
        if not ply.exists():
            continue
        tag = Path(f).name.replace("_rd_table.json", "")
        parts = tag.split("_")
        seq = "_".join(parts[1:-2]) if len(parts) > 3 else tag
        D, n = load_ply(str(ply))
        r = anatomy(D, n, OUR_XYZ, OUR_ROT)
        r.update(panel="ours_heldout", seq=seq, arm=parts[-2])
        rows.append(r)
    return rows


def panel_dynagslam(seeds=(0,)) -> list[dict]:
    rows = []
    for seed in seeds:
        pat = str(DYNAGSLAM_ROOT / f"BONN/*/seed{seed}/save_model/final/iter_final.ply")
        for p in sorted(glob.glob(pat)):
            seq = Path(p).parents[3].name
            D, n = load_ply(p)
            r = anatomy(D, n, DGS_XYZ, DGS_ROT)
            r.update(panel="dynagslam", seq=seq, arm=f"seed{seed}")
            rows.append(r)
    return rows


# ---------------------------------------------------------------- report
def summarise(rows: list[dict]) -> str:
    from collections import defaultdict
    agg: dict = defaultdict(list)
    for r in rows:
        agg[(r["panel"], r["seq"])].append(r)

    lines = ["| panel | seq | n | infl_scale | infl_xyz | iso_frac | aniso_med | rot_dev |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    order = {"ours_dynamic": 0, "ours_heldout": 1, "dynagslam": 2}
    for (panel, seq) in sorted(agg, key=lambda k: (order.get(k[0], 9), k[1])):
        rs = agg[(panel, seq)]
        m = lambda k: float(np.nanmean([x[k] for x in rs]))
        lines.append(f"| {panel} | {seq} | {int(m('n'))} | {m('infl_scale'):.3f} | "
                     f"{m('infl_xyz'):.3f} | {m('iso_frac'):.3f} | "
                     f"{m('aniso_median'):.3f} | {m('rot_dev_frac'):.3f} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panels", default="ours_dynamic,ours_heldout,dynagslam")
    ap.add_argument("--dgs-seeds", default="0")
    args = ap.parse_args()

    want = set(args.panels.split(","))
    rows: list[dict] = []
    if "ours_dynamic" in want:
        rows += panel_ours_dynamic()
    if "ours_heldout" in want:
        rows += panel_ours_heldout()
    if "dynagslam" in want:
        rows += panel_dynagslam(tuple(int(s) for s in args.dgs_seeds.split(",")))

    OUT_JSON.write_text(json.dumps(rows, indent=1))
    table = summarise(rows)
    md = [
        "# §4 解剖统计普查（2026-10-22）",
        "",
        "> **用途**：补齐 §4 中此前无生成脚本的两项（各向同性占比、四元数偏离单位模），",
        "> 并提供跨系统与静态场景对照。零 GPU，只读 PLY。",
        "> **工件**：`anatomy_census.json`；生成器：`scripts/gs_compress/anatomy_census.py`。",
        "",
        "口径：scale 为 log 域（PLY 直存 log-scale）；`iso_frac` = aniso<0.1 的基元占比，",
        "aniso = log s_max − log s_min；`rot_dev` = |‖q‖−1|>1% 的基元占比；",
        "`infl_*` = span_full / span_p0.1（与 `tail_census.py` 同定义）。",
        "DynaGSLAM 取第 0 时刻位置 `x000..` 与 `rot_000_*`（其 79 字段 schema 无簿记字段）。",
        "",
        table,
        "",
        "**读法边界**：本栈与 DynaGSLAM 是两个不同实现，差别不止一处（loss、densify 策略、",
        "时间参数化）；表内差异是描述性的，不作单变量因果归因。",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(table)
    print(f"\nwrote {OUT_JSON}\nwrote {OUT_MD}")


if __name__ == "__main__":
    main()
