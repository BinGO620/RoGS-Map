# 关卡② G2 整改自核销 — 论文2 tex/bib（2026-10-09）

> **账本**：D2-028 续轮。
> **审查报告**：`/tmp/slam_critic_g2_paper2_bib_2026-10-09.md`（slam-critic，G2 判决档）。
> **结论**：slam-critic **Accept-with-conditions**（无致命；2 重大 + 2 次要）。
> **处置**：2 重大**全销** + S1 说明 + S2 已改。本件为自核销记录（每项给复核证据）。

## 0. 被审对象
- base `479d7f3e6` → 被审 HEAD `f93101039`（commit `618609929`/`e9db9f03f`/`f93101039`）
- 整改 commit = `ae0889bdb`

## 1. 【重大 M1】等价性声明只被 2 臂中 1 臂支撑，且引证错宿主 —— **销**

**critic 指控**：tex §Codec Generalisation 新增句「the panel's maps come from runs under the
same arm configuration as the main panel」不成立——codec **主**面板臂 = `{baseline, final}`
（`scripts/gs_compress/l2_batch.sh:13` `ARM=(baseline final)`），codec **留出**面板臂 =
`{rb, gate}`（`scripts/gs_compress/l3_batch.sh:13` `ARM=(rb gate)`）；`baseline`↔`rb` 一致但
**`final`↔`gate` 不一致**（`SWBA.swba_max_static_conf` = `None` vs `0.38`）。而我的指纹脚本
`ARM_MAP` 核的是 **ATE 表三臂**（`baseline/swbaonly/gate` ↔ `rb/sw/gate`）**非 codec 面板**。

**独立复核（采纳）**：
- `ARM=(baseline final)` / `ARM=(rb gate)` 逐字确认（上引行）；
- 逐字段实测：`main[baseline]`=`SWBA=None conf=None LC=None` ≡ `held[rb]`；
  `main[final]`=`SWBA=True conf=None LC=True` ≠ `held[gate]`=`SWBA=True conf=0.38 LC=True`
  ⇒ **critic 属实**；
- L2 批 `rd/` 中无任何 `_gate_` tag（`ls rd/ | grep 'L2_*gate'` = 0 命中）⇒ codec 主面板确无 gate 臂。

**处置**：**删除** tex §Codec Generalisation 新增的等价性句（含其 gate2 注记），恢复到改动前；
脚本/测试 docstring + 证据件 + RERUN_MAP + NARRATIVE §6 + NOTES + DECISIONS 全加**作用域边界**
（"只覆盖 ATE 表三臂，不覆盖 codec 面板"）。**未**硬辩——指控成立。

## 2. 【重大 M2】被 tex 引用的证据件头部结论与本轮立场相反 —— **销**

**critic 指控**：`batch_fingerprint_g2s1_2026-10-09.md:13-15` §0 仍写「可与主表同稿引用，
叙事按 cross-benchmark generalization」——而该叙事本轮已判**口径错**（`RERUN_MAP:27`），
且该证据件被 tex 引用（引证错宿主类）。

**独立复核（采纳）**：证据件 §0 原文确与 RERUN_MAP 的裁定相反（"同稿引用" vs "不入表"）。

**处置**：重写证据件 §0——改「**限 ATE 表口径**」+ 作用域边界段 + §5「held-out 不入表三理由」；
删除"可与主表同稿引用 / cross-benchmark generalization"表述。

## 3. 【次要 S1】包声明 HEAD 与实际不符 —— **说明，不处置**

critic 指包声明 HEAD=`f93101039`、实测 HEAD=`22a4bc702`（多 3 个非 tex/bib commit）。
**属实**（包写于审前，审查中我继续提交了收口 commit）；**不涉 tex/bib、不影响结论**。
登记即可。

## 4. 【次要 S2】RERUN_MAP 用 "ladder" 指 gate 臂、与 tex 组件阶梯易混 —— **销**

**处置**：RERUN_MAP §1 注中 "ladder 在 6 条里 4 条劣化" → 改 "**gate 臂**在 6 条里 4 条劣化"；
现 RERUN_MAP 全文 `ladder` 命中 = 0。

## 5. 已独立复核通过（非问题，采纳 critic 的通过项）
- 4 条新 bib 引证：Crossref 逐字段全对（Kerbl TOG 42(4):1-14 / MipNeRF360 CVPR'22 5460-5469 /
  TanksAndTemples TOG 36(4):1-13 / DeepBlending TOG 37(6):1-15），无张冠李戴；
- 27 keys 全被引、无孤儿无缺引（双向差集空）；
- held-out ATE 三理由成立（选择性样本 / gate 4-6 劣化 + base·gate 各 2/6 <5cm / tracking 属背景）；
- 红线：无禁语、无新数字、未动 tables/booktabs、style em-dash 2。

## 6. 门（整改后复跑）
```
pages=14  overfull=0  missing_char=0  undefined_ref=0
pytest tests/paper2_fulltable = 41 passed
paper2_batch_fingerprint.py --selfcheck = PASS（正控检出 + 两负控成立）
```
