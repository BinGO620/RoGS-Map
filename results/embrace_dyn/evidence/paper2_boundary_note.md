# 论文 2 素材：动态区域的**分区渲染评测协议**与「保留动态」的代价边界

> **⚠ 门禁状态：关卡② 未过 —— 本文件是待审素材，不得直接写入 `papers/`（含 `NARRATIVE.md`）。**
> 按 `DISCIPLINE.md`「收口审查关卡」第 2 条，论文数字/骨架章节入表前须过 `slam-critic`。
> **数字来源**：`results/embrace_dyn/evidence/dyn_probe_verdict.json` 的五个判据机节
> （`judgments` / `causal_judgments` / `causal2_judgments` / `causal3_judgments` / `balloon_generality`），
> 本文件的表格由工件 **dump 后粘贴**（非手写；首版手写把轮 III 的数误填进母批行、并把
> `dyn_psnr` 与 `dyn_bad_psnr` 混用，已按工件更正 —— 见 `NOTES.md` 踩坑「把结论写强」）。
> **性质**：离线筛选，**非论文数字**；口径边界见 §4。

---

## 1. 可主张的**方法论贡献**：动态区域的分区渲染指标协议

### 1.1 为什么这是空位（文献侧）

`resources/lit_dyn_mapping/gap_analysis.md` **结论 2**（该目录由独立文献会话维护，按**节名**引用）：
12+ 篇动态/4D GS-SLAM 工作**只报全帧指标**；唯一的分区先例是 MoPe 的 `background-only` +
`tail-only`（单目 iPhone 残影专项、语义性的"最难段"）；**按 vacated 几何定义的残影分区 +
RGB-D 在线 SLAM 语境 = 空位**。同处亦记录：会场（CVM 2027）入选样本抽样 7 篇**无一报分区指标**
⇒ 报了是**差异化**（但见 §4 第 7 条的会场口径：**不能指望因此加分**）。

### 1.2 协议定义（可直接写进方法节）

**分区（逐帧、由 GT 与一个中性臂共同定义，对全部被评臂相同 ⇒ 配对）**：

| 记号 | 定义 | 用途 |
|---|---|---|
| `M_dyn` | GTMC 动态掩码 ∧ 有效 GT 深度 | 动态区域总集 |
| **`M_bad`** | `M_dyn` ∧ (**P1「抹掉」臂**的渲染 GT-深度误差 > **10 cm**) | **"反动态范式真的弄错了"**的像素 |
| `M_good` | `M_dyn` \ `M_bad` | P1 本已正确的动态像素 |
| `M_static` | 有效 GT 深度 ∧ ¬动态 | 静态区（`render_compare` 既有口径） |

**关键设计**：`M_bad/M_good` 的划分**只用中性臂 P1 与 GT**、不看任何被评臂的表现 ⇒ 分区在臂间
**完全相同**，比值可比。这是本协议与"事后挑好看的像素集"的**唯一分界**。
面积量级：`M_bad` 占图 **5.8%**（pt2，均值 17,747 px）/ **8.7–9.2%**（balloon），
`M_good` ≈ 14,078 px（≈4.6%）。**必须与每个数字同时报出。**

**必要性的文献论据**（吸收 `metrics.md` 后补）：DynaGSLAM 是 29 篇里**唯一**报动态区指标的
（DynaPSNR，正文 §6 逐字；机械 grep 30 个 PDF 仅它命中），而它自己的表注承认
**"DynaPSNR unavailable for [46], because dynamic objects are removed"**
⇒ **凡采用"抹掉"范式的系统，动态区指标直接不存在**（0 与 0 无限相似，也即 DynaGSLAM 补充材料 §B
点名的"无效像素置 0 作弊"的同类后果）。分区协议正是为了填这个洞：它让"抹掉派"与"保留派"
**可同表比较**。第二条空位：**位姿误差进入渲染指标的混淆**——29 篇全部用"掩码内评估"或全帧，
**无人做"同一地图、多组位姿扰动下的渲染指标敏感性"**；本协议的地图固定 + 同帧集配对设计
恰好把"地图内容"与"位姿质量"解耦（`M_bad` 只由 P1 与该帧 GT 定义，臂间共享）。

**指标与纪律**：

1. 每个分区内报 PSNR / 深度-L1（+ 既有 `ghost_excess`、`coverage`）；
2. **跨分区/跨像素集的 dB 不可比**（各自 P1 基线不同）⇒ 结论**只允许用同区内的比值**
   （如 `depth-L1(臂)/depth-L1(P1)`）；这是踩坑记录「真假增益必须分离」的直接产物；
3. 同帧集配对（冷启动帧剔除后各臂同集合）；
4. **阴性对照**：错位臂（拟合后沿相机系平移 0.30 m）给出"仪器判别力"，实测比值
   **1.77/1.81**（母批）、1.32/1.33（轮 I）、1.32/1.38（轮 II）、**1.25/1.25**（轮 III）——均 ≥1.15 阈值。

### 1.3 工具落点（既有代码，非新写）

`scripts/02_analysis/render_compare.py`（离线渲染 + 静态/残影分区）与
`scripts/02_analysis/dyn_probe.py`（动态分区 + 配对探针）；产物示例
`results/paper2_fulltable/evidence/fig_render_compare_*.png`。

### 1.4 评测卫生声明（CVM 呈现**必配**，见 §4 第 7 条）

按 `metrics.md` §3「评测卫生惯例」（文献会话给出的三条：无效像素处理、深度来源、对齐口径），
本协议的所有数字必须连带声明：

1. **深度来源**：`M_bad` / `M_good` 的划分与深度-L1 都用 **Bonn 数据集自带的 GT 深度**
   （非 Metric3D / DepthAnythingV2 等估计深度）；渲染侧深度用 3DGS 的**期望深度**
   （半透明基元会把背景深度混入 ⇒ 该指标对不透明度敏感，见 `verdict_dyn_probe.md` 局限节）。
2. **无效像素处理**：掩码内 **不做"无效区置 0"**——`coverage` 在各臂恒 1.000，即**没有洞**；
   渲染错的地方是**内容错**而不是缺失（母批结论 ③）。这条正是 DynaGSLAM 补充材料 §B
   警告的"置 0 作弊"的反面，应在论文中显式写出。
3. **对齐口径**：主表 ATE 用 **SE3** 对齐（RGB-D 度量主线）；**Sim(3) 尺度列已撤回**
   （见 §4 第 8 条）⇒ 论文中不得出现 Sim(3) 数字。

---

## 2. 天花板与代价（四轮放进同一张表）

**读法**：`M_bad` 上的**比值 vs P1** 越小越好；**比值 < 1 = 比"抹掉"好，> 1 = 更差**。
`n_dyn` = 插入的基元数（成本）。两数 = **gate / baseline** 两张同批地图
（**跨地图 dB 不可比，只比同地图同集比值**）。

> **⚠ 帧集不可跨轮相减**：各轮的评估帧集**不同**——母批 **16 帧**、轮 I **15 帧**（剔冷启动 f2）、
> 轮 II **12 帧**（再剔 3 个刚性退化帧）、轮 III **15 帧**（剔 f2）。本表用于看**方向与量级**，
> **不得**在轮与轮之间做差值/加总；同一轮内的臂间比较才是配对的。
> 各轮的 P1 基线也随之不同（母批 `M_bad` PSNR 20.55/20.61；轮 I 20.34/20.49；轮 III 20.34/20.49）。

| 轮 / 臂（一句话） | `M_bad` PSNR (dB) | `M_bad` 深度-L1 (cm) | **比值 vs P1** | 静态区 Δ (dB) | n_dyn | 成本 |
|---|---|---|---|---|---|---|
| 母批 **P1 抹掉**（现状，反动态范式） | 20.55 / 20.61 | 27.08 / 27.88 | 1.000 | +0.00 | 0 | 0 |
| 母批 **P2 逐帧插入（非因果上限）** | **31.28 / 31.58** | 15.30 / 15.46 | **0.565 / 0.555** | **+0.12 / +0.11** | 3,532 | 6.4% / 4.2% |
| 母批 P4 插一次即冻结 | 20.06 / 20.10 | 26.84 / 27.76 | 0.991 / 0.996 | −1.16 / −1.10 | 11,906 | 21.6% / 14.1% |
| 轮 I **P2cv 全局均值速度** | 18.32 / 18.83 | 24.32 / 24.59 | 0.911 / 0.887 | **−2.28 / −2.49** | 3,909 | 7.1% / 4.6% |
| 轮 I P2c 因果保持（控制） | 21.83 / 22.06 | 20.18 / 20.57 | 0.756 / 0.742 | −0.53 / −0.63 | 3,909 | 7.1% / 4.6% |
| 轮 II **P2cs 掩码最大连通域** | 21.00 / 21.19 | 20.16 / 20.06 | 0.730 / 0.706 | −0.67 / −0.79 | 4,234 | 7.7% / 5.0% |
| 轮 II **P2cm 全局中位速度** | **17.37 / 17.35** | 24.58 / 24.71 | 0.890 / 0.870 | **−2.73 / −2.89** | 4,234 | 7.7% / 5.0% |
| 轮 II **P2cr 刚性常扭转（主臂）** | 19.75 / 20.04 | 20.47 / 20.25 | 0.741 / 0.713 | −0.83 / −0.98 | 4,234 | 7.7% / 5.0% |
| 轮 III P2c 保持（控制） | 21.83 / 22.04 | 20.18 / 20.57 | 0.756 / 0.742 | −0.53 / −0.63 | 3,909 | 7.1% / 4.6% |
| 轮 III **P2cu 多帧并集（基元 ×5.13）** | 21.95 / 22.38 | 19.56 / 20.10 | 0.733 / 0.725 | −0.69 / −0.80 | 20,048 | 36.3% / 23.8% |
| 轮 III **P2cuv 并集 + 逐基元 KNN 速度（主臂）** | 20.65 / 21.09 | **21.18 / 21.86** | **0.793 / 0.789** | **−1.03 / −1.24** | 20,048 | 36.3% / 23.8% |
| 跨序列 **P2c（balloon）** | — | — | **0.214 / 0.184** | −0.26 / −0.19 | — | — |

**成本口径**（关卡② 第 1 次抓到我此列写错，2026-09-19）：成本 = **该行臂自身**的
`n_dyn / n_static`，其中 `n_static` 在轮 I/II/III 上**相同**（gate **55,174** / baseline **84,162**，
出处各轮 results JSON 的 `meta.<map>.n_static`）⇒ **跨轮可比**。
注意各轮的**成本判据**测的是**各轮自己的主臂**——轮 I `C4` 用 P2cv、轮 II `D5` 用 P2cr、
轮 III `E5` 用 P2cuv——**不是同一个臂**，故不能把判据读数直接当某一行的成本
（此前的写法把轮 III 主臂的 36.3% 错标到了 P2c 行上）。

**保留率判据**（键名逐条给出，便于回查；两数 = gate / baseline）：

| 量 | 轮 I（`causal_judgments`） | 轮 II（`causal2_judgments`） | 轮 III（`causal3_judgments`） |
|---|---|---|---|
| 几何保留（`M_bad`） | `C1b.retention_P2c` **0.5936 / 0.6068** ✅ | `D3.retention_bad_P2cr` 0.5826 / 0.6054 ❌ | `E3.retention_bad_P2cuv` 0.5021 / 0.4976 ❌ |
| 外观保留 | C1（全掩码口径）0.5902 / 0.5826 | `D2.retention_psnr_P2cr` **0.0475 / 0.0778** ❌ | `E2.retention_psnr_P2cuv` **0.0285 / 0.0535** ❌ |
| 速度项增益 | `C2.dl1_ratio_P2cv_over_P2c` **1.2296 / 1.2181**（>1 = 更差）❌ | 中位速度臂 PSNR 低于抹掉 | `E1` 0.9693 / 0.9775（**vs P2c**，仅作消融）❌ |
| 静态无伤 | `C3.d_static_P2c` −0.5346 / −0.6289 ❌ | `D4.d_static_db` −0.8309 / −0.98 ❌ | `E4.d_static_db` −1.0303 / −1.2425 ❌ |
| 仪器 | `C5` 1.3207 / 1.3308 ✅ | `D6` 1.3217 / 1.3756 ✅ | `E6` 1.2475 / 1.2546 ✅ |

**三句话结论（Discussion 骨架）**：

1. **空间很大**：把动态区域建出来，`M_bad` 上 PSNR **+10.73 / +10.98 dB**、深度误差**减半**
   （比值 0.565/0.555）；**全掩码口径** PSNR **+10.28 / +10.43 dB**、比值 0.577/0.561；
   连**全图** PSNR 都 **+2.09 / +2.28 dB**，代价只有 **6.4% / 4.2%** 基元
   ⇒ "反动态范式"丢掉的东西是实质的。
   **派生口径**：以上增益 = 工件 `means` 的两臂相减（如 `P2.dyn_psnr − P1.dyn_psnr`），
   **逐位可复算**。注：`NOTES.md` #24 行与 README 早期写的 `+10.29/+10.46`、`+11.00`
   属早期派生值的四舍五入偏差（≤0.03 dB，结论不变），已一并订正为可复算口径。
2. **但因果且离线的形态吃不到**：四条最省路径**全部不达标**且方向一致"越激进越差"——
   掩码连通域**无贡献**（`D1` = P2cs/P2c **1.0253 / 1.0260**）、
   中位速度**外观 PSNR 低于抹掉**（gate：17.37 vs P1 的 19.19；baseline：17.35 vs 19.09）、
   刚性常扭转把外观保留压到 **0.0475/0.0778**、
   逐基元 KNN 叠加速度后**比值劣于保持臂**（0.793 vs 0.756）。
   最关键的对照：**"插一次即冻结" ≈ 抹掉**（比值 0.991/0.996；balloon 上更差，
   静态损伤 4 dB 级）⇒ **生命周期/退役不是可选项**。
   另：**静态区代价**在每一个因果臂上都出现（−0.53 ~ −2.89 dB）= "陈旧基元停在人已离开处"。
3. **运动建模四次尝试无一可用**（`P2cv` 全局均值 / `P2cm` 全局中位 / `P2cr` 刚性常扭转 /
   `P2cuv` 逐基元 KNN），根因是**评估是像素级对齐**：把物体整体搬走而估错的动作，
   会连**原本已经对的部分**一起弄坏（F8）。这解释了"越激进越差"为何是稳定方向。

---

## 3. 瓶颈归因（本会话最有价值的产出）

来源：`evidence/diag_causal_fairness.json`（**轮 I/II/balloon 的纯重分析，`sources` 不含轮 III**）
+ 轮 III 自身的 `causal3_judgments.E7_stratified`。

| 因子 | 读数 | 结论 |
|---|---|---|
| **Δt（评估帧到最近 KF 的间隔）** | 外观保留 dt=1 **0.342** → dt=2 0.192 → dt≥3 **0.01–0.04** | 陈旧观测是**一阶**因子；KF 间隔恒 5 帧 ⇒ dt≥3 时插入的观测已"过期" |
| **KF 掩码规模**（键 `by_mask_size`，**两个指标必须分开读**） | 掩码 <中位：深度-L1 保留 **0.216**、**PSNR 保留 0.014**；≥中位：深度-L1 保留 **0.80**、PSNR 保留 **0.231**（轮 II 的 P2c） | 掩码质量是**一阶**因子。**注意**：`0.014` 与 `0.216` 属**不同指标**，此前被并写成"0.014–0.216"的区间是**错的**（关卡② 抓到，2026-09-19） |
| **拟合预算** | 各臂 loss 下降比 **0.37–0.42**（对等） | **不是**因子：失败不能归因于"没拟合够" |
| **基元数量** | 并集把基元从 3,909 → 20,048（**5.13×**），汇总口径（`E1`）只降 **3%** | **不是**因子：瓶颈不是"点太少" |
| **叠加运动模型** | 轮 III 分桶（阈值 = 15 帧 `n_dyn` 中位数 **3642**）：P2cu 几何两桶都升（差桶 0.216→**0.2902**、好桶 0.8012→**0.8478**），而 P2cuv **四个数全低于 P2c**（差桶 0.1767、好桶 0.6815） | 无可靠运动估计时，**保守（保持）优于激进（外推）** |

⇒ **落在离线探针之外的三件事**：① **每帧插入**（而非只在 KF）；② **连续优化**
（而非单帧 300 步一次性拟合）；③ **掩码的时序聚合/质量**（GTMC 在部分帧近乎失效）。
文献（DynaGSLAM）恰好三件都有机制（出处 `resources/lit_dyn_mapping/` 的 `mechanisms.md` §2 V2、
`open_questions.md` Q2 成本条、`papers/dynagslam.md` 的 Table 3 转录）。
**这是推断，不是本轮测量**——且离线还有未试的便宜变体（见 §4 第 6 条）。

**聚合口径警告**（写作时必须带上）：全集口径的保留率（`E2`/`E3`）与分桶口径（`E7`）**不可互换**——
全集上 `retention_of(means)` 与 `_retention_perframe` **数值相同**（`E3` 两法皆 **0.5021**），
把两个桶按帧数**再平均**（0.4459）既不等于全集也不等于任一桶（两桶分母不同）。

---

## 4. 口径边界与"不得越界引用"清单

1. **未测 ATE**：动态基元进入在线损失/BA 后对轨迹的影响**完全未知**（`DISCIPLINE #7` 绝对 ATE
   是第一验收标准）⇒ 以上一切**不得表述为"方法更好"**，只能表述为"该族的空间与代价"。
2. **单序列（pt2）+ 第二序列泛化（balloon）+ 单 seed**；两张同批地图**不是独立复现**
   （同序列同 seed ⇒ 只作臂间鲁棒性）。
3. **P2（天花板）非因果**：用了被评估帧自身的观测（`M_good` 上的"改善"甚至就是复制该帧输入）。
4. **跨分区/跨序列 dB 不可比**；只允许同集/同地图内的**比值**。balloon 与 pt2 的 dB **不得并列**。
5. **统计**：轮 III 分桶 n=7/8、单 seed、无方差/置信区间 ⇒ 分层读数是**观测比较**，非显著性检验。
6. **"离线已到边界"不成立**：未试的便宜变体 = 逐点速度**门控/平滑**（预注册自己写下、条件已触发
   但未执行）、退化帧回退、>2 KF 最小二乘、按 Δt 分档、掩码稳定化、换掩码源。只能说"边际收益预期低"。
7. **会场口径**（`venue_cvm.md` §6「该会场少见（做了也别指望加分）」）：分区指标在 CVM 入选样本中
   **少见 ⇒ 报了是差异化**，但该节**明确写着做了也别指望加分**；其"评测卫生"惯例见
   `metrics.md` §3，§6「呈现建议」把"无效像素处理声明"列为**必配**。
8. **Sim(3) 尺度列已撤回**（`results/paper2_fulltable/evidence/verdict_sim3_scale.md`），
   不得与本文件并列使用。
9. **母批的预注册文本缺陷**（不追溯改判）：判据③原写双侧 `|Δstatic| ≤ 0.25 dB`，实测为**正向**改善；
   若为负向应读作"不劣化 ≤0.25 dB"（`verdict_dyn_probe.md` 局限节）。
10. **P4 成本未配平**（11,906 = P2 的 3.37×）⇒ 其静态损伤**方向可信、幅度待配平后重测**
    （判据机 `2_motion_necessity.cost_note`）。

---

## 5. 英文 Discussion 段候选（两段，可直接改写使用）

**段 A——评测协议（差异化点）**
> Most dynamic-scene GS-SLAM papers report frame-wide rendering numbers, which cannot separate
> "the dynamic content is missing" from "the dynamic content is present but wrong". We report a
> *geometry-defined partition*: using ground-truth depth and a single neutral arm (the
> mask-everything baseline), we split the dynamic region into pixels where that baseline is
> actually wrong by more than 10 cm (`M_bad`) and pixels where it is already correct (`M_good`),
> and we report appearance and depth metrics per partition. Because the partition is defined
> without reference to the arm being evaluated, it is identical across arms and admits paired
> ratios; because the baselines differ per partition, we compare only within a partition, and we
> report the area fraction of `M_bad` (5.8% on one sequence, 8.7–9.2% on another) alongside every
> number.

**段 B——代价与瓶颈（边界刻画）**
> Building the dynamic content out is worth a great deal in principle: an oracle that inserts
> primitives from the evaluated frame itself raises `M_bad` PSNR by 10.7 dB and halves the depth
> error, at 6.4% additional primitives, and improves even the frame-wide PSNR by 2.1 dB. Our
> causal, offline attempts recover none of it. Freezing what was inserted once is no better than
> erasing (depth-error ratio 0.99; on the second sequence it is worse and much more harmful to the
> static region), so a lifecycle is a required part of the mechanism rather than an optimisation.
> Four motion models fail in the same direction, and a stratified analysis locates the binding
> constraint elsewhere: retention collapses with the age of the observation (appearance retention
> 0.34 at Δt = 1 versus 0.01–0.04 at Δt ≥ 3) and with keyframe mask size — below the median
> mask size depth retention is 0.22 and appearance retention is 0.014, against 0.80 and 0.23
> above it — while fitting budget is equal across
> arms (loss reduction 0.37–0.42) and a 5.1× increase in primitives buys 3%. We therefore report
> the ceiling and the cost as a boundary characterisation rather than a method contribution; the
> partition protocol above is offered as the measurement contribution.

*(段 A 的 5.8% / 8.7–9.2% 见 `manifest.json` 的 `bad_subset_decomposition` 键与
`verdict_dyn_probe_generality.md`；段 B 的每个数字都能指到 §2/§3 的键。)*

---

## 6. 与论文 2 主张的关系（供写作会话决策）

- 本文件**不改变**论文 2 主线（跟踪侧 SWBA + 门控的 ATE 贡献）；
- 两种用法：**(i)** §1 作为方法学贡献（分区指标协议，可直接主张）；
  **(ii)** §2/§3 作为 Discussion 的边界刻画，**必须连带 §4 的口径边界**，且**不得**写成方法优势；
- **若要在论文里加一句"该族值得做"**：只能写"该族空间很大但离线不可达、需要在线机制"，
  并必须同时给出两条反证——静态区代价（−0.53 ~ −2.89 dB）与"成本不是瓶颈"（×5.13 → 3%）；
- 候选在线机制的立项草案：`resources/notes/transient_map_online_prereg_draft_2026-09-19.md`。
