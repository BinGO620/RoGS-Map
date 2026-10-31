# paper2_rollout — 拉通扩大验证批（held-out 通用性面板）

> 目的：为论文 2 的通用性主张提供**未参与调参**的 held-out 序列证据
> （DISCIPLINE #8：任何方法的最终验证必须包含未参与调参的序列）。
> 上游：papers/paper2/NARRATIVE.md §7.5；resources/notes/paper2_plan.md §5。

## 1. 实验设计

- **序列**：20 条 held-out（Bonn 扩展 6 + TUM 14），含动态/物体搬运/静态/同步四类
- **臂**：
  - `roll_*` = gate 臂（SWBA 0.38 + LoopClosure，零参数重调，部署形态）
  - `rollbase_*` = Combined-Prune 裸基线（无 SWBA/回环）
  - `diag_e1/e2/e3` = f3_st_hf 悬崖分解臂（见 DIAGNOSIS_st_hf_decomposition.md）
  - `diag_f1r_a/b` = f1_room 归因臂（见 DIAGNOSIS_f1room.md）
- **seed**：gate 臂 seed0 先行（rollout_s0）；f3_st_hf 补至 3 seed
  （gate_seeds12）；✗ 行 3-seed 抽查（diag_seeds12）
- **config**：`configs/experiments/paper2_rollout/`（roll_/rollbase_/diag/）
- **运行**：远程 3090×2，HEAD 见各 .done 文件；全部 rc=0

## 2. 结果

### 2.1 通用性面板（seed0，gate 臂）

见 `PANEL.md` / `rollout_panel.csv`（单一事实源）。

- 已完成 19/20（static 因 Bonn 官方 depth 缺口暂缺），过 5cm 线 11/19
- 动态序列过线 5/10

### 2.2 ✗ 行 3-seed 抽查修正（DIAGNOSIS_xrows_seeds.md）

单 seed 面板误判 2 条：f3_st_rpy（5.85→中位 3.23 ✓）、f3_wk_rpy
（5.87→中位 4.65 ✓）。**真 ✗ 行 = 6**（原 8）。除 f3_st_hf 双峰外，
其余 7 序列跨 seed 波动 <±15% = 稳定特征（机制级或方法边界，非抽样彩票）。

### 2.3 机制性失效清单（修复优先级）

1. f1_room（SWBA 归因完成，DIAGNOSIS_f1room.md）
2. balloon_tracking2 / moving_obstructing_box（gate≈rollbase，Combined-Prune 共性）
3. balloon_tracking / f2_person（略超线）
4. f3_st_hf（悬崖：干净抽样率 2/3，随机分量；确定性分量见 mask_fix_iter）

## 3. 结论（只写事实）

- 通用性主张成立范围：静态/物体搬运/多数 TUM 动态序列过线；动态长序列
  （balloon_tracking2/moving_obstructing_box）与 f1_room 未过 = 方法边界，
  如实报告（进 Discussion，不作贡献）。
- **2026-09-17 重估（面板 baseline 列补齐后）**：本批**自有 baseline 臂**
  （`rollbase_*`，固定栈、SWBA/回环/门控全关）此前未进面板。补上对照后
  初判 **8/19 条 |Δ|>0.5cm 为负作用、5 条超跨批噪声地板**（最严重 f1_room
  +9.87cm）。⇒ 上一条"边界"的清单**不完整**，通用性主张的证据基础须重估。
  已立项 **R34**（同批复核 6 条，`evidence/prereg_r34.md`，已过关卡③）。
- **2026-09-18 R34 复核收口——「8/19 负作用」表述作废**（`evidence/verdict_r34.md`）：
  6 条放到同批同码 3 seed 下重测，**没有任何一读支持"5 条有害 / 8/19"**。
  分档事实（完整先验读）：**不可复现 2**（f1_room +8.152、f3_st_rpy +2.602，
  全关 baseline 自身跨批不稳）；**复现有害方向 2**（f3_office +1.603、
  f3_wk_rpy +1.706，由 SWBA 承载）；**方向反转 1**（mob −9.939，baseline 自身
  极差 18.8cm，判据无法判定）；**对照方向复现 1**（f1_desk2 −1.327）。K6 由
  "自动降级"改「部分不成立」。⇒ **改用上述分档事实，禁用"8/19 负作用"措辞**。
  面板 `rollout_panel.csv` 的 6 条 baseline 列已升级为 R34 同批 3-seed 均值
  （`baseline_src=r34rb3seed`，加 K7 标注）。
- **MonoGS 崩坏修复对照**（paper2_plan §6）：原写"MonoGS 复现 TUM 动态
  28-63cm vs 我方同序列 2.85-12.03cm = 5-12× 系统修复"。
  **2026-09-17 更正**：① 上限 **12.03 无出处**（须重新锚定）；
  ② **归因错误**——补上 `rollbase` 后可见该"修复"绝大部分属**继承的基础栈**
  （f3_wk_hf 14.2× / f3_wk_rpy 14.7× / f3_wk_xyz 8.6× / f3_st_rpy 7.1×
  由基础栈达成），加 SWBA+门控后**反而 −14%~−25%**；
  该对照实为"全家桶 vs 裸 MonoGS"。详见
  `resources/notes/method_review_2026-09-17.md` §4。
  f3_st_hf 12× 反例（34.68 vs 2.80）须同表呈现的要求不变。
- f3_st_hf 悬崖=随机分岔，单 seed 排序不可用（DIAGNOSIS_st_hf_decomposition.md）。
- **取数口径**：一律用 `tables/tracking_raw.csv` col 8；**顶层 `*.consolelog`
  不是有效取数源**——已实测 f1_room/f1_desk2/f3_wk_hf 三个 run 的 consolelog
  与 tracking `run_id` 不同源（见 prereg_r34 §1.2）。

## 4. 文件索引

| 文件 | 内容 |
|---|---|
| `PANEL.md` / `rollout_panel.csv` | 通用性面板（seed0，gate 臂） |
| `DIAGNOSIS_st_hf_decomposition.md` | f3_st_hf 悬崖分解（E1/E2/E3 + 随机分岔） |
| `DIAGNOSIS_f1room.md` | f1_room SWBA 归因（b 臂 = gate − SWBA） |
| `DIAGNOSIS_pre_switch.md` | 主线切换诊断（Sim3 分解、GTMC 掩码破损） |
| `DIAGNOSIS_xrows_seeds.md` | ✗ 行 3-seed 抽查修正 |
| `P1_VERDICT.md` | 基础模型位姿替换 P1（判负） |
| `PHASE1_REPORT.md` | VGGT 深度融合 phase 1（不确定） |
| `evidence/verdict.md` | 本批裁决 |
| `evidence/swba_gate_parse/` | SWBA 门控事件落盘 CSV |
| `*.done` | 各批运行记录（rc 可追溯） |

## 5. 运行信息

- 远程 3090×2；批次：rollout_s0（20）、diag_e12（2）、diag_e3（1）、
  diag_l2（1）、diag_seeds12（4）、gate_seeds12（2）——全部 rc=0
- 重数据（point_cloud）单副本存远程，按备份政策不主动归档
