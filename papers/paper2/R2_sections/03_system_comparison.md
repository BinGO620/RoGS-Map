# 03 System & Comparison（新节，含 11 方法横比）

> **状态**：已议定并落笔（2026-10-11 议定 / 2026-10-12 落笔 + 数字核验修正）。**上游**：`R2_NARRATIVE.md` §2/§4。
> **拍板记录**：D2-031（代号 `Prior RGB-D stack`；横比表只放 ATE，PSNR/FPS 进正文）+
> 用户 2026-10-11 三项（§3 开笔 / 发散格如实标 (d) 巨数保留 / 不加条形图）。
> **正文**：`paper2_cvm.tex` §3。**2026-10-12 追加**：补 tab2r_render（PSNR/SSIM/LPIPS 三指标）+
> tab4_efficiency + fig1_pipeline（总览）+ fig3_trajectory；关卡② 修正 3 处区间表述（ATE/PSNR/FPS）。

## 1. 这一节要讲的一句话（thesis）

**先给读者一个坐标系**：动态场景 RGB-D GS-SLAM 这一格上，11 个已发表系统（+ 本文前作栈）
在同机同协议下的 tracking / 渲染 / 效率各是什么水平；**静态方法在动态序列上崩掉**这一实测事实，
正是本文"地图侧代价"研究的动机。（系统本身不是本文贡献。）

## 2. 承接/引出

- **承接 §2 Related**：§2 讲完文献格局，§3 用数字把格局坐实。
- **引出 §4 Map anatomy**：坐标系给完，转"既然这个系统的地图值得研究，它里面到底有什么"。

## 3. 用哪些表

| 表号 | 内容 | 为什么在这 |
|---|---|---|
| `tab:baseline`（**新，机写**） | 11 方法 + 前作栈 × 公共 BONN 6 序列的 **ATE (cm)**；分 static/dynamic 组；发散格标 (d) | 系统坐标系的主表；"静态崩/动态稳"一眼可见 |
| PSNR / FPS | **只进正文**（D2-031 裁定：横比表只放 ATE；PSNR/FPS 进正文，14 页内从宽） | 有覆盖的方法报数 + 如实声明未覆盖（DynaSLAM/NGD/ORB-SLAM3 无 PSNR） |

**数据源**（机写，零手抄）：`resources/baselines/baselines_result/*/{tracking,mapping,efficiency}_raw.csv`
→ `scripts/02_analysis/paper2_baseline_table.py` → `results/paper2_fulltable/evidence/latex/tab_baseline.tex`。
覆盖报告 = `resources/baselines/05-coverage_report_2026-10-10.md`。

## 4. 用哪些图

| 图号 | 内容 | 为什么在这 |
|---|---|---|
| `fig:traj`（复用 fig3_trajectory_crowd2） | crowd2 轨迹对比 | 可选；若只讲 ATE 表则图可省 |
| ~~（可选新图）横比条形图~~ | **不加**（2026-10-11 裁定：表已够，14 页压力下先保表） | — |

## 5. 篇幅预算

**1.5 页**（含一张跨栏表）。

## 6. 数字来源 / 口径

- 全部机写自 `baseline_compare.json`；**不许手抄**。
- 口径（`03-metrics_checklist.md`）：Horn SE(3) 对齐 / cm / ddof=1 / 3 seed。
- **序列集**：公共 6 条 = balloon/balloon2/crowd/crowd2/person_tracking/person_tracking2；
  基线多的 mvnobox×2、本文多的 crowd3 **在题注或正文分开陈述**，不混入同格。

## 7. 红线自查

- ❌ 不得把前作栈写成"我们的/our system"（匿名）——表中名 = **Prior RGB-D stack**。
- ❌ 不得把系统横比写成**本文贡献**（它是背景/坐标系）→ 贡献栏三节之后再出现。
- ❌ SWBA / LoopClosure / +Gate 梯子**一字不提**（用户明确排除）。
- ⚠ 静态方法崩掉的巨数（Co-SLAM crowd ~3.6e4 cm）必须标 (d) 发散，**不能裸报**当读数。

## 8. 待用户确认项（**全部落定 2026-10-11**）

1. **PSNR/FPS 的处置** → **只进正文不列表**（D2-031 裁定；tab_baseline.tex 已按此机写，caption 注明 "PSNR and FPS are in the text"）。
2. **前作栈在表中的名字** → **`Prior RGB-D stack`**（D2-031 裁定；tab_baseline.tex 末行已用此名）。
3. **发散格 (d) 的呈现** → **如实标 (d) 并不裁剪，巨数保留**（用户 2026-10-11 拍板；Co-SLAM crowd 35866.32 cm 原样入表，不换 `div.`）。
4. **横比条形图** → **不加**（用户 2026-10-11 拍板；§3 只 1.5 页预算，表已能一眼看出"静态崩/动态稳"）。
