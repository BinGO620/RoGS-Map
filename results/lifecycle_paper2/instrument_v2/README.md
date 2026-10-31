# instrument_v2 — 仪器 v2（matched-control freshvac 三参照）全臂重评分

> 预注册（判据先锁）：`../evidence/prereg_instrument_v2.md`（commit 3cecccfe，先于任何实装/跑批）。
> 判读产物：`../evidence/instrument_v2_onepager_table.md`（程序化生成）。
> 本目录 = 测量代码 + 运行件 + 原始读数 + 批记录。

## 1. 目的

night_report §3b/§3c 发现：官方 freshvac（全域静态参照）在 Bonn pt 上的"残影超额"与服务
构型匹配的邻域环对照**符号相反**（+3.19 → −2.95cm），效应量与参照偏差同阶。本仪器加入
**第三对照**（深度分层匹配：GT 深度同带 + 非边缘），把"目标效应"与"参照区构型偏差"分离，并对全部
已有臂重评分（**只重渲染不重训**）。

三参照（逐帧并行，同一 vacated 区，同一渲染深度）：
1. 全域静态 = GT 有效 ∧ ¬dyn ∧ ¬vac（官方 freshvac 口径）
2. 邻域环 = dilate15(vac) ∧ ¬dilate5(vac) ∧ 静态
3. **深度分层匹配（m3）** = 静态 ∧ GT 深度 ∈ vac 区 GT 深度中位数 ± 带 ∧ 距边 ≥15px ∧ 支撑 ≥200px
   （深度源 = GT——被评对象不自证）

聚合口径：**median + IQR**（禁均值单独作结论，NOTES:516）；主读数 = **逐帧配对 Δ = 臂 − off 后再取中位**（prereg §2）。

## 2. 范围与覆盖率

| 项 | 值 |
|---|---|
| 期望（prereg §2b 全臂清单） | 109 run |
| **可评分** | **103 run** |
| 例外 | L2 gate 6 run（crowd/crowd2/person_tracking2 × s0/s1）|

**L2 6 run 不可评分（如实登记的范围偏差）**：该批 run 目录未留 `config.yml` 快照，且
`plot/trj_full_final.json` 两侧工作副本已空（git 亦从未跟踪；远程目录 mtime 2026-09-22 23:57
的被清空的 `plot/`、`reliability/` 等目录为证）⇒ **无相机位姿无法重渲**。补跑已尝试
（`--config` 指向 `configs/experiments/lifecycle_paper2/l2_*_gate.yaml`，继承式配置经
`utils.config_utils.load_config` 解析成功）但止于 trj 缺失；唯一替代路径（用 canon 渲染存盘的
17 张 depth PNG 反算）**未采用**——属第二条测量代码路径，且 L2 是已关闭的诊断臂（D1-008），
不影响 prereg §4 判读支柱。证据：`rescore_batch_shard*.done` 中 6 条 `rc=1` + `rescore_l2supp.log`。

## 3. 代码版本（双溯源）

| 运行件 | run 数 | 测量代码 | 说明 |
|---|---|---|---|
| 主批 | 103 产出 | `2864c997` | 双卡分片（55/54），远程 3090；**其中 73 个为本轮保留件** |
| 重跑（crowd 族 + TUM） | 30 | `5695bc94` | 全域静态对照空集守卫修正（原出 NaN，见 §5）→ **替换主批对应 30 个** |
| L2 补跑 | 0（6 尝试全败） | `3ac72fd0` | 仅新增 `--config` 参数；trj 缺失致不可评分 |
| 判读机 | — | `1623289b` → `29f21703` 整改 → 见 `git log -- scripts/02_analysis/instrument_v2_judge.py` | `instrument_v2_judge.py`（判据权威 = prereg §4 + 修正案 1/§9）；口径修正见本 README §4 与 prereg §8/§9 |

⇒ 权威读数构成：**73 @ `2864c997` + 30 @ `5695bc94`**（两者数值已证等价，见下）。

**阳性对照 ×2（证明版本差异非实质）**：
1. `--config` 版本（`3ac72fd0`）复算同一 run：与主批产物 **diff = 0 行**（除 run_dir 字段）。
2. **守卫路径对照**（旧码 `2864c997` vs 新码 `5695bc94`，同一 crowd run `L3_crowd_off_s0` 逐帧比对）：
   两臂皆有效的帧**数值逐位一致**（6 处），新码判 `None` 的帧**正是旧码产出 NaN 的帧**（11 处），
   真不一致 **0 处** ⇒ 守卫只改"可判性"（NaN→None），不改数值。

> **实施澄清**（prereg §8 追记）：第三对照实为**深度分层匹配**（无独立空间距离项）；
> `GEN` 为跨帧共享随机流（非每帧种子 0）；`m3_under_supported` 帧标记改以"可用帧数 +
> 支撑像素中位"落盘；采样上限仅作用于 m3。判据 §4 与 §2 主读数定义不变。

## 4. 判读口径

| 项 | 口径 |
|---|---|
| 主读数 | **逐帧配对 Δ = 臂 − off（同帧集）再取 median**（prereg §2；首版误为"各臂帧中位数相减"，已改） |
| 聚合 | median + IQR（§1c 明细列；mean 仅参考） |
| 判据 | 三参照 median 同号 且 \|median\| ≥ 0.5cm（prereg §4） |
| 方向 | **负 = exit 改善**（C1 假设方向）；标签区分"存活·改善 / 存活·变差" |
| 判据子集 | prereg §4 列 balloon2 / mvnobox / crowd3（9 对）；balloon / mvnobox2 为**扩展**（非判据） |
| **⚠稀薄（可判性）** | 任一参照**可用帧 < 50% 共同帧** ⇒ 对照区在多数帧上结构性缺失，**判效不可用**，不计入达标 |
| 匹配带 | **±15%**（97 run）；支撑不足按 prereg §3 序放宽至 **±25%**（6 run） |

## 5. 仪器参数与局限（对照区是否存在）

| 参数 | 值 | 性质 |
|---|---|---|
| 匹配带 | ±15% → 对拍放宽 ±25% | 仪器参数 |
| m3 支撑下限 | 200 px/帧 | 仪器参数 |
| m3 帧内采样上限 | 5000 px（跨帧共享随机流，固定种子 0） | 仪器参数；**vac 区不采样 ⇒ 样本量不对称** |
| 边缘排除 | 15 px（**仅作用于 m3**，vac 不排除） | 仪器参数；可抬升 \|exc_m3\| |

**参照可用性（本轮核心仪器发现）**：`support_px_median` 显示密人群域**不存在对照区**：

| 序列 | vac px（≈全图 66%） | 全域静态 px | 邻域环 px | 可用帧（full/ring/m3，共 17） |
|---|---|---|---|---|
| crowd2 | 204,006 | **0** | **0** | 少数（⚠稀薄） |
| crowd3 | 193,884 | **0**（中位） | **0**（中位） | 8 / 8 / 6（⚠稀薄） |
| crowd（dense 帧集） | 152,287 | **0** | **0** | 2 / 2 / 2（⚠稀薄） |
| balloon2（对照：稀疏域） | 200,522 | 10,010 | 2,882 | 17 / 17 / 15 |

⇒ `past`（历史掩码并集）在密人群序列上近乎覆盖全视野，参照区结构性消失；此类域
**任何「腾空区 vs 静止区」型仪器都判不了效**（night_report §3 的 TUM 结论在 Bonn 人群族复现）。
表中此类行标 **⚠稀薄**，按判据不可用。

**另一独立发现**：`ghost_population_census.py` 存在**跨帧污染**（同一 `no_grad` 块内连做 3 次
归因渲染，浮点残留影响后续帧基准渲染；balloon2 off s0 批量 17 帧与单帧重跑最大差 12.7cm，
单帧重跑与 instrument_v2 逐位一致）。已记 NOTES 踩坑。本仪器每帧单次渲染，不受此影响。

## 6. 运行环境

- **远程 3090 双卡（权威）**：`jiangwenheng@172.16.227.24`，`CUDA_DEVICE_ORDER=PCI_BUS_ID`，
  分片 2 卡并行；每 run ≈1.5–2.5 分钟（17 帧）。
- 本地 2060：仅 3 run **pilot**（脚本对拍用，产物 `sample_balloon2_{off,exit}_s0.json`），
  **非权威读数、且不在 `rescore/` 目录内 ⇒ 不进入任何判读计数**（判读机只读 `rescore/*.json`）。
  纪律偏差与其纠正见 NOTES 踩坑「正式批误放本地 2060」。

## 7. 产物清单

```
instrument_v2/
├── README.md                              # 本文件
├── rescore_batch_manifest.json            # 109 run 清单（run_dir + 帧集，源自 canon 渲染 render_metrics）
├── rescore/*.json                         # 103 个逐帧三参照读数（权威）
├── sample_balloon2_{off,exit}_s0.json     # 本地 pilot（非权威）
├── rescore_batch_shard{0,1}.done          # 主批 rc 记账（109 行 = 30 rc=0 + 73 skip-exists + 6 rc=1）
│   └── *.done.v1                          # 首次运行的记账副本（重跑前保留）
├── rescore_batch_l2supp.done              # L2 补跑 rc 记账（6 条，皆因 trj 缺失失败）
└── rescore_shard*.log / rerun_shard*.log / rescore_l2supp.log   # 运行日志
```

## 8. 判读结果摘要（数字权威 = `../evidence/instrument_v2_onepager_table.md`）

- **C1（prereg §4 子集 9 对）：2/9 达标**——均为 **balloon2 s1/s2 且方向为 exit 改善**
  （s1 −2.57/−2.78/−3.96；s2 −3.57/−2.09/−5.82）。**mvnobox 3 对同号但未达 0.5 阈值**
  （0.09–0.42）；**crowd3 3 对因对照区缺失不可判**（⚠稀薄）。扩展序列 0/6。
  三参照**共同帧严格版**（§1b）下 balloon2 三个 seed 全部同号（s0 环 leg 仅 −0.34）。
- **pt：不可判**（6 对中 3 对同号 3 对混号 ⇒ 符号不一致，效应量 < 仪器分辨力；
  与 night_report §3b 预期一致）。
- **TUM：只落表不判读**（prereg §2b；全域静态对照早期为空，ring 与 m3 方向相反且量级 ±20–44cm）。
- ⇒ **prereg §5 触发**：C1 未整体存活（判据子集 9 对中 7 对未过/不可判）⇒ **须呈报用户（D2），
  不自动改叙事**。
