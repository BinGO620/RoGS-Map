# 对抗式审查报告：embrace_dyn 因果轮 III 收口（关卡①）
审查时间：2026-09-19 | 角色：只读对抗式审查者
状态：进行中（增量追加）

## 审查对象
（待补）

## 机械事实（health_check）
（待补）

## 问题清单
（增量追加）

## 无法验证清单
（增量追加）

## 审稿结论
（待补）

## 审查对象（补充）
- 主审：`results/embrace_dyn/evidence/verdict_dyn_probe_causal3.md`（110 行，全文已读）
- 预注册：`results/embrace_dyn/evidence/prereg_dyn_probe_causal3.md`（54 行，全文已读）
- 工件：`dyn_probe_verdict.json:causal3_judgments`（gate/baseline）、`diag_causal_fairness.json`、
  `dyn_probe_causal3_results.json`（结构 + aggregate/per_frame 抽样）、`manifest.json:rounds.round_5_causal3`
- 门禁：`tests/embrace_dyn/test_dyn_probe.py:355-465`
- commit：裁决书草稿 428799cc(09:07) → 整改 7fe7eb24(10:14) → 门禁 cf6dd4c9(10:32)；HEAD=cf6dd4c9
- 机械事实：未跑 health_check（本轮被审对象非配置/运行态）；git 提交顺序与 sha 已核。

## 机械事实（commit / 顺序，已核）
- `c332a116`(03:46:40) 仅含 prereg；`7fddd0d7`(03:53:57) 含 probe+analyzer+config；`428799cc`(09:07:49)
  含 results+**analyzer 改动**+report+verdict.json+verdict.md。两者皆为 428799cc 祖先 ⇒ "先提交后跑批"成立。
- `verdict_dyn_probe_causal.json` 在 evidence/ 下**不存在**（`ls | grep -c` = 0）。

## 问题清单

### 致命
- **[致命] E7 helper 跑后修正 + 该块是"本轮最硬读法"的载体，且 manifest 未记跑后 analysis sha**
  证据：`verdict_dyn_probe_causal3.md:14`（"E7 分层 helper 于跑后修正（改在 428799cc）"）、`:72-76`；
  `git show --name-only 428799cc` 同提交含 `scripts/02_analysis/analyze_dyn_probe.py` + results + verdict；
  `manifest.json:rounds.round_5_causal3.measurement_code_commit` 只写 `7fddd0d7`，无 analysis sha；
  `test_dyn_probe.py:452-465` 只断言 sha 含路径，不断言当前 analyzer == 该提交内容 ⇒ 428799cc 的改动对门禁不可见。
  依据：`NOTES.md:433-437`（硬规则②"跑完若发现代码需改，先改再重跑，不要改代码解释旧结果"；③"双溯源
  （测量代码 sha + 分析代码 sha），两者都必须在批次之前"）、`NOTES.md:423-428`（同族三次被关卡① 判致命）。
  反驳通道：给出跑后修正只影响 E7、且 E7 从未作为判决依据的证明；补记 analysis sha=428799cc 并说明
  为何不必重跑（例如 E7 与 E1–E6 完全解耦 + E7 仅"报不判"）。注意本条**不否定 NO-GO**（E1–E6 复算一致）。

### 重大
- **[重大] README/裁决书称 P2cu"两桶普涨"，但 gate 外观好桶是下降（0.2311→0.2251），README 直接略去该数**
  证据：`README.md:184-185`（列出 3 个数、略去 0.2311→0.2251、断言"两桶普涨"）；
  `verdict_dyn_probe_causal3.md:53-54`（印出 0.2311→**0.2251** 仍写"普涨/普涨"）。
  依据：D7/D9 证据呈现纪律；P19（不得把部分事实说成整体）；判据机 `E7_stratified.by_mask_size`（gate 唯一一降）。
  反驳通道：证明"普涨"指"最差桶被抬起"而非"四个数都涨"，且 README 略去该数不构成选择性呈现（建议直接补数）。
- **[重大] "运动建模五次尝试 / 5 个运动变体"只有 4 个能指到工件**
  证据：`verdict_dyn_probe_causal3.md:44`（列 4 项）、`:94`（"5 个运动变体"）；`README.md:210,221`；
  `manifest...motion_model_attempts` 自称 "5 motion variants total"，随后只列 4 项。
  依据：手抄/计数家族（`NOTES.md:余`"判据机条目数 < 预注册条目数"、"手抄数字"复发坑）；计数须锚定工件。
  反驳通道：逐条列出第 5 个变体及其工件键（轮别 + 臂名 + 出处），否则应改为 4。
- **[重大] "离线已到边界"与预注册自己写下的失败模式处置冲突，改善路径未穷尽**
  证据：`prereg_dyn_probe_causal3.md:49`（跑前写下："若 P2cuv 明显劣于 P2cu ⇒ 逐点速度需门控/平滑，
  记录为'逐点速度的朴素形式不可用'"）；实测 P2cuv 两桶均劣于 P2cu（工件已证）⇒ 触发该条；
  而 `verdict:94` 写"机制层面离线已到边界"、`:44` 写"五次尝试、无一可用"，§5 只给"在线机制"或"停在此处"，
  未提预注册登记的离线改善路径（平滑/门控）。`README.md:221` 同。
  依据：D6（负结果不是终点，先穷尽改善路径；禁止以"边界刻画/负结果也是贡献"收尾）。
  反驳通道：证明"门控/平滑"在离线探针上结构性不可实现（给出理由或冒烟证据），或补一轮该消融。
- **[重大] 口径：主判据 E2/E3 是"均值之比"（pooled），E7 桶是"比的均值"（per-frame），裁决书只给 E1 贴了池化标签**
  证据：`analyze_dyn_probe.py:428-436`（E2/E3 用 `retention_of(m,...)` = 池化）、`:461-471`（E7 用
  `_retention_perframe`）；同一"几何保留"两口径：E3=0.5021，由工件桶值加权得 (7×0.1767+8×0.6815)/15=**0.4459**
  （相对差 11%）；`verdict:52-56` 仅对 E1 标"汇总口径"，未声明 E2/E3 与桶读数不同归一化；`manifest F11` 有声明但裁决书/README 无。
  依据：P1/P24/P29（跨口径混引家族，已 3 次）；门槛 0.40/0.75 与桶值同段并列 ⇒ 读者可误比。
  反驳通道：证明 E3 与桶值同归一化（须展示 `retention_of` 与 `_retention_perframe` 在该数据上数值相等）。
- **[重大] 关卡① 顺序：判决已落地（verdict+manifest+README）而关卡仍 PENDING；披露≠整改**
  证据：`DISCIPLINE.md:249`（"实验判决落地前（写 verdict.md / manifest.json 之前）"须过关卡①）；
  `manifest...gate_1: "PENDING"`、`verdict.md:3-4`（⏳ 待过）、`verdict.md:106-110`（§6 整改表为空）；
  `README.md:3`（状态行直接写 "❌ 因果轮 III NO-GO"，无 ⏳ 标记，而同文件 `:11` 又说"未标 ✅ 的不得当已收口结论引用"）。
  依据：DISCIPLINE「收口审查关卡」为必过项；本角色约定：未到场即收口判决本身即违反该条。
  反驳通道：说明为何"草稿落盘"不算"判决落地"（但 manifest.outcome 与 README 状态行已按落地口径书写）。

### 次要
- **[次要] 裁决书引用不存在的工件文件**：`verdict:46` 写 `verdict_dyn_probe_causal.json`，
  evidence/ 下无此文件（实际 = `dyn_probe_verdict.json:causal_judgments`，本次已据此核到 C1b 0.5936/0.6068）。
  依据：D12③ 可追溯。反驳：给出该路径存在的证明。
- **[次要] 预注册错归属**：`prereg:33` "轮 I 的 P2c 0.158" —— 0.1581/0.1562 实为**轮 II** 的
  `D2_appearance_retention.retention_psnr_P2c_reference`（report:156,181）；轮 I/本轮 P2c 外观保留 = 0.1376。
  依据：跨轮错引家族（P1/P24/P29）。反驳：给出轮 I 的 P2c 外观保留 = 0.158 的工件键。
- **[次要] E7 分桶阈值未落盘 ⇒ 桶定义与跨轮可比性无法核实**：`analyze_dyn_probe.py:466` 用 **P2c 的 n_dyn 中位**
  对全臂切桶（同臂同分割，这点没问题），但 artifact 只有 `"n_dyn<med"` 标签、无 med 值；
  `diag_causal_fairness.json` 则显式记 `median_n_dyn_threshold: 3642`（轮 I/II 同值）。
  依据：D9/P23 计数与口径须可核。建议：E7 块增记 med 与帧清单。
- **[次要] 门禁部分自证、覆盖不全**：`test:399-411` 只用**子串存在**钉 4 个数（0.2902/0.1767/0.8478/0.6815），
  同句另 5 个数（0.216/0.014/0.0476/0.2251/0.2311）未钉；`test:402-410` 的"出局规则被套用"实为复述结论
  （未从预注册规则文本 + 阈值重算）；**无 baseline 分桶断言**；无"analyzer 阈值 == 预注册 0.40/0.75/0.90"断言；
  无"`_retention_perframe` == fairness 算法"断言；`test_causal3_no_hand_copied_out_of_artifacts` 名不副实
  （只防 "×6.4" 与 5.13×，其它手抄数字不会被抓）。依据：D1 门禁实质有效性。
- **[次要] 核心读法只用 gate 桶，baseline 桶（同向且更强：四数全涨 / P2cuv 四数全低于 P2c）未并陈**：
  `verdict:55-56`；report:237-258 有 baseline E7。建议 §3.2 补 baseline 桶以支撑"两地图一致"。
- **[次要] 桶 n=7/8、单 seed、无方差/CI；"把累积的增益整个吃掉"是观测比较**（未做 D11 式失败分类）
  证据：`verdict:15,90`（已自陈单序列单 seed）。建议报每帧极差或至少声明可比性边界。
- **[次要] §1/§3.2 把"仅作消融"的 E1 门槛 0.90 与主判据并列**（`prereg:43` 明示 E1 仅消融），
  易读成决策项；且 E1 是 dl1 **比值**、非 retention，与 0.40/0.75 不同量纲。
- **[次要] 判据机"确定性可复算（重跑逐字节相同）"无落盘证据**（`README.md:236-238`），且复核方式需原地
  重写两个交付物（D3 风险）→ 建议在临时目录复核并落 hash。

## 已核通过的项（避免误报）
- **B 全数命中**：0.9693 / 0.0285 / 0.5021 / −1.0303 / −1.2425 / 0.3634 / 1.2475 / 5.13× 逐位命中
  `causal3_judgments`（E1–E6）与 `means`（20048.2/3909.07=5.1286）；表格 6 行 gate 全部命中；
  四舍五入正确（3656.7333→"3,657"、3909.0667→"3,909"）。**无手抄、无按比例外推。**
- **内部自洽复算**：E3=(26.7023−21.1848)/(26.7023−15.7136)=0.5021 ✓；E1=19.5635/20.1833=0.9693 ✓；
  E4=22.4825−23.5128=−1.0303 ✓ / 22.98−24.2225=−1.2425 ✓；E5=20048.2/55174=0.3634 ✓、/84162=0.2382 ✓；
  E6=26.4271/21.1848=1.2474 ✓；且 artifact means 由 `dyn_probe_causal3_results.json:aggregate`
  重算（15 帧配对集，P1 20.5542→20.3366 的变化即剔除冷启动帧）⇒ 判据机是**算**出来的。
- **判决被证据支撑**：两地图 E2/E3 皆 `pass:false`（0.0285<0.40、0.5021<0.75 / 0.0535、0.4976）⇒
  预注册出局规则 ¬E2∨¬E3⇒NO-GO 成立；E4 亦 fail（静态 −1.03/−1.24 dB）、E5/E6 pass。**判决方向无"强于证据"。**
- **轮 I PARTIAL 订正准确**：`causal_judgments` gate C1b 0.5936 / baseline 0.6068、outcome=PARTIAL ✓（0.594/0.607）。
- **来源分离干净**：`diag_causal_fairness.json:sources` = 轮 I / 轮 II / balloon（**不含本轮**），
  裁决书头部与 README:179-180 均如此声明，§3.2 明确标"跨轮对照"并并陈本轮自身桶 ⇒ **未把 fairness 当本轮证据**。
- **文献出处真实且转述未失真**：`venue_cvm.md:96-98` 原文确为"该会场少见（做了也别指望加分）/ 分区指标抽样 7 篇无一报
  ⇒ 我们报了就是差异化"+挂靠点；`:103` 必配"无效像素处理声明"；`metrics.md:46` 评测卫生节；
  `open_questions.md:33-34`（347ms/帧、动态 GS 22K）、`dynagslam.md:70`（347/95/22K/2.6GB）均逐字存在。
  22K/347ms **未出现在本轮裁决书中**，不构成越界主张。
- **无 P25 型版本漂移**：本轮 P2c 桶值（差 0.216/0.014、好 0.8012/0.2311）与 fairness 记录的
  轮 I（0.216/0.0143、0.8021/0.2309）、轮 II（0.2157/0.0145、0.8017/0.2313）几乎逐位相同 ⇒ 控制臂跨轮一致。

## 无法验证清单
1. "E7 修正不改结果 JSON 逐帧原始量"：results 与 analyzer 改动同处 428799cc，git 无法分离；
   需 `git show 428799cc --stat` 之外的原始 mtime/备份，或在**临时目录**重跑判据机比对
   （`python3 scripts/02_analysis/analyze_dyn_probe.py --help` 先确认输出路径参数，勿原地覆盖 evidence/）。
2. 本轮 E7 分桶 med 值与帧清单（artifact 未落盘）；建议 `_retention_perframe` 输出 med 后再核。
3. 判据机确定性重跑的 sha256（README 声称逐字节相同，无 hash 文件）。
4. `dyn_probe_causal3_results.json` 的 `per_frame` 是否含改码前原始量（仅确认键存在）。
5. 未跑 health_check（与审判对象无关；本轮为文书/工件审查）。

## 审稿结论
**Reject（阻塞项 = §致命 1 条 + 重大 5 条）**：NO-GO 方向本身有证据支撑（E2/E3 双不过、四舍五入与
逐位复算全中），但"跑后改判据机 + 最硬读法建立在该跑后块上 + manifest 未记 analysis sha"属历史致命族；
另需处理"普涨"表述（含 README 略数）、"5 个运动变体"无支撑、"离线已到边界"与预注册 §4 冲突、
pooled vs per-frame 两种归一化未在裁决书声明、以及判决落地早于关卡① 的整改。
