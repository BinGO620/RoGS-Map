# prereg_dyn_probe_5seq — 反动态代价探针跨序列扩展（B-1）

> **账本**：D2-026 写作轨（B 线）；本件 = **判据先锁**（跑批前提交，记 **commit 哈希**）。
> **上游**：`prereg_dyn_probe.md` + `prereg_dyn_probe_balloon.md`（判据**逐字沿用，不因序列调整**）；
> 判定 = B 线从"2 序列探针（自述非论文数字）"升级为"**多序列论文级代价测量**"。
> **性质**：离线渲染探针（冻结地图、配对同帧）；**零 SLAM 重跑**、零核心代码改动。
> **边界（事前声明）**：本件交付**代价测量**；"保留动态"的**在线机制（系统达成）属论文 3**
> （face-dynamic），本件不做、不主张。

## 0. 为什么（缺口）

B 线现状 = pt2 + balloon 两序列，`verdict_dyn_probe.md`/`_generality.md` **自述"离线筛选、非论文数字"**。
要写进论文当"代价刻画"，须补：① **多序列**（证明非特例）；② 与论文 3 的**干净边界**。
本批 = ①；②由正文划界句承担（阶段 3）。

## 1. 序列集与地图（先锁）

**5 序列 × 2 臂（seed0）= 10 图**；序列选取 = 覆盖 crowd 族主体 + 非 crowd 对照：

| 序列 | 选择理由 | run_dir（baseline / gate，r33_rebase seed0） |
|---|---|---|
| crowd | A 线暴露的"拥挤例外"主对象 | `r33_rebase_{baseline,gate}_crowd_seed0` |
| crowd2 | B 线原主域（复现） | `...crowd2_seed0` |
| crowd3 | crowd 族第三序列（泛化） | `...crowd3_seed0` |
| balloon2 | 非 crowd 对照 | `...balloon2_seed0` |
| person_tracking | 人动态、低掩码覆盖对照 | `...person_tracking_seed0` |

**帧选（内容判据，跑前锁；禁看结果指标）**：`dyn_probe.py coverage --mask-subdir dynamic_mask
--n-frames 16` 产出每序列 16 帧 + t0（工件 `evidence/coverage_b1/<seq>.json`）：

| 序列 | selected_frames | t0 |
|---|---|---|
| crowd | 247,269,300,322,344,367,421,443,466,518,540,563,585,607,630,750 | 585 |
| crowd2 | 6,32,59,85,111,141,167,222,257,283,309,336,362,405,720,746 | 336 |
| crowd3 | 0,37,63,113,140,166,193,233,294,321,418,571,602,629,688,787 | 602 |
| balloon2 | 0,16,31,60,75,91,132,147,163,178,194,210,331,424,439,455 | 194 |
| person_tracking | 28,56,159,169,179,189,200,210,220,230,241,251,261,271,282,292 | 241 |

**掩码**：canonical `dynamic_mask/`（`mask_subdir: auto` ⇒ 只认 canonical，不回退 legacy）。
**PLY**：`final_after_opt`（r33_rebase 每图存在；缺则退 `final`）。

## 2. 臂（与母 prereg 同）

`arms = [P1, P2, C-, P4, P2c]`：P1 抹除 / P2 保留（天花板，逐帧插入+拟合）/ C− 阴性对照（错位 0.30m）/
P4 烘焙（t0 插入后冻结）/ **P2c 因果臂**（仅用 ≤t 的帧；需 `kf_log`=consolelog）。
超参锁定 = `unproj_stride 3 / fit_iters 300 / lrs{xyz5e-4,scale5e-3,rot1e-3,opa5e-2,dc5e-3} /
control_shift_cam_m [0.30,0,0]`（**不得逐臂/逐序列调整**）。

## 3. 判据（**逐字沿用母 prereg §7 + M_bad 补遗；跨序列一致**）

**主读数 = M_bad 子集**（`M_bad(f) = dyn_mask ∧ GT-depth-valid ∧ [P1 渲染深度无效 或 |P1−GT|>0.10m]`）：

1. **①b 天花板（主）**：`dyn_bad_dl1(P2)/dyn_bad_dl1(P1) ≤ 0.70` **且** `dyn_bad_psnr` 差 **≥ +2.0 dB**。
2. **① 天花板（全掩码，参考）**：同上阈值（降为参考口径）。
3. **③ 无伤**：`|Δstatic_psnr(P2−P1)| ≤ 0.25 dB` 且 `Δfull ≥ −0.25 dB`。
4. **④ 成本**：`mean_n_dyn ≤ 50% × n_static`。
5. **⑤ 仪器（阴性对照）**：`dyn_dl1(C−)/dyn_dl1(P2) ≥ 1.15`；不满足 ⇒ **判仪器失效，先修工具**（非 NO-GO）。
6. **⑥ 阳性对照**：P1 全图 PSNR 与既有 `render_compare` 同帧 `max|Δ| ≤ 0.01 dB`。
7. **C1b 因果保留率**：`retention(P2c) ≥ 0.50`。
8. **描述性**：P4 vs P1（"插一次冻结 ≈ 抹掉"是否复现）。

**出局/判定规则（先锁）**：
- 每序列**独立判定**①b（**不做全局均值一把过**——A 线教训：crowd 例外会被均值掩盖）。
- ①b 过 ⇒ 该序列记为"代价成立"；不过 ⇒ 如实记"该序列不成立"，**不修阈值、不剔序列**。
- ⑤ 不过 ⇒ 该序列仪器失效，**其数据不入聚合**（登记原因）。
- **汇总口径**：报"**k/5 序列 ①b 过**"+ 逐序列 `dyn_bad_dl1` 比值与 PSNR 差（区间），不报单一总数。

## 4. 时间盒与冒烟测（先锁）

**先冒烟测 1 图**（crowd2/baseline，全 5 臂 16 帧）计时。
- 若单图 ≤ 20 min ⇒ 跑 **5 序列 × 2 臂 = 10 图**。
- 若 > 20 min ⇒ 砍到 **3 序列（crowd2、crowd3、balloon2）× 2 臂 = 6 图**（保 crowd 族主体 + 非 crowd 对照）。
- **决策规则**：以冒烟测实测墙钟 ×10 或 ×6 与"≤4h 单批"比较定规模；决定记入批日志。

## 5. 出口

- **k ≥ 3/5（或砍批后 k ≥ 2/3）序列 ①b 过** ⇒ 代价刻画具**跨序列**证据；正文 B 段按"多序列实证"写。
- **k < 3** ⇒ 代价刻画**降为单/两序列 observation**（如实写，正文只保留原 pt2+balloon，不夸大）。
- ⑤ 全失效 ⇒ **不写**（工具未验证）。

## 6. 工件与关门前置

- 判据键：`results/embrace_dyn/evidence/dyn_probe_5seq_<seq>_<arm>_results.json`（10 或 6 份，每图独立）。
- 帧选工件：`evidence/coverage_b1/<seq>.json`（已生成，锁帧）。
- config：`configs/experiments/embrace_dyn/probe_5seq_<seq>.yaml`（每序列一份；`mask_subdir: auto`）。
- 批驱动：`scripts/embrace_dyn/run_probe_5seq.sh`（写本文件后提交）。
- **数字入正文前过关卡②**（G2：数字/工件逐位、口径、臂归属、单变量）。噪声带/仪器/阳性对照按 §3。

## 7. 批信息（跑批前提交）

- 远程 3090（空闲即用）；单卡串行（离线渲染，非计时批，但避免与 owner 抢卡 ⇒ 单进程）。
- 冒烟测先行；规模由 §4 规则定；决定与理由入批日志。
- 提交 sha 记于账本 D1-030。
