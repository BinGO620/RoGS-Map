# G2 verdict 审查报告 — B 线反动态代价探针跨序列扩展 5 序列
审查对象: papers/paper2/paper2_cvm.tex §5.3 新段 + results/paper2_fulltable/evidence/{verdict_dyn_cost_5seq_2026-10-05.md, dyn_cost_5seq_2026-10-05.md/json, dyn_cost_decomp_2026-10-05.md}
HEAD: 0d06dc8cf
包型: G2 verdict（论文数字入表前读数审查）

## 机械事实
- HEAD 0d06dc8cf；工作区干净。prereg commit f724713be=17:02:03；冒烟启动 17:11:02；批 done 17:27:36。**先锁顺序成立**（prereg<smoke<batch）。
- 逐位复算 10 行（5 份 dyn_probe_5seq_*_results.json × 2 臂）**全部与 verdict/dyn_cost_5seq 表一致**（见下"复算"）。
- 5seq 掩码 = `dynamic_mask`（canonical），config `mask_subdir: auto`；canonical 目录 5 序列实有（928/895/848/470/581 帧）。
- 程序化门：pytest tests/paper2_fulltable 31 passed（任务书陈述，未复核）；本批无新单测。

## 复算核对（10 行，全部一致）
seq/arm: PSNR增益 / dl1比 / staticΔ / fullΔ / 仪器比 —— 与 verdict §2 主表逐位相符。
crowd/base +22.22/0.185/+0.29/+12.01/4.83；crowd/gate +22.22/0.187/+0.20/+11.91/4.81；
crowd2/base +21.55/0.179/+0.04/+10.61/5.25；crowd2/gate +21.54/0.176/-0.03/+11.04/5.37；
crowd3/base +21.00/0.187/+0.39/+10.43/4.68；crowd3/gate +21.31/0.182/+0.34/+10.26/4.81；
balloon2/base +17.92/0.162/+0.33/+5.39/5.04；balloon2/gate +18.79/0.153/+0.24/+6.31/5.39；
pt/base +19.51/0.269/+0.28/+8.70/3.41；pt/gate +18.12/0.238/+0.22/+8.41/3.75。
①b 10/10 过（比值 0.16–0.27≪0.70、增益+18~22≫+2.0）✓；⑤ 10/10 过（3.41–5.39）✓。
正文数字全对：动态区 18–22dB、深度比 15–27%、全图 5.4–12.0dB、拥挤度排序 crowd>pt>balloon2（同集与全图同序）✓。

## 问题清单

### 重大
- **[重大] ③"无伤"判定计数错误（verdict 自相矛盾：§0 写 4/10、§2 写 6/10，实际 5/10）**
  证据：脚本 judge_noharm 复算 = 5 过 / 5 超界（crowd/base 0.287、crowd3/base 0.3884、crowd3/gate 0.3408、balloon2/base 0.3327、pt/base 0.2805，阈值 0.25）。verdict_dyn_cost_5seq:11 写"4/10 行严格超界"、:36 写"6/10 行过"，而其括号内列举整整 **5** 条。同一文书内 4/6/5 三个数互斥。
  依据：D9/D19（判据机械应用）、P23（判据计数须锚定）、P31（计数与事实相反）。
  反驳通道：给出一条 |Δstatic|≤0.25 而脚本判 false 的行，或证明某行 staticΔ 定义不同。

- **[重大] 正文成本宣称 "adds a few percent of primitives" 与所引工件矛盾（实为 6.2–28.6%，median 22.2%）**
  证据：paper2_cvm.tex:476-477 "adds a few percent of primitives to the map"；dyn_cost_5seq_2026-10-05.json rows 复算 n_dyn/n_static = 6.2%（pt/gate）… 22.2%（median）… 28.6%（crowd2/gate）；crowd 族 21.8–28.6%。verdict:40 亦自述"个位数~十余%"，同样低估。
  依据：P1/D19（口径）、D20（数字须与工件一致）。prereg §3⑥④ 中的 ④（mean_n_dyn≤50%×n_static）**未机械施加**：probe_5seq_verdict.py:40 取 `P1["mean_n_dyn_static"]` 键不存在 ⇒ cost=None，脚本只判 ①b/③/⑤。
  反驳通道：给出"a few percent"所指的具体分母（若为 n_dyn/(n_static+n_dyn) 仍为 18%；无法得到个位数）。

- **[重大] 第二段（几何/外观拆解）头条数字 0.59–0.72 / ~0.22 源自 2026-09-19 旧批 **gtmc 掩码**，正文未声明来源批与掩码口径**
  证据：dyn_cost_decomp_2026-10-05.md/json ← dyn_probe_verdict.json（mtime 2026-09-19 10:12）的 causal_judgments / balloon_generality，其 mask_source = `dynamic_mask_gtmc`（dyn_probe_causal_results.json meta 确认；probe_pt2_causal.yaml / probe_balloon_generality.yaml `mask_subdir: dynamic_mask_gtmc`，已标 DEAD CONFIG）。NOTES.md 记载 gtmc 移动者召回 0.10–0.39、并集 51–96% 静态 FP，目录已按 D1-006 删除。**同口径 canonical 复算 5seq P2c retention = 0.80–0.93（比引用值高）** ⇒ 结论方向仍成立，但入稿的具体数字来自已判废掩码且未声明。
  依据：P9（GTMC 冻结掩码破损）、D20/D10（工件 provenance）、D21（口径跨源移植）、NOTES「掩码体系重构 v2」。
  反驳通道：给出 canonical 掩码下 pt2/balloon 的 retention 复算，或声明该段"沿用旧批 gtmc、仅定性"。

- **[重大] prereg §3 判据 ⑥ 阳性对照 本批未执行/未报告**
  证据：prereg:58 列 ⑥（P1 全图 PSNR vs render_compare，max|Δ|≤0.01dB）；probe_5seq_batch.log 对 positive/render_compare/control 命中 **0**；唯一工件 control_p1_vs_render_compare.json mtime=2026-09-19（pt2 旧件）。verdict §"判据机械应用"静默省略 ⑥（及 ④）。
  依据：D9（判据机械应用）、prereg §3、P17（rc=0≠组件生效）。
  反驳通道：提供本批 5seq 的 ⑥ 工件，或声明以旧件外推且给出适用性论证（P1 全图 PSNR 与掩码无关，或可成立——但须写明）。

### 次要
- **[次要] 批时段与 prereg 时刻陈述不准**：verdict:16 "批 17:02–17:27（25 min）"；批日志实为 start 17:11:02 / done 17:27:36（≈16 min）。verdict/prereg 称 prereg "17:00 提交"，git 提交时间 17:02:03（先锁顺序成立，仅时刻不精确）。依据 P4/P5（收尾锚定）。
- **[次要] 新工件无单测覆盖**：tests/ 无 dyn_cost_5seq / probe_5seq / dyn_cost_decomp 引用（D1/D22 建议补结构+数字逐位门）。
- **[次要] decomp 的 P2cv(~0.22) 仅来自 pt2 单序列**（balloon P2cv=null），正文 "about 0.22" 单序列支撑偏薄；建议声明仅 pt2 有该臂。
- **[次要] probe_5seq_batch.log 存在重复块**（行 1–14 的 SMOKE/DECISION/RUN 头在行 191–193 再现），疑 tee/追加所致，不影响读数。

## 无法验证清单
- 本地==origin==远程 HEAD 同步（任务书禁 ssh，未核）。
- health_check 本轮输出（任务未给；门控/同步类不适用本包）。
- ⑥ 阳性对照本批缺件（见重大项）。
- pytest 31 passed 为任务书陈述，未在本机复跑（无 pytest 环境；按 §2 不代跑）。

## 审稿结论
**Accept-with-conditions**（无致命；4 重大 + 4 次要，均可在执行前以补证/改措辞/补跑处置）。
- 最需先处置：③ 计数订正（5/10）、正文成本词改实（6–29%，median 22%）、第二段数字的来源批/掩码口径声明、⑥ 补跑或声明外推。
- 同族同类连发：本轮未发现（③ 计数与 P23 同源但为首次在本族出现，须入类登记表）。
