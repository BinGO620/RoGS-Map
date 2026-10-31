# G2 审查报告 — paper2 figs/bib (2026-10-08)
包型：G2（论文数字/图入表前）
审查对象：commit b8c6d5418..38570140b, 分支 feat/e2-affordability-diag
(A) fig6 定性对比图 (B) fig1 架构图 (C) bib 回源+撤除伪造占位 (D) 图镜像守护测试

## 进行中

## 审查对象
- commit b8c6d5418..38570140b（HEAD=38570140b），分支 feat/e2-affordability-diag
- (A) fig6 贡献③定性对比图 + `scripts/dynport_offline/dump_repair_render.py`（新，170 行）
- (B) fig1 架构图第三框拆分（`scripts/02_analysis/paper2_figures.py:72-103`）
- (C) `papers/paper2/template_cvm/cvmbib.bib` 回源 + 撤 MetricsRef 占位
- (D) `tests/paper2_fulltable/test_paper2_figures_committed.py`（新，50 行）

## 机械事实
- pdfinfo /tmp/paper2_build/paper2_cvm.pdf = **Pages: 14**（= 上限），mtime 2026-10-08 23:57（晚于三 commit）
- log: **Overfull = 0**，无 "Citation undefined"/"There were undefined references"
- 图镜像测试：`/data/conda_envs/monogs-ours/bin/python -m pytest tests/paper2_fulltable/test_paper2_figures_committed.py -q` = **2 passed**
- 手核 9 生成图 `cmp -s` 全部 OK（results/*/figs ↔ papers/paper2/figs 逐字节一致）
- MetricsRef 在 papers/paper2/ 全仓 **0 命中**；`\cite{BonnDataset,TUMBenchmark}` 在 tex 出现（:577）
- 贡献栏仍 = "Our contributions are three"（tex:130）；22 个 cite key 全部有定义（0 undefined）

## 问题清单

### 致命
（无）

### 重大
- **[重大] M1 GGD-SLAM 被错标为"arXiv-only 无 venue"，实为 ICRA 2026 已录**
  证据：bib:56-62 `@misc{GGD, howpublished={arXiv preprint arXiv:2604.12837}}`，annote="逐字回源 2026-10-08：arXiv-only 预印本，无 venue"；commit 601b945af 声称"DGS-SLAM comments='Preprint, Under review' ⇒ **三者均** arXiv-only 无 venue"。**亲自回源**：arXiv API `id_list=2604.12837` → `<arxiv:comment>` = **"8 pages, Accepted by ICRA 2026"**；Crossref bibliographic 查询 GGD-SLAM → container = **"2026 IEEE International Conference on Robotics and Automation (ICRA)"**, 2026-06。⇒ venue 存在，条目应为 `@inproceedings{...,booktitle={ICRA},year={2026}}`。同一错误陈述已在 `NARRATIVE_v2_system_2026-10-05.md` §5 复述（"仍为 arXiv-only（无 venue）：DGSLAM/Dy3DGS/GGD"）。
  依据：P38（自报整改不实/引证须亲自核宿主）+ D20（"已点火/等价"类声称须可复跑工件）；根因 = 以单条（DGSLAM）comment 推广到三条（P34 单变量外推同型）。
  反驳通道：给出 arXiv 2604.12837 的 comments 字段不含 "Accepted by ICRA" 的当日截图/API 原文，或证明该 ICRA 记录与被引预印本非同一工作。
- **[重大] M2 BonnDataset 的 provenance DOI 指向另一篇论文（ALTRO）**
  证据：bib:197 annote="DOI **10.1109/IROS40897.2019.8967788**"。Crossref `/works/10.1109/IROS40897.2019.8967788` → title=**"ALTRO: A Fast Solver for Constrained Trajectory Optimization"**, page=**7674-7679**（非 ReFusion）。ReFusion 正确 DOI = **10.1109/iros40897.2019.8967590**（Crossref 查得 p.7855-7862，作者 Palazzolo/Behley/Lottes/Giguère/Stachniss，与 bib 标题/作者/页码一致）。⇒ title/author/pages/venue 均对，仅 provenance DOI 错（不渲染进参考文献表，但为回源留痕字段）。
  依据：P38（引证不实）+ D22（账目/provenance 单一事实源）。
  反驳通道：给出 DOI 8967788 解析到 ReFusion 的记录。

### 次要
- **[次要] m1 三条 @misc 的 author 用双花括号 `{{...}}`，整串作者被渲染成一个名字**
  证据：bib:49/57/65 author = `{{Li, Mingrui and Zhou, Yiming and ...}}`。PDF `/tmp/_p2.txt:2355-2357` ref[12] 渲染为单作者串 "Li, Mingrui and Zhou, Yiming and Zhou, Hongxing and Hu, Xinggang and Roemer, Florian and Wang, Hongyu and Osman, Ahmad. Dy3DGS-SLAM:..."（ref[13] 同）。本 commit 把这三条从 @inproceedings 改 @misc 但保留了双括号。（pre-existing，非本轮引入）
  依据：D16/排版正确性。
- **[次要] m2 `dump_repair_render.py` 死代码 + 文档与实现矛盾**
  证据：`_median_eval_frame`（:58-64）无任何调用点（`grep -rn _median_eval_frame scripts/` 仅定义处）；模块 docstring :12 写"每序列取该 run 评估帧清单的**中位帧**"，但实际用 `_quantile_frames`（:67）取 30%/70% 分位，图注亦写"30th and 70th percentiles"。文档口径与实现不符。
  依据：D15（临时/死代码清理）+ 图注诚实性一致性。
- **[次要] m3 账本状态滞后 + 本轮 4 commit 未登记**
  证据：`DECISIONS.md:114` D2-028 状态列仍写"编译 **13 页**"，本轮已 14 页；`grep fig6|fig1_pipeline|test_paper2_figures_committed DECISIONS.md` = 0 命中（b8c6d5418/5d5d5c6e0/601b945af/38570140b 无对应账本行）。
  依据：D22/P36（呈报入账本、单一事实源）。

## 逐项核销（任务书必查项）
1. 帧选择确定性 —— **通过（强）**。`_quantile_frames` 用 `judge.derive_eval_frames`（console.log 的 `Evaluating ATE at frame:` → 该 run 自带日程）；亲自复算：crowd2 n=35 → 索引 round(.30*34)=10, round(.70*34)=24 → **[271,621]**；balloon2 n=18 → round(.30*17)=5, round(.70*17)=12 → **[146,321]**。与 `fig6_dynport_repair_frames.json` **逐位一致**。无人工挑帧（手册帧仅在显式 `--frames` 时启用）。图注 tex:499-500 如实声明"30th and 70th percentiles ... not a selection of the best outcomes"。
2. 渲染口径 —— **通过**。`grep _load_arm_causal` 仅调用一处且 `snapshot_pose=False`（:87，samepose §12 v4）；R0 走 `_load_arm`（静态底图，:86）。与 §7 表注一致（tab_dynport.tex 明确"offline numbers ... read at the evaluated frame's own pose"）及各 gate2 注记。
3. bib —— **MetricsRef 已 0 命中 ✅**；BonnDataset/TUMBenchmark 已在 tex 引用 ✅；TUMBenchmark 全字段（573-580 / DOI / 作者）✅；DynaSLAM RA-L 3(4):4076-4083 ✅（Crossref 核）；DGSLAM arXiv comment="Preprint, Under review" ⇒ 无 venue ✅；Dy3DGS 无 comment/jref ⇒ 无 venue ✅；**GGD ❌（见 M1）**；BonnDataset DOI ❌（见 M2）。
4. 贡献数一致性 —— **通过**：tex:130 = three；9 个 `\includegraphics` 文件全部存在于 papers/paper2/figs（守护测试实测 2 passed）。
5. 页数 —— **通过**：pdfinfo = 14 页 = 上限；0 overfull；0 undefined ref。

## 无法验证清单
- 图内像素质量（是否真实呈现"抹除态缺人 / 修复态补回"）——只读文本无法看图，按任务书由 visual-judge 负责；本轮只核生成逻辑与图注。

## 审稿结论
**Accept-with-conditions**（无致命；2 重大 + 3 次要）。条件清单（被审方自行处置即可，不必再开一轮）：
- C1（M1）：GGD bib 改 `@inproceedings{booktitle={ICRA},year={2026}}`（或保留 @misc 但删除"无 venue"字样）；同步更正 NARRATIVE §5 "三者均 arXiv-only" 为"DGSLAM/Dy3DGS 无 venue，GGD=ICRA 2026"。
- C2（M2）：BonnDataset annote DOI 改为 10.1109/iros40897.2019.8967590（或删 DOI 字段）。
- C3（m1）：三条 @misc 作者去掉外层多余花括号。
- C4（m2/m3）：删 `_median_eval_frame` 死码并修正 docstring "中位帧"→"分位帧"；DECISIONS D2-028 页数 13→14 并补本轮 commit 行。
**同族同类连发**：本轮无 P38 类前一轮同族致命记录（上一轮 dynport G2 为 Accept-with-conditions 且未列 P38 类），不构成"两轮连发"。
