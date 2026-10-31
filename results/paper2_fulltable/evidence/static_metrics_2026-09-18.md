> ⚠️ **2026-09-22 掩码事故重算**：本文件的静态区/残影读数用的是 `dynamic_mask_gtmc` / `seg_mask`(cls15)，两者 2026-09-21 均被证伪/证错类。
> canonical 掩码重算（44/44 rc=0）后：
> **① “static PSNR 全中性（|Δ|≤0.25dB）” 不成立**（新臂间 spread 0.17–0.69 dB，绝对水平抬升 +0.7–+7.8 dB）；
> **② “ghost_excess gate 方向一致更优” 不成立**（新口径 2/5 优、3/5 劣）；
> **③ “SWBA 损伤静态区 / 门控挽回” 成立**（swbaonly 在 crowd2 最低 −0.53dB；gate−swbaonly 4/5 为正）。
> 权威重算见 `static_metrics_canon_recompute_2026-09-22.md`。**原文按纪律保留不改。**

# P0 静态区/残影指标 — 三证据线合读（2026-09-18）

> 目标（用户布置）：补齐论文 2 的"渲染/稠密建图干净"量化——对齐 WildGS/MonoGS/SplaTAM
> 的评测惯例，并回答"我们的组件是否让地图更干净"。
> 结论先行：**static PSNR 跨臂完全中性**（8 序列 |Δ|≤0.25dB）；**ghost_excess（残影）在
> 多数序列上 gate 方向一致更优**（幅度小、未达显著）；**R34 mob 给出机制证据**——
> SWBA 稳定损伤静态区、门控稳定挽回。⇒ 论文定位：地图/渲染面作"**不退化**"证据，
> 残影可作**弱正面**证据（需 paired 统计），卖点仍集中在跟踪（ATE）。

## 一、证据线 1：R33 运行期 P-A（最强口径，48 读数）

**来源**：R33 批的 `tables/mapping_raw.csv` 中 `mask_type=='static'` 行——与主表**同批同码**，
88 帧 @every5，冻结 GTMC 掩码（`Results.static_bg_mask_subdir: dynamic_mask_gtmc`，
profile 见 `combined_prune/method.yaml:47`）。**这是本批的本就产出，非本次新跑**
（2026-09-18 方法文档调查时发现；此前无人读取该列）。覆盖 balloon/balloon2/pt1/pt2。

| seq | static PSNR base→gate | ΔPSNR | ghost_excess base→gate | Δge (cm) |
|---|---|---|---|---|
| balloon | 23.96 → 23.84 | **−0.12** | 4.47 → 4.29 | −0.18 |
| balloon2 | 21.40 → 21.30 | **−0.11** | −3.04 → −3.72 | −0.67 |
| person_tracking | 25.17 → 25.19 | **+0.02** | −1.21 → −1.08 | +0.13 |
| person_tracking2 | 24.10 → 24.14 | **+0.04** | −0.69 → −1.01 | −0.32 |

- **freshvac 残影**（窗口化"新鲜疤痕"）：gate 在 **9/12 seed** 上更优
  （mean Δ=−0.71cm，符号检验 p≈0.073，**临界未显著**）。
- 全部 12 行的 `static_coverage` = 1.0（无孔洞代价）。

## 二、证据线 2：crowd/crowd2 离线补测（24 run，本地 2060）

**原因**：crowd/crowd2 无 `dynamic_mask_gtmc`（只有 `seg_mask`，需 class15 二值化），
运行期 P-A 未产出行；用离线渲染器（同源指标函数）补齐。
**协议**：`render_compare.py`（8 帧 @interval5，`seg_mask` class15，三级时间戳匹配）。

| seq | static PSNR base→gate | ΔPSNR | ghost_excess base→gate | Δge (cm) |
|---|---|---|---|---|
| crowd | 20.36 → 20.16 | **−0.21** | 4.06 → 3.65 | −0.40 |
| crowd2 | 20.28 → 20.26 | **−0.03** | 4.34 → 2.09 | **−2.24** |

## 三、证据线 3：R34 mob（机制证据，9 读数）

**来源**：R34 三臂（rb/sw/gate）运行期 P-A（gtmc 掩码，589 帧全覆盖）。

| 指标 | rb | sw | gate | 解读 |
|---|---|---|---|---|
| static PSNR | 26.76±0.28 | **26.22±0.26** | 26.52±0.11 | **SWBA 损伤**（−0.55）→ 门控挽回（+0.31） |
| ghost_excess (cm) | +0.36±1.93 | **+3.16±0.38** | −0.06±2.72 | **SWBA 3/3 seed 变差**（+2.80）→ 门控挽回（−3.22，2/3 seed） |
| freshvac (cm) | −0.73±2.29 | +0.83±0.52 | −0.73±1.16 | gate−sw = −1.56（**3/3 seed 方向一致**） |

- SWBA 在 mob 上损伤静态区的方向**逐 seed 一致**（ghost_excess 3/3 为正）；
- 门控在 ghost 侧**稳定挽回**（gate−sw 2/3 seed 为负且幅度大 −5.06/−5.17cm）；
- 与 R34 主表（mob 是"方向反转"序列，gate 优于 rb 的 ATE）**机制自洽**：
  门控拦下了 SWBA 的有害修正 → 静态区残影更少。

## 四、合读（P0 结论）

1. **static PSNR：完全中性**。9 序列（R33 7 + R34 mob 2 视角）gate−baseline ∈ [−0.21, +0.04]dB，
   **7/7 R33 序列 |Δ|≤0.25dB**（噪声带内）。⇒ 组件不伤渲染，"干净"侧无退化。
   （**2026-09-18 补**：crowd3 此前无掩码不可算，本次补齐 → 静态 **7/7**；
   crowd3 ΔPSNR = −0.04dB，仍在噪声带内。）
2. **残影 ghost_excess：方向一致偏优**。R33 runtime 4 序列中 3 序列 gate 更优
   （Δ∈[−0.67, +0.13]cm）；离线 2 序列均更优（crowd2 **−2.24cm**）；
   R34 mob 上"SWBA 变坏→门控挽回"。**但幅度小且未达统计显著**（freshvac p≈0.073）。
3. **论文口径建议**（供拍板）：
   - static PSNR/SSIM/coverage → **"不退化"**证据（表格一行或附录）；
   - ghost_excess → **可写的弱正面**方向（"门控减少动态物体残留"），
     但须 paired 统计（n=12 seed，逐 seed 配对）并如实标注临界；
   - **不要**把它当主卖点——与方案 B 自洽几何（全批无一致分离）合读，
     静态面天花板已现，卖点仍应在跟踪（ATE）与方向 C（拥抱动态）。

## 五、工具与产物

- **读取器**：`scripts/02_analysis/paper2_tables.py`（静态列优先运行期 P-A，其次离线；两源不混算）
- **离线渲染**：`scripts/02_analysis/render_compare.py`（`--mask-subdir auto`，三级时间戳匹配）
- **掩码生成**：`scripts/build_static_eval_mask.py`（GTMC 运动一致性；Bonn 无掩码序列）
  与 `scripts/build_person_seg_mask.py`（**MaskRCNN person → seg_mask**，2026-09-18 新增）。
  crowd3 的 GTMC 掩码**不合格**（不覆盖走动的人主体，NOTES 踩坑 P9 形态；overlay 实测
  人未被标、背景家具被误标）⇒ 改用 **MaskRCNN person**（`seg_mask`，person=15，原始像素
  空间、与 crowd/crowd2 同口径）。crowd3 掩码 manifest 见
  `evidence/crowd3_seg_mask_manifest.json`。
- **产物**：`results/paper2_fulltable/evidence/tables_paper2_preview.{md,json}`
  （Tab.3 = 静态区全表，**静态 7/7 序列**）；离线 36 run 产物在 `render_compare_static/`
- **过程发现**（已入 NOTES 踩坑）：R33 批自带 P-A 列被遗漏三天（"跑完未读"形态第三次）——
  收口检查应包含"mapping_raw 含未读列"一形态。
