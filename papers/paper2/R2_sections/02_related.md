# 02 Related Work

> **状态**：已议定并落笔（2026-10-12；§7 两项按默认——4 个 `\paragraph` + 横比 11 方法全部在 §2 出现并被引）。
> **上游**：`R2_NARRATIVE.md` §7 禁语。**正文**：`paper2_cvm.tex` §2。
> **bib 补登**：RGD-SLAM（Pattern Recognition 175:113071, 2026）+ RoDyn-SLAM（arXiv 2407.01303）——横比表 11 方法全部可引。

## 1. thesis
把文献分成四条线并在末尾收口到本文位置：①优化式 splatting SLAM ②动态场景处理（抹/学/带证据）
③紧凑与可压缩地图 ④视觉媒体的评测惯例。收尾用一句 "In contrast, our work ..."（CVM 惯例）。

## 2. 衔接
§1 给了四问 → §2 说明"这四问前人做到哪" → §3 用数字坐实格局。

## 3. 表 / 图
无（纯文献）。可含 `tab:baseline` 的**方法出处脚注**对应关系（不给表）。

## 4. 篇幅
**1.5 页**（4 个 `\paragraph` 或改 4 个 `\subsection`——CVMJ 期刊用 subsection，会议格式 paragraph 亦可）。

## 5. 数字来源
无测量数字；引用 key 全部来自 `cvmbib.bib`（27 keys，禁孤儿）。

## 6. 红线自查（必须逐条落句）
- 必须**主动区分并引用**：CGS-SLAM / DiskChunGS（静态 SLAM 压缩）、TC3DGS（动态场景压缩）、
  MEGA（4DGS）、PWAS（重要度剪枝）、SOG / StitchGS（百分位范围量化）。
- 修复算子机制本体归 DynaGSLAM（arXiv:2503.11979，必引）；delta = 离线放置。
- 末句定位："In contrast, ..."（照 CVM 惯例）。
- 禁"首个"；禁把评测协议当贡献。

## 7. 待确认（**全部落定 2026-10-12**）

1. **4 个 `\paragraph` vs `\subsection`** → **`\paragraph`**（会议格式，CVM 双栏下 subsection 太占空间）。
2. **横比 11 方法覆盖** → **全部被引**：MonoGS/SplaTAM/CoSLAM/ORBSLAM3/DGSLAM/RGD-SLAM/WildGS/DynaGSLAM/DynaSLAM/NGDSLAM/RoDynSLAM（bib 已补 RGD + RoDyn，无孤儿）。
