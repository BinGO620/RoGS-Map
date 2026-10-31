## Metrics Checklist

本文件用于规范 baseline 复现实验的指标统计、结果表字段和 raw 数据保存方式。整体结构分为四张主要维护的 Excel 表和三类 raw CSV：

- 一张主表 Excel：汇总 tracking、mapping、efficiency 三张分表中最核心、最通用的指标。
- 三张分表 Excel：分别维护 tracking、mapping、efficiency 的通用指标。
- 三类 raw CSV：分别保存 tracking、mapping、efficiency 的逐次运行结果和方法自带的额外指标。

原则是：Excel 表只放通用、可比、大家一眼能理解的字段；各个方法自带的特殊指标放入对应 raw CSV，不强行进入主表或分表。

### 1. Result Files

| File | Format | Purpose |
|:---|:---:|:---|
| `main_results.xlsx` | Excel | 主表，从三张分表中抽取核心指标形成总览 |
| `tracking_results.xlsx` | Excel | tracking 分表，维护通用轨迹指标 |
| `mapping_results.xlsx` | Excel | mapping 分表，维护通用渲染和几何指标 |
| `efficiency_results.xlsx` | Excel | efficiency 分表，维护通用效率和资源指标 |
| `tracking_raw.csv` | CSV | tracking 逐次运行数据和方法自带 tracking 指标 |
| `mapping_raw.csv` | CSV | mapping 逐次运行数据和方法自带 mapping 指标 |
| `efficiency_raw.csv` | CSV | efficiency 逐次运行数据和方法自带 efficiency 指标 |

四张 Excel 表之间的关系：

- `tracking_results.xlsx`、`mapping_results.xlsx`、`efficiency_results.xlsx` 是主要维护的三张分表。
- `main_results.xlsx` 是三张分表的汇集，只选取最核心的指标用于整体比较。
- 三张分表的数据都应能追溯到对应 raw CSV。

### 2. Main Table

主表字段保持简洁，用于快速比较各方法在每个序列上的 tracking、mapping 和 efficiency 综合表现。

| Method | Dataset | Sequence | ATE (cm) | PSNR | SSIM | LPIPS | Depth L1 (cm) | FPS | GPU (GB) |
|:---|:---|:---|---:|---:|---:|---:|---:|---:|---:|
| method_name | dataset_name | sequence_name | mean ± std | mean ± std | mean ± std | mean ± std | mean ± std | mean ± std | mean ± std |

说明：
- `ATE (cm)` 来自 tracking 分表，默认使用所有帧 ATE RMSE。
- `PSNR`、`SSIM`、`LPIPS`、`Depth L1 (cm)` 来自 mapping 分表。
- `FPS`、`GPU (GB)` 来自 efficiency 分表，`GPU (GB)` 默认使用 peak GPU memory。
- 每个数值默认由 3 次重复实验统计得到，格式为 `mean ± std`。

### 3. Tracking Table

Tracking 分表维护轨迹估计相关的通用指标。

| Method | Dataset | Sequence | ATE RMSE (cm) | ATE Error STD (cm) | RPE Trans. RMSE (cm) | Path Length Ratio (%) | Keyframe ATE (cm) |
|:---|:---|:---|---:|---:|---:|---:|---:|
| method_name | dataset_name | sequence_name | mean ± std | mean ± std | mean ± std | mean ± std | mean ± std |

字段说明：
- `ATE RMSE (cm)`：绝对轨迹误差的均方根误差，tracking 主指标。
- `ATE Error STD (cm)`：同一次运行内 ATE 逐帧误差的标准差，用于反映轨迹误差稳定性；不要和多次重复实验的 `mean ± std` 混淆。
- `RPE Trans. RMSE (cm)`：相对位姿误差中的平移 RMSE，用于衡量局部运动估计质量。
- `Path Length Ratio (%)`：估计轨迹累计路径长度 / 真值轨迹累计路径长度，用于反映轨迹是否完整。该字段不是 success rate，可能因为漂移或抖动超过 100%。
- `Keyframe ATE (cm)`：只在关键帧上计算的 ATE。

评估方式：
- 使用 `evo` 将估计轨迹与真值轨迹对齐后计算 ATE / RPE。
- ATE 计算前必须统一轨迹对齐方法，默认使用 `evo` 的 Horn's Procrustes alignment。
- 默认计算所有帧的对齐误差；关键帧 ATE 作为 tracking 分表字段和 raw 字段保存。
- 默认将单位从 `m` 转为 `cm`，小数点后保留 4 位。
- `Path Length Ratio (%)` 按时间戳匹配后的轨迹计算，默认不做尺度校正；如果某方法必须做尺度校正，需要在 raw 的 `notes` 中注明。
- `Success Rate` 不作为逐序列表字段。如果需要报告成功率，应在跨序列或跨运行汇总时由 raw 中的 `success_by_threshold` 聚合得到，例如 `成功运行数 / 总运行数`。

### 4. Mapping Table

Mapping 分表维护渲染质量和几何重建相关的通用指标。

| Method | Dataset | Sequence | PSNR | SSIM | LPIPS | Depth L1 (cm) | Accuracy (cm) |
|:---|:---|:---|---:|---:|---:|---:|---:|
| method_name | dataset_name | sequence_name | mean ± std | mean ± std | mean ± std | mean ± std | mean ± std |

字段说明：
- `PSNR`：渲染 RGB 图像与真值 RGB 图像的峰值信噪比。
- `SSIM`：渲染 RGB 图像与真值 RGB 图像的结构相似度。
- `LPIPS`：渲染 RGB 图像与真值 RGB 图像的感知距离。
- `Depth L1 (cm)`：渲染深度图与真值深度图的 L1 误差。
- `Accuracy (cm)`：重建点云到真值点云的平均距离。该指标是一侧几何误差；如果某个方法还报告 completeness、F-score 等几何指标，放入 mapping raw CSV。

评估方式：
- 沿估计轨迹渲染全分辨率 RGB 图像和深度图，并与真值对比。
- 渲染指标必须在全分辨率下计算，不使用下采样结果。
- 如果几何指标原始单位是 `m`，统一转为 `cm`。
- 动态场景需要明确 mask 使用方式：不剔除动态像素、剔除动态像素，或分别统计 static / dynamic 区域。默认表格字段使用全图指标；区域指标保存到 mapping raw CSV 中。

### 5. Efficiency Table

Efficiency 分表维护运行速度、耗时和资源占用相关的通用指标。

| Method | Dataset | Sequence | FPS | Tracking FPS | Mapping FPS | Tracking Time (ms) | Mapping Time (ms) | GPU (GB) | #Gaussians |
|:---|:---|:---|---:|---:|---:|---:|---:|---:|---:|
| method_name | dataset_name | sequence_name | mean ± std | mean ± std | mean ± std | mean ± std | mean ± std | mean ± std | mean ± std |

字段说明：
- `FPS`：end-to-end 处理速度，主表默认使用该字段。
- `Tracking FPS`：tracking 模块处理速度。
- `Mapping FPS`：mapping / optimization 模块处理速度。
- `Tracking Time (ms)`：每帧 tracking 耗时。
- `Mapping Time (ms)`：每帧 mapping / Gaussian optimization 耗时。
- `GPU (GB)`：显存占用，优先记录 peak memory。
- `#Gaussians`：场景中的 Gaussian 数量，影响渲染质量、显存和速度。

说明：
- 如果方法无法拆分 tracking / mapping 时间，只记录 `FPS`，对应拆分字段可记为 `N/A`。
- 3DGS 方法需要尽量保存 `#Gaussians`；非 3DGS 方法可记为 `N/A`。

### 6. Raw CSV Requirements

三类 raw CSV 保存逐次运行数据，是四张 Excel 表的来源。每个 raw 文件都应至少包含以下公共字段：

| Field | Meaning |
|:---|:---|
| method | 方法名称 |
| dataset | 数据集名称，例如 `TUM` / `BONN` |
| sequence | 序列简称，例如 `f3_wk_xyz` / `crowd` |
| seed | 随机种子，默认 `0`, `1`, `2` |
| run_id | 同一设置下的运行编号 |
| status | `OK` / `N/A` / `FAIL` / `MISSING` |
| notes | 备注，例如失败原因、mask 设置或特殊配置 |

#### 6.1 Tracking Raw

| Field | Meaning |
|:---|:---|
| ate_rmse_cm | 所有帧 ATE RMSE |
| ate_error_std_cm | 同一次运行内所有帧 ATE error STD |
| rpe_trans_rmse_cm | RPE translation RMSE |
| path_length_ratio | 估计轨迹累计路径长度 / 真值轨迹累计路径长度 |
| success_by_threshold | 是否满足预设成功阈值，用于跨序列或跨运行聚合 success rate |
| success_threshold_cm | 成功阈值 |
| keyframe_ate_rmse_cm | 关键帧 ATE RMSE |

#### 6.2 Mapping Raw

| Field | Meaning |
|:---|:---|
| psnr | RGB rendering PSNR |
| ssim | RGB rendering SSIM |
| lpips | RGB rendering LPIPS |
| depth_l1_cm | Depth L1 |
| accuracy_cm | 点云 accuracy |
| mask_type | `full` / `static` / `dynamic` / other |

#### 6.3 Efficiency Raw

| Field | Meaning |
|:---|:---|
| fps_end_to_end | 端到端 FPS |
| tracking_fps | tracking FPS |
| mapping_fps | mapping FPS |
| tracking_time_ms | 每帧 tracking 耗时 |
| mapping_time_ms | 每帧 mapping / optimization 耗时 |
| gpu_memory_gb | peak GPU memory |
| num_gaussians | Gaussian 数量 |

方法自带的额外指标可以放在对应 raw CSV 中，但不要进入主表或三张分表。命名建议使用 `method_raw_*` 前缀，或者在 `notes` 中说明字段来源。

### 7. Repetition and Statistics

- 默认每个方法、每个序列重复 3 次实验。
- 默认随机种子为 `0`, `1`, `2`。
- Excel 表报告 `mean ± std`。
- 因为只有 3 次重复实验，标准差使用样本标准差，即 `ddof=1`，分母为 `n - 1`。
- 如果某个方法本身没有随机性，也仍然优先重复 3 次；如果 3 次结果完全一致，std 为 0。

### 8. Failure and Missing Values

| Status | Meaning | Handling |
|:---|:---|:---|
| `OK` | 实验正常完成，指标可计算 | 进入统计 |
| `N/A` | 该方法确实不支持或不强制报告该指标 | 不补跑，表中可记为 `N/A` |
| `FAIL` | 方法在该序列上失败，导致相关指标无法计算 | 保留失败记录，不用成功结果替换 |
| `MISSING` | 理论上应该有结果，但当前缺失 | 需要检查是否漏跑，并生成补跑任务 |

说明：
- 静态方法在动态数据集上可能 tracking 失败，这类情况记为 `FAIL`。
- 如果 tracking 失败，依赖轨迹的 mapping 和 efficiency 指标通常也记为 `FAIL`。
- `N/A` 和 `FAIL` 不应混用：`N/A` 表示方法或论文设定中没有该指标，`FAIL` 表示实验运行失败或无法得到有效结果。

### 9. Reproducibility Notes

- 数据集序列必须与原文保持一致，例如 TUM 的 `f3_wk_xyz`、BONN 的 `crowd` 等。
- ATE / RPE 的时间戳匹配、轨迹对齐和单位转换必须统一。
- 渲染指标使用全分辨率 RGB-D 数据计算。
- 动态场景需要记录是否使用动态 mask，以及 mask 的计算来源。
- 主表、三张分表和三类 raw CSV 的数值必须能互相追溯。
