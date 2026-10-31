# prereg_L1c_occupancy.md — L1c 时序先验（区域占据记忆）预注册（判据先锁；先于任何 L1c run 提交）

**日期**：2026-09-22 ｜ **级别**：R7 L1 最小效果验证 ｜ **立项**：**D2-006 用户拍板**（2026-09-22，时序先验路线 = 新机制族；`temporal_prior_route_recon_2026-09-22.md`）
**上游**：L1b 判决（主判据双口径 PASS、约束门双越、机制路径未证实）、L2 击杀判决（1/3→确认仍 1/3）、
机制复盘 `l2_kill_mechanism_postmortem_2026-09-22.md`（pt 家族残影 = 深度一致再占据，证据型机制不可达）

## 1. 因果主张（锁定）

> **逐帧运行的语义掩码是瞬时的。把它在时间维积成区域占据记忆（最近 K 个 KF 内被运行期
> 人物掩码占据过的世界空间 voxel），并对温暖区内低 α（< occupancy_alpha_guard）基元按每
> KF γ 乘法衰减，可在不依赖深度一致性证据、也不依赖几何合取门的前提下，压低人物轨迹区
> 残影（freshvac）。**

### 1.1 机制为何必要（三条 α 通路对照；锁定）

| 通路 | 约束 | pt 续命场景可达性 |
|---|---|---|
| reset（α<0.35） | `in_front`（z < obs_at−0.05）`select_reset_mask` | **结构性不可达**（z≈obs_at） |
| carve（α<0.20） | `in_front`（−0.10）∧ persistent（`select_carve_mask`） | **双门同挡**（α 钉死 0.2199 是第二门） |
| L1b gate | 只封顶不下降（`apply_evidence_gate`） | α 停 0.22，残影按 0.22 渲染 |
| **occupancy decay（本机制）** | **无几何门**；guard+乘法有界 | **可达**（唯一通路） |

### 1.2 参数（全部锁定；改参 = 先提修正案再重派）

`occupancy_memory=False`（默认关，arm 形状同 T3/L1b：仅 EXIT 臂启用）、
`occupancy_voxel_size=0.05`（m，抄 MaskStabilityLedger）、`occupancy_warm_kfs=10`、
`occupancy_decay=0.9`（γ）、`occupancy_alpha_guard=0.35`（=tau_reset）。
**机制开关独立**：occ 臂 `evidence_gate: false`（防归因混淆——审查 v1 计划时确认的致命项）。

### 1.3 安全性（证明照 L1b 形状；单测兜住）

① α≥guard **永不触碰** ⇒ 净静态结构（α≈1）的天花板伤害 = 0（掩码/体素 FP 无害化）；
② 伤害只落在本就低 α（<0.35）群体（按定义已是不确定内容）；
③ 单帧 FP 累计效应有界（γ^K 上界）。与 T3 区别：即时硬覆写 vs 乘法衰减+护栏+有界次数
（T3 判负 2026-08-20，且其排除依据已因掩码事故降"待复核"——**不得引用 T3 作为
"先验路线已证伪"的证据**，见 postmortem 护栏 1）。

## 2. 批构成（R7 L1 级，4 run ≈ 1h GPU）

| 臂 | config | seed | 说明 |
|---|---|---|---|
| occ | `l1c_person_tracking_occ.yaml`（exit + occupancy_memory: true + **evidence_gate: false**） | 0/1/2 | 主判据臂（3 run） |
| occoff | `l1c_person_tracking_occoff.yaml`（exit + occupancy_memory 缺省 + evidence_gate: false） | 0 | off 一致性验证（1 run） |

**对照零新增**：exit 臂 = L3 person_tracking 已有 canonical 渲染同 seed；gate 臂 = L1b 已有
读数（**只作并陈上下文，绝不与 occ 混合归因**）。序列 = person_tracking（postmortem 指认的
钉死场景，判决性测试）。机制代码 = default-off（be504ab0 起的 flag-gated 惯例）。

## 3. 主判据（锁定；程序化于 `scripts/02_analysis/l1c_occupancy_judge.py`）

- 逐 seed 配对：**Δᵢ = occ_i − exit_i**（freshvac ghost excess，canonical 仪器）。
- **PASS ⟺ (∀3 seeds Δᵢ < 0) ∧ (|mean Δ| > max(1.19, off_sd))**。
  门槛公式与 L1b/L2 同源（1.19 = conservative floor；off_sd = off 臂 3 seed canonical
  freshvac 样本 sd）。**"为负"是判据的显式分支**。
- **约束门**（同 L1b 限值，逐 seed 报告）：ATE Δ ≤ +0.5 cm 且 ≤ +5%；static PSNR Δ ≥ −0.25 dB
  （基值量纲护栏 [8,60] dB）。
- **代价风险声明（预锁）**：本机制比 gate 更激进（直接衰减 vs 封顶），代价可能更大；
  **"主判据过 + 约束门双越"的处置 = 如实写、不追加 run**（照 L1b §7 先例），不留事后裁量。
- **击杀确认分支预锁**：1/3 或 2/3 seed 为负（非全负）⇒ 补 s1 三序列 3 run 双 seed 重判
  （逐序列同号为负 ∧ |mean|>门槛）；重判后仍 <2/3 序列达标 ⇒ **时序先验族按 R2 关闭**
  （D2-006 立项承诺），转论文写作收口。0/3 ⇒ 直接关闭，不补 run。

## 4. 过程验证与诊断（不作判据；预锁观察位）

- **off 一致性三门**：① 代码面——`git diff <L1c派发点>..HEAD` 对 slam.py/α 文件只含
  flag-gated 新增；② 行为面——occoff 的 occ_* 计数器全零 + `alpha_gate_*` 全零；③ 轨迹面
  （诊断）——occoff ATE 落入同序列同栈全部 run 实测带内。
- **点火必要条件**：occ 臂 `occ_decay_events_total > 0`、`occ_no_mask_kfs = 0`；否则该批
  无效（单次重派机会，判据不变）。
- **过程正对照（防"机制没碰到目标"）**：`occ_warm_prims_total` 应达千级（与 L1b masked
  群体 ~162/KF × 116 KF 同量级）；若 ≈ 0 ⇒ 机制未触达目标，记流程异常（非机制失败）。
- **guard 失效风险（预注册登记）**：若 occ 臂 `occ_alpha_lt_guard_total ≈ 0` ⇒ α 群体
  高于 guard ⇒ 机制静默不动——该读数把此风险做成可审计量。
- **次要观察（明写：不作主张成立与否的依据——L1b 教训）**：① `alpha_carve_total` 是否
  首次 > 0（温暖区衰减穿阈 + 人离开后几何门可成立时，carve 才有机会点火——**点火与否
  不改变判决**）；② a_min 是否不再钉死 0.2199；③ ATE 的 seed 结构并陈（L1b s0 单点教训）。
- 完成判据 = 工件计数（`l1c.done`/渲染 `n_frames=17`），非日志 sentinel。

## 5. 失败分支与下一步（预锁）

| 批判定 | 动作 |
|---|---|
| 主判据 PASS + 约束门过 | 效应成立且无代价 ⇒ 呈报 D2 设计 L2 泛化（pt2/crowd/crowd2） |
| 主判据 PASS + 约束门越 | "效应真实但带代价"如实写 ⇒ 呈报 D2（照 L1b §7 先例） |
| 边际（非 3/3 负） | 击杀确认分支（§3）→ 重判后 <2/3 ⇒ **族关闭（R2）** |
| 0/3 或重判不过 | **时序先验族关闭** ⇒ 转论文写作收口（box 亚族主张 + 全部负结果作边界） |

**不追加判据外 run**；修正案纪律同 L1b（判据定标错误 vs 数据污染三分法；修正案先提交后重派）。

## 6. 工件键

- config：`configs/experiments/lifecycle_paper2/l1c_person_tracking_{occ,occoff}.yaml`
- 派发：`bash scripts/lifecycle_paper2/run_L1c_remote.sh <gpu>`（`l1c.done`）
- 渲染：`rerender_all_canon.sh`（含 L1c 4 tag；`canon_render.done`）
- 判据机：`python scripts/02_analysis/l1c_occupancy_judge.py`（`--selftest` 对调两臂负对照）
