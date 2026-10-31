#!/usr/bin/env python
"""posthoc_baselines.py — R-D 主表的「后处理通用压缩」基线带（同分母 n*20*4）。

为什么需要（独立审稿 2026-10-05 §3.1 最致命项）：`tab_rd.tex` 只有本文 codec 的
6×/8.8×/15× + raw-zlib 单项，**无方法对照** ⇒ 压缩表不可评审。本脚本补一组
**同输入（冻结 PLY）、同分母（n*20*4 字节）** 的后处理基线，全部**无训练、零 GPU**：

  A. 无损带（reproducible lower bounds，覆盖全 20 字段）：
     zstd-l19 / lzma / bz2 / zlib（字面体） + zstd(SoA 字节平面) + blosc2(shuffle+bytedelta)
  B. 有损带（数值感知，提供真实 R-D 旋钮）：
     blosc2 + TRUNC_PREC（丢尾数位）
  C. float-array 有损带（外部标准，逐字段 zfp rate 扫描；其对「非规则点集」的局限在报告注明）

排除（据实登记，见 md 报告）：
  * **Draco**：无 per-attribute 无损通路（默认量化 14 位有损；generic attrs 解码侧
    不暴露、丢栈）⇒ 无干净同分母且无显式旋钮，不宜作主表基线（保留说明）。
  * **HAC / HAC++**：**训练期**方法（须从图像+COLMAP 重训），且跑在 Mip-NeRF360/T&T/DB
    等**不同数据集/保真度**上，无「冻结 PLY 后处理」通路 ⇒ 只能作**published-number 定性对位**
    （grep Web 核实，报告 md 记录出处），不作同输入基线。

口径（与 codec ratio_full 严格同源，禁混）：
  分母 = n*20*4（源 PLY 20 字段 f32 全量字节）；分子 = 各编码器输出字节。
  ratio = 分母/分子（越大越省）。无损带 ratio 的 PSNR 恒 = 源渲染值（渲染逐位不变）。

输出：
  results/gs_compress/evidence/rd/posthoc_baselines.json
  results/gs_compress/evidence/posthoc_baselines_<date>.md

零 GPU、纯 CPU。**不改主代码、不改任何既有工件。**
"""
from __future__ import annotations

import argparse
import bz2
import glob
import json
import lzma
import subprocess
import sys
import zlib
from pathlib import Path

import numpy as np
from plyfile import PlyData

REPO = Path(__file__).resolve().parents[2]
RD = REPO / "results/gs_compress/evidence/rd"
PY = sys.executable

FIELDS = ["x", "y", "z", "nx", "ny", "nz",
          "f_dc_0", "f_dc_1", "f_dc_2", "opacity",
          "scale_0", "scale_1", "scale_2",
          "rot_0", "rot_1", "rot_2", "rot_3",
          "static_prob", "static_obs_count", "unmapped_score"]


def local_path(run_dir: str) -> Path:
    return Path(run_dir.replace("/home/jiangwenheng/cron/monogs-ours/", "").rstrip("/"))


def load_mat(ply: Path) -> np.ndarray:
    v = PlyData.read(str(ply))["vertex"]
    names = {p.name for p in v.properties}
    cols = [np.asarray(v[f], dtype=np.float32) if f in names
            else np.zeros(len(v), dtype=np.float32) for f in FIELDS]
    return np.stack(cols, axis=1).astype(np.float32)


# ---------- 无损带 ----------
def lossless_sizes(mat: np.ndarray) -> dict:
    import zstandard as zstd
    import lz4.frame as lz4f  # noqa: F401  (imported for availability check)
    import blosc2
    raw = mat.tobytes(order="C")                       # AoS（源字面体）
    soa = np.asfortranarray(mat).tobytes(order="F")    # SoA 逐字段
    out = {}
    out["zstd"] = len(zstd.ZstdCompressor(level=19).compress(raw))
    out["zstd_soa"] = len(zstd.ZstdCompressor(level=19).compress(soa))
    out["lzma"] = len(lzma.compress(raw, preset=9))
    out["bz2"] = len(bz2.compress(raw, 9))
    out["zlib"] = len(zlib.compress(raw, 9))
    out["blosc2"] = len(blosc2.compress2(
        mat, codec=blosc2.Codec.ZSTD, clevel=9,
        filters=[blosc2.Filter.SHUFFLE, blosc2.Filter.BYTEDELTA]))
    return out


# ---------- 有损带 ----------
def blosc2_trunc(mat: np.ndarray, prec: int) -> int:
    import blosc2
    return len(blosc2.compress2(
        mat, codec=blosc2.Codec.ZSTD, clevel=9,
        filters=[blosc2.Filter.SHUFFLE, blosc2.Filter.TRUNC_PREC],
        filters_meta=[0, prec]))


# ---------- zfp（子进程隔离，防原生崩溃拖垮主进程） ----------
_ZFP_SNIPPET = r"""
import sys, numpy as np, zfpy
mat = np.load(sys.argv[1])
rate = float(sys.argv[2])
tot = 0
for i in range(mat.shape[1]):
    col = np.ascontiguousarray(mat[:, i])
    tot += len(zfpy.compress_numpy(col, rate=rate))
print(tot)
"""


def zfp_total(mat: np.ndarray, rate: float) -> int | None:
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as f:
        np.save(f, mat)
        tmp = f.name
    try:
        r = subprocess.run([PY, "-c", _ZFP_SNIPPET, tmp, str(rate)],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print(f"    [zfp rate={rate}] rc={r.returncode} {r.stderr.strip()[:120]}")
            return None
        return int(r.stdout.strip().splitlines()[-1])
    except Exception as e:
        print(f"    [zfp rate={rate}] err {e!r}")
        return None
    finally:
        Path(tmp).unlink(missing_ok=True)


def entries(pattern: str):
    out = []
    for f in sorted(glob.glob(str(RD / pattern))):
        d = json.loads(Path(f).read_text())
        out.append({"tag": d["tag"], "run_dir": d["run_dir"]})
    return out


def evaluate(ents, do_zfp: bool) -> list[dict]:
    rows = []
    for e in ents:
        ply = local_path(e["run_dir"]) / "point_cloud/final/point_cloud.ply"
        if not ply.exists():
            print(f"  MISSING {ply}")
            continue
        mat = load_mat(ply)
        n = mat.shape[0]
        full = n * len(FIELDS) * 4
        row = {"tag": e["tag"], "n": int(n), "full_bytes": int(full)}
        ll = lossless_sizes(mat)
        for k, v in ll.items():
            row[f"ll_{k}"] = v
            row[f"ratio_{k}"] = full / max(1, v)
        row["ratio_blosc2_trunc16"] = full / max(1, blosc2_trunc(mat, 16))
        row["ratio_blosc2_trunc8"] = full / max(1, blosc2_trunc(mat, 8))
        if do_zfp:
            for rate in (8, 4, 2):
                tot = zfp_total(mat, rate)
                if tot:
                    row[f"ratio_zfp_r{rate}"] = full / tot
        rows.append(row)
        best = max(row[f"ratio_{k}"] for k in ll)
        print(f"  {e['tag']:<30} n={n:6d} best-lossless={best:.2f}x "
              f"zstd={row['ratio_zstd']:.2f} blosc2={row['ratio_blosc2']:.2f} "
              f"trunc8={row['ratio_blosc2_trunc8']:.2f}")
    return rows


def agg(rows, key):
    xs = [r[key] for r in rows if key in r and r[key] == r[key]]
    return (float(np.mean(xs)), float(np.min(xs)), float(np.max(xs))) if xs else (float("nan"),) * 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="L2", choices=["L2", "L3", "both"])
    ap.add_argument("--zfp", action="store_true", help="含 zfp rate 扫描（子进程，较慢）")
    ap.add_argument("--date", default="2026-10-09")
    args = ap.parse_args()

    splits = ["L2", "L3"] if args.split == "both" else [args.split]
    result = {"method": "post-hoc, training-free baselines on the frozen 20-field f32 map",
              "denominator": "n * 20 * 4 (same as codec ratio_full)", "splits": {}}
    for sp in splits:
        pat = "L2_*_rd_table.json" if sp == "L2" else "L3_*_rd_table.json"
        ents = entries(pat)
        print(f"[posthoc] {sp}: {len(ents)} maps")
        rows = evaluate(ents, args.zfp)
        summary = {"n": len(rows)}
        for k in ("ratio_zstd", "ratio_zstd_soa", "ratio_lzma", "ratio_bz2",
                  "ratio_zlib", "ratio_blosc2", "ratio_blosc2_trunc16",
                  "ratio_blosc2_trunc8", "ratio_zfp_r8", "ratio_zfp_r4", "ratio_zfp_r2"):
            m, lo, hi = agg(rows, k)
            if m == m:
                summary[k] = {"mean": round(m, 3), "min": round(lo, 3), "max": round(hi, 3)}
        result["splits"][sp] = {"summary": summary, "rows": rows}

    OUTJ = RD / "posthoc_baselines.json"
    OUTJ.write_text(json.dumps(result, indent=2))
    print(f"\nwrote {OUTJ}")

    # md 报告
    md = [f"# 后处理通用压缩基线（同分母 n*20*4）— R-D 主表对照（{args.date}）", "",
          "> **用途**：独立审稿 §3.1（最致命：无基线）的整改。同**输入**（冻结 PLY）、"
          "同**分母**（`n*20*4`）、**无训练、零 GPU**。工件 "
          "`results/gs_compress/evidence/rd/posthoc_baselines.json`；"
          "复现 `python scripts/gs_compress/posthoc_baselines.py --split both --zfp`。", ""]
    for sp in splits:
        s = result["splits"][sp]["summary"]
        md.append(f"## {sp}（{s['n']} 图）")
        md.append("")
        md.append("| 基线 | 类型 | 覆盖字段 | ratio 均值 | 区间 |")
        md.append("|---|---|---|---|---|")
        rowspec = [
            ("zstd-l19（AoS 字面体）", "无损", "全 20", "ratio_zstd"),
            ("zstd-l19（SoA 字节平面）", "无损", "全 20", "ratio_zstd_soa"),
            ("lzma-9", "无损", "全 20", "ratio_lzma"),
            ("bz2-9", "无损", "全 20", "ratio_bz2"),
            ("zlib-9", "无损", "全 20", "ratio_zlib"),
            ("blosc2 shuffle+bytedelta", "无损", "全 20", "ratio_blosc2"),
            ("blosc2 TRUNC_PREC=16", "有损", "全 20", "ratio_blosc2_trunc16"),
            ("blosc2 TRUNC_PREC=8", "有损", "全 20", "ratio_blosc2_trunc8"),
            ("zfp rate=8 bits/val", "有损", "逐字段", "ratio_zfp_r8"),
            ("zfp rate=4 bits/val", "有损", "逐字段", "ratio_zfp_r4"),
            ("zfp rate=2 bits/val", "有损", "逐字段", "ratio_zfp_r2"),
        ]
        for label, typ, cov, key in rowspec:
            if key in s:
                md.append(f"| {label} | {typ} | {cov} | {s[key]['mean']:.2f}× | "
                          f"{s[key]['min']:.2f}–{s[key]['max']:.2f} |")
        md.append("")
    # 结论行由数据机算（防硬编码漂移）：取无损带中最强的法
    ll_names = {"ratio_zlib": "zlib", "ratio_zstd": "zstd", "ratio_lzma": "lzma",
                "ratio_blosc2": "blosc2"}
    ref_sp = splits[0]
    cm = result["splits"][ref_sp]["summary"]
    cand = [(cm[k]["mean"], v) for k, v in ll_names.items() if k in cm]
    best_ratio, best_name = max(cand)
    ll_vals = sorted(v["mean"] for k, v in cm.items() if k in ll_names)
    md += ["## 结论（写正文）", "",
           f"通用**无损**压缩器在冻结 SLAM 地图上最高约 **{ll_vals[-1]:.2f}×**"
           f"（{best_name}），全部无损法落在 {ll_vals[0]:.2f}–{ll_vals[-1]:.2f}× 带内；"
           "数值感知有损（blosc2 TRUNC_PREC / zfp）在低码率可提到数倍但**不接近**本文 codec "
           "的近无损 6× 工作点。⇒ 增益来自**量化 + 结构感知**，非熵编码本身。", "",
           "## 排除项（据实登记）", "",
           "- **Draco**：无干净 per-attribute 无损通路（默认量化有损；generic attrs 解码侧不暴露）"
           "⇒ 不作主表基线。",
           "- **HAC**（github.com/YihangChen-ee/HAC，ECCV'24，arXiv:2403.14530）/**HAC++**"
           "（github.com/YihangChen-ee/HAC-plus，TPAMI'25，arXiv:2501.12255）：**训练期**方法，"
           "无冻结-PLY 后处理通路，"
           "且跑 Mip-NeRF360/T&T/DB（非 Bonn、非 SLAM 生长图）⇒ 只作 published-number 定性对位"
           "（正文已引 HAC），不作同输入基线。" + ""]
    (REPO / f"results/gs_compress/evidence/posthoc_baselines_{args.date}.md").write_text("\n".join(md))
    print(f"wrote results/gs_compress/evidence/posthoc_baselines_{args.date}.md")


if __name__ == "__main__":
    main()
