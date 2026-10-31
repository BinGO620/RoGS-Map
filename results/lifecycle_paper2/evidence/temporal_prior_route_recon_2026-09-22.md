# 时序先验路线立项前置核查：仓内占位 + 文献占位（2026-09-22）

**性质**：D2-006（新机制族立项"时序先验路线"）的前置核查工件（用户 2026-09-22 拍板立项）。
**核查对象**：用"占据时序记忆"（这块区域刚被人走过 ⇒ 区域内低 α 基元应当视为被续命的残影候选）
替代深度一致性证据，识别 pt 家族"深度一致再占据"型残影。**本文件只做占位核查，不含机制设计**
（设计与新 prereg 属立项后的第一步）。

## 1. 仓内占位：**干净**（零实装、零证伪、零 run）

Explore 扫描（全仓 `*.py/*.md/*.yaml`，关键词族：temporal prior/时序先验/appearance prior/
recency/last_seen/staleness/occupancy prior/person permanence/time since 等）：

- **零命中实装**：无任何"占据时序记忆/last_seen"类机制代码或实验记录；
  `NOTES.md` 实验清单时间线无此类条目。
- **想法的仓内出处**：`l2_kill_mechanism_postmortem_2026-09-22.md` §4.3 已把该路线点名为
  pt 家族唯一可行的剩余路径（理论依据可直接引用）。
- **近缘已实装方向（均非本想法，立项时须在 related-work/设计里区分）**：
  - **T3 语义 α 覆盖**（判负 2026-08-20"误杀 83.8%"）：外观/语义先验**即时硬改写 α**——
    机制形态与本想法（时序记忆软证据）不同；且其排除依据依赖已失效 gtmc 掩码
    （D1-006 降"待复核"）⇒ **护栏 1：不得把 T3 当作"先验路线已证伪"的证据**。
  - **ReliabilitySignal**（`utils/reliability_signal.py`，flow_raft 消费）：运动共识信号，
    非占据时序记忆；且 flow 在 Bonn 手持序列被自运动主导（recall 0.001–0.84）——
    时序先验恰好是绕开 flow 缺陷的替代通道。
  - **DeferredCommit**（`utils/deferred_commit.py`）：确认机制仍走深度证据 C±，
    与时序先验正交（可复用其"延迟确认"骨架）。
  - **freshvac recency window**（`utils/eval_utils.py:710,942`）：评估指标侧的 recency，
    不是地图生命周期机制——同一词在两个语境，避免混淆。
- **护栏 2**：postmortem 已证明任何以深度一致性为证据的机制识别不了 pt 家族 ⇒
  新立项判据必须**避开深度一致性证据通道**（这是机制设计的硬约束，也是与现有
  gate/carve/exit 家族的清晰分界）。

## 2. 文献占位：**近邻密集、目标缝隙未见占位**（截至 2026-09-22 检索）

检索源：paper-search（Semantic Scholar/arXiv）+ Tavily 三轮定向（recency/last-seen/
lifelong map maintenance/object permanence/amodal transient × 3DGS SLAM）。

- **赛道整体拥挤**（与 2026-09-20 机制调研结论一致）：动态 3DGS-SLAM 的动态移除主流
  = 语义掩码/不确定性（WildGS-SLAM CVPR'25、GARAD-SLAM、DL-SLAM、DAGS-SLAM 的
  per-Gaussian 运动概率）/光流（Flow4DGS-SLAM）/4D 时序建模（D4DGS-SLAM、4DTAM、
  CAD-SLAM 的 temporal Gaussians）；滑动窗口多帧聚合（MDPI Appl. Sci. 15(8):4190）。
- **长期地图维护线存在但驱动力不同**：LT-Gaussian（arXiv 2508.01704，自动驾驶地图更新，
  跨 session 变化检测）；DGOMapping（4D 多智能体，"growth–forgetting–cleanup"记忆调节
  ——**近缘度最高的一篇**，但其 cleanup 由渲染误差/跨 agent 一致性/时间正则的统一目标
  驱动，不是"行人再占据"的瞬态残影问题，且是多agent 4D 场景）；SLAM-RAMU 等 LiDAR
  lifetime 线。**未见**以"区域级占据时序（last-seen）作为软先验来识别深度一致再占据残影"
  为核心主张的论文。
- **瞬态移除线**：T-3DGS（arXiv 2412.00155，离线重建、掩码传播路线）；PersistGS
  （CVPR'26W，遮挡期 object permanence 由刚体仿真恢复，物体级非区域级）。均非在线
  SLAM 地图生命周期场景。
- **占位判定**：目标缝隙（**区域级 last-seen 时序先验 ∘ 在线 3DGS-SLAM 的 α 生命周期**）
  在本次检索深度下未见占位；但 DGOMapping 的"遗忘-清理"目标与 CAD-SLAM 的
  cross-time 不一致检测是**最近的两个邻居**，机制设计时必须正面区分（它们是本想法
  的天然 baseline/related work）。
- **检索深度声明**：本轮为定向占位核查（~4 轮检索、摘要级判读），**不是**系统性综述；
  正式立项文档写作时建议按"查论文流程"补一轮全文级核查（含 DGOMapping/CAD-SLAM
  方法节精读），406/冷却时换源。

## 3. 立项可行性结论

- **仓内**：干净，且有 postmortem 作理论动机 + 两条护栏清晰。
- **文献**：缝隙存在（摘要级判定），近邻两条（DGOMapping/CAD-SLAM）需正面区分。
- **建议立项形态**（供 prereg 起草参考，非本文件决定）：L1 最小验证 = pt 单序列 ×
  {对照 = L1b gate 臂已有读数}，判据沿用 freshvac Δ 门（门槛 1.19cm 家族），负对照
  继续用对调两臂；机制 default-off。
- **R7 注意**：这是**新机制族**（非证据门控族重试），R2"每族一次"的时钟重新起算；
  但若 L1 失败，时序先验族同样按 R2 关闭——立项即承诺这一点。
