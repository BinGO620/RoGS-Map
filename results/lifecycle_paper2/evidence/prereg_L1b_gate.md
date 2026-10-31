# prereg_L1b_gate.md — 证据门控回收（evidence gate）L1b 预注册（判据先锁）

> **账本登记（2026-09-25 追补，D2-015 同例；原文零改动）**：本预注册属账本设立前的文书，决策留痕见 `NOTES.md` 实验清单与 git 历史；本轮由 health_check H5 扩表（`prereg_*` 纳入覆盖面）后检出为“未挂账本号”，按机制登记补入本指针，不追改正文。

**日期**：2026-09-21 ｜ **先于任何 L1b run 提交**（git 时间戳为准）
**性质**：人群/动态人族的 R2 单次定位改进快筛（机制性定位 = `verdict_L3.md` §9 工件级诊断；
定位改进点 = α 门钉死，非参数重试）＋ 经修正仪器后的**机制判决性测试**
（见 `l3_instrument_rescore_2026-09-21.md` §5）。
**D2**：新机制族立项 ⇒ 一页纸呈报（选项 A/B/C，默认建议 A）；R3 保守默认 = A（本预注册即 A 支）。
**规模（R7 L1 级）**：**4 run** ＝ 1 个 off 一致性验证 + 3 个 gate（person_tracking × seed 0/1/2）；
对照 = 已有 L3 exit 同 seed（**零新增对照 run**）。

---

## 1. 机制（治续命 = 瞬态占据者的观测不得为静态结构作证）

`verdict_L3.md` §9：人群族（pt/pt2）`alpha_carve_total=0`——几何门满足（geom_free=291/454）
但 **α 钉死 0.2445/0.2223 > tau_carve 0.20**。原因 = 人回来再占据 ⇒ 渲染深度≈观测深度
⇒ `depth_inconsistency_evidence`≈0 ⇒ EMA 把 α 拉回 1 ⇒ carve 永不触发 ⇒ 人残影留存
（`l3_instrument_rescore_2026-09-21.md` §3.1：exit≈off，off 在人物轨迹区残影 3.96–5.01cm）。

**实装**（`slam_backend._alpha_lifecycle_step`，`ema_alpha_update` 之后、`does_exit` 分支之前）：
对每个投影落在**运行期动态掩码**（`viewpoint.dynamic_mask`，前端缓存，同 T3 读取模式）
内且本步 EMA 会**抬高** α 的基元：`α_new = min(α_pre, α_EMA)`——**只减不升（封顶），不是冻结，
更不是改写**。删除仍需 carve 的完整合取门（α<0.20 ∧ in_front ∧ persistent ∧ valid）。

**失败模式论证（为何比 T3 安全）**：
- 掩码假阳性落在静态区 ⇒ 静态基元 α≈1（`ensure_static_memory_state` 默认 0.7，静态证据
  一路拉向 1），封顶**不下压** ⇒ 永远到不了 0.20 ⇒ carve 不可达 ⇒ 静态结构不可删。
- 删除的唯一通路仍是深度不一致 EMA 下walk（exit 臂既有、L3 已按约束门检验的安全性）。

## 2. T3 前科登记（先例已知；`results/evidence/t3_semalpha_verdict.md`，2026-08-20 判负终止）

- **T3 是什么**：语义 α 覆盖——mask 命中 ∧ in_front(z < obs_at−0.10m) ⇒ α **直接改写**为低值。
  判负原因：误杀 83.8% vs 死线 5%（被 override 的基元 83.8% 落 GT 静态区，且远场
  p90=182px——运行期语义掩码覆盖面远大于真实动态区）。
- **为何 T3 的判负不覆盖本提案**：
  1. **失败模式不可达**：T3 = 即时硬改写（每个掩码 FP 立即变永久伤害）；gate = 只减不升的
     封顶（掩码 FP 不下压 α，静态结构 α≈1 到不了 carve 门）。
  2. **几何域不相交**：T3 的 in_front 合取在续命场景（z≈obs_at，人站在自己残影处）**结构性
     不触发**——T3 从未在我们要治的通路上动过手；其误杀全部发生在 in_front 区的漂浮基元上。
- **继承的教训**：T3 的"掩码覆盖面 >> 真实动态区"观察 ⇒ 本批阶段 0 已量化运行期掩码质量
  （§3.1：对人物区域召回 0.995——本序列上掩码不是瓶颈）。

## 3. 阶段 0 预检结论（本预注册的前置工件，均已入仓）

1. **运行期掩码质量**（`evidence/l1b_mask_recall_audit.json` + §1.2 of rescore）：
   对 person_tracking KF 网格（`evidence/l1b_audit_kf_grid.json`，153 帧 = exit 三 seed
   alpha-ledger KF 并集），运行期 MaskRCNN 对 cls12 人物区域召回 **0.995**（61/61 人在场 KF，
   min 0.980）⇒ **gate 功效不受掩码限制；"召回上界 <50% ⇒ 方法边界"分支前置关闭**。
2. **判据仪器修正**（`l3_instrument_rescore_2026-09-21.md`）：L3 原 freshvac 掩码 8/9 序列无效；
   本批一律用 **cls12 freshvac**（`--mask-subdir seg_mask --mask-class 12`）。

## 4. 主判据（唯一判定；程序化，禁手抄）

- **序列**：person_tracking；**读数** = `render_metrics.json:mean_freshvac_ghost_excess_depth_l1_cm`
  （cls12 仪器，渲染配方可复算）。
- **配对**：Δᵢ = gate_i − exit_i，i ∈ {s0,s1,s2}；exit 基线 = 已入仓 cls12 重渲染
  （`render_L3_person_tracking_exit_s{0,1,2}_seg12dense`：3.5053 / 4.2651 / 4.2156）。
- **PASS ⟺（≥2/3 seed 的 Δᵢ < 0）∧（|mean(Δ)| > 门槛）**——**"为负"是判据的显式分支**
  （判据机自带对调两臂负对照；L3 判据机同类 bug 的教训，NOTES 2026-09-20）。
- **门槛 = max(1.19, off_sd_cls12)**；off_sd_cls12 = off 臂 cls12 freshvac 3-seed 的**样本 sd
  （n−1，`statistics.stdev`）** = 0.5839（`render_L3_person_tracking_off_s{0,1,2}_seg12dense`：
  5.0066 / 4.0329 / 3.9613）⇒ **门槛 = 1.19 cm**（1.19 为预注册保守地板常数，其 L1 期出处已
  因仪器失效作废——见 rescore §4 表末行；沿用仅作地板，取值不变）。
- **判据机**：`scripts/02_analysis/l1b_gate_judge.py`（读工件键、量纲护栏、`--selftest`
  含对调两臂负对照）。

## 5. 约束门（逐 seed 配对 vs L3 exit；越门须如实写，不自动判负）

- **ATE**：Δ(gate−exit) ≤ +0.5 cm 且 ≤ +5%（`tables/tracking_raw.csv:ate_rmse_cm`）。
- **static PSNR（cls12 仪器）**：Δ(gate−exit) ≥ −0.25 dB（基值须落 [8,60] dB 量纲护栏）。

## 6. 过程验证（**不作判据**；失败即如实登记）

- `alpha_gate_capped_total > 0` 且 `alpha_gate_prevented_rise_sum > 0`（新计数器，
  `tables/efficiency_raw.csv`）。
- **`alpha_carve_total > 0`**（exit 臂在 pt 上为 0——gate 解锁 carve 的直接信号）。
- 末帧 `a_lt_carve > 0`、`a_min < 0.20`（consolelog alpha-ledger 行；exit 臂 a_min=0.2445）。
- **诊断预测**：掩码内 α 在人再占据时不回升（per-KF `alpha-gate` 日志行：capped/prevented
  持续非零；终态 PLY 不含 static_prob，运行期日志是唯一观测点）。

## 7. 分层失败分支（**不追加 run**；R2：每族一次）

| 情形 | 处置 |
|---|---|
| 掩码召回上界 <50% | **前置关闭**（阶段 0 实测 0.995） |
| 主判据未过（任何原因） | **证据门控族关门**（R2 一次已用尽）；人群族解决转非门控路径（D2 重议，系统不自裁） |
| 主判据过但越约束门 | "效果真实但带跟踪/渲染代价"如实写（用户方向：机制有一致小幅跟踪代价应进正文） |
| 过程计数器全零 | 实装失效（仪器故障方向排查：gate 未生效 ≠ 机制失败）——判 **无效批**而非机制判负，修复后**同预注册**重跑一次（此为唯一允许的重跑，须登记原因） |
| 主判据过 | 人群族出现首个可复制正效应 ⇒ L2 泛化（pt2 + crowd 族）提上 D2 |

## 8. 仪器与帧集（沿用 L3 修正案 1 全套 + 掩码源修正）

- 帧集 = `l3_framesets.json`（pt 17 帧；两臂同帧配对）。
- 渲染 = 单卡 `cuda:0` + `CUDA_DEVICE_ORDER=PCI_BUS_ID`；`--mask-subdir seg_mask --mask-class 12`；
  `--max-scale-m 0.5 --skip-unrenderable`；PLY = `final_after_opt`；断言 `n_frames == 17`。
- 训练配方 = `run_L3_remote.sh` 模式（幂等 skip、`.done` 工件计数判完成）。

## 9. off 一致性验证 run（前置，1 run，判据外门禁）

- config = `l1b_person_tracking_gateoff.yaml`（与 `l3_person_tracking_exit.yaml` **仅**
  `save_dir` 不同 + `evidence_gate: false` 显式写明），seed 0，同机（远程 3090）。
- **通过标准**：`ate_rmse_cm` 与 L3_person_tracking_exit_s0 逐位一致或 |Δ| ≤ 0.1 cm
  （同机同码重跑实测带 0.037 cm；跨机 0.59 cm 不可比——GPU 政策备忘）。
- **不通过 ⇒ 禁派 gate 批**（代码有混杂），排查后重来。

## 10. 实装边界（纪律）

- config 键 `AlphaLifecycle.evidence_gate`（**默认 false**；false = 代码路径零张量操作，
  逐位无混杂——由 §9 的 run 实证）。
- gate 仅在 **EXIT 臂内**生效（`does_exit` 同族判定；observe 安慰剂臂不启用——同 T3 的
  `does_semantic_override` 语义：无声混杂不是消融）。
- `viewpoint.dynamic_mask is None` ⇒ **fail-open + 计数**（`alpha_gate_no_mask_kfs`），
  不加载第二份 MaskRCNN（后端 VRAM 纪律，同 T3 注释）。
- 掩码采样**复用** `alpha_lifecycle.sample_map_at_gaussians`（不写第二套采样）。
- 计数器入 `backend_timing` → `efficiency_raw.csv`（关卡① M1 教训：仓内可核来源）。
- 生成图/表脚本入仓，图注数值取自工件（关卡① M3 教训）。

---

## 修正案 1（2026-09-21，§9 判据标定修正；**先于重派，跑前锁定**）

**触发**：§9 原判据（逐位一致或 |ΔATE| ≤ 0.1cm）首跑 **FAIL**：gateoff s0 ATE **11.6412** vs
L3_person_tracking_exit_s0 **12.8458**（Δ = −1.2046cm）。按原 §9 字面 ⇒ 禁派。逐项排查后
判定：**判据标定错误，非代码混杂**。排查证据（全部可回查）：

1. **代码面**（`git diff --stat 164a7128..HEAD -- utils/ gaussian_splatting/ slam.py`）：
   L3 派发点 → 本批提交之间，运行时文件的差异**只有 L1b gate 的新增代码**（+42 alpha_lifecycle /
   +7 eval_utils / +56 slam_backend / +2 新 config；**0 行删除**，`gaussians.static_prob` 回写
   仅一处、位置未变）。改动的执行路径在 `evidence_gate=false` 时逐句等同原路径。
2. **行为面**（硬证据，**已通过**）：gateoff s0 的 `tables/efficiency_raw.csv`：
   `alpha_gate_capped_total=0`、`alpha_gate_prevented_rise_sum=0.0`、`alpha_gate_no_mask_kfs=0`；
   consolelog 中 `alpha-gate` 行数 = **0** ⇒ 关闭态零动作。
3. **轨迹面（判据错在哪）**：本管线**同配置同 seed 重跑不是逐位可复现**（混沌：SLAM 的
   密集化对浮点实现次序敏感）。实测：L3 off 臂三 seed ATE = 11.5419 / 11.9218 / 10.3737
   （sd 0.81），exit 臂 = 12.8458 / 11.8729 / 10.9974（sd 0.93）；**gateoff s0 = 11.6412，
   正落在 off 臂分布中央** ⇒ 1.20cm 差为运行间散布，非混杂。
   （注：`NOTES` 的"同机重跑 0.037cm"不是 ATE 口径，不可作为本判据的噪声带——见 NOTES 坑区。）

**修正后的 §9（三部分；第 1、2 部分为硬门，第 3 部分为诊断记录）**：

1. **[硬] 代码面**：`git diff --stat <L3派发点>..<L1b提交> -- utils/ gaussian_splatting/ slam.py`
   仅含 L1b 新增且 flag-gated 的代码（0 删除行或删除行不落在关闭态执行路径）。
2. **[硬] 行为面**：gateoff run 的三个 `alpha_gate_*` 计数 = 0 且 consolelog `alpha-gate` 行数 = 0。
3. **[诊断，不作门] 轨迹面**：gateoff 的 ATE 须落在同序列 off 臂 3-seed 的 min–max 区间内
   （或差 ≤ 2×off 臂 sd）；越界 ⇒ 停下来人工排查后**再**消费本批数据。

**重派范围**：本轮 gateoff s0 / gate_s0（旧配置、含 gtmc static 行）**不计入** L1b 工件集，
重派 4 run（gateoff + gate × 3，修正配置见 修正案 2）。gate_s1 在跑中被停（SIGTERM，
`.done` 无 finished 行 ⇒ 非完成件）。

## 修正案 2（2026-09-21，配置修正；先于重派）

- **L1b 两个配置显式 `Results.static_bg_mask_subdir: null`**：`combined_prune/method.yaml:47`
  默认指向 `dynamic_mask_gtmc`，在 pt 上是**已知失效仪器**（rescore §1）——运行期 P-A 会往
  `mapping_raw.csv` 写 gtmc 口径的假 static 行。runtime P-A 路径吃不了类别掩码
  （`eval_utils.py:763` 用 `load_frozen_mask` >127，只支持 0/255 布尔图）⇒ 本批直接关闭该行，
  离线判据不受影响（走 render_compare cls12）。
- 登记：L3 全部 60 run 的 `mask_type='static'` 行同为 gtmc 口径 ⇒ 一并作废
  （补入 `l3_instrument_rescore_2026-09-21.md` §4 表）。

**§9 排查证据工件**（旧配置 gateoff s0 的原始 tables，保留以支撑修正案 1 的数字）：
`results/lifecycle_paper2/_l1b_probe_s9_preconfig/tables/{tracking,efficiency,mapping}_raw.csv`
（含 §9 引用的 ATE 11.6412、num_gaussians 98102、`alpha_gate_*` 全 0）。
