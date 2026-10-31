# 判决：DynPort-Offline L2 泛化批（§12 v4 samepose 口径）— 2026-10-08

> **账本**：D1-035。**判据出处** = `prereg_dynport_offline_L1.md` §12 v4（口径）+ §6（L2 路径，先锁：扩展序列 × 1 seed + 跨 seed ⇒ ≥2/3 泛化）。**数字零手抄**：本文件由 `scripts/dynport_offline/write_verdict_L2.py` 从 manifest 机写。**锁定 HEAD** `53fb88c10853275445e87b25fded90ec20c5bb55`。

## 0. 一句话

**泛化成立**：L2 共 **9** 个 run（扩展序列 × 1 seed + 跨 seed），**J3∧J1∧J2 全过 9/9**（门槛 9/9 ≥ 2/3 ⇒ **达标**）。扩展序列 J3 = 0.0308 / 0.0267 / 0.0000 dB；跨 seed J3 = -0.0137 / -0.0071 / 0.0449 / 0.0347 / 0.0000 / 0.0000 dB。

## 1. 读数（机写 manifest；出口口径 = samepose）

| 序列 | J1（≥2.5） | J2（≤0.70） | J3（\|Δ\|≤0.25） | J5 | J7 | J9 | 判 |
|---|---|---|---|---|---|---|---|
| crowd | 5.7637 | 0.5812 | 0.0308 | True | 1.3343 | pass | ✅ |
| crowd3 | 7.8946 | 0.4440 | 0.0267 | True | 1.5854 | pass | ✅ |
| person_tracking | 7.3834 | 0.4267 | 0.0000 | True | 1.9574 | pass | ✅ |
| crowd2_seed1 | 7.4714 | 0.5199 | -0.0137 | True | — | pass | ✅ |
| crowd2_seed2 | 7.7331 | 0.4502 | -0.0071 | True | — | pass | ✅ |
| balloon2_seed1 | 6.3986 | 0.2821 | 0.0449 | True | — | pass | ✅ |
| balloon2_seed2 | 5.7633 | 0.3385 | 0.0347 | True | — | pass | ✅ |
| person_tracking2_seed1 | 6.8162 | 0.4785 | 0.0000 | True | — | pass | ✅ |
| person_tracking2_seed2 | 7.1838 | 0.4607 | 0.0000 | True | — | pass | ✅ |

**泛化判据（§6）**：9/9 过 ⇒ **≥2/3 达标**。

## 2. 诚实边界

- **跨 seed 无 C− 臂** ⇒ 这些序列 J7 = None（阴性对照未跑；J7 非 PASS 票，见 prereg §3 注）。
- **口径边界**（承 L1 §12 v4）：J4 比值只报数；pt/person_tracking 末帧层为 0（J5 用**峰值**核验非退化）。
- **seed 数与序列数**：本批为 L2 泛化规模（1 seed × 扩展 + 跨 seed）；L3 = 全 7 序列 × 3 seed。

## 3. 工件与可追溯

- manifest：`results/dynport_offline/evidence_L2/manifest_offline_L1_L2.json`（head `53fb88c10853275445e87b25fded90ec20c5bb55`）。
- 判据机输出：`evidence_L2/dynport_offline_L1_<seq>_L2_{samepose,causal,final}.json`。
- run 目录：`results/dynport_offline/L2/<seq>_<arm>/`。
- 口径分解/位姿控制：`evidence/diag_j3_calibers.json`（L1 轮，同口径）。

## 4. 出口与后续

- **≥2/3 泛化达标** ⇒ 按 §6 进 **L3**（全 7 序列 × 3 seed + codec 联动）。
- 论文 2 方法腿：L1（3 序列）+ L2（泛化）双证据。

