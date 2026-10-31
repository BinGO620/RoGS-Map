# embrace_dyn 生死筛结果（判据机输出，无人工读数）

> 判据与阈值 = 预注册 `prereg_dyn_probe.md` §7（跑前锁定，**六条**）；本文件由 `scripts/02_analysis/analyze_dyn_probe.py` 生成，数字全部来自 `dyn_probe_results.json`。
> 配置一致性自检：通过 

## gate（n_static=55174）

| 臂 | dyn_psnr (dB) | dyn_dl1 (cm) | **bad_psnr** | **bad_dl1 (cm)** | bad_px | dyn_cov | full_psnr | static_psnr | ghost_excess | n_dyn |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 20.84 | 18.74 | 20.55 | 27.08 | 17747 | 1.000 | 21.31 | 23.76 | -2.59 | 0 |
| P2 | 31.12 | 10.81 | 31.28 | 15.30 | 17747 | 1.000 | 23.39 | 23.88 | -2.54 | 3532 |
| C- | 18.71 | 19.13 | 18.32 | 26.59 | 17747 | 1.000 | 19.30 | 20.05 | -1.69 | 3532 |
| P4 | 20.37 | 18.78 | 20.06 | 26.84 | 17747 | 1.000 | 20.76 | 22.60 | -2.16 | 11906 |

**远离 t0 帧（|f−t0|≥50，n=12）**：P2 dl1=10.49cm / P4 dl1=19.15cm

- **1_ceiling**: {'dl1_ratio': 0.5768, 'psnr_gain_db': 10.2821, 'pass': True, 'reference_only': True}
- **1b_ceiling_bad_subset**: {'dl1_ratio': 0.5647, 'psnr_gain_db': 10.7305, 'mean_bad_px': 17747.125, 'pass': True}
  - 注记：补遗规定本口径为**主读数**；全掩码口径 1_ceiling 降为参考
- **2_motion_necessity**: {'dl1_ratio_far': 1.8257, 'n_frames': 12, 'pass': True}
  - 成本注记：P4 的 n_dyn=11906 为 P2 均值 3532 的 3.37× ⇒ 两臂**未做成本配平**，故 P4 的静态区损伤幅度不可与 P2 直接对等比较
- **3_no_harm**: {'d_static_db': 0.1186, 'd_full_db': 2.0864, 'pass': True}
  - 注记：预注册该条字面为双侧 |Δstatic|≤0.25dB；实测为正向改善（详见 verdict 局限）
- **4_cost**: {'n_dyn_frac': 0.064, 'pass': True}
- **5_instrument**: {'dl1_ratio': 1.7696, 'pass': True}
- **6_positive_control**: {'max_abs_delta_db': 0.0003, 'n_frames': 8, 'pass': True, 'artifact': 'results/embrace_dyn/evidence/control_p1_vs_render_compare.json'}
- **desc_decomposition**: {'M_bad': {'px': 17747.125, 'dl1_ratio_P2_over_P1': 0.5647, 'psnr_P1': 20.5542, 'psnr_P2': 31.2847}, 'M_good': {'px': 14078.0625, 'dl1_ratio_P2_over_P1': 1.192, 'psnr_P1': 22.1642, 'psnr_P2': 30.9101}}
  - 注记：两个像素集的 dB 增益**不可直接比较**（P1 基线不同）；可比量是各集内的深度-L1 比值。M_good 上 P2 的增益即'用该帧自身观测复制已正确背景'的成分。
- **desc_P4_vs_P1**: {'dl1_ratio': 1.0023, 'psnr_delta_db': -0.4641, 'd_static_db': -1.1634}
- **desc_dyn_cov**: {'all_arms_value': 1.0, 'discriminative': False}
  - 注记：掩码内'有渲染且不透明度≥0.5'的比例；本设定下各臂恒 1.000 ⇒ **该列无判别力**：冻结地图的动态区被背景高斯覆盖（无洞），反动态范式的代价是**内容错**而非**内容缺**
- **desc_support_px**: {'P1': {'mean_dyn_px': 31825.2, 'mean_vacated_px': 205446.2}, 'P2': {'mean_dyn_px': 31825.2, 'mean_vacated_px': 205446.2}, 'C-': {'mean_dyn_px': 31825.2, 'mean_vacated_px': 205446.2}, 'P4': {'mean_dyn_px': 31825.2, 'mean_vacated_px': 205446.2}}
- **拟合生效证据（此前产出、本轮消费）**：`{"P2": {"n_frames_with_fit": 16, "mean_loss_first": 0.11302, "mean_loss_last": 0.027, "mean_opa_before": 0.5, "mean_opa_after": 0.7579, "max_loss_last": 0.03993}, "P4_single_fit_at_t0": {"iters": 300, "loss_first": 0.14034, "loss_last": 0.0286, "opa_mean_before": 0.5, "opa_mean_after": 0.7109}, "P4_n_dyn": 11906}`

⇒ **判决：GO**

## baseline（n_static=84162）

| 臂 | dyn_psnr (dB) | dyn_dl1 (cm) | **bad_psnr** | **bad_dl1 (cm)** | bad_px | dyn_cov | full_psnr | static_psnr | ghost_excess | n_dyn |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 20.92 | 19.12 | 20.61 | 27.88 | 17673 | 1.000 | 21.53 | 24.34 | -0.30 | 0 |
| P2 | 31.35 | 10.72 | 31.58 | 15.46 | 17673 | 1.000 | 23.81 | 24.46 | -0.21 | 3532 |
| C- | 18.73 | 19.45 | 18.46 | 27.33 | 17673 | 1.000 | 19.50 | 20.34 | 0.49 | 3532 |
| P4 | 20.25 | 19.69 | 20.10 | 27.76 | 17673 | 1.000 | 21.10 | 23.24 | 0.27 | 11906 |

**远离 t0 帧（|f−t0|≥50，n=12）**：P2 dl1=10.43cm / P4 dl1=20.37cm

- **1_ceiling**: {'dl1_ratio': 0.5608, 'psnr_gain_db': 10.4344, 'pass': True, 'reference_only': True}
- **1b_ceiling_bad_subset**: {'dl1_ratio': 0.5548, 'psnr_gain_db': 10.9783, 'mean_bad_px': 17673.3125, 'pass': True}
  - 注记：补遗规定本口径为**主读数**；全掩码口径 1_ceiling 降为参考
- **2_motion_necessity**: {'dl1_ratio_far': 1.9522, 'n_frames': 12, 'pass': True}
  - 成本注记：P4 的 n_dyn=11906 为 P2 均值 3532 的 3.37× ⇒ 两臂**未做成本配平**，故 P4 的静态区损伤幅度不可与 P2 直接对等比较
- **3_no_harm**: {'d_static_db': 0.1136, 'd_full_db': 2.2762, 'pass': True}
  - 注记：预注册该条字面为双侧 |Δstatic|≤0.25dB；实测为正向改善（详见 verdict 局限）
- **4_cost**: {'n_dyn_frac': 0.042, 'pass': True}
- **5_instrument**: {'dl1_ratio': 1.8137, 'pass': True}
- **6_positive_control**: {'max_abs_delta_db': 0.0003, 'n_frames': 8, 'pass': True, 'artifact': 'results/embrace_dyn/evidence/control_p1_vs_render_compare.json'}
- **desc_decomposition**: {'M_bad': {'px': 17673.3125, 'dl1_ratio_P2_over_P1': 0.5548, 'psnr_P1': 20.6057, 'psnr_P2': 31.584}, 'M_good': {'px': 14151.875, 'dl1_ratio_P2_over_P1': 1.0853, 'psnr_P1': 23.3482, 'psnr_P2': 31.452}}
  - 注记：两个像素集的 dB 增益**不可直接比较**（P1 基线不同）；可比量是各集内的深度-L1 比值。M_good 上 P2 的增益即'用该帧自身观测复制已正确背景'的成分。
- **desc_P4_vs_P1**: {'dl1_ratio': 1.0297, 'psnr_delta_db': -0.6662, 'd_static_db': -1.1048}
- **desc_dyn_cov**: {'all_arms_value': 1.0, 'discriminative': False}
  - 注记：掩码内'有渲染且不透明度≥0.5'的比例；本设定下各臂恒 1.000 ⇒ **该列无判别力**：冻结地图的动态区被背景高斯覆盖（无洞），反动态范式的代价是**内容错**而非**内容缺**
- **desc_support_px**: {'P1': {'mean_dyn_px': 31825.2, 'mean_vacated_px': 205446.2}, 'P2': {'mean_dyn_px': 31825.2, 'mean_vacated_px': 205446.2}, 'C-': {'mean_dyn_px': 31825.2, 'mean_vacated_px': 205446.2}, 'P4': {'mean_dyn_px': 31825.2, 'mean_vacated_px': 205446.2}}
- **拟合生效证据（此前产出、本轮消费）**：`{"P2": {"n_frames_with_fit": 16, "mean_loss_first": 0.11267, "mean_loss_last": 0.02668, "mean_opa_before": 0.5, "mean_opa_after": 0.7707, "max_loss_last": 0.03715}, "P4_single_fit_at_t0": {"iters": 300, "loss_first": 0.1495, "loss_last": 0.03318, "opa_mean_before": 0.5, "opa_mean_after": 0.7808}, "P4_n_dyn": 11906}`

⇒ **判决：GO**

## 材料盘点（残影候选，逐地图给区间避免与均值混引）

- **gate**：n_gauss=55174，抽样 23 帧中 23 帧掩码命中；挡在 GT 表面之前的点数 min=1 / mean=82.9 / max=335（max 占地图 0.6100%）。每 25 帧抽 1 帧；与评估 16 帧几乎不重叠 ⇒ 区间代表性有限
- **baseline**：n_gauss=84162，抽样 23 帧中 23 帧掩码命中；挡在 GT 表面之前的点数 min=2 / mean=157.2 / max=1016（max 占地图 1.2100%）。每 25 帧抽 1 帧；与评估 16 帧几乎不重叠 ⇒ 区间代表性有限

# 独立诊断（`diag_causal_checks.py`：帧率实测 / 速度分布 / M_bad 构成）

- **帧率（实测，非标称）**：median 间隔 0.0335s ⇒ **29.83 Hz**（源 `datasets/bonn/rgbd_bonn_person_tracking2/rgb.txt timestamps`）
- **速度估计器实测分布**（n=60）：m/帧 min=0.0092 / med=0.1187 / max=0.3473 ⇒ 按实测帧率 **0.27–10.36 m/s**（中位 3.54）
  - 判读：跨度 0.27–10.4 m/s：低端是正常步行速度、高端物理不合理 ⇒ 估计器**不稳定不可用**（并非一律不可能）；其使用使 C2 比值 1.23（更差）
- **M_bad 构成 gate**：掩码 509203 px 中 bad=283954 （55.8%）；其中**洞（P1 深度无效）=0**（占 bad 0.0%）、wrong(>10cm)=283954 ⇒ 50cm 惩罚常数生效 = **False**
- **M_bad 构成 baseline**：掩码 509203 px 中 bad=282773 （55.5%）；其中**洞（P1 深度无效）=0**（占 bad 0.0%）、wrong(>10cm)=282773 ⇒ 50cm 惩罚常数生效 = **False**

# 因果批（预注册 `prereg_dyn_probe_causal.md`）

> 因果臂的均值一律取**同帧集**（各臂共有有效帧的交集）——关卡① 重大项整改。

> 配置一致性自检：通过；因果臂只用帧号 ≤ t 的数据（插入帧 = 最近前置 KF）。

## gate（n_static=55174；冷启动帧 [2] 不计入）

| 臂 | dyn_psnr (dB) | dyn_dl1 (cm) | **bad_psnr** | **bad_dl1 (cm)** | good_psnr | good_dl1 | 全图 PSNR | 静态区 PSNR | n_dyn | n |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 20.62 | 18.51 | 20.34 | 26.70 | 22.01 | 5.01 | 21.00 | 23.51 | 0 | 15 |
| P2 | 31.11 | 11.03 | 31.18 | 15.71 | 31.00 | 6.02 | 23.20 | 23.64 | 3657 | 15 |
| P2c | 22.17 | 14.10 | 21.83 | 20.18 | 23.20 | 5.95 | 21.59 | 22.98 | 3909 | 15 |
| P2cv | 18.91 | 17.33 | 18.32 | 24.31 | 20.46 | 5.75 | 19.83 | 21.24 | 3909 | 15 |
| C-c | 18.75 | 18.62 | 18.43 | 26.30 | 20.50 | 5.84 | 19.13 | 20.26 | 3909 | 15 |

（同帧集：n=15；`dt_eval` ∈ [1.0, 4.0]；冷启动帧 [2]；v_norm 分位 {'min': 0.009198, 'median': 0.118711, 'max': 0.3473, 'n': 30}）

- **C1_causal_retention**: {'retention_P2cv': 0.1574, 'retention_P2c': 0.5902, 'oracle_gain_cm': 7.4763, 'pass': False, 'reference_only': True}
- **C1b_causal_retention_bad_subset**: {'retention_P2c': 0.5936, 'retention_P2cv': 0.2172, 'oracle_gain_cm': 10.9919, 'pass': True}
  - 注记：补遗规定本口径为主读数（主臂 = P2c，因 P2cv 的速度估计器被实测证伪）
- **C2_velocity_gain**: {'dl1_ratio_P2cv_over_P2c': 1.2296, 'pass': False}
  - 注记：不达标：速度项使结果更差 ⇒ 机制退化为'KF 插入+保持'。估计器实测分布 0.0092–0.347 m/帧（按实测 29.83Hz 折 0.27–10.4 m/s，中位 3.54）——低端是正常步行、高端物理不合理 ⇒ **不稳定不可用**；根因：GTMC 掩码面积在相邻 KF 间跳动 4k→116k px，质心随掩码形状漂移
- **C3_no_harm**: {'d_static_P2c': -0.5346, 'd_full_P2c': 0.5953, 'd_static_P2cv': -2.2763, 'd_full_P2cv': -1.1641, 'pass': False}
- **C4_cost**: {'n_dyn_frac': 0.0708, 'pass': True}
- **C5_instrument**: {'dl1_ratio': 1.3207, 'pass': True}

- 口径声明：掩码内覆盖率各臂恒 1.000 ⇒ 该列在本设定下无判别力（已登记，不参与任何判据）

⇒ **因果判决：PARTIAL**

## baseline（n_static=84162；冷启动帧 [2] 不计入）

| 臂 | dyn_psnr (dB) | dyn_dl1 (cm) | **bad_psnr** | **bad_dl1 (cm)** | good_psnr | good_dl1 | 全图 PSNR | 静态区 PSNR | n_dyn | n |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 20.81 | 18.91 | 20.49 | 27.72 | 23.39 | 4.78 | 21.30 | 24.22 | 0 | 15 |
| P2 | 31.51 | 10.97 | 31.70 | 15.94 | 31.72 | 5.25 | 23.71 | 24.34 | 3657 | 15 |
| P2c | 22.57 | 14.29 | 22.06 | 20.57 | 24.16 | 5.82 | 21.96 | 23.59 | 3909 | 15 |
| P2cv | 19.36 | 17.40 | 18.83 | 24.59 | 21.52 | 5.53 | 20.11 | 21.73 | 3909 | 15 |
| C-c | 18.96 | 19.01 | 18.71 | 27.31 | 20.66 | 6.44 | 19.28 | 20.50 | 3909 | 15 |

（同帧集：n=15；`dt_eval` ∈ [1.0, 4.0]；冷启动帧 [2]；v_norm 分位 {'min': 0.009163, 'median': 0.118716, 'max': 0.347216, 'n': 30}）

- **C1_causal_retention**: {'retention_P2cv': 0.1905, 'retention_P2c': 0.5826, 'oracle_gain_cm': 7.9446, 'pass': False, 'reference_only': True}
- **C1b_causal_retention_bad_subset**: {'retention_P2c': 0.6068, 'retention_P2cv': 0.2658, 'oracle_gain_cm': 11.7775, 'pass': True}
  - 注记：补遗规定本口径为主读数（主臂 = P2c，因 P2cv 的速度估计器被实测证伪）
- **C2_velocity_gain**: {'dl1_ratio_P2cv_over_P2c': 1.2181, 'pass': False}
  - 注记：不达标：速度项使结果更差 ⇒ 机制退化为'KF 插入+保持'。估计器实测分布 0.0092–0.347 m/帧（按实测 29.83Hz 折 0.27–10.4 m/s，中位 3.54）——低端是正常步行、高端物理不合理 ⇒ **不稳定不可用**；根因：GTMC 掩码面积在相邻 KF 间跳动 4k→116k px，质心随掩码形状漂移
- **C3_no_harm**: {'d_static_P2c': -0.6289, 'd_full_P2c': 0.6635, 'd_static_P2cv': -2.4906, 'd_full_P2cv': -1.1952, 'pass': False}
- **C4_cost**: {'n_dyn_frac': 0.0464, 'pass': True}
- **C5_instrument**: {'dl1_ratio': 1.3308, 'pass': True}

- 口径声明：掩码内覆盖率各臂恒 1.000 ⇒ 该列在本设定下无判别力（已登记，不参与任何判据）

⇒ **因果判决：PARTIAL**

# 因果轮 II（预注册 `prereg_dyn_probe_causal2.md`：掩码连通域 + 刚性常扭转外推）

> 配置一致性自检：通过；同帧集配对。

## gate（n_static=55174）

| 臂 | dyn_psnr | dyn_dl1 | **bad_psnr** | **bad_dl1** | good_dl1 | 全图 | 静态区 | n_dyn |
|---|---|---|---|---|---|---|---|---|
| P1 | 19.54 | 18.56 | 19.19 | 27.62 | 4.89 | 21.27 | 24.31 | 0 |
| P2 | 30.71 | 10.10 | 30.86 | 15.34 | 5.71 | 24.01 | 24.46 | 4344 |
| P2c | 21.43 | 13.14 | 21.04 | 19.66 | 5.94 | 22.01 | 23.64 | 4777 |
| P2cs | 21.29 | 13.40 | 21.00 | 20.16 | 5.86 | 22.00 | 23.64 | 4234 |
| P2cm | 17.76 | 16.95 | 17.37 | 24.58 | 5.72 | 19.88 | 21.57 | 4234 |
| P2cr | 19.85 | 13.64 | 19.75 | 20.47 | 6.11 | 21.75 | 23.48 | 4234 |
| C-c | 17.57 | 18.62 | 17.03 | 27.05 | 5.87 | 19.15 | 20.57 | 4234 |

（同帧集 n=12；mask_cc_frac {'min': 0.2074, 'median': 0.9001, 'max': 1.0, 'n': 12}；icp_rmse_m {'min': 0.010289, 'median': 0.038799, 'max': 0.67036, 'n': 12}）

- **D1_mask_stabilization**: {'bad_dl1_ratio_P2cs_over_P2c': 1.0253, 'pass': False, 'ablation_only': True}
- **D2_appearance_retention**: {'retention_psnr_P2cr': 0.0475, 'retention_psnr_P2c_reference': 0.1581, 'oracle_gain_db': 11.6706, 'pass': False}
- **D3_geometry_retention**: {'retention_bad_P2cr': 0.5826, 'oracle_gain_cm': 12.2852, 'pass': False}
- **D4_no_harm**: {'d_static_db': -0.8309, 'd_full_db': 0.483, 'P2c_reference_d_static': -0.672, 'pass': False}
- **D5_cost**: {'n_dyn_frac': 0.0767, 'pass': True}
- **D6_instrument**: {'bad_dl1_ratio_Cm_over_P2cr': 1.3217, 'pass': True}

- 平移类臂消融（不判）：{"P2cm": {"dyn_bad_psnr": 17.3661, "dyn_bad_dl1_cm": 24.582}}

⇒ **因果轮 II 判决：NO-GO**

## baseline（n_static=84162）

| 臂 | dyn_psnr | dyn_dl1 | **bad_psnr** | **bad_dl1** | good_dl1 | 全图 | 静态区 | n_dyn |
|---|---|---|---|---|---|---|---|---|
| P1 | 19.54 | 18.74 | 19.09 | 28.40 | 4.59 | 21.53 | 25.07 | 0 |
| P2 | 31.09 | 9.66 | 31.25 | 14.93 | 5.04 | 24.53 | 25.22 | 4344 |
| P2c | 21.73 | 12.96 | 20.99 | 19.56 | 5.71 | 22.36 | 24.29 | 4777 |
| P2cs | 21.78 | 13.25 | 21.19 | 20.06 | 5.69 | 22.35 | 24.28 | 4234 |
| P2cm | 17.90 | 16.86 | 17.35 | 24.71 | 5.68 | 20.16 | 22.19 | 4234 |
| P2cr | 20.29 | 13.39 | 20.04 | 20.25 | 5.89 | 22.08 | 24.09 | 4234 |
| C-c | 17.43 | 18.79 | 17.22 | 27.85 | 6.51 | 19.20 | 20.80 | 4234 |

（同帧集 n=12；mask_cc_frac {'min': 0.2074, 'median': 0.9001, 'max': 1.0, 'n': 12}；icp_rmse_m {'min': 0.010273, 'median': 0.038771, 'max': 0.66984, 'n': 12}）

- **D1_mask_stabilization**: {'bad_dl1_ratio_P2cs_over_P2c': 1.026, 'pass': False, 'ablation_only': True}
- **D2_appearance_retention**: {'retention_psnr_P2cr': 0.0778, 'retention_psnr_P2c_reference': 0.1562, 'oracle_gain_db': 12.1616, 'pass': False}
- **D3_geometry_retention**: {'retention_bad_P2cr': 0.6054, 'oracle_gain_cm': 13.4735, 'pass': False}
- **D4_no_harm**: {'d_static_db': -0.98, 'd_full_db': 0.551, 'P2c_reference_d_static': -0.7826, 'pass': False}
- **D5_cost**: {'n_dyn_frac': 0.0503, 'pass': True}
- **D6_instrument**: {'bad_dl1_ratio_Cm_over_P2cr': 1.3756, 'pass': True}

- 平移类臂消融（不判）：{"P2cm": {"dyn_bad_psnr": 17.3464, "dyn_bad_dl1_cm": 24.7056}}

⇒ **因果轮 II 判决：NO-GO**

# 跨序列泛化复现（第二序列 balloon；预注册 `prereg_dyn_probe_balloon.md`）

> 判据与 pt2 同阈值；**两序列都是单 seed**，故属「跨序列」而非「全表」级证据。

| 序列 | 地图 | 帧数 | P1 bad_psnr | P2 bad_psnr | **bad 增益 (dB)** | **bad dl1 比值** | bad 占图 | 静态区 Δ | 全图 Δ | n_dyn 占比 |
|---|---|---|---|---|---|---|---|---|---|---|
| balloon | gate | 15 | 18.2559 | 34.0723 | **15.8164** | **0.2137** | 8.720% | 0.1725 | 2.2522 | 7.680% |
| balloon | baseline | 15 | 18.476 | 34.3237 | **15.8477** | **0.184** | 9.160% | 0.1618 | 2.2526 | 12.080% |

**pt2 同口径参考**（母批，16 帧）：bad 增益 +10.73/+11.00 dB、bad dl1 比值 0.565/0.555、bad 占图 5.8%、n_dyn 占比 6.4%/4.2%。

- balloon/gate P2c 因果保留率：**bad_dl1 0.6963** / bad_psnr 0.2208 / 静态区 Δ -0.2555 dB（dt=0 帧 [125, 320] 剔除后：{'n_frames': 13, 'retention_bad_dl1': 0.6658, 'retention_bad_psnr': 0.1443}）
- balloon/baseline P2c 因果保留率：**bad_dl1 0.7186** / bad_psnr 0.2415 / 静态区 Δ -0.1945 dB（dt=0 帧 [125, 320] 剔除后：{'n_frames': 13, 'retention_bad_dl1': 0.6871, 'retention_bad_psnr': 0.1612}）

**pt2 同口径参考**（因果轮 I，15 帧）：P2c bad_dl1 保留 0.590/0.583、bad_psnr 保留约 0.12–0.14。

# 因果轮 III（预注册 `prereg_dyn_probe_causal3.md`：多帧并集插入 + 逐基元 KNN 速度）

> 配置一致性自检：通过；同帧集配对。

## gate（n_static=55174）

| 臂 | dyn_psnr | dyn_dl1 | **bad_psnr** | **bad_dl1** | good_dl1 | 全图 | 静态区 | n_dyn |
|---|---|---|---|---|---|---|---|---|
| P1 | 20.62 | 18.51 | 20.34 | 26.70 | 5.01 | 21.00 | 23.51 | 0 |
| P2 | 31.09 | 11.03 | 31.17 | 15.71 | 6.02 | 23.20 | 23.63 | 3657 |
| P2c | 22.17 | 14.10 | 21.83 | 20.18 | 5.95 | 21.59 | 22.98 | 3909 |
| P2cu | 22.28 | 13.83 | 21.95 | 19.56 | 6.34 | 21.61 | 22.82 | 20048 |
| P2cuv | 21.12 | 14.86 | 20.65 | 21.18 | 6.62 | 21.24 | 22.48 | 20048 |
| C-u | 18.61 | 18.91 | 18.35 | 26.43 | 6.30 | 18.95 | 19.86 | 20048 |

- **E1_multiframe_ablation**: {'bad_dl1_ratio_P2cu_over_P2c': 0.9693, 'pass': False, 'ablation_only': True, 'bad_psnr_P2c': 21.8278, 'bad_psnr_P2cu': 21.9475}
- **E2_appearance_retention**: {'retention_psnr_P2cuv': 0.0285, 'pass': False, 'refs': {'P2c': 0.1376, 'P2cu': 0.1487}}
- **E3_geometry_retention**: {'retention_bad_P2cuv': 0.5021, 'pass': False, 'refs': {'P2c': 0.5932, 'P2cu': 0.6496}}
- **E4_no_harm**: {'d_static_db': -1.0303, 'd_full_db': 0.2428, 'pass': False}
- **E5_cost**: {'n_dyn_frac': 0.3634, 'pass': True}
- **E6_instrument**: {'bad_dl1_ratio_Cu_over_P2cuv': 1.2475, 'pass': True}

- 逐点速度统计：{"n": 15, "mean_matched_frac": 0.7487, "median_v_m_per_frame": 0.0088, "d_bar_m_example": 2.90254}

- **E7 分层（Δt）**：{"P2c": {"dt=1": {"n": 3, "dl1": 0.9352, "psnr": 0.3415}, "dt=2": {"n": 5, "dl1": 0.6291, "psnr": 0.1924}, "dt=3": {"n": 4, "dl1": 0.2809, "psnr": 0.0118}, "dt=4": {"n": 3, "dl1": 0.5105, "psnr": 0.0378}}, "P2cu": {"dt=1": {"n": 3, "dl1": 1.0303, "psnr": 0.3306}, "dt=2": {"n": 5, "dl1": 0.664, "psnr": 0.1958}, "dt=3": {"n": 4, "dl1": 0.4005, "psnr": 0.0322}, "dt=4": {"n": 3, "dl1": 0.5249, "psnr": 0.0663}}, "P2cuv": {"dt=1": {"n": 3, "dl1": 0.8967, "psnr": 0.2461}, "dt=2": {"n": 5, "dl1": 0.5831, "psnr": 0.1746}, "dt=3": {"n": 4, "dl1": 0.2507, "psnr": -0.1407}, "dt=4": {"n": 3, "dl1": 0.2644, "psnr": -0.1507}}}

- **E7 分层（掩码规模）**：{"P2c": {"n_dyn<med": {"n": 7, "dl1": 0.216, "psnr": 0.014}, "n_dyn>=med": {"n": 8, "dl1": 0.8012, "psnr": 0.2311}}, "P2cu": {"n_dyn<med": {"n": 7, "dl1": 0.2902, "psnr": 0.0476}, "n_dyn>=med": {"n": 8, "dl1": 0.8478, "psnr": 0.2251}}, "P2cuv": {"n_dyn<med": {"n": 7, "dl1": 0.1767, "psnr": -0.0209}, "n_dyn>=med": {"n": 8, "dl1": 0.6815, "psnr": 0.0659}}}

⇒ **因果轮 III 判决：NO-GO**

## baseline（n_static=84162）

| 臂 | dyn_psnr | dyn_dl1 | **bad_psnr** | **bad_dl1** | good_dl1 | 全图 | 静态区 | n_dyn |
|---|---|---|---|---|---|---|---|---|
| P1 | 20.81 | 18.91 | 20.49 | 27.72 | 4.78 | 21.30 | 24.22 | 0 |
| P2 | 31.48 | 10.97 | 31.69 | 15.94 | 5.25 | 23.70 | 24.34 | 3657 |
| P2c | 22.56 | 14.28 | 22.04 | 20.57 | 5.82 | 21.96 | 23.60 | 3909 |
| P2cu | 22.78 | 14.09 | 22.38 | 20.10 | 6.03 | 21.99 | 23.43 | 20048 |
| P2cuv | 21.60 | 15.20 | 21.09 | 21.86 | 6.40 | 21.56 | 22.98 | 20048 |
| C-u | 18.73 | 19.32 | 18.46 | 27.42 | 6.91 | 19.13 | 20.10 | 20048 |

- **E1_multiframe_ablation**: {'bad_dl1_ratio_P2cu_over_P2c': 0.9775, 'pass': False, 'ablation_only': True, 'bad_psnr_P2c': 22.0379, 'bad_psnr_P2cu': 22.3814}
- **E2_appearance_retention**: {'retention_psnr_P2cuv': 0.0535, 'pass': False, 'refs': {'P2c': 0.1382, 'P2cu': 0.1689}}
- **E3_geometry_retention**: {'retention_bad_P2cuv': 0.4976, 'pass': False, 'refs': {'P2c': 0.6074, 'P2cu': 0.6467}}
- **E4_no_harm**: {'d_static_db': -1.2425, 'd_full_db': 0.2635, 'pass': False}
- **E5_cost**: {'n_dyn_frac': 0.2382, 'pass': True}
- **E6_instrument**: {'bad_dl1_ratio_Cu_over_P2cuv': 1.2546, 'pass': True}

- 逐点速度统计：{"n": 15, "mean_matched_frac": 0.749, "median_v_m_per_frame": 0.007, "d_bar_m_example": 2.90254}

- **E7 分层（Δt）**：{"P2c": {"dt=1": {"n": 3, "dl1": 0.7701, "psnr": 0.3855}, "dt=2": {"n": 5, "dl1": 0.6505, "psnr": 0.1287}, "dt=3": {"n": 4, "dl1": 0.3882, "psnr": 0.0367}, "dt=4": {"n": 3, "dl1": 0.5553, "psnr": 0.0618}}, "P2cu": {"dt=1": {"n": 3, "dl1": 0.8105, "psnr": 0.3796}, "dt=2": {"n": 5, "dl1": 0.6688, "psnr": 0.2053}, "dt=3": {"n": 4, "dl1": 0.4947, "psnr": 0.0452}, "dt=4": {"n": 3, "dl1": 0.5761, "psnr": 0.0831}}, "P2cuv": {"dt=1": {"n": 3, "dl1": 0.713, "psnr": 0.2813}, "dt=2": {"n": 5, "dl1": 0.5589, "psnr": 0.1214}, "dt=3": {"n": 4, "dl1": 0.351, "psnr": -0.119}, "dt=4": {"n": 3, "dl1": 0.3187, "psnr": -0.038}}}

- **E7 分层（掩码规模）**：{"P2c": {"n_dyn<med": {"n": 7, "dl1": 0.1927, "psnr": 0.0226}, "n_dyn>=med": {"n": 8, "dl1": 0.8059, "psnr": 0.2225}}, "P2cu": {"n_dyn<med": {"n": 7, "dl1": 0.2436, "psnr": 0.051}, "n_dyn>=med": {"n": 8, "dl1": 0.8397, "psnr": 0.2548}}, "P2cuv": {"n_dyn<med": {"n": 7, "dl1": 0.1518, "psnr": -0.0074}, "n_dyn>=med": {"n": 8, "dl1": 0.6632, "psnr": 0.0979}}}

⇒ **因果轮 III 判决：NO-GO**
