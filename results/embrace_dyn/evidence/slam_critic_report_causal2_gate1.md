# 审查报告：embrace_dyn 因果轮 II 裁决草稿（关卡①，第三次派发）
日期 2026-09-18，审查者 slam-critic，只读。
审查对象：results/embrace_dyn/evidence/verdict_dyn_probe_causal2.md（待落地）
仓库 /data/monogs-ours，分支 dev/v2，HEAD 4ae3192e
状态：进行中（本文件增量追加）


## 审查对象
- `results/embrace_dyn/evidence/verdict_dyn_probe_causal2.md`（裁决草稿，待落地，mtime 09-19 03:11）
- 预注册 `prereg_dyn_probe_causal2.md`；判据机 `analyze_dyn_probe.py:analyse_causal2`；测量代码 `dyn_probe.py`（config `probe_pt2_causal2.yaml`）
- commit：HEAD `4ae3192e`（草稿）← `38e9d10a`（判据机）← `15a7ad55`（预注册+config+测量代码同批先提交后跑）
- 分支 dev/v2；工作区**不干净**：`dyn_probe_report.md`、`dyn_probe_verdict.json`、`manifest.json` 均被修改未提交

## 机械事实
- `git show 15a7ad55 --stat`：本提交含 `configs/experiments/embrace_dyn/probe_pt2_causal2.yaml`、`evidence/prereg_dyn_probe_causal2.md`、`scripts/02_analysis/dyn_probe.py`（+272/-45）。**本轮机制确实在 15a7ad55 内**；判据机改动在 9f28a8e2→38e9d10a 之后，属"其后单独提交"（与草稿第 9-10 行自述一致）。
- 未跑 health_check（未涉及配置审计判定；本审查不依赖它）。

## 问题清单

### 致命
**[致命] 裁决草稿的数字与判据机工件不一致，且部分数字在两个地图的任何口径下都无法复算**
证据：
- 草稿第 38 行把 **gate 行**原样标注为 baseline："baseline 地图同向（P2cr：19.85 / 13.64 / bad 19.75 / 20.47 / 静态 −0.83 dB）"——我复算 gate P2cr 12 帧恰为 19.85/13.64/19.75/20.47/−0.83；判据机 baseline 实际为 `dyn_psnr 20.2856 / 13.3935 / bad_psnr 20.0371 / 20.2474 / static −0.98`（`dyn_probe_verdict.json` baseline means + criteria D4 `d_static_db: -0.98`）。
- 草稿第 43-47 行的 gate/baseline 双值，第二值有 4/6 与判据机 baseline 不符：D2 `0.035` vs 判据机 `0.0778`；D3 `0.577` vs `0.6054`；D4 `−0.89` vs `−0.98`；D1 `1.021` vs `1.026`；D6 `1.36` vs `1.3756`（1.3756 应四舍五入为 1.38）。
- 草稿第 34 行 P2cm 行 = 混合口径：`19.19`(gate 15 帧) / `21.12`(无任何口径可复算) / `18.88`(gate 15 帧) / `24.27`(gate 15 帧) / `—` / `20.55`(无任何口径可复算) / `21.33`(gate 15 帧) / `4,234`(12 帧)。而表头第 24 行声明"同帧集 n=12"。对照我复算：gate 12f = 17.76/16.95/17.37/24.58/5.72/19.88/21.57/4234，gate 15f = 19.19/17.23/18.88/24.27/5.67/19.89/21.33/3426，baseline 12f = 17.90/16.86/17.35/24.71/5.68/20.16/22.19/4234，baseline 15f = 19.50/17.41/19.09/24.76/5.65/20.21/21.91/3426。
- `good_dl1` 填 "—" 与工件矛盾：raw 记录里 P2cm 有 `dyn_good_dl1_cm`（gate 12f 5.72 / 15f 5.67）。
依据：P1/P24/P29 同类（数字-口径混引家族）；D3（results 工件）；DISCIPLINE §收口审查关卡第 1 条（判决落地前）
反驳通道：给出生成该行/该列的命令与所用文件（须能一键复算到草稿的 `21.12`、`20.55`、`0.035`）

### 重大
**[重大] 判据机工件未提交，HEAD 不可复算本判决**
证据：`git diff --stat` 显示 `dyn_probe_verdict.json` +315 行（`causal2_judgments` 整块）、`dyn_probe_report.md` +52 行（"因果轮 II"节）、`manifest.json` +32 行（`round_3_causal2`）全部只在工作区；`git show HEAD:.../dyn_probe_verdict.json` 无 causal2 键。
依据：D5（最小单元提交）；收口关卡"必须早于不可逆步骤"（判决引用工件须与 commit 对应）
反驳通道：把三个工件提交后再审，或说明为何草稿的数字来自未入库工件

**[重大] manifest.json 已在关卡①通过之前把草稿登记为工件**
证据：`manifest.json:315-319` `round_3_causal2.verdict = evidence/verdict_dyn_probe_causal2.md`（该块本身也是未提交改动）；草稿第 3-4 行自称"⏳ 待过、不得当作已收口判决引用"；`4ae3192e` 已把草稿 commit。
依据：DISCIPLINE §收口审查关卡（判决/manifest 落盘必须在审查之后）
反驳通道：提供 manifest 该块与 commit 的时间顺序证据，或改为审查通过后再登记

**[重大] §5"离线最小机制已到边界 + 剩余路径唯一化"越界：至少 4 条便宜变体未试**
证据：草稿第 75 行"剩余路径只有两条"。未试项（每条都与本轮结论直接相关）：① 退化帧回退到"保持"——草稿 F6 第 54 行自己写明"任何走几何估计的机制都必须带预注册的退化回退规则（本轮未定义）"，即已知有一条一行代码的改善路径却判"边界"；② 用 >2 个 KF 做最小二乘运动估计（本轮只用相邻 2 KF，`dyn_probe.py:917` `rigid_between(pc_prev, pts_cache["cc"])`）；③ 把外推限制在小 Δt（`frac` 实测 0.2–0.6、`dt_eval` 1–3，未做分档）；④ CC 之外的掩码稳定化（面积过滤/形态学）——臂空间实际只有 1 种掩码稳定化 × 2 种运动模型，且全部离线 GTMC 冻结掩码、单序列单 seed、两张同批地图。
依据：DISCIPLINE「负结果处理」第 2/3 条（必须先穷尽改善路径；"方向走不通"须给可复核证据）；D6；D8
反驳通道：逐条说明为何该变体不可行/已被前置实验排除（给出对应 run），或把 §5 的措辞降级为"本轮三条最省机制不达标"

**[重大] 预注册声明的 P2cm 臂未被判据机评估，草稿以来源不明的数字补位**
证据：`analyze_dyn_probe.py:271` `need = ("P1","P2","P2c","P2cs","P2cr","C-c")`（不含 P2cm）⇒ `m` 无 P2cm ⇒ `:297-300` `ablation_translation_arms` 只在 `m.get(a)` 存在时填值，报告实际输出 `{}`（`dyn_probe_report.md` "平移类臂消融（不判）：{}"）；而 P2cm 已实跑 15 帧（`dyn_probe_causal2_results.json` arms.gate.P2cm ok=15）。预注册 §1 第 4 行把 P2cm 列为臂、§4 第 3 条有分支判据"若 P2cm ≈ P2cr ⇒ 机制可更简单"。
依据：D9（组件/臂生效须有读数）；D16（预注册覆盖）；prereg §4 分支未收口
反驳通道：补出 P2cm 的判据机读数（同帧集、同 keys）并说明该分支结论

**[重大] 同帧集 n=12 的成员由被审臂自身失败决定，预注册未覆盖、无敏感性分析**
证据：`dyn_probe_causal2_results.json` arms.gate：P2c/P2cs/P2cm ok=15（f93/243/561 在内），P2cr/C-c ok=12（`no_velocity` 3 帧，`frame/kf` = 93/90、243/240、561/560）；`_paired_means`（`analyze_dyn_probe.py:35-47`）取 6 臂交集 ⇒ 交集由最弱臂 P2cr 决定，P2c 的"参考值"从 15 帧的 0.138 变成 12 帧的 0.158。
判定（明确回答派发包问题 1）：**不构成"跑后改口径改判据"**——D1–D6 的公式与阈值我逐条对照预注册 §3 与 `analyze_dyn_probe.py:26-30,253-302` 完全一致（harm 0.25/0.25、cost 0.50、instrument 1.15、D1 0.95、D2 0.40、D3 0.75），NO-GO 也是预注册"出局规则 ¬D2∨¬D3"的直接结果；但**评估域（population）确属跑后确定**，预注册 §1 只锁了冷启动规则。我做的敏感性复算：15 帧口径下 D1 = 1.0222（仍 ❌）、P2c 外观保留 0.138 ⇒ 判决方向不受影响（P2cr 在 3 帧上根本无输出）。
依据：P15（口径/抽样）；预注册 §3-§4；D8
反驳通道：给出 15 帧口径的完整并报表（含 P2cr 缺席帧标注），或说明为何交集口径已足够

### 次要
- **[次要] F6 的 KF 对标注与工件不一致**：raw 记录 `kf`=90/240/560，且同批 `dt_kf` 恒 5.0（`dyn_probe.py` 记 `dt_kf = k - kp`）⇒ 应为 85/90、**235/240**、555/560；草稿第 52 行写"240/245"。依据 P1（数字须与工件一致）。
- **[次要] F7 低估了自身证据、归因未分离**：草稿第 57 行只报 max 0.67m；我复算 12 帧中 **5 帧 icp>0.05m**（预注册 §4 第 4 条正是以 5cm 为"不可刚性对齐"触发线），中位 3.9cm 则 < 5cm ⇒ "错误模型"与"外推应用方式错误"在现有工件下不可分离，建议改为引 5/12 计数。
- **[次要] 掩码统计存在样本选择效应**：`mask_cc_frac` 仅 12 帧（12 个值：min 0.2074 / median 0.9001 / max 1.0），被排除 3 帧的记录只有 `frame/kf/no_velocity` 三个键（无 cc_frac/icp_rmse_m）⇒ 被排除帧恰是"CC 可能最激进/点云退化"的帧，未读数；故"CC 无贡献（D1 1.025）"不能推广到全部 15 帧（虽然 15 帧复算 1.0222 仍 ❌）。
- **[次要] P2cm 低于全擦除基线这一事实未点明**：gate 12 帧 P2cm bad_psnr 17.37 < P1 erase 19.19 ⇒ 保留率为负（−0.16），中位速度臂比"什么都不建"更差；草稿只写"更差"（相对 P2cs/P2c 而言）。
- **[次要] 流程次序**：草稿在自称"待过"的同时已被 commit（4ae3192e）且 manifest 已登记其路径，与"关卡须早于落盘"的次序相反（已由草稿首行免责声明部分缓解）。

## 无法验证清单
1. **探针原始日志缺失**：`grep -rls "rigid 估计失败|Degenerate covariance rank" results/` 仅命中 verdict/prereg/README/manifest 四个文本文件，`results/embrace_dyn/` 下无探针 consolelog ⇒ F6 的异常类型（`GeometryException: Degenerate covariance rank`）与"3/15 帧"只能由 JSON 的 `no_velocity` 计数（3）间接支持，异常名不可独立核实。需：探针 stdout 落盘路径或 `run_batch`/`tee` 日志。
2. **草稿 baseline 组数字的生成来源**（见致命项）：现有 3 个工件都无法复算，缺"生成命令 + 输入文件"这一证据链。
3. **P2cr 失败的物理原因**（掩码点云近平面 vs 掩码覆盖率骤降）无法从工件区分：被排除 3 帧无 cc_frac，需补该 3 帧的诊断输出。

## 已验证（供被审方复用的正面核对）
- 判据机公式/阈值与预注册 §3 逐条一致（含 D4 的 abs 与 full 两项、D5 的 `mean_n_dyn/n_static`、D6 的 C−c/P2cr）。
- gate 12 帧 P2c `bad_dl1` 均值 19.6608 与 `causal2_judgments.gate.means.P2c` 完全一致（逐帧复算）；D2 0.0475、D3 0.5826、D4 −0.8309、D5 0.0767、D6 1.3217 与草稿 gate 数字一致 ⇒ **§2 gate 组与 §1 判决可复算**。
- 配置/臂规格一致：`probe_pt2_causal2.yaml` 臂列表含 P2cm/P2cs/P2cr/C-c，`ARM_SPEC`（`dyn_probe.py:385-392`）与预注册 §1 表逐条对应（CC=mask "cc"、median=中位速度、rigid=常扭转、C−c=+0.30m 相机系横移）。
- 帧清单：轮 II 12 帧 ⊂ 轮 I 15 帧（12 ⊂ [93,122,...,561]）✓。

## 审稿结论
**Reject**（阻塞项 = 致命项：裁决草稿引用的 baseline 组与 P2cm 行数字与判据机工件不一致/不可复算；其余重大项须逐条处理或写明不采纳理由后才可落地为"✅ 已过"）。
