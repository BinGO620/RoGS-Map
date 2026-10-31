# L3 关卡① 独立对抗式审查报告（只读）
审查对象：results/lifecycle_paper2/evidence/verdict_L3.md（主）+ prereg_L3.md + prereg_L3_amendment_1_frameset.md + scripts/02_analysis/l3_paired_judge.py + configs/experiments/lifecycle_paper2/l3_mvnobox_exit.yaml
日期：2026-09-21
（增量追加中）

## 机械事实（已复算）
- 判据机复跑（本地）：输出与 verdict_L3.md 附录 A **逐字一致**（PASS=5/9、越门 ['crowd','person_tracking','person_tracking2','mvnobox']、Tier 同）。
- `--selftest`：mean Δ=-3.738、3/3 负、门槛 1.840、PASS=True；负对照（对调两臂）PASS=False，exit 0。
- render_L3_*_dense 目录 = 60，render_metrics.json = 60，n_frames 全 =17，skipped 全 0。
- l3_w0.done 30 条 `finished rc=0` / l3_w1.done 30 条 / 非零 0 条（共 60）。
- configs 目录 20 个 L3 config；exit vs off diff 仅 AlphaLifecycle 块 + save_dir。
- 臂间机制两态（efficiency_raw.csv）：off 全 9 序列 ×3 seed 的 steps/carve/reset 全 0；exit 全非 0。
  person_tracking carve=0 reset=417；balloon2 226；mvnobox 798；crowd3 408；person_tracking2 0 → §9 表值核实。
- §5.6 复算：crowd3 +2.089/+0.994/+0.917、crowd2 −2.674/−2.695/−2.381；crowd3 第850帧 freshvac_support_px=290、Δ=+30.21（占均值 85%）；crowd3 逐帧区间 [−15.6,+29.4]。
- 预注册澄清（"为负是判据的一部分"）git 核实属**跑前**：commit 1a52ee7e 2026-09-20 22:17 已含该段与 `mean_neg`（judge 脚本同一 commit）；pilot 首跑 09-20 22:54。该澄清**载荷性**（若仅"同号"，crowd3 3/3 全正会 PASS → 6/9 翻盘），但确为跑前钉死。

## 问题清单
### 致命
- 无。

### 重大
- **M1 §9 机制计数器的工件键错位**：verdict_L3.md:112 声明来源"逐 run `backend_timing.json`"，但 L3 run 目录内 `find … -name backend_timing.json` = **0**（该文件仅存在于旧 joint_correct/paper2_rollout run）；实测值在 `L3_*/tables/efficiency_raw.csv` 的 `alpha_carve_total` 等列。同一错误键亦在 prereg_L3_amendment_1_frameset.md:147 的绑定表。依据 P31/D10。整改：把 §9 与修正案 §6.0 的来源键改为 `tables/efficiency_raw.csv:<列>`。
- **M2 §9 逐-KF 诊断数值无本地工件可核**：verdict_L3.md:113,129-130,136 的 `geom_free=291`/`a_min=0.2445`/`a_lt_carve=0`/`a_lt_reset=151` 声明来自 consolelog，但仓库内 L3 **无任何 consolelog**（`results/lifecycle_paper2/*.consolelog` 仅 5 个，全为 L1）。字段名本身合法（utils/slam_backend.py:1057,1062-1064 实发 `a_min=/geom_free=/a_lt_reset=/a_lt_carve=`），但本轮无法核其值。依据 P4/P31。整改：把 60 份 L3 consolelog 入库（或给出远程路径+抽样区间），否则 §9 只能标"待核"。**远程未核**。
- **M3 渲染图 off 行标注符号与工件相反**：figs/L3_person_tracking_GT_off_exit.png 图注 "off (baseline) freshvac=-10.144cm"，而该帧（frame=248）实测 `L3_person_tracking_off_s0` freshvac = **+10.1439**（exit 行 +4.305 与实测一致）。且 fig 生成脚本**未在仓库中定位到**，无法复算 §4 声称的"取值帧=|Δ| 最大帧"（该帧对 s0 确为 248，但对 s1/s2 为 446/413）。依据 P31/D10。整改：给 fig 生成脚本并把图注对齐 `render_metrics.json`。

### 次要
- **m1 门槛 sd 口径未钉死**：l3_paired_judge.py:93 用 `statistics.stdev`（样本 sd, n−1）。预注册 §5.1 只写"off 臂 3 seed 的组内 sd"。改总体 sd 会使 crowd2 门槛=1.19（原 1.389）、ratio=2.25 ⇒ Tier1 而非 Tier2（附录 A §4）。不变 PASS/批级，但 Tier 表随口径漂移。建议在预注册钉死 sd 定义。
- **m2 PSNR 量纲护栏为区间启发式**：l3_paired_judge.py:132-135 仅判基值∈[8,60] dB。本批下确能拦住 freshvac(≈0–6) 与 ghost_excess(≈−7–7)，但同量纲的 `mean_depth_l1_cm`(24–55)、`mean_static_depth_l1_pen_cm`(14–21) 落在区间内 ⇒ 同类"喂错指标"仍会静默通过。建议改为显式键名/量纲断言。
- **m3 §5.1 护栏剔除数字无工件键**："off 0.711% / exit 0.614% / exit_fill 0.756%、max 0.231pt"（verdict_L3.md:60）未标源文件，本地亦无 l3_render.log（仅 l1_render.log）⇒ 不可核。依据 P31。
- **m4 §5.6 "8 条序列…完全不敏感"与其自身表格不符**：verdict_L3.md:76 称"完全不敏感"，但同节表 crowd +0.548→+0.486、crowd2 −2.674→−2.381 均随门槛变化。表述应改为"PASS/FAIL 结论不敏感"。该节为 09-21 事后追加（已披露，且未改判据，5/9 不变）。
- **m5 §9 对 person_tracking2 留白**：verdict_L3.md:124 `a_lt_carve`/`a_min` 为"—"，而 pt2 与 pt1 同属"人群族 carve=0"论据；缺失使"绑定 α 门"仅在 pt1 单 run 上有直接读数。建议补 pt2 同类诊断。
- **m6 失败分支处置与用户方向张力**：预注册 §5.2 失败分支字面 = "退回 box 族限定域写法（回 D2 重议）"，verdict_L3.md:84-94 记录用户 09-21 方向为"不主张收窄"。verdict 已声明"呈报用户拍板、系统不自裁"，无违规，但须在 D2 记录留痕，避免读作"按用户偏好改判据处置"（D18）。
- **m7 §9 因果外推证据不足（已标"设计输入"）**：EMA β=0.9 窗口"长期悬于阈值上"的解释（verdict_L3.md:139-140）无 β 敏感性/多序列核支撑，属机制推测；文中已限定为"D2 设计输入"、非结论，评级次要。

### 通过项（供反驳用，不构成免检）
- 判据未被事后换口径/换列/换门槛：逐序列判据与批级门在 judge 中一字对应 prereg §5；PSNR 门已真读 `static_psnr`（judge:153-154），修正不触及任何结论（PSNR 越门集 ⊂ ATE 越门集，批级门只依赖 ≥6/9 PASS 与 ATE）。
- 5/9 PASS + 批级未过确实落在 §5.2"逐序列如实写"支；§1 crowd3 行已内联"见 §5.6"，无"§5.6 削弱而 §1 仍作强结论"的残留。
- off 臂全计数器 0（9 序列 ×3 seed）为有效负对照；§9"α 门是绑定项"的逻辑成立（a_min=0.2445 > tau_carve=0.20 ⇒ a_lt_carve 恒 0，utils/alpha_lifecycle.py:257）。
- §2 约束门数字与判据机一致；§5.2-§5.5 混杂已披露；§8 已声明"关卡① 未送 ⇒ 数字不得进论文"。

## 无法验证清单
1. L3 逐 run consolelog（§9 逐-KF 诊断、§5.1 护栏剔除、§9 a_min/a_lt 值的唯一来源）——本地不存在，**远程未核**。
2. 运行时**合并 config 快照**：L3 run 目录仅 `tables/`，无 `datasets_*/seed_k/<时间戳>/config.yml`（旧 run 有）⇒ 无法逐位核对运行时 config 与声明 config（P2）。仅有 α 计数器两态（off 全 0 / exit 非 0）间接佐证臂差异生效。
3. fig 生成脚本位置（未定位）⇒ 图注与"|Δ|最大帧"规则不可复算。
4. 远程 3090 的 GPU/Xid 状态（verdict 称"批内 Xid 零新增"）——**远程未核**。

## 审稿结论
**Accept-with-conditions**。核心判决（批级未过、5/9 PASS、4/9 越门、逐序列如实写）由判据机**逐字复算通过**，未发现事后换口径/换列/换门槛；预注册澄清经 git 核实为**跑前**钉死，故不构成改判。阻塞性条件（须清）：M1 修正来源键、M2 补存/给出 L3 consolelog 以支撑 §9"工件级证据"、M3 修图注或给 fig 脚本。三者不改任何读数，但在澄清前 §9 与三件套 #3 不得作为"已核证据"引用。
