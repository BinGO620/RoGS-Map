# 05 A Simple Baseline Codec for Gaussian Maps

> **状态**：已议定并落笔（2026-10-12；§7 两项按默认执行——8 列保留 + codec cost 段保留）。
> **上游**：`R2_NARRATIVE.md` §3 贡献①。**正文**：`paper2_cvm.tex` §5。
> **结构校准**：承接 §4 三发现（死重已付/冗余可挖/重尾承重）；tab_rd.tex 自带环境直接 `\input`。

## 1. thesis
一个**故意朴素**的离线 codec（逐图范围均匀量化 + zlib 熵编码，无学习参数）就能把存储地图压到
近无损 ~6× / 中 ~8.8× / 激进 ~15×，且在留出面板复现。它的价值不在"新原语"，而在
**在一张动态场景生长地图上被认真测量**——包括哪些操作没用（分区/重要度分配、范围收缩、
轨迹剪枝）和哪个操作有代价（体素合并）。

## 2. 衔接
§4 解剖 → §5 压缩 → §6 讲被压缩对象"少了什么" → §7 装回去。

## 3. 表 / 图
| 资产 | 复用 | 内容 |
|---|---|---|
| `tab:rd`（tab_rd） | ✅ | R-D 主表：源/4 无损压缩器/三工作点/体素合并消融 |
| `fig:rd`（fig_rd_curves） | ✅ | R-D 曲线（全图 + 静态区双面板） |

## 4. 篇幅
**2.0 页**。

## 5. 数字来源
`results/gs_compress/evidence/rd/{l2_summary.json, L3_*, L2_*_baseline.json, posthoc_baselines.json}`；
codec = `gs_codec.py`；生成器 = `scripts/gs_compress/paper2_codec_tables.py`。

## 6. 红线自查
- 禁"首个 3DGS 压缩"；必须与 HAC/GSZip（learned NVS）、CGS-SLAM/DiskChunGS（静态 SLAM）区分。
- 无损带最强 = lzma 1.62×；**不得**把体素合并写成主工作点（它过不了 pregate，只作消融行）。
- 臂名 = `baseline`/`final`（**非 gate**，G2-M1 旧账）。
- codec↔修复边界：codec 只读单张合并 PLY（output②），读不了 4D 层序列（output①）——如实声明。

## 7. 待确认（**全部落定 2026-10-12**）

1. **R-D 主表列数** → **保持 8 列**（held-out 列 = 泛化证据，是贡献①的卖点之一，不移除）。
2. **codec cost 段** → **保留**（0.7µs/prim 是"离线不贵"的效率证据；`codec_timing_2026-10-05.md` 权威口径）。
