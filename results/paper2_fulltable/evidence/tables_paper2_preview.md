# 论文 2 表格（ATE + 渲染 + 静态 + 效率）— 机器生成（2026-09-19）

> 生成器 `scripts/02_analysis/paper2_tables.py`；来源 = **R33 same-batch (baseline/swbaonly/final/gate x 7 Bonn seqs x 3 seeds, all runs 2026-09-16, identical code)**。
> ATE=col8 全帧 3-seed mean±sd（主表口径）；Tab.5 为 col14 关键帧口径（**禁止混引**）；
> 渲染=离线协议 8 帧采样（与 run 内 eval 同源函数）。
> **静态列口径优先级**：① **运行期 P-A**（`mapping_raw.csv` 的 `mask_type=static` 行，
> ~88 帧 @every5，与主表同批同码）；② 离线 6 帧早期信号（其余序列回退）。**两源不混算**。
> Sim3 列 = 本生成器按 `utils/eval_utils.py:96` 同协议（evo align_trajectory）自算，
> 自检：自算 SE3-ATE 应等于 col8。数字入论文前须过**关卡②**。

## Tab.1 主表 — ATE（cm, col8 全帧, seed0-2）

| seq | baseline | +SWBA | +SWBA+LC | gate (deployed) |
|---|---|---|---|---|
| balloon | 3.25±0.07 | 4.21±0.14 | 4.24±0.08 | 4.22±0.04 |
| balloon2 | 5.48±0.27 | 5.37±0.08 | 5.34±0.08 | 5.32±0.17 |
| crowd | 2.23±0.10 | 2.35±0.12 | 2.44±0.10 | 2.32±0.19 |
| crowd2 | 2.26±0.32 | 4.09±0.44 | 4.05±0.25 | 2.50±0.22 |
| crowd3 | 1.53±0.02 | 2.48±0.20 | 2.44±0.03 | 1.83±0.05 |
| person_tracking | 11.31±0.70 | 8.62±1.53 | 8.21±0.33 | 7.95±0.70 |
| person_tracking2 | 10.40±0.28 | 11.83±0.47 | 12.39±0.63 | 11.68±0.37 |

## Tab.5 附表 — ATE（cm, col14 关键帧）。**与 Tab.1 不同口径，禁止混引**

| seq | baseline | +SWBA | +SWBA+LC | gate (deployed) |
|---|---|---|---|---|
| balloon | 3.23±0.07 | 4.08±0.15 | 4.09±0.07 | 4.08±0.04 |
| balloon2 | 5.45±0.26 | 5.24±0.08 | 5.26±0.08 | 5.22±0.17 |
| crowd | 2.73±0.11 | 2.67±0.41 | 2.85±0.29 | 2.95±0.62 |
| crowd2 | 2.28±0.22 | 3.83±0.41 | 3.81±0.24 | 2.35±0.15 |
| crowd3 | 1.54±0.04 | 2.28±0.16 | 2.29±0.06 | 1.75±0.03 |
| person_tracking | 11.20±0.67 | 8.66±1.54 | 8.26±0.37 | 7.97±0.71 |
| person_tracking2 | 10.39±0.24 | 11.74±0.44 | 12.32±0.64 | 11.60±0.39 |

## Tab.2r 渲染 — 全图 PSNR / SSIM（离线协议）

| seq | baseline | +SWBA | +SWBA+LC | gate (deployed) |
|---|---|---|---|---|
| balloon | 21.80 / 0.852 | 21.60 / 0.852 | 21.55 / 0.849 | 21.57 / 0.851 |
| balloon2 | 18.72 / 0.808 | 18.88 / 0.809 | 18.65 / 0.807 | 18.51 / 0.807 |
| crowd | 19.92 / 0.829 | 19.66 / 0.828 | 19.66 / 0.827 | 19.81 / 0.828 |
| crowd2 | 19.50 / 0.823 | 19.65 / 0.818 | 19.87 / 0.820 | 19.53 / 0.823 |
| crowd3 | 17.04 / 0.778 | 17.24 / 0.777 | 17.28 / 0.777 | 17.36 / 0.778 |
| person_tracking | 22.68 / 0.860 | 22.38 / 0.862 | 22.59 / 0.861 | 22.61 / 0.861 |
| person_tracking2 | 22.72 / 0.861 | 22.81 / 0.857 | 23.04 / 0.862 | 23.00 / 0.864 |

## Tab.3s 静态区分区指标（`M_static = valid-depth ∧ ¬dynamic`，冻结掩码）

| seq | arm | static PSNR | static SSIM | coverage | ghost_excess (cm) | 掩码源 |
|---|---|---|---|---|---|---|
| balloon | baseline | 27.68 | 0.911 | 1.000 | 2.97 | dynamic_mask |
| balloon | +SWBA | 27.37 | 0.912 | 1.000 | 2.94 | dynamic_mask |
| balloon | +SWBA+LC | 27.74 | 0.912 | 1.000 | 3.31 | dynamic_mask |
| balloon | gate (deployed) | 27.65 | 0.912 | 1.000 | 0.45 | dynamic_mask |
| balloon2 | baseline | 26.28 | 0.902 | 1.000 | -10.85 | dynamic_mask |
| balloon2 | +SWBA | 26.11 | 0.900 | 1.000 | -12.95 | dynamic_mask |
| balloon2 | +SWBA+LC | 26.12 | 0.898 | 1.000 | -11.00 | dynamic_mask |
| balloon2 | gate (deployed) | 26.45 | 0.900 | 1.000 | -13.24 | dynamic_mask |
| crowd | baseline | 27.61 | 0.923 | 1.000 | 1.45 | dynamic_mask |
| crowd | +SWBA | 27.28 | 0.922 | 1.000 | 0.73 | dynamic_mask |
| crowd | +SWBA+LC | 27.10 | 0.920 | 1.000 | 1.99 | dynamic_mask |
| crowd | gate (deployed) | 27.60 | 0.922 | 1.000 | 1.97 | dynamic_mask |
| crowd2 | baseline | 27.45 | 0.922 | 1.000 | 4.43 | dynamic_mask |
| crowd2 | +SWBA | 26.91 | 0.914 | 1.000 | -1.84 | dynamic_mask |
| crowd2 | +SWBA+LC | 27.27 | 0.914 | 1.000 | 3.39 | dynamic_mask |
| crowd2 | gate (deployed) | 27.54 | 0.922 | 1.000 | 4.49 | dynamic_mask |
| crowd3 | baseline | 24.79 | 0.919 | 1.000 | 4.54 | dynamic_mask |
| crowd3 | +SWBA | 24.79 | 0.917 | 1.000 | 3.44 | dynamic_mask |
| crowd3 | +SWBA+LC | 24.62 | 0.916 | 1.000 | 4.84 | dynamic_mask |
| crowd3 | gate (deployed) | 24.65 | 0.918 | 1.000 | 5.48 | dynamic_mask |
| person_tracking | baseline | 27.31 | 0.901 | 1.000 | 3.96 | dynamic_mask |
| person_tracking | +SWBA | 27.59 | 0.901 | 1.000 | 4.68 | dynamic_mask |
| person_tracking | +SWBA+LC | 27.65 | 0.904 | 1.000 | 3.47 | dynamic_mask |
| person_tracking | gate (deployed) | 27.60 | 0.901 | 1.000 | 3.86 | dynamic_mask |
| person_tracking2 | baseline | 27.74 | 0.893 | 1.000 | 2.21 | dynamic_mask |
| person_tracking2 | +SWBA | 28.19 | 0.896 | 1.000 | 1.57 | dynamic_mask |
| person_tracking2 | +SWBA+LC | 27.73 | 0.894 | 1.000 | 0.89 | dynamic_mask |
| person_tracking2 | gate (deployed) | 27.61 | 0.894 | 1.000 | 1.75 | dynamic_mask |

## Tab.4 效率（在线阶段；fps 受并发混杂，只作旁证）

| arm | 高斯数 mean（7 序列 × 3 seed） | 峰值显存 max (GB) | online_fps median |
|---|---|---|---|
| baseline | 47086 | 3.36 | 0.456 |
| +SWBA | 52476 | 4.13 | 0.354 |
| +SWBA+LC | 45212 | 3.58 | 0.354 |
| gate (deployed) | 47040 | 3.57 | 0.415 |

## Tab.2 pt 逐 seed（col8）+ 同批自算 Sim3

| seq | arm | seed0/1/2 ATE | Sim3 尺度 seed0/1/2 | Sim3-ATE seed0/1/2 |
|---|---|---|---|---|
| person_tracking | baseline | 11.46/10.55/11.92 | 1.161/1.145/1.147 | 7.31/6.82/8.71 |
| person_tracking | +SWBA | 10.38/7.70/7.77 | 1.111/1.093/1.098 | 8.24/5.47/5.28 |
| person_tracking | +SWBA+LC | 7.93/8.58/8.12 | 1.094/1.109/1.111 | 5.73/5.88/5.00 |
| person_tracking | gate (deployed) | 8.54/8.12/7.18 | 1.099/1.106/1.089 | 6.32/5.33/4.91 |
| person_tracking2 | baseline | 10.37/10.14/10.70 | 1.116/1.115/1.110 | 7.38/7.15/8.15 |
| person_tracking2 | +SWBA | 11.81/12.31/11.38 | 1.094/1.106/1.096 | 10.17/10.34/9.61 |
| person_tracking2 | +SWBA+LC | 11.72/12.97/12.48 | 1.100/1.089/1.096 | 9.87/11.68/10.90 |
| person_tracking2 | gate (deployed) | 12.04/11.69/11.30 | 1.104/1.099/1.097 | 10.10/9.87/9.47 |

## 覆盖状态

- baseline: ATE 7/7 | 渲染 7/7 | 静态 7/7 | 效率 7/7
- +SWBA: ATE 7/7 | 渲染 7/7 | 静态 7/7 | 效率 7/7
- +SWBA+LC: ATE 7/7 | 渲染 7/7 | 静态 7/7 | 效率 7/7
- gate (deployed): ATE 7/7 | 渲染 7/7 | 静态 7/7 | 效率 7/7
