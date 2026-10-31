# prereg_L2_gate.md — L2 gate 泛化批预注册（判据先锁；先于任何 L2 run 提交）

**日期**：2026-09-22 ｜ **级别**：R7 L2 场景类型泛化 ｜ **立项依据**：**D2-005 用户拍板 A**（2026-09-22，`d2_onepager_v2_2026-09-22.md`）
**上游**：L1b 判决 `verdict_L1b_gate.md`（主判据双口径 PASS、约束门双越、carve≈0、α 钉死 0.2199）；掩码体系 v2.1（canonical 仪器，`mask_system_refactor_v2_2026-09-21.md`）

## 1. 批构成与代码面

- **3 run** = `L2_{person_tracking2,crowd,crowd2}_gate_s0`（R7 L2 原文规格：+3 个序列 × 1 seed）。
- **零核心代码改动**：机制代码（`utils/alpha_lifecycle.py`、`gaussian_splatting/`、`slam.py`）经
  `git diff --quiet be504ab0..HEAD` 验证**逐字未动**（= L1b as-run 同代码）。本批只新增
  config / 派发脚本 / 判据机（分析侧）。
- **对照零新增**：gate 配对对照 = 已有 L3 exit 同 seed canonical 渲染
  （`render_L3_<seq>_exit_s0_canon`，已就位并核实）；off 臂 3 seed canonical
  （`render_L3_<seq>_off_s{0,1,2}_canon`）用于逐序列噪声带。
- 机制点火已被 L1b 判决（§3 过程验证）确立 ⇒ **本批不设 gateoff 一致性 run**。

## 2. 仪器（锁定）

- freshvac / static PSNR 一律 **canonical** 口径：渲染目录 `render_*_canon`
  （评估掩码 = `<seq>/dynamic_mask/`，0/255 布尔，9 序列全过三门验证，召回 0.981–0.992）。
- ATE ← `tables/tracking_raw.csv:ate_rmse_cm`；机制计数器 ← `tables/efficiency_raw.csv:alpha_*`。

## 3. 主判据（锁定；程序化于 `scripts/02_analysis/l2_gate_judge.py`）

- 逐序列：**见效 ⟺ Δ(s0) = gate − exit < 0 ∧ |Δ(s0)| > 门槛_seq**，
  其中 **门槛_seq = max(1.19, off_sd_seq)**，off_sd_seq = 该序列 off 臂 3 seed canonical
  freshvac 的样本 sd（n−1；不足 2 个读数时取 0）。**"为负"是判据的显式分支**
  （NOTES 2026-09-20 坑：只查同号会让"机制一致更差"也过）。
- 批判定：**≥2/3 序列见效 ⟺ 效应泛化成立**（R7：≥2/3 类型见效才升 L3）。
- **击杀确认分支（预锁）**：若 1/3 见效（边际）⇒ 允许补 s1 三序列 3 run（判据不变；
  逐序列重判 = **Δ(s0)、Δ(s1) 同号为负 ∧ |mean(Δ s0,s1)| > 门槛_seq**）⇒ 仍 <2/3 ⇒
  gate 方向在人群族击杀。0/3 或重判后仍 <2/3 ⇒ **不追加更多 run**（R7：击杀只补
  1–2 seed 确认，不做全表陪葬）。

## 4. 约束门（同 L1b 限值；逐序列报告，不改晋级判定）

- ATE Δ(gate−exit, s0 配对) ≤ **+0.5 cm 且 ≤ +5%**；static PSNR Δ ≥ **−0.25 dB**
  （基值量纲护栏 [8,60] dB）。
- **晋级唯由 §3 主判据决定**（L1b 先例："效果真实但带代价"）；代价模式（如 L1b 的
  PSNR 三 seed 一致偏低是否跨序列复现）逐序列如实登记，呈报 D2 定价。

## 5. 过程验证（不作判据）

- 每 run：`alpha_gate_capped_total > 0`（gate 在动作）、`alpha_gate_no_mask_kfs = 0`
  （运行期掩码可用；canonical 掩码在 crowd 系的覆盖已由 builder 验证，运行期为同一
  MaskRCNN 族）；`n_frames = 17`；rc=0（`l2.done` 工件计数为准，非日志 sentinel）。
- **注册预期**：`alpha_carve_total ≈ 0`（α 钉死 0.2199 > tau_carve 0.20 的参数共振，
  L1b 诊断定论）——若某序列 carve 显著 > 0，如实登记为**偏离预期**（可能是该序列
  α 分布不同），不作判据、不 retro 改判。

## 6. 已知背景登记（防过度解读）

- pt 的 s0 曾是"轨迹混沌坏运气 seed"（ATE 21.05 带外，L1b §2）⇒ 本批 s0 若出现单点
  ATE 爆炸，按同款结构并陈（均值 + 单点），不归因机制、不改判据。
- 人群族三种口径一致无 exit 效应（`l3_instrument_rescore` 附录 B.1）⇒ 本批的效应
  （若成立）归属于 **gate 增量**，不是 exit 的复活。
- 本批数字**关卡② 未过前不得进论文**。

## 7. 失败分支与下一步（预锁）

| 批判定 | 动作 |
|---|---|
| ≥2/3 见效 | 效应泛化成立；代价并陈 → **呈报 D2** 决定 L3 正式批与否 |
| 1/3 见效 | 击杀确认分支（§3）：补 s1 ×3 run → 重判 |
| 重判后 ≥2/3 | 同泛化成立支 |
| 重判后仍 <2/3（或初次 0/3） | gate 方向在人群族**击杀** → 呈报 D2（默认选项：机制参数路线（诊断 §4 B1）或 B3 如实收口） |

**不追加任何判据外 run**；修正案纪律同 L1b 修正案 1 先例（判据定标错误 vs 数据污染的
三分法；任何修正案须先提交后重派，且只可能是"判据标定"类，不得改主判据方向分支）。

## 8. 配置 / 派发 / 复算（工件键）

- config：`configs/experiments/lifecycle_paper2/l2_{person_tracking2,crowd,crowd2}_gate.yaml`
- 训练派发（远程）：`bash scripts/lifecycle_paper2/run_L2_remote.sh <gpu>`（`l2.done`）
- 渲染：`bash scripts/lifecycle_paper2/rerender_all_canon.sh cuda:0`（含本批 3 tag；
  `canon_render.done`）
- 判据机：`python scripts/02_analysis/l2_gate_judge.py`（`--selftest` 含对调两臂 /
  方向 / 幅度负对照）
