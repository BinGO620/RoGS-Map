# verdict_l1b_robust_range_2026-10-04.md — D2-025 乙线（新自有点：重尾感知范围量化）L1 判决

> **账本**：D2-025 乙线；判据出处 = `prereg_gs_compress.md` §10（v1.1 修正案，先锁）。
> **性质**：R1 机械判读（数字零手抄，全部来自 `evidence/rd/L1B_*.json` + `l1b_readout.json`）。
> **口径**：同码率对照 = 在每个 v2 点的码率上对 v1 折线线性内插取 PSNR（禁混引，prereg §4.0）。
> **上游**：G1 = Reject（3 致命，`/tmp/slam_critic_gscompress_g1_2026-10-04.md`）；
> **关卡② G2 = Accept-with-conditions**（`/tmp/slam_critic_gscompress_g2_2026-10-04.md`，7 重大已逐条处置，见 §8）。

## 0. 一句话

**乙线新自有点（重尾感知范围量化）判「边际，非帕累托」⇒ 按 prereg §10.3 不加 claim，回退甲**
（论文按"效率 codec + 存储代价刻画"定稿）。**但产出两条有价值的事实**（入边界/发现）：
① **SLAM 地图重尾是"承重"的**（clip 掉即崩 −0.68~−0.74 dB）；② **范围膨胀 (infl) 不是可压空间的可靠代理**。

## 1. 机制与判据（先锁回顾）

- **机制**：codec v1 每属性组用全局 min/max 范围量化（`gs_codec.py` encode）；SLAM 地图重尾撑大范围。
  v2 改稳健百分位范围 [p_q, p_{100−q}]，尾部走 escape（全范围同位宽另存）或 clip。
- **判据 R2（§10.2）**：同码率（±2%）下 ΔPSNR > 0 且 static Δ ≥ −0.3 dB ⇒ 帕累托。
- **出口（§10.3）**：边际/不稳 ⇒ claim 不加项（回退甲）；为负 ⇒ 击杀 + 记边界。

## 2. 读数（L1B，三图 × 三位宽点 × {v1, robust+escape, robust+clip}）

### 2.1 同码率 ΔPSNR（robust+escape vs v1@线性内插；v1 折线 3 点）

| 图 | 位宽点 | rate v1→v2 | Δrate% | ΔPSNR | Δstatic |
|---|---|---|---|---|---|
| balloon_baseline | 8/4/4/4/4 | 5.30→5.98 | +13.0 | **+0.151** | +0.914 |
| balloon_baseline | 10/6/6/6/6 | 9.20→9.90 | +7.6 | **+0.045** | +0.035 |
| balloon_baseline | 16/8/8/8/8 | 13.49→14.21 | +5.3 | unmatched（超 v1 折线右端 >2%） | — |
| crowd2_baseline | 8/4/4/4/4 | 4.99→5.73 | +14.8 | **+0.142** | +1.064 |
| crowd2_baseline | 10/6/6/6/6 | 8.77→9.55 | +8.9 | **−0.016** | +0.045 |
| crowd2_baseline | 16/8/8/8/8 | 13.18→14.03 | +6.5 | unmatched | — |
| person_tracking2_final | 8/4/4/4/4 | 5.49→6.28 | +14.5 | **+0.384** | +0.924 |
| person_tracking2_final | 10/6/6/6/6 | 9.32→10.10 | +8.4 | **+0.021** | +0.160 |
| person_tracking2_final | 16/8/8/8/8 | 13.50→14.31 | +6.0 | unmatched | — |

- **可测点仅 6 个（2 位宽点 × 3 图）**：16/8/8/8/8 三图**全 unmatched**（escape 结构性使 v2 码率高于 v1 近无损点 >2%，
  在最高效端**够不着**）⇒ **判据只在 2 个中低 bit 点可测**。
- 可测 6 点的 **ΔPSNR：中位 +0.0935，range [−0.016, +0.384]，all_positive = False**（crowd2@10/6 = −0.016）。
- **escape 码率代价 +5.3~+14.8%**（G2 重大-7 更正：**主因是稳健范围载荷的 zlib 压缩率下降**——
  clip 臂同样 +7~14%；escape 位图专属开销仅约 +1.1pp）。

### 2.2 robust+clip（无 escape）

| 图 | 位宽点 | Δrate%（vs v1 折线） | ΔPSNR | 读 |
|---|---|---|---|---|
| balloon | 8/4/4/4/4 | ~+11.9 | +0.122 | 略好 |
| balloon | 10/6/6/6/6 | ~+7.4 | −0.116 | 略差 |
| **crowd2** | 8/4/4/4/4 | ~+13.7 | **−0.676** | **崩** |
| **crowd2** | 10/6/6/6/6 | ~+8.3 | **−0.744** | **崩** |
| pt2 | 8/4/4/4/4 | ~+13.3 | −0.005 | 平 |
| pt2 | 10/6/6/6/6 | ~+7.8 | −0.308 | 差 |

**注（G2 重大-7）**：clip 臂码率同样高于 v1（+7~14%）⇒ §2.2 不宣称"同 v1 码率量级"；
clip 与 escape 的码率差（~1pp）才是 escape 专属代价。

## 3. 判据机械应用

- **R1 存在门 ✅**：全链跑通（重建 PLY 渲染无错；escape 位图随流自洽，`test_robust_escape_recovers_tail_exactly` 守护）。
- **R2 同码率帕累托 ❌**：见 §2.1——可测 6 点中位 +0.0935 dB、**all_positive=False**、码率代价 +5~15%。
- **R3 尾部无损性 ✅（合成地图）**：escape 后尾部误差回到 v1 量级（`test_robust_escape_recovers_tail_exactly`）。
  **诚实登记（G2 次要）**：R3 目前仅由合成重尾地图单测支撑，**未在真实地图上单独落盘读数** ⇒ 判"部分"。
- **R4 clip 变体（描述）**：稳健范围把尾部信息丢掉会崩（crowd2 −0.71 dB）⇒ **重尾承载渲染**。

### 3.1 R2 的口径诚实登记（G2 重大-1，G1 致命-2 未清）

prereg §10.2 的"超噪声带"定义（v1 重编码同一码流作控制）**因 codec 确定性而退化**（控制 ΔPSNR 恒 0，
见 G1 致命-2）⇒ 该判据**不能按原文机械判定**。本判决**未**用"超噪声带"，而改用**两条可查口径**：
(a) **跨图方向一致性**（all_positive）；(b) **ΔPSNR 量级 vs 同工作点跨序列散布**。
**这一替换是事后选择，属判据偏离，如实登记**（prereg 修订行见 §7）。三种读数（§10.2 原文、
§10.3 跨图一致、代码机械门 all_positive=False）**同向指向"边际非帕累托"**，故结论稳健。

## 4. 出口 = 「边际，非帕累托」⇒ 不加 claim，回退甲（prereg §10.3）

**乙线结论**：新自有点**不足以**升为正向机制贡献；按 §10.3 **不加 claim**，
论文回退**甲**（"动态场景 GS-SLAM 地图效率 codec + 存储代价刻画"）。

## 5. 边界发现（诚实登记，不作贡献主张；DISCIPLINE「负结果不作叙事主角」）

1. **SLAM 生长地图的重尾是"承重"的，不是可丢冗余**：稳健范围 clip 尾部 ⇒ crowd2 全图 PSNR −0.71 dB。
   **与记账字段（6 字段恒常数、可无损剥离）性质相反**——同为"范围外/异常"，一类可丢、一类承重。
   **更正（G2 重大-3）**：不能说"尾部基元近全不透明"——`tail_census_2026-10-04.md` 实测
   `opa(tail)` 在多数图 ≈0.99+（balloon/crowd2/balloon2）**但 pt2_final = 0.771 < opa(non)=0.7825**
   ⇒ 正确表述 = "**尾部基元尺度显著更大**（`s_max(tail)` 比非尾大 ≥2 log 单位），不透明度**多数**近饱和、**非全部**"。
2. **范围膨胀 (infl) 不是可压缩性的可靠代理**（**G1 致命-1 的结论，本判决以实测确认**）：
   scale 组 infl 1.36–2.15×（S0）但同码率 PSNR 增益 ≤0.4 dB 且非全正 ⇒ **范围比 ≠ 误差比**。
   证据：S0.5 量化误差探针（`qerr_probe_2026-10-04.md`）+ 本 L1B 渲染对照。

## 6. 撞车登记（回源核对结论；工件 = `resources/lit_dyn_mapping/gs_compression_range_prior_2026-10-04.md`）

- 百分位/稳健范围量化在 3DGS 压缩**已有先例**：**SOG**（3DGS.zip 综述记"clip various attribute ranges …
  based on percentile thresholds"）、**StitchGS**（"remove rare scale outliers using a percentile-based rule …
  Quantile(z, 0.999)"）⇒ **"范围轴未被试"的立项表述被推翻**（检索摘要级，**引用前须回源逐字核对**）。
  ⇒ 本自有点即使有效也**新颖度受限**；叠加 R2 边际 ⇒ 双杀。

## 7. 判据变更登记（G2 重大-6 / G1 致命-3）

- **追加 prereg 日期修订行**：本判决的 R2 代用口径（§3.1）、L1 图集确认（§10.4 的 pt2_final 属**已消费**held-out：
  `l1_readout_2026-10-04.md` §6.3 的 L2 42 图已含 pt2 ⇒ **非未污染 held-out**，如实登记），
  均随本件写入 prereg §10 附注。
- **账本**：本判决 = D1 类（R1 机械应用），登记入 `DECISIONS.md` D1 行（见 ledger 追加）。

## 8. G2 条件项处置（Accept-with-conditions → 逐条）

| # | G2 条件 | 处置 |
|---|---|---|
| 重大-1 R2 口径 | §3.1 如实登记判据偏离 + §7 修订行 |
| 重大-2 位宽点集合/unmatched | §2.1 显式列 6 可测点 + 16/8 全 unmatched |
| 重大-3 "尾部近全不透明" | §5.1 已更正（pt2_final 反例） |
| 重大-4 §5 边界#2 回收 G1 断言 | §5.2 改为"以实测确认 G1 致命-1"，并指 S0.5 证据 |
| 重大-5 §6 撞车无工件 | §6 落工件 `gs_compression_range_prior_2026-10-04.md` |
| 重大-6 图集改轴未登记 | §7 修订行 + DECISIONS 追加 |
| 重大-7 escape 码率归因错误 | §2.1/§2.2 已更正（主因=zlib 载荷压缩率；escape 专属 ~1pp） |
| 次要 static Δ 口径 | §2.1 用最近 v1 点（并注内插口径下 balloon@10/6 ≈ −0.03） |
| 次要 readout 未校验 range_mode | `l1b_readout.py` 已加 range_mode 字段读取（覆核） |
| 次要 "33 rc=0 无落盘证据" | 远程 `l1b_logs/_dispatch.log` 三行 `rc=0`；本地 33 判据键已入库 |
| 次要 R3 仅合成单测 | §3 已如实登记"部分" |

## 9. 工件
- 判读：`evidence/l1b_readout_2026-10-04.md` + `l1b_readout.json`（机写）
- 数据：`evidence/rd/L1B_*.json`（33 份，判据键，已入库）
- 普查/探针：`evidence/tail_census_2026-10-04.md`、`evidence/qerr_probe_2026-10-04.md`
- 撞车核查：`resources/lit_dyn_mapping/gs_compression_range_prior_2026-10-04.md`
- 代码：`scripts/gs_compress/{gs_codec,rd_harness,rd_sweep,l1b_batch,l1b_readout,tail_census,qerr_probe}.py`
- 关卡报告：G1 `/tmp/slam_critic_gscompress_g1_2026-10-04.md`；G2 `/tmp/slam_critic_gscompress_g2_2026-10-04.md`
