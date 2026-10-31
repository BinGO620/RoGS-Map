# 朴素压缩基线（raw zlib）— R-D 主表对照（2026-10-05）

> **用途**：独立审稿 P0-1 —— `tab_rd.tex` 无法解读的根因是**无基线**。本件补上「通用无损压缩器在**同一 20 字段 f32 源体**上能拿多少」。
> **口径**：分母 = `n*20*4`（与 codec `ratio_full` **同源**）；分子 = `zlib.compress(源 PLY f32 体, 9)`。codec 行是**有损**，本基线是**无损**。
> **工件**：`results/gs_compress/evidence/rd/raw_zlib_baseline.json`；复现：`python scripts/gs_compress/raw_zlib_baseline.py`。

## L2 (Bonn 7×2 臂×3 seed = 42 图)

- **AoS（源字面体）zlib**：1.47×（无损）
- **SoA（逐字段字节平面）zlib**：1.61×（无损；范围 1.60–1.62）

## L3 (held-out 36 图)

- **AoS（源字面体）zlib**：1.46×（无损）
- **SoA（逐字段字节平面）zlib**：1.60×（无损；范围 1.58–1.63）

## 解读（写进正文的结论）

通用无损压缩（最强的 layout 变体 = SoA）在动态场景 SLAM 地图上约 **1.6×**；本文有损 codec 在**近无损**工作点即达 6×、**激进**端 15×。基线落在 2× 量级，说明增益来自**量化 + 结构感知**而非熵编码本身——这正是 codec 需要被对照才能说明的事。
