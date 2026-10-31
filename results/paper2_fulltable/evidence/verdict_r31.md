# R31 裁决：自校验式 SWBA 门重测（H1）

> **账本补登（2026-09-25，D2-015 追溯登记）**：本件成文于决策账本设立（2026-09-20）之前，无当期账本号；统一追溯登记见 `DECISIONS.md` **D2-015**。

> 日期：2026-09-15 跑批 / 2026-09-15 裁决
> 臂：`r31_selfcheck_{0p5,1,2}` = gate 臂（SWBA static_conf 0.38 + LoopClosure）
> + `swba_min_rel_improve ∈ {0.005, 0.01, 0.02}` × 标准 Bonn 7 序列 × seed 0,1
> 远程 3090×2，**42/42 rc=0**（`r31.done`，17:05 batch all done，四 worker rc 全 0）
> 口径：主读数全帧 `ate_rmse_cm`（col 8），附表 keyframe（col 14）
> 预注册：`evidence/prereg_r31_selfcheck.md`（判据跑批前锁定）
> 复算：`evidence/manifest_r31.json` ← `scripts/02_analysis/gen_manifest_r31.py`（确定性可重建）
> 原始分析输出：`evidence/analyze_r31_output.txt`

> **参照臂重基线后的复核（2026-09-16，R32）**：本裁决的 MAIN/SUB 判据以
> `r29_framegate`（0.38 列）为参照，而该列已随 R32 重基线为 `r32_regate038`
> （当前 HEAD，21 run rc=0）。**按新参照重算**：
> MAIN —— 0.5% 维持 FAIL、1% 维持 PASS、**2% 由 PASS 翻为 FAIL**
> （crowd2 2.6933 vs 新阈值 2.6484）；SUB —— **三档全 FAIL，不变**；
> MECH —— **与参照臂无关**（取自本臂日志：691/385、380/681、90/989），三档维持 PASS。
> ⇒ **总判 "NOT ESTABLISHED（no arm passes all three gates）" 不变**，因为
> 它由 SUB 三档全否支撑。
> **不把 2% 的翻转当作"结论加强"**：该臂 crowd2 两 seed 极差 0.941cm，远大于
> 其 ±3% 判定带 0.081cm（本文件 §四.5 已自述），属噪声级判定；且 R32 实测
> 同码同 config 同 seed 的运行散度即达 0.18–0.62cm。
> 详见 `evidence/verdict_f_rebase.md` §五。

## 判决（一句话）

**三门未全过 ⇒ 自校验门不成立，记入已排除方向，回到"维持 static_conf 门 +
如实报告敏感度"。** 三档阈值中 0.5% 主判据否、1%/2% 主判据过而副判据否——
副判据**三档全否**，且提高阈值改善易序列的代价是 pt1 单调恶化，
不存在同时满足两侧的工作点。

## 一、门控语义（代码实证）

`utils/swba.py:730-740`：`rel_improve`（本次修正相对上次的**窗口光度代价**
相对改善）低于 `swba_min_rel_improve` 时跳过修正。阈值越高 → 修正越少被接受。
`rel_improve` 默认 0.0（等于门关），故本实验为纯 config 实验（DISCIPLINE #2），
相对 `r29_framegate` 仅加一行 `swba_min_rel_improve` + 改 save_dir（单变量）。

## 二、结果（全帧 ate_rmse_cm，n=2 均值）

| 序列 | 0.5% | 1% | 2% | r29_framegate 参照 (n=3) |
|---|---|---|---|---|
| balloon | 3.885 | 3.716 | 3.087 | 4.056 |
| balloon2 | 5.365 | 5.280 | 5.330 | 5.400 |
| crowd | 2.301 | 2.168 | 2.294 | 2.250 |
| crowd2 | 2.757 | 2.326 | 2.693 | 2.620 |
| crowd3 | 1.792 | 1.704 | 1.572 | 1.894 |
| **person_tracking** | **8.807** | **10.252** | **11.345** | 7.834 |
| person_tracking2 | 12.315 | 12.075 | 11.348 | 11.537 |

门两态计数（臂级，逐 run 见 manifest）：

| 臂 | applied (`edges free=`) | skipped (`correction not applied`) | skip 率 |
|---|---|---|---|
| 0.5% | 691 | 385 | 35.8% |
| 1% | 380 | 681 | 64.2% |
| 2% | 90 | 989 | **91.7%** |

## 三、预注册判据裁决

| 臂 | MAIN（易序列不退化） | SUB（pt1 ≤ 8.2cm） | MECH（两态共存） |
|---|---|---|---|
| 0.5% | **FAIL**（crowd2 2.757 > 2.699） | **FAIL**（8.807） | PASS（691/385） |
| 1% | PASS | **FAIL**（10.252） | PASS（380/681） |
| 2% | PASS | **FAIL**（11.345） | PASS（90/989） |

对照预注册判决规则：
- 0.5% 落「主判据否 ⇒ 判别力不足」分支
- 1%/2% 落「主判据过、副判据否 ⇒ 门过严，误拦有益修正」分支

**两个分支互斥且穷尽，而沿阈值轴移动只能在两者之间切换**（见 §四.2），
故不存在可收口的工作点——这是本次判负的完整理由。

## 四、判读（只写事实）

1. **副判据三档全否，且随阈值单调恶化**：pt1 = 8.807 → 10.252 → 11.345
   （阈值越高、门拦得越多、pt1 越差）。三档均高于 8.2cm 上限；
   2% 档已接近 baseline（13.62）方向。**有用修正被系统性误拦。**
2. **提高阈值只换来易序列的改善，且是同一权衡的另一端**：crowd3
   1.792→1.704→1.572、balloon 3.885→3.716→3.087（拦得越多越好），
   而 pt1 反向恶化。这与实验 F 中 static_conf 门的行为结构相同，
   即自校验门**没有绕开实验 F 的权衡，只是换了一根横轴**。
3. **（本实验内、无版本混淆的决定性证据）门的 skip 率跨序列近乎持平**——
   0.5% 臂 7 个序列的 skip 率全落在 27.5%–41.2%（极差 13.8pp），
   1% 臂 58.7%–71.3%（12.6pp），2% 臂 88.7%–95.6%（6.9pp）。
   而实验 F 的问题恰恰是**易序列与 pt1 需要相反的门行为**
   （易序列要压 SWBA、pt1 要放 SWBA）。一个在易序列和 pt1 上
   skip 率几乎相同的门，按其定义就无法完成这个区分——
   这与预注册 §五之二 探针给出的预警（46% vs 41%，分布重叠）一致，
   正式批以 42 run 予以确认。
4. **MECH 判据只在"排除 100% 恒 skip"的意义上有效**：三臂均两态共存，
   说明 R25 的恒 skip 事故未重演；但 2% 臂 91.7% skip 已属近恒关，
   臂级聚合（`analyze_r31.py:159-164`）无法识别单 run 的近恒关
   （2% 臂中 `balloon_seed0` = 4 applied/65 skipped）。
   MECH=PASS **不等于**门处于有效工作点（P21）。
5. **crowd2 的 MAIN 判定在噪声内，不可作为结论性依据**：2% 臂
   crowd2 两 seed = 3.164 / 2.223（极差 0.941cm），远大于 ±3% 判据带
   （均值 2.693 的 3% = 0.081cm）；0.5% 臂 FAIL 的差距
   （2.757 vs 2.699 = 0.058cm）同样小于其 seed 极差（0.156cm）。
   逐 seed 明细见 manifest。故 MAIN 在两处均为噪声级判定。

## 五、判据可识别性缺陷（如实披露，不追溯修改已锁定判据）

以下四条在跑批后复核中发现，**判据已锁定不动**，但其存在意味着
MAIN/SUB 的"PASS/FAIL"字面结论强度低于表面；本裁决的定性结论
（§四.3）不依赖它们。

1. **MAIN/SUB 容差小于参照臂自身的 seed 极差。**
   r29_framegate 三 seed 相对极差：crowd2 = 19.1%、crowd = 13.4%、
   pt1 = 11.4%（绝对值 sd 0.255 / 0.166 / 0.511cm），而判据带宽仅
   +3% / +5%。且 R31 为 n=2、参照为 n=3，n 不一致。
2. **参照臂与实验臂跨代码版本。** `r29_framegate` 跑于 2026-09-07，
   R31 跑于 2026-09-15；其间 `utils/swba.py` 有两次雅可比修复
   （`a21e0773`、`1150fb25`，均 2026-09-09），且 `a21e0773` 自述
   "修复改变部署 SWBA 行为"。同 config 同 seed 的修复后重跑
   （`results/joint_correct/gatefix_r29_framegate_*`）相对 09-07 原值：
   pt1 seed0 7.5461→7.5157、pt1 seed1 7.5316→7.7984、
   pt2 seed0 11.1784→**12.0408**、pt2 seed1 11.39→**12.024**
   （col 8）——pt2 偏移 0.63–0.86cm，与所测阈值效应同量级。
   R31 批内无同代码的 r29 对照臂。
3. **预注册 §三 的 MECH 字面计数模式是退化模式。** 文中写
   `` `applied` 计数 > 0 ``，但裸词 `applied` 会匹配到 skip 行内的子串
   （`correction not applied`）以及 LoopClosure 摘要行
   （`loop_closure.py` 的 `applied to N KFs`）——实测 pt1 探针
   `grep -c applied` = 45 = 44 条 skip 行 + 1 条 LoopClosure 行，
   而真实 applied（`edges free=`）= 63。**即使 100% 恒 skip 也会 >0**，
   即该字面判据无法实现它自己声明的目的（"不重演 R25 恒 skip"）。
   实际操作脚本 `analyze_r31.py` 用的是 `edges free=`（正确），
   故本裁决结果不受影响；缺陷限于锁定的判据文本，已记入 NOTES 踩坑。
4. **"只认 done 后 consolelog 末行 eval"在本项目得到的是 keyframe 口径。**
   `utils/eval_utils.py` 的末行 `Eval: RMSE ATE [m]` 只对关键帧计算
   （实测 r29_framegate_crowd2_seed0 末行 0.02147 m = col 14 的 2.1472，
   而 col 8 = 2.3435）。本裁决一律自 `tracking_raw.csv` 第 8 列取值，
   与 NOTES 主表口径一致。

## 六、结论与处置

- **自校验门不成立**：副判据三档全否 ⇒ 误拦有益修正；且 skip 率不区分
  易/难序列 ⇒ 无法承担实验 F 所需的区分职能。**不进入 3-seed 晋级确认。**
- **记入已排除方向**：`swba_min_rel_improve` 作为 static_conf 门替代的路线
  在 0.5%–2% 全区间无可用工作点（阈值再降则易序列失去抑制，再升则 pt1 增益
  进一步丢失）。代码保留（默认 0.0 = 门关，行为不变）。
- **维持现行方案**：static_conf 门 0.38 + 如实报告阈值敏感度
  （即 `verdict_f_sensitivity.md` 的"维持现状 + 如实报告"分支）。
- **下一步改善方向**：自校验信号本身（窗口光度代价相对改善）在掩码后
  仍不能把"有害修正"与"有益修正"分开——这是本次最直接的证据
  （§四.3）。若继续该方向，需要的是**判别信号**而非门阈值工程，
  属新研究周期，不在本次收口范围。

## 七、遗留待决（超出本实验范围，需用户拍板）

复核中发现并验证：**实验 F 的 0.38 臂与 R31 的参照臂同一问题**——
`r29_framegate`（0.38）跑于 2026-09-07 代码（雅可比修复前），
而 0.30/0.45 臂跑于 2026-09-14/15；`results/joint_correct/README.md`
§2.5c 已于 2026-09-09 明确宣布该组 gate 参照数字
（**7.83 / 4.06 / 2.62 / 1.89**）**作废**，而现行
`verdict_f_sensitivity.md` §二与 `papers/paper2/NARRATIVE.md` §4.6
表格的 0.38 列正是这组作废数字。同时 §一 激活计数表存在
不可复现项（person_tracking 0.45 写 86/88，实测该臂 gate=115、
逐 seed 放行 112–114，无 88 行分母的 run）。

处置建议（未执行，**本会话未派新实验**）：在**当前 HEAD** 重跑
0.38 × 7 序列 × 3 seed，与 0.30/0.45 同代码重出敏感度曲线；
在此之前 §4.6 表应加跨版本注记。**是否启动重跑需用户拍板。**

## 八、运行信息

- configs：`configs/experiments/paper2_fulltable/r31_selfcheck_{0p5,1,2}_{7序列}.yaml`（21 个，已入库）
- 跑批：`scripts/paper2_fulltable/run_batch.sh`，固定 worker 池、私有 `RUN_LIST`（规避 P10）
- 分析：`scripts/02_analysis/analyze_r31.py`（三判据自动裁决）、
  `scripts/02_analysis/gen_manifest_r31.py`（manifest 重建）
- L1 门禁：`tests/paper2_fulltable/test_fulltable_configs.py::test_r31_selfcheck_configs`
- 组件指纹：SWBA(0.38) + LoopClosure + SemanticMask + ReliabilitySignal +
  DeferredCommit + RobustTracking；MaskStability 未启用
- 运行目录：`results/paper2_fulltable/r31_selfcheck_{0p5,1,2}_{seq}_seed{k}/`
  （轻量产物：`console.log` + `tables/tracking_raw.csv` + `config.yml`）
