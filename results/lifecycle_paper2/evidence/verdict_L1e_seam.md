# verdict_L1e_seam — 缝隙带救援族终局判决（D2-008）

> **双溯源**：测量代码 = `19fd2e3a`（seam 实装 + 两 config + 派发脚本 + 渲染清单，先于批次）+
> `cee6172b`（判据机，先于批次完成）；分析代码 = 同左 + `773d826a`（eval_utils 键表补交，
> 执行件，仅影响 CSV 列不影响判定）+ `43cf412d`（渲染清单 tag 名纠错，执行件）。
> **关卡①**：slam-critic **先于本文件落盘**（2026-09-24，Accept-with-conditions，0 致命 /
> 2 重大 / 2 次要，条件清零见 §7；全量报告 /tmp/l1e_gate1_critic.md）。
> 写作纪律自查（NOTES 三问）：本判决为**负结果**，只作 §6 边界小节素材——不进贡献栏、
> 不命名、不作 headline；fill 插入等正面读数仅作诊断读数陈述（§5 措辞约束）。

## 0. 一句话终局

主判两臂皆败（seam 1/3 负、param 0/3 负）⇒ 预锁击杀分支补 s{3,4,5}（6/6 rc=0）⇒
6-seed 配对重判 seam **1/3 对达标、param 0/3（VERDICT_KILL 程序化 True）**⇒
**缝隙带救援族按 prereg §6 关闭**（seam+param 双臂一并，关闭范围预锁：不再有本方向
变体——含调 seam_tau/seam_delta/seam_warm 的组合）；**C 路线启动**（论文重定位一页纸
呈用户过目，写作解冻不晚于 10-01）。

## 1. 主判据（程序化；`l1e_seam_judge.py --arm <arm>` 逐字输出为权威）

| 臂 | freshvac Δ（3 seed） | n_neg | mean | 门槛 | PASS |
|---|---|---|---|---|---|
| seam | +0.062 / +0.597 / −0.267 | 1/3 | +0.130 | 1.19 | **False**（D① 未命中：seam carved Σ=0/3） |
| param | +0.719 / +2.315 / +0.477 | 0/3 | +1.170 | 1.19 | **False**（carve 5/1/2 点火但全正） |

## 2. 确认重判（prereg §6 预锁分支；6/6 rc=0，l1e_confirm.done）

**"配对重判"读法声明（critic 次要-1 整改）**：prereg §6 未定义"配对"形状；本判决采用
**L1c/L1d 判据机同形同号对**读法（{s0,s3}{s1,s4}{s2,s5}，对达标 ⟺ 两 seed 同负 ∧
|mean|>门槛）——先例 = `l1d_stacked_judge.py:172-197`；"∀6 负"读法无文本支撑。
两读法对 seam 殊途同归（配对 1/3 不达标；∀6 亦 4/6<6 FAIL），判决不受读法选择影响。

| 臂 | 6-seed Δ 全景 | 配对判定 | 结论 |
|---|---|---|---|
| seam | +0.06/+0.60/−0.27/−0.72/−1.03/−2.37（mean **−0.620**） | s0/s3 反号 ✗；s1/s4 反号 ✗；**s2/s5 同负且 |mean|=1.32>1.19 ✓** | **1/3 对达标 < 3 ⇒ 不过** |
| param | +0.72/+2.32/+0.48/−1.62/+1.57/−1.01（mean **+0.408**） | 三对全 ✗ | **0/3 ⇒ VERDICT_KILL=True** |

**防漂移声明（critic 清单 6 整改）**：seam s3-5 呈单调递进（−0.72→−1.03→−2.37）且
mean −0.62 接近门槛——**不构成继续补 seed 的文本依据**：prereg §6 的关闭条件是
"重判仍不过"，n_pairs_hit=1 < 3 即为不过；族关闭含参数变体（seam_tau/seam_delta/
seam_warm 的任何取值组合），重开须全新机制族 + 新 prereg（照 prereg_L1d §6 句式）。

## 3. 约束门 + 误删护栏（先锁语义，程序化）

- 约束门：seam s0 双过 / s1 PSNR 越（−0.46dB）/ s2 ATE+PSNR 双越；param s1 PSNR 越
  （−0.43dB）余过。越门不自动 FAIL，逐 seed 并陈如上（判据机 constraint_gates 字段）。
- **误删护栏**：两臂 12 run `mean_static_coverage` 全 ≥0.99（invalid_runs=[]）——
  护栏绿、无挖洞形态；**判决败于判据而非安全性**。

## 4. 机制归因（critic 重大-1/2 整改后的可支撑表述）

1. **"α 门一票否决"被证伪**：6 seed 的 alpha-seam 行 a_min 全批最小 =
   [0.2582, **0.2043**, 0.2508, **0.2204**, **0.1631**, **0.2322**]——4/6 低于
   seam_tau=0.25，其中 s4 a_min=0.1631 仍 carved=0。立项依据里的"α 地板 0.2582"
   是 **s0 单 seed 读数，不得冒充臂级结论**。
2. **可支撑的最强表述**：本批无任何基元同时满足四合取（carved Σ=0，三 seed 全零，
   consolelog alpha-seam 行 115 KF 全量在档）。**第一拦截者无法从现有工件定位**——
   alpha-seam 行只报 vacated_px/hist_regions/carved/a_min 四键，缺带内/obs_count
   分量计数（slam_backend.py:1215-1217 打印面）；定位它需要新插桩 = 新 run = 已关闭
   方向的变体，不做（§0 关闭范围预锁）。
3. **诊断修正**：立项依据 `offline_diagnosis_2026-09-23.md` §4 的"α 钉 0.2199"
   为 exit 模式读数；本批证明 **α 地板随模式漂移**（exit_fill 下 0.163-0.258 跨
   seed 分布）——"把 τ 设在诊断钉死值上方即可点火"的前提不成立，这是 param 臂
   （tau=0.25 点火 5/1/2）与 seam 臂（零点火）共同给出的新读数。
4. **点火≠改善（param 臂）**：carve 点火 5/1/2 + fill 插入后 Δfv 仍 0/3 全正——
   与 crowd3 形态同向（删的对象仍非鬼影或洞未补对），缝隙带几何不是充分条件。

## 5. fill 通路读数（诊断级，措辞约束：非"首次工作"）

critic 次要-2 整改：fill 在 pt 的插入事件为**每臂仅 s0 各一次**（seam s0 inserted=138/
62 步、param s0 inserted=419/54 步；其余步骤与全部其余 seed inserted=0）。正确表述 =
"s0 各发生一次插入事件"，**不写"fill 在 pt 首次工作"**（能力性措辞，D2-007 重大3
先例）。单事件与 Δfv 无改善并存，说明插入的背景未被保留或不在 freshvac 支撑区——
机理未定位，同 §4.2 不追插桩。

## 6. 工件键索引

- 判据机：`l1e_seam_judge.py`（--arm seam/param = 主判；--arm X --confirm = §2）
- 训练：`l1e.done`（6/6 rc=0）、`l1e_confirm.done`（6/6 rc=0）
- 渲染：`render_L1e_person_tracking_{seam,param}_s{0..5}_canon/`（12/12 n_frames=17）
- 计数器：`L1e_*_s*/tables/efficiency_raw.csv`（**s0-2 无 seam 列**——键表 773d826a
  补交前落地，seam 计数以 consolelog alpha-seam 行为权威；s3-5 CSV 有列且 carved=0
  与日志一致）；引用计数一律列名 DictReader（efficiency_raw 含带引号字段，裸列号错位）
- consolelog：`L1e_person_tracking_{seam,param}_s{0..5}.consolelog`
- 关卡①：/tmp/l1e_gate1_critic.md + /tmp/l1e_gate1_facts.md

## 7. 关卡① 条件清零（Accept-with-conditions → 本判决可落盘）

| # | 条件 | 处置 |
|---|---|---|
| 重大-1 | "α 地板"单 seed 冒充臂级 | §4.1 改为 6-seed a_min 全景 + s4 反例；亲核成立（本地 consolelog 复算一致） |
| 重大-2 | 零点火归因超工件 | §4.2 改为"四合取未同时满足，拦截者未定位" |
| 次要-1 | 配对读法未声明 | §2 读法声明块 |
| 次要-2 | "首次工作"措辞 | §5 改"每臂仅 s0 各一次插入事件" |

## 8. 出口执行（prereg §6）

- **缝隙带救援族关闭**（seam+param 双臂一并 + 参数变体范围预锁）。
- **C 路线启动**：论文重定位一页纸（叙事重心/主张清单与 balloon2+mvnobox+边界证据
  匹配）呈用户过目后动笔；写作解冻不晚于 2026-10-01（CVM 摘要 10-23）。
- 负结果去向：§6 边界小节素材（四条 α 通路 + gate×occ 叠加 + 缝隙带救援，机理链完整：
  掩码 ✓ → α 压制 ✓ → 几何带宽 ✗ → 缝隙带修复 ✗ → fill 单事件未保留）。

## 9. 反悔方式

R6 一句话否决（撤 D2-008 终局）；重开须全新机制族 + 新 prereg；GPU 沉没 ≈3h。
