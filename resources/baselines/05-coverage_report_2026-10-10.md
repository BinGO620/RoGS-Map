# 复现基线覆盖报告（机写）

> **生成**：`scripts/02_analysis/paper2_baseline_coverage.py`（2026-10-10）
> **来源**：`resources/baselines/baselines_result/<method>/{tracking,mapping,efficiency}_raw.csv`
> **性质**：论文 v1 §3 系统横向对比的**事实基础**；只读盘点，不改任何 raw 结果。

## 1. 方法清单（11）与能力

| 方法 | 类别 |
|---|---|
| Co-SLAM | static/nerf |
| DG-SLAM | dynamic/3dgs |
| DynaGSLAM | dynamic/3dgs |
| DynaSLAM | dynamic/keypoint |
| MonoGS | static/3dgs |
| NGD-SLAM | dynamic/keypoint |
| ORB_SLAM3 | static/keypoint |
| RGD-SLAM | dynamic/3dgs |
| RoDyn-SLAM | dynamic/nerf |
| SplaTAM | static/3dgs |
| WildGS-SLAM | dynamic/3dgs |

## 2. 覆盖矩阵（BONN 8 序列 × 3 seed 应有的行数 = 24）

| 方法 | tracking OK | mapping 指标 | efficiency OK | BONN 序列 |
|---|---|---|---|---|
| Co-SLAM | 24/24 | PSNR 24/24 | 24/24 | 8 |
| DG-SLAM | 24/24 | PSNR 24/24 | 24/24 | 8 |
| DynaGSLAM | 24/24 | PSNR 24/24 | 24/24 | 8 |
| DynaSLAM | 24/24 | PSNR 0/24 | 24/24 | 8 |
| MonoGS | 24/24 | PSNR 24/24 | 24/24 | 8 |
| NGD-SLAM | 24/24 | PSNR 0/24 | 24/24 | 8 |
| ORB_SLAM3 | 24/24 | PSNR 0/24 | 24/24 | 8 |
| RGD-SLAM | 24/24 | PSNR 24/24 | 24/24 | 8 |
| RoDyn-SLAM | 24/24 | PSNR 24/24 | 24/24 | 8 |
| SplaTAM | 24/24 | PSNR 24/24 | 24/24 | 8 |
| WildGS-SLAM | 24/24 | PSNR 24/24 | 24/24 | 8 |

## 3. 序列集对齐（BONN，本文 stack vs 复现套件）

- 复现套件 BONN 序列（缩写）：balloon, balloon2, crowd, crowd2, mv_no_box, mv_no_box2, person_t, person_t2
- 映射到本仓全名：balloon, balloon2, crowd, crowd2, mvnobox, mvnobox2, person_tracking, person_tracking2
- **本文 stack 的 BONN 七序列**：balloon, balloon2, crowd, crowd2, crowd3, person_tracking, person_tracking2
- **交集（可同表对比）**：balloon, balloon2, crowd, crowd2, person_tracking, person_tracking2  → 共 6 条
- 仅基线有（本文 stack 无 run）：mvnobox, mvnobox2
- 仅本文有（基线无，如 crowd3）：crowd3

## 4. 指标缺口（BONN）

| 方法 | ATE | PSNR/SSIM/LPIPS | Depth-L1 | Accuracy | FPS | GPU | #Gaussians |
|---|---|---|---|---|---|---|---|
| Co-SLAM | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| DG-SLAM | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| DynaGSLAM | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| DynaSLAM | ✓ | — | — | — | ✓ | — | — |
| MonoGS | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| NGD-SLAM | ✓ | — | — | — | ✓ | — | — |
| ORB_SLAM3 | ✓ | — | — | — | ✓ | — | — |
| RGD-SLAM | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| RoDyn-SLAM | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| SplaTAM | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WildGS-SLAM | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

> 非 3DGS 方法（ORB_SLAM3/DynaSLAM/NGD-SLAM/RoDyn-SLAM 部分列）无 mapping/GPU/Gaussians 字段，属 N/A（方法不支持）。

## 5. 口径提醒（入表前必须处理）

1. **序列集不一致**：基线含 `mv_no_box/mv_no_box2`（本文 stack 无 run），本文含 `crowd3`（基线无）。可同表对比的公共集见 §3。
2. **mask 口径**：基线 mapping 全图（`mask_type=full`，`mask_source=flow_motion_precomputed`）；本文 stack 渲染另有 static/dynamic 分区口径 —— 跨口径禁混引。
3. **对齐**：baseline 统一 Horn SE(3)（`03-metrics_checklist.md`）；本文 stack 亦 SE(3)。单目方法若需 Sim(3) 须单独声明（不混入主表）。
4. **静态方法在动态 BONN 上 tracking 崩**（如 Co-SLAM/SplaTAM 的 ATE 可达 10²–10⁴ cm）——如实呈现，不裁剪；这本身是反动态范式的动机证据。
5. **DynaGSLAM 跟踪外包 + 确定性（2026-10-11 补登）**：DynaGSLAM 的定位是「模块级分离」——建图自洽、**跟踪交由外部 DynoSAM 前端**（mapping_raw.csv `pose_source` 列 = `/data/DynOSAM/output/dynamic/.../frontend_camera_poses_tum.txt`，`external_pose_match_mode=interpolate`；机制见 `resources/lit_dyn_mapping/mechanisms.md` C6 行）。外部位姿固定 ⇒ 其 3 seed ATE **逐位相同**（std=0），按「3 次结果完全一致则 std 为 0」条款（`03-metrics_checklist.md`）以单值呈现。**表内与自跟踪方法并排时须在题注注明**（tab_baseline caption 已含 "DynaGSLAM delegates tracking to an external front-end ... reported without variance"）。
