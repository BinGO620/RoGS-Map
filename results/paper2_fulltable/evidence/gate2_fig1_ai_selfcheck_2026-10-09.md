# G2 整改自核销 — fig1 AI 定稿落论文轮（2026-10-09）

- **审查**：slam-critic G2 判决档，报告 `/tmp/slam_critic_g2_fig1_ai_2026-10-09.md`，
  结论 **Accept-with-conditions（0 致命 / 3 重大 / 4 次要）**。
- **审查对象**：commit `a434c9c0d`（fig1 换 AI 定稿版 + 守护改造 + provenance）。
- **机器门（自跑）**：全量 pytest **586 passed**（fig1 守护 6 测）；编译
  `bash scripts/paper2_fulltable/build_paper2.sh` = **14 页（=上限）/ 0 overfull /
  0 missing char / 0 undefined ref**；health_check **0 FAIL（62 PASS/14 WARN）**；
  三方一致 `a434c9c0d`（本地 = origin = 3090）。

## 重大（3）全销

| # | 问题（critic 原文要旨） | 整改 | 状态 |
|---|---|---|---|
| M1 | PROVENANCE 称"迭代指令落在 images/ 会话记录"，images/ 实无记录文件；源图 sha 无落盘载体 | PROVENANCE.md 补：源图+备选版 sha256 真值（`974aaf20…`/`62fc46cd…`，sha256sum 实算）+ gen1→gen2_A 迭代指令全文落盘 | ✅ 销 |
| M2 | 几何/分辨率门只测 PNG，tex 实嵌 PDF，pdf 漂移无门 | 新增 `test_ai_fig1_pdf_mediabox`：MediaBox = 183×61mm±1pt + 3:1（实测 518.74×172.91pt 过） | ✅ 销 |
| M3 | 4 新文件处 `??` 态，`git add -u` 式提交会 clone 红 | 显式 `git add` 全部 10 路径后提交；`git status` 提交前回读全 `A/M`；clone 视角 = 远端已 pull 同步成功 | ✅ 销 |

## 次要（4）处置

| # | 问题 | 处置 |
|---|---|---|
| S1 | README 仍称 fig1"程序生成现状（参考/占位）" | 已改"AI 定稿版"+ 列 PROVENANCE/backup 结构树 ✅ |
| S2 | PROVENANCE "严格 3:1" 实为 3.00139 | 已改"3.00139:1，容 0.01 内视为 3:1" ✅ |
| S3 | evidence/figs/fig1_pipeline.* 死副本或被复现者误认图源 | results/ 只写不改（纪律 #3）；改在生成器 docstring 声明"evidence/figs 同名副本不再是论文图源"+ README 指向 PROVENANCE ✅（声明式） |
| S4 | gen2_B 回切锚在 gitignored 文件 | PROVENANCE 注明"git 不保、须从 images/ 取或重生成" + sha256 指纹 ✅ |

## critic 建议不采纳项（留痕）

- **sweep_citation_claims 注册 PROVENANCE 声称**：机制化建议有价值，但 sweep 门目前
  只挂论文正文声称（DECISIONS D2-028 语义），PROVENANCE 是图工件侧记录、已有独立
  镜像+几何门守护；本轮不扩 sweep 语义（扩了反而稀释该门的指向性）。后续若
  PROVENANCE 声称进入正文再挂。
