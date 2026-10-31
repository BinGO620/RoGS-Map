# 预注册：实验 F 的 0.38 臂重基线（R32，2026-09-15）

> **账本登记（2026-09-25 追补，D2-015 同例；原文零改动）**：本预注册属账本设立前的文书，决策留痕见 `NOTES.md` 实验清单与 git 历史；本轮由 health_check H5 扩表（`prereg_*` 纳入覆盖面）后检出为“未挂账本号”，按机制登记补入本指针，不追改正文。

> 依据：`results/joint_correct/README.md` §2.5c（2026-09-09 宣布 gate 参照数字
> 7.83/4.06/2.62/1.89 作废，须以修复后代码重测）+ NOTES 踩坑
> 「对照臂与实验臂跑在不同代码版本上」（2026-09-15）。
> **纪律合规**：零代码改动——本次是**同 config 重基线**，不是新机制
> （DISCIPLINE #2：只改 config）。判据先锁定（本文件），跑批在判据锁定之后。
> **修订记录**：本文件经 slam-critic 第 3 档审查后修订（致命 2 + 重大 5 全部
> 独立复核成立后采纳，见 §八）。

## 一、问题与动机

实验 F 的 static_conf 阈值敏感度曲线三臂跑在**不同代码版本**上：

| 臂 | 阈值 | 运行日期 | 代码版本 |
|---|---|---|---|
| `r29_framegate` | 0.38 | 2026-09-07 | **早于** SWBA 雅可比修复 |
| `r30_conf030` | 0.30 | 2026-09-14/15 | 含修复 |
| `r30_conf045` | 0.45 | 2026-09-14/15 | 含修复 |

其间 `utils/swba.py` 有两次雅可比修复：`a21e0773`（2026-09-09，`_edge_frozen`
i 侧全局反号，自述"修复改变部署 SWBA 行为"）与 `1150fb25`（2026-09-09，
`_edge_depth_frozen` i 侧 ωy 列）。`a21e0773` 不是 r29 运行代码的祖先
（`git merge-base --is-ancestor` 判否），是 r30 运行代码的祖先。

**量化版本漂移**：同 config 同 seed 的修复后重跑
（`results/joint_correct/gatefix_r29_framegate_*`，2026-09-09）相对 09-07 原值
（col 8 全帧 ATE）：

| 序列 | seed | r29 (09-07) | gatefix (09-09) | 偏移 |
|---|---|---|---|---|
| person_tracking2 | 0 | 11.1784 | 12.0408 | **+0.86 cm** |
| person_tracking2 | 1 | 11.3900 | 12.0240 | **+0.63 cm** |
| person_tracking | 0 | 7.5461 | 7.5157 | −0.03 cm |
| person_tracking | 1 | 7.5316 | 7.7984 | +0.27 cm |

偏移量（0.63–0.86cm）与实验 F 所报的阈值极差（crowd2 +0.82、crowd3 +0.61）
**同量级**——即版本漂移足以污染敏感度曲线的判读。

## 二、范围裁定：为什么是 21 run 而不是 63 run

交接笔记提出一个待查项：`online_fps` 在 r29（crowd2 seed1 ≈ 0.72）与
r30/r31（≈ 0.40）之间差约 1.8 倍。若该差异来自**代码**，则"默认关 =
行为不变"的声明需复核，0.30/0.45 臂也须重跑（→ 63 run）。

### 2.1 直接依据（决定性的、与 fps 无关）

**裁定 21 run 的依据是代码同一性，不是 fps。**

1. **r30/r31 的核心代码与 HEAD 逐位相同**：
   `git log 715d7bd0..HEAD -- utils/ slam.py gaussian_splatting/` 为**空**，
   且 715d7bd0（2026-09-13 20:24，账本族最后一笔）是 r30 config 提交
   `4727bed4`（09-14 18:50）与 r31 config 提交 `dcb2208a`（09-15 01:52）的
   共同祖先（`merge-base --is-ancestor` 均 YES）。r30/r31 批运行于其 config
   提交之后 → 运行代码 == HEAD 核心代码。
2. **唯一的非门控行为差异 = SWBA 雅可比修复本身**。对
   `8f981fc6`(r29 运行期)..`c37adebf`(r30 运行期) 的核心 diff 逐文件核过：
   `loop_closure.py`（app_backend=netvlad 分支）、`slam_backend.py`
   （depth_reanchor）、`slam_frontend.py`（MaskStability 账本）、
   `eval_utils.py`（`MONOGS_DEPTH_RATIO_DEBUG` 环境变量）**全部默认关/门控**；
   `mask_stability.py`、`place_recognition.py`、`mast3r_verify.py`、
   `depth_reanchor.py` 为**新增模块**（默认不实例化）；
   `swba.py` 的 `_edge_frozen` i 侧雅可比是唯一无门控的行为改动。
3. **MaskStability 提交对这批臂惰性**：`6978d154`/`f98ed1ac`/`715d7bd0`
   只改 `utils/mask_stability.py`（+测试）；`get_mask_stability_ledger`
   （`utils/mask_stability.py:275-289`）在 `config["MaskStability"]["enabled"]`
   缺失时返回 `None`，调用点（`utils/slam_frontend.py:524`）随即跳过；
   且 r29/r30/r31 的**运行时 merged config 中 `MaskStability` 块均不存在**。
4. **config 继承链未动**：`configs/rgbd/bonn/*.yaml` 与
   `configs/experiments/combined_prune/method.yaml` 自 2026-09-01 起零改动。

⇒ 0.30/0.45 臂已在当前 HEAD 有效代码上，**不需要重跑**。范围 = **21 run**。

### 2.2 旁证（fps），及其边界

fps 只作旁证，**不作判据**（它与 ATE 判据无关，且不可靠——见下）。

- merged 运行时 config 逐行 diff（r29-run vs r30-run，同 crowd2 seed1）：
  6 行不同——`sequence` 名、3 个输出路径、`save_dir`、
  `swba_max_static_conf`(0.38 vs 0.30)。无其它组件差异。
- 方向反证：0.30 门放行 SWBA 更少（crowd2 7% vs 0.38 的 34%，
  `verdict_f_sensitivity.md` §一），若代码是原因，0.30 应**更快**而非更慢。
- 并发分层（用 `*.done` 的 start/finished 时间戳重建每个 run 的真实并发数，
  汇总 r29/r30/r30_seed2/r31/seed3_promotion/fulltable 六份 done）：

  | 序列 | r29 @conc=4 | r30c030 @conc=4 | 比值 |
  |---|---|---|---|
  | balloon | 0.3447 (n=3) | 0.3454 (n=3) | **1.00x** |
  | crowd3 | 0.4405 (n=2) | 0.4317 (n=3) | **1.02x** |
  | balloon2 | 0.4345 (n=3) | 0.3562 (n=3) | 1.22x |
  | crowd | 0.5575 (n=1) | 0.4429 (n=3) | 1.26x |
  | person_tracking | 0.4084 (n=1) | 0.3151 (n=3) | 1.30x |

  **诚实边界**：匹配并发后 balloon/crowd3 差异消失，但 balloon2/crowd/pt
  仍残留 1.2–1.3x——故**不能**说"差异全部来自调度"。该残差与 2.1 的代码
  结论不矛盾：残留通道（机器状态/共驻/热漂移）与**臂间代码差异无关**，
  且 r30/r31 已与 HEAD 同码（2.1 第 1 条），无论残差成因为何都不改变
  21 run 的裁定。fps 的绝对水平受并发强烈影响（全池 mean：conc=4 → 0.380，
  n=80；conc≤3 → 0.57–0.75，n=4），故**跨批 fps 横比无意义**。

> 口径注记：`efficiency_raw.csv` 的 `online_fps` 是**含调度噪声的墙钟读数**，
> 并发数不同时不可跨批比较。本文件所有 fps 比较均在匹配并发下进行。

## 三、实验设计

- **臂**：`r32_regate038_<seq>` = 从 `r29_framegate_<seq>.yaml` 复制，
  **仅改 `save_dir`**（含臂名）——SWBA 阈值、LoopClosure 块逐字段保持 0.38 臂原值
- **序列**：标准 Bonn 7 序列（balloon/balloon2/crowd/crowd2/crowd3/
  person_tracking/person_tracking2）
- **seed**：0, 1, 2（3 seed，与既有 0.30/0.45 臂对齐，保持 n=3 平衡）
- **唯一变量**：**无**。本次是**同 config 重基线**——目的是把 0.38 臂搬到
  与 0.30/0.45 相同的代码版本上，使敏感度曲线三臂可比
- **命名**：**不得沿用 `r29_framegate_*`**——`run_batch.sh:30` 按
  `tables/tracking_raw.csv` 存在性跳过已完成 run，沿用旧名会被全部跳过；
  且覆盖旧 run 目录违反 D3
- **并发策略**：4 fixed worker（2 per GPU），与 0.30/0.45 臂相同

## 四、预注册判据（跑批前锁定）

### 4.1 执行判据

**全 21 run 的 done 行须为 `finished rc=0`**（NOTES 踩坑：judge 只查
"finished" 不查 "rc=0"，曾让 rc=137 的 run 混入判决）。非 rc=0 的 run
单独归因后再决定补跑。

### 4.2 口径判据

**0.38 列一律取 `tables/tracking_raw.csv` 的 col 8（`ate_rmse_cm`，全帧）**，
逐 seed 列出，不只报均值。col 14（keyframe）仅作附表并声明口径差异
（NOTES 踩坑：consolelog 末行 eval 是 col 14，不得当主表值）。

### 4.3 生效验证（DISCIPLINE #9；计数按门实例化、锚定整行形状）

本臂只启用 static_conf 门 ⇒ `correction not applied`（自校验门专属）在本臂
**应为 0，属正常，不得据此判"组件未生效"**。逐 run 核这三项：

| 项 | 命令 | 期望 |
|---|---|---|
| (a) 执行 | `grep -c "edges free=" <consolelog>` | > 0 |
| (b) 拦截 | `grep -cE "SWBA kf=[0-9]+: +static_conf=.*>" <consolelog>` | > 0 |
| (c) 合流 | `grep -c "SWBA gate kf=" <consolelog>` | `(a)+(b) ≤ (c) ≤ (a)+(b)+1` |

**delta 允许 0/1（2026-09-16 跑中实测修正）**：首个 gate 检查可能已 armed 但窗口
未就绪，既不产生执行行也不产生 skip 行，故 `(c)-(a)-(b)` 实测为 0 或 1
（13 个已完成 run 全落在 {0,1}）。原锁定的严格等式 `(c) == (a)+(b)` 会**误判
合格 run 为不合格**——已在 `analyze_r32.py` 与 `prereg_rebase_arms.md` G3 同步放宽。

**禁止用裸模式 `grep -c "SWBA kf="`**：实测正常 run（r29 crowd2 seed0）= 178、
**退化到恒 skip 的 run（r25_gate_crowd2_seed0）= 177**，恒真、不可能失败
（NOTES P23 同形态）。参照值（0.38/crowd2/seed0）：执行 61 / 拦截 117 /
gate 178（61+117=178 ✓）。

新臂同序列同 seed 的 (a)(b) 应与 r29 臂同量级；任一项显著偏离须先归因再收口。

### 4.4 判读判据（跑批前写死，跑后照判；不得为保结论挑数字）

重基线后重出敏感度曲线，对既有结论逐条按**数字触发条件**重判：

| 结论 | 成立条件（全部满足才算成立） |
|---|---|
| pt1 0.38 甜点 | `mean(r32) < min(mean(0.30), mean(0.45))` 且逐 seed 不重叠 |
| 易序列单调（SWBA 越多越差） | crowd2 与 crowd3 上同时 `mean(0.30) < mean(0.38) < mean(0.45)` |
| 定性保证 | **易序列**（balloon/crowd/crowd2/crowd3）全部 ≤5cm；且 pt1 相对 baseline 降幅 ≥30% |

**显著性规则（批间噪声地板）**：r32 是**新批**，与 0.30/0.45 跨批。用
0.30/0.45 臂自身的**批内跨批残差**（seed2@09-15 01:08 批 vs seed0/1@09-14 批）
作噪声地板：实测 balloon −8.7%、crowd **+10.6%**、crowd2 −1.0%、crowd3 +1.2%、
pt1 −0.5%、pt2 **−10.5%**、balloon2 −1.4%（0.45 臂同法：crowd2 −14.6%、
pt1 −12.5%）。⇒ **5–10% 量级的逐序列差在批间噪声内**。
逐序列 `|Δ|` 须超过该序列的噪声地板，或**明确标注"在批间噪声内"**；
只报均值不报逐 seed 视为未达标。

**任一条不成立 ⇒ 结论行改为"不成立/部分不成立" + 止损项，不得保留原判读。**

> **判据勘误（2026-09-16；锁定文本笔误，方向=收窄，非结果导向）**：原锁定行写作
> "除 balloon2（baseline 既有 >5cm）外 7 序列全部 ≤5cm"——该文本**自相矛盾**
> （7 序列去掉 balloon2 只剩 6），且与实验 F 原始判据
> （`verdict_f_sensitivity.md` §三.4「易序列全部 ≤5cm」）及 R33 预注册 G6
> （「易序列（balloon/crowd/crowd2/crowd3）… ≤5cm」）**一致指向易序列口径**，
> 故按易序列判。**两种口径的结论差如实披露**：按"7 序列"字面读，r32 的
> pt1=8.0647、pt2=12.1561 均 >5cm ⇒ 定性保证 **FAIL**；按易序列读 ⇒ **PASS**。
> 分析脚本的收窄改动发生在跑批完成之后（commit 晚于 `r32.done` 的 `batch all done`），
> 故此处**必须**以独立 commit 留下修订痕迹，供复核者判断是否为结果导向。

> **pt1「0.38 甜点」的判据执行补记（2026-09-16，关卡① 复核发现）**：锁定判据为
> `mean(r32) < min(mean(0.30), mean(0.45))` **且逐 seed 不重叠**，但脚本初版
> **只核了与 0.30 的不重叠**，未核 0.45。补齐后：r32 pt1 {7.9691, 8.0671, 8.1580}
> 与 0.30 {8.569, 8.8273, 9.1783} **无重叠** ✓，但与 0.45 {7.7264, 8.5389, 9.1255}
> **有重叠**（0.45 的 seed 7.7264 优于 r32 全部 seed）✗。
> 且两个差距（vs 0.30 = 9.0%、vs 0.45 = 4.7%）均**低于该序列的批间噪声地板
> 12.5%** ⇒ 按 §4.4 显著性规则须标注"在批间噪声内"。
> **故"0.38 是 pt1 甜点"只能在均值层陈述，不构成逐 seed 稳健分离。**

### 4.5 单变量保持

- (a) **r32 vs r29_framegate**：逐字段一致，**仅 `save_dir` 异**（阈值同为
  0.38）。L1 门禁 `test_r32_regate038_configs` 断言（含阈值 0.38 在、
  `swba_min_rel_improve` 不在）。
- (b) **r32 vs r30_conf030/045**：仅 `swba_max_static_conf` + `save_dir` 异
  （经 `test_r30_sensitivity_configs` 锚在 r29 上传递成立）。
- 收口时抽查 ≥1 个 run 的运行时 `config.yml` 与 r29 对应 run 做 diff，
  差异只应限路径。

## 五、成本与风险

- 成本：7 序列 × 3 seed = **21 run**。参考实测：r30_seed2 的 14 job 用 2h30m、
  r30 的 28 job 用 4h45m ⇒ **21 job 期望 2.7–3.7h**（非 1–1.5h）
- 风险 1：远程双卡可能被机器主人占用 → 派发前查 `nvidia-smi`；
  长序列（person_tracking 家族）注意体量，但本臂均为标准 Bonn 短序列，
  2/卡按纪律允许
- 风险 2：跨批 ATE 噪声地板 5–10%（见 4.4）→ 判读已按噪声地板设阈值；
  若 r32 与 r29 原值差异**超出** gatefix 已量化的 0.63–0.86cm 量级，
  须归因（是否有第三个未识别的版本效应）
- 风险 3：`fps` 跨批不可比（并发混杂）→ 判据不依赖 fps

## 六、执行顺序

1. 建 config（7 个）+ L1 门禁（已完成，commit `f3a044ab`）
2. 关卡③：派发前过 `slam-critic`（已执行，修订见 §八）
3. **同步远程 → 查 nvidia-smi → 派 21 run**。同步走 **git bundle 旁路**
   （远程 GitHub SSH 通道不通）：`git bundle create /tmp/x.bundle
   <远端实有HEAD>..dev/v2` → scp → 远端 `git fetch /tmp/x.bundle
   dev/v2:refs/temp/t && git merge --ff-only refs/temp/t`。
   **注意：不要用 `scripts/sync_to_remote.sh`**——其 `:19 BRANCH=mask_fix_iter`
   与头注释（dev/v2）矛盾，会把远程切到掩码线（已核实，见 §八 致命 1）。
   派发命令（P10：禁默认共享 RUN_LIST）：
   ```
   REPAIR_CFGS="r32_regate038_balloon r32_regate038_balloon2 r32_regate038_crowd \
   r32_regate038_crowd2 r32_regate038_crowd3 r32_regate038_person_tracking \
   r32_regate038_person_tracking2" \
   DONE_FILE=r32.done SEEDS="0 1 2" RUN_LIST=/home/jiangwenheng/r32_jobs.txt \
   bash scripts/paper2_fulltable/run_batch.sh
   ```
4. 挂**主动通知**监视器（harness 后台任务，退出即通知；判活用输出文件 mtime
   推进 + 退出通知，不用裸 pgrep）
5. 拉回轻量产物（`--include` console.log / tables/tracking_raw.csv /
   config.yml，加顶层 `.consolelog` 与 `r32.done`）
6. 关卡①：落 verdict 前过 `slam-critic`
7. 更新 `gen_manifest_expF.py`：`gate0.38` 指向 `r32_regate038_{s}_seed{k}`，
   **并同时改 `:57-62` 的硬编码 `date`/`criterion`/`verdict`**（否则重生成会产出
   "新数字 + 旧结论"的自相矛盾 manifest）；重生成 `manifest_f_sensitivity.json`。
   同理更新 `scripts/02_analysis/analyze_expF.py` 的臂指针。
8. 更新 `verdict_f_sensitivity.md`：旧 0.38 列标注为"r29_framegate（09-07 代码，
   2026-09-15 重基线作废）"，新增"重基线"小节承载新数字与新判读。
   **注意**：D3 的"禁止手动编辑"对象是 run 目录**原始输出**；verdict/README/
   manifest 是**要求撰写的记录文件**，明确不在保护之列（DISCIPLINE「results 规范」
   原文），且 D16 要求实验完成时同步更新。故结论行**按新数字原地重写**，
   旧值保留并标"作废"以保证溯源，不是"不改结论行"。
9. 更新骨架与其余引用点（**范围远超 §4.6**，见 §七）
10. 关卡②：论文数字/骨架入表前再过 `slam-critic`
11. NOTES 实验清单追加 + 结论同步；每最小单元 commit，跑完同步远程并确认三方一致

## 七、更新范围（0.38 列散落点，逐处核过）

0.38 臂就是论文的**部署 gate 臂**，其数字出现在 ≥10 处，不止 §4.6：

**live 文档（须更新）**
- `papers/paper2/NARRATIVE.md`：`:39`（摘要句 13.62→7.83）、`:78/:83`（§4.1 主表
  gate 列）、`:99/:102`（§4.2 门控阶梯）、`:161/:166/:171`（§4.6 表）、`:196`、`:245`
- `papers/paper2/REVIEW_skeleton_2026-09-14.md:26`
- `resources/notes/paper2_plan.md:115/:122/:145`（pt1 7.83 vs DynaSLAM 5.4）
- `results/paper2_fulltable/README.md:12-16` 与 `:45`（口径注记 4）
- `NOTES.md:42`（实验清单 #15）、`:482-484`（seed3 晋级结论）
- `results/paper2_fulltable/evidence/manifest.json:208/:223`（seed3 晋级 manifest）
- `results/paper2_fulltable/evidence/verdict_seed3_promotion.md:21/:28`

**冻结历史件（不改，加注记或不加）**
- `configs/experiments/joint_correct/person_tracking_j1.yaml:16`、
  `configs/experiments/depth_reanchor/person_tracking{,_2}_d1.yaml:14`
  ——已关闭实验的**预注册门限文本**，是当时决策的原始记录，不追改
- `resources/notes/strategy_decision_2026-09-09.md`、
  `results/paper2_rollout/DIAGNOSIS_pre_switch.md`——带日期的历史诊断
- `results/joint_correct/README.md` §2.5c——作废声明的出处本身

**跨裁决依赖（须复核并留痕）**
- **R31 的判据参照臂正是 r29_framegate 列**：
  `prereg_r31_selfcheck.md` §三 主判据 = "≤ r29_framegate 同序列值（+3%）"、
  副判据 = "pt1 ≤ 8.2cm（= 7.83 + 5%）"；
  `scripts/02_analysis/analyze_r31.py` 与 `gen_manifest_r31.py` 硬编码该参照。
  `manifest_r31.json` 显示 `r31_selfcheck_0p5` 的 MAIN 失败余量仅
  crowd2 2.7573 vs 参照 2.6201 = **0.137cm**，而 r29 crowd2 三 seed 极差
  0.50cm ⇒ **r32 的 0.38 列若移动 >0.14cm，R31 该臂 MAIN 判定可能翻转**。
  （R31 总体结论——"三门未全过、不晋级"——由副判据**三档全否**
  （8.81/10.25/11.34 全 >8.2）支撑，对参照移动**稳健**；但 0.5% 档
  "MAIN 亦否"这一子句须复核。）⇒ 收口时按新参照重算 R31 判据并如实更新。

**另发现（本次不扩大范围，留用户拍板）**
- 论文 §4.1 主表的 **`final` 列**（以及 §4.2 阶梯的 `swbaonly` 列）运行于
  2026-09-06/09-07（`fulltable.done` 首行 09-06 21:39），**同样早于
  09-09 的雅可比修复**，且 SWBA 在该两臂**是开启的** ⇒ 同属旧代码。
  `baseline` 列不受影响（SWBA 关）。故论文主表目前存在
  `baseline(不受影响) / final(旧码) / gate(旧码，本批修复)` 的版本混排。
  交接笔记明确"范围已核，不要再扩大"，故本次**只**重基线 0.38 臂；
  `final`/`swbaonly` 是否需同批重基线，留用户拍板。

## 八、slam-critic 审查结论与采纳记录（2026-09-15）

第 3 档关卡输出 **Reject**（2 致命 + 5 重大）。逐条独立复核后处置：

| # | 发现 | 复核结果 | 处置 |
|---|---|---|---|
| 致命 1 | `sync_to_remote.sh:19` 硬编码 `BRANCH=mask_fix_iter`，与头注释（dev/v2）矛盾，执行会把远程切到掩码线 | **成立**（`:19` 实为 mask_fix_iter；本机 `git branch -vv` 确认 mask_fix_iter=ee4175c8 与本次无关） | **采纳**：改走 bundle 旁路；§六 第 3 步已写明禁用该脚本 |
| 致命 2 | §四生效验证锁定 `SWBA kf=` 是恒真模式 | **成立**（实测 r29 crowd2 seed0=178、r30=178、**恒 skip 的 r25=177**） | **采纳**：§4.3 改为 `edges free=` + `static_conf=.*>` + 合流等式 |
| 重大 1 | "原结论行不改（D3）"误引 D3 | **成立**（D3 原文明确 verdict/README/manifest **不属**保护列） | **采纳**：§六 第 8 步改写为"原地重写 + 旧值标作废" |
| 重大 2 | 更新范围缺 ≥10 处 | **成立**（逐处核过，见 §七） | **采纳**：§七 全列 |
| 重大 3 | R31 判据参照即 r29 列，未声明 | **成立**（`manifest_r31.json` MAIN 余量 0.137cm） | **采纳**：§七 增"跨裁决依赖"并列入收口动作 |
| 重大 4 | 主判据恒真；manifest 硬编码旧结论 | **成立**（`gen_manifest_expF.py:57-62` 硬编码日期/判据/结论） | **采纳**：§六 第 7 步写入同步改；旧"可复算性"降为 §4.1/4.2 |
| 重大 5 | 风险 3 措辞"同批"不实；批间噪声未量化 | **成立**（0.30/0.45 为 09-14/15 批，r32 为新批；跨批残差实测 5–10%） | **采纳**：§4.4 写入噪声地板规则；§五 风险 3 改写 |
| 次要 | B3"匹配并发差异消失"过强 | **成立**（balloon/crowd3 消失，但 balloon2 1.22x / crowd 1.26x / pt 1.30x 残留） | **采纳**：§2.2 降级为旁证并写明边界 |
| 次要 | §四副判据配对写错（r32 与 r29 阈值**相同**） | 成立 | **采纳**：§4.5 拆 (a)(b) 两条 |
| 次要 | B1"差异仅 4 处"少算 | 成立（实为 6 行） | 采纳：§2.2 已改 |
| 次要 | 工时低估 | 成立（实测 21 job ≈ 2.7–3.7h） | 采纳：§五 已改 |
| 次要 | 派发参数未锁定 | 成立 | 采纳：§六 第 3 步已给全参数 |
| 次要 | verdict_f §一 计数表另有一处错误（pt1-0.45 写作 86/88，实测 gate=115） | **成立**（未在本批判据内，但同文档） | 收口时一并如实修正 |

**未能验证项（如实记录，不得当作"已过"）**
- r29/r30 运行时的**远程 HEAD 无法硬证**：远程 reflog 仅回溯到 2026-09-13。
  以"r29 config 提交日 = 运行日（09-07）+ `a21e0773` 非其祖先"间接推定。
- 运行时 **conda 环境快照**无历史 → r32 与 r30 之间可能存在依赖差异，
  属任何重基线都躲不开的残差，已知并声明。
- 未跟踪工件（`weights/{dust3r,netvlad}`、datasets）仅核 mtime 早于 09-14，
  未做 sha256 登记。

## 九、纪律映射

- 预注册先行（本文件）✓
- 零代码改动（纯 config 重基线）✓
- 3 seed（与既有臂对齐；非方法迭代故不适用 2-seed 筛选档）✓
- 单变量（本次"无变量"，是版本对齐）✓
- 生效验证（§4.3，计数按门实例化 + 整行形状 + 合流等式）✓
- 判据先锁定、跑批在后（本文件定稿于派发之前）✓
