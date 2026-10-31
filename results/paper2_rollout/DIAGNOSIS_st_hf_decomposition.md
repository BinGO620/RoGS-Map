# st_hf 分解诊断（diag_e1 / diag_e2 / rollbase）— 进行中

目的：f3_st_hf 在部署机 gate 全开配置下 ATE 34.68cm（v1 同病 35.7），
分解各组件对该数字的贡献。裸 MonoGS 复现 2.80cm（MonoGS 动态崩坏修复
证据链的对照点，见 resources/notes/paper2_plan.md §六）。

## 分解表

| 配置 | mapping/insertion | SWBA/回环/门控栈 | st_hf ATE | 状态 |
|---|---|---|---|---|
| gate（部署机全开） | T/T | on | 34.68 cm | 已归档 |
| E1 = gate − mask_insertion | T/F | on | **14.55 cm** | ✅ 2026-09-10 |
| E2 = gate − mask_mapping − mask_insertion | F/F | on | **9.11 cm** | ✅ 2026-09-11 |
| rollbase（Combined-Prune 裸臂） | **F/F（默认值）** | off | **33.53 cm** | ✅ 2026-09-11 |
| E3 = rollbase + mapping/insertion 全开 | T/T | off | **3.35 cm** | ✅ 2026-09-11 |
| 裸 MonoGS 复现 | 无（无掩码机制） | off | 2.80 cm | 已归档 |

**rollbase 有效配置注记**（重要，推翻"rollbase 掩码开"的先验）：
method.yaml 的 SemanticMask 只写 enabled=true，代码默认
mask_mapping=False / mask_insertion=False（semantic_mask.py:85、
slam_frontend.py:507），故 rollbase 的建图/插入掩码**实际全关**；
enabled=true 仍带动辅助消费（dyn_coverage→occ_tighten、
max_mask_ratio 跳帧、mask QA），但这些不直接遮挡建图。

## E1 读数细节（证据：远程 diag_e1_st_hf_seed0.consolelog）

- 终值 RMSE ATE = **0.14552 m**（39 次 eval 的最后一行）。
  注：会话交接曾记 14.83，是第 27 次 eval 附近的中途读数；峰值 14.89（第 26 次）。
- **曲线形态**（关键机制证据）：
  - eval 1–14（对应前段）：0.80–1.75 cm，开局干净；
  - eval 15 起发散：2.90 → 7.23 → 9.49 → … 单调爬升至 ~14.9 cm 后平台化。
- run 目录：远程 `results/paper2_rollout/diag_e1_st_hf_seed0/`
  （tables 落地晚于 Eval 行，final save 阶段长）。
- config：`configs/experiments/paper2_rollout/diag/diag_e1_st_hf.yaml`
  （单变量 = mask_insertion off，其余与 gate 一致；SWBA/LoopClosure 全开）。

## E2 读数细节（证据：远程 diag_e2_st_hf_seed0.consolelog，rc=0）

- 终值 RMSE ATE = **0.09114 m**（45 次 eval；tables 已落地）。
- **曲线形态**：eval 1–14 为 0.73–1.35cm 干净开局；**第 15 次 eval 起跳变**
  （4.16→5.79→…）爬升至 ~9.1cm 平台化。
- config：`diag/diag_e2_st_hf.yaml`（单变量增量 = mask_mapping 也 off）。

## E3 读数细节（证据：远程 diag_e3_st_hf_seed0.consolelog，rc=0）

- 终值 RMSE ATE = **0.03348 m**（45 次 eval，tables 已落地；峰值 3.58cm）。
- **曲线形态**：开局 0.80cm，全程无悬崖、无跳变，平滑漂移至 3.35cm——
  2×2 中唯一不发生中段发散的 Combined-Prune 变体。
- config：`diag/diag_e3_st_hf.yaml`（rollbase 继承链 + mask_mapping=T +
  mask_insertion=T，栈全 off）。

## 判读（只写事实，2026-09-11 E3 落地后定稿）

1. **中段悬崖的分布**：E1/E2/rollbase（悬崖，eval 14–15 从 ~1–1.8cm 跳至
   ≥4cm 后平台化）的共同点 = 掩码与栈至少一边全关且另一边为 on 的
   组合中掩码 off 的三个；**唯一无悬崖的是 E3（掩码开+栈关）**。
   → 掩码（mapping/insertion）阻止悬崖；栈不阻止。
2. **栈在不悬崖的配置上重造灾难（破坏性交互实锤）**：
   - 掩码开：栈 off 3.35 → 栈 on 34.68（+31.3cm）；
   - 掩码关：栈 off 33.53 → 栈 on 9.11（−24.4cm，栈此时是保护性的）。
   栈的作用方向完全取决于掩码开关——gate 的 34.68 = "掩码的修复作用
   被栈反转成毒药"。
3. **单组件分解（栈 on 侧）**：insertion +20.13（E1→gate，开局崩坏）、
   mapping +5.44（E2→E1）。但 E3 证明 insertion/masking 在无栈时无害
   （3.35 ≈ 裸 MonoGS 2.80）——掩码组件的危害**只在栈存在时兑现**。
4. rollbase 的 33.53 = Combined-Prune 无掩码无栈的固有中段发散，是
   全部现象的底座；掩码或栈各自都能部分/完全压制它，但叠加崩坏。

## ⚠️ L2 复现性存疑（2026-09-11 04:0x，E3 定稿后自查发现）

**rollbase 与 E3 是同一有效配置**：`method_from` 经
`update_recursive` 全量合并（config_utils.py:32），method.yaml 的
SemanticMask.mask_mapping/mask_insertion 均为 true → rollbase 与 E3
均为（掩码 T/T + 栈 off）+ seed0 + 同代码（be9ba127→8d4745ce 仅改
文档/config，无代码变更）。但两者结果 **33.53 vs 3.35**——远超 L2
"允许小浮动"。

可能解释：① st_hf 悬崖是随机分岔（同配置各次 run 独立掷骰，落入
~3cm 干净盆地或 ~33cm 发散盆地），单 seed 读数不能给配置排序；
② 并发互扰（rollbase 与 E2 同卡并发时段跑，E3 与 f3_office 并发）；
③ 卡间差异（rollbase=GPU1, E3=GPU0，可能性最低）。

**后果**：本分解表全部单元格是 n=1 抽样，若 ①成立则 2×2 的格值
（尤其 E2 9.11 / gate 34.68 的对比）都可能是双峰分布的单次抽样。
处置：L2 重跑 rollbase（同 config 同 seed，TAG_PREFIX=l2）在跑；
若重跑复现 33.5 或翻到 3.35 均证实分岔 → 全矩阵需 multi-seed 重估
（DISCIPLINE 种子纪律：筛选臂 2 seeds 起步）。gate 格有 v1 35.7/v2
34.68 两次独立 ~34-35 佐证，暂视为该格稳定。

**L2 结果（2026-09-11 04:24，rc=0，45 evals 全程）**：终值 **34.19cm**，
与原 rollbase 33.53 同盆地（差 0.66cm，L2 意义上"同型"），曲线同型
（开局 0.84–1.88，eval 14–15 跳崖）。41 分钟 vs 常规 69–77 分钟为
并发负载差异，不影响判读。

**分岔定论（同配置 (T/T, 栈off) seed0 三次抽样）**：
{33.53, **34.19**, 3.35} —— 两次落发散盆地 ~34，一次（E3）落干净
盆地。**悬崖是随机的，单 seed 读数不能给配置排序**；E3 的"掩码阻止
悬崖"判读不成立（n=1 幸运抽样），上一版判读第 1/2 条作废。
（L2 运行信息：GPU0，03:43–04:24，config=rollbase_f3_st_hf.yaml，
TAG_PREFIX=l2，与 seed0 原 run 仅输出目录不同。）

## 种子补齐结果（2026-09-11 07:53，全部 rc=0）

| 格（mapping/insertion × 栈） | 三次抽样 ATE (cm) | 干净抽样 |
|---|---|---|
| gate（T/T × on） | 34.68 / **3.30 / 3.04** | 2/3 |
| E1（T/F × on） | 14.55 / 19.22 / 17.31 | **0/3** |
| E2（F/F × on） | 9.11 / 28.02 / 2.49 | 1/3 |
| rollbase+（T/T × off，含 E3/L2） | 33.53 / 34.19 / 3.35 | 1/3 |
| 裸 MonoGS | 2.80 | — |

读数（只写事实）：
1. **所有 Combined-Prune 格均为双峰**：每格都同时存在 ~2.5–9cm 干净
   抽样与 ~9–34cm 发散抽样。v2 gate 34.68 与 v1 35.7 的"同病"是两次
   单抽的巧合；v1 "关 ReliabilitySignal 修复"（2.15/2.39 两次干净）
   与 v2 gate seeds1,2 干净（3.30/3.04）提示历史因果归因可能部分是
   抽样运气，需重审。
2. **E1（insertion off）是唯一 3/3 全发散的格**（14.5–19.2cm，幅度
   一致），n=3 下 0/3 干净 vs gate 2/3 干净，若 P(干净) 相同则概率
   (1/3)³≈3.7%——弱证据提示 insertion off + mapping on 可能反而
   提高发散概率（待更多抽样）。
3. 单 seed 配置排序在此序列上**不可用**；2×2 交互判读全部降级为
   "双峰分布的形状差异，n=3 无法定参"。
4. 裸 MonoGS 2.80（n=1）与 v1 无可靠性臂 2.15/2.39 未见发散抽样；
   "悬崖为 Combined-Prune 特有随机失效"假设待 bare 格补抽样确认。

## 悬崖帧定位（per_frame_ape.csv，12 run 全查，2026-09-11）

全部 12 个 run（含干净抽样）都存在最大单帧跳变，位置聚集成两个
事件区：**帧 ~325–500（早期，约序列 30–46% 处）与帧 ~880–953（晚期，
约 82–88% 处）**，n=1078。逐 run 最大跳变帧（ape_cm，cm 单位）：

| run | 跳变帧 | 跳变幅 | 终值 |
|---|---|---|---|
| gate seed0 | 325 | 47→58 | 31.6 |
| gate seed1 | 880 | 1.5→11.8 | 5.8（恢复） |
| gate seed2 | 880 | 2.0→12.9 | 5.3（恢复） |
| E1 s0/s1/s2 | 905/905/953 | 11→21 / 13→23 / 14→27 | 11.0/16.9/14.4 |
| E2 s0/s1/s2 | 365/948/938 | 1.9→12 / 21→29 / 7.8→17 | 10.7/23.5/4.8 |
| rollbase/L2 | 397/345 | 14→17 / 42→48 | 25.2/25.0 |
| E3 | 497 | 3.3→6.8 | 4.2（恢复） |

判读（只写事实）：
1. 干净与发散 run 的差别不在"是否遇到激励"，而在**激励后是否恢复**
   （gate s1/s2 于帧 880 受 12cm 激励后回到 5–6cm；E1 同区受激后
   不回归）。悬崖 = 恢复机制失效，非单次事件触发。
2. gate seed0 第 0 帧 APE 已 50.9cm（开局崩坏实证，对应
   mask_insertion 假说的画面中央无地图）；seeds1,2 无此现象——
   开局崩坏本身也是随机分岔的一部分。
3. 单帧 argmax 是粗指标；精确的"永久脱离 ~2cm 带"时刻与
   reliability_signal/frames.csv、mask_coverage 的联动分析留待
   修复设计阶段（数据均在 run 目录，可离线重放）。

## 修复方向（2026-09-11 用户拍板后修订）

**定性裁决（用户，2026-09-11）**：实验不确定性 vs 机制性失效的区分——
"大多数时候好、偶尔失败"= 实验不确定性，可接受，只需确认失败不是
频繁出现；"确定性机制缺口"= 必须修。f3_st_hf 属于后者：慢动作人在
画面中长期静止，掩码把人像素排除出建图 → 画面中央长期空洞影响跟踪
（v1 即已确认），这是方法的真实缺陷，**必须解决，不作为叙事收口
素材**（DISCIPLINE：诚实负结果不作为贡献、失效机制解释不得当结论）。

判读与修复的对应关系（基于 2×2 + n=3 数据）：
- **确定性分量 = mask_insertion 的开局/空洞危害**：gate s0 第 0 帧
  APE 50.9cm；v1 p9 关 ReliabilitySignal 后 2.15/2.39 修复实证；
  E1（insertion off）n=3 全 14.5–19.2。慢动作人 = 掩码静止性判定
  的失效区：人被语义标为动态但实际静止 → 像素被永久排除出建图。
- **随机分量 = 中段悬崖**：同配置双峰（含裸 Rollbase 链），位置在
  两事件区（帧 ~325-500 / ~880-953），干净与发散=激励后是否恢复。
  此分量按不确定性处理：抽查批（✗行 ×seeds 1,2）正在量化失败频率
  ——频率低 = 不确定性；频率高且配置相关 = 也升级为机制问题。

修复立项（预注册判据先行，代码后动）：
1. **掩码静止性判定 + 空洞回填**（v1 static_prob 账本的理论落地）：
   长期静止的语义动态像素不再永久排除出建图（静止性判据：连续 N
   帧掩码重叠 ≥ 阈值 + 光流幅度 < 阈值，与具体序列无关，DISCIPLINE #8）。
2. 预注册判据（草稿，实现前定稿）：f3_st_hf/f3_wk_hf（慢动作人）双
   序列 n=3 中位数显著改善且 f3_st_static/f3_wk_static（静坐人）不
   退化 + 标准 Bonn 7 序列不退化 + 至少一条 held-out。
3. 悬崖随机分量：等 ✗ 行抽查频率数据落地后决定是否需要机制定位。

## 修复方向（预注册，待分解完成后再动代码）

候选：掩码静止性判定 + 洞回填（v1 static_prob 账本的理论落地）；
语义优先级融合规则。判据先于实现，遵循 DISCIPLINE #8（机制针对问题类别）。
