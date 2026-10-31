# slam-critic 审查报告 — R34 关卡① 收口审查
- 审查对象：/data/monogs-ours/results/paper2_rollout/evidence/verdict_r34_draft.md（R34 判决草稿）
- 预注册：/data/monogs-ours/results/paper2_rollout/evidence/prereg_r34.md
- 分析器：/data/monogs-ours/scripts/02_analysis/analyze_r34.py；输出存档 evidence/analyze_r34_output.txt
- 原始数据：results/paper2_rollout/r34_{rb,sw,gate}_{f1_room,f1_desk2,f3_st_rpy,f3_office,moving_obstructing_box,f3_wk_rpy}_seed{0,1,2}/tables/tracking_raw.csv（54 run）+ 先验 rollbase_*/diag_f1r_* 等
- 生成时间：$(date '+%F %T')
- 免责：本报告仅为线索生成器，被审方需自行复核每条。

## 1. 审查对象
（见上；commit 待补）

## 2. 机械事实（确定性重跑 / 独立复算）
（待填）

## 3. 关键数字独立复算
（待填）

## 4. K5/K6 两版本先读 vs 预注册原文一致性
（待填）

## 5. 如实披露核查
（待填）

## 6. 计数/折行坑（P22/P23/P29）
（待填）

## 7. 不一致清单
（待填）

## 8. 无法验证清单
（待填）

## 9. 审稿结论
（待填）

### 检查块 1：分析器确定性重跑 ✅
- 命令：`python3 scripts/02_analysis/analyze_r34.py --root results/paper2_rollout`（rc=0）
- 存档 diff：`/tmp/r34_diff.txt` **0 行**（180 行重跑 vs 180 行存档完全一致）
- 结论：分析器确定性成立，存档可信。

### 检查块 2：关键数字独立复算 ✅（含 2 处小瑕疵）
- 从 18 个 r34 run 的 tracking_raw.csv 逐行自取 col8 末行 OK 值，与草稿 §二「逐 seed col 8」表**逐格一致**（54/54 格）。
- 均值/极差复算：f1_room rb 16.391（4.7585/27.9942/16.4192）、sw 13.897、gate 17.948；f3_office Δ(rb→gate)=+1.603（+1.732/+1.663/+1.414）；f3_wk_rpy +1.706（+2.509/+2.532/+0.078）；f1_desk2 −1.327（−1.060/−1.294/−1.626）——全部与草稿一致。
- 容差复算：f1_room max−min([8.2384,6.4318,4.7338,7.0213,9.3311])=4.5973→4.60 ✅；f3_st_rpy 1.8263→1.83 ✅；mob 18.7691→18.77 ✅；f3_wk_rpy 0.2714<1.0→1.00 ✅。
- 先验值来源抽查（8 个 x_rows_seeds12 run 目录 col8）：rollbase f1_room s1/s2=6.4318/4.7338、f3_st_rpy s1/s2=2.7578/4.5114、mob s1/s2=37.5449/20.9375、wk_rpy s1/s2=4.4823/4.2109——**全部来自对应 run 目录，精确一致** ✅。
- diag_f1r_b s0/s1 col8=7.0213/9.3311 属实；9.1446=col14（P29 防混引成立）✅。
- 标准 54 格标准差（ddof=1）抽验 6/6 一致（如 f1_room rb ±11.618、f3_office gate ±0.146）。
- 瑕疵 A：草稿 §六「其余 16 run：med 0.00 max 0.00」——实测 = 15 run（18−2 非零−1 skip）；16 与随后单列的 skip 行重复计数。（次要）

### 检查块 3：运行时 config 指纹 + 先验 provenance ✅
- 54/54 run 运行时 config 指纹（SWBA 块/阈值、LoopClosure、ReliabilitySignal）与三臂设计逐 run 一致，0 异常。
- rb vs rollbase（f1_room 抽验）：非路径差异仅 sequence/save_dir/*_path/experiment 名；gate vs roll 同；**sw vs rb 差 = `SWBA.enabled: true` 一项** ✅（与草稿 §三「归因② 细节」一致）。
- diag_f1r_b config：SWBA.enabled=false + LoopClosure.enabled=true（LC-on 属实）；其回环修正行 med 0.00/max 0.00（291/290 KFs）；rollbase_f1_room / r34_rb 无任何 LoopClosure 行 ⇒「行为等价」论据成立 ✅。
- x_rows_seeds12.done：30/30 `finished rc=0`；先验 8 值（f1_room/f3_st_rpy/mob/f3_wk_rpy 的 rollbase s1/s2）与对应 run 目录 col8 精确一致 ✅。
- 覆盖完整性另证：远程审计（remote_audit_2026-09-18.md）152 个远程独有目录清单不含 f1_desk2/f3_office 的 rollbase/roll seed1/2 ⇒ 两序列「仅 seed0 先验」在审计范围内成立（f3_office/f1_desk2 先验仍 1 点）。

### 检查块 4：折行/计数坑残留核查 ✅（含 1 条信息性提示）
- 18 个 gate consolelog：`corrections` 出现次数 == RE_LOOP_SUM（含 `\s*` 容错）命中数，**18/18 相等**，无残留漏配。
- 变体正则（all-`\s*`）复算 18 run 的 med/max/KFs **与存档逐格一致**（0 mismatch）。
- `corrections|dt|` 零空格断行确实存在（f3_wk_rpy s0："corrections|dt| med 0.00cm max 0.00cm applied to 176 KFs"）✅。
- **信息性**：SWBA 执行行还存在另一种零空格断行 `max0.47cm`（f1_room/desk2/office 等 gate run 的 `|dt| med Xcm maxYcm` 行）——分析器当前不解析该行的 med/max 数値，无本次影响；若未来要解析执行行数值，须同样容忍零空格。
- f1_desk2 seed1 "0 verified skip" 合法形态（§C 单列）✅。
- 每 consolelog 恰含 1 个自报 run 目录时间戳（54/54，多归属事故形态 0）✅。

### 检查块 5：K3/K4 计数与配置核对 ✅
- K3 loose 计数（`\s+` 容忍 rich 插空/断行）与存档 strict 计数 **54/54 逐 run 一致**（0 mismatch）⇒ 本批日志上 strict 模式无漏配残留。
- K1-c 独立复核：54/54 run 的 tracking `run_id` 均出现在对应 consolelog 文本中（0 mismatch）。
- rb 18/18 正控全零（exec=0/anySWBA=0/loop=0）；sw 18/18 (a)>0 且 loop=0（f3_office 502/502/503 式）；gate 18/18 三态 + delta∈{0..5} ✓。
- 旧批 roll_f3_st_rpy seed0/1/2 回环摘要行均为 0.00/0.00cm（160 KFs）⇒ 与草稿「旧批同 config 同 verified 对为 0.00cm ⇒ 非确定性」一致 ✅。
- 6 序列 × {rb↔rollbase, gate↔roll} 的运行时 config 归一化 diff **12/12 CLEAN**（仅 path/sequence/save_dir 类差异）✅；sw↔rb 差异抽查 = `SWBA.enabled` 一项 ✅。

### 检查块 6：冻结值/草稿一致性发现
- 冻结 12 值（6 seq × rollbase/roll seed0 col8）全部从对应 run 目录复算精确一致（8.2384/18.1034/7.1966/3.5267/2.6851/5.8459/1.6438/3.6579/18.7758/20.7368/4.2924/5.8689）✅。frozen≈prior 重合核：f1_room/f3_st_rpy/mob/wk_rpy 均一致（f1_desk2/f3_office 无 s1/s2 prior ⇒ 数值来源=冻结值 rollbase seed0，条目标注正确）。
- **草稿内部不一致（重大）**：`verdict_r34_draft.md:74` §三标题「**4/6 EXCEEDS**，归因触发器全部执行」与本节表格/正文（EXCEEDS=3 行，完整先验读；4/6 仅 legacy 读）矛盾；同文 :54 又写「完整先验 3/6 EXCEEDS」。标题未随 67008e50 升版同步。**反驳通道**：能证明 §三标题指 legacy 读并已标注者（当前标题无任何版本限定词，逐字读=完整先验读的默认口径）。
- **草稿内部不一致（次要）**：:172「其余 16 run：med 0.00 max 0.00」——精确 = 15 run（18−2 非零−1 skip）；«16» 将其后单列的 f1_desk2 s1 skip 行重复计 1。属陈述计数误差，不影响结论。

### 检查块 7：代码版本窗口（P25 家族）✅
- 先验批（09-10/11/12）与 R34（09-17）之间触碰核心的提交四枚：`c9ecca49`（09-12 前端 +12 行，ledger 调用）、`6978d154`/`f98ed1ac`/`715d7bd0`（09-13，仅 `utils/mask_stability.py`+tests）。`c9ecca49` 的前端集成被 `get_mask_stability_ledger` 严格门控（config 无 MaskStability 块 ⇒ 返回 None ⇒ 不改 person_mask）；实测 54/54 r34 config 与全部先验 config **均无 MaskStability 块**、54/54 日志无 "MaskStability" 字样 ⇒ 该模块对两批均**惰性**（默认关逐位一致承诺成立）。
- R34 运行窗口（09-17 07:24–22:14）内 `git log -- utils/ gaussian_splatting/ slam.py` = **0 提交**（窗口内提交全为 NOTES/脚本/文档）⇒ 批内漂移证据干净。
- SWBA 相关修复（a21e0773/1150fb25）均早于两批 ⇒ 先验与 R34 在行为相关代码上同码；窗口内漂移对 K5 输入集无实质影响。
- 遗留（无法硬证）：运行期远程 HEAD（见无法验证）。health_check 现场 FAIL：`Sync: 远程==origin` 远程=fccd2550、origin=de92b9b6（远程落后 9 提交，已知 bundle 债；fccd2550 含 18 个 r34 config，与派发门禁一致）。

### 检查块 8：K5/K6 预注册原文 vs 草稿两读 ✅（自洽，除标题）
- 预注册 K5 原文（:282-287）：触发器「依次①K1-b/K1-c ②config diff ③两者干净⇒改判不可复现并剔除，不计入 K6 分子/分母」；草稿 §三 逐序列列 ①/② 判定 + 处置列（f1_room/f3_st_rpy 剔除；f1_desk2 记方向复现——其为对照非有害清单成员，预注册剔除条款以 5 条有害清单为限，处理自洽）。
- 预注册 K6 原文（:299-306）：「Δ 仍为正且逐 seed 均值 |Δ|>1.0cm 者 ≥3 条（分母=未被 K5 剔除者；K5 剔除 ≥3 条 ⇒ 自动降级）」。完整先验读：剔除 2 ⇒ 保留 3；达标 2/3 ⇒ 「部分不成立」+ 止损项（草稿 §五/§七一致）；legacy 读：剔除 3 ⇒ 自动降级「不可复现」（草稿并陈一致）。两读分母/分子逻辑经机器输出复核无冲突。
- 原主张「5 条有害」两读均不成立（完整读：复现 2 + 反转 1 + 不可复现 2；legacy 读：复现 2 + 不可复现 3）——草稿「两读同底线」表述复核成立。

### 检查块 9：如实披露清单核验 ✅
- x_rows_seeds12 补全记录：提交 06ef87b8（30 run 补拉，197 files）为 HEAD 祖先；30/30 rc=0；本地 8 序列×2 臂×{s1,s2}=32 目录全在（16 为 R34 六序列相关）；先验 8 值逐目录复算精确一致。
- mob 改判说明（§三注）：完整陈述极差 18.77⇒容差、改判 PASS、「保留≠复现」；与输出一致。
- 「不补 final 臂」4 理由（§六）：与预注册 §2.1 决策规则（取决于序列主结论地位）一致；守卫句在。
- 关卡①未过留痕（§九 + 文首）：两轮失败原因与用户处置如实；未以「数字已复算」冒充过关。
- Bonn-scoped 收窄：提交 6c8c6021 恰改 5 文件（NOTES/NARRATIVE/method_review/README_r34/prereg），与草稿「5 处文档已改」相符；NARRATIVE:102/NOTES:75/method_review:22/README_r34:29 均有正确表述。
- 回环非确定论据：旧批 roll_f3_st_rpy s0/s1/s2 摘要行均 0.00/0.00cm（160 KFs）vs 新批 s0 10.36/s2 13.23 ⇒「同批 verified 对（335→385,310→415,630→665,240→275）非确定性」复核成立。
- 面板/文档门禁：rollout_panel.csv 19 行 baseline 列仍为冻结值（门槛③ 联动尚未执行——草稿 §七 止损 1 已列为行动项，属预期未办态而非隐瞒）；manifest.json 不存在（生成器 gen_manifest_r34.py 备测，待过关卡①后落，草稿已声明）。8/19 表述仍在 NOTES:88/445、README.md:49、method_review:410/498（草稿 §七 止损 2 已宣停止使用——同上属待办）。

### 检查块 10：问题清单（分级；反驳通道见各条）
**重大**
1. `verdict_r34_draft.md:74` §三标题「**4/6 EXCEEDS**，归因触发器全部执行」与本节表格（EXCEEDS ×3：f1_room/f1_desk2/f3_st_rpy）及 :54「完整先验 **3/6** EXCEEDS」自相矛盾——标题为 legacy 读数且无版本限定词，逐字读为完整先验读的默认口径。（依据：P20/P29 同族——跨版本混引；D16 文档联动。）
   反驳通道：证明该标题指 legacy 读并有显式版本标注（当前无）；或举证 4/6 在当前口径下的正确性（输出存档为 3/6）。
**重大**
2. `NOTES.md:48` 同行内两读并存且未标版本：头部「K5 双读 4/6↔3/6→「部分不成立」」vs 正文「**K5 复现性 4/6 EXCEEDS**（f1_room +8.152/tol **2.31**、…mob +10.400）⇒ **3 条**有害序列判「不可复现」剔除；**K6 触发自动降级**」——正文为补全前（f4052be5 冻结态）读数，与 analyze_r34_output.txt / 升版草稿（3/6、tol 4.60、mob PASS、剔除 2、K6 部分不成立）冲突。（依据：P28/P29 同族——旧读数未加版本锚污染后续引用；D16。）
   反驳通道：证明该段属被显式标注的「补全前冻结记录」或已声明被取代；否则要求加版本锚。
**次要**
3. `verdict_r34_draft.md:172`「其余 16 run：med 0.00 max 0.00」应为 **15 run**（18 − 2 非零 − 1 skip；16 将下一行的 f1_desk2 s1 重复计入）。
4. `verdict_r34_draft.md:16-17`（同 NOTES:48）「逐条复核**全采纳**」与 `prereg_r34.md` §七 处置列不符——重大 1 为「**部分采纳**」（13 全采纳 + 1 部分采纳）。数字层不影响，属记录表述误差。
5. （信息性，P29 家族）执行行亦存在零空格折行（`max0.47cm`，f1_room/desk2/office gate run 的 `|dt| med X cm maxYcm` 行）；分析器当前不解析该行数值故无影响，未来若解析须同样容忍零空格。

## 无法验证清单
- 各臂运行期远程 HEAD 无法硬证（远程 reflog 仅回溯至 09-13；本审查以「窗口内核心提交=0 + config 逐字段 diff + 执行正控」间接证据组合，与 prereg §八 同款债务）。
- 远程是否有未清点的其他 R34 六序列 all-off 观测（本审查核了 roll/rollbase/diag_f1r 命名族与 x_rows 批；全量 comm 差集为远程审计文档所做，未逐目验）。
- health_check FAIL（Sync 远程≠origin）与 R34 数字无关，但下次派发前须 bundle 同步（D4 相邻债）。

## 反驳受理
（待被审方提交证据；只认证据。）

## 审稿结论
**Accept（带条件）——无致命；两项重大（均为文档一致性、单行可修）须在落 `verdict_r34.md` 前清零**：
① 修 `verdict_r34_draft.md:74` §三标题（3/6 完整先验读，或加「legacy 4/6 / 完整 3/6」双读标注）；
② 修 `NOTES.md:48` 正文残留 legacy 段（加版本锚或改完整读）。
数字与判据层全部复算通过：分析器重跑 diff=0；54 格 col8、18 格 sd、12 冻结值、8 先验值、容差 4.60/1.83/18.77、Δ 全量、col14 全量、K1-c 54/54、K3 54/54、config 54+12+6、delta 上界 0–5、旧批回环 0.00、R25 负控=0 均一致。改后可直接落盘并回填 §九 审查记录。

---
## 定稿导读（骨架节 1–9 的占位符以本导读为准）
- 审查对象/commit → 检查块 1（+本报告头）。
- 机械事实（health_check）→ 检查块 7 末段（FAIL: 远程≠origin；WARN: 简化臂外推=rb 设计本身、组件不一致=多臂对照预期）。
- 独立复算 → 检查块 2/4/5/6；确定性重跑 diff=0 → 检查块 1。
- K5/K6 两读一致性 → 检查块 8；如实披露 → 检查块 9。
- 计数/折行坑（P22/P23/P29）→ 检查块 4（含零空格断行残留提示）+ 检查块 5（loose 计数 54/54）+ R25 负控=0。
- 问题清单/无法验证/审稿结论 → 检查块 10（含分级、反驳通道、结论）。
- 成本：本审查约 38 次工具调用、无仓库写入；唯一写入=本报告文件。
