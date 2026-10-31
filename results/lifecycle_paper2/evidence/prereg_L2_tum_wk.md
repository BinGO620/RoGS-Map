# prereg_L2_tum_wk — 新域移植：TUM fr3_walking_rpy 上的 α 生命周期（D2-009 夜间保守执行件）

> **性质**：新域（TUM walking，人动态）上的既有机制移植——**零新代码**（沿用 L3 的
> off/exit 臂定义与同一套判据机/仪器）。执行依据：
> * Phase 0 普查发现 TUM wk_rpy 的**新鲜腾空区缺陷 +13.7~+15.7cm**（Bonn pt 仅 1.8-3.5cm，
>   `census_tum_wkrpy_gate_s{0,1,2}.json`），且随 settled 收敛到 ~0 ⇒ 信号在量级上可测；
> * 用户 2026-09-23/24 两次指示"方法继续、要处理人"+"晚间自动迭代"；
> * R3（呈报未获答复 ⇒ 执行最保守可逆选项并留痕）+ R7（L2 级：3 seed × 2 臂 = 6 run）。
> **本批不改变任何已关闭族的结论**；A/B/C 决策（D2-009 一页纸）仍留给用户。

## 1. 背景与信号（先于本批已入仓的事实）

- TUM wk_rpy 评估掩码：**新建**（`build_dynamic_mask.py`，857 帧，mean_recall=0.959 vs
  deeplabv3 参照，empty_rate=0.010，sha256=734a68a4b03d）——TUM 首次有 canonical 掩码。
- 普查（3 seed，R34 gate 臂为基线）：`exc_nowstat_fresh` = +15.68/+13.67/+14.49cm
  （新鲜腾空区 vs 当前静态区）；`exc_nowstat`（全历史走廊）≈ 0.00/+0.34/+0.01cm
  ⇒ **缺陷集中于新鲜段、随观测收敛**（"观测债"形态）。
- 生命周期机制（exit/carve/fill）**从未在 TUM 上运行过**。

## 2. 臂与成本

| 臂 | config | 说明 |
|---|---|---|
| off | `l3_tum_wk_rpy_off.yaml` | 无 AlphaLifecycle 块（论文 1 栈） |
| exit | `l3_tum_wk_rpy_exit.yaml` | `enabled+mode: exit`（reset/carve）；阈值走默认 |

6 run（2 臂 × 3 seed）双卡；TUM wk_rpy 872 帧，单 run ≈20-25min ⇒ 约 1.5-2h。
对照 = 同批 off 臂（**禁用跨批对照**：不在 R34 gate 臂上做绝对比较——跨批/跨配置绝对
比较禁止，本批自建配对的 off）。

## 3. 主判据（先锁，与 L1b/L1c/L1d/L1e 同源门槛）

Δᵢ = exit_i − off_i（freshvac，canonical 仪器，`render_compare.py --vacated-window-frames 30`）。
**PASS ⟺ ∀3 seeds Δᵢ < 0 ∧ |mean Δ| > max(1.19, off_sd)**。

## 4. 约束门（同 L1b，逐 seed 报告；越门不自动 FAIL）

ATE ≤ +0.5cm 且 ≤ +5%；static PSNR ≥ −0.25dB。

## 5. 诊断读数（预锁，不作判据；带工件键）

- D① `alpha_exit_reset_total` / `alpha_carve_total`（efficiency_raw）：驻留 TUM 是否点火；
- D② 新鲜腾空缺陷的配对消长：本批 off/exit 的 census（`ghost_population_census.py`）
  `exc_nowstat_fresh`（预锁为**诊断**——若 exit 显著压低它而 freshvac 判据未过，
  说明仪器口径与缺陷定义错位，须并陈）；
- D③ 全历史走廊口径（`exc_nowstat`）与 settled 形态（对照 Phase 0）。

## 6. 分支（预锁）

- PASS ⇒ L2+ 扩展：wk_xyz/sitting_* 序列 + 掩码补齐 + 正式批（另立 prereg，呈用户）。
- 非 3/3 负 ⇒ 补 s{3,4,5}（3 run）；重判仍不过 ⇒ **本域移植支关闭**，如实报告
  （负结果只以边界小节身份存在，DISCIPLINE:363）；A/B/C 决策仍留给用户。

## 7. 流程

prereg + config + 派发脚本一次提交记 sha → 6 run 双卡 → 渲染（清单同 commit 列全 6 seed）
→ 判据机（复用 l1b/l1e 读取函数；freshvac 同源）→ 关卡① 先于落盘 → verdict 三件套。
跑批期禁改在批脚本、禁 sync。反悔：GPU ≈2h 沉没；run 数据可弃；零代码改动。
