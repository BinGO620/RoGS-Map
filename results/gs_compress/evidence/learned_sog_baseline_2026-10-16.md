# learned 压缩器基线（SOG）— 冻结地图后处理压缩（R4-P3 / 门槛 3，方案 A′ 第一基线）

> **用途**：R4 独立审稿 P3/门槛 3 的整改——把"压缩无同类基线"变为**同场量化对照**。
> **口径**（与 Table 4 其余行同源，prereg §4.0）：同输入（冻结 PLY，20 字段 f32）、同分母
> （`n_src*20*4`）、同渲染仪器（`render_compare.py` 固定帧集 0/60/120/180/240）、同指标（full-image PSNR）。
> **方法**：SOG（Morgenstern et al., ECCV 2024，本稿 §2 已引）官方代码，**非排序输入通路**
> （其 train.py L202–206 官方注释 "enable compression of non-sorted gaussians"）；**无训练、零 GPU**
> （压缩本身 CPU + torch 张量操作）。
> **工件**：`evidence/rd/learned_sog_L{2,3}.json`（168 行，逐图逐配置）。
> **复现**：`bash scripts/gs_compress/build_sogs_env.sh` →
> `/data/conda_envs/sogs/bin/python scripts/gs_compress/learned_sog_baseline.py --split L2 --configs jxl_101,jxl_quant`（L3 同）。

## 结果

L2 = 42 张冻结地图（7 序列 × 2 臂 × 3 seed）；L3 = 36 张 held-out 面板（5 TUM + 1 Bonn）。

| 配置 | split | n | ratio 均值 | ΔPSNR 均值 | B/prim |
|---|---|---|---|---|---|
| jxl_101（近无损，未量化） | L2 | 42 | 1.81× | −0.000 dB | 44.1 |
| jxl_quant（量化 14/6/6/6） | L2 | 42 | **6.53×** | **−0.023 dB** | 12.3 |
| jxl_101 | L3 | 36 | 1.81× | +0.000 dB | 44.3 |
| jxl_quant | L3 | 36 | **6.61×** | **−0.043 dB** | 12.2 |

对照（同表口径）：本文 codec 近无损 **5.96× @ −0.01 dB**（L2）/ 8.77× @ −0.06 / 15.11× @ −0.64；
通用无损带 1.37–1.62×。

## 结论（写正文用）

1. **量化后**：SOG 在 L2 达 **6.53× @ −0.023 dB**，与本文免参 codec 的 5.96× @ −0.01 dB
   **实质同档**（比值高约 10%、质量略低 0.02 dB）；held-out 面板一致（6.61× @ −0.043 dB）。
2. **未量化**（jxl_101）：SOG 仅 1.81×——高于通用无损带上沿（1.62×，其上下文建模对浮点属性有
   小幅增益），但远低于本文 codec 的 5.96× ⇒ **增益主体来自量化选择**，与 §5 现结论一致，
   且现在有了**跨方法证据**。
3. 与 SOG 在**训练场景**上自报的 19.9–39.5×（其 ECCV'24 评测；Mip-NeRF360/T&T/DB，含 SH-rest
   与平滑正则训练）相比，同一方法在我们这类**冻结 SLAM 生长地图**上只到 ~6.5×
   ⇒ **learned/免参的差距在此分布上坍缩**——这是本文分布论点的量化版本。
4. 高码率端无同档对照：SOG 官方配置集在本文地图上最高约 6.6×，本文 codec 的 15.11× @ −0.64 dB
   处没有 learned 对照点（其配置面向近无损；照实登记，不外推）。

## 适配注记（照实登记；正文/题注择要）

1. 官方**非排序**通路：`prune_to_square_shape` → `sort_into_grid` → `run_single_compression` /
   `run_single_decompression`（与官方 train.py L202–206 同配方）；**无** smoothness 正则训练
   （地图冻结、不重训）。
2. 记账 6 字段（nx,ny,nz + static_prob,static_obs_count,unmapped_score）SOG 不携带 ⇒ 旁路
   **lzma-9** 计入分子（实测 ~0.01 B/基元；法线全零、记账字段近常量）。分母口径不变。
3. DC-only 适配：其 `load_ply` 对 sh_degree=0 合法（assert 0==0），但
   `prune_all_but_these_indices` 对空 `_features_rest` 索引报 IndexError ⇒ 驱动内重排为 `(P,0,3)`。
4. 配置取官方 `config/compression/umbrella.yaml` 默认实验（jxl_101 / jxl_quant），**未**在本文地图上调参。
5. 解码 PLY（17 字段，与本文 codec 重建 PLY 同构）以**本文仪器**渲染；未使用其自带 PSNR。
6. SOG 丢弃 0.1–0.4% 低不透明度基元（方形剪枝，逐图记录 `n_after`）。

## 与门槛 3 字面清单的关系

门槛 3 点名 HAC / Compact3DGS / TC3DGS / MEGA——可行性核查（官方代码逐行）见
`evidence/learned_baseline_feasibility_2026-10-15.md`：TC3DGS 代码未发布且对象为动态表示；
MEGA 训练期 4D 框架；HAC 训练期；Compact3DGS 无冻结-PLY 入口。
**SOG 是 §2 七方法之一且官方支持非排序输入**，为现成可跑的同类 learned 压缩器；
Compact3DGS 的"重训再压"忠实适配作为**第二基线**（工件 `evidence/rd/learned_nied_*.json`，
适配注记见其驱动 docstring）。

---
*2026-10-16 产出。零 GPU（SOG 压缩）；渲染评测走 2060、与 Table 4 同仪器同帧集。*
