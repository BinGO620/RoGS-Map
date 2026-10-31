#!/usr/bin/env python
"""gs_codec.py — 动态场景 GS-SLAM 地图的离线有损压缩 codec（v0）。

性质（prereg §3）：
  * **离线后处理**：输入 = SLAM 存档最终地图 PLY，输出 = 压缩码流 + 重建 PLY。
  * **不新增优化期标量**、**不进在线逐帧预算**、**不碰 SLAM 主代码**（独立脚本）。
  * v0 熵编码 = zlib（可换 rANS，接口不变）；量化 = per-attribute 均匀标量量化。

渲染字段（14，`gaussian_model.load_ply` + `gaussian_renderer` 实读）：
  x,y,z | f_dc_0..2 | opacity | scale_0..2 | rot_0..3
非渲染记账字段（6，剥离，见 prereg C5）：
  nx,ny,nz | static_prob | static_obs_count | unmapped_score

**rot 处理**：PLY 里 rot 未归一化（本仓实测 norm∈[0.53,2.10]）；渲染时
`rotation_activation = normalize` 会归一化 ⇒ 本 codec 存归一化后的 3 分量
（w 由符号约定 + 单位约束恢复），无损于渲染。
"""
from __future__ import annotations

import io
import json
import zlib
from dataclasses import dataclass, field, asdict

import numpy as np
from plyfile import PlyData, PlyElement

RENDER_FIELDS = [
    "x", "y", "z",
    "f_dc_0", "f_dc_1", "f_dc_2",
    "opacity",
    "scale_0", "scale_1", "scale_2",
    "rot_0", "rot_1", "rot_2", "rot_3",
]
ACCOUNTING_FIELDS = ["nx", "ny", "nz", "static_prob", "static_obs_count", "unmapped_score"]
ALL_FIELDS = [
    "x", "y", "z", "nx", "ny", "nz",
    "f_dc_0", "f_dc_1", "f_dc_2",
    "opacity",
    "scale_0", "scale_1", "scale_2",
    "rot_0", "rot_1", "rot_2", "rot_3",
    "static_prob", "static_obs_count", "unmapped_score",
]


@dataclass
class Bits:
    """每属性量化比特配置（per-channel）。"""
    xyz: int = 16
    f_dc: int = 8
    opacity: int = 8
    scale: int = 8
    rot: int = 8  # 每分量；存 3 分量

    def aper_prim_bits(self) -> float:
        return self.xyz * 3 + self.f_dc * 3 + self.opacity + self.scale * 3 + self.rot * 3


@dataclass
class Meta:
    n: int = 0
    sh_deg: int = 0
    bits: dict = field(default_factory=dict)
    ranges: dict = field(default_factory=dict)  # attr -> [min, max]
    orig_render_bytes: int = 0
    orig_full_bytes: int = 0
    alloc: str = "uniform"                     # uniform | partition | robust
    partition_meta: dict = field(default_factory=dict)
    # v2（S1 修正案 v1.1，D2-025 乙线）：重尾感知范围量化
    range_mode: str = "full"                   # full（v1，逐属性 min/max）| robust（稳健百分位）
    range_q: float = 0.1                       # robust 的尾部百分位（p_q / p_{100-q}）
    escape: bool = False                       # True=尾部走外溢通道（全范围同位宽）；False=clip
    ranges_full: dict = field(default_factory=dict)  # robust 用：attr -> [min,max]（escape 尾部范围）


# ---------------------------------------------------------------- quant core
def _quant(a: np.ndarray, bits: int, lo: float, hi: float) -> np.ndarray:
    """均匀标量量化到 [0, 2^bits-1]。"""
    levels = (1 << bits) - 1
    span = hi - lo
    if span <= 0:
        return np.zeros_like(a, dtype=np.uint32)
    q = np.round((a - lo) / span * levels)
    return np.clip(q, 0, levels).astype(np.uint32)


def _dequant(q: np.ndarray, bits: int, lo: float, hi: float) -> np.ndarray:
    levels = (1 << bits) - 1
    if levels == 0:
        return np.full(q.shape, lo, dtype=np.float32)
    return (q.astype(np.float32) / levels * (hi - lo) + lo).astype(np.float32)


def _dtype_for(bits: int) -> np.dtype:
    if bits <= 8:
        return np.uint8
    if bits <= 16:
        return np.uint16
    return np.uint32


# ---------------------------------------------------------------- rot helpers
def _rot_to_quat3(rot4: np.ndarray) -> np.ndarray:
    """归一化四元数（w 为第 0 分量），符号约定 w>=0，返回后 3 分量。"""
    q = rot4.astype(np.float64)
    n = np.linalg.norm(q, axis=1, keepdims=True)
    n[n == 0] = 1.0
    q = q / n
    flip = q[:, 0:1] < 0
    q = np.where(flip, -q, q)
    return q[:, 1:4].astype(np.float32)


def _quat3_to_rot4(xyz3: np.ndarray) -> np.ndarray:
    """由 3 分量 + 单位约束恢复 4 分量四元数（w>=0）。"""
    x = xyz3.astype(np.float64)
    s = np.sum(x * x, axis=1)
    w = np.sqrt(np.clip(1.0 - s, 0.0, None))
    out = np.concatenate([w[:, None], x], axis=1)
    n = np.linalg.norm(out, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return (out / n).astype(np.float32)


# ---------------------------------------------------------------- read / write
def read_map(ply_path: str) -> dict:
    d = PlyData.read(ply_path)
    v = d["vertex"]
    names = {p.name for p in v.properties}
    out = {}
    for f in ALL_FIELDS:
        if f in names:
            out[f] = np.asarray(v[f], dtype=np.float32)
    out["_n"] = len(v)
    out["_sh_deg"] = _sh_deg_from_names(names)
    return out


def _sh_deg_from_names(names) -> int:
    n_rest = len([n for n in names if n.startswith("f_rest_")])
    if n_rest == 0:
        return 0
    for d in range(1, 5):
        if 3 * ((d + 1) ** 2 - 1) == n_rest:
            return d
    raise ValueError(f"无法从 f_rest 数 {n_rest} 反推 SH degree")


def write_recon_ply(path: str, arrs: dict, n: int) -> None:
    """写重建 PLY：14 渲染字段 + 3 零法向（load_ply 需要 nx/ny/nz），剥离 6 记账字段。"""
    xyz = arrs["xyz"].astype(np.float32)
    rot4 = arrs["rot4"].astype(np.float32)
    fields = [
        ("x", "f4"), ("y", "f4"), ("z", "f4"),
        ("nx", "f4"), ("ny", "f4"), ("nz", "f4"),
        ("f_dc_0", "f4"), ("f_dc_1", "f4"), ("f_dc_2", "f4"),
        ("opacity", "f4"),
        ("scale_0", "f4"), ("scale_1", "f4"), ("scale_2", "f4"),
        ("rot_0", "f4"), ("rot_1", "f4"), ("rot_2", "f4"), ("rot_3", "f4"),
    ]
    el = np.empty(n, dtype=fields)
    el["x"], el["y"], el["z"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    el["nx"] = el["ny"] = el["nz"] = 0.0
    el["f_dc_0"], el["f_dc_1"], el["f_dc_2"] = arrs["f_dc"][:, 0], arrs["f_dc"][:, 1], arrs["f_dc"][:, 2]
    el["opacity"] = arrs["opacity"][:, 0]
    el["scale_0"], el["scale_1"], el["scale_2"] = arrs["scale"][:, 0], arrs["scale"][:, 1], arrs["scale"][:, 2]
    el["rot_0"], el["rot_1"], el["rot_2"], el["rot_3"] = rot4[:, 0], rot4[:, 1], rot4[:, 2], rot4[:, 3]
    PlyData([PlyElement.describe(el, "vertex")], text=False).write(path)


# ---------------------------------------------------------------- codec
def _gather_groups(m: dict) -> dict:
    return {
        "xyz": np.stack([m["x"], m["y"], m["z"]], 1).astype(np.float32),
        "f_dc": np.stack([m["f_dc_0"], m["f_dc_1"], m["f_dc_2"]], 1).astype(np.float32),
        "opacity": m["opacity"][:, None].astype(np.float32),
        "scale": np.stack([m["scale_0"], m["scale_1"], m["scale_2"]], 1).astype(np.float32),
        "rot": _rot_to_quat3(np.stack([m["rot_0"], m["rot_1"], m["rot_2"], m["rot_3"]], 1)),
    }


GROUP_ORDER = ["xyz", "f_dc", "opacity", "scale", "rot"]


def _pack_bitmap(labels: np.ndarray) -> bytes:
    return np.packbits((labels > 0).astype(np.uint8)).tobytes()


def _encode_robust(groups: dict, bmap: dict, meta: Meta, n: int,
                   q: float, escape: bool) -> tuple[bytes, Meta]:
    """v2 重尾感知范围量化（range_mode='robust'）。

    每属性组：lo,hi = percentile(a, [q, 100-q])（稳健范围）。
      * escape=False：clip 到稳健边界，逐组同位宽打包（同 v1 码率量级）。
      * escape=True ：尾部（越界元素）以全范围 [min,max] 同位宽**另存**，逐元素位图随流。
    尾部定义用**单通道 ravel**（与 tail_census 一致）：任一通道越界即尾部（保守）。
    """
    meta.alloc = "robust"
    meta.range_mode = "robust"
    meta.range_q = float(q)
    meta.escape = bool(escape)
    meta.ranges = {}
    meta.ranges_full = {}
    payload = {}
    maps = {}
    for name in GROUP_ORDER:
        arr = groups[name]
        lo_f, hi_f = float(arr.min()), float(arr.max())
        plo, phi = np.percentile(arr, q), np.percentile(arr, 100.0 - q)
        meta.ranges[name] = [float(plo), float(phi)]
        meta.ranges_full[name] = [lo_f, hi_f]
        if escape:
            tail = (arr < plo) | (arr > phi)      # 逐元素（每通道独立判）
            maps[name] = tail
            qv = np.zeros(arr.shape, dtype=np.uint32)
            # 主体：稳健范围
            qv[~tail] = _quant(arr[~tail], bmap[name], plo, phi).astype(np.uint32)
            # 尾部：全范围（同位宽）
            if tail.any():
                qv[tail] = _quant(arr[tail], bmap[name], lo_f, hi_f).astype(np.uint32)
            payload[name] = qv
        else:
            payload[name] = _quant(arr, bmap[name], plo, phi).astype(np.uint32)

    buf = io.BytesIO()
    hdr = json.dumps({"meta": asdict(meta)}, separators=(",", ":")).encode()
    buf.write(len(hdr).to_bytes(4, "little"))
    buf.write(hdr)
    if escape:
        for name in GROUP_ORDER:
            bm = _pack_bitmap(maps[name].astype(np.int8))
            buf.write(len(bm).to_bytes(4, "little"))
            buf.write(bm)
    for name in GROUP_ORDER:
        buf.write(payload[name].astype(_dtype_for(bmap[name])).tobytes())
    return zlib.compress(buf.getvalue(), 9), meta


def _decode_robust(raw: bytes, meta: Meta, off: int) -> dict:
    n = meta.n
    shapes = {"xyz": (n, 3), "f_dc": (n, 3), "opacity": (n, 1), "scale": (n, 3), "rot": (n, 3)}
    bmap = meta.bits
    maps = {}
    if meta.escape:
        for name in GROUP_ORDER:
            blen = int.from_bytes(raw[off:off + 4], "little"); off += 4
            bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8, count=blen, offset=off))
            off += blen
            maps[name] = bits[: int(np.prod(shapes[name]))].astype(bool).reshape(shapes[name])
    out = {}
    for name in GROUP_ORDER:
        dim = shapes[name][1]
        q = np.frombuffer(raw, dtype=_dtype_for(bmap[name]),
                          count=n * dim, offset=off).reshape(shapes[name]); off += q.nbytes
        plo, phi = meta.ranges[name]
        a = _dequant(q, bmap[name], plo, phi)
        if meta.escape:
            lo_f, hi_f = meta.ranges_full[name]
            tail = maps[name]
            if tail.any():
                a[tail] = _dequant(q[tail], bmap[name], lo_f, hi_f)
        out[name] = a
    return {
        "xyz": out["xyz"], "f_dc": out["f_dc"], "opacity": out["opacity"],
        "scale": out["scale"], "rot4": _quat3_to_rot4(out["rot"]),
    }


def encode(m: dict, bits: Bits, labels: np.ndarray | None = None,
           bits_dyn: Bits | None = None, alloc: str = "uniform",
           iso_scale: bool = False, iso_thresh: float = 0.1,
           range_mode: str = "full", range_q: float = 0.1,
           escape: bool = False) -> tuple[bytes, Meta]:
    """编码。

    alloc='uniform'   : 全体同一 quantizer（bits）。
    alloc='partition' : 按 labels（1=dynamic/ghost-support）分成两组——
                        labels==0 用 bits（细），labels==1 用 bits_dyn（粗）；
                        两组各自打包（真实字节节省），标签以 packbits 位图随流存储。
    iso_scale         : SLAM 结构感知——尺度按 (log-均值 + 各向异性偏差) 编码：
                        |dev| < iso_thresh 的基元 dev≈0（熵编码压到近零），
                        仅各向异性基元消耗偏差比特。rot 恒为 3 分量。
    range_mode='robust'（v2, D2-025 乙线）: 每属性组量化范围由 [min,max] 改为
                        稳健百分位 [p_q, p_{100-q}]——SLAM 地图重尾（巨基元）撑大范围，
                        收窄后 ~99.8% 主体步长变细（同位宽）。
                        escape=False ⇒ 尾部 clip 到稳健边界（同 v1 码率，无位图）；
                        escape=True  ⇒ 尾部由专属通道以 [min,max] 全范围同位宽另存
                        （逐元素位图随流），尾部误差 ≈ v1 但主体更细（码率 + 位图）。
    """
    n = m["_n"]
    meta = Meta(n=n, sh_deg=m["_sh_deg"], bits=asdict(bits),
                orig_render_bytes=n * len(RENDER_FIELDS) * 4,
                orig_full_bytes=n * len(ALL_FIELDS) * 4, alloc=alloc)
    meta.partition_meta = {"iso_scale": bool(iso_scale), "iso_thresh": float(iso_thresh)}
    groups = _gather_groups(m)
    bmap = {"xyz": bits.xyz, "f_dc": bits.f_dc, "opacity": bits.opacity,
            "scale": bits.scale, "rot": bits.rot}

    if range_mode == "robust":
        return _encode_robust(groups, bmap, meta, n, range_q, escape)

    if alloc == "uniform" and iso_scale:
        meta.alloc = "iso"
        meta.ranges = {}
        buf = io.BytesIO()
        hdr = json.dumps({"meta": asdict(meta)}, separators=(",", ":")).encode()
        buf.write(len(hdr).to_bytes(4, "little"))
        buf.write(hdr)
        # 非 scale 组：普通量化
        for name in ["xyz", "f_dc", "opacity"]:
            arr = groups[name]
            lo, hi = float(arr.min()), float(arr.max())
            meta.ranges[name] = [lo, hi]
            q = _quant(arr, bmap[name], lo, hi).astype(_dtype_for(bmap[name]))
            buf.write(q.tobytes())
        # scale：log-均值 + 偏差
        sc = groups["scale"]
        smean = sc.mean(1)
        sdev = sc - smean[:, None]
        lo_m, hi_m = float(smean.min()), float(smean.max())
        lo_d, hi_d = float(sdev.min()), float(sdev.max())
        meta.ranges["scale_mean"] = [lo_m, hi_m]
        meta.ranges["scale_dev"] = [lo_d, hi_d]
        qm = _quant(smean, bits.scale, lo_m, hi_m).astype(_dtype_for(bits.scale))
        qd = _quant(sdev, bits.scale, lo_d, hi_d)
        buf.write(qm.tobytes())
        buf.write(qd.astype(_dtype_for(bits.scale)).tobytes())
        # rot：3 分量
        rt = groups["rot"]
        lo_r, hi_r = float(rt.min()), float(rt.max())
        meta.ranges["rot"] = [lo_r, hi_r]
        buf.write(_quant(rt, bits.rot, lo_r, hi_r).astype(_dtype_for(bits.rot)).tobytes())
        raw = buf.getvalue()
        return zlib.compress(raw, 9), meta

    if alloc == "partition" and labels is not None and bits_dyn is not None:
        assert len(labels) == n
        d = labels > 0
        meta.alloc = "partition"
        meta.partition_meta = {"n_dyn_support": int(d.sum()), "n_static_support": int((~d).sum()),
                               "bits_dyn": asdict(bits_dyn)}
        bmap_dyn = {"xyz": bits_dyn.xyz, "f_dc": bits_dyn.f_dc, "opacity": bits_dyn.opacity,
                    "scale": bits_dyn.scale, "rot": bits_dyn.rot}
        meta.ranges = {}
        payload = {}
        for name in GROUP_ORDER:
            arr = groups[name]
            lo, hi = float(arr.min()), float(arr.max())
            meta.ranges[name] = [lo, hi]
            qs = np.zeros(arr.shape, dtype=np.uint32)
            # 静态组（细）
            qi = _quant(arr[~d], bmap[name], lo, hi).astype(np.uint32)
            qs[~d] = qi
            # 动态组（粗）
            if d.any():
                qd = _quant(arr[d], bmap_dyn[name], lo, hi).astype(np.uint32)
                qs[d] = qd
            payload[name] = qs
        bitmask = _pack_bitmap(labels)
    else:
        meta.alloc = "uniform"
        meta.ranges = {}
        payload = {}
        for name in GROUP_ORDER:
            arr = groups[name]
            lo, hi = float(arr.min()), float(arr.max())
            meta.ranges[name] = [lo, hi]
            payload[name] = _quant(arr, bmap[name], lo, hi).astype(np.uint32)
        bitmask = b""

    buf = io.BytesIO()
    hdr = json.dumps({"meta": asdict(meta)}, separators=(",", ":")).encode()
    buf.write(len(hdr).to_bytes(4, "little"))
    buf.write(hdr)
    if alloc == "partition":
        buf.write(len(bitmask).to_bytes(4, "little"))
        buf.write(bitmask)
    for name in GROUP_ORDER:
        # 分区臂：两组各自用其 dtype 打包（组内 dtype 按各自位宽；混合位宽时统一 uint32 会失去节省）
        payload[name] = payload[name]
    if alloc == "partition":
        d = labels > 0
        for name in GROUP_ORDER:
            # 静态组按 bmap 位宽打包
            q = payload[name][~d]
            buf.write(q.astype(_dtype_for(bmap[name])).tobytes())
        for name in GROUP_ORDER:
            if d.any():
                q = payload[name][d]
                bd = {"xyz": bits_dyn.xyz, "f_dc": bits_dyn.f_dc, "opacity": bits_dyn.opacity,
                      "scale": bits_dyn.scale, "rot": bits_dyn.rot}[name]
                buf.write(q.astype(_dtype_for(bd)).tobytes())
    else:
        for name in GROUP_ORDER:
            buf.write(payload[name].astype(_dtype_for(bmap[name])).tobytes())
    raw = buf.getvalue()
    blob = zlib.compress(raw, 9)
    return blob, meta


def decode(blob: bytes, meta: Meta, labels: np.ndarray | None = None) -> dict:
    raw = zlib.decompress(blob)
    hlen = int.from_bytes(raw[:4], "little")
    off = 4 + hlen
    n = meta.n
    shapes = {"xyz": (n, 3), "f_dc": (n, 3), "opacity": (n, 1), "scale": (n, 3), "rot": (n, 3)}
    bmap = meta.bits

    if meta.alloc == "iso":
        out = {}
        for name in ["xyz", "f_dc", "opacity"]:
            dim = shapes[name][1]
            q = np.frombuffer(raw, dtype=_dtype_for(bmap[name]), count=n * dim, offset=off).reshape(shapes[name])
            off += q.nbytes
            lo, hi = meta.ranges[name]
            out[name] = _dequant(q, bmap[name], lo, hi)
        # scale：均值 + 偏差
        qm = np.frombuffer(raw, dtype=_dtype_for(bmap["scale"]), count=n, offset=off); off += qm.nbytes
        smean = _dequant(qm, bmap["scale"], *meta.ranges["scale_mean"])
        qd = np.frombuffer(raw, dtype=_dtype_for(bmap["scale"]), count=n * 3, offset=off).reshape(n, 3)
        off += qd.nbytes
        sdev = _dequant(qd, bmap["scale"], *meta.ranges["scale_dev"])
        out["scale"] = (smean[:, None] + sdev).astype(np.float32)
        # rot 3 分量
        qr = np.frombuffer(raw, dtype=_dtype_for(bmap["rot"]), count=n * 3, offset=off).reshape(n, 3)
        off += qr.nbytes
        out["rot"] = _dequant(qr, bmap["rot"], *meta.ranges["rot"])
    elif meta.alloc == "robust":
        return _decode_robust(raw, meta, off)
    elif meta.alloc == "partition":
        # 位图随流存储（真实 codec 自洽）；labels 参数可覆盖（用于验证一致）
        blen = int.from_bytes(raw[off:off + 4], "little")
        off += 4
        stored = np.unpackbits(np.frombuffer(raw, dtype=np.uint8, count=blen, offset=off))[:n]
        off += blen
        if labels is None:
            labels = stored.astype(np.int8)
        else:
            assert np.array_equal((labels > 0).astype(np.uint8), stored), "labels 与码流位图不一致"
        d = labels > 0
        nd, ns = int(d.sum()), int((~d).sum())
        bd = meta.partition_meta["bits_dyn"]
        out_q = {name: np.zeros(shapes[name], dtype=np.float32) for name in GROUP_ORDER}
        for name in GROUP_ORDER:
            dim = shapes[name][1]
            qs = np.frombuffer(raw, dtype=_dtype_for(bmap[name]), count=ns * dim, offset=off).reshape(ns, dim)
            off += qs.nbytes
            lo, hi = meta.ranges[name]
            out_q[name][~d] = _dequant(qs, bmap[name], lo, hi)
        for name in GROUP_ORDER:
            if nd == 0:
                continue
            dim = shapes[name][1]
            bdw = bd[name]
            qs = np.frombuffer(raw, dtype=_dtype_for(bdw), count=nd * dim, offset=off).reshape(nd, dim)
            off += qs.nbytes
            lo, hi = meta.ranges[name]
            out_q[name][d] = _dequant(qs, bdw, lo, hi)
        out = out_q
    else:
        out = {}
        for name in GROUP_ORDER:
            dim = shapes[name][1]
            q = np.frombuffer(raw, dtype=_dtype_for(bmap[name]), count=n * dim, offset=off).reshape(shapes[name])
            off += q.nbytes
            lo, hi = meta.ranges[name]
            out[name] = _dequant(q, bmap[name], lo, hi)

    return {
        "xyz": out["xyz"],
        "f_dc": out["f_dc"],
        "opacity": out["opacity"],
        "scale": out["scale"],
        "rot4": _quat3_to_rot4(out["rot"]),
    }


def unpack_bitmap(raw_bits: bytes, n: int) -> np.ndarray:
    bits = np.unpackbits(np.frombuffer(raw_bits, dtype=np.uint8))[:n]
    return bits.astype(np.int8)  # 注意：此处 raw_bits 为压缩前位图；调用方须自解压


def roundtrip_stats(blob: bytes, meta: Meta) -> dict:
    return {
        "n": meta.n,
        "bits_per_prim": meta.bits["xyz"] * 3 + meta.bits["f_dc"] * 3 + meta.bits["opacity"]
        + meta.bits["scale"] * 3 + meta.bits["rot"] * 3,
        "codec_bytes": len(blob),
        "codec_bytes_per_prim": len(blob) / max(1, meta.n),
        "orig_full_bytes": meta.orig_full_bytes,
        "orig_render_bytes": meta.orig_render_bytes,
        "ratio_full": meta.orig_full_bytes / max(1, len(blob)),
        "ratio_render": meta.orig_render_bytes / max(1, len(blob)),
    }
