# learned 压缩器基线可行性调研（R4-P3 / 门槛 3）— 冻结-PLY 后处理通路核查（2026-10-15）

> **背景**：R4 独立审稿（`papers/paper2/CVM_REVIEW_v8.4_2026-10-15.md`）判 Reject，P3（压缩无同类基线）是四条 Major 之一，门槛 3 是六门槛中**唯一未满足项**。门槛 3 原文（报告 L142）：
> "补一个同类压缩基线。在 Table 4 中加入 HAC、Compact3DGS 或 TC3DGS/MEGA 中**至少一个**，跑在同一批冻结地图、同一评测集、同一指标上；报告**等 PSNR 下的比值**或**等比值下的 PSNR**。若需适配（如重训 entropy model），写明适配方式并照报数字。门槛 = 6×/15× 必须与至少一个 learned 压缩器同场出现且仍成立。"
> **本调研性质**：零 GPU、零训练；全部结论来自**官方代码/README 逐行核查** + 仓内工件盘点（2026-10-15）。
> **口径锚点**（与 Table 4 同源，prereg §4.0）：同一批冻结地图（L2 42 张 + L3 36 张 = 78 张）、同一渲染仪器（`render_compare.py` 固定帧集）、同一分母（`n*20*4` 源字节）。

## 0. 结论摘要（TL;DR）

1. **门槛 3 点名的四个方法，没有一个能直接作用于冻结地图**：
   - **TC3DGS / MEGA**：压缩对象是**动态(4D)表示**（时序剪枝 / 轨迹插值 / 4D 训练框架），与"单时刻 3DGS 冻结地图"结构性不匹配；且 TC3DGS 代码**未发布**（官方仓仅 1 commit + README "The code will be released soon"）。
   - **HAC/HAC++**：训练期方法（已登记于 `evidence/posthoc_baselines_2026-10-09.md §排除项`，本轮复核维持）。
   - **Compact3DGS**：**无冻结-PLY 入口**——其压缩产物（learnable mask / R-VQ 码本 / hash 神经场）全部是**其训练循环的产物**；唯一忠实适配 = 以冻结地图为初始化的重训（研究级改造，见 §2.2）。
2. **真正现成可跑的"同类 learned 压缩器"存在，且本稿 §2 已引用**：**SOG**（Morgenstern et al., ECCV'24, bib key `SOG`）。官方代码明确支持压缩**未排序**高斯（`train.py` L202–206 注释原文 "enable compression of non-sorted gaussians without affecting results"），压缩/解压为独立函数、解压输出标准 PLY——可绕开其渲染评测，纯做"压缩 → 解压 → 我们渲染"。压缩本身零 GPU（CPU + torch 张量操作）。
3. **推荐**：先跑 SOG（全 78 张、2–3 个码率点，2–3 天、低风险），把 §5 的"不比较"句（tex L409–417）改为**量化对照**；Compact3DGS 重训适配（+4–7 天、中高风险）作为"字面满足点名清单"的加强项，按时间线取舍（§3）。

## 1. 事实基础

| 项 | 事实 | 来源 |
|---|---|---|
| 冻结地图集 | L2 = 7 序列 × 2 臂 × 3 seed = 42 张；L3（held-out）= 6 序列 × 2 臂 × 3 seed = 36 张 | `evidence/rd/L{2,3}_*_rd_table.json`（78/78 在库） |
| 地图规模 | 基元 24,737–221,845（中位 57,226；合计 5.27M）；PLY 1.98–17.75 MB（合计 0.42 GB） | 本轮逐图实测（PLY header + 文件大小） |
| 字段构成 | 20 字段 f32 = **14 渲染字段**（xyz / f_dc×3 / opacity / scale×3 / rot×4）+ **6 记账字段**（nx,ny,nz + static_prob, static_obs_count, unmapped_score = 24 B/基元 = 30%） | `scripts/gs_compress/posthoc_baselines.py FIELDS`；与论文 §4 的 24B/30% 对位 |
| 分母口径 | `n*20*4` 源字节；ratio = 分母/码流字节；对照同码率 ±2%；rate = 压缩码流字节/基元 | prereg §4.0 / `results/gs_compress/README.md` |
| 渲染仪器 | `render_compare.py` 固定帧集（0,60,120,180,240）；掩码 = canonical 冻结 `dynamic_mask/` | `results/gs_compress/README.md` |
| Table 4 现结构 | 4 组：source+无损带 / 通用有损（rate-only）/ 本文 codec 三点 / voxel 消融 | `papers/paper2/tables/tab_rd.tex` |
| §5 现状句 | "We do not compare against learned 3DGS compressors such as HAC [5] or Compact3D [12]: they act on trained static or 4D models…"（整段 L409–417） | `papers/paper2/paper2_cvm.tex` |

## 2. 逐候选核查

### 2.1 SOG（Morgenstern et al., ECCV 2024）— ✅ 可行（推荐）

**代码证据**（fraunhoferhhi/Self-Organizing-Gaussians，graphdeco fork）：
- `train.py` L202–206：`# enable compression of non-sorted gaussians without affecting results` + `gaussians_to_compress = deepcopy(gaussians)` + `.prune_to_square_shape()` ⇒ **非排序输入是官方支持的路径**（其排序/正则训练只影响压缩率，不是压缩的前提）。
- `compression/compression_exp.py`：`run_single_compression`（L166）/ `run_compressions`（L193）/ `run_single_decompression`（L210）为**独立函数**，不依赖渲染；`run_experiments` 里的渲染评测（PSNR/SSIM/LPIPS）可整体绕过——我们只用其压缩+解压。
- `compression/decompress.py`：解压输出 `decompressed_model/point_cloud/iteration_1/point_cloud.ply`（标准 PLY，可进我们的 rd-harness recon 布局）。
- `config/compression/umbrella.yaml`：多档码率配置（`jxl_101` 近无损 / `jxl_quant` 量化 14/6/6/6/6 位 / `png_16` / `exr…`），**每个配置都注释掉了 `_features_rest`** ⇒ 无 SH-rest（DC-only）是其标准用法——我们的地图恰好 DC-only。
- 压缩 = PLAS 排序 + 网格化 + JPEG-XL/EXR/PNG 逐属性编码；`quantize`/`normalize` 为码率旋钮。压缩尺寸 = 压缩目录文件字节和（其 `get_size_of_files_in_dir` 惯例 = 我们的码流字节惯例）。

**适配点（须在正文/证据报告写明）**：
1. 记账 6 字段旁路：SOG 只压 14 渲染字段；分子 = SOG 码流 + **lzma(记账 6 字段)**，分母仍 `n*20*4`，与 Table 4 其余行同口径；
2. 无 smoothness 正则训练（地图冻结、不重训）——照实登记为适配；
3. xyz 一步按其 train.py 现成配方（`gaussians._xyz = inverse_xyz_activation(...)`）处理；
4. 配置取 umbrella 默认集 2–3 档，**不在我们地图上调参**（可复现性优先）；
5. 解压 PLY 用**我们的** `render_compare` 渲染取 PSNR（同仪器）。

**成本**：Phase 0 环境+单图冒烟 0.5 天（clone --recursive：PLAS/rasterizer/simple-knn 子模块；`environment.yml`：CUDA 11.8 / torch 2.4 / **imagecodecs==2023.9.18 必须固定**——其后版本 JXL 体积回归，其 issue #3）；Phase 1 L2 42 张 × 2–3 档 1 天；Phase 2 L3 36 张 0.5–1 天；Phase 3 集成（生成器增组 → tab_rd 重生+镜像 → §5 L409–417 改写 → 题注 → 重建查 14 页 → pytest）1 天。**合计 2–3 天；建议 10-16 启动、10-19 前完成，距 10-26 留一周缓冲。**

**与门槛 3 的关系**：SOG 是"同类 learned 压缩器"（且就在本稿 §2 的七方法名单里），满足"6×/15× 与至少一个 learned 压缩器同场出现"的**实质**；但**不在门槛 3 点名的四方法字面清单内**——字面清单的处置见 §2.2–2.5 与 §3 方案 B。

### 2.2 Compact3DGS（Lee et al., CVPR 2024）— ⚠️ 无冻结-PLY 入口；适配 = 重训

**代码证据**（maincold2/Compact-3DGS）：
- `train.py` L218 `--start_checkpoint` 只装高斯参数；L107 `final_prune(compress=comp)`、L116 `scene.save(iteration, compress=comp, store=store_npz)` ⇒ 压缩产物（npz：mask + R-VQ 索引 + hash 网格 + Huffman）**全部是训练循环的产物**；README 无"压缩预训练模型"入口。
- 解码回 PLY 有近似：神经场颜色是视角相关的；其 README 说 viewer 需"绕过神经场或把神经场训练成视角无关"才能存 PLY ⇒ 颜色需烘焙，属近似。

**唯一忠实适配**：以冻结地图为初始化 + 其标准训练（图像+COLMAP 管线；我们的 SLAM 数据集可转，`trj_full_final.json` + 图像在库）→ `--comp --store_npz` → 解码 PLY（颜色近似）→ 我们渲染。
**代价**：4–7 天工程（环境/rasterizer 子模块、SLAM 数据集接入其 Scene 管线、解码→PLY）+ GPU 1–2 天（78 图 × 数万 iters）。
**口径注记**：属"重训再压"，与冻结输入对照需单独标注（可能因再拟合而 PSNR 上升，等 PSNR 口径下仍可比较）。
**结论**：可行但重、慢；仅当需要字面满足门槛 3 点名清单时上（§3 方案 B）。

### 2.3 HAC / HAC++ — ❌

训练期方法（从图像+COLMAP 联合训练 entropy model）；无冻结-PLY 后处理通路；评测集 Mip-NeRF360/T&T/DB（`posthoc_baselines_2026-10-09.md §排除项`，本轮复核维持）。门槛 3 允许"重训 entropy model"式适配，但其代码不支持"冻结属性、只训熵模型"的分叉，改造量 ≥ Compact3DGS 且收益不明。不推荐。

### 2.4 TC3DGS — ❌（对象不匹配 + 无代码）

BMVC'25（arXiv:2412.05700）；对象 = 动态表示（时序剪枝 + 梯度感知混合精度量化 + 轨迹 RDP 插值）。我们的冻结地图是**单时刻** 3DGS，无时域可压。官方仓 `saqibjaved1/TC3DGS` 仅 1 commit / README："The code will be released soon." ⇒ 不可运行。

### 2.5 MEGA — ❌（对象不匹配 + 训练期）

ICCV'25；4DGS **训练框架**（deformation field + opacity entropy loss；压缩 = 训练后 FP16 存储 + zip delta，30k iters）。对单时刻冻结地图无适用对象。

### 2.6 Niedermayr et al.（Compressed 3DGS, CVPR'24）— 备选（未点名、本稿未引）

官方仓 `KeKsBoTer/c3dgs` README L66 起：`python compress.py --model_path <model_folder> --data_device cuda --output_vq <out>`——**明确入口：压缩已重建的 3DGS 场景**；压缩含 QAT（量化感知微调，需数据集图像）；`npz2ply.py` 可回 PLY。
**代价**：+1–2 天（含新 bib 条目 + §2 一行；命名与 Compact3DGS 缩写冲突，措辞需区分）。
**价值**：第二个 learned 基线，"同场竞争语境"更强。

## 3. 方案与工作量

| 方案 | 内容 | 工期 | 风险 | 对门槛 3 |
|---|---|---|---|---|
| **A（推荐）** | SOG 单跑 | 2–3 天 | 低 | 实质满足（同类同场）；四个点名方法以本报告登记不可行/无入口理由 |
| A′ | SOG + Niedermayr | 3–5 天 | 低-中 | 同上 + 双 learned 基线 |
| B | A′ + Compact3DGS 重训适配 | 8–12 天 | 中-高 | **字面**满足点名清单 |
| C | 不补跑 | 0 | — | 维持现状（R5 大概率仍卡） |

**取舍点**：10-26 截止。B 若 10-23 未出数则回退 A′。任何方案完成后，§5 的"不比较"段改写 + Table 4 增组 + 全套守护测试走既有流水线（生成器 → 重生 → 镜像 → 重建 → pytest）。

## 4. 风险与口径注记

- **SOG 接线风险**：hydra cfg 构造、xyz activation 一步、`prune_to_square_shape` 对 2.5万–22万 计数的行为 → Phase 0 冒烟先钉住；兜底 = 直接调 `run_single_compression` 低层函数。
- **公平性注记（必写进正文/证据）**：记账 6 字段旁路；无 smoothness 正则训练；配置未调参；解压 PLY 以我们仪器渲染。
- **imagecodecs 固定 2023.9.18**（后版本 JXL 体积回归）。
- **许可**：SOG / c3dgs 均 graphdeco 系研究许可（非商用）——研究用途合规。

## 5. 证据指针

| 用途 | 指针 |
|---|---|
| 门槛 3 原文 | `papers/paper2/CVM_REVIEW_v8.4_2026-10-15.md` L142 |
| SOG 非排序压缩路径 | `Self-Organizing-Gaussians/train.py` L202–206；`scene/gaussian_model.py` L490 `prune_to_square_shape` / L515 `sort_into_grid` |
| SOG 独立压缩/解压 | `compression/compression_exp.py` L166/L193/L210；`compression/decompress.py`（→ `…/iteration_1/point_cloud.ply`） |
| SOG 码率配置 | `config/compression/umbrella.yaml`（jxl_101 / jxl_quant / png_16 / exr…，均注释掉 `_features_rest`） |
| SOG 依赖 | `environment.yml`（CUDA 11.8 / torch 2.4 / imagecodecs==2023.9.18 / PLAS+rasterizer 子模块） |
| Compact3DGS 入口核查 | `Compact-3DGS/train.py` L218 `--start_checkpoint` / L107 `final_prune` / L116 `scene.save(store_npz)`；README 无 pretrained 入口 |
| TC3DGS 无代码 | github.com/saqibjaved1/TC3DGS（1 commit，"code will be released soon"） |
| MEGA 训练期 | ICCV'25 paper：训练 30k iters；FP16 + zip delta（github.com/Xinjie-Q/MEGA） |
| Niedermayr 入口 | `KeKsBoTer/c3dgs` README：`compress.py --model_path … --output_vq …`；`npz2ply.py` |
| 现行 §5 句 | `papers/paper2/paper2_cvm.tex` L409–417 |

---
*本报告为 2026-10-15 换手会话产出；零 GPU；未改任何投稿工件。*
