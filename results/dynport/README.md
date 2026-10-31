# results/dynport — DynPort：在线动态 GS 管理（DynaGSLAM 式移植）

> **账本**：**D2-027**（立项 + 用户四项拍板）。**判据本体** = `evidence/prereg_dynport_L1.md`
> （判据先锁 commit `03ffdee6f`；§10 标定轮修订 λ_d=0.20；§11 因果仪器实证）。
> **实装设计** = `evidence/impl_design_dynport_L1.md`（§8 实装期修正登记）。

## 目的

论文 2 的**系统腿修复**：把 DynaGSLAM（arXiv:2503.11979, WACV 2026）的动态 GS 管理算法
移植到本仓 RGB-D 在线环路——Case1 KNN 复用（均值替换）+ Case2 新建 + Cond1 可观测删除
+ Cond2 寿命删除 + 分储合渲分优。**不撞 α 共线墙**（D2-017：机制无 per-primitive 可学标量）。

## 方法（一层一段）

- **决策核** `utils/dyn_port_buffer.py`（`MapAccess` 协议）：纯几何/数据管理；常速度外推替代
  DynaGSLAM 的光流 warp（本仓不引 RAFT）。
- **在线 adapter** `utils/dyn_port_online.py`：落真实 `GaussianModel`（`insert_candidate_gaussians`
  + lineage + `prune_points`）。
- **接线** `utils/slam_backend.py`：keyframe 挂 `_dynport_step`（含局部拟合 = DynaGSLAM 步 4）；
  `push_to_frontend` 把动态行不透明度置 0（跟踪隔离，行数不变避开 occ 脱钩）。
- **生命周期豁免** `gaussian_splatting/scene/gaussian_model.py`：`dyn_lineage_base`（默认 0）
  使静态管线（densify_and_prune / reset_opacity_nonvisible）不裁剪动态层（"分优"）。
- **因果仪器** `utils/dynport_causal_log.py`：每 KF 快照动态层 + 位姿（修 final-map 对瞬态层的偏置）。

## 结果（跑批中；完成后本段换成机写读数）

- L1 正式批 = 远程 3090，crowd2 + balloon2 × {E,D,C−} = 6 run（`scripts/dynport/run_L1.sh`）。
- 判据机 `scripts/dynport/judge_dynport.py`（双仪器：动态区 J1/J2 用 `--causal`、静态区 J3 用
  final-map；禁混引）；汇总 `scripts/dynport/collect_L1.py` → `evidence/manifest_L1.json`。
- **pilot 实证（非权威，4 帧 seed0 本机 2060）**：同 run 两仪器对判 J1 final-map −0.35 vs
  causal **+9.28 dB** ⇒ 机制成立，"D≈E" 是仪器偏置。

## 结论与出口

**待正式批**。出口（prereg §4，先锁）：J1≥+2.5 且 J2≤0.70 ⇒ PASS 进 L2；[1.0,2.5) ⇒ 边界
（一次 R2）；<1.0 ⇒ FAIL 止损。**已知边界**（如实）：无持久动态身份记忆（短窗 + 到期删，
物体离开视野回来即重建）——属论文 3。

## 运行信息

- prereg：`03ffdee6f`；实装+整改：`d374…`~`962d70f08`（见 git log）。
- 远程：`jiangwenheng@172.16.227.24` 单卡 3090（主人任务绝对优先）。
- 判活看 `logs/L1.done` + `logs/L1_monitor_status.txt`（禁裸 pgrep）。
