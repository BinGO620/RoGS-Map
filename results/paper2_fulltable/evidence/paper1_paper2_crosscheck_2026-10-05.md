# 论文 1 ↔ 论文 2 数字交叉核对表（2026-10-05，零 GPU）

> **账本**：D2-026 写作轨；回应关卡② G2-M4。**性质**：口径核对（防 salami-slicing / 自引混淆 / 数字混引）。
> **用途**：论文 2 §3 "component provenance" 小节的数字依据。

## 1. 核心关系（一句话）

**论文 2 的 Tab.1 首列（"Base"）= 论文 1 的完整方法**（论文 2 的 baseline 臂配置
`r33_rebase_baseline_*.yaml` 的 `method_from` 指向 `combined_prune/method.yaml`，仅关 SWBA/回环）。
⇒ 论文 2 关于"ours vs baseline"的任何表述，**本质是"论文 2 相对论文 1"**。

## 2. 组件 provenance（哪个来自论文 1，哪个是论文 2 新增）

| 组件 | config 键 | 来源 | 论文 2 处置 |
|---|---|---|---|
| R robust reweighting (Huber δ=0.1) | `RobustTracking` | **论文 1** | 如实标"继承" |
| L reliability signal | `ReliabilitySignal` | **论文 1** | 继承（gate 只阈值化它） |
| K keyframe coverage (gap_cap=5) | `DynamicKeyframe` | **论文 1** | 继承 |
| D lineage lifecycle (deferred/prune) | `DeferredCommit`+`Mapping.lifecycle_mode` | **论文 1** | 继承 |
| 语义掩码 (MaskRCNN) | `SemanticMask` | **论文 1** | 继承 |
| SWBA 窗口光度 BA | `SWBA` | **论文 2 净增** | 本文贡献（但见 §3 边界） |
| LoopClosure | `LoopClosure` | 论文 2 净增 | **但 Bonn ≈ no-op**（如实披露） |
| gate (static_conf 阈值) | `SWBA.swba_max_static_conf` | 论文 2 净增 | 作消融 |
| **地图 codec + 存储刻画** | — | **论文 2 净增（D2-025）** | **本文主贡献之一** |

## 3. 数字一致性核对（论文 1 主表 vs 论文 2 引用）

**论文 1 事实（从 `papers/MMM2027_RoGS-SLAM_submission.pdf` 抽取，2026-10-05）**：
- 论文 1 = **测量/分析型论文**（自述"contributions are the measurements that bound this result"、
  "claim no state-of-the-art accuracy"）——**与论文 2 v2 的定位同族**（这点很重要：论文 2 不是特例）。
- ⚠ **面板不同**：论文 1 主表 = **4 个 BONN 动态场景**（Table 1："four BONN dynamic scenes"）；
  论文 2 主表 = **7 个 BONN 序列**。
- 论文 1 头条：crowd 场景 combined **2.3 / 2.2 cm**（backbone 漂移 86.5 / 147.5 cm）；4.0 GB 显存。

| 项 | 论文 1（MMM 投稿件，4 场景） | 论文 2（r33_rebase 同批，7 序列） | 一致性 |
|---|---|---|---|
| pt1 ATE | ~7.83cm（旧批，`strategy_decision` 引用） | base 11.31 / gate 7.95（R33 同批） | ⚠ **不同批**⇒ 禁引 7.83 |
| crowd | 2.3 / 2.2 cm（combined） | base 2.23 / gate 2.32 | ✅ 同量级（不同批，须并列标注） |
| 场景数 | **4** | **7** | ⚠ **不同面板**，禁混算 |

**规则（先锁）**：
1. 论文 2 **只引 r33_rebase 同批数字**（`tables_paper2_preview.md` / `tab*.tex`）。
2. 引用论文 1 的绝对数字时**必须注明"论文 1 批 / 4 场景"**，不与论文 2 同批数字混排。
3. `7.83`（pt1）等旧批数字**不得**出现在论文 2。
4. **论文 1 与论文 2 的场景面板不同（4 vs 7）⇒ 两表不可合并、不可逐序列对比**。

## 4. 待补（若需要）
- [ ] 从 `papers/MMM2027_RoGS-SLAM_submission.pdf` 抽取论文 1 主表逐序列 ATE 入本表
      （当前 §3 只填了 pt1 一个代表值；抽取为机械工作，不重跑）。
