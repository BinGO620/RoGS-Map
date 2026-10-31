# prereg_dynport_L1 — DynPort：在线动态 GS 管理（DynaGSLAM 式）L1 判据先锁

> **账本**：D2-026 下游（论文 2「修好系统腿」轨，用户 2026-10-05 拍板：动系统、狠心、在线环路、本仓信号源）。
> **本件 = 判据先锁**（跑批前提交，记 **commit 哈希**；prereg 提交时间须**早于**任何批工件 mtime）。
> **上游**：B 线 `prereg_dyn_probe_5seq_2026-10-05.md`（评测口径逐字沿用）+ 文献卡
> `resources/lit_dyn_mapping/papers/dynagslam.md`（机制出处，arXiv:2503.11979, WACV 2026）。
> **性质**：**在线环路实装**（改前端/后端/config），default-off，关闭时与主线逐位一致。
> **边界（事前声明，写进 Discussion）**：本机制**无持久动态身份记忆**（Hermite 短窗 + Cond2 到期删除，
> 物体离开视野回来即重建）——这是如实边界，**不包装成卖点**；持久 4D 记忆属论文 3（face-dynamic）。

## 0. 缺口与动机

1. **系统腿的缺口**：论文 2 现用前作栈（+SWBA+LC+Gate）在 Bonn 上 pt2=11.68cm（**比 baseline 劣化 +12.2%**）、
   pt1=7.95cm；SWBA 只在 pt1 净有效。R33 归因 = SWBA 净伤害**机制固有**（现有信号维度分不开可修/不可修）。
2. **为什么换 DynPort 而非再修 SWBA**：9 次失败全栽在 **α 共线墙**（D2-017：任何 per-primitive 可学
   标量必经 α_eff）。DynPort **不给基元加可学标量**——用几何/数据管理（KNN 复用 + 均值替换 + 删除规则），
   **不撞 α 墙**。
3. **novelty 落点（据实，G1-次#1 纠正）**：本机制**不是** gap #12（"信号 = SLAM 自身误差统计"——
   那要求无外部模型；本仓语义掩码 = MaskRCNN，**属外部检测器**，不满足 #12）。据实定位 =
   **gap #11 的窄形态**（"把动态保留在地图里、但从跟踪证据中排除"）+ **DynaGSLAM 管理算法的 RGB-D 在线移植**：
   - **可借（DynaGSLAM）**：Case1/2 + Cond1/2 管理算法本体（几何/数据管理，非可学标量）；
   - **差异化（我们的自有点）**：① **RGB-D 在线联合优化**（DynaGSLAM 定位外包 DynoSAM、不联合优化）；
     ② **前端不引 RAFT/SAM2**（用本仓 MaskRCNN 掩码 + 传感器深度 + 自身跟踪）⇒ 无动态专用基础模型先验；
     ③ **反动态 vs 保留的配对分区评测**（DynaGSLAM 无实测反动态基线，其 DynaPSNR 对抹除范式不可测）。
   - **⚠ 纪律**：**不得**写成"信号来自 SLAM 自身"（那是 #12，本机制不满足）；主张面收窄为
     "已验证管理算法在本仓在线环路的可移植性 + RGB-D 联合优化形态"。
4. **文献锚点**：探针已证"插一次即冻结 ≈ 抹掉"（P4），DynaGSLAM Cond.1 设计动机逐字同构。
5. **与论文 2 定性（D2-026）的关系**：论文 2 原定性"系统 + 地图侧、机制移交论文 3"。本立项 = **用户 2026-10-05
   推翻该定性中的"系统腿"部分**（D2-027）——把系统腿从"前作栈如实报告"升级为"修好的系统"。**地图侧贡献
   （codec/代价刻画）不变**。D2-026 的"机制移交论文 3"仅指**持久 4D/face-dynamic**；本机制（瞬态保留管理）
   不等于 face-dynamic，落在论文 2 系统腿。

## 1. 机制定义（先锁，实装前定稿）

**DynPort = 动态基元分储 + 均值替换复用 + 可观测/寿命生命周期**，信号源全用本仓现有件：

| 环节 | 做法 | 出处/复用 |
|---|---|---|
| 插入（Case1 复用） | 掩码内像素反投影点云 → cKDTree 1-NN 匹配既有动态基元，`d_min ≤ λ_d·d̄` ⇒ **替换均值**（显式搬移） | `dyn_probe.DynPortBuffer.step:1101`（算法原型，**在线须换真信号**，见下） |
| 插入（Case2 新建） | 未命中 ⇒ 新建基元（`_gaussians_from_points`） | 同上 |
| 生命周期 Cond1（可观测删除） | 当前观测点云无近邻的旧基元 ⇒ 删 | 同上 `:1142` |
| 生命周期 Cond2（寿命删除） | 存活 > `lmax` 帧 ⇒ 删 | DynaGSLAM §5.2 |
| 分储合渲分优 | 动态/静态基元分开优化（不同 lr、静态图损失剔除动态像素），联合渲染 | DynaGSLAM §5.2-5.3 |

**信号源（★区分两个"掩码"，G1-重大#2 纠正；二者不可混同）**：

| 用途 | 来源 | 说明 |
|---|---|---|
| **方法输入**（机制每帧消费） | **运行期掩码** `compute_semantic_dynamic_mask`（本仓 MaskRCNN，`utils/semantic_mask.py:88`）| 在线系统现有通路（与 `mask_insertion`/`mask_mapping` 同源）；**不是** canonical 目录 |
| **评估分区**（判据 M_bad/static 用） | **canonical `dynamic_mask/`**（冻结参照，`utils/dynamic_mask_spec.py:29` 明文 `EVAL_MASK_SUBDIR`）| 只读、单源（测量口径 #3）；**方法绝不消费** |

> **G1-重大#2 纠正**：prereg v1 误把 canonical `dynamic_mask/` 当方法输入。canonical 是**冻结评估参照**，
> 方法消费它 = 仪器污染 + E/D 双变量。**方法输入 = 运行期 MaskRCNN 掩码**（与现有在线系统同一检测器、
> 同一通路），评估分区 = canonical（只读）。两者分离：机制在**运行期掩码**上插入/复用；判据机在
> **canonical 掩码**上划 M_bad/static 分区。**不引 RAFT/SAM2/DynoSAM**（品牌：无动态专用基础模型先验）。

**超参（先锁，不得逐臂/逐序列调整；与实装默认对齐——G1-重大#8 纠正）**：
`λ_d = 0.05`（DynaGSLAM 实测值）、`cap = 50000`（**实装默认须改为 50000**；`DynPortBuffer.__init__` 现默认
60000 `:499`，实装时显式传参，不靠默认）、`lmax = 45`（寿命阈值，帧；**标定轮**由 crowd2 单 run 探针定，
标定轮在 L1 之内、先于正式 6 run，标定判据 = "动态基元数稳态落在 5k–50k 且无持续增长"，标定结果记
`evidence/dynport_lmax_calibration.json`）、`unproj_stride 3`、`fit_iters 300`、
`lrs{xyz5e-4,scale5e-3,rot1e-3,opa5e-2,dc5e-3}`（沿用探针锁定值）。

**实装可移植性（G1-重大#7 纠正；"探针≠在线"边界）**：`dyn_probe.DynPortBuffer` 是**算法原型**，
直接搬上线会踩本仓"探针≠在线"边界（`NOTES.md`）——原型用 **GT 深度 / `trj_est` 离线位姿 / canonical 掩码**，
在线必须换成 **传感器深度 / 在线估计位姿 / 运行期掩码**。实装时逐项替换并在单测里守护（探针类不得在线调用）。

## 2. 臂（先锁）

L1（机制主场，2 序列 × 1 seed）：

| 臂 | 含义 |
|---|---|
| **E** | 主线 erase（无 DynPort；= 当前系统行为） |
| **D** | DynPort on（本案机制） |
| **C−** | 阴性对照：D 臂但插入基元错位 0.30m（仪器判别力锚） |
| **P2** | 离线天花板锚（探针逐帧插入，非在线）——**只作参照，不进在线判据** |

**单变量声明**：E 与 D 只差 `DynPort.enabled`；其余 config 逐行 diff 仅路径/sequence 名。

## 3. 判据（R1 机械应用，禁手抄；每序列独立判定）

主读数 = **动态区 M_bad 子集**（`M_bad(f) = dyn_mask ∧ GT-depth-valid ∧ [E 臂渲染深度无效 或 |E−GT|>0.10m]`，
配对同帧；沿用 B 线口径）。判据机 = 仿 `scripts/embrace_dyn/judge_p0.py` 新写 `scripts/dynport/judge_dynport.py`。

| # | 判据 | 阈值（先锁） | 依据 |
|---|---|---|---|
| **J1 动态区增益（主判）** | `dyn_bad_psnr(D) − dyn_bad_psnr(E)` median ≥ **+2.5 dB** | 2.5 | 与 P0/E2 主判同线（`judge_p0.MAIN_PASS_DB`）；P0/E2 历史实测 +3.83/+9.68 |
| **J1b 天花板占比（描述性，不设硬阈）** | `J1_median / (P2天花板 median)` ——**只报数、不判过**（标定轮后如需再锁硬阈另走带日期修订行） | 无 | **不做硬约束**：离线 oracle ≈ +18~22 dB，P0/E2 在线只到 oracle 的 ~0.18 ⇒ "0.8×" 无标定依据（mope 立项教训：阈值须有依据） |
| **J2 深度误差比** | `dyn_bad_dl1(D) / dyn_bad_dl1(E)` median ≤ **0.70** | 0.70 | 沿用 B 线 ①b |
| **J3 静态区无伤** | `Δstatic_psnr(D−E)` median ∈ **[−0.25, +0.25] dB**（**双边带**；静态区变好也算超界，如实登记）且 `Δfull ≥ −0.25 dB` | ±0.25 | 沿用 B 线 ③（**G1-次#3 纠正**：原写 `\|Δ\|` 语义不清，改双边带） |
| **J4 成本有界** | ① `n_dyn ≤ 50k` 上限**未触顶**（`cap_hits`/n_frames < 10%）——**若触顶 ⇒ 判不可判**，先修 cap 或降 stride；② **mapping 相位**在线墙钟增量 ≤ **15%**（单卡串行+相邻配对+交替，I/O 不圈进计时，报噪声地板） | 15% | **G1-重大#4 纠正**：15% 是 **mapping 相位**口径（本机制跑 KF 率，非逐帧 tracking）；项目既定"在线**逐帧**机制"线 = **5%**（mope D1-025，tracking 相位）。**换算前提**：15% mapping ≈ 5% tracking，当且仅当 mapping 相位时长 ≥ 3× tracking 相位时长——**此比须在 L1 用实测两相位时长核验**（落 `evidence/dynport_phase_ratio.json`）；核验不过 ⇒ J4② 记**不可判**，不改线 |
| **J5 机制生效** | 落盘 `dynport_counters.csv` 三计数全 >0：`case1_hits`（Case1 复用命中）∧ `cond1_deleted`（可观测删除）∧ `cond2_deleted`（寿命删除） | 计数>0 | **G1-重大#3 纠正**：`reuse_rate` 本仓无落点，改用实装已有计数名（`dyn_probe.py:1085/1128` 的 `case1_hits` 等） |
| **J6 可判性** | 配对可用帧 ≥ 50%，`bad_px` 中位 > 0 | ≥0.5 | 测量口径 #2 |
| **J7 阴性对照** | `dyn_bad_dl1(C−)/dyn_bad_dl1(D) ≥ 1.15`（仪器能检出 30cm 错位） | 1.15 | 仪器有效性（失败 ⇒ 判仪器失效，非 NO-GO） |
| **J8 ATE（L1 = 描述性 + 噪声地板）** | **报** ΔATE(D−E) 逐序列 + 同批噪声地板（1 seed）；**若任一序列 Δ > +1.0cm ⇒ 标记 L2 必查**。**L1 不做硬门** | 报数；+1.0cm 标记 | **G1-重大#5 纠正**：+0.5cm 落在 1-seed 噪声内（pt2 seed 极差 0.72cm，`verdict_f_rebase`），无地板 ⇒ L1 硬门无效。**J8 硬门移到 L2（3 seed，有真地板）**：ΔATE ≤ 地板 或 ≤ E+0.5cm |
| **J9 阳性对照（G1-重大#6 新增）** | E 臂（DynPort **off**）与主线同 config 基线**逐位一致**：全图 PSNR `max\|Δ\| ≤ 0.01 dB`（同帧，与既有 `render_compare` 对拍）；或 default-off 单测证明逐位相同 | 0.01 dB | 锚"off ≡ 主线"，防机制静默激活污染 E 臂（B 线 ⑥ 同型） |

## 4. 出局与判定规则（先锁）

- **每序列独立判定 J1**（禁全局均值一把过——A 线 crowd 例外教训）。
- **J7 不过** ⇒ 该序列仪器失效，数据不入聚合（登记原因），**非 NO-GO**。
- **J5 不过**（机制零生效）⇒ **FAIL（机制未生效）**，先查接线/依赖，不判"机制无效"。
- **J6 不可判** ⇒ 该序列 FAIL（不判通过也不判边界）。
- **J9 不过**（off 臂 ≠ 主线）⇒ **VOID（实验装置污染）**，整批作废，先修 default-off。

**出口（先锁；G1-重大#3 纠正：J2/J4 归属写对）**：
- **J1 ∧ J2 ∧ J3 ∧ J5 ∧ J9 全过**（两序列）⇒ **PASS** ⇒ 进 L2。（J1b/J8 只报数；J8 硬门在 L2。）
- **J1 在 [+1.0, +2.5) 或仅一序列过线，且 J3/J5/J9 过** ⇒ **边界** ⇒ 允许一次 R2 定位改进快筛（判据不变）。
  - **边界分支补注**：若**仅 J2 不过**（动态区 PSNR 过但深度误差没压到 0.70）⇒ 记为 **"边界（深度未达标）"**，
    归因查 Cond1/Cond2 删除时序，不并入"机制无效"。
- **J1 < +1.0** ⇒ **FAIL（机制无效）** ⇒ 止损。
- **J4 不过** ⇒ **FAIL（在线不可负担）** ⇒ 转离线边界形态（论文 2 系统腿降级为如实局限）：
  - **J4① 不过**（cap 触顶）⇒ 先按 §1 标定轮修 cap/stride **一次**，仍不过 ⇒ FAIL。
  - **J4② 不过**（墙钟超线）⇒ FAIL（在线不可负担），同 MoPe 处置。

## 5. 时间盒与硬门（先锁）

- **L1 硬顶 = 2026-10-13**。到点未过 ⇒ 止损，不追加 run，回地图侧保底（论文 2 按现形态投）。
- 实装硬顶 = 2026-10-09（含 default-off 单测两态）。实装超期 ⇒ 直接止损。
- **L1 规模 = 2 序列（crowd2 机制主场 + balloon2 对照）× 1 seed × {E, D, C−} = 6 run**（禁首跳大批，R7）。
- **标定轮（先于 6 run，含在 L1 硬顶内）**：crowd2 单 run 探针定 `lmax`（判据 = 动态基元数稳态 5k–50k 且无持续增长），
  落 `evidence/dynport_lmax_calibration.json`；标定轮不入判据计数。
- **冒烟测（G1-次#4 纠正：去掉 20–30min 盲带）**：crowd2 单 run 计时 → 按**批级硬顶 ≤ 4h** 决策：
  - 若 6 run 预估 ≤ 4h ⇒ 跑满 6 run；若 > 4h ⇒ 砍到 **1 序列 × {E,D,C−} = 3 run**。
  - 决策规则记入批日志（含实测单 run 墙钟与预估算式），不留盲带。

## 6. 出口后路径（先锁）

- **PASS** ⇒ L2（+crowd/crowd3/person_tracking × 1 seed，3 类型泛化）⇒ ≥2/3 见效升 L3（3 seed × 全序列，重跑 Bonn 主表 ATE）。
- **边界** ⇒ 一次 R2 快筛（唯一一次；失败 ⇒ 本族关闭）。
- **FAIL** ⇒ 本族止损，论文 2 保持"系统 = 前作栈 + 地图侧贡献"，系统局限如实写。

## 7. 工件与关门前置

- 四件套：`configs/experiments/dynport/`、`scripts/dynport/`、`tests/dynport/`、`results/dynport/`。
- 判据键：`results/dynport/evidence/dynport_L1_<seq>_<arm>_results.json`（每 run 独立）+ 计数器 `dynport_counters.csv`。
- 判据机：`scripts/dynport/judge_dynport.py`（数字零手抄，仿 judge_p0）。
- config：`configs/experiments/dynport/L1_<seq>_{E,D,Cneg}.yaml`（单变量：仅 `DynPort.enabled`）；
  键名统一 = `DynPort.{enabled, lam_d, cap, lmax, unproj_stride, fit_iters}`（**G1-次#5 纠正**：v1 混用
  `unproj_stride`/`dynp_stride`，统一为 `unproj_stride`，与实装参数同名）。
- **数字入正文前过关卡②**（G2：数字/工件逐位、口径、臂归属、单变量、计时噪声地板）。
- **实装前过关卡③**（G3）——但**时序**：prereg 先过 G1，G3 与实装并行（若 G3 致命 ⇒ 弃 run）。

## 8. 批信息（跑批前提交）

- 远程 3090（先查 `nvidia-smi`；主人任务绝对优先；空闲即用）。
- **ATE 精度批**可并发（≤2/卡，短序列）；**J4② 计时批单卡串行、禁并发**（D1-024/025）。
- 提交 sha 记于账本（D1- 新行）；HEAD 一致性：新旧数字禁混引（D1-027 教训）。

## 9. 已知坑（逐条对照，写进实装清单）

1. **跨代码版本比性能 = 归因污染**（D1-027）⇒ 重跑主表前 HEAD 一致。
2. **计时并发毁 A/B**（D1-024/025）⇒ J4② 单卡串行 + 相邻配对 + 交替 + I/O 不圈进计时。
3. **`get_xyz` 是 `@property` 不是方法**（D1-021）⇒ 接线时不写 `g.get_xyz()`。
4. **default-off 逐位一致**：机制 key 不在 yaml ⇒ `get(..., False)` ⇒ 等价 HEAD；单测两态覆盖。
5. **ledger 同步**：动 `_xyz` 必须同步 `static_prob/lineage_id/n_obs`（`prune_points:950` 会动它们）。
6. **判据先锁**：prereg commit 时间 < 批工件 mtime。
7. **不做**：不借 RAFT/SAM2/DynoSAM；不做持久 4D 记忆；不救 SWBA。

## 10. 标定轮结果 + 超参修订（2026-10-06；prereg §5「标定轮」条款执行）

**动机**：G3 判 **Reject（致命：J5 `cond2_deleted>0` 不可达）**——实测所有 run 的 `cond2_deleted=0`。
根因（本机 2060 pilot + CPU 复现）：**Case1 缺 DynaGSLAM 的光流 warp**，在关键帧间隔（5 帧，
人位移 ~0.25–0.5m）下匹配容差 `λ_d·d̄`（0.05·2.5≈0.12m）**小于位移** ⇒ 每 KF 全部 miss ⇒
Cond1（可观测删除）抢先清空 lineage ⇒ Cond2 无对象可删（计数恒 0）+ n_buf 塌陷（删-重插 churn）。

**修复**（commit 见账本）：
1. **常速度外推**（DynaGSLAM `v⁻` 的替代，无光流）：按 lineage 质心帧间差分估计速度，匹配前外推
   （`_predict`/`_refresh_tracks`）⇒ 消除帧间位移。
2. **Cond1 用外推后位置**（与 Case1 同口径）。
3. **Cond1 空观测回退阈值同源**（G3-重大#7：消除 `λ_d·1.0` vs `λ_d·d̄` 的 ~40× 尺度漂移）。

**标定网格**（crowd2, 120 帧, seed0, 本机 2060 pilot，**非权威**；`results/dynport/logs/calib2*`）：

| λ_d | cond2_max (J5) | cond1_max (churn) | case1_max (reuse) | ATE (m) |
|---|---|---|---|---|
| 0.05 | 4 | 234961 | 467539 | 0.0140 |
| 0.12 | 213 | 78735 | 636338 | 0.0157 |
| **0.20** | **335** | **47108** | 664158 | 0.0153 |

**超参修订（先锁，替代 §1 的 `λ_d=0.05`）**：**`λ_d = 0.20`**（理由：J5 可触达 + churn 5× 降低；
ATE 三档差 ≤1.3mm 落在 1-seed 噪声内，不作取舍依据）。**`lmax`**：保持 45（本批短短序列未触发寿命轴，
L2 长序列再标）。**修订性质** = 标定轮产出（prereg §5 明许），**判据（J1–J9）不变**。

**⚠ 已登记的结构性局限（据实，不掩饰）**：DynaGSLAM 逐帧插入；本实装挂**关键帧** cadence（5 帧），
即使外推后仍残留 churn（cond1 47k ≫ 0）。**该 cadence 差是机制效率的主因**，写入 Discussion；
若 L1 J1 不达标，第一归因查此，而非机制无效。

## 11. 因果仪器实证（2026-10-06；判据机的仪器口径修订）

**同一 run（crowd2 D 臂 pilot, 120 帧）两种仪器对判：**

| 仪器 | J1 (动态区 bad-PSNR Δ vs E) | J2 (bad dl1 比) | 出口 |
|---|---|---|---|
| final-map | **−0.35** | 1.000 | FAIL（假阴性） |
| **causal snapshot**（本 §） | **+9.28** | **0.252** | **PASS** |

⇒ **机制本身成立**（+9.28 dB 动态区增益、深度误差降到 25%）；此前所有 "D≈E" 读数**全是 final-map
仪器偏置**——动态基元停在末帧位置、渲染早期帧=错位（E2 已登记同款签名，prereg_E2_online §9）。

**仪器口径修订（先锁，替代 §7 的单一仪器）**：
- **动态区 J1/J2 必须用 `--causal`**（静态底图去动态行 + 最近 ≤t 快照动态层 + 快照位姿渲染）。
- **静态区 J3 用 `--final-map`**（静态内容不移动，最终地图即其正确载体；因果底图是收尾态，
  用早期位姿渲染反而结构性错位）。**两口径不可混引**（测量口径 #6）。
- 判据机输出 `instrument` 字段标注所用仪器；判决须并陈两口径。

**⚠ 边界（据实）**：pilot 只有 4 个评估帧、seed0、本机 2060 ⇒ 上述数字**非权威**，仅证机制方向；
正式数待远程 3090 L1 全批。J3 的因果口径偏差（−7.07）已定性为残余混杂（收尾态静态底图），
故 J3 走 final-map —— 该处置写入判决。

## 12. L1 批中途发现 + v1/v2 处置（2026-10-06；**跑批中判定，非跑后**）

**L1 批 v1**（远程 3090，commit `78837c48e`，batch 05:31 起）跑至 3/6（crowd2 E/D/Cneg 完成，
balloon2 进行中）时，从工件读得 **crowd2**：E ATE 2.72cm / **D ATE 5.33cm（+2.61cm，破 J8）**；
D 地图 41812 vs E 29081（+44%）。

**根因（本会话实读代码，非推测）**：`dyn_lineage_base` 豁免当时**只覆盖 prune**
（`densify_and_prune` 的 prune_mask），**未覆盖 `densify_and_clone`/`densify_and_split` 的
`selected_pts_mask`** ⇒ 动态基元被静态梯度致密化**无界 clone/split**（+44% 膨胀 + 跟踪劣化）。
⇒ "分优"未完整（DynaGSLAM 的动态层不参与静态致密化）。

**修复**（commit `1e30d1c72`）：densify clone/split 的 `selected_pts_mask` 也过 `_dynport_protect`。
默认关 ⇒ 逐位不变；单测覆盖 3 处豁免点。

**v1/v2 处置（诚实登记，不改 v1 判据）**：
- **v1 批不中止**（内部一致：6 run 同码 `78837c48e`），跑完如实判 —— 其结果是"v1 形态"的**真读数**
  （J8 破，若 J1 仍达标则出口 = 在线不可负担）。**不因"已知可修"而丢 v1**（丢=掩盖）。
- **v2 批**（修复后，新 commit）**另跑一套 6 run**，与 v1 同判据对比 ⇒ 隔离"densify 豁免"的效应。
- 两批**禁混引**（跨代码版本，D1-027 教训）；判决须并陈 v1/v2。
- **时序合规**：v1 的 prereg（03ffdee6f）早于 v1 工件；v2 的修复 commit（1e30d1c72）早于 v2 工件。
