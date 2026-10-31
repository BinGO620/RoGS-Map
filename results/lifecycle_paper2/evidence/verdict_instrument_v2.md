# verdict_instrument_v2 — 仪器 v2（matched-control freshvac 三参照）全臂重评分判决

> **双溯源**：测量代码 = `2864c997`（主批保留件 73 run）+ `5695bc94`（crowd 族/TUM 重跑件 30 run；
> 等价性工件 `results/lifecycle_paper2/instrument_v2/control/control_report.md`：旧码 vs 新码在同一
> crowd run 上逐帧比对，真不一致 = 0）；分析代码 = `a9895d1e`（`instrument_v2_judge.py` 生成一页表时的提交）。
> **预注册**：`evidence/prereg_instrument_v2.md`（判据先锁 `3cecccfe`，早于任何跑批）+ 修正案 1（§9，`29f21703`）。
> **关卡①**：slam-critic **先于本文件落盘**，共 3 轮——第 1 轮 Reject（1 致命/7 重大/6 次要）、
> 第 2 轮 Reject（3 重大）、第 3 轮 **Accept-with-conditions**（4 条件：分析码 sha 记错 / thin 分母未落表 /
> §5 回引二义 / night_report 旧名 / 对照脚本前提未声明）——**条件已逐条清零**（见 §7）。
> 全量报告：`/tmp/instrument_v2_gate1_2026-09-24.md`、`..._round2_...md`、`..._round3_...md`。
> **写作纪律自查（NOTES 三问）**：本判决是**诊断级仪器重读**，不是机制主张——不进贡献栏、
> 不起包装名、不作 headline（`DISCIPLINE.md:363-364`）。其结论只回答"测量地基是否可靠、
> 哪些历史判决在此地基上仍成立"，机制侧（A/B）另议且依 prereg §5 呈报用户。

## 0. 一句话终局

仪器 v2 使 **C1 从"整体成立"降为"部分成立"**：prereg §4 判据子集 9 对中 **2 对达标**
（均为 **balloon2 s1/s2 且方向为 exit 改善**，三参照 median −2.57/−2.78/−3.96 与 −3.57/−2.09/−5.82）；
**mvnobox 3 对三参照同号但量级未达 0.5cm**（0.09–0.42，且 s2 方向反向）；**crowd3 3 对不可判**
（对照区结构性缺失）；**pt 不可判**（符号随参照翻转、跨 seed 不一致）。同时查明一项**仪器级硬限制**：
**密人群域不存在对照区**（crowd2：全域静态与邻域环支撑中位均为 0，可用帧 2–8/17）⇒
**任何"腾空区 vs 静止区"型仪器在该域都判不了效**（night_report §3 的 TUM 结论在 Bonn 人群族复现）。

## 1. 目的与判据（先锁）

- **目的**：night_report §3b/§3c 发现官方 freshvac（全域静态参照）在 pt 上的"残影超额"换邻域环参照
  **符号翻转**（+3.19 → −2.95cm）⇒ 参照区构型偏差与目标效应同阶。本仪器加**第三对照**（深度分层匹配）
  分离二者，并对全部已有臂重评分（**只重渲染不重训**）。
- **判据（prereg §4）**：C1 支柱（prereg 子集 = balloon2 / mvnobox / crowd3，9 对）三参照 median
  **同号** 且 **|median| ≥ 0.5cm**；方向规定 **负 = exit 改善**。
- **主读数（prereg §2）**：逐帧配对 Δ = 臂 − off（同帧集）再取 **median + IQR**（禁均值单独作结论）。
- **可判性判据（修正案 1/§9）**：任一参照可用帧 < 50% 两臂共同帧，或任一臂 support 像素中位为 0
  ⇒ ⚠稀薄 ⇒ **判效不可用**，不计入达标。

## 2. 方法与仪器

三参照逐帧并行于同一 vacated 区与同一渲染深度（`utils/instrument_v2_core.py` / `instrument_v2_rescore.py`）：

| 参照 | 定义 |
|---|---|
| 全域静态 | GT 有效 ∧ ¬dyn ∧ ¬vac（官方 freshvac 口径） |
| 邻域环 | dilate15(vac) ∧ ¬dilate5(vac) ∧ 静态 |
| **深度分层匹配 (m3)** | 静态 ∧ GT 深度 ∈ vac 区 GT 深度中位数 ± 带（±15%，支撑不足按 §3 序放宽至 ±25%）∧ 距边 ≥15px ∧ 支撑 ≥200px |

仪器参数：m3 帧内采样上限 5000 px（跨帧共享随机流，固定种子 0）；边缘排除仅作用于 m3；
`--config` 支持继承式配置解析（L2 补跑用 `/tmp` → 见 §6）。**实施与原文字的差异**已登记 prereg §8。

## 3. 结果（权威数字 = `evidence/instrument_v2_onepager_table.md`，程序化生成）

### 3.1 C1 支柱（prereg 判据子集 9 对）

| 支柱 | seed | Δ 全域静态 / 邻域环 / m3（median，cm） | 读数 |
|---|---|---|---|
| balloon2 | s0 | −0.80 / +1.95 / −2.08 | 混号 |
| balloon2 | s1 | **−2.57 / −2.78 / −3.96** | **存活·改善** |
| balloon2 | s2 | **−3.57 / −2.09 / −5.82** | **存活·改善** |
| mvnobox | s0 | −1.72 / −1.43 / −0.24 | 同号<0.5 |
| mvnobox | s1 | −3.35 / −0.42 / −1.92 | 同号<0.5 |
| mvnobox | s2 | +0.69 / +0.25 / +0.09 | 同号<0.5（方向反向、量级 ~0） |
| crowd3 | s0/s1/s2 | 三参照数值见一页表 §1 | **不可判（对照区缺 ⚠稀薄）** |

- **汇总：2/9 达标**（含 thin）；**不含 thin 的对照读法 = 4/9**（另含 crowd3 s0/s1，两者均 ⚠稀薄，
  且 s0 方向为 exit 变差）——两读法并陈见 prereg §9。
- **三参照共同帧严格版**（一页表 §1b）：balloon2 s0/s1/s2 **全部同号**（s0 的环腿 −0.34 偏弱），
  mvnobox 三对同号、crowd3 共同帧仅 6/17。
- 扩展序列（balloon / mvnobox2，非 prereg 判据）：达标 0/6。

### 3.2 pt（person_tracking / person_tracking2）

6 对中 3 对同号、3 对混号（且同号者方向不一致）⇒ **符号不一致 ⇒ 效应量 < 仪器分辨力，
pt 侧 1–2cm 级效应不可判**（与 night_report §3b 预期一致）。

### 3.3 其余臂（如实落表，一页表 §3）

L1b gate 三参照 −2.55/−1.16/−0.48（同号<0.5，方向与历史结论一致但量级未达阈）；
L1c occ、L1d stacked、L1e seam/param 以**混号为主**（与其"无稳定效应"的负结论一致，未被 v2 推翻）；
crowd/crowd2 行均 ⚠稀薄（对照区缺）。

### 3.4 TUM

prereg §2b 规定**只落表不判读**（官方 render_compare 为准）：全域静态对照在密集帧上缺失、
邻域环与 m3 方向相反且量级 ±20–44cm。

## 4. 仪器级发现（本轮附加价值）

1. **对照区结构性缺失（人群族）**：`past`（历史掩码并集）覆盖 ≈66–100% 视野 ⇒
   全域静态支撑中位 = 0、邻域环 = 0；crowd3 可用帧 8/8/6（共 17）、crowd 仅 2/2/2。
   ⇒ **"腾空区 vs 静止区"型指标在密人群域不可用**（比"未通过"更强的陈述：该类仪器在此域
   连判效资格都没有）。
2. **邻域环支撑本身很小**：稀疏域（balloon2）环支撑中位仅 **2,882 px**（vac 200,522 px）——
   环是"薄环带"，样本量远小于目标区，读数对小样本噪声敏感。
3. **`ghost_population_census.py` 跨帧污染**（独立发现，已入 NOTES 踩坑）：同一 `no_grad` 块内
   连做 3 次归因渲染，浮点残留污染后续帧基准渲染（balloon2 off s0 批量 vs 单帧最大差 12.7cm；
   单帧重跑与 instrument_v2 逐位一致）⇒ 夜间普查的**逐帧数字**（非中位聚合）带此污染。
4. **全域静态对照空集守卫缺失的后果**（本仪器自身修复）：无守卫时空集区产出 NaN 并污染
   run 级中位（30 run 受影响）——已由 `5695bc94` 修复并做旧/新码逐帧对照。

## 5. 核心交付：哪些历史判决在 v2 下仍成立

| 历史判决（出处） | 原口径读数 | v2 三参照读数 | v2 下的判定 |
|---|---|---|---|
| **C1 深度侧有效（D2-002 / L3 正式批）** | mvnobox Δ−4.1cm / balloon2 Δ−3.1cm（全域静态） | balloon2 s1/s2 **存活·改善**；mvnobox 同号但 0.09–0.42（未达阈，s2 反向） | **部分成立**：balloon2 腿成立；**box(mvnobox) 腿未达 v2 阈值**⇒ D2-002 的"box+balloon 一并有效"表述须收窄为 balloon 族 + box 族"方向一致但量级不达标" |
| **L1b gate 主判 PASS（D1-004，−1.893cm）** | −1.893cm（污染代理口径） | −2.55/−1.16/−0.48（同号<0.5） | **方向成立、量级未达 v2 阈值**；其"PASS"依赖当时口径 |
| **L1c occ / L1d stacked / L1e seam+param（负）** | 主判皆败 | 混号为主 | **与 v2 一致**（负结论未被推翻） |
| **L3 人群族判读（D1-004：5/9 PASS → 人群族全否）** | 人群族全否 | 人群族**不可判**（对照区缺） | **改判为"不可判"**：该域此仪器类无判效资格——比"未通过"更强的否定 |
| **TUM 移植支（D1-012：关闭）** | Δ mean −0.160（官方口径） | 本仪器不判读（§2b） | 不变（官方 render_compare 为准） |
| **静态 PSNR 线（D1-007 重算）** | 臂间 spread 0.17–0.69dB | 不在本仪器范围 | 不变 |

**一句话**：v2 保住 **balloon2** 一条腿、把 **box 腿**降为"方向一致但未达阈"、把 **人群族**从
"未通过"升级为"**不可判**"、把 **pt** 判为"**不可判**"；负结果类历史判决全部维持。

## 6. 覆盖率与范围偏差

- prereg §2b 期望 109 run；**可评分 103 run**（= 109 − L2 6 run）。
- **L2 gate 6 run 不可评分**：run 目录无 `config.yml` 快照、`plot/trj_full_final.json` 两侧工作副本已空
  （git 亦从未跟踪；远程被清空目录 mtime 2026-09-22 23:57 为证）⇒ 无相机位姿无法重渲。
  补跑已尝试（`--config` 指向 `configs/experiments/lifecycle_paper2/l2_*_gate.yaml`，解析成功）
  但止于 trj 缺失；未采用"用存盘 depth PNG 反算"的替代路径（第二条测量代码路径，且 L2 为已关闭
  诊断臂，不影响 §4 判据）。证据：`rescore_batch_shard*.done` 6 条 `rc=1` + `rescore_l2supp.log`。
- 本地 pilot 3 run（`sample_balloon2_*`）为脚本对拍用，**不在 `rescore/` 内、不进入任何判读计数**。

## 7. 关卡① 记录与整改（条件清零）

| 轮 | 结论 | 主要项 | 整改 |
|---|---|---|---|
| 1 | Reject | 1 致命（crowd3 计存活却违反自定 §5 规则）+ 7 重大（双溯源 103/73 混、三参照非同帧集、对照空转、分母偏离 prereg、方向未进标签、IQR 未落表、`m3_under_supported` 未实装） | 可判性判据统一为"可用帧占比"；标签加方向；判据子集与扩展分列；IQR 与可用帧落表；prereg §8 实施澄清 |
| 2 | Reject | 3 重大（对照无工件 / thin 分母二义 / thin 属事后判据门未走修正案） | 对照做成可复跑工件（`control/`）；分母唯一化并落 §1c 列；**修正案 1（§9）** 登记 thin + 两读法并陈 + 呈报 D2 |
| 3 | **Accept-with-conditions** | 条件 4 项（分析码 sha 记错 / 分母未落表 / §5 回引二义 / night_report 旧名 / 对照脚本前提） | 表在含生成码的提交处重生成（`a9895d1e`）；分母列入表；§5 对齐 §9；night_report 加命名追记；脚本与报告声明远程+GPU 前提（远程实跑 rc=0） |

## 8. 复跑命令（任何一条都可独立验证）

```bash
# 判读表重生成（只读 rescore/*.json）
/data/conda_envs/monogs-ours/bin/python scripts/02_analysis/instrument_v2_judge.py \
  --out results/lifecycle_paper2/evidence/instrument_v2_onepager_table.md
# 守卫路径对照（需远程 3090 + 该 run 的 PLY）
ssh jiangwenheng@172.16.227.24 'cd ~/cron/monogs-ours && PY=<远程python> bash scripts/02_analysis/instrument_v2_guard_control.sh'
# 单测（第三对照构造 + 负对照）
/data/conda_envs/monogs-ours/bin/python -m pytest tests/lifecycle_paper2/test_instrument_v2_m3.py -q
```

## 9. 呈报（D2，prereg §5 触发）

**prereg §5 明示**：若 C1 在 v2 下不（整体）存活 ⇒ **呈报用户，不自动改叙事**。本判决即该触发条件：
- 事实：C1 判据子集 2/9 达标（含 thin）/ 4/9（不含 thin）；balloon2 腿成立、box 腿收窄、人群族与 pt 不可判。
- **待用户拍板**：① 论文叙事如何据 v2 收窄（是否把"box+balloon 深度侧有效"改为"balloon 族成立 +
  box 族方向一致未达阈"）；② 是否接受"人群族/密人群域不可判"作为边界陈述；③ 机制路线 A/B
  是否据此调整（观测债补偿 A 的目标量在人群域同样面临"无对照"的度量问题）。
- 本判决**不落任何机制主张**，也不动历史 verdict 原文（仅日志式指针）。
