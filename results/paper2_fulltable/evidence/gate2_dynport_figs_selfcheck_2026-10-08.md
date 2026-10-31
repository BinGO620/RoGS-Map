# 关卡② G2 自核销 — paper2 figs/bib 轮（2026-10-08）

> **账本**：D2-028（贡献③ 落地）的配套关卡②。**包型** = G2（论文数字/图入表前）。
> **审查对象**：commit `b8c6d5418`..`38570140b`（fig6 图/生成器、fig1 架构图、cvmbib.bib 回源、图镜像守护测试）。
> **全量报告** = `gate2_dynport_figs_report_2026-10-08.md`（slam-critic 产出，逐字）。
> **结论** = **Accept-with-conditions**（无致命；2 重大 + 3 次要）。

## 条件逐条处置（全部由主会话**自行复核** slam-critic 结论后采纳——P38 纪律：不采信转述，逐条亲核）

| # | 级别 | 问题 | 亲核证据 | 处置 |
|---|---|---|---|---|
| M1 | 重大（P38 自报不实 + P34 同型） | GGD-SLAM 被错标"arXiv-only 无 venue"，实为 **ICRA 2026 已录** | `arxiv.org/abs/2604.12837` comments = **"8 pages, Accepted by ICRA 2026"**（WebFetch 亲核）+ ICRA 2026 program **ThI1I.98**（tavily 命中 ras.papercept.net） | ✅ 改 `@inproceedings{GGD, booktitle=ICRA 2026}`；NARRATIVE §5 同步（GGD 移出"arXiv-only"）；根因 = 以 DGSLAM 单条推广到三条 |
| M2 | 重大（P38 引证错宿主） | BonnDataset 的 DOI `...8967788` 指向**另一篇论文** | Crossref `10.1109/iros40897.2019.8967788` = **"ALTRO: A Fast Solver..." p.7674-7679**（亲核）；ReFusion 正确 = `...8967590` p.7855-7862（Crossref 亲核） | ✅ 改 DOI `...8967590`；编译后 PDF `grep -c ALTRO` = **0** |
| m1 | 次要（排版） | 三 @misc author 双花括号 `{{...}}` ⇒ 作者串渲染成一个名字 | `grep '{{' cvmbib.bib` 亲核命中 DGSLAM/Dy3DGS/GGD | ✅ 去双括号（GGD 转 @inproceedings，余二条 `author={...}`） |
| m2 | 次要（D15 死码） | `dump_repair_render.py` 死码 `_median_eval_frame` + docstring "中位帧"与实现/图注 30%/70% 分位矛盾 | 亲读脚本 | ✅ 删死码；docstring 改"30%/70% 分位帧" |
| m3 | 次要（D22/P36 账目） | D2-028 状态列写"13 页"（实 14）；本轮 commit 未登记 | 亲读 `DECISIONS.md:114` | ✅ 见本文件同批的账本更新 |

## 必查项逐条核销（slam-critic 自跑，主会话复核）

1. **帧选择确定性** ✅：crowd2 n=35→[271,621]、balloon2 n=18→[146,321]，与 `fig6_dynport_repair_frames.json` 逐位一致；重跑脚本产同帧（确定性已实测）；图注 tex 如实写"30th/70th percentiles, not selection of best outcomes"。
2. **渲染口径** ✅：`grep _load_arm_causal` 仅一处且 `snapshot_pose=False`（samepose §12 v4）；R0 走 `_load_arm`（静态底图）——与 §7 表注一致。
3. **bib 真实性** ✅（修后）：MetricsRef 0 命中；TUMBenchmark 全字段核（573-580/作者/DOI 10.1109/IROS.2012.6385773）；DynaSLAM RA-L 3(4):4076-4083；DGSLAM comment="Preprint, Under review"⇒无 venue；Dy3DGS 无 comment⇒无 venue；**GGD→ICRA 2026**（M1 修）；**BonnDataset DOI 更正如上**（M2 修）。
4. **贡献数一致性** ✅：tex `Our contributions are three`；9 个 `\includegraphics` 全存在（`test_paper2_figures_committed.py` 覆盖）。
5. **页数** ✅：`pdfinfo /tmp/paper2_build/paper2_cvm.pdf` = **Pages 14**（=上限）；Overfull=0；0 undefined ref。
6. **图镜像守护** ✅：`test_paper2_figures_committed.py` = 2 passed（负对照：注入 1 字节漂移变红，已实测）。

## 无法验证（如实登记）

- **图内像素质量**（"抹除缺人 / 修复补回"是否真实）：slam-critic 只读文本无法看图 ⇒ 归 visual-judge。
  **本会话处置**：visual-judge 子代理**启动失败**（account-connection-unavailable）⇒ 按交接指示由**主会话自审**：
  fig6 三列关系正确（GT 有人 → Erased 缺人留残影 → Repaired 补回）；inset 可读；4 行标签清晰；
  fig1 五框 + 两 dashed"this paper"offline 框 + 箭头方向正确。**已目视通过**（非独立审查，如实标注）。

## 结论

**Accept-with-conditions，全部条件已核销** ⇒ 本轮 figs/bib 产物可入表/提交。
