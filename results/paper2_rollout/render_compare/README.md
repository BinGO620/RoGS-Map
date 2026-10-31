# 渲染对比批（离线渲染协议）— 2026-09-18 夜间批

> 工具: `scripts/02_analysis/render_compare.py`（单 run）+ `render_batch.py`（批驱动）。
> 协议: PLY=`point_cloud/final_after_opt`；帧=interval=5 均匀抽 8 帧（离线，不受 run 时 eval 采样影响）；
> 指标函数与 run 内 `eval_rendering` 同源（psnr/ssim/lpips/depth_l1）。
> 产物: `results/{exp}/render_compare/<run>_<ts>/`（cmp_*.jpg=[GT|render] + depth_*.jpg + render_metrics.json）。

## 1. R33 四臂 × 7 序列（84 run 全格，seed0-2）

| seq | baseline | swbaonly | final | gate | Δ(gate−base) | Δ(gate−swb) |
|---|---|---|---|---|---|---|
| balloon | 21.80 | 21.60 | 21.55 | 21.57 | -0.23 | -0.03 |
| balloon2 | 18.72 | 18.88 | 18.65 | 18.51 | -0.22 | -0.38 |
| crowd | 19.92 | 19.66 | 19.66 | 19.81 | -0.11 | +0.15 |
| crowd2 | 19.50 | 19.65 | 19.87 | 19.53 | +0.03 | -0.12 |
| crowd3 | 17.04 | 17.24 | 17.28 | 17.36 | +0.32 | +0.11 |
| person_tracking | 22.68 | 22.38 | 22.59 | 22.61 | -0.07 | +0.23 |
| person_tracking2 | 22.72 | 22.81 | 23.04 | 23.00 | +0.28 | +0.19 |

- baseline: mean = 20.341 dB (n=21)
- swbaonly: mean = 20.318 dB (n=21)
- final: mean = 20.377 dB (n=21)
- gate: mean = 20.340 dB (n=21)

## 2. R34（gate 3-seed；rb/sw = seed0）

| seq | gate mean | gate s0/s1/s2 | rb s0 | sw s0 |
|---|---|---|---|---|
| f1_room | 20.37 | 20.04/20.66/20.41 | 21.38 | 20.39 |
| f1_desk2 | 22.21 | 22.13/22.00/22.52 | 22.51 | 21.95 |
| f3_st_rpy | 21.98 | 22.32/21.85/21.77 | 22.22 | 21.69 |
| f3_office | 25.15 | 24.91/25.10/25.44 | 25.71 | 25.01 |
| moving_obstructing_box | 24.56 | 24.20/24.37/25.11 | 25.37 | 24.12 |
| f3_wk_rpy | 18.24 | 18.33/18.06/18.33 | 18.58 | 17.01 |

## 3. 关键事实

- **run 时 eval 的 PSNR=NaN 根因已定位（离线渲染器不受影响）**：`eval_rendering(interval=5)` 采样网格
  与关键帧网格完全碰撞（KF 编号恰落在 5 的倍数上）→ 循环体全 `continue` → 空聚合 → NaN。
  多序列命中（r33 批 79/84 NaN、mask_fix_iter 同因）。历史 run 的 PSNR 缺失是**采样 bug**，不是渲染差；
  本批离线渲染补齐 r33 全部 7 序列 PSNR（含此前缺的 crowd 家族）与 R34 全格。
- `scripts/render_gaussian_mesh.py` 于 v2 清理时被误删（`da832882`），`utils/geometry_metrics.py` 仍引用 →
  重建管线曾断链；2026-09-18 已从 v1 tag 恢复并实测通过（balloon 23 万面 mesh）。
- 几何评估 17 run 产物已落各 run（`geometry/` + `mapping_geometry_metrics_v2.json`）；
  官方 Bonn 绝对指标暂不可用（GT-in 决定性检验未对齐，详见 `resources/notes/bonn_geometry_alignment_2026-09-18.md`）。

## 4. 产物位置

- 本地: `results/{paper2_fulltable,paper2_rollout,mask_fix_iter}/render_compare/`
- 远端保留全量 png/jpg（`results/*/render_compare/`）
