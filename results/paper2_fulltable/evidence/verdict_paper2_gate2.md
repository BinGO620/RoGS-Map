# 裁决：论文 2「数字/骨架包」关卡② 第 1 次审查 —— **Reject → 已整改**（2026-09-19）

> **账本补登（2026-09-25，D2-015 追溯登记）**：本件成文于决策账本设立（2026-09-20）之前，无当期账本号；统一追溯登记见 `DECISIONS.md` **D2-015**。

> **关卡② 状态：第 1 次审查 = Reject（3 致命 / 9 重大 / 若干次要）⇒ 逐条处理后**，
> 本包仍是**待审生成物**：`evidence/latex/README.md` 的门禁（"不得 `\input` 进论文"）
> **保持有效**，直到其列出的未关闭项（主表主张 scope）由用户/写作会话决定后复审。
> 审查者 = `slam-critic`（独立会话）；全量报告
> `results/paper2_fulltable/evidence/slam_critic_report_paper2_gate2.md`。
> **性质**：判定 + 生成器修 bug + 重生成（**零新实验、零 GPU**；生成器确定性 ⇒ 重生成可复现）。

## 1. 三条致命项与我核实后的处置

| # | 审查者主张 | 我独立复核 | 处置 |
|---|---|---|---|
| 1 | **Tab.4 的 FPS 列是错数**：`round(median(fps))` 取整到 0，下游 `if fps_med` 真值过滤又把 0 当缺失剔除（审查者报真值 0.32–0.50） | **成立，且是生成器真 bug**。复核：修前产出的 `fps_med` 在工件里就是 `[0,0,0,1,0,0,0]`（baseline）与全 0（其余三臂）⇒ 表里只剩 `1.000` 与 `--` | **改代码**：`round(...,3)` + 两处过滤改 `is not None`（MD 与 LaTeX 两条路径）；**重生成**后真值 **0.456 / 0.354 / 0.354 / 0.415**。新增回归用例 |
| 2 | **Tab.3s 同表混用两种静态协议**（运行期 P-A 4 序列 + 离线 `seg_mask` 3 序列），而包 README 称"两源不混算"；LaTeX 版比 Markdown 版**少一列**（丢 `mask source`） | **成立**。复核 `tables_paper2_preview.json`：balloon/balloon2/pt/pt2 = `runtime_pa:dynamic_mask_gtmc`，crowd/crowd2/crowd3 = `seg_mask` | LaTeX 版**恢复 `mask source` 列**（下划线已转义）＋表注声明"跨序列慎比"；README 表述改为准确的"逐序列源"；新增回归用例。注：`NARRATIVE.md` 的 Tab.3s 行**原本就写了**"运行期 P-A + 离线 seg_mask"——是 latex README 的措辞不准确 |
| 3 | **主表与验收红线冲突而本包零披露**：`gate` 在 3/7 序列劣于 `baseline`，过 5cm 线集合与 baseline 相同（净贡献零），pt1 头条降幅 p=0.30 | **成立，且比审查者更严重**：按 `ate_mean` 逐序列比，**劣化为 5/7**（balloon +30.1% / crowd3 +19.4% / pt2 +12.2% / crowd2 +10.6% / crowd +3.8%），过 5cm 线集合确实与 baseline **完全相同**（balloon, crowd, crowd2, crowd3） | **不在本包改写论文主张**（那是 scoping 决定）。已在包 README 与 `NARRATIVE.md` §5.3 加**显式警告**并新增披露回归用例；**升级为须用户决定的事项** |

## 2. 重大项处置（摘）

- **Tab.3s 的 `coverage` 恒 1.000**（项目已登记无判别力）⇒ 表注声明 `non-discriminative`，并加断言把"恒 1.000"这一事实钉住。
- **Tab.2r 图注断言"没有臂弄坏静态场景"是假的**（gate 静态 PSNR **5/7 序列**低于 baseline）⇒ 图注改为只声明全图口径 + 指向 Tab.3s，并给出实测最大跨臂全图差 **≤0.38 dB**（旧文写 0.6 dB 是我先写的，已按工件收紧）。
- **Sim(3) 撤回未传播**：`tab2_pt_seed.tex` 图注原仍在陈述被撤回的主张（"Scale is the dominant error component"）⇒ 改为**显式撤回警告**；`NARRATIVE.md` 三处 Sim3 引用（表→数据源、§5.1、§6）加撤回标记，并把 Tab.2 的数据源从历史件 `j1_screen_summary.csv` 改为最新生成器输出。
- **无测试校验已提交的 `.tex`** ⇒ 新增 `tests/paper2_fulltable/test_paper2_latex_committed.py`（7 项）。

## 3. 我**不采纳**审查者结论的地方（留痕）

1. **重大 9 的归因错**：审查者认为我的成本列"轮 I 7.08% vs 轮 III 36.34% 是分母从 55.2k 变 10.8k"。
   实测**分母完全相同**（`meta.n_static`：gate 55,174 / baseline 84,162，轮 I/II/III 逐位一致）；
   真因是**各轮成本判据测的是各轮自己的主臂**（轮 I `C4` 用 P2cv、轮 II `D5` 用 P2cr、轮 III `E5` 用 P2cuv）。
   **但审查者指出的"我的成本列口径错"成立**（我把轮 III 主臂的 36.3% 标到了 P2c 行）⇒ 已改为
   **逐行按该臂自身 `n_dyn / n_static`** 计算并声明分母。
2. **重大 5 的表述**：审查者说"Tab.2r 表注与 Tab.3s 矛盾"成立；但它把 tab2r 描述为"自身是全图口径"这一半我已确认无误，故只改图注不改表。
3. **次要 14**（"离线 6 帧"实为 8 帧）与 **次要 13**（ghost_excess 负值语义）：**接受**，已在包 README 标注为待澄清项，不改数字（负值语义须由 `render_compare` 的口径定义方确认，属另一条线）。

## 4. 未关闭项（须用户/写作会话决定，本包不代决）

1. **主表主张 scope**（致命 3）：`gate` 相对 `baseline` 在 5/7 序列劣化、过 5cm 线集合相同。
   这直接关系论文 2 的 headline 能不能写"降低 ATE"。**必须由用户定调**。
2. **静态/渲染面"不退化"卖点**：工件上不成立（5/7 序列静态 PSNR 下降，幅度 −0.03 ~ −0.20 dB）。
   候选改写：只声明"全图渲染跨臂差异 ≤0.38 dB"，静态区逐序列并陈。
3. 本包的门禁**保持"不得 `\input`"**，直到 1/2 决定后做一次复审。
