# prereg_L1d_stacked — gate×occupancy 叠加棘轮（L1d，D2-007）

> **性质**：D2-007 立项的预注册。判据先锁、先于任何 run 提交。
> 用户 2026-09-23 拍板批准执行（账本 D2-007）。一页纸 = `d2_onepager_stacked_2026-09-23.md`
> （§1 不动点推导**不在此重推导**；本 prereg 只锁判据与流程）。
> **零新代码**：`evidence_gate`（L1b 实装+关卡①过）与 `occupancy_memory`（L1c 实装+关卡①过）
> 均 default-off，本批 = 纯 config 组合。写于 2026-09-23，基线 commit = `7094abd4`。

## 1. 假设（一句话）

L1c 不动点分析（一页纸 §1）：occ 单开钉 0.47（EMA 抬升与 decay 互相抵消）、gate 单开钉
0.22（无下降项）、**叠加 = 单调棘轮** α←0.9α ⇒ 占据期 α 从 0.22 下行穿 tau_carve=0.20
（4 KF）→ 人走后 `in_front` 打开 → carve 首次点火 → 残影删除 → fill 补背景。
**前置条件验证**：棘轮组合顺序已于派发前以单元测试验证（`test_l1d_stacked_config.py`
组合用例：warm∩gate_hit 基元 α 按 0.9ⁿ 单调下行、非收敛 0.47）；测试失败 ⇒ 停派发、
回一页纸修订（零新代码约束下不改代码重排）。

## 2. 臂与成本

- **臂**：`L1d_person_tracking_stacked`（exit + `evidence_gate: true` + `occupancy_memory: true`）
  × seed 0/1/2 = **3 run**（R7 L1 级），远程 3090 双卡，≈40min。
- **对照**：零新增——L3 exit s0-2 canonical 已入库。
- **免 occoff**：零新代码 ⇒ 行为面以计数器核对替代（§5）。

## 3. 主判据（先锁）

Δ = stacked − exit（freshvac，canonical 口径，与 L1b/L1c 同源）。

**PASS ⟺ ∀3 seeds Δ<0 ∧ |mean Δ| > max(1.19, off_sd)**

（1.19 = balloon2 off 跨 seed sd，L1b/L1c 同款门槛；off_sd = 本批对照侧可得的散度估计，
取两者较大防"门槛被噪声吃掉"。）

## 4. 约束门（自含语义，照 L1b 先例）

- 限值：ATE ≤ +0.5cm 且 ≤ +5%；static PSNR ≥ −0.25dB。逐 seed 报告。
- **判决语义**：约束门越门**不自动 FAIL 主判据**——逐 seed 如实报代价并计入 verdict；
  代价 profile 喂 L2 headroom 设计（L1b 先例：主判据 PASS + 双越门如实并陈）。
- **代价风险预锁**：gate 单开时 static PSNR −1.74dB（三 seed 一致），叠加可能更狠——
  如实写，不追加 run、不因代价改判据。

## 5. 诊断预测（预锁，不作判据；每键带数据源工件）

| # | 预测 | 数据源工件键 |
|---|---|---|
| D① | a_min 在连续占据段**单调下行穿 0.20**（棘轮直接指纹） | consolelog 的 gate 分支行逐 KF `a_min=` 字段（`slam_backend.py` alpha-gate 打印） |
| D② | `alpha_carve_total` 首次 >0（pt 族从未发生过） | run 目录 counters JSON |
| D③ | 棘轮不触 α≥guard 净静态结构（安全性同 L1c） | `occ_alpha_lt_guard_total` + carve 计数器审计 |
| D④ | 人走后 α 回升速率（EMA 0.81α+0.09 竞速窗口长度，以 KF 计） | consolelog 逐 KF a_min 序列回升段斜率 |

**两种失败形态预锁判读**（都走击杀分支，但边界小节写法不同）：
- 计数器全零（capped=0 ∧ decayed=0）⇒ **组合未生效**（实装级）——与"配置生效"事故族
  同型，层 3/4 验证应已拦住；若仍出现 = 验证层失效，如实登记。
- a_min 棘轮下行成立但 `alpha_carve_total=0` ⇒ **窗口竞速失败**（机制时序级）：
  人走后 EMA 回升跑赢 carve 持续性条件。此形态直接决定 occ v2
  （per-primitive identity）是否值得立为下一个 D2 提案——**该信息必须保留进 verdict**。

## 6. 击杀确认分支（预锁）

非 3/3 负 ⇒ 补 **stacked s{3,4,5}（仅 3 run + 3 渲染；exit s3-5 对照已在 L1c 确认批
入库，不再重跑）**，6-seed 配对重判。重判仍不过 ⇒ **gate×occupancy 链式假说关闭**：
- 负结果进 §6 边界小节（`DISCIPLINE.md:363`：不进贡献栏/不命名/不作 headline）；
- **关闭范围预锁**：不再做任何 gate×occupancy 纯 config 组合变体（含调 tau/β/warm 的
  组合）——防漂移成参数扫描（一页纸 §3"不做"条款落成硬规则）；重开须全新机制族 + 新 prereg。

## 7. 配置生效验证（四层，派发前全过；用户指认事故模式对症锁）

1. **层 1 静态 diff**：vs `l1b_person_tracking_gate.yaml` 仅差 save_dir + occupancy 块；
   vs `l1c_person_tracking_occ.yaml` 仅差 `evidence_gate: false→true`。
2. **层 2 两态实例化**（pytest）：yaml → AlphaLifecycle params → 断言
   `does_evidence_gate() ∧ does_occupancy_memory()` 双 True + occupancy 四参数逐键=L1c；
   已知陷阱：两 flag 均被 `mode=="exit"` 门控（`alpha_lifecycle.py:115-126`）。
3. **层 3 组合单元测试**：§1 所述棘轮序列断言（合成 KF 链）。
4. **层 4 提交纪律**（NOTES 踩坑"跑批代码未提交"四条）：prereg+config+判据机+测试
   一次提交记 sha；`git status --porcelain scripts/ configs/` 为空才派发。

**行为面计数器契约**（arm-activity ledger，`slam_backend.py` 预置）：落地后核对
`alpha_gate_capped_total>0 ∧ occ_decay_events_total>0 ∧ occ_warm_prims_total>0`；
`*_no_mask_kfs` 留痕归因。任一臂标签计数器=0 ⇒ 该臂未跑其处理 ⇒ run 无效，不进判决。

## 8. 流程铁律（沿用）

关卡① slam-critic **先于** verdict 落盘（L1b 顺序偏差已修正的纪律）；判决数字必须指到
工件键（判据机程序化输出）；verdict 头部双溯源（测量代码 sha + 分析代码 sha，均先于批次）；
交付三件套 = 渲染指标表 + 跟踪指标表 + 渲染图 vs 原图对比（重点帧放大框）；
PASS ⇒ headroom 定向 L2 另立 prereg（预锁"序列 headroom"入选条件，一页纸 §4）。

## 9. 反悔方式

GPU 时间沉没 ~40min（确认分支再 +3 run）；run 数据可弃；两个母族状态不变（本就已关闭）；
撤销 = 停批零边际成本。用户可 R6 一句话否决。
