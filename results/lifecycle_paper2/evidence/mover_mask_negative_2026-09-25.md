# 建图侧"掩码覆盖扩展"路线：**上限核算 = 否决**（2026-09-25；诊断级，不落机制判决）

> **性质**：用户 2026-09-25 定目标"要建图侧正向效果"后，选定的第一条路线（掩码覆盖面：
> person → 人+非人行体）的**先验核算**。结论 = **该检测器不可用作判效仪器**（非"机制失败"）。
> **本件不改任何历史判决**；`dynamic_mask/` 未被触碰，历史读数保持可复现。

## 0. 一句话

把评测掩码从"只覆盖人"扩到"人+非人行体"**确实放大了度量窗口并让效应现身**（balloon m3
−0.97→−1.72、mvnobox −0.24→−4.97），但同一张掩码**把构型对照区吃掉了**——积累腾空区在
box 族吞掉 **75–79%** 画面 ⇒ **4 序列里 3 序列不通过"对照区存活"门**（含 balloon/balloon2）。
故该掩码**不得用于判效**；唯一存活的 mvnobox 其逐 seed 散布达 **15cm**（s2 反号 +8.02）。

## 1. 动机与原判（先锁）

- 现有 canonical `dynamic_mask/` **只覆盖人**（MaskRCNN COCO person=1）。对 mvnobox/mvnobox2，
  箱体是画面最大移动体却**既不在掩码、也不在残影度量里** ⇒ "方法有没有清掉箱子残影"**不可测**。
- 关键结构事实：**L3 主臂 `mode: exit` 运行期不读掩码**（`select_reset_mask`/`select_carve_mask`
  由 `in_front ∧ α<τ` 驱动、类无关，`utils/alpha_lifecycle.py:340-366`）⇒ 换掩码对已有臂是
  **纯度量**改动：**零训练、零改方法**（这正是"便宜"的来源）。

## 2. 做了什么（全部可复跑）

1. `build_mover_mask.sh`：GT 位姿刚体一致性运动残差（`utils/gtmc_mask.robust_motion_seeds`
   →`build_dynamic_masks_robust`）→ `dynamic_mask_motion/`；再与 `dynamic_mask/` 求并集 →
   `dynamic_mask_mover/`（`compose_mover_mask.py`）。**独立目录，不覆盖 canonical。**
2. `audit_mover_mask.py` 四门→**五门**（见 §4 的门缺陷）。
3. `rerender_L3_mover.sh`：4 序列 × `{off,exit}` × 3 seed + `{mvnobox,balloon2} exit_fill` × 3
   = **30 臂零训练重渲**（rc0=30/30），帧集与 canonical 同字面列表。
4. `run_instrument_v2_batch_mover.sh`：30 臂 **instrument_v2 三参照**重评分（rc0=30/30）。
5. `compare_mask_coverage.py`（单参照）/ `compare_mask_coverage_3ref.py`（三参照）并陈两掩码。

## 3. 结果（并陈；跨掩码禁混引）

### 3.1 度量窗口确实变大（正面）

| 序列 | canonical `freshvac` 支撑 | mover 支撑 |
|---|---|---|
| balloon | 32,747 px | 87,782 px |
| balloon2 | 42,738 px | 91,952 px |
| mvnobox | **0 px**（该指标退化，仅 n=6 帧可用） | 64,775 px |
| mvnobox2 | **0 px**（同上） | 70,542 px |

> 附带发现（独立成立）：**`render_compare` 的 freshvac（30 帧窗口）在 box 族 canonical 下
> 支撑为 0** ⇒ 该序列上这一口径此前**结构性不可测**（不是"读数为 0"）。这不是本线的产物，
> 是对现有度量的一条限制说明（instrument_v2 的 exc_full/ring/m3 是另一套定义，不受此限）。

### 3.2 效应读数（三参照，Δ = exit − off，负 = 改善；mom = 逐 seed median 的 median）

| 序列 | canon m3 | mover m3 | m3 负 seed | mover 下判定 |
|---|---|---|---|---|
| balloon | −0.97 | **−1.72** | 3/3 | 同号（但见 §4） |
| balloon2 | −3.96 | −2.74 | 2/3 | 同号（弱化） |
| mvnobox | −0.24 | **−4.97** | 2/3 | 同号（s2 反号 +8.02） |
| mvnobox2 | −0.87 | −0.17 | 3/3 | **⚠稀薄（对照区缺）⇒ 不可判** |

### 3.3 **否决依据**：对照区塌陷

| 序列 | 积累腾空区占画面（canon→mover） | mover 下 static_bg | mover 下 ring |
|---|---|---|---|
| balloon | 44.6% → **64.5%** | **2,396** | **560** |
| balloon2 | 65.3% → 63.5% | **3,518** | 1,398 |
| mvnobox | 28.9% → **78.8%** | 10,578 | 3,027 |
| mvnobox2 | 15.4% → **75.0%** | **1,103** | **226** |

**根因（诊断）**：GT 位姿运动残差检的是"**正在动**"的像素，在**手持** Bonn 上把相机自运动/
模糊帧**大面积过判**（构建器 docstring 自述的保守过排除）；残影指标消费的是**历史积累并集**，
过判被逐步放大 ⇒ 腾空区吞掉画面 ⇒ 构型对照（全域静态/邻域环）塌到千像素级 ⇒ 不可判。
**这与 instrument_v2 在密人群域发现的"不存在对照区"是同一类失效**（`verdict_instrument_v2.md` §4.1）。

## 4. 门缺陷（自审门本身的第一条教训，已修）

**G1–G4 全部通过，但仪器不可用。** G4 只看**逐帧**面积中位（1.1–20.7%，全部达标），
而指标消费的是**积累区**——门与失效模式**测的不是同一个量**。
已补 **G5 对照区存活**（直接读仪器产出 `support_px_median`：`static_bg ≥ 5000` 且 `ring ≥ 1000`；
依据 = repo 自身把 ring 2,882 px 记为"薄环带"、static_bg 10,010 记为"稀薄"，故取再降一档的底线）。
补 G5 后：**balloon ✗ / balloon2 ✗ / mvnobox ✓ / mvnobox2 ✗** ⇒ 该掩码**仅 1/4 序列可用**。

## 5. 结论与边界

- **本路线按 R2 式关闭（检测器形态）**：GT 位姿运动残差**不能**用作"人+非人行体"判效掩码。
  这不是"机制无效"，而是**仪器未建成** —— 故不产生任何机制判决，也不关闭"非人行体覆盖"这个
  **科学问题**。
- **可用的非人行体检测器需要同时满足**（本轮实测给出的准入条件）：
  ① 对移动体召回高（本轮并集后 G1≡1.0 靠的是语义人掩码，运动侧自身对人仅 0.25）；
  ② **对相机自运动/模糊帧的假阳要低**（当前最大失效点）；
  ③ 面积必须按**积累**口径受控，而非逐帧（否则 G5 类失效）；
  ④ 不破坏构型对照（static_bg/ring 存活）。
- **不做**：不改 canonical 掩码、不用 `_mover` 读数推翻/支持任何历史 C1 结论（跨掩码禁混引）。

## 6. 复跑命令

```bash
# 掩码（远程）：运动残差 → 并集 → 五门审计
PY=<远程python> bash scripts/lifecycle_paper2/build_mover_mask.sh
PY=<远程python> python scripts/02_analysis/audit_mover_mask.py \
    --seq-dir datasets/bonn/rgbd_bonn_mvnobox --rescore-dir results/lifecycle_paper2/instrument_v2/rescore
# 零训练重渲 + 三参照重评分
PY=<远程python> bash scripts/lifecycle_paper2/rerender_L3_mover.sh cuda:0,cuda:1
PY=<远程python> bash scripts/lifecycle_paper2/run_instrument_v2_batch_mover.sh
# 并陈读数（本地）
python scripts/02_analysis/compare_mask_coverage.py
python scripts/02_analysis/compare_mask_coverage_3ref.py --out results/lifecycle_paper2/evidence/mask_coverage_compare_3ref_2026-09-25.md
```
