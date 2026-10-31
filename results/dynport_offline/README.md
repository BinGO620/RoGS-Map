# results/dynport_offline — DynPort-Offline：离线地图动态修复算子

> **账本**：**D1-033**（立项 + 用户 2026-10-06 批「甲方案」= 论文 2 方法腿）→ **D1-034**（J3
> 口径 amend 后 L1 重判 PASS）→ **D1-035**（L2 泛化 PASS）→ **D1-036**（L3 正式批 PASS +
> 「codec 联动」缺口呈报）。
> **判据本体** = `evidence/prereg_dynport_offline_L1.md`（§12 v4 = J3/J1/J2 同帧位姿口径）。
> **上游**：在线 DynPort（`results/dynport/`，D1-032 判 FAIL）——本案 = 同机制的**离线放置**。

## 目的

论文 2 方法腿：反动态范式留下的「已抹除地图」里，用逐帧 RGB/深度/掩码 + 最终位姿**离线**重建
动态层（Case1 KNN 复用 + Case2 新建 + Cond1/Cond2 删除），**静态层全程冻结**。回答一个关于
地图的知识问题：**动态内容能否从一张已抹除的地图里被恢复、收益多少、代价多少**。不主张在线
能力、不主张 4D 重建 SOTA（属论文 3）。

## 方法（一层一段）

- **离线算子** `scripts/dynport_offline/repair_map.py`：载入底图 run → 复刻其 KF 日程（stride=5）
  → 逐 KF 离线重算 MaskRCNN 掩码 → 掩码∧传感器深度反投影 → 决策核 → **冻结静态拟合**（只优化
  动态层参数）→ 落盘（逐 KF 快照 + 合并 PLY + counters + timing）。
- **决策核** `utils/dyn_port_buffer.py`（与在线同型，放置无关）；**自持动态层** `utils/dyn_port_offline.py`。
- **输出①** 逐 KF 4D 层序列（`dynport_causal/frame_*.npz`）= **PASS 的交付形态**；
  **输出②** 单张合并 PLY = 静态区结构性带伤（时切片伪影，见 `evidence_v4/verdict_*` §3）。
- **S5 结构快修**（§4 那一次）= {投影掩码剪枝 + 尺度夹回}，timing 显式落 `s5_suppress_out_mask`
  /`s5_scale_clamp`（provenance 可机检）。

## 结果（机写判决；数字零手抄）

| 关卡 | 规格 | 出口 | 判决文件 |
|---|---|---|---|
| **L1** | 3 序列（crowd2/balloon2/pt2）× seed0 × {R1,C−} | **PASS**（J3∧J1∧J2 + 守门） | `evidence_v4/verdict_dynport_offline_L1_v4_2026-10-07.md` |
| **L2** | 扩展序列 × seed0 + 跨 seed（9 格） | **PASS（9/9 ⇒ ≥2/3）** | `evidence_L2/verdict_dynport_offline_L2_2026-10-08.md` |
| **L3** | **全 7 序列 × 3 seed = 21 格** | **PASS（21/21）** | `evidence_L3/verdict_dynport_offline_L3_2026-10-08.md` |

**L3 读数**（出口口径 = samepose）：J1 = 5.49–8.95 dB（≥+2.5）｜J2 = 0.23–0.61（≤0.70）｜
J3 = −0.035–0.196 dB（±0.25）｜J5/J9 守门过｜J7（seed0 锚）= 1.33–2.31｜J4 报数 0.11–0.30×
（参考线无判别力）。**判据机与算子在 L1_v4/L2/L3 三批 HEAD 间逐位一致**（跨批复用合法）。

## 已知边界（如实，不掩饰）

- **单 PLY（output②）在新口径下仍 FAIL**（结构性遮挡）；只主张 **4D 层序列（output①）** 成立。
- **J2 余量最小**（最紧 crowd_seed2 = 0.6104，仅 1.15×）——S5 剪枝/夹回保静态（J3）的代价是
  深度比（J2）变差，**J3/J2 存在结构性张力**。
- **person_tracking 族 J3 恰为 0.0000**（饱和；动态体与静态区几乎不重叠）⇒ 其"过"不作机制证明。
- **J7 仅锚 seed0**（跨 seed 格无 C− 阴性对照 ⇒ 14/21 为 None）。
- **`codec 联动`**（prereg §6 括注）= 未定义占位 ⇒ 缺口报告 `L3/report_L3_scope_2026-10-08.md`。
- **简化臂豁免声明**：离线算子**不碰 SLAM 主循环**（纯后处理，输入 = 已完成的底图 run），
  SWBA/LoopClosure 结构性不适用；config 继承自底图（R33 baseline 本身无 SWBA/LC）⇒
  health_check「简化臂外推风险」WARN 对本实验**不构成外推边界**（结论只声称离线修复算子，
  不声称在线系统）。

## 运行信息

- **判据先锁**：`evidence/prereg_dynport_offline_L1.md`（§12 v4，commit `6571bbade`）。
- **批驱动**：`scripts/dynport_offline/{run_L1.sh, run_L3.sh}`（计时批单卡串行）；汇总
  `collect_L1.py`（支持多根跨批复用）；判决生成 `write_verdict_{L2,L3}.py` / `write_verdict_L1_v4.py`。
- **远程**：`jiangwenheng@172.16.227.24` 单卡 3090（`ssh remote`/`3090` 别名是错的）；临时文件写
  `/home`（根分区满盘教训）。
- **测试**：`tests/dynport_offline/`（12 passed）；判据键门 `scripts/02_analysis/prereg_criterion_keys.py`
  （MISSING_TOTAL=0）。
- **关卡**：G1（设计档）/ G2（判决档，L1/L3 已跑，L2 承 L1 口径）——数字入论文前必过。
