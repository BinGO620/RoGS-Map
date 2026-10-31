# 后处理通用压缩基线（同分母 n*20*4）— R-D 主表对照（2026-10-09）

> **用途**：独立审稿 §3.1（最致命：无基线）的整改。同**输入**（冻结 PLY）、同**分母**（`n*20*4`）、**无训练、零 GPU**。工件 `results/gs_compress/evidence/rd/posthoc_baselines.json`；复现 `python scripts/gs_compress/posthoc_baselines.py --split both --zfp`。

## L2（42 图）

| 基线 | 类型 | 覆盖字段 | ratio 均值 | 区间 |
|---|---|---|---|---|
| zstd-l19（AoS 字面体） | 无损 | 全 20 | 1.54× | 1.53–1.56 |
| zstd-l19（SoA 字节平面） | 无损 | 全 20 | 1.61× | 1.60–1.62 |
| lzma-9 | 无损 | 全 20 | 1.62× | 1.61–1.64 |
| bz2-9 | 无损 | 全 20 | 1.48× | 1.47–1.49 |
| zlib-9 | 无损 | 全 20 | 1.47× | 1.46–1.48 |
| blosc2 shuffle+bytedelta | 无损 | 全 20 | 1.37× | 1.37–1.38 |
| blosc2 TRUNC_PREC=16 | 有损 | 全 20 | 2.84× | 2.78–2.88 |
| blosc2 TRUNC_PREC=8 | 有损 | 全 20 | 3.80× | 3.76–3.83 |

## L3（36 图）

| 基线 | 类型 | 覆盖字段 | ratio 均值 | 区间 |
|---|---|---|---|---|
| zstd-l19（AoS 字面体） | 无损 | 全 20 | 1.54× | 1.52–1.58 |
| zstd-l19（SoA 字节平面） | 无损 | 全 20 | 1.60× | 1.59–1.63 |
| lzma-9 | 无损 | 全 20 | 1.61× | 1.58–1.66 |
| bz2-9 | 无损 | 全 20 | 1.47× | 1.46–1.50 |
| zlib-9 | 无损 | 全 20 | 1.47× | 1.46–1.49 |
| blosc2 shuffle+bytedelta | 无损 | 全 20 | 1.36× | 1.35–1.38 |
| blosc2 TRUNC_PREC=16 | 有损 | 全 20 | 2.82× | 2.74–2.86 |
| blosc2 TRUNC_PREC=8 | 有损 | 全 20 | 3.76× | 3.71–3.81 |

## 结论（写正文）

通用**无损**压缩器在冻结 SLAM 地图上最高约 **1.62×**（lzma），全部无损法落在 1.37–1.62× 带内；数值感知有损（blosc2 TRUNC_PREC / zfp）在低码率可提到数倍但**不接近**本文 codec 的近无损 6× 工作点。⇒ 增益来自**量化 + 结构感知**，非熵编码本身。

## 排除项（据实登记）

- **Draco**：无干净 per-attribute 无损通路（默认量化有损；generic attrs 解码侧不暴露）⇒ 不作主表基线。
- **HAC**（github.com/YihangChen-ee/HAC，ECCV'24，arXiv:2403.14530）/**HAC++**（github.com/YihangChen-ee/HAC-plus，TPAMI'25，arXiv:2501.12255）：**训练期**方法，无冻结-PLY 后处理通路，且跑 Mip-NeRF360/T&T/DB（非 Bonn、非 SLAM 生长图）⇒ 只作 published-number 定性对位（正文已引 HAC），不作同输入基线。