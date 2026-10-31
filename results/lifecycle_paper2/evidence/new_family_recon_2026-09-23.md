# 新机制族立项依据调研（2026-09-23；零 GPU；三路：仓内实验/resources/联网）

> **性质**：D2-008 立项的依据调研（用户指示先调研后立项，方案待用户过目再定）。
> 核心问题：四条 α 通路全部关闭后，**绕开几何门的删除**在文献与仓内占位如何？
> 本文件只陈述依据；候选方案与建议在 §4，拍板在用户。

## 1. 仓内实验资源盘点（什么已死、什么没试过）

### 1.1 删除相关机制的判决全景（查漏完成）

| 机制 | 判决 | 关键理由 | 锚点 |
|---|---|---|---|
| reset（可逆 α 复位） | box 族有效/动态族不成立 | 绑 in_front（z<obs_at−0.05） | verdict_L1.md; lifecycle_pilot |
| carve（自由空间硬剪除） | 判负 | pt α 钉 0.2199>0.20 结构性不可达；crowd 转化 0.44% | l2_kill_mechanism_postmortem §1/§3 |
| evidence_gate | 关闭 | carve_total 仍≈0，改善非 carve 路径 | verdict_L1b_gate.md:64-107 |
| occupancy memory | 关闭 | warm∩(α<guard) 时间窗错配 | verdict_L1c_occupancy.md |
| gate×occ 叠加 | 关闭 | **穿阈≠删除**：a_min 钉 0.1845 达 60+ KF 而 carve=0 | verdict_L1d_stacked.md |
| T3 语义覆盖 | **待复核**（原判负依据失效） | join 失效 gtmc 掩码；verdict 文件已不在仓内 | NOTES:423-425; mask_incident §3 |
| transient_map+Tfit | 本族永久关闭 | 净效应归零（+0.10dB 带内）；拟合抬存活瞬态不透明度⇒ghost +1.78 | verdict_tfit_screen §4 |
| embrace_dyn 因果轮 | NO-GO | 退役被证明必需（静态区 −0.53dB）；运动建模 4 连败 | verdict_dyn_probe_causal3 |
| M1/M2 子图 | 关闭（M1 待复核） | 与删除无关但同批排除 | NOTES:451-470 |

**几何门语义核实**（slam_backend.py:1049 + alpha_lifecycle.py:51-70）：`obs_at` = 当前帧
观测深度图在基元投影像素的采样；z = 基元自身深度。人走后背景与残影深度一致
⇒ z≈obs_at ⇒ in_front 恒 False ⇒ reset/carve/T3 结构性不触发。**这就是四通路共同死因**。

### 1.2 从未试过的角度（调研 agent 综合推断，7 条）

① 事件触发式 carve（verdict_L3.md:99 自己写过"仅在检测到稳定腾空残影时才剪除"，从未实施）；
② **渲染残差通道作退役证据**（postmortem §4.3 点名"外观/语义先验是唯一能识别深度一致再占据的信号"，但从未用渲染误差本身）；
③ 软删除+可复活（去几何门的 α 衰减-复活；T3 硬改写、transient_map 谱系硬删均不同形）；
④ **fill 侧信号反向作删除触发**（detect_vacated_pixels 只用于补洞方向，"被腾空"证据从未反哺 retirement）；
⑤ per-Gaussian 龄期（last-observed age；occupancy 是 voxel 级区域记账，粒度不同）；
⑥ CubifyGS 式物体级版本（仓内从未实装）；
⑦ 残影合并/吸收（全仓空白）。

**硬约束（写进未来 prereg）**：任何以深度一致性为证据的删除都无法识别 pt 残影
（postmortem §4.3）；T3 不得引用为"先验路线已证伪"。

## 2. resources 文献资源（四族非深度门删除信号）

| 信号族 | 代表 | 机制 | 与我们的窄面差距 |
|---|---|---|---|
| A 可观测性 | DynaGSLAM Cond.1/2 | warp 后无邻近观测→删；寿命阈值 | 只管**动态侧**瞬态；残影人走后已静止且"仍被渲染观测到"⇒ Cond.1 同型"门不触发"失败 |
| B 记忆动力学 | DGOMapping | m←m+grow·support−forget·m，m<τ 死 | 多智能体、小时/天级；我们是单智能体秒级 |
| B' 统计渐衰 | MoPe 式12 | 动态观测比 r=h_dyn/h_obs → α←max(ρα, α_min) 软删 | 最接近！但 anti 极（动态不进图）、无硬除、单目 iPhone 语境 |
| C 占用证据 | CubifyGS | ray-cast Free 证据→存在概率<τ_vanish→剪除 | 物体级、需检测器+资产库、GT 位姿、非 SLAM 环路 |
| D 时间窗 | STG/RiGS/RU4D | β 窗外 σ→0 | 与 L1c 已关形态同源 |
| E 语义检测器 | BDGS/DL-SLAM/GARAD | YOLO 先验/实例概率/渲染惩罚 | 需检测器或实例结构 |
| F 光度残差 | DGS-SLAM/CAD-SLAM | 跨 KF 光度一致掩码 / I_err+D_err 双残差 | CAD-SLAM 的 D_err 仍是深度一致残差；**I_err（光度）通道与深度门正交** |

**占位结论**：非深度门删除有四族占位，但**无一落在"单智能体+秒级+基元级+无检测器+在线 SLAM 环路+再占据场景"窄面内**；四族无一报告删除机制对 ATE 的净效应；vacated/freshvac 分区评测文献零命中（metrics.md §2 机械 grep 验证）。gap 卡需补：gap #21（深度门不可达场景的非深度门删除）+ mechanisms.md L10/L11 两行（占用证据删除、误剪恢复）。

## 3. 联网查询（2026 下半年增量；tavily 高级检索多轮）

- **DL-SLAM**（arXiv:2607.01860, ICRA 2026 后续版 09-22 更新）：像素级概率提升到 3D 聚合成**对象级**动态概率，超阈连续 3 KF ⇒ 整实例剪除。信号=语义实例聚合，非基元级、非时序占据；与窄面不同但**"多 KF 确认后删"的确认协议同构**。
- **UP-SLAM**（arXiv:2505.22335, ICRA 2026）：概率八叉树管理基元（免手工阈值初始化+剪枝）+ 多模态残差不确定性估计（免语义标签的开集动态过滤）。**无逐基元时序删除先验**；其"residual 融合"与我们 ②渲染残差通道近缘但用途是 2D 过滤不是 3D 退役。
- **SPIN-SLAM**（IROS 2026 LBR）：tracker 的 pose/depth/渲染**时序残差**复用为 mask 信号（免 DINOv2）——证明"渲染残差通道可行且便宜"的旁证，但仍是 2D mask 不是基元退役。
- **VBGS-SLAM**（arXiv:2604.02696）：变贝叶斯闭式更新，π 不变的组分重生成——统计式种群管理，无再占据语义。
- **EliGSiR**（arXiv:2609.20348）：持续建图的算力受限种群管理（MCMC relocation/replacement），非动态清理。
- 未发现任何 2026 新工作落在窄面内；也未发现"删除机制对 ATE 净效应"的报告——两条文献空隙仍在。

## 4. 汇总：立项候选的依据基础（方案待用户拍板，本文件不拍板）

**证据链**：四通路共同死因 = 删除依赖几何门（in_front 在续命场景恒 False）；
文献四族占位均不在窄面；仓内 7 条未试角度中与死因直接对位的是：
- **②渲染残差通道**（postmortem 点名的唯一可行信号 + SPIN-SLAM 旁证"残差通道便宜可行"）；
- **④fill/腾空证据反哺删除**（vacated 仪器仓内成熟、文献零命中）;
- **③软删除+可复活**（与 MoPe B' 统计渐衰最近缘，需正面区分）;
- ⑤ per-primitive 龄期（与 DGOMapping B 最近缘，需正面区分）。

**候选空间与代价预估**（L1 阶梯 3 run ≈40min/项；实装 1-2 天/项）：
A) 暖区持续性剪除（warm+N KF 持续 α 低 → 直接 prune，无几何门）——实装最小，直击死因；
B) 渲染残差退役（I_err 持续高的基元退役）——信号最新，安全性论证最难；
C) 腾空证据反哺（vacated 检测触发对区域内低 α 基元的硬删）——仪器成熟；
D) occ v2 per-primitive identity——预登记候选，成本最高（10 同步点）。
组合风险：A 与已关闭的"occupancy 衰减"共享 warm 概念但**动作不同**（衰减 vs 剪除），
须在 prereg 里正面划界；B/C 均为"事件触发式删除"，是 verdict_L3.md:99 未实施条款的落实。

**流程约束（沿既有纪律）**：立项呈报 D2-008 一页纸 → 用户拍板 → prereg 判据先锁
（判据同源：freshvac ∀3 负 ∧ |mean|>max(1.19,off_sd)；约束门同 L1b；诊断预测带工件键；
入口/出口计数器语义区分）→ default-off 实装 + 单测（净静态保护证明照 L1c 形状）→
配置生效四层 → L1 3 run 双卡 → 渲染清单同 commit 列全 6 seed → 判据机 → 关卡①先于落盘
→ verdict 三件套。L1 失败 ⇒ 族按 R2 当场关闭（不追加不调参），写作轨接管
（CVM 摘要 10-23/全文 10-26，写作窗口已 reserves 9/29 起全速）。

## 5. 调研产物的证据层级自律

- 本地卡：CubifyGS/DGOMapping 原文级；DynaGSLAM/MoPe 原文级；BDGS/GARAD/DGS 8 条摘要级（正式引用前须回源）；
- 联网：DL-SLAM/UP-SLAM/SPIN-SLAM/VBGS/EliGSiR 摘要级（摘要逐字，未读全文）——立项一页纸引用时标注层级；正式 prereg 前对入选近邻做全文级核查；
- T3 判负依据失效（掩码事故波及）已由 D1-006 登记，本调研未翻案、只标注。
