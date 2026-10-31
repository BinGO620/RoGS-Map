# Slam-Critic 审查报告：embrace_dyn 跨序列泛化复现（balloon）裁决草稿（关卡①）
日期：2026-09-18  角色：只读对抗式审查者
对象：results/embrace_dyn/evidence/verdict_dyn_probe_generality.md（工作区未提交）

## 审查对象
- 裁决草稿（待落地，未提交）：`results/embrace_dyn/evidence/verdict_dyn_probe_generality.md`（69 行，工作区 untracked）
- 预注册/配置：`prereg_dyn_probe_balloon.md`、`configs/experiments/embrace_dyn/probe_balloon_generality.yaml`
- 判据机输出：`dyn_probe_report.md` §「跨序列泛化复现」（191-205）、`dyn_probe_verdict.json:balloon_generality`
- 原始读数：`dyn_probe_balloon_results.json`（untracked）；选帧工件 `frame_coverage_balloon.json`
- 自称测量代码：`6e6e8a79`（实测 `git show --stat` 仅 3 文件：prereg/config/frame_coverage，561 行）
- 参照：`verdict_dyn_probe.md`（母批）、`verdict_dyn_probe_causal.md`（因果轮 I）

## 机械事实（已核）
1. 选帧工件与预注册一致（已验证）：`frame_coverage_balloon.json` n_candidates=202、median_nonzero_coverage=0.036367、selected=16、t0=297 cov=0.237，与 prereg L15-16 逐字相符。
2. 复算通过（本审查器独立复算，与判据机逐位一致）：以 `dyn_probe_balloon_results.json` 逐帧值按 (P1−Pc)/(P1−P2) 复算 P2c 保留率，dt≥1 子集 n=13 ⇒ gate dl1 **0.6658**/psnr **0.1443**、baseline **0.6871**/**0.1612**，与 `balloon_generality.excl_dt0` 完全一致 ⇒ 判据机 dt=0 敏感性算术无误。
3. 补充稳健性（本审查器新增，判据机未做）：剔除 dt∈{0,1}（n=10）⇒ gate dl1 **0.6738**/psnr 0.1494、baseline **0.6937**/0.1761。相对 dt=0 剔除口径变化 ≤0.008（dl1）/0.015（psnr）⇒ **dt=1 帧不解偏**，草案"只剔 dt=0"的处理在数值上足够。
4. 地图 provenance：两序列地图同属 R33 rebase **2026-09-16** 批（balloon gate 02:45:13 / baseline 01:37:09；pt2 gate 14:47:45 / baseline 13:23:00），P25 型跨版本混淆风险低（未逐臂 `git log -- utils/swba.py` 核实，见未验证项）。
5. pt2 侧的 dt=0 帧数 = **0**（`dyn_probe_causal_results.json` 的 P2c dt_eval ∈{1,2,3,4}），balloon 侧 = 2（125/320）。两侧 dt=1 帧数均为 3/15 ⇒ 草案把 balloon 的 dt=0 剔除后与 pt2 原值比，方向公平，但草案未声明"pt2 无 dt=0"。
6. pt2 参照值来源已核：`+10.73 dB` = `dyn_probe_report.md:18` 的 `1b_ceiling_bad_subset.psnr_gain_db 10.7305`；`0.565/0.555` = 母批 M_bad 比值；`−0.53/−0.63 dB` = `verdict_dyn_probe_causal.md:53`（C3）。**但** `0.590/0.583` 是**全掩码**口径（同文件 :50/:51 明确 M_bad 口径 = 0.594/0.607）。
7. 气球判据机输出（`balloon_generality._judgments`）两地图 1b/3/4/5/6 全 pass；`desc_P4_vs_P1`（gate dl1 0.928、psnr −1.08、d_static −3.97；baseline 0.862、−1.60、−4.32）；`desc_dyn_cov.all_arms_value=1.0`（无判别力）。**报告 191-205 与裁决书正文均未出现这三项**。

## 问题清单

### 致命
- **[致命] 自称的测量代码提交 `6e6e8a79` 不含本轮任何测量代码；产生 §2 全部数字的判据机改动仍在工作区未提交 ⇒ 判决不可复算**
  证据：`git show --stat 6e6e8a79` 仅 `probe_balloon_generality.yaml`+`frame_coverage_balloon.json`+`prereg_dyn_probe_balloon.md`（3 文件 561 行，无 `scripts/`）；`git status` 显示 ` M scripts/02_analysis/analyze_dyn_probe.py`，`git diff --stat` = +102 行，含 `cross_sequence_row`（analyze_dyn_probe.py:354-397）、`retention_of`（:335-352）、dt=0 敏感性（:381-395）；`git show HEAD:scripts/02_analysis/analyze_dyn_probe.py | grep cross_sequence_row/retention_of` **零命中**。裁决书 L7 与 `manifest.json` 的 `rounds.round_4_generality_balloon.measurement_code_commit = 6e6e8a79` 均把它标为测量代码提交。
  依据：NOTES.md:431-436（"测量代码未提交就跑批 ⇒ 判决不可复算（关卡① 致命项）"；规则②"裁决书/manifest 里的 HEAD 字段必须指向**包含测量代码的那个提交**"）；DISCIPLINE #12③ 可追溯（L67-68）与 L348。
  反驳通道：提交 `analyze_dyn_probe.py` 并给出含测量代码的 sha、同步更新 verdict L7 与 manifest 该字段；或证明该 102 行 diff 不参与任何已报数字。注：探针 `dyn_probe.py` 侧已在库（HEAD 含 P2c/dt_eval，:386-390/:963），故仅判据机侧不可复算。

### 重大
- **[重大] 口径混引（pt2 保留率用了全掩码口径，却标 M_bad）**
  证据：草案 L29 表头"M_bad 口径"，L33/L47 填 pt2 `0.590/0.583`；而 `verdict_dyn_probe_causal.md:50` 明确"**C1b 因果保留率（补遗主判据，M_bad 子集）= 0.594/0.607**"，`:51` "C1（**全掩码口径**，参考）P2c 0.590/0.583"；`:77` 亦为 0.594/0.607。balloon 侧用的是 M_bad 口径（0.696/0.719 与 excl 0.666/0.687）。
  依据：DISCIPLINE #12①（L59-60"不同口径不得混引"）+ L348；P1/P24/P29（跨口径混引家族，本项目已发生 3 次）；该口径错误正是 pt2 因果轮整改表第 4 条处理过的同类问题。
  反驳通道：给出 pt2 M_bad 口径保留率并改表（应作 0.594/0.607），或证明 0.590/0.583 亦为 M_bad 口径（需贴判据机对应行）。
- **[重大] 帧数口径自相矛盾：表 15 帧 / 正文 16 帧 / 预注册锁 16 帧，被剔除的 frame 2 未声明**
  证据：草案 L23-24"帧数 15"、L35"balloon 的 **16 个**评估帧中 125 与 320 本身就是 KF…剔除后 n=13"（16−2=14≠13）；JSON `balloon_generality.*.n_frames=15`、`excl_dt0.n_frames=13`；实测 P2c 在 frame 2 的 `dt_eval=None`、`dyn_bad_psnr=None`（冷启动无前置 KF），`_paired_means` 将该帧从 **P1/P2 主列一并剔除**（analyze_dyn_probe.py:363-370）；prereg L15 锁定 16 帧、L17 说 C− 等臂同法。
  依据：DISCIPLINE #12①③；P4/口径声明家族。
  反驳通道：在 §2 显式写"配对同帧集 n=15（frame 2 因冷启动无前置 KF 被剔），主列 P1/P2/占比均取该 15 帧"，并把 L35 的"16"改掉。
- **[重大] G1 的核心量化依据（跨序列 dB 增益）不可比：P1 基线、P2 天花板、M_bad 面积三重不同**
  证据：草案 L41-44/L23-25 用 `+15.82/+15.85 dB` vs pt2 `+10.73/+11.00 dB` 支撑"代价更大"；而 balloon bad P1 = 18.26/18.48、P2 = 34.07/34.32，pt2 bad P1 = 20.34、P2 = 31.18（`dyn_probe_report.md:18`、母批 §2 逐臂均值）；M_bad 面积 8.72%/9.16% vs 5.8%。pt2 母裁决书本人已裁定"两个像素集的 **dB 不可直接比较（P1 基线不同）**，故一切结论只用**同集比值**"（`verdict_dyn_probe.md` §3 补记），判据机 JSON `desc_decomposition.note` 亦同款。
  依据：DISCIPLINE #12①③、L348；DISCIPLINE #8（泛化结论须排除序列/子集构成混淆）。
  反驳通道：用面积无关量（同集 dl1 比值）为主证据并**声明 dB 仅在各自序列内可比**；或做同面积归一（按 P1 误差分位数而非固定 10cm 取等面积子集）后重算。
- **[重大] G3 借用了未对因果臂预注册的阈值带，且超带余量 = 实测噪声底**
  证据：草案 L51-53"gate 地图上仍超出 ±0.25 dB 的无伤带"；实测 P2c `d_static_db = −0.2555` ⇒ 超带 **0.0055 dB**；而母批实测 L2 重复性"含拟合臂最大偏差 **0.0055 dB / 0.017 cm**"（`verdict_dyn_probe.md` §2）。预注册判据 3 定义在 **P2−P1** 上（prereg L25），balloon 预注册 8 条判据中无 P2c 静态区阈值（判据 7 只含 retention ≥0.50）。
  依据：DISCIPLINE #12①③；P21（阈值必须与信号同尺度、事后改用须留痕）；D9。
  反驳通道：给出该"无伤带"适用于 P2c 的预注册出处；或在 §2 标注"−0.2555 与 0.25 之差 ≈ L2 噪声量级，属边界而非确证超带"。
- **[重大] 气球判据 5/6/8 机器读数跑完未读（D9 组件生效证据未消费）**
  证据：`balloon_generality._judgments.{gate,baseline}.criteria` 含 `5_instrument`（C− 仪器对照，pass=True）、`6_positive_control`（P1 vs render_compare，pass=True）、`desc_P4_vs_P1`（gate 0.928/−1.08/−3.97；baseline 0.862/−1.60/−4.32）、`desc_dyn_cov=1.0`；`dyn_probe_report.md` 跨序列节（191-205）与裁决书全篇（69 行）均未出现这些结论。
  依据：DISCIPLINE #9（组件/仪器生效优先，须有落盘证据并纳入检查清单）；#12③。
  反驳通道：在报告跨序列节补判据 5/6/8 结论行，或在裁决书注明"判据 5/6/8 结果见 JSON，本轮不作结论"并给出去处。

### 次要
- [次要] `n_dyn 占比` 分母未声明且两地图分子完全相同：P2 逐帧 `n_dyn` 列表在 gate/baseline **逐位一致**（3886），7.68% vs 12.08% 之差不来自机制，只来自 `n_static`（50593 vs 32174）⇒ 与 pt2 的 6.4%/4.2% 跨行比较无意义。证据：`dyn_probe_balloon_results.json` arms.P2.n_dyn 两地图相同；`analyze_dyn_probe.py:370`（`n_dyn/n_static`）。依据 #12①③。
- [次要] `bad 占图` 分母未声明：代码写死 `/(480*640)`（`analyze_dyn_probe.py:369`），草案 L23-25 只写百分数。依据 #12①。
- [次要] dt=1 敏感性未做（本审查器补做，n=10 ⇒ 0.6738/0.6937、0.1494/0.1761，结论不变）⇒ 建议把该行补进 §2 作为稳健性一行，并把"pt2 侧 dt=0 帧数=0"写明（草案 L35-37 只给了 balloon 侧）。
- [次要] G2 标题"跨序列**稳健**"对 n=2 序列/单 seed 过度（正文与 §4 已有声明）；依据 #8、#13（论文数字须 3 seeds）。
- [次要] §4「局限」未把两条更有力的未做对照列为未做项：① 同序列内受控对照（取 pt2 中运动最平滑帧子集，用于把"目标类型"与"机制极限"分开）；② 同面积归一（见上一条 G1）。草案 §4 只列了"离线命令未试便宜变体"。依据 #8。

## 无法验证清单
1. balloon 臂的 L2 重复性（同 config 两次）：`l2_repeatability.json` 为 pt2 批（2026-09-19 01:04），balloon 未测 ⇒ G3 的 0.0055 dB 余量在 balloon 上**无噪声底**可核。需主 Agent 提供 balloon 的 L2 复跑或声明未测。
2. R33 两地图的 SLAM 代码 commit 一行未核（仅按 run 目录日期 2026-09-16 判同批）：需 `git log --date=short -- utils/swba.py utils/slam_frontend.py` 对 2026-09-16 各臂定格核实（P25）。
3. balloon 掩码 `dynamic_mask_gtmc` 的覆盖正确性（是否覆盖充气球主体、有无误标背景，P9）未核；`frame_coverage_balloon.json` 只给覆盖率，未给可视化/实例统计。
4. 选帧"等距（np.linspace, round）"的实际间距未逐步复算（工件 `selection_rule` 声明为等距，我未重跑 `cmd_coverage`）。
5. 判据机 `cross_sequence_row` 的 `have` 分支对 `P2cs/P2cr/P2cm` 的兼容性（balloon 未启用这些臂）未测。

## 审稿结论
**Reject**（阻塞项 = 1 条致命：判决/ manifest 标注的测量代码提交 `6e6e8a79` 不含产生 §2 全部数字的判据机改动，改动仍在工作区 ⇒ 判决不可复算，与 NOTES.md:431-436 判定的关卡① 致命项同型）。数字侧好消息：判据机算术已被本审查器独立复算逐位验证（0.6658/0.6871 精确一致），dt=1 补充检验不改变任何结论；因此整改面很小——提交 `analyze_dyn_probe.py` + 改 sha 与 manifest，再修 2 条口径（pt2 保留率 0.594/0.607、n=15 与 frame 2 声明）与 1 条措辞（G1 的 dB 仅同序列内可比），即可重审。
