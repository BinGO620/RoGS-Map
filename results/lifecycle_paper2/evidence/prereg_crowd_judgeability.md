# prereg_crowd_judgeability.md — crowd 族「可判性确认」预注册（C 步；D2-003 = C→A 用户拍板）

**日期**：2026-09-20 ｜ **状态**：判据**跑前锁定**（本文件先于任何训练 run 提交） ｜ **上位**：`DECISIONS.md` D2-003（用户拍板 **C→A**）、`crowd_degradation_improvement_2026-09-20.md` §4 候选 0、`crowd_judgeability_2026-09-20.md`（第①步：零训练重渲染已证「密帧口径可判」）
**性质**：**诊断级**（非论文数字）；无论成败**不改判** L1 的 4 帧口径结论（`verdict_L1.md` §8 C9）。

## 1. 问题

crowd2（拥挤行人）在 4 帧离线口径下不可判（Δ−1.71cm < 同码噪声 3.03cm）。第①步用**密帧**（17 帧）
重渲染现有地图后：Δ−2.01cm > 噪声 0.96cm ⇒ **可判**——但该噪声来自**单对**同码 run，且帧集是**事后**选择。
本预注册把这两点补上：**帧集先锁 + 三对同码复制出 sd**。

## 2. 已锁定的仪器与口径（本条一旦提交不得再改）

| 项 | 取值 |
|---|---|
| 渲染帧集 | **密帧 50,100,…,850 步长 50（17 帧）**（＝第①步用的那一组；**先锁**，不得按结果换帧集） |
| 真空窗 | `render_compare --vacated-window-frames 30`（与运行期 `static_freshvac_*` 同构） |
| PLY 变体 | `point_cloud/final_after_opt` |
| 掩码 | `auto`（crowd2 → seg_mask class 15） |
| 主读数 | `mean_freshvac_ghost_excess_depth_l1_cm`（负 = 残影更小） |
| 副读数 | `mean_ghost_excess_depth_l1_cm`（污染代理，仅描述） |

## 3. 臂与 run 数（**3 个新 run**）

| 臂 | 现有 | 新增（本次） | 合计 |
|---|---|---|---|
| crowd2 **off** | `L1_crowd2_off`、`L1_crowd2_off_rep` | `crowd2_off_r2` | 3 |
| crowd2 **exit** | `L1_crowd2_exit` | `crowd2_exit_r2`、`crowd2_exit_r3` | 3 |

同码 = 同 config（仅 `save_dir` 不同）、同 seed 0、同栈（paper-1 栈 / Combined-Prune）；差异只有非确定性。
复制配置：`configs/experiments/lifecycle_paper2/crowd2_{off_r2,exit_r2,exit_r3}.yaml`。

## 4. 判据（跑前锁定；机械应用）

- 配对：**Δᵢ = exitᵢ − offᵢ**，i=1..3（同臂内按 run 序号任意配对，报告全部三对）。
- **判定 = 3 对全部同号 且 |mean(Δ)| > 1.19cm**（沿用 L1 补遗 2 的 3-seed 配对门；1.19cm 出处 = `prereg_L1.md`）。
- 噪声报告（**描述性，不作判据**）：off 组内 3 读数的 sd、exit 组内 3 读数的 sd（各 n=3）。
- **失败分支（R2：本族一次机会）**：若不同号 或 |mean| ≤ 1.19cm ⇒ **crowd 族终态 = 「不可判/不成立」**，
  按 R7 写边界节，**不追加任何 run**，资源转向 A（L3）。
- **预期方向（诚实登记，不作免死金牌）**：第①步 −2.01cm（单对）⇒ 预期为负（机制使残影更小）。

## 5. 成本与交付

- 3 run × ~20 min ≈ **1 GPU 小时**（两卡并行 ~35 min）+ 重渲染 <1 min；
- 交付：三件套（渲染指标表 + 跟踪指标表 + 渲染图 vs 原图）＋ 本预注册的机械应用结果（`crowd_judgeability_confirm.md`）；
- 数据落点：`results/lifecycle_paper2/L1_crowd2_{off_r2,exit_r2,exit_r3}/` 与 `render_fv_*_dense/`。

## 6. 边界声明

- 本预注册**不产出论文数字**：单序列、单 seed、诊断级；L3（A 档）若纳入 crowd2，须在其自身预注册中重锁；
- 跨口径绝对比较禁止（4 帧 vs 17 帧差 9.28cm 已登记）；本预注册只做**同口径内配对**。
