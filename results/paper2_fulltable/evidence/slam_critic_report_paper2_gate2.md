# 审查报告：论文2 数字/骨架包（关卡② 收口审查）
审查日期：2026-09-19　审查者：slam_critic（只读）
状态：进行中（增量追加）

## 审查对象
- results/paper2_fulltable/evidence/latex/README.md + 6 tex
- results/paper2_fulltable/evidence/verdict_sim3_scale.md
- results/embrace_dyn/evidence/paper2_boundary_note.md
- tests/paper2_fulltable/test_paper2_tables.py
- scripts/02_analysis/paper2_tables.py

## 机械事实
（待填）

## 问题清单
（待填）

## 无法验证清单
（待填）

## 审稿结论
（待填）

## 审查对象（定稿）
- HEAD = 80ab15ab；`papers/paper2/paper2_cvm.tex` 仍是 CVM 空模板（title "A Template for CVM Proceedings"）。
- 被审包：results/paper2_fulltable/evidence/latex/{README.md,6 tex}、evidence/tables_paper2_preview.json、
  evidence/verdict_sim3_scale.md、results/embrace_dyn/evidence/paper2_boundary_note.md、
  tests/paper2_fulltable/test_paper2_tables.py、scripts/02_analysis/paper2_tables.py。
- 批次：R33 同批（2026-09-16，168 个 r33_rebase_* 目录，4 臂 × 7 序列 × 3 seed）。

## 机械事实
- 未跑 health_check（本轮为纯数字包审查；健康检查覆盖不到表内口径）。
- tab1 与 preview JSON 逐位一致（抽查 7 序列 × 4 臂 mean/sd 全对）；tab1 的 raw 来源核过 24 个 seed 值
  （tracking_raw.csv col8/col14 与 JSON ate_seeds/kf_ate_seeds 逐位一致）。
- gate 臂 static_conf 门两态在 21/21 run 均 >0（`edges free=` 49–105 / `static_conf=.*>` 9–116）⇒ 门未恒关亦未恒开。
- gate 臂 config 无 `swba_min_rel_improve`（该臂日志 `rel_improve`=0、`correction not applied`=0）⇒
  未启用自校验门，按 P23「两态按门实例化」属正常，不构成"组件未生效"。

## 问题清单

### 致命
1. **tab4_efficiency.tex 的 online FPS 列是错数（1.000 / 其余 "--"），且 3/4 臂的值被静默丢弃**
   证据：真值 efficiency_raw.csv online_fps：baseline balloon 0.3624、crowd2 seeds 0.5033/0.4809/0.5099、
   gate 0.3402（crowd2 0.4378）、swbaonly 0.3257、final 0.324。生成器 `fps_med` 用
   `round(statistics.median(...))`（paper2_tables.py:257）把 0.34 变成 0，写入时又用 `if table[...]["fps_med"]`
   把 0 当缺失剔除（:482-486）⇒ baseline 只剩 crowd2 的 1 个非零值（0.5033 round→1）⇒ 打印 "1.000"；
   其余三臂全 0 ⇒ "--"。落盘产物 tab4_efficiency.tex:10-13。
   依据：D12（数字须能指到工件/口径）、红线「数字不得与原始产物矛盾」；README:63 的"数字完整性"自检未覆盖效率。
   反驳通道：给出 fps_med 的原始 21×3 值列表并说明 "1.000" 的合法来源。
2. **tab3s_static.tex 同表混算两种静态协议，且 README 的"两源不混算"与事实相反**
   证据：preview JSON 的 `mask_source`：balloon/balloon2/pt/pt2 = `runtime_pa:dynamic_mask_gtmc`（~88 帧 @5）；
   crowd/crowd2/crowd3 = `seg_mask`（离线 render_compare_static；n_frames=8，/render_compare_static 的
   render_metrics.json 自带 mask_source='seg_mask'）。baseline_crowd 的 mapping_raw.csv 只有 1 行
   mask_type='full'（无 static 行、static_psnr 为空）⇒ `runtime_static_of` 返回 None ⇒ 回退；离线三 seed
   static_psnr = [19.8692, 20.7822, 20.4275] 均值 20.3596 = tab3s 的 crowd Base 20.36（逐位）。
   即：同一张表 4 行来自 88 帧运行期口径、3 行来自 8 帧离线口径，表内无任何来源列/脚注，
   README:44 写"运行期 P-A > 离线 6 帧；**两源不混算**"。
   依据：D12（口径与工件核验 #12）、P1/P29 口径混引家族。
   反驳通道：给出三个 crowd 序列该行的运行期 P-A 来源（mapping_raw 的 static 行）或说明此混算已声明。
3. **主表（tab1）与项目自己的验收红线冲突，而数字包内无一处披露**
   证据：tab1_main.tex:10-16 gate vs Base：balloon 3.25→4.22（+30.1%）、crowd3 1.53→1.83（+19.4%）、
   pt2 10.40→11.68（+12.2%）劣化；crowd 2.23→2.32、crowd2 2.26→2.50 亦劣；仅 pt1（11.31→7.95）与 balloon2 改善。
   过 5cm 线集合与 baseline 完全相同（4/7，且是同样 4 条）⇒ 净过线贡献为零；NARRATIVE:131-168 已如实写
   （"净过线贡献为零""pt1 置换检验 p=0.30 ⇒ 与抽样噪声不可区分"），但**数字包本体**（latex/README.md + 表注）
   对"gate 在 3/7 序列劣于 baseline"只字未提。
   依据：D7（绝对 ATE 第一验收标准）、红线「易序列不得退化」、P19/D6（负结果不得包装）。
   反驳通道：给出 README 或表注已含该披露的版本号/行号。

### 重大
4. **tab3s 的 coverage 列恒 1.000（28/28），而项目判据机自己已登记该列"无判别力"**
   证据：tab3s_static.tex:8-37 全列 1.000；dyn_probe_verdict.json `causal_judgments.gate.dyn_cov_note` =
   "掩码内覆盖率各臂恒 1.000 ⇒ 该列在本设定下无判别力（已登记，不参与任何判据）"。
   依据：D12；审稿人必然问该列意义。反驳通道：说明该列在论文中的解读价值。
5. **tab2r_render.tex 表注断言 "no arm degrades the rendering of the static scene"，与同包 tab3s 的数字矛盾**
   证据：tab2r_render.tex:20。tab3s 静态 PSNR gate vs Base：balloon 23.96→23.84、balloon2 21.40→21.30、
   crowd 20.36→20.16、crowd2 20.28→20.26、crowd3 23.93→23.88（5/7 下降）；tab2r 本身是全图口径
   （balloon 21.80 ≠ 静态 23.96），却拿"静态场景"下结论。另 tab2r 自身也有下降项（balloon2 18.72→18.51）。
   依据：D12 表注须与所示数字同口径；P1/P29 跨口径引用。
6. **Sim3 撤回未传播到 NARRATIVE（写作会话的权威映射仍要求用该列）**
   证据：NARRATIVE.md:345「Tab.2 pt 逐 seed | … + Sim3 scale 列 | … joint_correct/evidence/j1_screen_summary.csv」、
   :375「§5.1 … Tab.2 pt 逐 seed（Sim3）」、:382「§6 Discussion：Sim3 分解…」；而 verdict_sim3_scale.md:78
   明令"不得进入正文/表格/Discussion"。且 Tab.2 映射的数据源（j1_screen_summary.csv）与生成器实际源
   （tables_paper2_preview.json）不是同一个。
   依据：D16（文档联动）、D6。反驳通道：提供已更新的 NARRATIVE 或澄清"Sim3 分解"所指。
7. **tab2_pt_seed.tex 本体无撤回警告，表注仍在陈述被撤回的主张；门禁反而要求该列必须存在**
   证据：tab2_pt_seed.tex:21「Scale is the dominant error component here; the same-batch Sim(3)-aligned ATE
   is reported in the text.」——即被撤回的"尺度是主要误差成分"；撤回警告只在 latex/README.md:16。
   test_paper2_tables.py:117-129 逐位断言 Sim3 列必须与 JSON 相符 ⇒ 按撤回删列该测试会红。
   依据：P19（不得把失效机制当结论）、D16。缓解：README:11 已声明该目录关卡②隔离。
8. **边界素材 §3 把 PSNR 保留与深度-L1 保留混成一个"几何保留"区间**
   证据：causal3_judgments.gate.E7_stratified.by_mask_size.P2c.n_dyn<med = {dl1: 0.216, psnr: 0.014}；
   paper2_boundary_note.md:123 写「几何保留 掩码 <中位 **0.014–0.216**」（0.014 是 psnr、0.216 是 dl1），
   段 B（:186）同。dl1 口径的真实区间为 0.1767–0.2902（P2cuv/P2c/P2cu）。
   依据：P1/P29 跨口径混引。反驳通道：给出 dl1 口径下"0.014"的来源。
9. **边界素材 §2 的"成本"列口径未声明，且轮 I 与轮 III 在测量完全相同的情况下成本差 5 倍**
   证据：causal_judgments.gate.means.P2c 与 causal3_judgments.gate.means.P2c **逐位相同**
   （dyn_bad_psnr 21.8293/21.8278、dl1 20.1776/20.1833、full_psnr 21.5928/21.5929、n_dyn 3909.0667/3909.0667，
   frames_used 逐元素相同），但 `C4_cost.n_dyn_frac`=0.0708 vs `E5_cost.n_dyn_frac`=0.3634（D5=0.0767）⇒
   分母从 ~55.2k 变成 ~10.8k。表头却把 n_dyn 标为"成本"、另设"成本"列（:67）。
   依据：D12/P29；审稿人会认定表内有错。反驳通道：给出 E5 成本定义与 5× 差异的解释。

### 次要
10. 13 项门禁里恒真/自证项：`test_sim3_not_worse_than_se3`（test:63-71，Sim(3) 比 SE(3) 多 3 自由度 ⇒
    RMSE 不可能更高，数学恒真）；`test_captions_declare_protocol`（:87-92 只测表注字符串）；
    `test_selfcheck_clean`（:74 用生成器自己的 selfcheck 断言生成器）；`test_tab1_numbers_match_json`/
    `test_tab2_pt_numbers_match_json`（:102-129 拿同一次运行写到 tmp 的表去断言同一模块的输出，只证明确定性）。
    真门禁 = `test_sim3_positive_control_matches_col8`（:48-60，对工件 col8 的独立两路径核对）+ 4 项结构测试。
11. **缺该测而未测**：(a) 没有任何测试校验已提交的 `evidence/latex/*.tex`——测试全部写 tmp_path（:29-33），
    所以产物与生成器漂移时依然全绿（tab4 的 1.000 正是这样漏出去的）；
    (b) tab2r/tab3s/tab4 三张表**零数字一致性测试**；(c) 无"静态指标必须来自运行期 P-A"的断言（致命 2 无人拦）；
    (d) 阳性对照门槛 `checked >= 60`（:60）低于 README:56 宣称的 84，覆盖可静默退化到 60。
12. README:56「逐位吻合」用词不准（判据实为 ≤0.01cm）；README:63 的覆盖自检只查 ATE/渲染/静态，不查效率。
13. tab3s 的 ghost excess 在 4/7 序列为负（balloon2 −3.04、crowd3 −10.61、pt −1.21、pt2 −0.69），
    crowd3 达 −12.97，表注只写 "lower is better"，未定义负值语义。
14. README:44 称离线源为"离线 6 帧"，但 crowd 系离线源 n_frames=8（render_compare_static 的
    render_metrics.json），balloon 的离线源只有 seed0（6 帧）⇒ 文案与实际不符。
15. verdict_sim3_scale.md:64 的表把 balloon2 路径比 0.7231→0.6696 标为"gate 更近 1"，但
    |1−0.6696|>|1−0.7231|，方向标反（我独立复算得同值 0.7231/0.6696）。不影响撤回结论。
16. 边界素材 :5-6 声明数字来源是 dyn_probe_verdict.json 五节，但 §1.2/:36 与段 A(:174) 的 `M_bad` 面积
    5.8%/17,747px 引的 `bad_subset_decomposition` **不在该 JSON**（全文 grep 返回 False）；
    :117 的 `evidence/diag_causal_fairness.json` 是相对路径、未写全。
17. 边界素材 :65 的"各轮 P1 基线"清单漏轮 II（其 P1=19.19/19.09 见 :103），而 §2 的"比值 vs P1"列依赖各轮 P1。
18. 跨轮禁令是文本警告而非结构隔离：:62-64 禁止跨轮相减，但 §2 把四轮并入同一张表、共用"比值 vs P1"与
    "静态区 Δ"两列（这正是自述的历史事故成因，:7-8）。且轮 I 与轮 III 帧集逐元素相同（见重大 9），
    "不得跨轮相减"对 I↔III 反而过度限制。

## Sim3 撤回的独立复核（结论：撤回正确，不过强，且偏保守）
- 理由一：我从 JSON 复算 gate/baseline 的 |1−scale| 方向 = 5 好 2 差（balloon 1.09453→1.09932、
  balloon2 1.15876→1.16993 更差；其余更近 1），与判据书表格逐位一致 ⇒ 成立。
- 理由三：我独立复算路径长度比（trj_full_final.json 位置差分范数和之比）：
  pt1 0.7693→0.6671、pt2 0.7123→0.6069、crowd 0.6250→0.4692、balloon2 0.7231→0.6696，
  与判据书第二列逐位一致 ⇒ 成立；且我补算 balloon 0.7970→0.7217、crowd3 0.5294→0.4488 ⇒
  **路径比对 6/6 序列都显示 gate 的 est 路径相对 GT 更长**，与 LS 的"5 好"系统性相反。
- 判据书漏掉的第四条理由（可加固撤回）：LS 与 ATE 方向不一致——pt2 LS 说 gate 更近 1 而 col8 ATE 说
  gate 更差（11.68>10.40）；crowd LS 说 gate 更好而 ATE 说更差（2.32>2.23）。
- 结论：撤回不过强（"可靠性未建立"的表述甚至偏保守）；但**tab2_pt_seed.tex 保留该列不安全**（见重大 7）。

## 边界素材越界检查（结论：未把未测 ATE 写成方法优势，但"可主张"门槛偏低）
- :4/:142-143 明令不得表述为"方法更好"、未测 ATE；:201-203 再次强调 ⇒ 声明方向正确。
- 但 :200「§1 作为方法学贡献（分区指标协议，**可直接主张**）」在 0 个 ATE 证据、单序列(pt2)+单 seed+
  第二序列(balloon) 的前提下门槛偏低（D7：ATE 是第一验收标准）⇒ 建议改为"候选协议，待在线 ATE 验证后主张"。
- §2 的五节判据数字可逐条指到工件（我核 13 个判据键全对：C1b 0.5936/0.6068、C2 1.2296/1.2181、
  C3 −0.5346/−0.6289、C5 1.3207/1.3308、D1 1.0253/1.0260、D2 0.0475/0.0778、D3 0.5826/0.6054、
  D4 −0.8309/−0.98、D6 1.3217/1.3756、E2 0.0285/0.0535、E3 0.5021/0.4976、E4 −1.0303/−1.2425、
  E6 1.2475/1.2546；balloon bad_px_frac 0.0872）⇒ 该部分可靠性好。
- 帧集：母批 16（=轮 I 的 15 帧 + cold_start [2]，judgments 节无 frames_used 字段，属推断）、
  轮 I 15、轮 II 12（causal2 frames_used=12）、轮 III 15 ⇒ :62 的 16/15/12/15 与工件一致。
- :3 的"关卡② 未过、不得写入 papers/"声明**足够防"越界宣称方法更好"，但不足以防**：
  把未测 ATE 的协议当"可主张贡献"（:200）、表内口径错误（重大 8/9）、面积数字不在所声明工件（次要 16）。

## F：是否有数字已进论文
- papers/：paper2_cvm.tex 仍是 CVM 模板（无任何本包数字）；papers/paper2/ 另有 NARRATIVE.md、
  REVIEW_skeleton_2026-09-14.md（NARRATIVE 已引用数字，属关卡②对象）。
- /data/master_thesis：3 个文件引用 `paper2_fulltable` 路径（04_writing/chapters/04_swba.md:5、
  03_results/tables/person_tracking_ladder.md:75、02_analysis/scripts/verify_tables.py），
  按字面量 grep（4.22/3.25/47086/23.96/21.80/1.0983/7.95）未命中本包数字 ⇒ 未发现泄露，但非逐文件通读。

## 无法验证清单
- V1 evo LS scale 本身未复算（需 evo 环境）；只复算了其派生的路径比（与判据书一致）。
- V2 母批 16 帧无直接字段（见上，推断）。
- V3 6 张表的 84×3 单元格未逐一核；已核范围 = tab1（24 个 seed 的 raw col8/col14 + 全表 JSON↔tex）、
  tab5（4 个）、tab3s（crowd/balloon 的来源链）、tab4（全表）、tab2_pt（pt1/pt2 全 24 格）。
- V4 master_thesis 是否以其它形式引用本包数字（未逐文件通读）。

## 反驳受理
（待被审方提交证据后逐条裁决）

## 审稿结论
**Reject（阻塞项 = 致命 1/2/3）**：tab4 的 FPS 列是错数；tab3s 混算两种静态协议且 README 声称相反；
主表与验收红线冲突而数字包无披露。Sim3 列撤回本身正确（我独立复算支持，且可加第四条理由加固），
但撤回未传播到 NARRATIVE 且 .tex 本体保留无警告。
