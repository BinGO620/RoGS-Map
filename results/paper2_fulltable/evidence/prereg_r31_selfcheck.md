# 预注册：自校验式 SWBA 门重测（R31，2026-09-15）

> **账本登记（2026-09-25 追补，D2-015 同例；原文零改动）**：本预注册属账本设立前的文书，决策留痕见 `NOTES.md` 实验清单与 git 历史；本轮由 health_check H5 扩表（`prereg_*` 纳入覆盖面）后检出为“未挂账本号”，按机制登记补入本指针，不追改正文。

> 依据：`results/paper2_fulltable/evidence/verdict_r25_recheck.md`（R25 代价门
> 从未在有效阈值下被测试；否决理由"SWBA 边无掩码"与代码不符）。
> **纪律合规**：零代码改动——机制已实现（`swba_min_rel_improve`），
> 本实验为纯 config 实验（DISCIPLINE #2）。判据先锁定（本文件），
> 跑批在判据锁定之后。

## 一、假设与动机

**假设 H1**：SWBA 的窗口光度代价相对改善 `rel_improve` 若设在**信号量级**
（0.5%–2%，而非 R25 的 20%），可作为"修正是否有益"的自校验信号——
在易序列（有害修正）上拦截，在 pt1（有益修正）上放行，从而**消除
static_conf 绝对阈值的跨序列敏感度**（实验 F 的问题）。

**动机（解决什么）**：实验 F 证实 static_conf 门控存在阈值敏感度，根因是
static_conf 的绝对水平跨序列不齐（balloon 中位 0.343 vs crowd2 0.432）。
自校验门不依赖"难度阈值"，而是直接问"这次修正有没有降低（静态）窗口代价"，
原理上对序列无关。

**关键前提（R25 复核的修正）**：SWBA 边**已应用 person 掩码**
（`dba_lite.py:91-95` 源侧、`swba.py:176-178` 目标侧），故窗口代价是
**静态像素上的代价**，不是"被人物像素欺骗的代价"——R25 的循环论证
否决理由不成立。

## 二、实验设计

- **臂**：`r31_selfcheck_{0.5,1,2}` = gate 臂（SWBA 0.38 + LoopClosure）
  + `swba_min_rel_improve ∈ {0.005, 0.01, 0.02}`
- **序列**：标准 Bonn 7 序列
- **seed**：0, 1（2 seed，筛选纪律）
- **对照**：r29_framegate（0.38，无自校验门）为参照；baseline 为下界
- **config 派生**：从 `r29_framegate_*.yaml` 复制，仅加
  `swba_min_rel_improve` 一行 + 改 save_dir（单变量）

## 三、预注册判据（跑批前锁定）

**主判据（易序列不退化）**：对 crowd2/crowd3/balloon，自校验门臂的
全帧 ATE ≤ r29_framegate 同序列值（允许 +3% 噪声带）。
- 通过 ⇒ 自校验门在易序列上等效或优于 static_conf 门

**副判据（pt1 增益保留）**：person_tracking 自校验门臂 ATE ≤ 8.2cm
（即 r29 的 7.83 + 5% 容差），且 < baseline 13.62 显著。
- 通过 ⇒ 有益修正未被误拦

**机制判据（生效验证，DISCIPLINE #9）**：consolelog 中
`correction not applied` 计数 > 0 且 `applied` 计数 > 0
（两态都出现 ⇒ 门在判别，而非恒开/恒关）。
- **不满足则该臂作废**（重演 R25 的恒 skip 事故）

**判决规则**：
- 三门全过 ⇒ 自校验门成立，作为 static_conf 门的**替代或叠加**候选，
  进入 3-seed 晋级确认
- 主判据过、副判据否 ⇒ 自校验门过严，误拦有益修正（记录，调阈值方向）
- 主判据否 ⇒ 自校验门判别力不足（与 R25 的真实观察一致），
  记入已排除方向，回到"维持 static_conf 门 + 如实报告敏感度"

## 四、成本与风险

- 成本：3 阈值 × 7 序列 × 2 seed = **42 run**（~2.5h，双卡）
- 风险 1：阈值仍可能全 skip/全 apply → 机制判据（第三节）先拦，作废重设
- 风险 2：自校验门与 static_conf 门可能冗余（都拦易序列）→ 副判据区分
- 风险 3：`rel_improve` 在**掩码后**的静态代价上重算，信号分布可能与
  R25 时代不同 → 跑前先做 1 run 探针读日志分布（见第五节）

## 五、执行顺序

1. **探针（1 run，~30min）**：`r31_selfcheck_0.005` × crowd2 × seed0，
   读 consolelog 的 `rel_improve` 分布，确认信号量级与两态共存
2. 探针通过 → 派 42 run 正式批
3. 收口：verdict_r31 + manifest + 更新骨架 §4.6（若成立）

## 五之二、探针实测（2026-09-15，本地 2060，机制判据通过）

探针在本地 2060 跑全序列（截断跑不可用：前 150 帧 static_conf 全 >0.38，
SWBA 零执行）。两序列各 1 run，seed0，阈值 0.5%：

| 序列 | gate-checks | applied | skipped | skip 率 | applied 的 rel_improve | skipped 的 rel_improve |
|---|---|---|---|---|---|---|
| crowd2（易） | 178 | 35 | 30 | 46% | 0.5–2.4% | 0.0–0.4% |
| person_tracking（难） | 115 | 63 | 44 | 41% | 0.5–3.7% | 0.0–0.5% |

**机制判据通过**：两序列均两态共存（skip>0 且 apply>0），阈值 0.5% 恰在
信号分布内部，门确实在判别——**R25 的"恒 skip"事故未重演**。

**但探针已给出预警**：两序列的 skip 率几乎相同（46% vs 41%），
`rel_improve` 分布高度重叠（易序列 0.0–2.4% vs 难序列 0.0–3.7%）。
自校验门若无法在**放行率**上区分易/难序列，则它拦掉的修正对两侧是
同一类，主判据（易序列不退化）能否成立存疑——正式批 42 run 定论。

> 日志口径注记：`Log()` 用 rich Console，`[gate-skip]`/`[rel-gate skip]`
> 标记被 markup 解析吞掉，计数须用 `correction not applied` /
> `edges free=`（见 NOTES 2026-09-15 踩坑）。

## 六、纪律映射

- 预注册先行（本文件）✓
- 零代码改动（纯 config）✓
- 2 seed 筛选（DISCIPLINE seed 两级）✓
- 生效验证（机制判据）✓
- 单变量（仅加 `swba_min_rel_improve`）✓
- 若判负：如实记录，不包装
