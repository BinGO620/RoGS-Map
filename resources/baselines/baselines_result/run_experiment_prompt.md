## Prompt for Rerunning Baseline Experiments

使用前，把以下三个规范文件放到对应 baseline 项目中，智能体会自动读取：

- `01-baselines_method.md`
- `02-datasets_sequence.md`
- `03-metrics_checklist.md`

---

你是一个负责检查、重跑和全量产出 SLAM baseline 实验结果的智能体。当前目录是某个 baseline 项目的代码仓库，项目中已经放入了以下三个规范文件：

- `01-baselines_method.md`
- `02-datasets_sequence.md`
- `03-metrics_checklist.md`

你的任务是自动读取这三个文件，按照其中的规范检查当前项目已有实验结果。如果现有结果不足以稳定生成四张 Excel 表的全部字段，需要写批量脚本、修改必要的评估代码或补充日志统计，并尽量一次性重跑或复算完整实验。最终必须得到规范的 raw CSV 和 Excel 结果表。默认不要删除已有结果；如需清理占用空间大的中间结果，必须先确认它们不再用于追溯，并在最终报告中说明。

### 1. 首先自动读取规范文件

开始任何检查、实验、脚本编写或代码修改前，必须先在当前项目中查找并完整阅读：

1. `01-baselines_method.md`
2. `02-datasets_sequence.md`
3. `03-metrics_checklist.md`

如果这三个文件不在当前目录根部，先在项目内搜索同名文件。  
如果仍然找不到，停止并报告缺失文件，不要凭记忆继续。

不要重新设计指标体系。数据集序列、字段、单位、统计方式、状态标记，都以这三个文件为准。

### 2. 直接检查并全量产出当前项目结果

当前项目对应的方法已经由用户分配好，不需要再判断项目属于哪个 baseline，也不需要处理 `01-baselines_method.md` 中列出的其他方法。

只需要围绕当前项目完成下面的事：

- 检查当前已有实验结果。
- 以四张 Excel 表中的规定字段为最低目标，能计算的必须尽量计算完整。
- 对确实无法计算的字段，不要强求，不要伪造；必须用 `N/A`、`FAIL` 或 `MISSING` 标清原因。
- 对已有输出能计算的指标，直接计算并写入对应 raw CSV。
- 如果决定重跑或复算，不要只补单个缺失字段；应尽量一次性计算完整的 tracking、mapping、efficiency 指标，避免后续再次补实验。
- 对当前项目自带且有分析价值的额外指标，保存到对应 raw CSV，不要加入四张 Excel 主字段。
- 如果现有脚本不能稳定产出完整字段，写批量脚本、补评估代码或补日志统计。
- 必要时按 seed `0`、`1`、`2` 重跑当前项目实验，并在同一次流程中生成全部可计算指标。
- 最终生成或更新三类 raw CSV、三张分表 Excel 和一张主表 Excel。
- 当需要重跑实验时，可以检查 `conda env list`，通常项目已有对应环境配置。

### 3. 需要维护的结果文件

按照 `03-metrics_checklist.md`，最终需要检查、生成或更新：

- `main_results.xlsx`
- `tracking_results.xlsx`
- `mapping_results.xlsx`
- `efficiency_results.xlsx`
- `tracking_raw.csv`
- `mapping_raw.csv`
- `efficiency_raw.csv`

关系如下：

- 三类 raw CSV 保存逐次运行结果。
- 三张分表 Excel 从对应 raw CSV 聚合得到。
- 主表 Excel 从 tracking、mapping、efficiency 三张分表抽取核心指标汇总得到。
- 任何主表或分表里的数值，都必须能追溯回 raw CSV。

### 4. 检查当前已有结果

对当前项目、`02-datasets_sequence.md` 中要求的数据集序列、以及 seed `0`、`1`、`2`，检查是否已有：

- 估计轨迹
- 真值轨迹
- 渲染 RGB 图像
- 渲染深度图
- 重建点云
- tracking 日志
- mapping 日志
- FPS / 耗时记录
- GPU 显存记录
- Gaussian 数量记录

然后判断已有结果是否足够生成四张 Excel 表要求的全部字段：

- tracking 指标
- mapping 指标
- efficiency 指标

如果已有结果足够，直接计算并写入对应 raw CSV。  
如果已有结果不够，不要只补当前看见的单个缺口；应制定一次性补齐方案，尽量通过重跑或批量复算同时得到 tracking、mapping、efficiency 的完整指标。  
确实无法计算的字段，不要强行构造结果，必须判断是 `N/A`、`FAIL` 还是 `MISSING`，并在 raw CSV 的 `notes` 中写明原因。

### 5. Tracking 指标

Tracking 分表和 `tracking_raw.csv` 的字段以 `03-metrics_checklist.md` 为准，重点包括：

- `ATE RMSE (cm)`
- `ATE Error STD (cm)`
- `RPE Trans. RMSE (cm)`
- `Path Length Ratio (%)`
- `Keyframe ATE (cm)`

要求：

- 使用 `evo` 或等价工具计算 ATE / RPE。
- ATE 计算前统一轨迹对齐方法，默认使用 Horn's Procrustes alignment。
- 单位统一从 `m` 转为 `cm`。
- 默认保留小数点后 4 位。
- `Path Length Ratio (%)` 是估计轨迹累计路径长度 / 真值轨迹累计路径长度，不是 success rate。
- `Success Rate` 不作为单个序列字段，只能从 raw 中的 `success_by_threshold` 跨序列或跨运行聚合得到。

`Path Length Ratio (%)` 的计算方式为：

$$
\mathrm{Path\ Length\ Ratio} =
\frac{\sum_{i=1}^{N-1} \lVert \hat{\mathbf{t}}_{i+1} - \hat{\mathbf{t}}_i \rVert_2}
{\sum_{i=1}^{N-1} \lVert \mathbf{t}_{i+1} - \mathbf{t}_i \rVert_2}
\times 100
$$

其中，$\hat{\mathbf{t}}_i$ 是估计轨迹第 $i$ 帧的平移，$\mathbf{t}_i$ 是真值轨迹第 $i$ 帧的平移。

如果 tracking 指标不完整：

- 优先检查项目是否已有轨迹评估脚本。
- 如果已有脚本但字段不全，修改或包一层脚本导出规范 CSV。
- 如果需要重跑 tracking，尽量同时保存后续 mapping / efficiency 会用到的轨迹、关键帧、日志和时间统计。
- 如果没有脚本，新增批量 tracking 评估脚本。

### 6. Mapping 指标

Mapping 分表和 `mapping_raw.csv` 的字段以 `03-metrics_checklist.md` 为准，重点包括：

- `PSNR`
- `SSIM`
- `LPIPS`
- `Depth L1 (cm)`
- `Accuracy (cm)`

要求：

- 沿估计轨迹渲染全分辨率 RGB 图像和深度图。
- RGB 指标与真值 RGB 图像比较。
- Depth L1 与真值深度图比较，单位统一为 `cm`。
- `Accuracy (cm)` 是重建点云到真值点云的平均最近邻距离。
- 动态场景必须记录 mask 使用方式，例如 `full`、`static`、`dynamic`。
- 方法自带且有分析价值的特殊 mapping 指标放入 `mapping_raw.csv`，不要加进 mapping 分表。

`Depth L1 (cm)` 的计算方式为：

$$
\mathrm{Depth\ L1} =
\frac{1}{|\Omega|}
\sum_{\mathbf{u} \in \Omega}
\left| D_{\mathrm{pred}}(\mathbf{u}) - D_{\mathrm{gt}}(\mathbf{u}) \right|
\times 100
$$

其中，$\Omega$ 是有效深度像素集合，深度单位默认为 `m`，最终结果转换为 `cm`。

如果 mapping 指标不完整：

- 优先复用项目已有 renderer / evaluation 脚本。
- 如果已有脚本但不能批量处理，写批量 wrapper。
- 如果字段不全，修改评估输出，保证能写入 `mapping_raw.csv`。
- 如果需要重新渲染，尽量一次性保存 RGB、depth、mask、点云或中间结果，避免之后为了单个指标再次渲染。

### 7. 点云 Accuracy / Completion 评估

`Accuracy (cm)` 是 mapping 主字段之一，必须优先尝试计算。若当前数据集没有官方真值点云，需要使用可追溯的替代真值点云生成方式，并在 raw CSV 的 `notes` 中写清楚。

设重建点云为 $P_{\mathrm{rec}}$，真值点云为 $P_{\mathrm{gt}}$。从两者中各随机采样 $200{,}000$ 个点后，按 3DG SLAM 论文的评估方式计算：

$$
\mathrm{Accuracy} =
\frac{1}{|P_{\mathrm{rec}}|}
\sum_{\mathbf{p} \in P_{\mathrm{rec}}}
\min_{\mathbf{q} \in P_{\mathrm{gt}}}
\lVert \mathbf{p} - \mathbf{q} \rVert_2
\times 100
$$

$$
\mathrm{Completion} =
\frac{1}{|P_{\mathrm{gt}}|}
\sum_{\mathbf{q} \in P_{\mathrm{gt}}}
\min_{\mathbf{p} \in P_{\mathrm{rec}}}
\lVert \mathbf{q} - \mathbf{p} \rVert_2
\times 100
$$

$$
\mathrm{Completion\ Ratio} =
\frac{1}{|P_{\mathrm{gt}}|}
\sum_{\mathbf{q} \in P_{\mathrm{gt}}}
\mathbb{1}
\left[
\min_{\mathbf{p} \in P_{\mathrm{rec}}}
\lVert \mathbf{q} - \mathbf{p} \rVert_2
\le 0.05
\right]
\times 100
$$

其中，点云坐标单位默认为 `m`；`Accuracy` 和 `Completion` 最终转换为 `cm`；`Completion Ratio` 的距离阈值为 `5 cm`。

#### 7.1 TUM 数据集

TUM RGB-D 数据集没有官方真值点云。可以使用融合 GT 的方式补出可追溯的 `Accuracy (cm)`：

- 使用 TUM 的真值位姿和真值深度图融合得到 GT 点云。
- 融合时记录使用的序列、帧范围、深度尺度、相机内参、深度截断阈值、体素大小或采样策略。
- 将重建点云与融合得到的 GT 点云放在同一坐标系中评估 `Accuracy`。
- 在 `mapping_raw.csv` 的 `notes` 中明确写明：`TUM has no official GT point cloud; GT point cloud is fused from GT poses and GT depth.`

如果项目无法可靠融合 GT 点云，`Accuracy (cm)` 记为 `MISSING`，并说明缺少的输入或工具。不要用渲染深度直接替代点云 Accuracy。

#### 7.2 BONN 数据集

BONN 数据集有官方 GT 点云，文件已放在数据集根目录下：

- `rgbd_bonn_groundtruth_1mm_section.ply`

BONN 有 24 个动态序列和 2 个静态序列，所有序列在同一个房间采集，并共享同一个 GT 点云。每个序列都有自己的 `groundtruth.txt`，因此每个序列都需要单独计算对齐变换。

BONN 数据集目录结构示例：

```text
BONN/
├── rgbd_bonn_balloon/
│   ├── rgb/
│   ├── depth/
│   ├── groundtruth.txt
│   └── ...
├── rgbd_bonn_balloon2/
│   ├── groundtruth.txt
│   └── ...
├── ...
└── rgbd_bonn_groundtruth_1mm_section.ply
```

GT 点云信息：

- 文件名：`rgbd_bonn_groundtruth_1mm_section.ply`
- 格式：PLY ASCII
- 点数：54,676,774，降采样版
- 采集设备：Leica BLK360 地面激光扫描仪
- 坐标系：激光扫描仪坐标系，与 RGB-D 传感器坐标系不同

必须把重建结果从 RGB-D 传感器坐标系变换到 GT 点云坐标系：

$$
T_g = T_{\mathrm{ROS}}^{-1} T_0 T_{\mathrm{ROS}} T_m
$$

其中，$T_m$ 是从 RGB-D 传感器坐标系到动捕标记点坐标系的固定变换：

$$
T_m =
\begin{bmatrix}
1.0157 & 0.1828 & -0.2389 & 0.0113 \\
0.0009 & -0.8431 & -0.6413 & -0.0098 \\
-0.3009 & 0.6147 & -0.8085 & 0.0111 \\
0.0 & 0.0 & 0.0 & 1.0
\end{bmatrix}
$$

$T_{\mathrm{ROS}}$ 是固定的 ROS 坐标系修正矩阵：

$$
T_{\mathrm{ROS}} =
\begin{bmatrix}
-1 & 0 & 0 & 0 \\
0 & 0 & 1 & 0 \\
0 & 1 & 0 & 0 \\
0 & 0 & 0 & 1
\end{bmatrix}
$$

$T_0$ 是每个序列不同的第一帧 GT 位姿矩阵，需要从该序列 `groundtruth.txt` 的第一行读取并构造为 $4 \times 4$ 齐次变换矩阵。

每个 BONN 序列的对齐和评估步骤：

1. 读取该序列的 `groundtruth.txt` 第一行。
2. 提取第一帧位姿，构造 $T_0$。
3. 计算 $T_g = T_{\mathrm{ROS}}^{-1} T_0 T_{\mathrm{ROS}} T_m$。
4. 使用 $T_g$ 将该序列的重建点云或 Gaussian 点云变换到 GT 点云坐标系。
5. 与 `rgbd_bonn_groundtruth_1mm_section.ply` 计算 `Accuracy (cm)`、`Completion (cm)` 和 `Completion Ratio (%)`。

给智能体的关键指令：

- 所有 BONN 序列共享同一个 GT 点云。
- 每个序列必须单独计算 $T_g$，不要复用其他序列的 $T_0$。
- 从 GT 点云和重建点云中各采样 $200{,}000$ 个点。
- `Accuracy (cm)` 写入 mapping 分表和 `mapping_raw.csv`。
- `Completion (cm)` 和 `Completion Ratio (%)` 如果不属于四张 Excel 主字段，只保存到 `mapping_raw.csv` 作为额外指标。
- 在 `notes` 中记录 GT 点云文件、对齐公式、采样点数和阈值。

### 8. Efficiency 指标

Efficiency 分表和 `efficiency_raw.csv` 的字段以 `03-metrics_checklist.md` 为准，重点包括：

- `FPS`
- `Tracking FPS`
- `Mapping FPS`
- `Tracking Time (ms)`
- `Mapping Time (ms)`
- `GPU (GB)`
- `#Gaussians`

要求：

- `FPS` 默认是 end-to-end FPS。
- 如果方法无法拆分 tracking / mapping FPS，对应字段记为 `N/A`。
- `GPU (GB)` 优先记录 peak GPU memory。
- 3DGS 方法尽量记录 `#Gaussians`。
- 非 3DGS 方法的 `#Gaussians` 可以记为 `N/A`。

如果 efficiency 指标不完整：

- 先检查已有日志。
- 如果日志不够，新增轻量 logging 或 wrapper 脚本。
- 如果需要重跑，尽量在同一次运行中记录 FPS、tracking / mapping time、peak GPU memory 和 Gaussian 数量。
- 不要为了 efficiency 指标大改算法核心逻辑。

### 9. 重复实验和聚合

默认每个方法、每个序列重复 3 次：

- seed `0`
- seed `1`
- seed `2`

Excel 表报告：

$$
\mathrm{mean} \pm \mathrm{std}
$$

标准差使用样本标准差：

$$
\mathrm{std} =
\sqrt{
\frac{1}{n - 1}
\sum_{i=1}^{n}
\left(x_i - \bar{x}\right)^2
}
$$

其中，$n$ 是有效重复次数，默认应为 3。若方法本身没有随机性，也优先重复 3 次；如果三次结果完全一致，`std` 为 0。

### 10. 状态标记

raw CSV 中必须保留状态字段 `status`：

- `OK`：实验正常完成，指标可计算。
- `N/A`：该方法确实不支持或不强制报告该指标，不需要补跑。
- `FAIL`：方法在该序列上失败，导致相关指标无法计算，必须保留失败记录。
- `MISSING`：理论上应该有结果，但当前缺失，需要生成补跑任务。

注意：

- 静态方法在动态数据集上失败，可以记为 `FAIL`。
- 如果 tracking 失败，依赖轨迹的 mapping 和 efficiency 指标通常也记为 `FAIL`。
- 不要把 `N/A` 和 `FAIL` 混用。
- 不要删除失败记录。
- 不要伪造缺失指标。
- 不要为了得到某个指标而强行修改算法核心逻辑或使用不一致的评估定义。

### 11. 需要写脚本时

如果发现四张 Excel 表所需字段不能完整生成，需要写批量脚本。脚本目标不是只补一个字段，而是尽量一次性产出完整 raw CSV。脚本必须做到：

- 批量处理 `02-datasets_sequence.md` 中列出的序列。
- 按 seed `0`、`1`、`2` 组织结果。
- 输出结构化 CSV，不要只打印终端日志。
- 保存 `method`、`dataset`、`sequence`、`seed`、`run_id`、`status`、`notes`。
- 运行失败时也写入 `FAIL` 或 `MISSING` 记录。
- 不覆盖已有有效结果，除非明确是在复算同一实验设置。
- 保留或说明原始日志来源。
- 自动保存当前项目自带且有分析价值的额外指标到对应 raw CSV。

优先新增这些脚本：

- `scripts/eval_tracking_batch.*`
- `scripts/eval_mapping_batch.*`
- `scripts/eval_efficiency_batch.*`
- `scripts/aggregate_results.*`

脚本语言按项目习惯选择，优先使用项目已有 Python / Bash 工具链。

### 12. 允许和禁止

允许：

- 新增评估脚本。
- 新增聚合脚本。
- 小范围修改日志输出，使其包含耗时、显存、Gaussian 数量等指标。
- 小范围修改 evaluation 代码，使其输出规范字段。
- 在不改变算法核心逻辑的前提下，补充可追溯的评估输入，例如 TUM 融合 GT 点云。

禁止：

- 为了刷指标修改算法核心逻辑。
- 改动 tracking / mapping 默认行为但不说明。
- 未经用户明确许可删除已有结果。
- 手工填数代替计算。
- 伪造缺失指标。

所有代码修改都要在最终报告中说明。

### 13. 最终报告

完成后给出简短报告，必须包含：

- 当前项目已完成的数据集和序列。
- 已生成或更新的文件路径。
- 哪些字段已经完整生成，是否满足四张 Excel 表的最低要求。
- 哪些指标由已有结果计算得到。
- 哪些指标通过重跑、批量复算或新增脚本得到。
- 哪些项目自带的额外指标被保存到了 raw CSV。
- 哪些结果是 `N/A`、`FAIL`、`MISSING`。
- 如果还有 `MISSING`，列出需要补跑的具体方法、数据集、序列、seed 和原因。
- 如果修改了代码，列出修改文件和修改目的。

最终目标：任何人都可以从三类 raw CSV 追溯到三张分表，再从三张分表追溯到主表。
