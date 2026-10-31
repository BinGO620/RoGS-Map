# verdict_L1d_stacked — gate×occupancy 叠加棘轮终局判决（D2-007）

> **⚠ 2026-09-24 对照臂批源标注（D1-014 M3 整改；不改动本判决原文与 PASS/FAIL）**：
> 本判决 6-seed 配对的对照臂（exit）**混两个批**——s0-2 来自 L3 批
> （`render_L3_person_tracking_exit_s{0,1,2}_canon`）、s3-5 来自 L1c 确认批
> （`render_L1c_person_tracking_exit_s{3,4,5}_canon`，8f90f00d/5e6a42eb 补齐件）。
> 原文披露了"零新增对照 run"但**未设批次等价性门**。影响评估：本判决为**负结论**
> （0/3 对达标、双向散布），混批只增噪声、不掩盖一致信号 ⇒ **结论方向不受威胁**；
> 但本判决的 6-seed 数值**不得作跨批绝对值引用**。per-frame median[IQR] 重读表
> （`judge_reread_median_2026-09-24.md`，s0-2 off=L3 exit / s3-5 off=L1c exit 映射）已给出第二读法。

> **双溯源**：测量代码 = `ed50fbdb`（判据机主分支 + 单测，先于主批判决）+
> `8b1033cd`（--confirm 确认分支，先于确认批判决）+ `a0daa144`（执行件补提交：
> tpl_exit s3-5 前缀兼容，critic 重大2 整改）；分析代码 = 同上（本批无其他分析代码）。
> **零新代码**成立面 = slam.py + gaussian_splatting/ + utils/ 本批逐 commit 复核零改动
> （基线 7094abd4 → HEAD 全部为脚本/测试/派发/文档）。
> **关卡①**：slam-critic **先于本文件落盘**（2026-09-23，Accept-with-conditions，
> 3 重大/3 次要，条件清零情况见 §7；全量报告 /tmp/l1d_gate1/critic_report.md）。
> 写作纪律自查（NOTES 三问）：本判决为**负结果**，只作 §6 边界小节素材——不进贡献栏、
> 不命名、不作 headline；"棘轮/carve 点火"等词仅作机制读数描述，非贡献表述。

## 0. 一句话终局

**主判据 1/3 负 PASS=False ⇒ 预锁击杀分支执行（确认批 3 run + 渲染 3）⇒ 6-seed 配对
重判 0/3 对达标 ⇒ gate×occupancy 链式假说按 prereg §6 关闭**（关闭范围预锁：不再做
任何 gate×occupancy 纯 config 组合变体，含调参；重开须全新机制族 + 新 prereg）。

## 0.1 确认重判（预锁分支 §6；`l1d_stacked_judge.py --confirm` 程序化输出为权威）

| 对 | Δ(stacked−exit) 两 seed | 同负 | 幅度>1.19 | 达标 |
|---|---|---|---|---|
| s0/s3 | +2.5837 / **−2.8298** | ✗ | ✗（|mean|=2.71 但方向不同号） | ✗ |
| s1/s4 | +1.0833 / **+2.0456** | ✗ | ✓ | ✗ |
| s2/s5 | −0.6979 / −1.4823 | ✓ | **✗（|mean|=1.0901<1.19）** | ✗ |

- **0/3 对达标 ⇒ VERDICT_KILL=true（程序化）**。6-seed Δ 全景：
  +2.58/+1.08/−0.70/−2.83/+2.05/−1.48（mean **+0.117**）——双向散布、无臂间一致信号；
  s3（−2.83）与 s4（+2.05）相邻反号大幅对称，与 L1c 同型 = 管线混沌形态
  （L1b s0 单点 21.05 教训：单点不可归因）。
- 执行件：stacked s{3,4,5} 3 run + 渲染（`l1d_confirm.done`，3/3 rc=0）；
  对照 exit s3-5 沿用 L1c 确认批补齐件（`render_L1c_*` 前缀，8f90f00d/5e6a42eb），
  **零新增对照 run**（prereg §2 承诺兑现）。

## 1. 主判据（程序化；`l1d_stacked_judge.py` 逐字输出为权威）

freshvac（canonical）：stacked = [5.453, 4.5132, 3.245]，
exit = [2.8693, 3.4299, 3.9429]；Δ = [+2.584, +1.083, −0.698]；
**1/3 负，mean +0.9897 < 门槛 1.19（off_sd=0.670 < 地板）⇒ PASS=False，tier 3**。

## 2. 约束门（prereg §4：越门不自动 FAIL，逐 seed 如实并陈；喂 L2 headroom 设计）

| seed | ATE Δ（stacked−exit） | ATE 门（≤+0.5cm 且 ≤+5%） | static PSNR Δ | PSNR 门（≥−0.25dB） |
|---|---|---|---|---|
| s0 | +0.92cm（13.77 vs 12.85） | **越**（+7.2%） | +1.06dB | 过 |
| s1 | −1.46cm（10.42 vs 11.87） | 过 | −0.09dB | 过 |
| s2 | +2.72cm（13.71 vs 11.00） | **越**（+24.7%） | −1.01dB | **越** |
| s3 | −2.18cm（9.38 vs 11.56） | 过 | +0.76dB | 过 |
| s4 | −2.10cm（11.08 vs 13.18） | 过 | +0.93dB | 过 |
| s5 | −0.43cm（10.36 vs 10.78） | 过 | +0.88dB | 过 |

主判 3 seed（s0/s1/s2）代价 profile：1/3 双过、1/3 单越、1/3 双越——叠加未复现
L1b 的"三 seed 一致 −1.74dB"（本批 s0 反而 +1.06dB），代价方向在 seed 间不一致。

## 3. 诊断预测四键（prereg §5 预锁，不作判据；全部程序化读取）

| 键 | 预测 | 实测 | 结论 |
|---|---|---|---|
| D① | a_min 占驻段单调下行穿 0.20 | **非单调**（占据/离开交替；但 s0 末段 60+ KF 钉 0.1845、s2 计 60 个 KF a_min<0.2199——穿阈真实发生） | 未命中（穿阈发生但非单调） |
| D② | carve 首次 >0 | s2=1（KF100）、s4=1、s5=2；s0/s1/s3=0 | 臂内多 seed 零星命中 |
| D③ | 不触 α≥guard | lt_guard 有界（18690/8378/1307/3938/4435/2097）、static_coverage 0.99-1.0 | 过（安全性同 L1c） |
| D④ | 人走后 a_min 末段回升 | 三主判 seed tail_rebound=False（人走后 hit=0 capped=0，a_min 平台非回升） | 未命中 |

## 4. 机制形态：混合型（不属于 prereg §5 任一预锁纯形态）

批评员复核确认（关卡① 清单 4）：本批**既非 combination_inert**（capped 1.7-2.1 万
全 seed 点火、棘轮穿阈真实发生）**也非纯 window_race_failure**（s0 穿阈后钉死
0.1845 达 60+ KF 而 carve=0——合取门 in_front/持续性不满足，非 EMA 回升跑赢）。
如实归类 = **混合形态**：机制全部点火 + 棘轮穿阈在真实训练中发生 + carve 零星非零 +
freshvac 无一致改善。三个具体机制读数（consolelog/CSV 复核）：

1. **guard 平台期**（新读数）：s2 有 26 个 KF 钉 a_min≈0.3466（≈guard 0.35）——
   棘轮只在 α<guard 时工作；warm 区内 α>guard 的基元不衰减，等 EMA 缓降后才能进入
   棘轮作用域。衰减窗口被 guard 切成分段。
2. **穿阈≠删除**：s0 穿阈后 a_min 钉死 0.1845 达 60+ KF（hit=0 capped=0 = 人已离开）
   却无 carve——残影以 0.18 α 持续渲染。α<tau_carve 只是 carve 合取门之一，
   in_front/持续性才是 pt 场景的真瓶颈（postmortem 结论在叠加形态下再次成立）。
3. **freshvac 与机制读数无因果**：s2 carve 点火 + 60 KF<0.2199 却是 6-seed 最好
   （Δ=−0.70）；s0 穿阈+钉死反而最差（Δ=+2.58）。主判据测的是新鲜腾空区渲染误差，
   机制读数无法预测它（与 L1b"改善非 carve 路径"结论一致）。

**纠错（关卡① 重大3，批评员 DictReader 双重核验，我亲核成立）**：prereg §5 D② 与
一页纸 §1 的"carve 在 pt 族从未发生过"**是假事实**——L1b_gate_s2 carve=2、
L1c_occ_s3=1、L1c_occ_s5=2 均早于本 prereg 落盘。verdict 措辞统一降格为
"L1d 臂内多 seed 零星命中"；先验错误如实登记（prereg 不追溯改，以此块为准）。

## 5. 执行有效性（prereg §7 计数器契约 + 例外备案）

- capped>0 ∧ warm>0 全 6 seed；no_mask_kfs=0 全 seed（fail-open 无发生）；
  层 1-4 验证（diff/两态实例化/组合棘轮单测/提交纪律）派发前全过。
- **例外备案（关卡① 重大1，反驳通道采纳）**：s2 主判 run `occ_decay_events_total=0`
  字面命中"任一标签计数器=0 ⇒ run 无效"。亲核语义：s2 的 warm 区全程与 α<guard
  基元**空间错开**（116 KF warm 最大 2412 基元而 decayed 全 0；lt_guard=1307 计的
  是全部 <guard 观测、与 warm 无交集），即"occupancy 记忆在工作、但无可作用对象"
  ——decay=0 是**真实读数而非机制未运行**（occupancy 行 116 KF 全在打印、
  warm_prims=61459 为累加口径）。处置：s2 保留进判决（机制确实运行），若按契约
  剔除 s2 则主判 2 run 不足 3 对、确认判 s2/s5 对缺失——两种处置下终局判定不变
  （主判 PASS=False 已定，确认判 0/3 不依赖 s2 单点）。契约的"计数器=0 ⇒ 无效"
  应精确化为"臂机制**入口**计数器=0"（capped/observe），"出口"计数器（decayed/
  carve）=0 是合法读数——NOTES 回填此语义区分。

## 6. 交付三件套

1. **渲染指标表**：§1-§2 全部数字自 `render_L1d_*_canon/render_metrics.json` 程序化读取；
2. **跟踪指标表**：§2 ATE 列自 `L1d_*/tables/tracking_raw.csv`；
3. **渲染图 vs 原图**：`render_L1d_person_tracking_stacked_s{0..5}_canon/cmp_f*.jpg`
   17 帧 × 6 seed（含重点帧放大框；本地留档，按 2026-09-23 gitignore 政策不入 git）。
   抽检：s0 f215 残影与 s2 f215 对照可见臂间/seed 间形态差异。

## 7. 关卡① 条件清零（Accept-with-conditions → 本判决可落盘）

| # | 条件 | 处置 |
|---|---|---|
| 重大1 | s2 decay=0 契约冲突未处理 | §5 例外备案（反驳通道：真实读数非机制未运行 + 双处置终局不变） |
| 重大2 | 判据机 4 行未提交即产出 confirm 数字 | `a0daa144` 补提交；数字复算不受影响（批评员已独立复算） |
| 重大3 | "pt 族历史首次 carve"假事实 | §4 纠错块；措辞全篇降格 |
| 次要1 | 确认批计数器漏记 | §0.1/§4 补齐（s4=1、s5=2） |
| 次要2 | 约束门逐 seed 并陈 | §2 表 |
| 次要3 | health sync FAIL | a0daa144 push 后自愈（0 FAIL） |

## 8. R2 关闭判定（防漂移声明）

- **s2 carve=1（及 s4/s5 的 1/2）不构成 R2"新证据"**：单点/零星点火 + 6-seed 无一致
  信号，与 L1c 先例（D1-008 曾交裁定的 161/175 大数点火亦未重开）同判；本族母假设
  （不动点推导）已被 6-seed 数据正面否定（棘轮发生≠残影删除≠渲染改善）。
- **关闭范围（prereg §6 预锁）**：不再做任何 gate×occupancy 纯 config 组合变体
  （含调 tau/β/warm/guard）；occ v2 per-primitive identity = 新机制族，若立项走
  新 D2 呈报 + 新 prereg（本批混合形态提示其瓶颈在合取门几何条件而非时序窗，
  先验中性偏负）。
- 反悔方式：R6 一句话否决（撤 D1-011）；重开须新证据 + 新 prereg。

## 9. 工件键索引

- 判据机输出：`scripts/02_analysis/l1d_stacked_judge.py`（默认=主判；`--confirm`=§0.1）
- 训练：`results/lifecycle_paper2/l1d.done`（3/3 rc=0）、`l1d_confirm.done`（3/3 rc=0；
  尾行 sentinel 文本 "L1C_CONFIRM_ALL_DONE" 为脚本 sed 模板残留，工件名/时间戳均为
  l1d，如实登记）
- 渲染：`render_L1d_person_tracking_stacked_s{0..5}_canon/`（6/6 n_frames=17）
- 计数器：`L1d_person_tracking_stacked_s{0..5}/tables/efficiency_raw.csv` 末行
- consolelog：`results/lifecycle_paper2/L1d_person_tracking_stacked_s{0..5}.consolelog`
- config 副本：`L1d_*/config_snapshot.yaml`（= committed `l1d_person_tracking_stacked.yaml`）
- 关卡①：`/tmp/l1d_gate1/critic_report.md` + `/tmp/l1d_gate1/batch_facts.md`
