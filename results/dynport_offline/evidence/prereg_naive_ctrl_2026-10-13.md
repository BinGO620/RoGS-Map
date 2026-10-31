# 预注册：朴素插入对照臂（NaiveCtrl）— 2026-10-13

> **性质**：论文 2 模拟审稿 P0-1（§6↔§7 口径矛盾）的**消融对照**，不改变主判据。
> **账本**：**D1-037**（R1 机械应用 + R8 执行全委；用户 2026-10-13 拍板"跑"）。
> **上游**：`simulated_review_2026-10-13`（P0-1）；`prereg_dynport_offline_L1.md` §12 v4（出口口径）。
> **判据先锁**：本文件落盘（commit 先于实装/派发），先声明后实装。

## 1. 动机（一句话）

§6 的"无运动插入挽回 0.80–0.93"是 **GT 深度 oracle 探针**（P2c/P1 残差 0.22–0.38）；
§7 算子（传感器深度 + 生命周期 + S5）J2 = 0.23–0.61。审稿人必问：**完整算子是否优于
同口径的朴素插入？** 本对照用**与算子逐位同口径**（传感器深度 / MaskRCNN 掩码 / 同 KF 日程 /
同帧位姿渲染 / 同 fit）的"纯朴素插入"臂回答，把差异归因于**生命周期管理 + S5 结构保护**本身。

## 2. 臂定义（单变量：生命周期 + S5）

| 件 | R1（完整算子，既有） | Naive（本对照） |
|---|---|---|
| 底图 / KF 日程 / 掩码源 / 深度源 / stride / fit | 同 | **同**（`repair_map.py` 同管线） |
| 决策核（KNN 复用 / Cond1 / Cond2 / cap） | 开（DynPortBuffer） | **关**：逐 KF 全量插入为新基元 |
| S5（投影掩码剪枝 + 尺度夹回） | 开（默认） | **关**（与 R1 隔离变量） |
| 静态层冻结 / 快照 / 合并 PLY | 同 | 同 |
| 输出形态 | output① 4D 层序列 | 同（judge --samepose 可判） |

**实现**：`repair_map.py` 加 `--naive` 开关 —— `naive=True` 时：
1. 不构造/不调用 `DynPortBuffer`（无 Case1/Cond1/Cond2/cap）；
2. 逐 KF 把 `unproject_mask` 的点**全部** `omap.insert(pts, cols, 新 lineage)`；
3. 跳过 `_suppress_out_of_mask` 与 `_clamp_dyn_scale`（`s5_*` 落 False）；
4. fit / 快照 / 合并 PLY / counters 照旧（counters 走简单计数，J5 不适用本臂）。

## 3. 判据（先锁；回答"算子是否优于朴素"）

主读数 = **samepose 出口键**（`judge_dynport.py --samepose`，与 §12 v4 同一仪器）：
- **J1**：dynamic-region PSNR gain（vs erase 底图），门槛 ≥ +2.5（与主判据同）；
- **J2**：depth-error ratio（vs erase），门槛 ≤ 0.70（与主判据同）；
- **J3**：static-region ΔPSNR ∈ ±0.25（与主判据同）。

**对比判据（本件新增，仅作对比不作 PASS/FAIL 主判决）**：
- **C1（算子的增量）**：`ΔJ2 = J2(R1) − J2(Naive)`（同序列同 seed 配对；J2 越小越好）
  —— ΔJ2 < −0.05 且 J1(R1) ≥ J1(Naive) − 0.5 ⇒ **生命周期 + S5 带来可测增益**（算子必要）；
  - 若 |ΔJ2| ≤ 0.05 ⇒ 算子 ≈ 朴素 ⇒ 论文 §7 改述为"可行性 + 4D 层形态 + 静态零损伤"，
    朴素插入作消融行并陈；
- **C2（代价面）**：Naive 的 `n_dyn` 峰值 vs R1（生命周期是否控制基元量）；报数不判。
- **C3（J3 保护）**：J3(Naive) vs J3(R1)：朴素无 S5 ⇒ 若 J3(Naive) 破 ±0.25 而 J3(R1) 过，
  即证明 **S5 的保护作用 = 算子相对朴素的关键增量**（此时 ΔJ2 若为负，归因于 S5 而非生命周期）。

**诚实边界**：本对照是**单变量于生命周期+S5**（同一传感器深度/掩码/位姿/拟合预算），
**不是** §6 P2c 探针的复现（P2c 是 GT 深度 oracle，口径不同，禁与 P2c 直接混比）。

## 4. 规模

3 序列（crowd2 / balloon2 / person_tracking2）× seed0 × {Naive} = **3 run**（R1 复用 L1_v4 存量，
零重跑）；离线、单卡串行（计时不作判据，但遵循纪律）。机器 = 本地 2060 或远程 3090（空闲者）。

## 5. 处置（先锁）

- 判读机写（`judge_naive_ctrl.py` 从 samepose JSON 汇总，零手抄）；
- 结论落 `evidence_naivectrl/naive_ctrl_2026-10-13.md` + `manifest_naive_ctrl.json`；
- 论文 §7 按结果改述（C1/C3 决定叙事）；**无论结果，§6 的 oracle 标签与 §7 的可实现标签都必须
  在论文里显式分层**（本次审阅 P0-1 的文本修复，与实验结果解耦）。

## 6. 已知坑（防重蹈）

- 坑① 链式赋值：判读脚本禁 `arr[mask][idx]` 双层索引写（历史 bug）；
- 坑② 掩码源：`_offline_mask` 走 MaskRCNN（方法输入），judge 用 canonical（评估分区）——
  两源分离，勿混；
- 坑③ 位姿：一律 `--samepose`，禁 `--causal`（快照位姿混杂，§12 v4）；
- 坑④ counters：Naive 无 DynPortBuffer ⇒ `dynport_counters.csv` 仍须落（简单逐帧计数），
  但 **J5 不适用于 Naive 臂**（无生命周期计数语义），collect 时须标注。
