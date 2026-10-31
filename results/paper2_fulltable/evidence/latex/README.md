# evidence/latex/ — 论文 2 表格（CVM 2027 版式，机器生成）

**生成器**：`scripts/02_analysis/paper2_tables.py`（v0 主表；确定性，只读 `results/` 既有产物）
+ `scripts/02_analysis/paper2_baseline_table.py`（`tab_baseline.tex`，11 方法横比；数据源
`resources/baselines/baselines_result/`，覆盖报告 `resources/baselines/05-coverage_report_2026-10-10.md`）
**来源批次**：**R33 同批同码**（baseline / +SWBA / +SWBA+LC / gate × Bonn 7 序列 × 3 seed，
全部 run 时间戳 2026-09-16）
**重新生成**：
```
/data/conda_envs/monogs-ours/bin/python scripts/02_analysis/paper2_tables.py --selfcheck
```

## 门禁状态：**v0 已归档；新稿未立；`tab_baseline.tex` 待关卡②**（2026-10-11 更新）

按 `DISCIPLINE.md`「收口审查关卡」第 2 条（论文数字入表前须过 slam-critic）：**v0 时代的
入表审查全部作废**——v0 已随重写立项冻结（D2-029，`papers/paper2/archive/v0_2026-10-10/`），
活区无 tex 可 `\input`。**重写后的新稿**若引用本目录任一表（含 `tab_baseline.tex`），
须**重新走关卡②** 方可入表；本目录数字源 = 本目录 .tex + `tables_paper2_preview.json` +
其引用的 run。`tab_baseline.tex`（11 方法横比，`scripts/02_analysis/paper2_baseline_table.py`
生成）**尚未过关卡②**。历史审查记录见下节（保留作 v0 时代证据，不再更新）。

## 关卡② 第 1 次审查 = **Reject**（2026-09-19）→ 已整改

审查者 = `slam-critic`（独立会话）。**3 致命 / 9 重大 / 若干次要**。已整改项：

| # | 级别 | 问题 | 处理 |
|---|---|---|---|
| 1 | **致命** | **Tab.4 的 FPS 列是错数**：生成器 `round(median(fps))` 取整到 0，下游 `if fps_med` 真值过滤又把 0 当缺失剔除 ⇒ 只余一个 `1.000`、其余三臂 `--` | 生成器两处都修（`round(...,3)` + `is not None`）；重生成后真值 **0.456 / 0.354 / 0.354 / 0.415** |
| 2 | **致命** | **Tab.3s 同表混用两种静态协议**（运行期 P-A 4 序列 + 离线 seg_mask 3 序列），而 README 称"两源不混算"；LaTeX 版还比 Markdown 版**少一列**（丢了 `mask source`） | LaTeX 版恢复 `mask source` 列（下划线已转义）；表注显式声明"跨序列慎比"；本 README 表述改为逐序列源的准确说法 |
| 3 | **致命** | **主表与验收红线冲突而本包零披露**：`gate` 相对 `baseline` 在 **5/7 序列**劣化（balloon +30.1% / crowd3 +19.4% / pt2 +12.2% / crowd2 +10.6% / crowd +3.8%），且**过 5cm 线的序列集合与 baseline 完全相同**（balloon, crowd, crowd2, crowd3） | **本包不擅自改写论文主张**——该披露已写入本节；**scoping 决定须由用户 + 写作会话做**。数字来源 `tables_paper2_preview.json` 的 `ate_mean` |
| 4 | 重大 | Tab.3s 的 `coverage` 28/28 恒 1.000，而项目已登记该列无判别力 | 表注已声明"non-discriminative, reported for completeness only" |
| 5 | 重大 | **Tab.2r 图注断言"没有任何臂弄坏静态场景"是假的**（gate 静态区 PSNR 在 5/7 序列低于 baseline） | 图注改为只声明全图口径 + 指向 Tab.3s；并给出实测的最大跨臂全图差 **≤0.38 dB**（7 序列） |
| 6–7 | 重大 | **Sim(3) 撤回未传播**：`tab2_pt_seed.tex` 图注仍在陈述被撤回的主张；`NARRATIVE.md` 仍要求用该列 | `tab2_pt_seed.tex` 图注改为**显式撤回警告**（"WITHDRAWN and must not be used"）；NARRATIVE 侧加警告标记（正文 scoping 属写作会话） |
| 10–11 | 次要 | 门禁部分自证；**无任何测试校验已提交的 `evidence/latex/*.tex`** | 新增 `tests/paper2_fulltable/test_paper2_latex_committed.py`：校验提交产物与生成器一致、FPS 列无 `--`、tab3s 有掩码源列、撤回警告在场、图注不含被撤回主张 |

**#3 已定调并落地（2026-09-19 用户定调，2026-10-10 收口）**：系统表 scope = **前作栈**——
系统表降为 **Base 单列**（论文 2 无新系统配置）；含 SWBA+LC+gate 的复合臂**不进主表**，
其完整四梯只在附表 `tab:ladder`（消融）。#4/#5 已按工件更正；静态区"不退化"卖点按候选改写收编
（只声明全图跨臂差 ≤0.38dB + 逐序列并陈，已实施于 Tab.2r 图注与 NARRATIVE §5.3）。
依据：gate 相对 Base 5/7 序列 ATE 劣化 + 过 5cm 线集合相同 + 基线栈静态 PSNR 5/7 更好
（本表 #3 行 + `evidence/diag_ate_degradation.md`）。

## 表清单与口径（DISCIPLINE #12 ①）

| 文件 | 表 | 口径 |
|---|---|---|
| `tab1_main.tex` | 系统 ATE | ATE **col8 全帧**（`ate_rmse_cm`），3-seed mean±sd；**单列 = 前作栈（Base）**（2026-10-10 G2-M1 修订：论文 2 无新系统配置 ⇒ 系统表只报 Base；含 SWBA/LC 的复合臂不进主表） |
| `tab5_ladder.tex` | 阶梯消融 | **四梯消融**（Base/+SWBA/+SWBA+LC/+Gate），ATE col8 全帧（2026-10-10 方案 A：原「关键帧口径附表」退役，本文件改为审计用阶梯表 `tab:ladder`） |
| `tab2r_render.tex` | 渲染 | 全图 PSNR/SSIM，**离线渲染协议**（`render_compare.py`，采样避开 KF 网格）；单列 = Base |
| `tab3s_static.tex` | 静态区 | `M_static = valid-GT-depth ∧ ¬dynamic`；**逐序列**用哪个源由数据决定：4 序列 = 运行期 P-A（`runtime_pa:dynamic_mask_gtmc`），crowd/crowd2/crowd3 = 离线 `seg_mask`（8 帧）⇒ **表内混两种协议**，故**必须保留 `mask source` 列**（表注已声明"跨序列慎比"）。同一个数字**不**由两源平均得出；单列 = Base |
| `tab4_efficiency.tex` | 效率 | Base 单行：`online_num_gaussians` / `online_peak_gpu_memory_gb` / `online_fps`（**fps 受并发混杂，仅作旁证**，表注已声明） |
| `tab_baseline.tex` | 11 方法横比（新，2026-10-10） | **公共 BONN 6 序列** × 11 方法（static/dynamic 组）ATE (cm)，Horn SE(3)/ddof=1；发散格标 `(d)`；**来源** `resources/baselines/baselines_result/*/tracking_raw.csv`；**⚠ 待关卡②**（生成器 `scripts/02_analysis/paper2_baseline_table.py`） |
| `tab2_pt_seed.tex` | pt 逐 seed | **已删除**（2026-10-09：正文零 `\input` 的死件）；逐 seed/Sim3 读数仍在 preview JSON/md |

## 自检（生成器每次运行打印）

1. **阳性对照**：本生成器自算的 SE3-ATE 与 run 自报的 `tracking_raw.csv` col8 **逐位吻合**
   （84/84，全部 ≤0.01cm）——证明对齐路径与 run 内评测同协议、表格数字无二次口径漂移。
2. 口径隔离：col8 与 col14 分文件、分标题；两者数值大面积相同即报错（疑取错列）。
3. LaTeX 结构：环境配对、每行列数一致、`_` 转义（无 TeX 工具链下的可编译性代理）。
4. 覆盖：每臂 ATE/渲染/静态均 7/7。

测试：`tests/paper2_fulltable/test_paper2_tables.py`（13 项，含上述 1-3 的常驻化）。

## Sim(3) 列——**⚠ 已撤回：不得入论文**（2026-09-19）

**撤回判定书**：`evidence/verdict_sim3_scale.md`。三条理由（逐条带工件键）：

1. **跨序列方向不一致**：同批 7 序列全表里，gate 相对 baseline 的"离 1.0 距离"**5 好 2 差**，
   而差的两条正是 **balloon（1.0945→1.0993）/ balloon2（1.1588→1.1699）** ⇒ 按 `DISCIPLINE.md`
   第 8 条（易序列不得退化；pt 家族结论推广前只是假设）**不成立为通用结论**。
   原表述只检验了 pt1/pt2（其余 5 序列的数据**同批在手**却未看）。
2. **归因错误**：pt1 上三个方法臂（swbaonly 1.1006 / final 1.1048 / gate 1.0983）彼此只差
   ~0.2–0.5%，而与 baseline（1.1511）差 ~4.8%；pt2 上 **gate 均值反而高于 final**
   （1.0999 > 1.0946）⇒ 效应应记在 **SWBA** 上，**不是门控**。原"SWBA + 门控"的写法须收窄。
3. **该列可靠性未建立**：换用路径长度比 `gt_path/est_path` 作独立估计量，**在 pt 家族上与
   Sim3 尺度方向相反**（pt1：LS 支持 gate 1.1612→1.0992，路径比支持 baseline 0.7693→0.6671），
   量级也差一倍以上（LS 0.80–1.18 vs 路径比 0.29–0.80）。病根未定位（所有 run 的对齐旋转都是
   ~172–178°，属本项目已登记过的退化量级）。

⇒ **动作**：`tab2_pt_seed.tex` 里该列**不得使用**（文件本身保留，仅作已撤回工件）；
`NOTES.md` 的候选条目已改为"已撤回"。**若日后要用**：先定位病根并加退化守卫，
再在**七序列一致**的前提下重新走判定流程与关卡②。

### 原始读数（仅为可追溯而保留，**不得作为主张**）

同批自算给出（gate 臂均值）：pt1 = 1.0983（seeds 1.099/1.106/1.089）、pt2 = 1.0999；
**baseline 臂** pt1 = 1.145–1.161、pt2 = 1.110–1.116（pt1 上逐 seed 严格分离）。
**注意**：这两条序列上的分离是真的，但它**不是**通用结论（见上第 1、3 条）。

## 已知缺表（本目录尚未生成）

- **Tab.3 消融 + 悬崖率**：悬崖率来自 held-out rollout 批（`paper2_rollout`），非本批数据源，待写作会话另立来源后生成。


> **2026-09-24 口径更正（D1-014 F1 整改后）**：本文件下述 "5/7" 均为**旧 gtmc 运行期口径**下的审查结论（历史留痕，不改动原文）。canonical 口径重算后：ATE 劣化格数不变（跨批比较基准未变），**静态 PSNR 劣化格数 5/7 → 4/7**（balloon/crowd/crowd3/person_tracking2），`tables_paper2_preview.json` 为权威数字源。
