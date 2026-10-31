# 预注册：拉通批同批复核（R34，2026-09-17）

> **账本登记（2026-09-25 追补，D2-015 同例；原文零改动）**：本预注册属账本设立前的文书，决策留痕见 `NOTES.md` 实验清单与 git 历史；本轮由 health_check H5 扩表（`prereg_*` 纳入覆盖面）后检出为“未挂账本号”，按机制登记补入本指针，不追改正文。

> 触发：2026-09-17 方法梳理会话发现 `results/paper2_rollout/` **存在自有
> baseline 臂（`rollbase_*`）却未进面板**（`rollout_panel.csv` 的
> `baseline_ate_cm` 列全空），补上对照后 **6/19 条序列的 |Δ| > 1.5cm**
> （跨批噪声地板 0.18–0.62cm），其中 5 条为负作用。
> 详见 `resources/notes/method_review_2026-09-17.md` §4。
> 用户 2026-09-17 批准"先出复核批"。
>
> **纪律合规**：零代码改动——纯 config 重跑（DISCIPLINE #2）。
> 判据先锁定（本文件），跑批在判据锁定之后。编号用 **K1–K6**，
> 避免与 NOTES 踩坑 P1–P26、R33 的 G1–G6 撞名。

## 一、问题：跨批对照冒充同批对照

现有 `rollbase_*`（09-10/11 批）与 `roll_*`（09-09/10 批）**分属两批**。
方法梳理会话已判定两臂**同码**（窗口内仅 `a21e0773`/`1150fb25` 两处
雅可比修复于 09-09 13:50 完成，19 序列两臂 run 时间戳全部晚于此），
故差值**不是版本效应**——但**仍是跨批**，与 R32 实测的跨批偏移
（平均 |Δ|=0.14cm、最大 0.48cm）叠加。

**现有 1-seed 观测（col 8 全帧，冻结，供 K5 复算）**：

| seq | `rollbase`（全关） | `roll`（gate） | Δ | 方向 |
|---|---|---|---|---|
| f1_room | 8.2384 | 18.1034 | **+9.87** | 有害 |
| f1_desk2 | 7.1966 | 3.5267 | **−3.67** | 有益 |
| f3_st_rpy | 2.6851 | 5.8459 | **+3.16** | 有害 |
| f3_office | 1.6438 | 3.6579 | **+2.01** | 有害 |
| moving_obstructing_box | 18.7758 | 20.7368 | **+1.96** | 有害 |
| f3_wk_rpy | 4.2924 | 5.8689 | **+1.58** | 有害 |

**序列选择规则（客观、非任意）**：全 19 条可比序列中取
**|Δ| > 1.5cm** 者——恰好 6 条（5 有害 + 1 有益）。
未被选入的 13 条 |Δ| ≤ 1.16cm（最短 f3_st_static +0.02、最长 f3_st_hf +1.16）。

### 1.1 阈值依据与**已知局限**（跑批前如实登记，不事后补）

- **1.5cm 的独立依据**：跨越"跨批噪声地板"（标准 Bonn 上实测 0.18–0.62cm）
  **两倍以上**的裕度。**局限（不得省略）**：该地板**只在标准 Bonn 7 序列上测过**，
  本批 6 条序列（TUM f1/f3 5 条 + Bonn 扩展 1 条）**没有自有跨批地板测点**。
  这与 R33 被 critic 判为重大成立的"异方差阈值挪用"是**同一形态的已知债务**，
  本批只能如实声明，不能假装有依据。
- **1.5cm 阈值不考虑序列自身 seed 方差**：本批 6 条中多条属**已知高方差族**——
  `roll_f3_st_hf` col8 逐 seed = **34.677 / 3.6876 / 3.4926**（seed 内极差 31.2cm，
  P15 点名的双峰序列）；对照标准 Bonn 的 baseline 臂 seed 内极差最大仅 0.608cm。
  ⇒ **本规则可能选入"因抽样碰巧分离"的序列**。这是本批设计最强的自认弱点，
  **由 K5 的复现判据直接检验**：若这些 Δ 在 3-seed 同批下不复现，
  K6 会判"不成立"，结论降级——**这正是本批存在的意义**。
- **f1_desk2 作"方向对照"的功效有限（n=1）**：它的作用**不是**"证明有益方向存在"
  （n=1 无功效），而是"检验同批重测是否复现**方向**"。K6 对它的判据只要求
  符号一致，**不得**用它支撑或否决 19 条层面的主张。

### 1.2 冻结参照的 provenance（**关卡③ 致命 2 整改**）

关卡③ 独立复核发现：6 个 `roll_*` 源 run 里 **2 个的顶层 consolelog 自报
save_dir 时间戳与 `tracking_raw.csv` 的 `run_id` 不一致**，且
`roll_f1_room_seed0` 下并存**两个** run 目录。**本次逐条独立复核结论**：

| seq | consolelog 自报 | tracking `run_id` | 判读 |
|---|---|---|---|
| f1_room | 2026-09-09-**18-09-09** | 2026-09-09-**22-25-07** | **不一致**（两个目录并存；22:25 目录有 `config.yml`+`per_frame_ape`，18:09 目录只有 plot/psnr/point_cloud） |
| f1_desk2 | 09-09-17-47-49 | 09-09-22-03-50 | **不一致** |
| f3_st_rpy / f3_office / f3_wk_rpy / moving_obstructing_box | 同 run_id | 同 | 一致 |

**取数裁定**：K5 的冻结值**取自 `tables/tracking_raw.csv`（run_id 所在目录）**，
且已用该目录的 `per_frame_ape.csv` 独立复算验证
（f1_room：1315 帧复算 = 18.1034，与 col 8 一致）。
**另核（加固）**：6 个 run_id 目录内的 `config.yml` 全部为 gate 形态
（`SWBA.enabled=True`、`swba_max_static_conf=0.38`、`LoopClosure.enabled=True`）
⇒ **冻结值确属 gate 臂、臂归属无误**。
**⇒ 冻结值本身可复算、可信**；不可信的是**顶层 consolelog 的归属**
（它描述的是另一次执行，如 f1_room 的 18:09 那次）。
**对本批的影响与处置**：K3 的生效判据读 consolelog ⇒
**本批新 run 必须额外核验"consolelog 自报 run_id == tracking run_id"**
（新增 K3-b，见 §三），否则同一事故会重演且无法察觉。

### 1.3 已知的 rc=0 但 consolelog 截断形态（**关卡③ 重大 7 整改**）

逐 run 复核 40 个 rollout run：**`roll_f3_wk_hf_seed0` 的 consolelog 在
kf=600 处截断（`MonoGS: Done` = 0、`LoopClosure` = 0），而 done 记
`finished rc=0`、`tracking_raw.csv` `status=OK`、col8=3.6625**。
⇒ **rc=0 与"consolelog 完整收尾"不是一回事**（P5/P17 同族），
且本批 K3 与 §2.1 自证**全部依赖 consolelog**。
**处置**：K1 增补 `MonoGS: Done` = 1 的存在性判据；K3 增补"无输出"例外条款
（见 §三）。


## 二、实验设计

- **序列**（6，由 §一 规则锁定）：
  `f1_room` / `f1_desk2` / `f3_st_rpy` / `f3_office` /
  `moving_obstructing_box` / `f3_wk_rpy`
- **臂**（3）：
  - `r34_rb_{seq}` ← 复制 `rollbase_{seq}.yaml`，**仅改 save_dir**
    （两组件全关）
  - `r34_sw_{seq}` ← 由 `r34_rb` 派生，**加 `SWBA.enabled: true`**
    （SWBA 开、回环关）
  - `r34_gate_{seq}` ← 复制 `roll_{seq}.yaml`，**仅改 save_dir**
    （SWBA 开 + `swba_max_static_conf: 0.38` + LoopClosure 块）
- **seed**：0, 1, 2（3 seed）
- **规模**：**3 臂 × 6 序列 × 3 seed = 54 run**
- **并发**：4 fixed worker（2 per GPU，R33 同一脚本同一策略）
- **派发顺序**：按**序列**交错三臂（§六 的 CFGS 串），使同序列各臂相邻

### 2.1 为什么是 3 臂而不是 4（**本批设计的核心依据**）

R33 已同批证明 **`swbaonly → final` 的唯一步长（= LoopClosure 开关）在
42 个 run 上恒为零修正**，且同批 7 序列效应平均 |Δ|=0.170cm、符号随机
（3 正 4 负），整条落在同码重跑散度 0.18–0.62cm 之内
（`resources/notes/method_review_2026-09-17.md` §0-A/§0-B；
机制根因 = 验收器把边钉死在里程计位姿上，`utils/loop_closure.py:657-672`）。
⇒ **省掉 `final` 臂**（否则 6 序列再加 18 run），把预算用于
**SWBA/门控 两段归因**——这正是本批要回答的第二个问题。

> **⚠ 作用域更正（2026-09-17 跑中，如实留痕）**：上文"恒为零修正"的
> **作用域是标准 Bonn 7 序列**（R33 的 42 run 全在 Bonn）。本批的
> held-out 序列**不适用**——跑中实测见下方"风险与自证"的触发记录。
> 预注册原文本已把这一风险写明并指定了自证手段，故非事后追认。

**风险与自证**：若回环在**这 6 条 held-out 序列**上并非零效应，
则 3 臂设计会漏掉 `final` 一列。**自证手段**：`r34_gate` 臂含完整
LoopClosure，其 consolelog 的 `corrections |dt| med/max …` 行
**直接给出这 6 序列 × 3 seed 的回环修正量**（K3 判据）——
若仍全为 0.00cm，则 3 臂设计成立；若出现非零，须补 `final` 臂后再裁。

> **✅ 自证已执行（2026-09-17 16:00，跑中，按预注册处置）**：已完成 gate run
> 逐 run 核（去折行）：
> - `f1_room` 三 seed、`f1_desk2` seed0/seed2、`f3_st_rpy` seed1 → `max 0.00cm`
> - **`f3_st_rpy` seed0 → `max 10.36cm`、seed2 → `max 13.23cm`（非零）**
> - 对照：旧批 `roll_f3_st_rpy_seed0`（同 config）**同一批 verified 对**
>   （335→385, 310→415, 630→665, 240→275）为 `0.00cm`
>   ⇒ **同一输入、修正量不同 = 非确定性**，非配置错
>   （新旧 config diff=0；执行路径代码逐字节一致，当日核验）。
> **根因自洽**：该序列被接受边的 KF 间隔 **35–105**（Bonn 多为 30–40）；
> 间隔更长 ⇒ 漂移更大 ⇒ 边不再与里程计一致 ⇒ 图优化真的有活干。
> **⇒ 决策**：① "零修正"结论**收窄为 Bonn-scoped**（已同步
> NARRATIVE/NOTES）；② `f3_st_rpy` 的**回环那一份效应无法从本批三臂中
> 拆出**（rb→gate 含 SWBA+门控+回环）——若 f3_st_rpy 的归因结论
> 依赖"回环为零"，须按预注册补 `final` 臂；③ 是否补臂取决于该序列
> 在本批的**主结论地位**（若它只是 5 条有害序列之一且归因由 rb→sw
> 承载，则 SWBA 归因不受影响）。收口时在 verdict 中明确裁定。


### 2.2 为什么需要 `sw_`（swbaonly）臂

f1_room 的单变量诊断（`diag_f1r_{a,b}`，**该臂 09-12 已跑完 1315 帧全长
但未收口**，本次从落盘 `per_frame_ape.csv` 复算，见
method_review §4 附）指向 **SWBA 是回归主因**（去 SWBA 7.02cm 优于
baseline 8.24cm；保 SWBA 则 17.26–18.10cm）。但那是 **1 seed、单序列**。
本批用 `rb → sw → gate` 三步**同批同码**在 6 序列上重做该归因，
使其成为可入论文的因果证据。

## 三、预注册判据（跑批前锁定）

### K1 执行

done 行=`finished rc=0` **全串**锚定（只查 "finished" 会放过 rc=137，
NOTES 踩坑）。完成时须同时满足：
`grep -c "finished rc="` = 54 **且** `grep -c "finished rc=0"` = 54。
非零退出单独归因后再定补跑。

**K1-b（关卡③ 重大 7 整改）：consolelog 完整性。**
rc=0 **不能**保证 consolelog 完整——`roll_f3_wk_hf_seed0` 实测
rc=0 + tracking OK 但 consolelog 在 kf=600 截断（`MonoGS: Done`=0）。
故每个 run 须额外满足：
`grep -c "MonoGS: Done" <consolelog>` = 1（允许 ≥1 以防多进程重复行）。
`Done`=0 的 run 判**不合格**（即便 rc=0），须补跑——
否则 K3 会因 `edges free=`=0 把它误判为"组件未生效"，
而 K1 会因 rc=0 判它"合格"，**两个判据给出互斥结论**。

**K1-c（关卡③ 致命 2 整改）：consolelog 归属核验。**
对每个 run，核验 consolelog 自报的 run 目录时间戳
（`seed_0/<YYYY-MM-DD-HH-MM-SS>`）**等于**该 run 的
`tables/tracking_raw.csv` 的 `run_id`。不等 ⇒ 该 run 判
"consolelog 与判决数字不同源"，**其 K3 判读作废**（须以 run 目录内
`consolelog` 为准，若缺失则补跑）。
**依据**：既有 rollout 中 f1_room/f1_desk2/f3_wk_hf 三个 run 已实测不一致。


### K2 口径

主读数 `tables/tracking_raw.csv` **col 8（`ate_rmse_cm`，全帧）**，
逐 seed 列出；col 14 仅附表并声明口径。**禁止**用 consolelog 末行 eval
（那是 col 14 口径，NOTES 踩坑）。

### K3 生效验证（按臂实例化 + 整行形状 + 正控）

**禁止**裸模式 `SWBA kf=`（恒 skip 时仍 >0，NOTES 踩坑）；**禁止**
用"`SWBA gate kf=`=0"判组件没跑（该行打印条件与门无关，
`utils/slam_frontend.py:2318-2322`，NOTES 踩坑）。

**计数模式（必须用这些，含 rich 折行/吞标记两道已知坑）**：

- 执行 (a) = `^MonoGS: SWBA kf=\d+: \d+ edges free=`
- 拦截 (b) = `^MonoGS: SWBA kf=\d+:\s+static_conf=[\d.]+ > [\d.]+`
  —— **必须用 `\s+` 而非字面双空格**：rich Console 会插入额外空格，
  用字面空格会漏掉全部 skip 行（本预注册修订中实测：漏计后 delta 假性
  放大到 3–527，改用 `\s+` 后回到 0/1）。**且禁用 `[rel-gate skip]` 字面量**
  —— 该标记被 rich 吞掉（`utils/logging_utils.py:18`，NOTES 踩坑）。
- 合流 (c) = `^MonoGS: SWBA gate kf=\d+: static_conf=[\d.]+ \(max [\d.]+\)`

| 臂 | 判据 |
|---|---|
| `r34_rb` | (a) = 0 **且** `^MonoGS: SWBA` = 0（正控：SWBA 子系统零输出）**且** `MonoGS: LoopClosure` = 0 |
| `r34_sw` | (a) > 0；**(b) 允许 0 或 >0**；`LoopClosure` = 0。**注意**：`r34_sw` 无 `swba_max_static_conf` ⇒ 默认 `max_sc=1.1` ⇒ 该帧恒放行，(c) 行的 `max` 显示 1.10。(c) 在无门臂上**无判别力**（它由 `ReliabilitySignal.enabled` 决定，三臂同开）——**故 `r34_sw` 的有效性证据是 (a) > 0，不是 (c)** |
| `r34_gate` | (a) > 0；**(b) > 0**；**(c) ≥ (a)+(b)**（**不等号，非区间**；见下） |

**delta 判据修正（关卡③ 致命 3 整改，必读）**：
原锁定的 `(a)+(b) ≤ (c) ≤ (a)+(b)+1` 在本批对象上**不成立**。
本次逐 run 复核 22 个 rollout gate run（修正上述计数模式后）：
**20 个 delta ∈ {0,1}，但 2 个为 delta 4/5** ——
恰在本批 6 条之内：
`roll_moving_obstructing_box_seed0` delta=**4**、
`roll_f3_wk_rpy_seed0` delta=**5**。
根因（代码实证）：`gate` 行打印在 `on_new_keyframe` **之前**
（`utils/slam_frontend.py:2320`），而 `edges free=` 打印在其**返回之后**
（`utils/swba.py:815`）；`on_new_keyframe` 有**两条静默提前返回路径**
（`utils/swba.py:693-694` kfs 空；`:697-698` geom 为 None 或点数 <
`min_points`）——该 KF 既无 (a) 行也无 (b) 行，**只有 (c) 行**。
⇒ 判据改为 **(c) ≥ (a)+(b)**（下界锚定，不设上界），
并把 `(c) − (a) − (b)` 的**上界实测值**逐 run 记录入档
（本批预期 0–5，超 5 须归因）。

**K3-c 形态例外登记（关卡③ 重大 7 整改）**：
"(a) 行不存在" 有**三种成因**，须分类记录，不得一律判"未生效"：
1. `0 verified, skip` 型（回环侧）→ 记 "skip"；
2. **静默提前返回型**（本 K3 新登记）→ 该 KF 只有 (c) 行；
3. **consolelog 截断型** → 由 K1-b 拦截，判不合格补跑。
**回环修正行的读取必须先去折行**（rich 硬换行，
`scripts/paper2_rollout/parse_swba_log.py` 已是跨行解析实现，复用勿重写）。

**回环自证（§2.1）**：`r34_gate` 臂的 `corrections |dt| med X cm max Y cm`
行——**去折行后**记录逐 run 的 med/max；若任 run max > 0 ⇒ 触发 §2.1 的补臂流程。
既有 6 条的实测（本次复核）为 **6/6 全 `med 0.00cm max 0.00cm`**，verified 数 2–6。


### K4 单变量保持

L1 断言（`test_r34_rollout_configs`）：
① `r34_rb` 与源臂 `rollbase_{seq}.yaml` 逐字段一致（仅 save_dir 异）；
② `r34_gate` 与源臂 `roll_{seq}.yaml` 逐字段一致（仅 save_dir 异）；
③ `r34_sw` = `r34_rb` + `SWBA.enabled: true`（**逐字段差仅此一项**）；
④ 三臂 `inherit_from` **同一基座**、且与源臂一致
（**注意：本批 6 序列混编 TUM 与 Bonn——`moving_obstructing_box` 的基座是
`configs/rgbd/bonn/moving_obstructing_box.yaml`**，故基座须从源 config 派生
校验，不得硬编码 `tum/` 前缀；本预注册首版即写错，已被 L1 用例拦下）。
**边界**：该断言只走 YAML 字面量、不解析 `inherit_from`/`method_from`
合并链（`utils/config_utils.py`），故**不验证运行时组件集**——
三臂的 `method_from` 层完全相同（同一 `combined_prune/method.yaml`），
两侧对称故无碍。
**补充**：收口时抽查 ≥3 个 run（三臂各一）的运行时 `config.yml`
与对应源臂旧 run 做 diff，差异只应限路径。

**K4 运行时抽查（2026-09-17 跑中已做，f1_desk2 三臂 seed0）**：
从各 run 的 `datasets_tum/.../config.yml`（合并后运行时态）读出：

| 臂 | `SWBA` | `LoopClosure` | `ReliabilitySignal.enabled` |
|---|---|---|---|
| `r34_rb` | **None（无块）** | **False** | True |
| `r34_sw` | `{enabled: True}` | **False** | True |
| `r34_gate` | `{enabled: True, swba_max_static_conf: 0.38}` | **True** | True |

⇒ `rb` vs `sw` 的差集**恰为 `{SWBA}`**；`sw` 无 `LoopClosure`；`gate` 带
0.38 阈值与回环块。**与设计一致**（也确认 §三 K3 对 `r34_sw` 的判据说明：
`ReliabilitySignal` 三臂同开 ⇒ 该臂 `SWBA gate kf=` 行由 `SWBA.enabled` 决定）。

### K5 一致性判据（核心科学判据）

**冻结参照 = §一 表的 1-seed 值，复算口径必须一致（col 8，全精度见 §1.2）**。

- **主判据（复现性，关卡③ 重大 4 整改）**：`r34_rb` 与冻结 `rollbase`
  1-seed 值逐序列比对，|Δ| 须 ≤
  **`max(1.0cm, 该序列旧观测的 seed 内极差)`**。
  - 为什么不是固定 1.0cm：跨批地板 0.18–0.62cm **只在标准 Bonn 测过**，
    本批序列无自有地板测点（§1.1）；而本批含高方差族
    （`roll_f3_st_hf` seed 内极差 31.2cm）。固定阈值会**必然误报**。
  - 已知的既存突破点（如实登记）：`f1_room` 上 SWBA-关 的两个臂
    （`rollbase_f1_room_seed0` col8 8.2384 vs `diag_f1r_b_seed0` 7.0213）
    实测 |Δ| = **1.217cm > 1.0cm** ⇒ 固定 1.0cm 在本批对象上**已被历史数据突破**，
    这也是改判据的直接证据。
- **归因触发器（补判定规则，不再只说"不得直接收口"）**：若某序列超上阈值，
  **依次**执行：① 核 K1-b/K1-c（run 完整性 + consolelog 归属）；
  ② 核两臂运行时 `config.yml` diff（应只限路径与臂名）；
  ③ 若 ①② 均干净，则该序列**改判"该序列不可复现"**，
  在结论中**从 5 条有害清单中剔除**（不得计入 K6 分子/分母），
  并把剔除记入 verdict——**这不是"跑没了"，是判据本身的止损出口**。
- **归因判据（本批要回答的问题）**：对 5 条有害序列，
  逐序列比较 `rb → sw` 与 `rb → gate`：
  - 若 `|Δ(rb→sw)|` 已 ≥ 最终 `|Δ(rb→gate)|` 的大部分 ⇒ **归因 SWBA**；
  - 若 `rb→sw` ≈ 0 而 `gate` 才恶化 ⇒ **归因门控本身**（须查
    门控是否把 SWBA 从"有益"拦成"有害"）。
  - 逐 seed 与均值**都**判。
- **对照方向**：`f1_desk2`（1-seed 为 −3.67 有益）用于检验**方向是否复现**。
  **功效声明**：n=1 序列的符号**不足以**支撑或否决 19 条层面的主张
  （关卡③ 重大 2 指出）；它的作用仅是把"符号随机"这一可能摆上台面。

### K6 不变量（数字阈值，防"重跑把结论跑没了"）

- 5 条有害序列：`r34_gate` vs `r34_rb` 的 Δ **仍为正**（方向一致）且
  **逐 seed 均值 |Δ| > 1.0cm** 者 ≥ **3 条**（分母为**未被 K5 剔除者**，
  正常情形为 5；若 K5 剔除 ≥3 条则该主张自动降级为"不可复现"）；
- `f1_desk2`：Δ **仍为负**（方向复现）；
- 任一条不成立 ⇒ 结论行改为"不成立/部分不成立" + 止损项，
  **不得**保留原判读（D3 保护对象是 run 目录原始输出，
  非 verdict/README/manifest）。

### K7 简化臂外推限制（关卡③ 重大 6 整改；D2/账本事故同族）

`r34_rb` 的指纹（`DeferredCommit/ReliabilitySignal/RobustTracking/SemanticMask`，
无 SWBA/回环）**正是 health_check 点名的"简化臂外推风险"**。
本批内部使用正确（rb 只作**同批对照**，不外推）；
但其数字将进入 `rollout_panel.csv` 的 `baseline_ate_cm` 列 ⇒ **该列必须标注**：
"固定栈 baseline（SWBA/回环/门控全关），仅作同批对照；
**不得**单独作为方法对照或跨实验外推"。
（账本事故模式 = 简化臂结论被外推，P2/D2。）

## 四、成本与风险

- 成本：**54 run**（= 3 臂 × 6 序列 × 3 seed）。**实测口径**
  （关剌③ 次要 1 整改）：从 rollout done 文件取本批 6 序列的 12 个
  源 run 实测时长——mean **74.7 min**、median 49.9、**max 245.1**
  （`roll_f3_office` 245min 与 `rollbase_f3_office` 180min **两条独立观测
  都在 3–4h 档，不是单例异常**，原稿"疑受并发干扰"的排除不成立）。
  按 cfg-major/seed-inner 顺序 + `NR%4==w` 轮转模拟 54 job：
  4 worker 负载 942/980/1002/1109 min ⇒ **makespan ≈ 18.5h**。
  ⇒ **值守 ≥ 20h**（原稿 ≥14h 低估约 30%）。
- 风险 1：远程卡被机器主人占用 → 派发前 `nvidia-smi` 两卡实查
- 风险 2：长批内漂移 → 按序列交错三臂摊平；K5 用它判定
- 风险 3：`r34_rb` 出现系统偏移 ⇒ 两臂不同码 → K5 归因触发器（已补判定规则）
- 风险 4：`f3_office` 三臂 3 seed 共 9 run，若都在 3–4h 档 ⇒
  该序列单独贡献 27–36h 卡时，**是 makespan 主导项**
- 风险 5：远程磁盘 → 派发前查余量（54 run 轻量产物，实测 13–48MB/run，
  合计 ≈1.9GB，相对 55G 余量无风险）


## 五、纪律映射

- 预注册先行（本文件）✓
- 零代码改动（纯 config）✓
- 3 seed ✓
- 生效验证（K3，按臂实例化 + 整行形状 + 正控）✓
- 判据先锁定、跑批在后 ✓
- 关卡③（正式批派发前过 `slam-critic`）→ 见 §七

## 六、执行顺序（派发前必须逐条走完）

0. **前置（关卡③ 致命 1 整改——原文此处自相矛盾，照抄必失败）**：
   `check_code_sync.sh` **只校验、不推送**（其 :36/:70 只打印 push 提示），
   而 `sync_to_remote.sh:19` 有 `BRANCH=mask_fix_iter` 硬编码坑（会切错分支）。
   故**必须显式执行**：
   ```
   # 本地
   git push origin dev/v2
   git rev-parse HEAD                       # 记为 LOCAL
   # 远程
   ssh jiangwenheng@172.16.227.24 'cd /home/jiangwenheng/cron/monogs-ours && \
     git fetch origin && git checkout dev/v2 && git pull --ff-only origin dev/v2 && \
     git rev-parse HEAD && ls configs/experiments/paper2_rollout/r34_*.yaml | wc -l'
   ```
   **门禁**：远程 HEAD == LOCAL **且** 远程能列出 **18** 个 r34 config
   （configs 不在远程 HEAD 上 ⇒ 54 job 全 rc≠0）。
   随后远程 `nvidia-smi` 两卡实查 + 无存活 `slam.py`。
1. **派发**（顺序即队列顺序，勿改）：
   ```
   REPAIR_CFGS="r34_rb_f1_room r34_sw_f1_room r34_gate_f1_room \
   r34_rb_f1_desk2 r34_sw_f1_desk2 r34_gate_f1_desk2 \
   r34_rb_f3_st_rpy r34_sw_f3_st_rpy r34_gate_f3_st_rpy \
   r34_rb_f3_office r34_sw_f3_office r34_gate_f3_office \
   r34_rb_moving_obstructing_box r34_sw_moving_obstructing_box r34_gate_moving_obstructing_box \
   r34_rb_f3_wk_rpy r34_sw_f3_wk_rpy r34_gate_f3_wk_rpy" \
   DONE_FILE=r34.done SEEDS="0 1 2" \
   CFG_SUBDIR=paper2_rollout OUT_SUBDIR=paper2_rollout \
   RUN_LIST=/home/jiangwenheng/r34_jobs.txt \
   nohup bash scripts/paper2_rollout/run_batch.sh > /home/jiangwenheng/r34_batch.out 2>&1 < /dev/null &
   ```
   （**不要**设 `TAG_PREFIX`。`RUN_LIST` 必须私有——NOTES 踩坑 P10
   并发批共用队列文件会互相覆盖。`CFG_SUBDIR`/`OUT_SUBDIR` 是
   `scripts/paper2_rollout/run_batch.sh:22-23,39` **真实支持**的变量，
   无需改动 runner——原文"见 §七 处置"已删。）
2. **完成判据**：`r34.done` 出现 `batch all done`，且
   `grep -c "finished rc="` = 54、`grep -c "finished rc=0"` = 54
   （**并**逐 run 过 K1-b `MonoGS: Done`=1 与 K1-c consolelog 归属）
3. 拉回轻量产物 → 关卡①（落 verdict 前过 `slam-critic`）→ 出裁决
4. 关卡②（论文数字/骨架入表前再过 `slam-critic`）
5. 下游联动：`results/paper2_rollout/rollout_panel.csv`（补 baseline 列 +
   K7 标注）、`results/paper2_rollout/README.md`、
   **`results/paper2_rollout/evidence/manifest.json` 须显式更新**
   （关卡③ 重大 5；R33 同型项曾被判重大成立：manifest 未随批更新会
   与面板事实源矛盾）、`papers/paper2/NARRATIVE.md` §7 第 5/6 条、
   "5-12×" 锚定（paper2_plan:178 / rollout README:48 / NARRATIVE:339）

## 七、关卡③ 审查记录（2026-09-17）

`slam-critic` 输出 **Reject（3 致命 + 7 重大 + 4 次要）**。
逐条独立复核后处置（详见证件链，本次全部自行复算）：

| # | 发现 | 独立复核 | 处置 |
|---|---|---|---|
| 致命 1 | 代码未 push（local 领先 origin 1），且 §六 第 0 步的同步路径自相矛盾（`check_code_sync.sh` 只校验不推送） | **成立**（`git rev-list --count origin/dev/v2..HEAD`=1；该脚本 :36/:70 只打印 push 提示） | **采纳**：已 `git push`（origin=012aa13a）；§六 步 0 改为明确的 push + 远程 pull |
| 致命 2 | K5 冻结参照来源不明：顶层 consolelog 自报 save_dir 与 tracking run_id 不一致（5/6），同一 seed 下并存两个 run 目录 | **成立**（本次逐条复算：f1_room/f1_desk2/f3_wk_hf 不一致；f1_room 两目录并存：18:09 无 config/per_frame，22:25 有） | **采纳**：新增 §1.2 记录取数裁定（**冻结值取自 tracking_raw 所在目录，已用 per_frame_ape 独立复算验证**）+ 新增 **K1-c** consolelog 归属核验 |
| 致命 3 | K3 的 `(a)+(b) ≤ (c) ≤ (a)+(b)+1` 在本批对象上不成立（delta 可达 4/5） | **成立，但根因与 critic 表述不同**：critic 称"18 个 run delta 0/1"，我实测**全部 22 个 delta 都 >1**——差异源于计数模式：我的 skip 模式用字面空格，**rich Console 插入了额外空格**导致 skip 全漏。改用 `\s+` 后：**20 个 delta∈{0,1}，2 个为 4/5，恰在本批 6 条内**（moving_obstructing_box / f3_wk_rpy） | **采纳**：K3 判据改 **(c) ≥ (a)+(b)**（去上界）；补两处 rich 计数坑（`\s+`、禁 `[rel-gate skip]` 字面量）；根因代码定位 `utils/swba.py:693-698` 静默返回 |
| 重大 1 | 省掉 final 臂的论证基于标准 Bonn，自证手段在 held-out 上不可靠 | 成立（机制论证本身我复核为对，但自证形态有 3 类：有行/折行/无行） | **部分采纳**：补"去折行"操作 + 复用 `parse_swba_log.py`；**保留 3 臂设计**（理由：R33 42-run 恒零修正是结构性论证，且本批 gate 臂 6/6 实测仍为 0.00cm）；若 K3 自证出现非零则补 final 臂 |
| 重大 2 | 1.5cm 阈值未考虑序列自身 seed 方差（本批含 f3_st_hf 双峰） | **成立**（`roll_f3_st_hf` seed 内极差 31.2cm vs 标准 Bonn baseline 0.608cm） | **采纳**：§1.1 如实登记为"本设计最强自认弱点"，交由 K5/K6 复现判据检验；f1_desk2 功效声明补"n=1 不足以支撑/否决 19 条主张" |
| 重大 3 | `r34_sw` 的 `(c)` 判据无判别力（无门臂 max_sc=1.1 恒放行） | **成立** | **采纳**：K3 表明确"r34_sw 的有效性证据是 (a)>0 而非 (c)" |
| 重大 4 | K5 的 1.0cm 容差过紧且归因触发器无判定规则 | **成立**（`f1_room` 上两个 SWBA-关臂实测 |Δ|=1.217cm **已突破 1.0**） | **采纳**：改 `max(1.0cm, 该序列 seed 内极差)`；补 ①②③ 判定规则 + "改判不可复现并剔除"的止损出口 |
| 重大 5 | 下游清单漏 `manifest.json` 具体更新项 | 成立（R33 同型项曾被判重大） | **采纳**：§六 步 5 显式列出 |
| 重大 6 | `r34_rb` 是 health_check 点名的"简化臂外推"指纹，未登记限制 | **成立**（health_check WARN 原文含 DeferredCommit/ReliabilitySignal/RobustTracking/SemanticMask=rb 指纹） | **采纳**：新增 **K7** 简化臂外推限制 + 面板列标注要求 |
| 重大 7 | K1/K2 未覆盖"rc=0 但 consolelog 截断" | **成立**（`roll_f3_wk_hf_seed0`：rc=0 + tracking OK + `Done`=0/`LoopClosure`=0） | **采纳**：新增 **K1-b**（`Done`=1 存在性判据）+ K3-c 三形态例外登记 |
| 次要 1 | 成本估算偏低约 28% | **成立**（12 个源 run 实测 mean 74.7min/max 245.1；模拟 makespan **18.5h**） | **采纳**：§四 全面重写，值守 **≥20h**；删"f3_office 疑异常"的排除 |
| 次要 2 | §六 把"run_batch 需支持 CFG_SUBDIR"挂在待填的 §七 | 成立（脚本已支持） | **采纳**：删除该括注 |
| 次要 3 | §一 表取整显示（9.87 vs 9.8650）不应进冻结参照 | 成立 | **采纳**：§1.2 声明冻结参照为全精度 col 8 |
| 次要 4 | "无修正行"只登记 1 种成因，实为 3 种 | 成立 | **采纳**：并入 K3-c |

**已确认无误（省却自证成本）**：18 个 config 的族结构（rb==rollbase、
gate==roll、sw==rb+SWBA 且无 LoopClosure）critic 逐条 diff 复核一致；
L1 门禁 4 passed；§一 的 6 个 col 8 值全部独立复算一致；
派发命令 18 个 cfg 与磁盘一一对应；远程双卡空闲无残留。

**未能验证项（如实记录）**：各臂运行期远程 HEAD 无法硬证
（远程 reflog 仅回溯至 09-13）；运行时 conda 环境快照无历史；
6 条序列无自有跨批噪声地板实测（§1.1 已声明为债务）。

