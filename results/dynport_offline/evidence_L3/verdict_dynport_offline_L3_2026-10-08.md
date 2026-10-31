# 判决：DynPort-Offline L3 正式批（全 7 序列 × 3 seed；§12 v4 samepose 口径）— 2026-10-08

> **账本**：D1-036。**判据出处** = `prereg_dynport_offline_L1.md` §12 v4（口径）+ §6（L3 = 全 7 序列 × 3 seed，先锁）。**数字零手抄**：本文件由 `scripts/dynport_offline/write_verdict_L3.py` 从 manifest 机写。**锁定 HEAD** `3302209329b533f46c5d32840114037afca64b72`。**复用纪律**：L1_v4/L2 已在盘的 12 R1 + 6 C− **不重跑**（同批代码逐位一致），本批补 9 新 R1 + balloon C− + crowd2 OFF；判据机在 collect 时统一重跑（读存量 PLY）。

## 0. 一句话

**L3 正式规模泛化成立**：全 7 序列 × 3 seed = **21** 格（实得 21 格），**J3∧J1∧J2 全过 21/21**（出口 §6 = ≥2/3 ⇒ **达标**）。J1 区间 = 5.4915–8.9467 dB；J2 区间 = 0.2268–0.6104；J3 区间 = -0.0353–0.1958 dB。

## 1. 网格读数（机写 manifest；出口口径 = samepose）

| 序列 | seed0 | seed1 | seed2 |
|---|---|---|---|
| balloon | ✅ J1 8.95 / J2 0.230 / J3 0.097 | ✅ J1 7.89 / J2 0.270 / J3 0.196 | ✅ J1 8.64 / J2 0.233 / J3 0.123 |
| balloon2 | ✅ J1 6.08 / J2 0.227 / J3 0.071 | ✅ J1 6.40 / J2 0.282 / J3 0.045 | ✅ J1 5.76 / J2 0.339 / J3 0.035 |
| crowd | ✅ J1 5.76 / J2 0.581 / J3 0.031 | ✅ J1 5.85 / J2 0.579 / J3 0.003 | ✅ J1 5.49 / J2 0.610 / J3 0.035 |
| crowd2 | ✅ J1 7.95 / J2 0.473 / J3 -0.035 | ✅ J1 7.47 / J2 0.520 / J3 -0.014 | ✅ J1 7.73 / J2 0.450 / J3 -0.007 |
| crowd3 | ✅ J1 7.89 / J2 0.444 / J3 0.027 | ✅ J1 7.52 / J2 0.464 / J3 0.043 | ✅ J1 7.56 / J2 0.505 / J3 0.030 |
| person_tracking | ✅ J1 7.38 / J2 0.427 / J3 0.000 | ✅ J1 7.24 / J2 0.406 / J3 0.000 | ✅ J1 7.67 / J2 0.412 / J3 0.000 |
| person_tracking2 | ✅ J1 6.42 / J2 0.550 / J3 0.000 | ✅ J1 6.82 / J2 0.478 / J3 0.000 | ✅ J1 7.18 / J2 0.461 / J3 0.000 |

**泛化判据（§6）**：21/21 过 ⇒ **≥2/3 达标**。

**关卡② G2（Accept-with-conditions，2 重大已销）**：
- **J3 `Δfull ≥ −0.25` 子句回接出口**（原只产键 `J3_full_delta`、`j3_ok` 不消费）⇒ 现出口 = static ∈ ±0.25 **∧** Δfull ≥ −0.25；实测 Δfull 区间 = 0.0109–4.8073 dB（全 ≥ −0.25 ⇒ 子句不改变判词）。
- **J5「启用/停用两态 PSNR max|Δ| > 0.01 dB」核验回接**（原用逐位 off≡底图替代，非 PSNR 两态）⇒ 新键 `J5_two_state_full_psnr_maxabs`；实测区间 = 5.92–10.52 dB（≫0.01 ⇒ 机制真起作用）。
- 两子句均**由数据满足** ⇒ **21/21 与 PASS 不变**；改动 = 「已声明子句真接进出口」+ 键门登记，机制/阈值/口径零改。测试 `tests/dynport_offline/test_repair_map.py::test_exit_logic_behaves_on_synthetic_inputs`。

## 2. 逐格明细（J5/J7/J9 与 J4 报数）

| 格 | J1（≥2.5） | J2（≤0.70） | J3（\|Δ\|≤0.25） | J3 Δfull（≥−0.25） | J5（峰值 + 两态） | J7 | J9 | J4 | 判 |
|---|---|---|---|---|---|---|---|---|---|
| balloon | 8.9467 | 0.2304 | 0.0965 | 3.4964 | True (peak 6176, 2st 8.25) | 1.7862 | pass | 0.156× | ✅ |
| balloon_seed1 | 7.8926 | 0.2697 | 0.1958 | 3.1720 | True (peak 6166, 2st 7.81) | — | pass | 0.155× | ✅ |
| balloon_seed2 | 8.6442 | 0.2334 | 0.1234 | 3.4815 | True (peak 6192, 2st 8.02) | — | pass | 0.158× | ✅ |
| balloon2 | 6.0822 | 0.2268 | 0.0711 | 2.5117 | True (peak 6359, 2st 5.92) | 2.3130 | pass | 0.296× | ✅ |
| balloon2_seed1 | 6.3986 | 0.2821 | 0.0449 | 2.8169 | True (peak 6155, 2st 6.51) | — | pass | 0.275× | ✅ |
| balloon2_seed2 | 5.7633 | 0.3385 | 0.0347 | 2.6299 | True (peak 6269, 2st 6.17) | — | pass | 0.287× | ✅ |
| crowd | 5.7637 | 0.5812 | 0.0308 | 4.4068 | True (peak 12654, 2st 9.15) | 1.3343 | pass | 0.288× | ✅ |
| crowd_seed1 | 5.8511 | 0.5793 | 0.0034 | 3.9545 | True (peak 10084, 2st 8.80) | — | pass | 0.190× | ✅ |
| crowd_seed2 | 5.4915 | 0.6104 | 0.0354 | 4.2628 | True (peak 7955, 2st 9.27) | — | pass | 0.190× | ✅ |
| crowd2 | 7.9545 | 0.4731 | -0.0353 | 4.3967 | True (peak 10085, 2st 10.52) | 1.7940 | pass | 0.253× | ✅ |
| crowd2_seed1 | 7.4714 | 0.5199 | -0.0137 | 4.3058 | True (peak 8144, 2st 9.49) | — | pass | 0.247× | ✅ |
| crowd2_seed2 | 7.7331 | 0.4502 | -0.0071 | 4.4959 | True (peak 9899, 2st 9.97) | — | pass | 0.286× | ✅ |
| crowd3 | 7.8946 | 0.4440 | 0.0267 | 4.8073 | True (peak 13227, 2st 8.59) | 1.5854 | pass | 0.255× | ✅ |
| crowd3_seed1 | 7.5236 | 0.4636 | 0.0434 | 4.6337 | True (peak 10717, 2st 8.26) | — | pass | 0.260× | ✅ |
| crowd3_seed2 | 7.5625 | 0.5050 | 0.0305 | 4.6002 | True (peak 9059, 2st 8.72) | — | pass | 0.255× | ✅ |
| person_tracking | 7.3834 | 0.4267 | 0.0000 | 0.0109 | True (peak 5070, 2st 7.03) | 1.9574 | pass | 0.112× | ✅ |
| person_tracking_seed1 | 7.2431 | 0.4062 | 0.0000 | 0.0402 | True (peak 5144, 2st 8.07) | — | pass | 0.118× | ✅ |
| person_tracking_seed2 | 7.6710 | 0.4119 | 0.0000 | 0.0165 | True (peak 4994, 2st 6.88) | — | pass | 0.110× | ✅ |
| person_tracking2 | 6.4244 | 0.5501 | 0.0000 | 1.9878 | True (peak 4734, 2st 6.43) | 1.5275 | pass | 0.152× | ✅ |
| person_tracking2_seed1 | 6.8162 | 0.4785 | 0.0000 | 2.3391 | True (peak 4738, 2st 8.09) | — | pass | 0.187× | ✅ |
| person_tracking2_seed2 | 7.1838 | 0.4607 | 0.0000 | 2.3632 | True (peak 4734, 2st 7.93) | — | pass | 0.195× | ✅ |

## 3. 诚实边界

- **跨 seed（seed1/seed2）无 C− 臂** ⇒ 这些格 J7 = None（阴性对照未跑；J7 非 PASS 票，见 prereg §3 注）。
- **J4 只报数**（§10.7 参考线，比值恒 <0.3 ⇒ 标「参考线无判别力」，不入结论支撑）。
- **口径边界**（承 L1 §12 v4）：出口 = samepose；旧 `--causal`（快照位姿）与 `final_map`（合并图末帧层）为诊断口径，禁进出口/禁混引；单 PLY（output②）在新口径下的状态见 L1 v4 §3（不主张单 PLY 可用）。
- **pt/person_tracking 末帧层 ≈0** ⇒ J5 用**峰值**核验非退化（不是末值）。

## 4. 工件与可追溯

- manifest：`results/dynport_offline/evidence_L3/manifest_offline_L1_L3.json`（head `3302209329b533f46c5d32840114037afca64b72`）。
- 判据机输出：`evidence_L3/dynport_offline_L1_<label>_L3_{samepose,causal,final}.json`（samepose=出口）。
- run 目录：`results/dynport_offline/L3/<label>_<arm>/`（本批新跑）+ 复用 `L1_v4/`、`L2/`（跨批同一算子）。
- SHA256 provenance：`evidence_L3/artifact_sha256_L3.json`。
- 口径分解/位姿控制：`evidence/diag_j3_calibers.json`（L1 轮，同口径）。

## 5. 出口与后续

- **L3 正式规模泛化达标** ⇒ 论文 2 方法腿（L1 3 序列 + L2 泛化 + L3 全网格）三证据在盘。
- **`codec 联动`（§6 括号内）为**未定义占位** —— 见 `results/dynport_offline/L3/report_L3_scope_2026-10-08.md`（无设计档/无接口；A 线 codec 无动态层通路）。**本判决只覆盖已锁的网格部分**，缺口另呈。
- **G2（关卡②）**：本判决数字入论文/账本前必过。

