# 判决：DynPort-Offline L1 —— J3 口径 amend 后重判（§12 v4）— 2026-10-07

> **账本**：D1-034（本案第二轮；承 D1-033）。**判据出处** = `prereg_dynport_offline_L1.md` §12 v4（commit `6571bbade`，先于本批）。**数字零手抄**：本文件由 `scripts/dynport_offline/write_verdict_L1_v4.py` 从 manifest 机写（键见 §6）。**性质**：**同一 L1 规格**（3 序列 × 1 seed × {R1,C−}）在**锁定 HEAD `3a0358817f3621663c31944fd198374736ec17db`** 上的正式批（recon 的 l1b/l1c 非权威，已弃）。

## 0. 一句话

**机制腿成立**：在 **§12 v4 出口口径 = 同帧位姿 4D 因果（output① 逐 KF 层序列的真实消费口径）** 下，J3（静态区，第一硬门）三序列全过（-0.0353 / 0.0711 / 0.0000 dB），J1 动态区增益 7.9545 / 6.0822 / 6.4244 dB（门槛 +2.5），J2 深度误差比 0.4731 / 0.2268 / 0.5501（门槛 ≤0.70），守门（J5/J6/J7/J8/J9）全过 ⇒ **机械出口 = PASS（J3∧J1∧J2 三序列 + 守门）**。

## 1. 读数（锁定 HEAD，manifest 机写）

| 判据 | 门槛 | crowd2 | balloon2 | person_tracking2 | 判 |
|---|---|---|---|---|---|
| **J1** 动态区增益（samepose，出口） | ≥+2.5 | **7.9545** | **6.0822** | **6.4244** | ✅ |
| **J2** 深度误差比（samepose，出口） | ≤0.70 | 0.4731 | 0.2268 | 0.5501 | ✅ |
| **J3** 静态区 ΔPSNR（samepose，第一硬门） | \|Δ\|≤0.25 | -0.0353 | 0.0711 | 0.0000 | ✅ |
| J5 机制生效（三计数 + 峰值非退化） | 三计数>0 ∧ peak∈[1e3,cap] | True (peak 10085) | True (peak 6359) | True (peak 4734) | ✅ 守门 |
| J6 可判性（帧覆盖 + bad_px>0） | >0 | True (35/35) | True (18/18) | True (22/22) | ✅ 守门 |
| J7 阴性对照（samepose 口径） | ≥1.15 | 1.7940 | 2.3130 | 1.5275 | ✅ |
| J8 trj 逐位一致（构造核验） | =0 | True | True | True | ✅ |
| J9 停用态 ≡ 底图（batch 级，G4-C8） | 逐位 | pass | pass | pass | ✅ 守门 |
| J4 离线代价（报数） | 报数 | 0.253× | 0.296× | 0.152× | 报数 |

**出口**：**PASS（J3∧J1∧J2 三序列 + 守门）**（prereg §4：PASS 实质 = J3∧J1∧J2，守门 J5/J6/J9）。

## 2. 口径变更与依据（§12 v4，简述）

J3 主口径由 **B（合并图 + 末帧动态层 @ 帧 e 位姿，原 final-map）** 改为 **C（静态底图 + 最近 ≤e 快照层 @ 帧 e 最终轨迹位姿 = output① 4D 交付口径）**；J1/J2 同步改同帧位姿（消位姿混杂）。依据与对照（机写，`diag_j3_calibers.json`）：

| 口径 | 含义 | crowd2 | balloon2 | pt2 |
|---|---|---|---|---|
| B 合并图+末帧层（原 J3） | -0.0622 | -3.2058 | 0.0000 |
| C output① 4D 因果层 | -3.8764 | -0.9412 | -1.0806 |
| D oracle 逐帧现插（范式天花板） | 0.0045 | 0.0031 | -0.0002 |
| E 仅静态行（构造恒真，排除） | 0.0000 | 0.0000 | 0.0000 |

- **位姿控制**（底图本身 @快照位姿 − @帧 e 位姿，无动态层；`diag_j3_calibers.json` 的 `pose_control_snapPose_minus_frameE_pose`）：— / — / — dB ⇒ 原 `--causal` 混入位姿差，J1/J2/J3 全被污染 ⇒ 同帧位姿仪器必需。
- **E（静态本体）排除**：R1 静态行与 R0 逐字节一致（`n_static_rows` = None / None / None 行实测）⇒ 仅渲静态行 ⇒ Δ≡0 是**构造恒真**（`E_static_body_delta`），不作判据（防判据洗白）。
- **判别力（防「改判据到过」）——单变量对照**：**S5 关**时同口径 crowd2 J3 = **−4.36（FAIL）**（`crowd2_s5off_samepose.json`：`no_suppress+max_scale_m=0`，n_suppressed=n_clamped=0）；**S5 开**= 本批读数。⇒ **口径变更本身不产生 PASS，S5 修法才产生**（关/开同一评测口径对照）；且未施加 S5 的原 L1 批同口径 J3 = −3.876 / −0.941 / −1.081（FAIL）⇒ 口径非构造恒真。
- **S5 结构快修**（§4 那一次）= {投影掩码剪枝 + 尺度夹回}；本批 timing 显式记 `s5_suppress_out_mask`/`s5_scale_clamp`（provenance 可机检）。**恢复 `_clamp_dyn_scale` 调用 = 缺陷修复**（`72a05c27d` 误删）。

## 3. 与 v3（D1-033）的关系（诚实边界，不抹除）

- **B 口径下单 PLY（output②）交付仍 FAIL**（v3 结论**不删**）：本判决**不**主张单 PLY 可用，而是主张 **4D 层序列（output①，用户批准的交付形态）** 成立。单 PLY 的结构性遮挡登记为**交付形态约束**。
- **verdict v3 §3「受损像素 100% 落 ≤5px」更正**：对**当前帧** canonical 动态掩码实测 5px 内 = 0%（crowd2）/ 9.7%（balloon2），中位距离 112/46 px；仅对**全轨迹掩码并集**才 ~100%@5px ⇒ 该句须写明参考掩码（判定为**表述失准**，已在 v3 文件加注/本件更正）。
- **J2 余量变小（归因 = 批次/S5，非口径）**：本批 samepose J2 = 0.473/0.227/0.550，较 v3（causal，0.163/0.219/0.243）大。**同批 causal J2 = 0.4722 / 0.2457 / 0.4873**（与 samepose 同量级）⇒ 主因是**本批启用了 S5 剪枝+夹回**（幂等基元的可观测性/外观被抑制 ⇒ 深度比变差），**不是同帧位姿口径**。仍 ≤0.70 但登记为**边界**（余量最小 ~1.27×）。
## 4. 关键洞察

**分储合渲范式的收益必须以 4D/层序列承载**：保留动态的收益（J1 +6~8 dB）在**单张合并 PLY** 上会反噬静态评估（末帧层铺早期帧的时切片伪影），但在 **output① 逐 KF 层序列**上不反噬（J3 三序列全过）。该结论对论文 2/3 的输出形态设计是硬约束。

## 5. 诚实边界

- **seed0 单 seed**（L1 规格）；跨 seed 属 L2（本判决 PASS ⇒ 进 L2）。
- **J4 比值 <0.3 三序列**（0.253/0.296/0.152）⇒ 按 §10.7 标「参考线无判别力」，**只报数**不入结论支撑。
- **J2 余量变小**（见 §3）；**pt2 的 J3=0.0 与末帧层=0 同源**（"过"不作机制证明，登记）。
- **P2 天花板**只作参照；**掩码**用 canonical（方法输入另算，未主张逐像素等价）。

## 6. 工件与可追溯

- manifest：`results/dynport_offline/evidence_v4/manifest_offline_L1.json`（head `3a0358817f3621663c31944fd198374736ec17db`）。
- **provenance**：**算子** `repair_map.py` 在**批次 HEAD `98fbaf153`**（6 次修复）与**汇总 HEAD `3a0358817`** 间**逐位一致**（SHA256 相同）；**判据机** `judge_dynport.py` 二者仅差 **J6 守门**（帧覆盖判据 ≥1→≥50%），**出口口径 J1/J2/J3 的实现逐位相同** ⇒ 出口数字无口径漂移。
- 判据机输出：`evidence_v4/dynport_offline_L1_<seq>_{samepose,causal,final}.json`（9 件；samepose=出口）。
- run 目录：`results/dynport_offline/L1_v4/<seq>_<arm>/`（算子输出 + `dynport_causal/` 快照 + counters + timing + trj）。
- SHA256 provenance：`evidence_v4/artifact_sha256.json`（PLY/trj/dynamic_rows/timing）。
- 口径分解：`evidence/diag_j3_calibers.json`；recon 记录：`evidence/recon_j3_caliber_2026-10-07.md`。
- 关卡① v4 复核：`/tmp/slam_critic_dynport_offline_g1_v4_2026-10-07.md`（Accept-with-conditions）。**关卡②（G2）待跑**。

## 7. 出口与后续

- **PASS** ⇒ 进 L2（扩展序列 × 跨 seed）；写作轨恢复论文 2 贡献 2（方法腿）。
- **G2（关卡②）**：本判决数字入论文/账本前必过。
- **在线版 D1-032 的 J3 归因复核**：本件证 J3 混淆「静态被改」与「动态层遮挡」，在线 J3 −0.49/−1.02 须复核是否含遮挡项。

