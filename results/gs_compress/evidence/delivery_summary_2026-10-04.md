# 交付摘要：动态场景 GS-SLAM 地图压缩线（D2-025，L1+L2+L3 完成，2026-10-04）

> **账本**：D2-025。**性质**：写作轨输入（一页纸口径汇总；数字全部有工件键，禁手抄）。
> **口径铁律**：rate = 压缩码流；渲染 = 同地图重载渲染（`render_compare` 固定帧集）；
> **禁与 R33 表 / run 时 eval / 跨批数字混引**；对照一律同码率 ±2%。

## 1. 一句话

一个**离线、无学习参数、逐图自适应**的 3DGS 地图 codec：把 SLAM 生长出的**动态场景地图**压缩到
**近无损 6× / 中 9× / 激进 15×**（vs 原始 20 字段 f32），并在 **未见域（R34 留出 36 图）复现同量级**。

## 2. 主表（L2，Bonn 7 序列 × 3 seed × {baseline,gate} = 42 图）

| 工作点 (xyz,f_dc,opacity,scale,rot) | 全局 ratio | 全图 PSNR | 静态区 PSNR |
|---|---|---|---|
| 16,8,8,8,8（近无损） | **5.96×** | 15.370 | 21.791 |
| 10,6,6,6,6（中） | **8.77×** | 15.322 | 21.637 |
| 8,4,4,4,4（激进） | **15.11×** | 14.740 | 19.209 |

- 单序列 R-D：`evidence/rd/l2_summary.md`；曲线图：`figs/fig_rd_curves.{pdf,png}`。

## 3. 泛化（L3，R34 留出：TUM fr1/fr3 四场景 + Bonn box × 3 seed × {rb,gate} = 36 图）

| 工作点 | 全局 ratio | 全图 PSNR |
|---|---|---|
| 16,8,8,8,8 | **5.96×** | 15.896 |
| 10,6,6,6,6 | 8.73× | 15.685 |
| 8,4,4,4,4 | 14.82× | 14.132 |

⇒ 与主表**同量级**（近无损两处均 5.96×）⇒ **泛化成立**（判读 `l3_generalization_2026-10-04.md`）。

## 4. 组合 codec（近无损量化 + SLAM 结构感知 + 体素合并）

| 序列 | 原始 20字段f32 | 近无损+dedup | 激进+dedup |
|---|---|---|---|
| balloon | 2.94 MB | **7.26×** | 10.57× |
| crowd2 | 3.22 MB | **7.70×** | 11.30× |
| pt2 | 4.78 MB | **7.39×** | 10.44× |

SLAM 结构感知件：① rot 存 3 分量（PLY 未归一化 89–94%）；② 尺度各向同性塌缩（83–90% 近各向同性，省 scale 组
34%）；③ 记账字段剥离（6 字段恒常数，占 30% 原始字节，但**熵编码下已被压掉 ⇒ 只作 accounting**）；④ 体素合并 2cm（**−18~20% 字节 @ PSNR −0.05**）。

## 5. 存储代价账（零 GPU，`storage_accounting_2026-10-04.md`）

gate 臂 vs baseline 地图体量**跨序列 −18.7%~+33.0%**（七序列 seed 均值 +3.8%）。
**⚠ 论文禁用立项时写的"+21.58%"**（那是旧批单 run；规范四臂口径非全局膨胀）。图：`figs/fig_storage_accounting.*`。

## 6. 贡献框定与边界（诚实）

**可主张**：① 动态场景 GS-SLAM 地图的离线量化 codec（R-D 主表 + 泛化）；
② SLAM 结构感知编码（rot3 / iso-scale / 记账剥离）；③ 动态/拥挤 regime 的存储代价刻画。

**边界（如实登记，不作贡献）**：
- **分区/可见性/属性比特分配 = 权衡非帕累托**（8 类尝试无一有同码率优势）⇒ 降为消融；
- **"轨迹可见性剪枝"不安全**（SLAM 稠密地图该基元仍参与 alpha；GT 深度空洞致 87% 假不可见）；
- 量化 codec 是成熟技术 ⇒ **单靠效率分量撑 CVM 偏薄**（是否够须用户检查点① 拍板）。

**禁**："首个 3DGS 压缩"（3DGS.zip/HAC）；"首个 GS-SLAM 压缩"（CGS-SLAM/DiskChunGS 静态场景）。
**必须区分**：CGS-SLAM、DiskChunGS（静态）；3DGS.zip/HAC（离线 NVS）。引用 `[ID未核]` 须回源逐字核对。

## 7. 工件入口
- 判据：`prereg_gs_compress.md`；判读：`l1_readout_2026-10-04.md` / `l3_generalization_2026-10-04.md`；呈报：`checkpoint1_onepager_2026-10-04.md`
- 数据：`rd/*.json`（581 份）+ `rd/l2_summary.md`；图：`figs/*`
- 代码：`scripts/gs_compress/{gs_codec,partition,rd_harness,rd_sweep,l2_batch,l3_batch,l2_aggregate,make_figs}.py`；单测 `tests/gs_compress/`（7 passed）
- 复算：见 `results/gs_compress/README.md`
