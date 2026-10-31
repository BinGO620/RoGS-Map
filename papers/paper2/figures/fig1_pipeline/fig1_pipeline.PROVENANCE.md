# fig1_pipeline 定稿 provenance（2026-10-09；当晚二次改版；2026-10-12 架构图候选）

## 2026-10-12 追加：纯架构示意图候选（生图 MCP，待用户核文字）

**背景**：用户 2026-10-12 要求"架构图用生图 MCP 生成"。当前 `fig1_pipeline.{pdf,png}`
（程序拼合真实数据总览图）**含真实实验工件**（mask overlay / 真实 PLY 俯视 / 真实渲染），
按红线**不能**用生成模型。故本轮另出**纯架构示意图**候选（无数据，可生图），三版：

| 候选 | 文件 | 程序化属性 |
|---|---|---|
| gen1 | `fig1_arch_gen1.png`（1536×1024） | 白底 84%，朱红强调色 0.07% |
| gen2 | `fig1_arch_gen2.png`（1536×1024） | 白底 85%，朱红强调色 0.34%（最明显） |
| gen3 | `fig1_arch_gen3.png`（1536×1024） | 白底 81%，朱红强调色 0.11% |

**⚠ 待人工核对（主会话硬约束，无法自证）**：当前会话模型**不支持图像输入** +
visual-judge 子代理账号不可用 ⇒ 主会话**无法逐字核对生图文字标签**。生图模型最易错处
正是文字拼写/框数/箭头方向。**请用户逐字核对 7 个标签**：
`RGB-D frames` / `tracking (pose vs map)` / `dynamic weighting` /
`3DGS map (grown online)` / `rasterised render` / `offline map codec (this paper)` /
`offline dynamic repair (this paper)`。

**备选（文字 100% 可控）**：程序版纯框图 `fig1_pipeline_programmatic_backup.{pdf,png}`
（5 框 + 2 离线框，矢量，文字逐字正确、与其余 8 图风格统一）——若生图文字核对不过，
直接用它作架构示意图，零风险。

---

# fig1_pipeline 定稿 provenance（2026-10-09；当晚二次改版）

- **现行定稿（v2，2026-10-09 晚）**：**程序拼合真实数据总览图**（matplotlib，
  `scripts/02_analysis/paper2_fig1_overview.py`，数字全部机写自 rd/samepose JSON）——
  用户参照竞品 Fig.1（带真实输入缩略图 + 中间量可视化 + 真实输出）重定方向；
  AI 文生图版退役（v1 说明保留于本文件末尾）。
- **真实工件来源（全部已落盘工件，未重演实验）**：
  - **可复跑命令（两步，本机 2060 亚秒级）**：
    `python scripts/02_analysis/paper2_fig1_export_assets.py`（导出 /tmp/fig1_assets/*.npy）→
    `python scripts/02_analysis/paper2_fig1_overview.py`（重出 fig1_pipeline.pdf/png）。
  - 上带（crowd2 f621）：input GT 帧 / run 内 canonical 掩码 overlay（与数据集
    dynamic_mask IoU=1.0000）/ 地图 PLY 俯视散点 / 在线渲染 = judge_dynport 加载器现渲
    （R0 run = r33_rebase_baseline_crowd2_seed0）；
  - 下带 codec：`results/gs_compress/render/{L1_crowd2_baseline,L1_crowd2_b16-8-8-8-8}/cmp_f00240.png`
    右半（未压缩 vs 重建）；比率 = 42 份 `evidence/rd/L2_*_b16-8-8-8-8.json` 的
    ratio_full 均值（**机写 6.0×**）；
  - 下带 repair：`results/dynport_offline/L1_v4/crowd2_R1` samepose 渲染（erased vs repaired）；
    增益 = 三序列 `evidence_v4/dynport_offline_L1_*_samepose.json` 的
    J1_samepose_bad_psnr_delta.median 均值（**机写 +6.8 dB**）。
- **QA**：nature-figure `audit_figure_collisions` PASS / `audit_pdf_text`（最小 7.6pt）PASS；
  tex 缩放 0.80\linewidth 后有效最小字号 ≥6.2pt。
---

## 以下为 v1（AI 文生图版）记录 —— **已于 2026-10-09 晚退役**，图源不再是本文件上半所述定稿

- v1 = AI 文生图（gpt-image-2，OpenAI 兼容端点），版本 = gen2_A 分区底带版（提示词迭代第 3 轮）。
- **源图指纹（定稿输入，原图在 gitignored images/，以此指纹 + 下列迭代指令为载体）**：
  `fig1_pipeline_gen2_A_crop.png` sha256 = `974aaf20d68a2e6d2c4f633d82ab8efe8ee494183ca8da015d56eb8d861763a2`（2061×687）。
- **制版**：PIL LANCZOS 升采样 2061×687 → 2161×720（= 300 dpi @183 mm，宽高比 3.00139:1，
  容 0.01 内视为 3:1），matplotlib 封装为 183 mm × 61 mm 单页 PDF（`fig1_pipeline.pdf`，
  96a92462369adc…）。PNG 同源（585fb6be03eaa2…）。
- **选版**：gen2_A（推荐）与 gen2_B（泳道极简，`images/fig1_pipeline_gen2_B_crop.png`）二选一；
  取 A。B 版可随时一键回切（工作区只换文件名重镜像 + commit）。
- **人工核验（2026-10-09，主会话逐字放大核对）**：7 个框标签 + 2 条底带标题全部逐字正确；
  4 实线箭头左→右；2 虚线箭头均从 box4（3DGS map）底边引出（优于现行程序版——其第二
  虚线箭头视觉上从 render 框下方引出）；色盲安全（蓝/橙 Okabe-Ito 族）；无标题无水印。
- **科研诚信**：本图为**概念示意图**（无实验数据），是 9 张图中唯一允许文生图的一张
  （红线判据表 `papers/paper2/figures/README.md`）。其余 8 张实验数据/渲染照片图未用 AI。
- **提示词**：`fig1_pipeline.prompt.txt`（基础 prompt）。**迭代指令（gen1→gen2_A，会话内下
  达，落盘于此防 provenance 断链）**：
  1. gen1→gen2 轮：「整体重画。不要朴素横向流程图；改为两个横向分区带：上带 = 在线 SLAM
     环路（5 个主框+实线箭头），下带 = 离线地图侧处理（2 个虚线框）；上带标题
     ONLINE SLAM LOOP - PRIOR STACK，下带标题 OFFLINE MAP-SIDE PROCESSING - THIS PAPER；
     每个框加扁平小图标；虚线箭头严格从 3DGS map 框底边引出、指向下带两框顶边」。
  2. gen2_A→crop：内容 bbox 裁切（去掉四周大片留白）+ 补白归一到 3:1。
  3. 选版：gen2_A（分区底带版，胜出）vs gen2_B（泳道极简风）——取 A。
- **回退锚点**：程序版留档 `fig1_pipeline_programmatic_backup.{pdf,png}`
  （生成器 `scripts/02_analysis/paper2_figures.py::fig_pipeline`）。备选版 gen2_B 在
  gitignored images/（sha256 = `62fc46cd2409731587dd19814c2b7deb9af1c99090be8521cfdb9962a7bdc68e`，
  若需回切须从该目录取或重生成——git 不保）。
- **守护**：`tests/paper2_fulltable/test_paper2_figures_committed.py`——
  fig1 已从生成器镜像对摘出，改为「figures/ 工作区 ↔ figs/ 提交副本」逐字节镜像 +
  程序版留档存在门（阴性对照已实测：篡改 1 字节即红）。
