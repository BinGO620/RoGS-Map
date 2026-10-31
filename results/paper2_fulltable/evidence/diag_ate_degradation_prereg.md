# 诊断预注册：R33 批 ATE 劣化的归因（零 GPU 纯重分析）

**落盘时间**：2026-09-19（在任何全量提取运行之前；此前只看过 balloon/crowd2 的 gate 臂 seed0 各 10 行 + 代码语义）
**对象**：`results/paper2_fulltable/` 的 R33 同批（4 臂 × 7 序列 × 3 seed = 84 run），零 GPU、只读
**动机**：关卡② 致命项——`gate` 相对 `baseline` 在 5/7 序列 ATE 劣化、过 5cm 线集合与 baseline 相同。已做的分解（21 个 seed×序列配对点）：**元凶是 SWBA**（+SWBA 中位 +0.71cm），R26 门在救火（中位 0.71→0.29），全批净效应 ≈ 0（均值 −0.09cm），pt1 大赚 −3.4cm。

## 0. 代码语义（已核实，作为假设的基础）

- 四臂唯一定义差（crowd2 seed0 的合并 config 实测）：
  `baseline`（无 SWBA/LC）→ `swbaonly`（+SWBA **总是跑**）→ `final`（+LC）→ `gate`（在 final 上**仅**加 `SWBA.swba_max_static_conf: 0.38`）。
- R26 门（`utils/slam_frontend.py:2307-2336`）：`static_conf ≤ 0.38` 时 SWBA **才跑**（"tracker struggling 才修"）；`static_conf > 0.38` 打 `[rel-gate skip]`。
- `static_conf` 的计算（`utils/slam_frontend.py:1232-1233`）：`reliability_soft = (1−w_map)` 的**全帧均值**——`w_map` 是逐像素跟踪权重（动态/不可靠像素 ≈1）。
  **⇒ 动态占比大的帧，均值被动态区系统性拖低，即使静态背景跟踪良好。**
- 每帧的 person 掩码像素数有逐帧 log（`Semantic insertion gate frame N: X person px zeroed`）⇒ 可以构造 **masked-mean 代理**。

## 1. 假设（跑前写死）

- **H1（信号口径错配，主假设）**：`static_conf` 全帧均值被动态区拖低 ⇒ 在"动态占比大、静态背景跟踪良好"的序列（balloon 类）上**误开 SWBA**（其窗口光度边恰好被动态污染——R26 注释自己承认"no mask"）。
  **可检验推论**：masked-mean 代理 `mean/(1−dyn_frac)`（假设动态像素 reliability≈0 的下界修正）在 balloon 上**跨过 0.38**（门会关），在 pt1 上**仍 ≤0.38**（门仍开、大赚保留）。
- **H2（修正量不携带方向信息）**：SWBA 的 `|dt|`（平移修正量）在有害与有益序列上同量级 ⇒ "修多少"不区分"该不该修"，门控必须依赖信号而非修正量。
- **H3（窗口数非主因）**：balloon 轨迹短（439 帧）不是它救不回的原因（crowd3 854 帧且被救回；KF 数与效益方向无系统相关）。
- **H4（pt2 的通道构成）**：pt2 的劣化 = SWBA（+1.43）为主 + LC 加重（+0.56），R26 门只救回 −0.71 ⇒ 门在 pt2 已部分生效（存在 skip）但留残余；残余来自"信号说 struggling 而 SWBA 边仍被污染"的那部分帧。

## 2. 提取清单（只读 consolelog + 既有 JSON）

每个 run（84 个）：`SWBA gate kf=N: static_conf` 全轨迹、`[rel-gate skip]` 计数、
`SWBA kf=N: N edges free=[..] anchors=M |dc| ..% |dt| med .. max ..` 全量、
`SWBA kf=N: [gate-skip] rel_improve` 计数（内层门）、`Semantic insertion gate frame N: X px`（掩码轨迹）、
LoopClosure `verify/plain|icp` 计数；ATE 取自 `tables_paper2_preview.json`（不重算）。

## 3. 判定规则（跑前锁定）

对每个序列算三个效应（3-seed 均值，ate_mean 差）：
`E_SWBA = swbaonly − baseline`；`E_LC = final − swbaonly`；`E_gate = gate − final`（负=救回）。

- **判 (a) 信号/配置级可修**，当且仅当：**单一**信号变换（masked-mean 代理，不逐序列调参）能把
  "门开（修正后 conf≤0.38）⇒ SWBA 实际有益（E_SWBA<0 或 |E_SWBA|<0.2cm）"的序列级一致率提到 **≥6/7**
  （对照：现行信号的同一口径一致率）。此时修法 = 把 R26 门的信号从全帧均值改为掩码内均值（一处代码、config 开关、默认关闭逐位一致）。
- **判 (b) 机制固有**：否则（代理无法分离，或有害/有益序列的 conf 分布重叠到任何单一阈值/变换都分不开）。
  此时只做论文口径收窄，诊断结论写进失败归因。

**边界**：本诊断是**纯重分析**，其代理信号 ≠ 实装后的真实信号（动态像素的 reliability 并非恰为 0）；
判 (a) 只是"值得进入例外流程实装快筛"的依据，不等于修法已验证。实装仍须：预注册判据 → 先提交 → 2060 快筛 → 3090 2-seed。

## 4. 不做的事

不跑任何 GPU；不改任何代码/config；不动 results/ 原始输出；结论只落
`diag_ate_degradation.{json,md}` + NOTES #26；数字一律 dump-to-table，禁手抄。
