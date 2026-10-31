#!/usr/bin/env python
"""ratio_4d_12bit.py — 4D 层序列 codec 12bit 工作点压缩比（2026-10-13）。

口径 = /tmp/probe_4d_v3_ratio.py 逐字同构（该脚本产出报告 7.12/8.12× 等既有数字）：
  逐帧：排除抑制（1bit 标记）→ 持续基元 xyz 常速度残差量化 + 其余属性绝对量化
        （rot 先 rot3 归一化取 3 分量）→ 全部字节流 zlib 压缩；
  ratio = Σ 原始属性字节（float32） / Σ 压缩字节。
bits = 12,12,12,12,12（12bit 工作点）。
输出 JSON 到 evidence_4d12bit/（fig7 数据源 + 报告引用）。
"""
import json
import sys
import zlib
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

_ATTRS = ["xyz", "log_scale", "rot", "opa", "f_dc"]
import sys as _s; B = [int(x) for x in (_s.argv[1] if len(_s.argv)>1 else "12,12,12,12,12").split(",")]
MATCH_THR = 0.03


def quantize(v, bits, lo, hi):
    level = (1 << bits) - 1
    span = max(hi - lo, 1e-9)
    q = np.round(np.clip((v - lo) / span, 0, 1) * level)
    return q.astype(np.uint16) if bits > 8 else q.astype(np.uint8)


def rot3e(v):
    n = np.linalg.norm(v, axis=1, keepdims=True)
    return (v / np.maximum(n, 1e-12))[:, :3]


def bidi_match(xa, xb, thr=MATCH_THR):
    if len(xa) == 0 or len(xb) == 0:
        return None, None
    d_ab, ii_ab = cKDTree(xb).query(xa, k=1)
    d_ba, ii_ba = cKDTree(xa).query(xb, k=1)
    bidi = np.zeros(len(xa), bool)
    for j in np.unique(ii_ab):
        for si in np.nonzero(ii_ab == j)[0]:
            if ii_ba[j] == si and d_ab[si] < thr:
                bidi[si] = True
    return np.nonzero(bidi)[0], ii_ab


ROOTS = {
    "crowd2_R1": REPO / "results/dynport_offline/L1_v4/crowd2_R1",
    "crowd_R1": REPO / "results/dynport_offline/L2/crowd_R1",
    "balloon2_R1": REPO / "results/dynport_offline/L1_v4/balloon2_R1",
    "person_tracking_R1": REPO / "results/dynport_offline/L2/person_tracking_R1",
}

out = {}
for seq, root in ROOTS.items():
    cdir = root / "dynport_causal"
    snaps = sorted(cdir.glob("frame_*.npz"))
    total_raw = 0
    total_comp = 0
    prev_data, prev_vel = None, None
    for p in snaps:
        d = np.load(p)
        total_raw += sum(len(d[a].tobytes()) for a in _ATTRS)
        opa = d["opa"].reshape(-1)
        alive = opa > -10.0
        n_vis = int(alive.sum())
        raw = bytearray(np.packbits(alive))
        if n_vis == 0:
            total_comp += len(zlib.compress(bytes(raw), 6))
            continue
        cur = {a: d[a][alive] for a in _ATTRS}
        if prev_data is None:
            for ai, attr in enumerate(_ATTRS):
                v = cur[attr].astype(np.float64)
                if attr == "rot":
                    v = rot3e(v)
                lo, hi = np.percentile(v, [1, 99])
                q = quantize(v, B[ai], lo, hi)
                raw += q.astype(np.uint16).tobytes() if B[ai] > 8 else q.tobytes()
            total_comp += len(zlib.compress(bytes(raw), 6))
            prev_vel = np.zeros((n_vis, 3), np.float64)
        else:
            mi, ii_ab = bidi_match(prev_data["xyz"], cur["xyz"])
            if mi is not None and len(mi) > 0:
                pred = prev_data["xyz"][mi].astype(np.float64) + prev_vel[mi]
                actual = cur["xyz"][ii_ab[mi]].astype(np.float64)
                resid = actual - pred
                lo, hi = np.percentile(resid, [1, 99])
                q = quantize(resid, B[0], lo, hi)
                raw += q.astype(np.uint16).tobytes() if B[0] > 8 else q.tobytes()
                new_vel = np.zeros((n_vis, 3), np.float64)
                new_vel[ii_ab[mi]] = actual - prev_data["xyz"][mi].astype(np.float64)
                prev_vel = new_vel
                for ai, attr in enumerate(["log_scale", "rot", "opa", "f_dc"]):
                    v = cur[attr][ii_ab[mi]].astype(np.float64)
                    if attr == "rot":
                        v = rot3e(v)
                    lo, hi = np.percentile(v, [1, 99])
                    q = quantize(v, B[ai + 1], lo, hi)
                    raw += q.astype(np.uint16).tobytes() if B[ai + 1] > 8 else q.tobytes()
                matched_b = np.zeros(n_vis, bool)
                matched_b[ii_ab[mi]] = True
                rest = np.nonzero(~matched_b)[0]
                if len(rest):
                    for ai, attr in enumerate(_ATTRS):
                        v = cur[attr][rest].astype(np.float64)
                        if attr == "rot":
                            v = rot3e(v)
                        lo, hi = np.percentile(v, [1, 99])
                        q = quantize(v, B[ai], lo, hi)
                        raw += q.astype(np.uint16).tobytes() if B[ai] > 8 else q.tobytes()
            else:
                for ai, attr in enumerate(_ATTRS):
                    v = cur[attr].astype(np.float64)
                    if attr == "rot":
                        v = rot3e(v)
                    lo, hi = np.percentile(v, [1, 99])
                    q = quantize(v, B[ai], lo, hi)
                    raw += q.astype(np.uint16).tobytes() if B[ai] > 8 else q.tobytes()
                prev_vel = np.zeros((n_vis, 3), np.float64)
            total_comp += len(zlib.compress(bytes(raw), 6))
        prev_data = cur
    ratio = total_raw / max(total_comp, 1)
    out[seq] = {"n_snapshots": len(snaps), "raw_bytes": total_raw,
                "comp_bytes": total_comp, "ratio": round(ratio, 3)}
    print(f"{seq:<22} {len(snaps):>4} snapshots  raw={total_raw/1e6:7.2f}MB  "
          f"comp={total_comp/1e6:6.2f}MB  ratio={ratio:.2f}x")

Path(REPO / "results/dynport_offline/evidence_4d12bit/ratio_{}.json").write_text(
    json.dumps(out, indent=1))
print("saved → results/dynport_offline/evidence_4d12bit/ratio_{}.json")
