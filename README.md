# RoGS-Map

**动态场景 Gaussian SLAM 地图：解剖、压缩与离线修复**（研究内容二 / CVM 2027 在投）。

对一个动态场景 RGB-D 3DGS-SLAM 系统所产生的**地图**做对象级研究：用 11 个复现 SLAM
系统横比确立"一张动态场景点图贵在哪、差在哪"，再用**离线 codec** 压缩它、用**离线修复
算子**把反动态范式抹掉的动态内容装回去。三条贡献（全地图侧）：

1. **地图 codec**：离线、逐图自适应、无学习参数的 3DGS 地图压缩（近无损 ~6× / 中 ~8.8× / 激进 ~15×）。
2. **地图侧代价刻画**：反动态范式的可测代价（腾空区 +17.9–22.2 dB）+ 几何/外观拆解 + 地图结构解剖 + 重尾承重实测。
3. **离线地图动态修复算子**：DynaGSLAM 式动态 GS 管理移到离线放置（静态层逐位冻结），J1 5.49–8.95 dB，21/21 过。

系统层（tracking/渲染/效率）为**背景**：前作栈（= 论文1 方法，见 RoGS-SLAM）+ 11 方法横比。
**SWBA / LoopClosure 不属于本文**（R33 同批复测判净伤害 +1.27~1.99cm，叙事红线排除），
本仓不含其代码；final/gate/swbaonly 臂的 run 数据仅作审计性证据保留。

## Installation

```bash
git clone --recursive https://github.com/BinGO620/RoGS-Map.git
cd RoGS-Map
./setup_env.sh          # conda env + 两个 CUDA 扩展（pin SHA）+ Bonn/TUM 数据集
conda activate rogs-map
bash scripts/download_assets.sh   # 离线轨底图（GitHub Release，PLY+轨迹，sha256 校验）
```

## Usage（表 → 命令）

| 论文位置 | 内容 | 复现命令 |
|---|---|---|
| §3 横比 Table 1 | 11 方法 × BONN ATE | `python scripts/02_analysis/paper2_baseline_table.py`（数据 `resources/baselines/`） |
| §3/§8 前作栈主表 | baseline 臂 7 序列 × 3 seed | 先跑 `bash scripts/paper2_fulltable/run_batch.sh`，再 `python scripts/02_analysis/paper2_tables.py` |
| §4 解剖 | 簿记死重/冗余/重尾 | `scripts/gs_compress/{anatomy,storage,tail}_census.py` |
| §5 codec R-D | 42 图 R-D 主表 | `python scripts/gs_compress/rd_sweep.py --run-dir <底图run> ...` |
| §6 反动态代价 | 5 序列探针 | `results/embrace_dyn/`（判据机 `scripts/embrace_dyn/judge_p0.py`） |
| §7 放置/修复 | 在线 vs 离线对照 | `python scripts/dynport_offline/repair_map.py --base-run <底图run> --arm R1 ...` |
| §5 泛化边界 | 36 图 held-out | `results/paper2_rollout/evidence/`（R34，ATE 不入表） |

```bash
# 门禁测试（284 个）
pytest tests/gs_compress tests/dynport tests/dynport_offline tests/embrace_dyn \
       tests/paper2_fulltable tests/lifecycle_paper2 tests/test_config_valid.py -q
```

## 离线轨底图（GitHub Release 资产）

codec 与修复算子是**离线后处理**：输入 = SLAM run 的最终 PLY + 逐帧轨迹 + config
（重资产，不入 git）。`scripts/download_assets.sh` 从 Release 下载并校验 sha256；
`tools/package_release_assets.sh` 生成资产包（run 清单与哈希见 `tools/release_assets.sha256`）。

## Project Structure

```
slam.py / utils/ / gaussian_splatting/ / gui/   # 运行主干（=RoGS-SLAM 同源；裁剪见 PROVENANCE.md）
configs/experiments/{paper2_fulltable,paper2_rollout,...}/  # 实验臂
scripts/{02_analysis,gs_compress,dynport,dynport_offline,paper2_fulltable}/
results/                                        # 判据小件 + evidence（R33 现役批 + 各族判决）
papers/paper2/                                  # 论文2 活区源（本仓为其唯一真身）
resources/baselines/                            # 11 方法复现横比（Table 1 数据源）
```

## Provenance

本仓库由 monogs-ours@`31b0f0367` 按依赖闭包裁剪重建；复制清单、删改明细、验证记录见
[PROVENANCE.md](PROVENANCE.md)。三仓关系：RoGS-SLAM（论文1）→ 本仓（论文2）→
RoGS-Densify（论文3）；`diff -r utils/` = 论文间机制差异。

## Acknowledgements

Built on [MonoGS](https://github.com/muskie82/MonoGS) and
[3D Gaussian Splatting](https://github.com/graphdeco-inria/gaussian-splatting).
