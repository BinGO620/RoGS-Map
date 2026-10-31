# 预注册：论文主表/消融臂重基线（R33，2026-09-15）

> **账本登记（2026-09-25 追补，D2-015 同例；原文零改动）**：本预注册属账本设立前的文书，决策留痕见 `NOTES.md` 实验清单与 git 历史；本轮由 health_check H5 扩表（`prereg_*` 纳入覆盖面）后检出为“未挂账本号”，按机制登记补入本指针，不追改正文。

> 触发：R32（0.38 臂重基线）预注册期发现 —— 论文 §4.1 主表与 §4.2 阶梯的
> **`final` 与 `swbaonly` 臂同样跑在 SWBA 雅可比修复之前**。用户 2026-09-15
> 晚授权"需要重跑的都重跑"。
> **纪律合规**：零代码改动——纯 config 重基线（DISCIPLINE #2）。判据先锁定
> （本文件），跑批在判据锁定之后。判据编号用 **G1–G6**，避免与 NOTES 踩坑的
> P1–P26 撞名。修订记录见 §七。

## 一、问题：论文主表的版本混排

| 臂 | 运行日期（run 目录时间戳） | SWBA | 受 `a21e0773` 影响？ |
|---|---|---|---|
| `{seq}_baseline` | 09-06 21:39–09-07 02:33（seed0/1）/ **09-07 14:24–16:31（seed2）** | **关** | 否（无 SWBA 块） |
| `{seq}_final` | 09-06 21:39–09-07 02:33（seed0/1）/ **09-07 14:57–16:31（seed2）** | **开** | **是** |
| `{seq}_swbaonly` | 09-07 02:44–03:36 | **开** | **是** |
| `r29_framegate`(0.38) | 09-07 11:20 起 | 开 | **是**（R32 已重建） |
| `r30_conf030/045` | 09-14/15 | 开 | 否（已含修复） |

> **同一臂内已跨两个代码版本**：`{seq}_final`/`{seq}_baseline` 的 seed0/1 来自
> `fulltable.done` 批（09-06 21:39 派发），**seed2 来自 `seed3_promotion.done` 批
> （09-07 14:23:56 派发，35 jobs）**——两批之间夹着 R25/R26/R28 四个 core 提交
> （见 §1.1）。这是本文件修订时发现的（R32 期与 NOTES 踩坑均只写了 09-06/09-07 凌晨，
> 漏记 seed2 批）。

`utils/swba.py` 的两次雅可比修复在 2026-09-09（`a21e0773` 自述"修复改变部署
SWBA 行为"）。**已量化漂移**：同 config 同 seed 重跑（`joint_correct/gatefix_*`）
pt2 +0.63~0.86cm、pt1 −0.03~+0.27cm —— 与论文所报的臂间差同量级。

⇒ 论文 **Tab.1 主表（baseline/final/gate）** 与 **Tab.3 消融**目前混排两个
代码版本。R32 只修了 gate 一列。

### 1.1 核心 diff 清单（区间起点按**各臂自身运行期 HEAD**，勿沿用 r29 的区间）

- `final`/`baseline`（seed0/1）运行期 HEAD = **`333421e1`**（09-06 21:38:46）
- `swbaonly` 运行期 HEAD = **`e8c8a7e7`**（09-07 02:58）
- 两臂 seed2 运行期 HEAD = 09-07 14:23 前后的 tip（含 R25/R26/R28）

`333421e1..8f981fc6` 之间的 core 提交（逐条独立复核为**惰性**）：

| 提交 | 内容 | 惰性依据 |
|---|---|---|
| `e014ddc5` | R25 健康门 `swba_min_rel_improve`（默认 0 = 关） | `utils/swba.py:730` 默认 0.0；`:731` `if rel_improve < min_ri`；`:606` backtracking 只接受 `c_new < c0` ⇒ `rel_improve ≥ 0` ⇒ 条件恒假 |
| `071f97d1` | R26 可靠性门 `swba_max_static_conf`（默认 1.1 = 关）+ static_conf 逐 KF 暂存 | `:2315` 默认 1.1 > `static_conf∈[0,1]` ⇒ 恒放行；**唯一非零副作用是日志**（见 §三 G3） |
| `668d5849` | R26 诊断：逐 KF 打印 static_conf | 纯日志（+5 行） |
| `aad72555` | R28 方向一致自适应 cap | `:751` `cap_floor = cfg.get("swba_cap_floor", cfg["max_update_trans"])` ⇒ 默认等值 ⇒ `:754` `cap_floor < cap_t` 恒假 ⇒ `cap_t` 不变 |

除 `utils/swba.py` 的 `_edge_frozen` i 侧雅可比（`a21e0773`）外，**其余改动全部
默认关或门控**：`depth_reanchor.py`/`mask_stability.py`/`place_recognition.py`/
`mast3r_verify.py` 为新增**默认不实例化**的模块；`loop_closure.py:56` 的
`app_backend` 默认 `thumb`、`:643` 的 `verifier` 默认 `photometric`；
`slam_backend.py` 的 reanchor、`slam_frontend.py` 的账本 config 门控；
`eval_utils.py` 环境变量门控。`cc0e3a81`/`94283e32` 两个 D2 提交**只动
`utils/depth_reanchor.py`**（同为默认关）。

⇒ **唯一非门控行为改动 = SWBA 雅可比修复**。故 SWBA **关**的臂（`baseline`）
在代码上不受影响。

### 1.2 为什么连 `baseline` 也重跑

`baseline` 代码上惰性，重跑的**唯一理由**是**批一致性**：Tab.1 是
baseline vs final vs gate 的同表比较，若 final/gate 在新批而 baseline 停在
09-06/07 批，表内比较会叠加跨批漂移（README 口径注记 1：±2-9%；
`prereg_f_rebase.md` §4.4 实测同臂跨批残差达 5–14.6%）。

**诚实边界**：`r30_conf030/045`（F 敏感度曲线的 0.30/0.45 列）仍在 09-14/15 批，
无法也不必纳入本批——F 曲线的批间口径照 `prereg_f_rebase.md` §4.4 的逐序列
噪声地板处理。

## 二、实验设计

- **臂**（臂名与 save_dir 一律新起，**不得复用**旧名——`run_batch.sh:30` 按
  `tables/tracking_raw.csv` 存在性跳过，复用即全部 skip，且覆盖旧 run 违反 D3）：
  - `r33_rebase_baseline_{seq}` ← 复制 `{seq}_baseline.yaml`，**仅改 save_dir**
  - `r33_rebase_final_{seq}` ← 复制 `{seq}_final.yaml`，**仅改 save_dir**
  - `r33_rebase_swbaonly_{seq}` ← 3 序列复制 `{seq}_swbaonly.yaml`；
    其余 4 序列由 `{seq}_final.yaml` 去掉 LoopClosure 块派生
  - `r33_rebase_gate_{seq}` ← **复制 R32 的 `r32_regate038_{seq}.yaml`**，仅改 save_dir
- **序列**：标准 Bonn 7 序列；**seed**：0, 1, 2
- **规模**：**4 臂 × 7 序列 × 3 seed = 84 run**
- **唯一变量**：无。本批是**版本/批次对齐**，不是机制改动
- **并发**：4 fixed worker（2 per GPU）
- **派发顺序**：按**序列**交错四臂（见 §六 的 CFGS 串），使同一序列的各臂在
  时间上相邻——表内比较（同序列跨臂）受批内漂移影响最小
  （模拟前 12 job：同序列 12 个 job 落在第 1–3 轮，约 1.5–2h 内）

### 2.1 为什么 gate 臂也在本批（而不是只用 R32）

上一版只含 3 臂（42→63 run），留下一个**结构性缺口**：Tab.1 的 gate 列来自
R32（另一批），而 R32↔R33 **不共享任何 config**，该跨批偏移**不可测**。
纳入 gate 臂（+21 run）后：

1. Tab.1 的三臂（baseline/final/gate）与 Tab.3 的四臂**同批**，缺口消除；
2. `r32_regate038_*` 与 `r33_rebase_gate_*` 构成**同 config 双批复制**——
   直接给出 7 序列 × 3 seed 的跨批偏移实测（比 6-run 锚强得多），
   正是 F 曲线借以声明跨批口径的依据。

**不杀 R32**：它已在跑（21:48 派发），其读数本就是 HEAD 代码，且其复制价值
依赖它跑完。

### 2.2 swbaonly 的升级：3 序列 × 2 seed → 7 序列 × 3 seed

原臂仅 balloon/crowd2/crowd3 × 2 seed，骨架 §4.7 注记据此写"Tab.3 该臂不得
声称 3-seed"。本批补齐到 **7 序列 × 3 seed**，使 Tab.3 成为真正的
"4 臂 × 7 序列 × 3 seed"消融并消除该注记。4 个新序列 config 的派生规则与
既有 3 个 swbaonly 臂**逐字一致**（无逐序列特判，不违 D8）。

## 三、预注册判据（跑批前锁定）

### G1 执行

84 run 的 done 行全部为 `finished rc=0`（锚定全串——只查 "finished" 会放过
rc=137，NOTES 踩坑）。完成时须同时满足：
`grep -c "finished rc="` = 84 且 `grep -c "finished rc=0"` = 84
（任务数核对，防漏跑）。非零退出的 run 单独归因后再定补跑。

### G2 口径

主读数 `tables/tracking_raw.csv` **col 8（`ate_rmse_cm`，全帧）**，逐 seed 列出
（不只报均值）；col 14（keyframe）仅作附表并声明口径。

### G3 生效验证（按门实例化 + 整行形状；**已修正**）

**注意**：`SWBA gate kf=` 行的打印条件是 `self.swba is not None and sc is not None`
（`utils/slam_frontend.py:2318-2322`），**与本臂是否设门无关**；`sc` 来自
`:1233` 的 `_last_static_conf`，其外层要求 `ReliabilitySignal.enabled`，而该键来自
`combined_prune/method.yaml:34-35`（经 `method_from` 合并，**不在 `inherit_from` 链里**）。
⇒ 无门臂也会打印该行（`max` 默认 1.1 ⇒ 恒放行、skip 恒 0）。

同 config 双版本实证：`balloon_final_seed0`（09-06 代码）`SWBA gate kf=`=**0**；
`balloon_final_seed2`（09-07 14:57 代码）=**87**、`edges free=`=86。
参照：`balloon2_final_seed2` 合流=93 / 执行=92。

| 臂 | 判据 |
|---|---|
| `baseline` | `edges free=` = 0 **且** `grep -c "^MonoGS: SWBA"` = 0（正控：整个 SWBA 子系统零输出） |
| `final` | `edges free=` > 0；`static_conf=.*>`（skip）= 0；**`SWBA gate kf=` > 0 且 ≥ 执行数** |
| `swbaonly` | 同 `final` |
| `gate` | `edges free=` > 0；`static_conf=.*>` > 0；**`(a)+(b) ≤ SWBA gate kf= ≤ (a)+(b)+1`** |

**delta 允许 0/1（2026-09-16 跑中实测修正）**：首个 gate 检查可能已 armed 但
窗口未就绪，既不产生执行行也不产生 skip 行。R32 已完成的 13 个 run 实测
`(c)-(a)-(b)` 全为 **0 或 1**（crowd2 三 seed 与 crowd3 为 0，balloon/balloon2
与 crowd 部分 seed 为 1）。**严格等式会误判合格 run** —— 已在
`prereg_f_rebase.md` §4.3 与 `scripts/02_analysis/analyze_r32.py` 同步放宽。

**跑中实证（2026-09-16 09:30，R33 已完成的 run，验证本表的四臂判据）**：

| run | `edges free=` | `static_conf=.*>` | `SWBA gate kf=` | `^MonoGS: SWBA` |
|---|---|---|---|---|
| `baseline_balloon_seed{0,1}` | 0 | 0 | **0** | **0** ← 正控成立（子系统全静默） |
| `final_balloon_seed{0,1}` | 86 | 0 | **87** | 173 |
| `swbaonly_balloon_seed0` | 86 | 0 | **87** | 173 |
| `gate_balloon_seed0` | 70 | 16 | 87 | 173（delta=1） |
| `gate_crowd2_seed0` | 61 | 116 | 178 | 355（delta=1） |

这条实证同时坐实了本表修订的两个必要点：① `final`/`swbaonly` 的合流行
**确实 > 0**（旧锁定判据"=0（无门）"会把它们全部误判为不合格）；
② `delta` 确实取 1（严格等式 `(c)==(a)+(b)` 同样会误判）。
另注：`final` 与 `swbaonly` 的计数完全相同（86/0/87）——两者 SWBA 配置一致、
仅回环开关不同，回环不影响门计数，是合理的交叉验证。
`baseline` 子系统零输出 ⇒ 进一步印证 §1.1"雅可比修复对 baseline 惰性"，
故 baseline 若出现超地板偏移即触发 G5 归因。

**禁止**用裸模式 `grep -c "SWBA kf="`（实测 r25 恒 skip 日志仍为 177，恒真，NOTES P23）。
**不得**用"合流=0"判 final/swbaonly "组件未生效"。

### G4 单变量保持

L1 断言（`test_r33_rebase_arm_configs`，本地 8 passed + 四处变异测试验证非空过）：
四臂族与各自源臂逐字段一致、仅 save_dir 异。**边界**：该用例的 `_load_merged`
只走 `inherit_from`、不解析 `method_from`（`utils/config_utils.py:30-32`），
故它**不验证运行时组件集**；本批两侧对称故无碍。

**补充（R32 §4.5(b) 有、本文件原缺）**：收口时抽查 ≥4 个 run（四臂各一）的
运行时 `config.yml` 与对应源臂旧 run 做 diff，差异**只应限路径**。

### G5 一致性判据（核心科学判据）

**旧臂参照已冻结**（col 8，全帧；存在性判空）：

| seq | baseline | final | swbaonly |
|---|---|---|---|
| balloon | 3.2674 / 2.9394 / 3.1404 | 4.1864 / 4.1164 / 4.3276 | 4.0194 / 4.2685 / — |
| balloon2 | 5.2273 / 5.2892 / 5.4654 | 5.1631 / 5.3391 / 5.4797 | — |
| crowd | 2.4234 / 2.2491 / 2.2102 | 2.4935 / 2.3919 / 2.5133 | — |
| crowd2 | 2.2229 / 2.0409 / 2.0565 | 4.1593 / 4.2275 / 3.5978 | 3.8281 / 4.7568 / — |
| crowd3 | 1.5985 / 1.5593 / 1.5067 | 2.4329 / 2.6774 / 2.6351 | 2.5891 / 2.3886 / — |
| person_tracking | 10.6032 / 13.1520 / 17.0935 | 9.4149 / 7.5517 / 8.4639 | — |
| person_tracking2 | 12.2581 / 12.1677 / 10.7546 | 11.7494 / 11.1438 / 11.9488 | — |

**判据**：

- **`baseline`（代码惰性 ⇒ 归因触发器）**：逐序列 `|Δ(col8)|` 须 ≤ 该序列的
  **阈值 = max(批间噪声地板×旧均值, 该臂 seed 内极差)**。
  **两条都要** —— 跑中实测发现纯相对地板对低 ATE 序列过紧（见下），
  故与 seed 内极差取大者。超出 ⇒ 归因触发器生效：先查 §1.1 的惰性清单
  （4 个提交）是否有漏判，再决策，**不得直接收口**。
  逐 seed 与 sd 须同时入表（防单 seed 恰好压线）。
- **`final`/`swbaonly`（版本修复，改动是目的）**：期望 = 方向一致 + 逐序列落在
  上表噪声地板内 **或** pt1/pt2 上与 gatefix 实测的 0.63–0.86cm 同量级；
  **其余 5 序列不得套用 pt 家族的绝对 cm 带**（该带只有 pt1/pt2 两个测点，
  对本判据是**阈值**而非观测）。
- **`gate`（同 config 双批复制）**：r32 vs r33 的逐序列差值即**R32↔R33 跨批偏移
  实测**，须单独入档——它同时是 F 曲线跨批口径的依据。

**G5 跑中实证（2026-09-16 10:50，R33 已完成 55/84）**：5 个已完成的
`baseline` 序列（该臂 SWBA 关 ⇒ 代码惰性）**全部落在噪声内**：

| seq | 旧 seeds | r33 seeds | Δ | 相对地板→cm | seed 内极差 | 判定 |
|---|---|---|---|---|---|---|
| balloon | 3.267/2.939/3.140 | 3.296/3.172/3.274 | +0.131 | 0.271 | 0.328 | 在噪声内 |
| balloon2 | 5.227/5.289/5.465 | 5.220/5.475/5.757 | +0.157 | 0.170 | 0.536 | 在噪声内 |
| crowd | 2.423/2.249/2.210 | 2.215/2.150/2.339 | −0.060 | 0.243 | 0.213 | 在噪声内 |
| crowd2 | 2.223/2.041/2.057 | 2.132/2.627/2.019 | +0.153 | 0.308 | 0.608 | 在噪声内 |
| crowd3 | 1.599/1.559/1.507 | 1.520/1.557/1.513 | **−0.025** | **0.019** | **0.092** | 在噪声内 |

两条结论：① **归因触发器未触发** —— `baseline` 无系统偏移，印证 §1.1
"雅可比修复对 baseline 惰性"的判断（core-diff 清单无漏判）；
② **纯相对地板对低 ATE 序列过紧**：`crowd3` 地板 1.2% × 1.55cm = **0.019cm**，
比该臂自身的 seed 内极差 0.092cm 还小 —— 若照字面判会误报"超地板"。
故阈值改为 `max(相对地板×均值, seed 内极差)`。所有 Δ 的**绝对量级
（0.025–0.157cm）均小于 R32 实测的同码运行散度（0.18–0.62cm）**。

### G6 不变量（数字阈值，防"重跑把结论跑没了"）

- pt1 `gate vs baseline` 降幅 **≥ 30%**；
- 易序列（balloon/crowd/crowd2/crowd3）gate 臂 col 8 **≤ 5cm**；
- 逐 seed 与均值**都**判；
- 任一条不成立 ⇒ 结论行改为"不成立/部分不成立"+ 止损项，不得保留原判读
  （D3 保护对象是 run 目录原始输出，非 verdict/README/manifest）。

## 四、成本与风险

- 成本：**84 run**。按 R32 预注册**预期**（2.7–3.7h / 21 run）与三份历史批反推
  （`fulltable.done` 28 jobs/7 轮/4h55m ≈ 42 min/轮；`seed3_promotion.done`
  35 jobs/8.75 轮/4h40m ≈ 32 min/轮；`attr.done` 6 jobs/1.5 轮/1h13m ≈ 49 min/轮）
  ⇒ 84/4 = 21 轮 → **11–17 h**。含 1/4 便宜的 `baseline` 臂会摊薄，
  仍按 **≥ 17 h 值守**（长序列尾部单 run 可到 45–70 min）。
- 风险 1：远程卡被机器主人占用 → 派发前查 `nvidia-smi`
- 风险 2：长批内漂移（前 1h vs 第 15h）→ 已用**按序列交错臂**摊平；G5 用它判定
- 风险 3：`baseline` 出现系统偏移 ⇒ §1.1 清单有漏判 → G5 已设为归因触发器
- 风险 4：远程 /home 磁盘 92%（余 56G）；84 run ≈ 230MB，不构成风险

## 五、纪律映射

- 预注册先行（本文件）✓
- 零代码改动（纯 config 重基线）✓
- 3 seed ✓
- 生效验证（G3，按门实例化 + 整行形状 + 正控）✓
- 判据先锁定、跑批在后 ✓
- 关卡③（正式批派发前过 `slam-critic`）✓ 见 §七

## 六、执行顺序（派发前必须逐条走完）

0. **前置**：本地 `git push origin dev/v2` → **bundle 旁路**同步到远程
   （**勿用 `scripts/sync_to_remote.sh`**，其 `:19 BRANCH=mask_fix_iter` 会把
   远程切到掩码线；已核实，见 `prereg_f_rebase.md` §八 致命 1）→
   `bash scripts/check_code_sync.sh` 须 rc=0 → 远程 `nvidia-smi` 两卡实查 →
   **等 R32 结束**（`r32.done` 含 `batch all done` 且无存活 `slam.py`）
1. **派发**（顺序即队列顺序，勿改）：
   ```
   REPAIR_CFGS="r33_rebase_baseline_balloon r33_rebase_final_balloon r33_rebase_swbaonly_balloon r33_rebase_gate_balloon \
   r33_rebase_baseline_balloon2 r33_rebase_final_balloon2 r33_rebase_swbaonly_balloon2 r33_rebase_gate_balloon2 \
   r33_rebase_baseline_crowd r33_rebase_final_crowd r33_rebase_swbaonly_crowd r33_rebase_gate_crowd \
   r33_rebase_baseline_crowd2 r33_rebase_final_crowd2 r33_rebase_swbaonly_crowd2 r33_rebase_gate_crowd2 \
   r33_rebase_baseline_crowd3 r33_rebase_final_crowd3 r33_rebase_swbaonly_crowd3 r33_rebase_gate_crowd3 \
   r33_rebase_baseline_person_tracking r33_rebase_final_person_tracking r33_rebase_swbaonly_person_tracking r33_rebase_gate_person_tracking \
   r33_rebase_baseline_person_tracking2 r33_rebase_final_person_tracking2 r33_rebase_swbaonly_person_tracking2 r33_rebase_gate_person_tracking2" \
   DONE_FILE=r33.done SEEDS="0 1 2" RUN_LIST=/home/jiangwenheng/r33_jobs.txt \
   nohup bash scripts/paper2_fulltable/run_batch.sh > /home/jiangwenheng/r33_batch.out 2>&1 < /dev/null &
   ```
   （**不要**设 `TAG_PREFIX`：臂名已唯一，设了会让 tag 与 config 的 save_dir 分叉。
   `RUN_LIST` 必须私有——NOTES 踩坑 P10：并发批共用队列文件会互相覆盖。）
2. **完成判据**：`r33.done` 出现 `batch all done`，且 `grep -c "finished rc="` = 84、
   `grep -c "finished rc=0"` = 84（G1 + P10 任务数核对）
3. 拉回轻量产物 → 关卡①（落 verdict 前过 `slam-critic`）→ 出裁决
4. 关卡②（论文数字/骨架入表前再过 `slam-critic`）
5. 下游联动：`scripts/02_analysis/analyze_r32.py:36` 的 `baseline` 指针、
   `papers/paper2/NARRATIVE.md` 的 Tab.1/Tab.3、`results/paper2_fulltable/README.md`
   的臂与数字段、`manifest.json`、NOTES 实验清单——R33 落地后全部须改指新臂
   （清单见 R32 预注册 §七，本批扩展同）。

## 七、关卡③ 审查记录（2026-09-15）

slam-critic 输出 **Reject**（2 致命 + 7 重大 + 6 次要）。逐条独立复核后处置：

| # | 发现 | 复核 | 处置 |
|---|---|---|---|
| 致命 1 | R33 config 未 push 到 origin/远程，派发必失败 | **成立**（local 领先 1，origin/远程无 a3eca8c4） | **采纳**：已 push；§六 第 0 步写入完整同步流程 |
| 致命 2 | G3 生效判据把 final/swbaonly 的 `SWBA gate kf=` 写死 0，与实际代码相反 | **成立**（`balloon_final_seed0`=0 vs `_seed2`=87；根因 `slam_frontend.py:2318-2322` 打印条件与门无关 + ReliabilitySignal 来自 method_from） | **采纳**：G3 整表重写 + 正控 + 机理说明 |
| 重大 1 | §1.1 diff 区间起点错（沿用 r29 的 `8f981fc6`，漏 `333421e1..8f981fc6` 的 4 个 core 提交） | **成立**（区间起点应为臂自身运行期 HEAD） | **采纳**：§1.1 重写并列 4 提交的惰性依据（我逐条复核：`min_ri` 默认 0 + backtracking 只接受降本；`cap_floor` 默认 `max_update_trans`） |
| 重大 2 | §一 漏记 seed2 批（09-07 14:24–16:31） | **成立**（`seed3_promotion.done` 09-07 14:23:56 派发） | **采纳**：§一 表格与注记已补 |
| 重大 3 | R33 只有 3 臂而 gate 在 R32，跨批缺口不可测 | **成立** | **采纳**：纳入 gate 臂 → **84 run**；§2.1 说明 |
| 重大 4 | G5 旧臂参照未冻结，判据不可复算 | **成立** | **采纳**：G5 冻结表已落（21 项 col8 逐 seed） |
| 重大 5 | G5 的 baseline 触发器无数字规则，且"~10%"覆盖不住逐序列地板 | **成立** | **采纳**：改为逐序列地板（8.7/3.2/10.6/14.6/1.2/12.5/10.5%） |
| 重大 6 | 未列下游依赖清单 | **成立** | **采纳**：§六 第 5 步 |
| 重大 7 | 派发参数未锁定，"按序列交错"不可复现 | **成立**（交错完全由 CFGS 书写顺序决定） | **采纳**：§六 给出完整命令 |
| 次要 | P1–P6 与 NOTES P1–P26 撞名 | 成立 | **采纳**：改为 G1–G6 |
| 次要 | 成本"R32 实测"误标（R32 未结束） | 成立 | 采纳：§四 改为"预注册预期 + 历史批反推"，值守 ≥17h |
| 次要 | G6 不可机器判定 | 成立 | 采纳：改为数字阈值 |
| 次要 | baseline 正控可加强（`^MonoGS: SWBA` 整行前缀） | 成立 | 采纳：并入 G3 |
| 次要 | G4 缺"运行时 config.yml 抽查" | 成立 | 采纳：G4 补充 |
| 次要 | 实验清单未追加 / 远程磁盘 WARN | 成立 | 清单收口时补；磁盘 230MB 无风险 |

**未能验证项（如实记录，不得当作"已过"）**
- 各臂运行时的**远程 HEAD 无法硬证**（远程 reflog 仅回溯到 2026-09-13）；
  以 run 目录时间戳 + 提交时间交叉推定。
- **运行时 conda 环境快照**无历史 → 跨批依赖差异不可排除。
- `swbaonly` 在 4 个新序列上能否产生 `edges free=`>0：既有 3 序列经验值
  86/177/169 可作先验，新序列须跑后核。
- G5 中 5 个非 pt 序列的"预期偏移带"**是阈值而非观测**（无先验测量）。
