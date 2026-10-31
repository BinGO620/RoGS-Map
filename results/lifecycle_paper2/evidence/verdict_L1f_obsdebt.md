# verdict_L1f_obsdebt — L1f 观测债补偿（机制 A）判决

> **双溯源**：预注册 = `4d5dd720`（+ 修订 `77d48328`，判据先锁，先于任何实装/跑批）；
> **测量代码** = `00c4a38c`（obsdebt-boost 段局部 `enable_grad` 实装修复，先于 6-seed 确认批）
> + `40f3074e`（重跑驱动）；**分析代码** = `d5c8094e`（判据机 + 单测，先于本判决）。
> **仪器**：渲染后缀 `_canon`（掩码源 = `<seq>/dynamic_mask/`，canonical 0/255 布尔）；
> 读数参照 = instrument_v2 三参照（**m3 深度分层匹配为主读数**；全域静态/邻域环并陈）；
> 重评分清单 `instrument_v2/rescore_batch_manifest_L1f.json`（15 run，独立于冻结的 109-run 主清单）。
> **关卡①**：slam-critic **先于本文件落盘**（2026-09-25），结论 **Reject** —— 致命 2 / 重大 7 / 次要 6；
> 逐条处置见 §5。全量报告 `/tmp/slam_critic_l1f_2026-09-25.md`。
> **写作纪律自查**：本判决是**机制 L1 的负结论**（机制未成立），不进贡献栏、不起包装名、不作 headline
> （`DISCIPLINE.md:457-459`）；只以边界小节/讨论身份存在。

## 0. 一句话终局

**机制未成立（PASS 不成立）**。预注册 3-seed 主判 **FAIL**（m3 median-of-medians **+3.5703cm**，方向
**与假设相反**，仅 1/3 seed 为负）；预锁击杀分支补训 s3-5 后，6-seed 重判**机械 PASS**（mom −3.5172cm，
4/6 负，**恰在 2/3 地板**），但该 PASS **不可归因于机制**：把读数限制在**机制实际动作**的 seed
（s0-s3）后 mom = **+0.0644cm、2/4 负 ⇒ FAIL**，而全部负号恰恰集中在**机制零动作**的 s4/s5
（`boost=0` 且 `fill=0`）。这与"机制在本域**作用面过薄**"互为印证：② 预算重分配**结构性零触发**
（全 15 run 0 行），③ 迭代配额**全批仅 4 事件**（s4/s5 为零）。

## 1. 判据与机械读数（判据本体零改动）

判据权威 = `prereg_L1f_obsdebt.md` §2/§2b/§3/§4（先锁）。读法：Δ = **obsdebt − exit_fill**
（同管线单变量，prereg §2）；逐帧配对 → 逐 seed median → **跨 seed median-of-medians**；
PASS ⟺ mom **< −1.48cm** 且 **≥2/3 seed 为负**；主域 = balloon2（pt 只作约束门）。

| 读数层 | m3（主参照） | 全域静态 | 邻域环 | 判定 |
|---|---|---|---|---|
| **3-seed 主批（s0-2，预注册）** | **+3.5703** | +3.7166 | +3.4077 | **FAIL**（1/3 负，方向相反） |
| **6-seed 确认批（s0-5）** | **−3.5172** | −1.5947 | −1.4834 | **机械 PASS**（4/6 负） |
| **限机制动作 seed（s0-3）** | **+0.0644** | — | — | **FAIL**（2/4 负） |

逐 seed median（m3）= `[+3.5703, +12.0035, −3.4415, −6.7049, −3.5929, −5.8265]`。

**两半反号**：s0-2 mom **+3.57（FAIL）** vs s3-5 mom **−5.83（PASS）** —— 结论由"取哪 3 个 seed"决定。

## 2. 归因检验（关卡① **致命-1**，本判决的核心）

判据机新增 `mechanism_attribution`（**诊断，不作判据本体**）：把 seed 分为
**机制实际动作**（② `fill kept>0` 或 ③ `boost>0`；① 账本记账不改变优化，不算动作）
与**零动作**两集，在动作集上重施加 prereg §3 形状。

| seed | ② fill kept | ③ boost 事件 | median Δ(m3) | 机制动作 |
|---|---|---|---|---|
| s0 | 0 | 1 | +3.5703 | 是 |
| s1 | 0 | 1 | +12.0035 | 是 |
| s2 | 0 | 2 | −3.4415 | 是 |
| s3 | 0 | 1 | −6.7049 | 是 |
| **s4** | **0** | **0** | **−3.5929** | **否** |
| **s5** | **0** | **0** | **−5.8265** | **否** |

**结论**：两个**机制完全未动作**的 seed 贡献了最负的读数。这是"6-seed PASS 是噪声而非机制效应"
的直接证据 —— 机制不动的地方反而"最好"。故 **6-seed PASS 不成立**。

## 3. 脆弱性诊断（关卡① 重大）

- **留一（leave-one-out）**：`loo_pass_count = 2/6` —— 丢掉 s2-s5 **任一** 即翻回 FAIL；
  16-seed 地板本身是**恰 2/3**（4/6）。
- **跨 seed 散布 = 18.71cm = 门槛的 12.6×**（B0 §2 已预告 IQR 3–7cm ⇒ 单 seed 判别力弱；本批更甚）。
- **邻域环 6-seed mom = −1.4834cm，距门槛仅 0.0034cm**（发丝级余量）。

## 4. 约束门 / 护栏 / 点火（如实落表）

| 项 | 结果 | 说明 |
|---|---|---|
| ATE 非劣化（vs off，prereg §4） | **ok**（mean −1.72%，max +0.71%） | 仅 s0-2 可评（无 `L3_balloon2_off_s3-5`）；**补充同批读数** vs exit_fill：mean +0.37%、max +3.17%，ok |
| static PSNR 非劣化（vs ctrl） | **ok**（Δ +0.203dB ≥ −0.65） | canon 口径 |
| 误删护栏 coverage ≥ 0.99 | **ok**（15/15 有效） | 破 = run 无效；本批无破 |
| **基元膨胀 ≤ +80%**（prereg §4） | **FAIL**（worst **+210%**，s3 main 77600 vs ctrl 24997） | prereg 措辞为"**如实落表**"（非"破=run 无效"）⇒ 记为越界事实，不改主判；s3 亦为对照臂异常低值 seed |
| 机制点火（prereg §2b） | ① 账本 s0-5 各 77–84 行（单调）；**② 恒 0**；**③ 仅 4 事件** | 三项非全零 ⇒ 名义 run 有效；但**②结构性零作用面、③作用面过薄** |
| pt 约束域（prereg §3，只作约束门） | ATE ok=false（max +11.4% > +10%）；PSNR ok=false（−1.04dB） | pt 为诊断域**不判效**；且 pt 臂跑于 pre-fix 代码（18:06-18:28 < 21:19）且 ③ 零点火 ⇒ **门不可归因于 obsdebt** |

## 5. 关卡① 记录与整改（逐条）

| # | 级别 | 问题 | 处置 |
|---|---|---|---|
| 1 | **致命** | PASS 的两 seed（s4/s5）是机制零动作 run；剔除后 mom=+0.064 ⇒ FAIL | **采纳**：新增 `mechanism_attribution` 诊断（判据机程序化），§2 落表；**判 PASS 不成立** |
| 2 | **致命** | 3-seed 主判 FAIL 被 6-seed PASS 覆盖；prereg 只预锁确认批的 FAIL 结局 ⇒ 疑"事后扩样翻盘" | **采纳**：判"机械 PASS 不可归因"，**不采纳 6-seed PASS 作生效结论**；prereg 缺口登记 §7 呈报 D2 |
| 3 | 重大 | 6-seed PASS 时 ATE 约束仅 3/6 seed 可评 | **采纳**：§4 明标；补同批 vs-exit_fill 读数（6/6 可评） |
| 4 | 重大 | §5 汇总键掩盖 pt 门 FAIL | **采纳**：判据机汇总改 `prereg_mechanical_PASS` + `attributable_readings` 分列；pt 单列 |
| 5 | 重大 | pt 臂跑于 pre-fix 代码且 ③ 零点火 ⇒ 门不可归因 | **采纳**：§4 如实登记 |
| 6 | 重大 | 跨批对照无等价门 | **部分采纳**：`git diff f20d448b..HEAD -- utils/ gaussian_splatting/ slam.py` 证**仅** obsdebt-gated 改动（对对照臂惰性）；但**未做可复跑阳性对照**（局限见 §6-③），如实登记 |
| 7 | 重大 | 散布 18.71cm ≫ 门槛，未转"不可判" | **采纳**：§3 落表；**未擅自新增判据门**（prereg 未锁散布门，须修正案）⇒ 以"归因失败"作实质判据 |
| 8 | 重大 | 点火门近乎空判（② 死、① 独撑） | **采纳**：§4 落表；② 的处置属 D2-012（呈报中，R3 默认乙） |
| 9 | 重大 | 唯一 FAIL 的门（基元膨胀 s3 +210%）未落 manifest | **采纳**：manifest `constraint_gates.primitive_budget` 已落 |
| 10 | 重大 | "对照臂可比/单变量"无可复跑等价工件 | **部分采纳**：git diff 证据入判决；可复跑工件**未做**（见 §6-③） |
| 11-16 | 次要 | coverage 未接入 PASS / config 头注释陈旧 / manifest 缺 PSNR 与 3-seed 主判 / ring 发丝余量 / 本地缺 as-run config 与 done / confirm 驱动 DEVICE 未透传 | **采纳**：coverage 已接入 `judge_balloon2`（剔除无效 seed）；manifest 已补 PSNR/3-seed/prim；其余如实登记 §6；config 注释与 DEVICE 为既有形态，本判决不改代码（登记待整改） |

## 6. 覆盖与局限（如实登记，不掩盖）

① **判据缺口**：prereg §3 未预锁"3-seed FAIL 后 6-seed 变 PASS"的处置，也未锁"跨 seed 散布门"
   与"可归因性门"。本判决**不改判据本体**，以"归因诊断失败"作实质依据 ⇒ **必须经 D2 确认**（§7）。
② **跨批**：4 个子批（对照 s0-2 @09-24 17:13 / 主臂 s0-2 @09-24 21:31 / 主臂 s3-5 @09-25 10:02 /
   对照 s3-5 @09-25 10:53）跨 commit 与跨日；代码差异经 git diff 证为 obsdebt-gated 唯一改动，
   但**运行环境差异无登记可查**（无法验证项）。
③ **未做阳性对照工件**：无 `control_report` 类"同 run 两码复算 diff=0"的等价性工件
   （DISCIPLINE「测量口径」4 要求）；本判决只有 git diff 的静态证据。
④ **本地缺件**：本地无各 run 的 as-run `config.yml` 与 s0-2 的 rc/done 记录（疑部分同步）；
   判据机依赖的 `tables/*.csv`、`console.log`、rescore JSON 已拉回并在盘。
⑤ **pt 域**不可判效（prereg §3 + instrument_v2 §5"pt 不可判"）。

## 7. 处置与呈报

- **机制族处置**：prereg §3 击杀分支精神 + §2 归因失败 ⇒ **观测债族（A，含容量定向形态）关闭**，
  不再做参数变体；机制轨成果**不进 CVM 正文**（D2-011：机制轨 = 方法线方向，不进正文）。
  本判决**不重开任何已关闭族**（prereg §5）。
- **呈报 D2**（未答按 R3 保守默认）：本次暴露 **prereg §3 未覆盖"确认批反转"** 的缺口，
  以及 **R2 关闭 vs 保留待议** 的取舍；系统默认 = 按"未成立"关闭（最保守、可逆性最高：
  代码 default-off，无外部影响）。
- **D2-012 状态更新**：其"形态二选一（甲：债驱动致密化 / 乙：单分支立判）"的**乙**已执行完毕，
  结论 = 单分支机制在 balloon2 域**无作用面**（② 恒 0）+ ③ 效应不可归因 ⇒ 乙路径**已走到终点且未成立**。

## 8. 复算命令（任一可独立验证）

```bash
cd /data/monogs-ours
# 3-seed 主判（预注册）/ 6-seed 确认 + 归因/脆弱性诊断
/data/conda_envs/monogs-ours/bin/python scripts/02_analysis/l1f_obsdebt_judge.py
/data/conda_envs/monogs-ours/bin/python scripts/02_analysis/l1f_obsdebt_judge.py --confirm
# 判据形状自测 + 单测（21 例，含负对照与归因/留一）
/data/conda_envs/monogs-ours/bin/python scripts/02_analysis/l1f_obsdebt_judge.py --selftest
/data/conda_envs/monogs-ours/bin/python -m pytest tests/lifecycle_paper2/test_l1f_obsdebt_judge.py -q
# manifest 重生成（双溯源）
/data/conda_envs/monogs-ours/bin/python scripts/02_analysis/gen_manifest_L1f.py --date 2026-09-25 \
  --verdict "<一行>" --prereg-commit 4d5dd720 --measure-commit 00c4a38c --analysis-commit <HEAD> \
  --seeds 0,1,2,3,4,5
# 指令级复算（点火计数）
grep -c "obsdebt KF"   results/lifecycle_paper2/L1f2_balloon2_obsdebt/datasets_bonn/*/seed_*/*/console.log
grep -c "obsdebt-fill" results/lifecycle_paper2/L1f2_balloon2_obsdebt/datasets_bonn/*/seed_*/*/console.log
grep -oE "extra_steps=[1-9]" results/lifecycle_paper2/L1f2_balloon2_obsdebt/datasets_bonn/*/seed_*/*/console.log | wc -l
```

**三件套**：① 渲染指标 = `render_L1f*_canon/render_metrics.json` + `instrument_v2/rescore/rescore_L1f*_canon.json`；
② 跟踪指标 = `L1f*/tables/tracking_raw.csv`；③ 渲染图对比 = `figs/L1f_balloon2_GT_obsdebt_ctrl_s{0,1,2}.png`
（由 `l1f_figures.py` 程序化生成，图注数值自 rescore JSON 取）。
