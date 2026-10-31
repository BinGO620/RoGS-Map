# prereg_dynport_offline_L1 — DynPort-Offline：离线地图动态修复算子 L1 判据先锁

> **账本**：D1-032（DynPort 在线判决 FAIL）下游；用户 2026-10-06 批准「甲方案」（论文 2 方法腿
> = 离线修复算子）。**设计档** = `resources/notes/dynport_offline_design_2026-10-06.md`（commit `8a44acc26`）。
> **本件 = 判据先锁**（跑批前提交，记 **commit 哈希**；prereg 提交时间须**早于**任何批工件 mtime）。
> **上游**：`prereg_dynport_L1.md`（机制/超参/仪器纪律逐字沿用；**放置从在线改为离线**）+
> `prereg_dyn_probe_5seq_2026-10-05.md`（代价口径）+ `resources/lit_dyn_mapping/papers/dynagslam.md`（机制出处）。
> **性质**：**离线后处理算子**（新脚本，零 SLAM 主循环改动，default-off 语义 = 输出与输入底图逐位一致）。
> **边界（事前声明，写进 Discussion）**：无持久动态身份记忆（Case1 因果 KNN + 到期删）；
> **不主张在线能力、不主张 4D 重建 SOTA**——本案只测"同一机制换放置"的收益/代价结构。

## 0. 缺口与动机

1. **在线判决**（D1-032）：机制成立（J1 +6.97/+6.96 dB、J2 0.355/0.259、J5/J7 过）但 **在线不可负担**
   （J4② +95%/+89%）+ **静态区受损**（J3 −0.49/−1.02）。按 prereg_dynport_L1 §4「J4 不过 ⇒ FAIL
   （在线不可负担）⇒ **转离线边界形态**」——本件 = 该出口的执行。
2. **为什么离线是正解而非降级**：两道死因**结构性消失**——① 离线无在线预算约束（J4 改报数）；
   ② 离线不碰前端/tracking ⇒ ATE 结构性零影响（J8 从测量改构造核验）。
   **冻结静态**（独立 Adam、静态行梯度清零）是把在线 J3 的"建图侧未隔离"根因**结构性**消除。
3. **科学问题（论文 2 叙事）**：动态内容能否从**一张已抹除的（反动态范式）生长地图**里被恢复，
   收益多少、代价多少？与在线批组成"同机制三放置对照表"（设计档 §5）。
4. **底图语义（先锁，实测）**：底图臂 = **R33 rebase `baseline`**——它是论文 Tab.1 首列报告之
   **栈**（Base (MonoGS)）的**单 seed run**（Tab.1 本体 = 7 序列 × 3 seed 均值，**禁**与本案 seed0
   数字对拍），语义掩码开着（`mask_insertion/mask_mapping: true`，maskrcnn / COCO `person=1`，
   `dilate_px: 7`——三序列 config 逐一实测）⇒ **动态像素被挡在地图插入外 = "抹除"的来源**；
   且与在线 DynPort L1 批**同栈**（SWBA/LC 均关，底图 console 命中 0）。

## 1. 机制定义（先锁，实装前定稿）

**DynPort-Offline = 底图（全静态）+ 逐 KF：掩码重算 → 决策核（Case1 复用/Case2 新建/Cond1/Cond2）
→ 冻结静态的局部拟合 → 动态层快照。** 算法本体与在线版**同型**。

> **⚠ 单变量澄清（G1-F1）**：**不**主张"在线↔离线只变一个变量"。放置从在线改到离线**必然连带
> 4 处共变**（位姿源 / 静态保护 / KF 日程 / 掩码通路，见设计档 §2.2 表）——这是"离线放置"的定义，
> 非瑕疵。故本 prereg 的单变量仅指**内部三臂 R0/R1/C−**（同底图/同 config/同数据/同日程）；
> **在线↔离线为跨放置描述性对照，含 4 处共变，不作因果主张**（§11 表须标批号）。

| 环节 | 离线做法 | 复用件 |
|---|---|---|
| 反投影 | 掩码 ∧ **传感器深度** → 世界点（同在线） | `DynPortManager._unproject`（`dyn_port_online.py:215`） |
| 决策核 | Case1 KNN 复用（λ_d·d̄ 均值替换）/ Case2 新建 / Cond1 可观测删 / Cond2 寿命删 | `DynPortBuffer`（`dyn_port_buffer.py`；MapAccess 协议与放置无关） |
| 拟合（"分优"） | **冻结静态**：`fit_iters` 步，静态行梯度清零（Adam 对 grad≡0 行恒 0 ⇒ 逐位不动） | `transient_fit_build_optimizer/mask_grads`（`slam_backend.py:100/114`）+ `_dynport_fit` 损失结构（`:1854`） |
| 插入 | world→pixel 桥 + `insert_candidate_gaussians` | `GaussianModelMap.insert`（`dyn_port_online.py:96`，构造同名相机喂 trj 位姿） |
| 位姿 | **最终轨迹** `trj_full_final.json`（全帧 C2W） | `dyn_probe.Run` 读法 |
| 掩码（方法输入） | **离线重算检测器**（同 config：maskrcnn, COCO `person=1`, dilate_px=7） | `compute_semantic_dynamic_mask`（`semantic_mask.py:128`；`:88` 是带 Camera 缓存的运行期包装，离线不用） |
| 快照（输出①） | 每 KF `frame_<kf>.npz` = 动态层 raw 参数 + 该 KF 的估计位姿（**最终轨迹**位姿） | `utils/dynport_causal_log.py` 同格式（judge `--causal` 零改动消费） |
| 修复地图（输出②） | 底图 + 动态层合并 PLY + `dynamic_rows.npy`（哪些行是动态） | `GaussianModel.save_ply` + `np.save` |

**KF 日程（先锁；G1-F1 整改：以实测为准）**：**复刻底图 R0 的 KF 日程**（console `Candidate insert KF`
严格 **stride=5**，`slam_backend.py:2201`；crowd2 178 / balloon2 93 / person_tracking2 113 个 KF）。
**依据 = R1 是对 R0 这张底图做修复，日程须与 R0 一致**。**不**复刻在线 D 臂日程（实测被 DynPort
自身扰动为 **mean 6.98 帧**，crowd2 129 KF）——两者相差 +38%，**该差是放置轴的第 3 处共变，已登记**
（设计档 §2.2a）；离线与 **R0 的日程则完全相同**（⇒ 内部三臂单变量成立）。

**超参（先锁，沿用在线批标定值，不得逐臂/逐序列调整）**：
`λ_d = 0.20`（在线标定轮产出）、`cap = 50000`、`lmax = 45`、`unproj_stride = 3`、`fit_iters = 300`、
`lrs{xyz5e-4, scale5e-3, rot1e-3, opa5e-2, dc5e-3}`、`lineage_base = 402653184`、
`min_scale_m = 0.001`、`max_scale_m = 0.02`、`control_shift_m = 0.30`（仅 C− 臂）。

**不做（先锁）**：不做双向/全序列实体关联（离线可做"回头看"，属 L2+ 候选；L1 保机制同型）；
不换拟合步数/损失/掩码通路；不借 RAFT/SAM2/DynoSAM；不做持久 4D 记忆。

## 2. 臂（先锁）

L1（3 序列 × 1 seed = 3 组，每组 {R1, C−} 2 次离线修复）：

| 臂 | 含义 | 来源 |
|---|---|---|
| **R0** | 修复前底图（baseline 臂最终地图，无动态内容）= **对照** | 在盘（R33 rebase baseline, seed0） |
| **R1** | 离线算子输出（快照 + 修复地图） | 本批跑 |
| **C−** | 阴性对照：R1 流程但插入错位 0.30m（仪器判别力锚） | 本批跑 |
| **P2** | 天花板参照（探针逐帧插入 oracle，**只报数不判**） | 已有读数（`dyn_probe_5seq_*`） |

**判据机臂名映射**：`judge_dynport.py` 的 `E`↔**R0**、`D`↔**R1**、`Cneg`↔**C−**（`judge_dynport.py:181`
硬编码 `loaded["E"]` 作 M_bad 参照 ⇒ R0 在 arms 里**必须**命名为 `E`）。
**渲染类（J1/J2/J3/J6/J7）judge 零改动**；**J4/J5/J8/J9 须改** `scripts/dynport_offline/collect_L1.py`
（prereg §7）。R0 无 `dynport_causal/` ⇒ causal 加载器走 fallback 普通渲染（`:121-124`，实测属实）= "抹除基线"语义。

**序列与底图 run（先锁，实测在盘）**：

| 序列 | 底图 run（R33 rebase baseline, seed0） | 评估帧（console 日程，个数） |
|---|---|---|
| crowd2 | `results/paper2_fulltable/r33_rebase_baseline_crowd2_seed0/datasets_bonn/.../2026-09-16-06-54-45/` | 35 |
| balloon2 | `.../r33_rebase_baseline_balloon2_seed0/.../2026-09-16-03-15-56/` | 18 |
| person_tracking2 | `.../r33_rebase_baseline_person_tracking2_seed0/.../2026-09-16-13-23-00/` | 22 |

**内部单变量声明**：R0/R1/C− 三臂同底图、同 config、同数据、**同 KF 日程**（§1）；
R1 与 C− 只差 `control_shift_m`。**跨放置（在线↔离线）不作单变量主张**（4 处共变，§1 警示框）。

## 3. 判据（R1 机械应用，禁手抄；每序列独立判定）

主读数 = **动态区 M_bad 子集**（`M_bad(f) = dyn_mask ∧ GT-depth-valid ∧ [R0 臂渲染深度无效 或
|R0−GT|>0.10m]`，配对同帧；沿用 judge_dynport 实现）。**仪器口径（继承在线教训 §11）**：
动态区 J1/J2 = **因果快照**（`--causal`）；静态区 J3 = **final-map**（默认）；**两口径禁混引**。

| # | 判据 | 阈值（先锁） | 依据/变化 |
|---|---|---|---|
| **J3 静态区无伤（第一硬门）** | `Δstatic_psnr(R1−R0)` median ∈ [−0.25,+0.25] dB（**双边带**）；且 `Δfull = full_psnr(R1)−full_psnr(R0)` median ≥ −0.25 dB | ±0.25 | 在线版待改善项→离线版**结构性主张**（冻结静态 ⇒ 应天然满足）⇒ **先于 J1 判**。**Δfull 落点（G1-M1）**：`dyn_probe.frame_metrics` 已产 `full_psnr`（实测键存在）⇒ 判据机须**新增**把 `full_psnr` 差写入 `J3_full_delta`（否则该子句不可判） |
| **J1 动态区增益（主判）** | `dyn_bad_psnr(R1) − dyn_bad_psnr(R0)` median ≥ **+2.5 dB** | 2.5 | 沿用在线 §3（主判线不因放置调整） |
| **J2 深度误差比** | `dyn_bad_dl1(R1) / dyn_bad_dl1(R0)` median ≤ **0.70** | 0.70 | 沿用在线 §3 |
| **J4 离线预算（报数 + 尺度自检）** | **报**：`repair_wall_s` + 与底图 SLAM `online_time_s` 之比；**且报**机制本体分相位（拟合/KNN/掩码重算各占时）。**1× 参考线只报不判**；若该比恒 <0.3 则**标"参考线无判别力"**（G1-M8：底图 `online_time_s` 含全程 tracking+mapping，与"机制本体"不同尺度） | 报数 | 在线 15% 硬门语义失效；计时批**单卡串行**；尺度差入 Discussion |
| **J5 机制生效（离线守门力有限，见 §3 注）** | 算子 `dynport_counters.csv` 三计数全 >0（case1_hits ∧ cond1_deleted ∧ cond2_deleted）**且**动态层总基元数落 [1e3, cap]（非退化）；**并与"算子启用/停用"两态的 R1 输出做 PSNR max\|Δ\| 核验（>0.01 dB 才证明真起作用）** | 计数>0 + 两态差 | **离线弱化**（G1-M2）：离线 J5"跑完即 >0"守门力弱 ⇒ 加"两态差"补强（对应在线 J5 守"接线真的通了"）。**"停用态"= 仅 crowd2 单次**（一次即可证接线，G4-C8 澄清），**不计入 §5 的 6 次 L1 规模**（规模 = 3 序列 × {R1, C−}） |
| **J6 可判性** | 配对可用帧 ≥50% **且** `dyn_bad_px` 中位 >0（**须机械落点**） | ≥0.5 | 沿用；**落点（G1-次要）**：judge 须吐 `dyn_bad_px`，`collect_L1` 须含 J6 |
| **J7 阴性对照** | `dyn_bad_dl1(C−)/dyn_bad_dl1(R1) ≥ 1.15` | 1.15 | 沿用。**唯归因边界（G1-M6）**：R1/C− 是两次独立运行，比值含运行间差异 ⇒ 不过时**二者皆可能**，归因记"仪器判别力不足 **或** 运行间波动"，须补一次同臂复跑定噪声地板（§10.8） |
| **J8 ATE（构造核验）** | **结构性零**：R1 输出目录 trj 与 R0 trj **逐位一致**（max\|Δ\| = 0，脚本核验记布尔） | 逐位 | 离线不碰 tracking ⇒ 从"测量 Δ"改"构造核验"（判据机不写回任何 tracking 消费文件；实装须核验 R1 输出目录不含 tracking 回流路径） |
| **J9 阳性对照（离线构造恒真，见 §3 注）** | 算子 `enabled=false` ⇒ 输出 PLY 与输入底图**逐位一致**（SHA 核验 + 单测两态） | 逐位 | **离线弱化**（G1-M2）：off = 不跑脚本 ⇒ 恒真；保留为"装置卫生"守门（守实现无副作用/无 OOB 写），**不计入 PASS 票** |

**§3 注（G1-M2 采纳）**：离线版 J5/J9 的守门力弱于在线版——J5"跑完即 >0"是构造事实，
J9"off ⇒ 逐位一致"是构造恒真。故：**出口 PASS 的实质判据 = J3 ∧ J1 ∧ J2**（三条）；J5/J9 作
**接线/装置守门**（不过 ⇒ 先修不判机制），**不作为 PASS 的独立一票**（避免"两票恒真支撑 PASS"）。

## 4. 出局与判定规则（先锁）

- **每序列独立判定**；**J7 不过** ⇒ 该序列仪器失效（不聚合，登记原因，非 NO-GO）。
- **J5 不过**（计数零 **或** 两态差 ≤0.01 dB）⇒ FAIL（机制未生效）——先查接线，不判"机制无效"。
- **J6 不可判** ⇒ 该序列 FAIL。
- **J9 不过**（off 与底图非逐位）⇒ VOID（实验装置污染），先修 default-off。
- **顺序**：**J3 先判**（第一硬门）——不过 ⇒ 允许**一次**修结构快筛（动态层 → 静态区污染路径），
  仍不过 ⇒ **FAIL（离线放置下静态隔离不成立）**，全案退乙/丙。

**出口（先锁；G1-M2 整改：PASS 实质 = J3∧J1∧J2）**：
- **J3 ∧ J1 ∧ J2 全过**（3 序列）**且** J5/J6/J9 守门全过（接线/装置无污染）⇒ **PASS** ⇒ 进 L2。
- **J1 ∈ [+1.0,+2.5)** 或仅部分序列过线（且 J3 过）⇒ **边界** ⇒ 允许一次 R2 改进快筛（判据不变）。
- **J1 < +1.0**（且 J3 过）⇒ **FAIL（机制在离线放置下不成立）** ⇒ 止损，全案退乙/丙。
- J4 只报数（不设 FAIL）；若比值恒 <0.3 ⇒ 标"参考线无判别力"，不入结论支撑。

## 5. 时间盒与硬门（先锁）

- **实装硬顶 = 2026-10-11**（含 default-off 两态单测）。超期 ⇒ 止损。
  **工作量登记（G1-M7）**：实装清单 = 离线 MapAccess 主循环 + 掩码重算通路 + 快照落盘 + 修复地图
  合并 + default-off 两态单测 + 冒烟；其中"底图 dynamic_rows 通路"本仓从未离线跑通（在线 v2 正式批
  `dynport_causal/` 实测为空）⇒ 硬顶为**先锁值**，若中途评估不可能则按"超期即止损"执行，不硬撑。
- **L1 硬顶 = 2026-10-15**。到点未过 ⇒ 止损，不追加 run，论文 2 回乙（纯测量形态照投）。
- **L1 规模 = 3 序列 × 1 seed × {R1, C−} = 6 次离线修复**（禁首跳大批，R7）。
  **另 +1 次**：crowd2「停用态」核验 run（J5 两态差用，见 §3 注）——该 1 次为装置核验、
  **不计入 6 次规模**（G4-C8 澄清）。
- **冒烟测（先于 6 次）**：crowd2 单次修复（本机 2060 或远程；**非权威 pilot**）→ rc=0 + 三计数非零 +
  快照/修复地图落盘 + J9 字节核验通过 ⇒ 才派正式批。冒烟抓出的缺陷修复走 commit + 登记（impl §8 先例）。
- **批级硬顶**：6 次修复 预估超 4h ⇒ 砍至 crowd2 + balloon2（2 序列 × 2 臂）。决策记批日志。
  **估时参照（G1-M8）**：在线机制本体 2.66 s/KF（`dynport_time_s` 340.3 s ÷ `dynport_frames` **128**，
  G4-C5 口径：**128 = 计数器写盘帧数**，与 console KF 会话 **129** 同批不同口径，禁混引）；
  离线 129–179 KF 外推 ≈343–476 s/序列（不含掩码重算）。**但底图 `online_time_s`（1778 s）
  含全程 tracking+mapping** ⇒ J4 比值尺度不同（详见 §10.7）。

## 6. 出口后路径（先锁）

- **PASS** ⇒ L2（+crowd/crowd3/person_tracking/person_tracking2 扩展 × 1 seed；跨 seed）⇒
  ≥2/3 泛化 ⇒ L3（全 7 序列 × 3 seed + codec 联动）⇒ 写作轨（贡献栏三条定稿）。
- **边界** ⇒ 一次 R2 快筛（唯一一次；失败 ⇒ 本族关闭）。
- **FAIL** ⇒ 本族止损；论文 2 贡献 2 撤下 ⇒ 回乙（纯测量形态）投 CVM。

## 7. 工件与关门前置

- 四件套：`configs/experiments/dynport_offline/`（如需）、`scripts/dynport_offline/`、
  `tests/dynport_offline/`、`results/dynport_offline/`。
- 判据键（机写）：`results/dynport_offline/evidence/dynport_offline_L1_<seq>_{causal,final}.json` +
  `manifest_offline_L1.json`（HEAD/时间/臂路径/评估帧/计数/计时/核验布尔）。
- 算子输出目录结构（R1/C− 各一份，落 `results/dynport_offline/L1/<seq>_<arm>/`）：
  `config.yml` + `point_cloud/final_after_opt/point_cloud.ply` + `plot/trj_full_final.json`
  （后两者以 baseline run 为依据：PLY = 修复后合并；trj = 逐位复制）+ `dynport_causal/`
  （快照 + `dynamic_rows.npy`）+ `dynport_counters.csv` + `repair_timing.json`。
- **工件入库（G1-M5）**：`.gitignore` 忽略 `results/**/*.{npy,npz}` 与 `*.ply` ⇒ 快照/修复地图
  默认不入库；S5 收口时须**显式** `git add -f` 关键 npz/npy 与修复 PLY（或落 SHA256 校验和），
  否则远程丢失即永久不可复算（违 D3）。
- 判据机 = `scripts/dynport/judge_dynport.py`（**渲染类 J1/J2/J3/J6/J7 零改动**，但须**新增**
  `J3_full_delta`（Δfull）与 `dyn_bad_px` 落键——G1-M1/次要项；E/D/Cneg 名映射见 §2）；
  汇总 = `scripts/dynport_offline/collect_L1.py`（J4 读 repair_timing.json、J5 读算子计数+两态差、
  J6 读 bad_px、J8 读 trj 核验、J9 读 SHA 核验）。
- **数字入正文前过关卡②**（G2）；**实装前过关卡① G1**（设计档包型，**本轮已走**：Reject ⇒ 本件整改 ⇒ G4 核销）
  **与关卡③ G3**（实装包型）。

## 8. 批信息（跑批前提交）

- 远程 3090（先查 `nvidia-smi`；主人任务绝对优先；空闲即用）；**计时批单卡串行、禁并发**。
- 提交 sha 记于账本（D1- 新行）；HEAD 一致性：新旧数字禁混引（D1-027 教训）。
- 远程临时文件写 `/home`（根分区满盘教训），不写 `/tmp`。

## 9. 已知坑（逐条对照，写进实装清单）

1. **因果/终图混引**（在线教训 §11）⇒ 动态区 `--causal`；静态区 `--final-map`；judge 输出 instrument 字段。
2. **判据先锁**：本 prereg commit 时间 < 批工件 mtime；超参改动走带日期修订行。
3. **default-off 逐位一致**（J9）：算子 off ⇒ 输出 = 输入底图逐位；单测两态。
4. **底图 lineage 全 UNTRACKED**（`load_ply` 不持久 lineage）⇒ 离线算子自持 lineage；
   `dynamic_rows.npy` 在输出侧生成（judge 依赖）。
5. **`get_xyz` 是 `@property`**（D1-021）⇒ 取属性不调方法。
6. **位姿时刻**：离线用最终轨迹；与在线批"中态位姿"数字**禁逐位对拍**（同机制不同位姿时刻）。
7. **跨批混引**（D1-027）：本案数字只与本案工件比；参照在线数字须标批号（v2/f0fcdb6f8）。
8. **远程 `/` 满盘**：写 `/home`。
9. **计时口径**：J4 = 修复全程墙钟；不套在线 15% 线；比值尺度差见 §10.7。
10. **KF 日程当单变量**：离线 = R0 日程（stride=5）；与在线 D 臂 mean 6.98 的差是放置轴共变（§1）。
11. **判据无机械落点**：新增判据须先在判据机产出键再进 prereg（G1-M1 教训）。
12. **底图代码版本**（G1-M4）：R0 底图 = 09-16 代码；离线/判据机 = 10-06 代码。共享代码改动
    （`fd2a105cf`/`1e30d1c72`）声明 `dyn_lineage_base==0 ⇒ 逐位不变`——**须在 S3 实装期补一次
    逐位一致实测**（同 config 两态 PLY/PSNR `max|Δ|`），落证后再派批（§10.9）。

## 10. 诚实边界（不掩饰）

1. **新颖度**：机制本体归 DynaGSLAM（arXiv:2503.11979，必引）；delta = 离线放置 + 冻结静态的
   建图侧隔离 + 时间放置代价对照。单独看"移植改离线"薄——须三件捆提 + 数字硬度。
2. **位姿残差**：离线用最终轨迹（Bonn ATE ~1.4cm 量级）⇒ 修复质量受此限制。
3. **离线日程与 R0 同、与在线 D 臂不同**（§1）：离线复刻底图 stride=5（178/93/113 KF）；
   在线 D 臂被机制扰动为 mean 6.98（crowd2 129 KF）。**跨放置比较含此共变**。
4. **L1 规格**：3 序列 × 1 seed；跨 seed/跨检测器属 L2。
5. **gtmc 缺**：全仓/数据集均无 `dynamic_mask_gtmc/`；本案判据用 canonical `dynamic_mask/`，
   与 gtmc 无关；跨表引用禁混口径。选 person_tracking2 的理由 = **探针读数现成**（非 gtmc）。
6. **P2 天花板口径**：探针 P2 是"逐帧插入 + GT 深度"oracle；与 R1（stride=5 + 传感器深度）
   不同口径，**只作参照**。
7. **J4 参考线尺度（G1-M8）**：底图 `online_time_s`（crowd2 1778 s / balloon2 933 s / pt2 1258 s）
   含**全程 tracking+mapping**；离线"机制本体"外推 ≈343–476 s ⇒ 比值 ≈0.19–0.27×，**1× 线
   大概率恒不触发** ⇒ 标"参考线无判别力"，只报数 + 分相位（拟合/KNN/掩码重算）。
8. **J7 归因边界（G1-M6）**：R1/C− 是两次独立运行 ⇒ 比值含运行间差异；须补一次 **R1 同臂复跑**
   定噪声地板（落 `repair_repeat.json`），否则 J7 不过时归因不可定。
9. **底图代码版本（G1-M4）**：见 §9.12；S3 实装期补逐位一致实测，落 `base_arm_identity.json`。
10. **掩码一致性（G1-M9）**：离线掩码重算 vs 在线运行期掩码**未实测逐像素一致**；登记为
    "同模型同调用路径"，不主张逐像素等价（GPU 非确定性未声明）。
11. **Tab.1 引证（G1-M3）**：底图 = "Tab.1 首列所报告之栈的**单 seed run**"，**禁**与 Tab.1
    的 3-seed 均值数字对拍。
12. **SH degree ≠ 0 的后果（G4-C3）**：判据机 `_snap_to_dyn`（`judge_dynport.py:113`）只喂 `f_dc`，
    动态层 `features_rest = 0`。**当前三序列底图 PLY 实测 SH degree = 0**（`f_rest_` 计数 0）⇒
    前提成立、无偏；**但若底图 degree ≥ 1**（L2/换数据集），动态层会系统性偏暗且该退化未建模
    ⇒ **S3 实装须在加载时断言底图 degree == 0**（fail-loud），degree ≥1 时拒跑并登记。修复地图
    落盘时 `features_rest` 与 degree-0 底图的拼接行为同须实测（`_gaussians_from_points` 的
    `coefficient_count` 除零风险）。
13. **判据机臂名 fail-loud（G4-C6）**：`judge_dynport.py:181` 在缺 "E" 臂时**静默** `bm=None`
    （M_bad 语义静默改变）⇒ **S3 实装须改为 fail-loud**（缺 R0/`E` 臂即报错），防 M_bad 参照缺失
    导致的静默口径漂移。

## 11. 与在线版的关系（对照结构；论文用法）

| | 在线（DynPort v2，`f0fcdb6f8`） | 离线（本案） |
|---|---|---|
| 位姿 | 前端中态估计 | 最终轨迹 |
| 静态保护 | 无（J3 伤） | 冻结静态（J3 待测） |
| KF 日程 | 真 KF（被机制扰动，mean 6.98） | 复刻 R0 底图（stride=5） |
| 掩码 | 运行期 MaskRCNN（缓存） | 离线 MaskRCNN 重算 |
| 前端/tracking | 共享地图（ATE +1.06/+1.47cm） | 不碰（ATE 构造零） |
| 代价 | +95%/+89%（FAIL） | 报数 vs SLAM 全程（尺度见 §10.7） |
| 工件出处 | `manifest_L1_v2.json` | `manifest_offline_L1.json` |

**禁混引**：两表并列展示时须标批号/代码版本；数字不跨列比（除设计声明为对照）。

## 12. 修订记录（append-only；带日期）

- **2026-10-06 v2（G1 整改轮）**：关卡① G1（slam-critic，设计档包型）判 **Reject**（1 致命 + 9 重大 + 5 次要，
  报告 `/tmp/slam_critic_dynport_offline_g1_2026-10-06.md`）⇒ 本件整改。逐条：
  - **F1（致命，KF 日程）**：原"在线批平均间隔 ~5 帧 / baseline console 无 KF 事件"**与实测相反**。
    实测：在线 D 臂 KF = mean **6.98**（crowd2 129 KF），底图 R0 = 严格 **stride=5**（178 条
    `Candidate insert KF`）。整改 = 离线**复刻 R0 日程**（§1）；"离线 179 vs 在线 D 129"的 +38%
    差**登记为放置轴共变**（§1 警示框 / §10.3）。
  - **F1 连带**：删除"在线↔离线单变量"声明，改为"**内部三臂 R0/R1/C− 单变量；跨放置为描述性对照，
    含 4 处共变（位姿/静态保护/KF 日程/掩码）**"（§1 / 设计档 §2.2/§5）。
  - **M1**：J3 的 `Δfull` 原无机械落点 ⇒ 显式要求判据机**新增** `J3_full_delta`（`full_psnr` 键实测已存在）（§3/§7）。
  - **M2**：J5/J9 离线守门力弱 ⇒ 出口 PASS 实质判据收紧为 **J3∧J1∧J2**，J5/J9 降为接线/装置守门（§3 注/§4）；
    J5 增"启用/停用两态 PSNR 差"补强（§3）。
  - **M3**：修"底图 = 论文 Tab.1 首列"为"**Tab.1 首列所报告之栈的单 seed run**"（§0.4/§10.11）。
  - **M4**：底图 09-16 代码 vs 离线 10-06 代码 ⇒ 增 S3 前置核验 `base_arm_identity.json`（§9.12/§10.9）。
  - **M5**：动态行/快照未入库（`.gitignore` 忽略 npy/npz/ply）⇒ 增 S5 显式入库核验（§7）。
  - **M6**：J7 归因边界（R1/C− 两次运行）⇒ 增 R1 同臂复跑定噪声地板 `repair_repeat.json`（§10.8）。
  - **M7**：实装工作量登记 + 硬顶按实测重估（§5）。
  - **M8**：J4 参考线尺度差（底图 `online_time_s` 含全程 tracking+mapping）⇒ 标"参考线无判别力"（§5/§10.7）。
  - **M9**：修引证行号（`:88`→`:128`）+ 标 COCO `person=1` 口径 + 掩码一致性不主张逐像素等价（§1/§10.10）。
  - **次要**：J6 增机械落点（`dyn_bad_px`）；person_tracking2 选理由改"读数现成"（非 gtmc）（§10.5）。
  - 整改性质 = **判据/口径修订 + 引证更正**，机制本体与超参未改；按 G1 报告建议走 **G4 小包核销**。

- **2026-10-06 v3（G4 核销轮）**：关卡① 复核（G4，报告 `/tmp/slam_critic_dynport_offline_g4_2026-10-06.md`）
  判 **Accept-with-conditions**（无致命；F1 已销、M1–M6/M8/M9 已销、M7 部分销）⇒ 本件处置 8 条条件：
  - **C1（M1 落点·代码）**：`J3_full_delta` 生产者未落地 ⇒ **列入 S3 实装必做**（本轮已建机器门
    `scripts/02_analysis/prereg_criterion_keys.py` 覆盖之，S3 后须转绿，§9.11）。
  - **C2（M4·代码）**：`base_arm_identity.json` 逐位一致实测 ⇒ **S3 实装前置**（§9.12/§10.9）。
  - **C3（M5 措辞·纸面）**：SH degree / `features_rest` 边界**已补**（§10.12）：S3 加载时**断言底图
    degree == 0**（fail-loud），degree≥1 拒跑登记。
  - **C4（M7·纸面）**：实装工作量登记已在 §5；**估时分解/中间 checkpoint** 并入 S3 执行清单（每完成
    一个通路即 commit + 回读，超顶即止损）。
  - **C5（口径·纸面）**：`128`（`dynport_frames` 写盘帧）vs `129`（console KF 会话）**已补口径注**（§5）。
  - **C6（fail-loud·代码）**：`judge_dynport.py:181` 缺 "E" 臂静默 `bm=None` ⇒ **S3 改为 fail-loud**（§10.13）。
  - **C7（类登记表·机制）**：本轮新类"**prereg 声明的机械判据键，判据机未产出**"（M1/J6/J4 同族）⇒
    **已建门** `scripts/02_analysis/prereg_criterion_keys.py` + 负对照
    `tests/lifecycle_paper2/test_prereg_criterion_keys.py`（6 passed），并登记进 `.zcode/agents/slam-critic.md` §0.3。
  - **C8（口径·纸面）**：J5「停用态」核验 run = **仅 crowd2 单次**、不计入 6 次 L1 规模（§3 注/§5）。
  - **术语冲突（G4 新发现·纸面）**："不换掩码通路" → 改"不换**检测器**（掩码通路随放置共变）"（设计档 §2.2）。
  - **整改性质**：条件级（纸面 5 + 代码 3 已挂 S3）⇒ **无新致命/重大，Accept-with-conditions 可直接执行**
    （G4 定义：条件清单随执行留痕，不必再开一轮）。

- **2026-10-07 v4（J3 仪器口径 amend 轮；用户 2026-10-07 批准「甲」= amend J3 仪器口径 + 丙 = 去鬼）**：
  **判据本体变更** —— J3 与 J1/J2 的**仪器口径**（阈值不变：J3 ±0.25 dB / J1 ≥+2.5 dB / J2 ≤0.70）。
  **触发**：v3 判决登记 J3 破线（balloon2 −3.21，B 口径），但同会话诊断已证**静态本体零损伤**
  （oracle 逐帧层 Δ≈+0.003；静态行逐字节一致）。用户批准 amend ⇒ 本件先锁口径，再 G1，再实装/重判。
  **证据（全部机写）**：`evidence/diag_j3_calibers.json`（六口径分解，commit `71b92f935`）+
  `evidence/recon_j3_caliber_2026-10-07.md`（含位姿控制与 A/B 判别力对照）。
  - **A1（口径变更·本件的核）**：J3 主口径由 **B = 合并图 + 末帧动态层 @ 帧 e 位姿**（= 原 `final-map`，
    测"底图 + 单张末帧层"）改为 **C = 静态底图 + 最近 ≤e 快照动态层 @ **帧 e 最终轨迹位姿**
    （= output① 4D 层序列的真实消费口径）**。**依据（先于结果，非事后选定）**：
    ① **交付形态**：用户批准的甲明确输出形态 = **逐 KF 层序列（output①）**，非单 PLY（output②）；
    ② **B 是烘焙伪影**：B 的负号随末帧层规模单调（层=0→0.00/29→−0.06/1436→−3.21），即"把末帧层
    铺在早期帧上"的时切片伪影，**无任何 4D 消费者如此使用**（判据不得惩罚未采用的交付形态）；
    ③ **E（静态本体）不采纳**：仅静态行渲染恒等于底图（构造恒真），是判据洗白，**排除**；
    ④ **D（oracle）**：范式天花板 Δ≈0，证明范式不伤静态（保留为参照，不判）。
  - **A2（位姿去混·J1/J2/J3 同改）**：**位姿控制**（底图本身换位姿渲染，无动态层）实测
    base@snapPose − base@frameE_pose = **−4.03 / −3.27 / −8.34 dB**（crowd2/balloon2/pt2）
    ⇒ 原 `judge --causal` 中 **E 臂走帧 e 位姿、D 臂走快照位姿**（`judge_dynport.py:145`）**混入位姿差**，
    J1/J2/J3 全被污染。**故 J1/J2 亦改用同帧位姿仪器**（全臂帧 e 位姿 + 最近 ≤e 快照层），
    与 J3 同源。**旧 `--causal` 数值不再可引**（标为位姿混杂口径）。
  - **A3（§4 一次结构快修的归属·登记非第二次）**：v3 §4 已用"一次结构快修"（掩码收边/尺度夹回/
    投影掩码剪枝探针）。本轮**不新增修法**，仅：① **恢复 `_clamp_dyn_scale` 调用**——`28283206a`
    引入并在 `repair()` 调用，`72a05c27d` 误将其替换为 `_suppress_out_of_mask` ⇒ `max_scale_m` 成死参
    （CLI 传入但从不使用）；**恢复属缺陷修复，非第二次快修**；② 认可 **S5 = {投影掩码剪枝 + 尺度夹回}**
    为 §4 那**一次**结构快修的**完成态**（两探针此前在 B 口径下测得"未达线"，实为口径伪影）。
  - **A4（判别力核验·防"改到过"）**：同帧位姿口径**可证否**——对**未施加 S5 的原 L1 批**
    （`f093c880b`），同口径 J3 = **−3.876 / −0.941 / −1.081**（FAIL）；施加 S5 后 = −0.049/+0.086/0.000。
    ⇒ 口径非构造恒真、非平凡过。
  - **A5（诚实边界·FAIL 不抹除）**：**在 v3 原锁口径 B 下，单 PLY 交付仍 FAIL**（本件**不**删该结论）。
    本件仅声明：**operator 的 4D 交付形态（output①，甲批准）在诚实同帧位姿口径下过线**；
    单 PLY（output②）的结构性遮挡作为**交付形态约束**登记（回照 verdict §7）。
  - **A6（recon 非权威·须正式重跑）**：本件依据的 l1b/l1c 为**侦察 run**（远程 3090，非锁定 HEAD）
    ⇒ **判决数字须来自锁定 HEAD 后的正式批**（`manifest` 机写）；侦察仅定口径。
  - **A7（新机械键·先声明后实装）**：判据机须新增 `J3_samepose_static_delta`（= C 口径 static Δ）
    与 `J1_samepose_bad_psnr_delta` / `J2_samepose_bad_dl1_ratio`；旧 `J3_static_delta`（B）保留为
    **诊断**不进出口。经 `prereg_criterion_keys.py` 登记（须转绿）。
  - **整改性质**：**判据口径修订（本体变）** ⇒ **必须 G1 复核**（判据本体已变）；机制核心/超参未改。

