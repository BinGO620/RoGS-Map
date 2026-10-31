# lifecycle_paper2 — 静态侧退场清理（exit/carve）的 L1 阶梯验证

**状态**：⚠️ L1 **收口重开**——关卡① 的最新结论 = **Accept-with-conditions（条件已清）**；
**轮次与结论的单一事实源 = `DECISIONS.md` D1-003**（本文件不复述轮次数字）；**D2-003 = C→A（已拍板）**，C 步执行中；L2/L3 **未派发**
**分支**：`transient_map`（研发窗口期本地/origin/3090 三方同分支）
**性质**：论文 2 的**正面机制**候选（`DECISIONS.md` D2-002 将"静态侧生命周期"定为主线方向）；
本目录是它的最小效果验证（R7 阶梯 L1），**非论文数字**。

## 机制（一句话）

动态物体离开后，用 **SLAM 自身的几何证据**（深度不一致 + α 账本 EMA）逐基元判定"腾空区残影"，
先**可逆复位**（reset，A 相）再**硬剪除**（carve，B 相，需持续 ≥3 KF + 位于观测面前 δ），
可选背景补洞（fill，C 相；L1 未启用）。**无检测器、无掩码、无资产库**；`AlphaLifecycle.enabled=false`
时与主线**逐位一致**。

- 实装：`utils/alpha_lifecycle.py`（参数 + 选择器）、`utils/slam_backend.py:851-1184`（每 KF 钩子）、
  计数器导出到 `backend_timing.json`（`alpha_exit_reset_total` / `alpha_carve_total` 等）
- 配置：`configs/experiments/lifecycle_paper2/{mvnobox,balloon2,crowd2}_{off,exit}.yaml`（仅 `enabled`+`mode` 两键，阈值全走默认）

## L1 结论（15 run，2026-09-20）

| 族（场景） | 新鲜腾空区 Δ（§6，**事后口径**） | 污染代理 Δ（§1，**原判据**） | 离线独立仪器 | 判定 |
|---|---|---|---|---|
| mvnobox（显式移除，3 seed） | 3/3 负，**−1.83cm** | 3/3 负，−2.10cm | −1.68cm（同向） | ✅ 成立（两口径 + 两仪器同向） |
| balloon2（气球/悬浮物，3 seed × 2 批） | 3/3 负（今天 −2.50；9-06 −1.73） | **2/3 负，−0.77cm（未过）** | **+0.84cm（反向）** | ⚠️ **口径/仪器冲突 ⇒ 须并陈**（不可单报） |
| crowd2（拥挤行人） | 无读数（运行期列缺失） | —（运行期 static 列整段缺失，无本列读数） | **Δ−1.33cm**（4 帧；同码噪声 **2.33cm**） | ⚠️ **不可判**（效应 < 噪声）；基元 **+21.6%** 如实报告（`verdict_L1.md` §8） |

**约束（引用时同写）**：机制**非零代价**——mvnobox seed0 ATE **+0.45cm（+18%）**，其余 seed 小幅变好；
static PSNR **mvnobox seed1 = −0.27dB（越 −0.25 预注册门）**、其余在 ±0.4dB 内（`verdict_L1.md` §8 C4）。

**仪表**：主指标 = `static_freshvac_ghost_excess_*`（跨批漂 3-seed 0.063/2.201/0.820cm）；
代理 `static_ghost_excess`（腾空区−背景）跨批漂 5.11/1.05/1.12cm ⇒ **均值比 ≈2.4×**（**非 §6 旧文的"80×"**，已撤回）。
两口径的原判据/事后口径差异**必须并陈**（代理口径下 balloon2 未过）；**跨批绝对比较一律禁止，只做批内配对**（`verdict_L1.md` §2/§6/§8）。

## 产物

```
evidence/prereg_L1.md                        # 判据（跑前锁定；含补遗 1/2/3）
evidence/verdict_L1.md                       # 单一事实源：判决 + §6 仪表更正 + §7 crowd 收口
evidence/crowd_degradation_improvement_2026-09-20.md   # 拥挤族可判性/改进评估（候选 0/1/2，分级启动）
evidence/crowd_judgeability_2026-09-20.md              # 候选 0 第①步实测：密帧口径 → crowd2 由不可判变可判（零训练）
evidence/prereg_crowd_judgeability.md                  # C 步预注册（判据先锁）+ 修正案 1（仪器健壮性，判据不变）
evidence/crowd_judgeability_confirm.md                 # ★ C 步裁决：3 对同码复制 ⇒ crowd 族可判且方向为负（诊断级）
evidence/prereg_L3.md                              # ★ A 档 L3 正式批预注册（**待用户过目**：规模/fill 臂/主仪器三点）
figs/L1_{mvnobox,balloon2,crowd2}_GT_off_exit.png      # 三件套之"渲染图 vs 原图"
L1_{mvnobox,balloon2,crowd2}_{off,exit}*/tables/*.csv  # 15 run 的表（跟踪 + 渲染 + 效率）
render_{...}/                                # 离线渲染对照（含 --max-scale-m 护栏、--skip-unrenderable）
```

## 下一步（D2-003 = **C→A**，执行中）

1. **scope 定调**：A 限定域机制（+ 措辞收窄：在线 / 无检测-掩码-资产库 / 基元级 / ATE+分区，
   并正面引用区分 CubifyGS——见 `resources/lit_dyn_mapping/occupancy_recheck_2026-09-20.md`）
   ／ B 纯协议+边界 ／ C **先补可判性**（候选 0：crowd 族 freshvac 口径 + 扩帧集/配对，2 run 近乎零训练；
   见 `crowd_degradation_improvement_*.md` §4，条件成立后有界改进 ≤6 run、上限 8 run）；
2. scope 定后写 L2/L3 预注册（序列集 = Bonn 7 + box 族；臂 off/exit[/exit+fill]；3 seed；三件套）；
3. **关卡① 轮次/结论见 `DECISIONS.md` D1-003**（单一事实源；当前 = 第 7 轮 Accept-with-conditions）；
   **关卡②** 未送（数字入表前）——整改全文在 `verdict_L1.md` §8。
