# 裁决：论文 2 的 Sim(3) 尺度列 —— **候选结论撤回，不得入论文**

> **账本补登（2026-09-25，D2-015 追溯登记）**：本件成文于决策账本设立（2026-09-20）之前，无当期账本号；统一追溯登记见 `DECISIONS.md` **D2-015**。

> **关卡② 状态：⏳ 未过（本文件是"撤回"判定，不是论文数字）**。判定对象 =
> `tables_paper2_preview.json` 的 `sim3_scale_seeds` 列（生成器
> `scripts/02_analysis/paper2_tables.py:sim3_of`，R33 同批）。**本列不得写入论文正文、表格或 Discussion**；
> 生成物 `evidence/latex/tab2_pt_seed.tex` 现已**含该列**，该目录按 `latex/README.md:11` 处于
> 关卡② 隔离状态，本轮**追加**一条"Sim3 列已撤回"警告（见文末）。
> **性质**：判定与重分析（**零新实验**，只读既有 R33 产物）。

## 1. 撤回的结论

**原候选主张**（`NOTES.md:228-240`，"已验证结论·方法层面"）：
"同批 Sim(3) 尺度：门控/SWBA 臂降低尺度漂移"——依据是 pt1 上 baseline 1.145–1.161
vs gate 1.089–1.106 **逐 seed 严格分离**。

**判定：撤回。** 三条独立理由（逐条给工件键）：

### 理由一：跨序列方向不一致（该主张的通达范围远超证据）

`tables_paper2_preview.json`（键 `"<arm>|<seq>".sim3_scale_seeds`，同批 3 seed）里，
"离 1.0 更近 = 尺度漂移更小"口径下，**gate 臂在两条序列上比 baseline 更远离 1.0**：

| 序列 | baseline（seeds 均值） | gate（seeds 均值） | \|Δ1\| baseline → gate |
|---|---|---|---|
| balloon | 1.0945 | **1.0993** | 0.0945 → **0.0993（更差）** |
| balloon2 | 1.1588 | **1.1699** | 0.1588 → **0.1699（更差）** |
| crowd | 1.1692 | 1.1425 | 0.1692 → 0.1425（更好） |
| crowd2 | 1.0740 | 0.9959 | 0.0740 → 0.0041（更好） |
| crowd3 | 1.0529 | 1.0406 | 0.0529 → 0.0406（更好） |
| person_tracking | 1.1511 | 1.0983 | 0.1511 → 0.0983（更好） |
| person_tracking2 | 1.1136 | 1.0999 | 0.1136 → 0.0999（更好） |

即 5 好 2 差，且**差的两条正好是 balloon 家族**。按 `DISCIPLINE.md` 第 8 条
（"任何方法的最终验证必须包含未参与调参的序列；**易序列不得退化**；pt 家族上的迭代结论
**在推广前只是假设**"），该主张**不成立为通用结论**。原主张只在 pt1/pt2 上做过检验
（7 序列数据**本来就同批在手**，属于"只看了支撑结论的那两列"）。

### 理由二：即使在 pt 家族内，效应也不能记在"门控"头上

pt1 上三个方法臂彼此差异极小，而它们与 baseline 的差距大一个量级：

| 臂 | pt1 均值 | pt2 均值 |
|---|---|---|
| baseline | 1.1511 | 1.1136 |
| swbaonly | 1.1006 | 1.0987 |
| final（+SWBA+LC） | 1.1048 | **1.0946** |
| gate | 1.0983 | **1.0999** |

⇒ 与 baseline 的差距 ≈ **4.8%（pt1）/ 1.5%（pt2）**，而三个方法臂之间只有 **~0.2–0.5%**，
且 **pt2 上 gate 的均值高于 final**（1.0999 > 1.0946）⇒ **归因应为 SWBA，不是门控**。
`NOTES.md:228` 的标题"门控/SWBA 臂降低尺度漂移"**把效应记到了门控上**，须收窄。

### 理由三：该列本身的可靠性未建立（两个独立估计量方向相反）

对同一批 `plot/trj_full_final.json`（与主表 ATE 同源：阳性对照已证自算 SE3-ATE 与
`tracking_raw.csv` col8 逐位吻合 84/84），用**另一个**尺度估计量交叉检验——
路径长度比 `gt_path/est_path`（同一 seed0 12+ 个 run，命令见 §3）：

| 序列（arm=baseline → gate） | LS Sim3 尺度 | 路径长度比 |
|---|---|---|
| person_tracking | 1.1612 → 1.0992（gate **更近 1**） | 0.7693 → 0.6671（baseline **更近 1**） |
| person_tracking2 | 1.1161 → 1.1039（gate 更近 1） | 0.7123 → 0.6069（baseline 更近 1） |
| crowd | 1.1703 → 1.1420（gate 更近 1） | 0.6250 → 0.4692（baseline 更近 1） |
| balloon2 | 1.1588 → 1.1673（gate 更差） | 0.7231 → 0.6696（gate 更近 1） |

⇒ **两估计量在 pt 家族上方向相反**（LS 支持 gate、路径长度比支持 baseline），且量级都对不上
（LS 0.80–1.18 vs 路径比 0.29–0.80）。**至少有一个不可信**；在两个估计量给出一致结论之前，
该列**不能作为"尺度漂移"的度量**使用。

附带的诊断线索（未诊断完，如实登记）：所有 run 的 Sim3 对齐旋转都是 **171.9–178.2°**
（帧约定翻转量级）；本项目此前已登记同类退化先例（自洽几何 Plan B：Umeyama 在短轨迹上给出
**175° 伪解**）。est 轨迹路径长度（4.2–7.6 m）远大于 GT（1.9–4.3 m），而 SE3-ATE 只有 5–12 cm
⇒ 全局相似变换在做的事情与"均匀尺度误差"不符。**该列的病根未定位，属"可靠性未建立"而非"已证错"。**

## 2. 结论与动作

1. **撤回** `NOTES.md` 的候选条目（`已验证结论·方法层面`），改为"已撤回/不成立"，并写明三条理由。
2. **不写入论文**：Sim(3) 尺度列（及其派生的任何论断）不得进入正文/表格/Discussion。
   `evidence/latex/tab2_pt_seed.tex` 现含该列 ⇒ 在该目录 README 追加撤回警告。
3. **若日后要用该列**，前置条件（按顺序）：① 定位病根（对齐旋转约定 vs 真尺度误差；
   加退化守卫：旋转角/尺度合理性区间 + 与 SE3-ATE、路径长度的**三方一致性**检验）；
   ② 七序列全部一致后才允许作为候选；③ 仍需按与 ATE 同标准过关卡②。
4. **方法论教训入 NOTES 踩坑**：新算列在**跨序列 + 双估计量交叉检验**之前不得登记为候选结论。

## 3. 口径与可复算

- **数据源**：`results/paper2_fulltable/evidence/tables_paper2_preview.json`，
  键 `"<arm>|<seq>"` → `sim3_scale_seeds` / `sim3_ate_seeds`（arm ∈ {baseline, swbaonly, final, gate}，
  seq = Bonn 7 序列，seed 0/1/2）。生成器 `scripts/02_analysis/paper2_tables.py`（`sim3_of`，只读既有产物）。
- **本文件 §1 的三个表**分别来自：该 JSON 的原始键（理由一、二）；理由三的第二列由下列只读命令算出
  （`evo.core.trajectory.align_trajectory(..., correct_scale=True, return_parameters=True)` 的 scale
  与 `PosePath3D.positions_xyz` 的相邻差分范数和之比）：

  ```
  results/paper2_fulltable/r33_rebase_<arm>_<seq>_seed0/datasets_bonn/r33_rebase_<arm>_<seq>/seed_0/*/plot/trj_full_final.json
  ```

- **口径边界**：Sim(3) 是全轨迹**全局**对齐的最优尺度，与 Tab.1 的 SE3-ATE（`ate_rmse_cm`，全帧）
  是**不同口径**，任何情况下不得混引；`DISCIPLINE.md` 第 12 条（口径与工件核验）。
- **未做**：未诊断病根；未在其他 seed 上重复理由三的交叉检验（只用了 seed0）；
  未检查 `trj_gt` 的位姿约定与 est 是否同系——这三项是本判定**留白**，如实登记。
