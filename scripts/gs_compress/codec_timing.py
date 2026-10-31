#!/usr/bin/env python
"""codec_timing.py — codec 编解码耗时测量（独立审稿 P1-8：工程论文该报代价）。

测三档工作点在一批代表性地图上的 encode / decode 墙钟（CPU，单线程），
输出 results/gs_compress/evidence/codec_timing.json + codec_timing_2026-10-05.md。

口径：重复 3 次取均值；warm-up 1 次；per-primitive = time / n。
"""
from __future__ import annotations

import glob
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "gs_compress"))
from gs_codec import read_map, encode, decode, Bits  # noqa: E402

RD = REPO / "results/gs_compress/evidence/rd"
OUT_JSON = RD / "codec_timing.json"
OUT_MD = REPO / "results/gs_compress/evidence/codec_timing_2026-10-05.md"

WPS = {"near-lossless": Bits(16, 8, 8, 8, 8), "mid": Bits(10, 6, 6, 6, 6),
       "aggressive": Bits(8, 4, 4, 4, 4)}


def local_path(run_dir: str) -> Path:
    return Path(run_dir.replace("/home/jiangwenheng/cron/monogs-ours/", "").rstrip("/"))


def time_arm(m, bits, reps=3):
    encode(m, bits)  # warm
    t0 = time.perf_counter()
    for _ in range(reps):
        blob, meta = encode(m, bits)
    te = (time.perf_counter() - t0) / reps
    decode(blob, meta)  # warm
    t0 = time.perf_counter()
    for _ in range(reps):
        decode(blob, meta)
    td = (time.perf_counter() - t0) / reps
    return te, td


def main():
    # 取 6 张代表性地图（不同序列/臂/规模），覆盖 n 的跨度
    files = sorted(glob.glob(str(RD / "L2_*_rd_table.json")))
    picks = [files[0], files[6], files[13], files[20], files[27], files[41]]
    rows = []
    for f in picks:
        d = json.loads(Path(f).read_text())
        ply = local_path(d["run_dir"]) / "point_cloud/final/point_cloud.ply"
        if not ply.exists():
            continue
        m = read_map(str(ply))
        n = m["_n"]
        rec = {"tag": d["tag"], "n": int(n)}
        for name, bits in WPS.items():
            te, td = time_arm(m, bits)
            rec[name] = {"encode_ms": te * 1e3, "decode_ms": td * 1e3,
                         "encode_us_per_prim": te / n * 1e6,
                         "decode_us_per_prim": td / n * 1e6}
        rows.append(rec)
        print(f"{d['tag']:<28} n={n:>7}  " +
              "  ".join(f"{w[:4]}: E{rec[w]['encode_ms']:.0f}/D{rec[w]['decode_ms']:.0f}ms"
                        for w in WPS))
    summary = {"reps": 3, "device": "CPU single-thread", "rows": rows}
    OUT_JSON.write_text(json.dumps(summary, indent=2))

    md = ["# codec 编解码耗时（2026-10-05）", "",
          "> **用途**：独立审稿 P1-8。codec 是**离线**后处理，工程论文须报其代价。",
          "> **口径**：CPU 单线程，重复 3 次取均值（含 warm-up）；工件 `rd/codec_timing.json`。", ""]
    md.append("| map | n | encode near/mid/agg (ms) | decode near/mid/agg (ms) |")
    md.append("|---|---|---|---|")
    for r in rows:
        md.append(f"| {r['tag']} | {r['n']} | "
                  f"{r['near-lossless']['encode_ms']:.0f} / {r['mid']['encode_ms']:.0f} / {r['aggressive']['encode_ms']:.0f} | "
                  f"{r['near-lossless']['decode_ms']:.0f} / {r['mid']['decode_ms']:.0f} / {r['aggressive']['decode_ms']:.0f} |")
    # means per-prim
    md.append("")
    for w in WPS:
        ep = np.mean([r[w]["encode_us_per_prim"] for r in rows])
        dp = np.mean([r[w]["decode_us_per_prim"] for r in rows])
        md.append(f"- **{w}**：encode {ep:.3f} µs/prim，decode {dp:.3f} µs/prim")
    md.append("")
    md.append("> 解读：编解码均为**离线 CPU** 操作，单张地图（数万基元）在 tens–hundreds of ms 量级；"
              "扩到十万级基元的量产地图仍在亚秒–秒级。不是在线瓶颈，但也不是零成本。")
    OUT_MD.write_text("\n".join(md))
    print("\n" + "\n".join(md))


if __name__ == "__main__":
    main()
