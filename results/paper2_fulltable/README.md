# paper2_fulltable — 小论文2 主表数据（3-seed 标准子集 + 组件臂）

## 目的

小论文2（Ch4 载体）的主实验面板：标准 Bonn 7 序列 × 3 seeds 上的
final（SWBA+回环）/ gate（部署终态=final+逐帧 static_conf 门）/
baseline / swbaonly 消融臂对照，确立部署机器的 ATE 主张与易序列
不退化硬门。

## 臂与数字（3-seed ATE cm；**四臂同批同码，R33，2026-09-16**）

单一事实源：`evidence/manifest_r33.json`（84 run rc=0，四臂 × 7 序列 × 3 seed）。

| 臂 | pt1 | pt2 | balloon | crowd | crowd2 | crowd3 | balloon2 |
|---|---|---|---|---|---|---|---|
| baseline | 11.31±0.70 | 10.40±0.28 | 3.25±0.07 | 2.23±0.10 | 2.26±0.32 | 1.53±0.02 | 5.48±0.27 |
| swbaonly | 8.62±1.53 | 11.83±0.47 | 4.21±0.14 | 2.35±0.12 | 4.09±0.44 | 2.48±0.20 | 5.37±0.08 |
| final | 8.21±0.33 | 12.39±0.63 | 4.24±0.08 | 2.44±0.10 | 4.05±0.25 | 2.44±0.03 | 5.34±0.08 |
| **gate** | **7.95±0.70** | 11.68±0.37 | 4.22±0.03 | 2.32±0.19 | 2.50±0.22 | 1.83±0.05 | 5.32±0.17 |

- **gate vs baseline**：pt1 **−29.7%**（t≈5.9）；crowd3 +19.4%、crowd2 +10.6%、
  balloon +30.1%、crowd +3.8%、balloon2 −3.0%、**pt2 +12.2%**。
- **pt1 降幅不是单一数字**：baseline 为高方差序列（6 seed 极差 10.55–17.09，
  置换检验 p=0.30 ⇒ 批间差与抽样噪声不可区分），降幅随抽样 **−30%~−42%**，
  6-seed 合并点估计 −36%。~~sd 3.27→0.09（收敛 36×）~~ **作废**——
  跨批拼数，**同批收敛比 1.01×**。
- **pt2 不再是"与基线持平"**：同批逐 seed 严格不重叠（baseline max 10.7013 < gate min 11.2971），
  gate 实为 **+12.2% 劣化**；所有 SWBA 使能臂都比 baseline 差 **+1.27~1.99cm**
  （gate +1.27、swbaonly +1.43、final +1.98）。
- **SWBA 净代价（同批 baseline→swbaonly，最硬证据）**：crowd2 +81.2%、
  crowd3 +62.1%、balloon +29.8%（三者逐 seed 分离）；
  **balloon 上门控不回本（收回 −1.1%）**；**pt1 上 SWBA 反而有益（−23.8%）**。

裁决：`evidence/verdict_r33.md`（含关卡① 复核整改与下游更新清单）。
旧值（`{seq}_{baseline,final,swbaonly}_seed*`、`r29_framegate_*`）**保留仅供溯源**。

## 口径注记（重要）

1. **并发双稳态**：2-per-GPU 时代 ATE 批间比较存在 ±2-9% 启动模式
   漂移（NOTES R19），机制读数优先于 ATE 小差值
2. **GTMC 掩码破损口径注记（2026-09-10）**：mapping_raw 的
   static_psnr/static_ghost_excess 等静态区渲染指标依赖 GTMC 冻结
   掩码，而该掩码在 person 主体上覆盖率中位≈0（详见 NOTES 踩坑
   "GTMC 冻结掩码严重破损"）——掩码对所有方法一致（相对结论成立），
   但绝对数字不是纯"静态背景 PSNR"；论文引用需加口径限定
3. 效率列（FPS/高斯数）的计时受运行时调度条件影响，跨臂比较需
   同条件重测（见 lifecycle_formal 效率教训）
4. **跨代码版本注记（2026-09-15 发现 / 2026-09-16 两批重基线完成）**：
   `r29_framegate`（gate 0.38 臂）原跑于 2026-09-07，`r30_conf030/045`
   跑于 09-14/15，`{seq}_{baseline,final,swbaonly}` 跑于 09-06/07，
   其间 `utils/swba.py` 有两次雅可比修复（`a21e0773`/`1150fb25`）。
   **R32 重测 0.38 臂（21 run）、R33 把四臂全部重跑到同批同码（84 run）**，
   故 Tab.1/Tab.3（baseline/swbaonly/final/gate）**现在可同批横比**。
   两条仍然成立的注意：
   - **跨批噪声真实存在**：R33 实测同码同 config 同 seed 散度 0.18–0.62cm
     （`gatefix_*` vs r32）、r32↔r33 同 config 双批复制的平均 |Δ| 0.14cm。
     各臂间的小差（<~0.3cm）须按噪声读。
   - **F 敏感度曲线（0.30/0.38/0.45）仍跨三批**——不得与 Tab.1 混引，
     见骨架 §4.6 的批结构注记。
   裁决：`evidence/verdict_r33.md`（四臂） + `evidence/verdict_f_rebase.md`（0.38）。

## 证据索引（evidence/）

| 文件 | 内容 | 状态 |
|---|---|---|
| `verdict.md` | R25-R29 部署门控家族定型 | 有效（R25 段见下注） |
| `verdict_r25_recheck.md` | R25 复核：代价门从未在有效阈值下被测试 | 有效 |
| `verdict_seed3_promotion.md` | 3-seed 晋级确认（2026-09-07 历史件） | **三列均已由 R33 同批取代**，仅作历史记录 |
| `verdict_f_sensitivity.md` | 实验 F：static_conf 阈值敏感度（K8） | 0.38 列已于 09-16 换 r32；判读按"噪声受限"重写 |
| `verdict_f_rebase.md` | **R32：0.38 臂重基线裁决**（21 run rc=0）+ 关卡① 整改记录 + 下游更新清单 | 有效（baseline 口径已随 R33 更新） |
| `verdict_r33.md` | **R33：四臂同批重基线裁决**（84 run rc=0）——pt2 改口、sd 卖点作废、pt1 降幅降格为区间 | 有效 |
| `manifest_r33.json` | **当前 Tab.1/Tab.3 的单一事实源**（四臂同批，含 derived 列）← `gen_manifest_r33.py` | 有效 |
| `verdict_r31.md` | R31：自校验式门重测（H1）→ **判负，已排除方向** | 有效（参照已随 R32 更新，总判不变） |
| `prereg_f_rebase.md` / `prereg_rebase_arms.md` | R32 / R33 预注册（判据锁定文本，含勘误留痕） | 有效 |
| `analyze_r32_output.txt` | R32 判据核验的确定性输出（`scripts/02_analysis/analyze_r32.py`） | 有效 |
| `manifest.json` / `manifest_f_sensitivity.json` / `manifest_r31.json` | 可追溯元数据（三者均由脚本确定性重建） | `manifest.json` = **09-07 历史件**，其 gate 列已由 `manifest_r33.json` 取代（内含 `superseded_r29_framegate` 声明） |

> 注：`verdict.md` 的 R25 段（"零拦截（177/115 全应用）"、"循环论证"）
> 与其自身日志相反，已被 `verdict_r25_recheck.md` 推翻。**注记已于
> 2026-09-15 回填**（`verdict.md` R25 段末 + R29 段末两处 blockquote，
> 原文按 D3 保留不改）——引用该段前先读注记与 recheck。