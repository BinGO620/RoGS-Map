# verdict_L1b_gate.md — 证据门控（治续命）L1b 判决书

> **⚠ 2026-09-24 口径标注（D1-014 M1 整改；不改动本判决原文与 PASS/FAIL）**：
> 本判决的主判据读数（mean Δ = −1.893cm，PASS）为**单参照（freshvac）+ 均值聚合**——
> 均值可被少数帧主导（`NOTES:516` 规则，当时未生效）。**后续重读**：
> ① per-frame median[IQR] 重读表（`judge_reread_median_2026-09-24.md`：s0 −4.14 [−5.74,−2.96] /
> s1 −1.03 [−1.29,+1.52] / s2 −3.19 [−4.24,+3.66]，n=9——s1 的 IQR 含 0）；② 仪器 v2 三参照
> （`verdict_instrument_v2.md` §3.3：三参照混号、s1 符号翻转 ⇒ **量级未达 v2 阈值**）。
> 引用本 PASS 时**必须带此标注**；两读法冲突时的权威 = `verdict_instrument_v2.md`。

**日期**：2026-09-21 ｜ **性质**：L1b 最小效果验证（R7 L1 级）＋ R2 单次定位改进快筛
**判据权威（不得在此重新定义）**：`prereg_L1b_gate.md` §4–§6 ＋ **修正案 1/2**（§9 判据标定修正 + 配置修正；**均先于重派**）
**批量**：4 run ＝ 1 off 一致性验证（gateoff s0）＋ 3 gate（person_tracking × seed 0/1/2）；**对照 = 已有 L3 exit 同 seed（零新增对照 run）**
**执行**：**4/4 rc=0**（`results/lifecycle_paper2/l1b.done`）；训练单卡 19:48→20:41（≈53 min，13 min/run）；渲染单卡串行 3/3 rc=0、`n_frames` 全 17（`results/lifecycle_paper2/l1b_render.done`，`L1B_RENDER_DONE bad=0`）
**as-run 配置 provenance**：运行时合并 config = 提交 `be504ab0` 版（修正案 2：`static_bg_mask_subdir: null`）；当前 HEAD 自 `021469e8`（掩码体系 v2 收口）起已改为 `"dynamic_mask"`——**不影响本批 as-run 事实**（本批 run/渲染完成于 2026-09-21 20:42，早于该提交），但复算本批 seg12dense 读数须以本判决 §1–§2 口径为准（见 §7 注）。**2026-09-24 补（D1-014 M8）**：本批 run 目录无 `config_snapshot.yaml`（当时产物形态），as-run config 以本段文字 + consolelog 为准。
**判据机**：`scripts/02_analysis/l1b_gate_judge.py`（程序产出，禁手抄；`--selftest` 含对调两臂负对照）
**仪器**：freshvac 一律 **seg_mask cls12**（修正仪器；`render_L1b_person_tracking_gate_s{0,1,2}_seg12dense`）

> **纪律偏差登记（带日期）**：本判决书先于关卡①落盘/提交（2026-09-21），违反
> `DISCIPLINE.md`「收口关卡必须早于落盘」的字面要求。**关卡①（补审，2026-09-22）=
> Accept-with-conditions**：无致命项，数字基础 100% 复算成立（主判据 9/9、ATE 10/10、
> 计数器 18/18、判据机逐字段一致、三重负对照过）；程序偏差裁决为**补救充分**
> （补审 + 本登记 + 条件整改），不触发重跑。条件 C1–C6 已于 2026-09-22 全部清零
> （done 证据拉回 / 复算命令后缀注明 / as-run config 指针 / 诊断-判决矛盾调和 /
> 12.79dB 无键数字处置 / 本登记）。全量报告：`/tmp/l1b_gate1_report.md`。

---

## 0. 一句话

**主判据 PASS**（3/3 seed 负、mean Δ = **−1.893 cm**、门槛 1.19 cm、ratio 1.59 ⇒ Tier 2）——
证据门控把 person_tracking 的人物轨迹区残影显著压下来了，**人群族出现首个可复制正效应**；
但**约束门双双越门**（ATE +1.36 cm / +11.4%；static PSNR −1.74 dB）⇒ 按预注册 §7
**"效果真实但带代价"**如实写，**不追加 run**。

## 1. 主判据（唯一判定；程序化）

| seed | gate freshvac | exit freshvac | Δ = gate − exit |
|---|---|---|---|
| 0 | 2.4514 | 3.5053 | **−1.0539** |
| 1 | 2.4273 | 4.2651 | **−1.8378** |
| 2 | 1.4280 | 4.2156 | **−2.7876** |

- **3/3 同号为负**、**mean Δ = −1.8931 cm**、off 臂 cls12 sd = 0.5839、**门槛 = max(1.19, 0.5839) = 1.19 cm**
- **PASS ⟺ (≥2/3 负) ∧ (|mean| > 1.19)** ⇒ **PASS = True**（`sign_ok=True, mag_ok=True, tier=2`）
- 判据机负对照（`--selftest`）：对调两臂 ⇒ PASS=False；一致更差 ⇒ False；幅度不足 ⇒ False（三重负对照全过）
- 三 seed Δ 与 off 臂分布对照：gate 2.45/2.43/1.43 **全部低于 off 臂最小值 3.96** ⇒ 不只是"比 exit 好"，是**低于无机制的 off 臂**——即 gate 让 exit 的残影降到了 off 以下（机制净收益方向明确）。

## 2. 约束门（逐 seed 配对 vs L3 exit）—— **两项均越门**

| 门 | 读数 | 判定 |
|---|---|---|
| ATE Δ | **+1.3572 cm**（+11.4%） | ❌ 越门（限 +0.5cm / +5%） |
| static PSNR Δ | **−1.7442 dB** | ❌ 越门（限 −0.25dB） |

**但必须并陈 ATE 的 seed 结构**（防读成"机制伤跟踪"）：

| seed | exit | gate | gateoff | off 臂 |
|---|---|---|---|---|
| 0 | 12.8458 | **21.0512** | 10.5715 | 11.5419 |
| 1 | 11.8729 | **9.9298** | — | 11.9218 |
| 2 | 10.9974 | **8.8067** | — | 10.3737 |

⇒ **2/3 seed 的 gate ATE 优于 exit（−1.94 / −2.19 cm）**，均值越门由 **s0 单点 21.05 cm** 独力推动。
s0 的 run 无异常特征（正常 `Done.`、基元 71801、耗时 518 s 与其余一致；渲染成功但质量
偏低——mean_psnr 17.09dB、最低帧 12.02dB，均见
`render_L1b_person_tracking_gate_s0_seg12dense/render_metrics.json`，非崩溃）⇒ 定性为**本管线
轨迹混沌的坏运气 seed**（同栈实测带 10.37–12.85，21.05 在带外）。
**如实登记**：约束门按预注册机械判定为**越门**（不改判据、不挑 seed）；上述 seed 结构作为
解释性并陈，供 D2 与后续 L2 判断。**本判据不因此翻案。**

## 3. 过程验证（不作判据）—— 机制点火确凿，但 **carve 仍几乎不触发**

| 计数器（efficiency_raw.csv，末行） | s0 | s1 | s2 |
|---|---|---|---|
| `alpha_gate_capped_total` | 18808 | 21951 | 20778 |
| `alpha_gate_prevented_rise_sum` | 468.42 | 559.74 | 512.24 |
| `alpha_gate_no_mask_kfs` | 0 | 0 | 0 |
| **`alpha_carve_total`** | **0** | **0** | **2** |
| `alpha_exit_reset_total` | 2330 | 7286 | 8061 |
| `alpha_lifecycle_steps` | 116 | 116 | 115 |

- **gate 全程可用**：`no_mask_kfs=0`（116 个 KF 掩码全在）⇒ 阶段 0 的召回 0.995 在运行期兑现。
- **gate 确实在动作**：每 run 约 1.9–2.2 万个基元的 α 抬升被压回（prevented 468–560）。
- **但 `alpha_carve_total` 仍 ≈ 0**（与 exit 臂同病）⇒ **主判据的改善不是通过 carve 实现的**。
  **已诊断定论**（`l1b_mechanism_diagnosis_2026-09-21.md`，逐 KF 工件级）：gate 把 α
  **钉死在 0.2199**（KF 300 起恒定），恰在 `tau_carve=0.20` **之上 0.02** ⇒ carve 合取门
  结构性不可达。原因是 `beta=0.9` 的 EMA 与"每帧都被观测为静态（ev≈0）"形成动态平衡：
  EMA 每次想抬升、gate 每次压回。**现有证据指向参数共振而非实装缺陷**（tau_carve 落在该
  不动点轨迹可达范围之上；但未经 β 敏感性实验的排他性证明，保留被推翻空间）；`verdict_L3`
  §9 的 exit 臂钉在 0.2445 与此同源。⇒ 改善来自**α 被持续压制
  本身**的间接效应（复位 `a_lt_reset` 1→361 明显抬升），**机制路径与设计预期不同**。
- 预注册 §6 的"诊断预测（掩码内 α 在人再占据时不回升）"**未被直接观测**（终态 PLY 不含
  static_prob；per-KF 日志只有聚合量）——登记为**未验证**，不声称成立。

## 4. 边界与限制（如实登记）

1. **单序列**：仅 person_tracking（L1 级最小验证）。**不得外推到 crowd/pt2/box 族**——L2 泛化未做。
2. **n=3 seed**；ATE 约束门由单 seed 主导（§2）；无同码重跑噪声带 ⇒ 主判据的
   "|mean| > 1.19" 用的是**跨 seed 散布**而非同码重跑散布（后者本管线不可得，见修正案 1）。
3. **static PSNR 越门 −1.74dB 无 seed 结构可归因**（三 seed 均低：19.67/18.77/18.10 vs exit
   20.14/20.92/20.70）⇒ 这一项是**一致的代价信号**，不像 ATE 那样能归因到单点。
4. **机制路径未按设计生效**（§3：carve≈0）⇒ 即便主判据 PASS，"证据门控通过解锁 carve 治续命"
   这个**因果叙事尚未被证实**；被证实的是"门控（某种路径）改善残影读数"。
5. 关卡② 未过 ⇒ **数字不得进论文/表**；本判决为**机制验证级**。

## 5. 对 D2 的含义（呈报；系统不自裁）

- **主判据 PASS 意味着**：人群族（person_tracking）在有效仪器下首次出现可复制正效应
  （3/3 负、低于 off 臂），且方向与机制假设一致（瞬态占据者的观测不作静态证据）。
- **但两条代价/疑点**须用户知悉：① 约束门两项越门（ATE 由单 seed 主导、PSNR 一致偏低）；
  ② **carve 未被解锁** ⇒ 机制路径与设计不同，主张只能是"门控改善残影"，不能是"解锁了 carve"。
- **选项**（一页纸另附，`d2_onepager_l1b_gate_2026-09-21.md` 的更新版）：
  A. **L2 泛化**（pt2 + crowd 族，+6 run）：验证可复制性与代价是否普遍——**默认建议**；
  B. 先做**机制路径诊断**（为何 carve 仍 0：α 分布/per-KF 追踪；零 GPU 先做 consolelog 分析）；
  C. 止损：以"门控改善残影但带 ATE/PSNR 代价、机制路径未证实"如实收口。
- **R2 状态**：证据门控族的**单次定位改进机会已用**（本批）。若 L2 不过 ⇒ 本族关门。

## 6. 三件套交付（R7 契约）

| # | 交付物 | 工件 |
|---|---|---|
| 1 | 渲染指标 | `render_L1b_person_tracking_gate_s{0,1,2}_seg12dense/render_metrics.json`（freshvac/static PSNR/PSNR/SSIM，cls12 仪器） |
| 2 | 跟踪指标 | `L1b_person_tracking_gate_s{0,1,2}/tables/tracking_raw.csv`（ATE/RPE）+ `L1b_person_tracking_gateoff/` |
| 3 | 渲染图 vs 原图 | 待生成（`render_compare.py --jpg` 已产出 cmp/depth PNG，随渲染目录）；**入仓前须用 `l3_figures.py` 同款纪律（图注取自工件 JSON + 帧号断言）** |

## 7. 复算命令

> 注（2026-09-22，关卡① 条件 C2）：本判决 §1–§2 的 freshvac/PSNR 数字为 **seg12dense
> 口径**。判据机默认 `--render-suffix` 已随掩码体系 v2 漂移为 `_canon`（重算得 −1.437，
> 见 `l3_instrument_rescore_2026-09-21.md` 附录 B.2）⇒ 复算本批原始数字必须显式加后缀。

```bash
PY=/data/conda_envs/monogs-ours/bin/python
$PY scripts/02_analysis/l1b_gate_judge.py --render-suffix _seg12dense   # 主判据 + 约束门 + 计数器（= §1–§2 口径）
$PY scripts/02_analysis/l1b_gate_judge.py --render-suffix _seg12dense --selftest          # 判据机负对照
$PY scripts/02_analysis/l1b_gate_judge.py --check-off-consistency   # §9 三门（行为面/轨迹面/代码面）
```
