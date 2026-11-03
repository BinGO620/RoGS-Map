# PROVENANCE — 本仓库与 monogs-ours 的对应关系

- **源**：`/data/monogs-ours` @ `31b0f03670a4366e8c6a5a7012963962a8203663`（分支
  `feat/bpw-densification`）。monogs-ours 不拆分、不修改，作为备份库。
- **构建方式**：manifest 复制（`/data/monogs-export/manifests/rogs_map.yaml`）→ 减法 →
  overlay 补丁 → 验证。任一步可从备份库确定性重建。

## 组织原则

同 RoGS-Densify/PROVENANCE.md（减法不改名、显式清单、主干同源、继承显式化、判据件同仓）。

## 代码减法（对主干文件的修改）

### 删除的模块（11 个）

- **论文3 致密化**（2）：`utils/{densification_selection, selective_densification}.py`
- **SWBA 系**（5）：`utils/{swba, loop_closure, place_recognition, mast3r_verify, dba_lite}.py`
  —— 依据：R33 同批复测判净伤害（所有含 SWBA 臂 +1.27~1.99cm，`results/paper2_fulltable/
  README.md`），叙事红线「SWBA / LoopClosure 一律不出现」（`papers/paper2/R2_NARRATIVE.md:111`），
  依赖 gate 臂的 storage claim 已删（D2-031）。final/gate/swbaonly 臂 run 数据仅审计保留。
- **保留**：`dyn_port_{buffer,online,offline}.py` + `dynport_causal_log.py`（§7 时间放置对照
  的在线列属论文证据链）。

### 接线修改（monogs-ours 源行号）

| 文件 | 源行号 | 内容 |
|---|---|---|
| `slam.py` | 41–47 | loop_closure/dba_lite import |
| `slam.py` | 419–461 | DBA/LoopClosure 结尾三臂（DynPort 因果保存块保留） |
| `utils/slam_backend.py` | 142–164 | dba_lite/selective_densification/densification_selection/static_prob 函数 import |
| `utils/slam_backend.py` | 354–364 | FDose 事件序数 reset |
| `utils/slam_backend.py` | 406–445 | init 站点向量 dispatch → 换纯标量 `densify_and_prune` |
| `utils/slam_backend.py` | 798–822 | selective residual-EMA ledger 块 |
| `utils/slam_backend.py` | 829–873 | map 站点向量 dispatch + log_sel_dens_state → 纯标量 |
| `utils/slam_backend.py` | 1595–1601 | P2a DBA 诊断块 |
| `utils/slam_frontend.py` | 52 | swba import |
| `utils/slam_frontend.py` | 413–415 | Route B SWBA init |
| `utils/slam_frontend.py` | 2928–2962 | Route B SWBA 健康门与调用块 |

等价性：论文2 所有臂配置下被删分支均不激活；`compute_per_gaussian_knobs`/`log_sel_dens_state`
禁用时零副作用早退（不耗 RNG），标量路径逐位一致（与 RoGS-SLAM 同一核证）。

## results 取舍（判据件口径）

- **paper2_fulltable**：保留 `r33_rebase_*`（四臂 84 run 现役批，Tab 主表单一事实源
  `evidence/manifest_r33.json`）、`effctl*`（Tab.4 同码计时批，D1-027）、`render_compare*`
  （Tab.2r/3s 渲染源）、`evidence/`；**丢弃** r29/r30/r31/r32/v2 被取代批（219 目录
  ~108MB）与 legacy `{seq}_{arm}_seed*`——判决/勘误链在各 verdict md 中完整。
- **paper2_rollout**：保留 `r34_*`（fingerprint 跨批臂等价门 G2-S1 需要）+ `evidence/`
  （R34 ATE 不入论文表，结论由 verdict 承载）+ 顶层诊断 md。
- **lifecycle_paper2**：评测仪器库，保留 `evidence/`。
- **trj 政策**：`plot/trj_full_final.json` 保留（sim3 阳性对照与离线轨底图复现需要）；
  逐 KF `trj_N/stats_N` 与图片不入库。PLY 一律不入库（底图走 Release）。

## 论文2 活区源（papers/paper2/）

本仓为 `papers/paper2/` 的**唯一真身**（tex/tables/figures/supplement，39MB；archive
版本快照 79MB 不带）。此前 monogs-ours 与 biyelunwen 双副本问题就此收敛。
大论文仓库后续以引用/快照方式取用。

## 测试取舍（如实）

保留全部复现/门禁测试（284 个全绿）。**移除 4 项 monorepo 治理门**（与可复现性无关，
依赖备份库的 git 历史与 archive/closed_families）：
- `tests/embrace_dyn/test_dyn_probe.py` 中 `test_causal3_measurement_code_committed_before_run`
  / `test_causal3_analysis_provenance_recorded`（硬编码 monogs-ours commit SHA 断言祖先关系，
  重建仓结构上不可满足；预注册溯源由 monogs-ours 历史 + evidence 文件日期承载）；
- `tests/lifecycle_paper2/test_gate1_class_sweep.py`、`tests/lifecycle_paper2/test_sweep_citation_claims.py`
  （全库文本/归档族清扫，属开发纪律而非复现门）。
overlay 机制：修订版 `test_dyn_probe.py` 存于 `/data/monogs-export/overlays/`，复制后覆盖。

## 验证记录

| 项 | 结果 |
|---|---|
| AST import 闭包 | 无缺失（仅 namespace 包误报） |
| `py_compile` slam.py / slam_frontend.py / slam_backend.py | 通过 |
| pytest 全门禁 | **284 passed, 0 failed**（gs_compress/dynport/dynport_offline/embrace_dyn/paper2_fulltable/lifecycle_paper2/test_config_valid） |
| submodule pin | `diff-gaussian-rasterization@43e21bff`、`simple-knn@44f764299` |
| 2060 冒烟 A/B（40 帧 r33 baseline balloon） | 见下 |
| 离线轨 rd_harness 单点 | 见下 |

## 数字验证矩阵（论文 PDF ↔ 表 tex ↔ 生成器 ↔ run CSV 全链）

| 论文表（\input） | 内容 | 全链验证 |
|---|---|---|
| tab_baseline | 11 方法 × BONN 系统横比（含 Prior RGB-D stack 行） | pytest 门禁（生成器==committed tex）+ **PDF 数字 103/103 命中** |
| tab2r_render / tab3s_static | 渲染/静态指标 | 门禁 + **PDF 14/14、22/22 命中** |
| tab4_efficiency | 同码计时两列 FPS | 门禁（非退化+中位复算）+ **PDF 14/14 命中** |
| tab_rd | R-D 主表 42 图 | 门禁 + **PDF 58/58 命中** |
| tab4d_ablation / tab_dyncost_seq / tab_dynport | 4D 消融 / 反动态代价 / 放置对照 | 门禁 + **PDF 10/10、10/10、8/8 命中** |
| R33 四臂主表（tab1_main，审计用，论文未 input） | baseline/swbaonly/final/gate | pytest coverage 7×4 全有值 + sim3 阳性对照 60+ 样本双路径一致 |
| §5 泛化边界（rollout） | R34，ATE 不入表 | evidence verdict 承载 |

**PDF 抽检 = 8 张表 239/239 数字 100% 命中**（pdftotext 全文检索，2026-11-01）。
配置同源：347 个 yaml 与 monogs-ours@31b0f0367 逐字节一致（parity check）。
主干与 RoGS-SLAM 的差异恰为预期论文差：dynport 四件（§7 在线对照列）+ slam.py/
slam_backend.py 两处接线文件；frontend 与 RoGS-SLAM 逐字节一致。

## 事故记录（2026-11-01，parity 机检发现并修复）

copy_by_manifest 为覆盖式复制：补 embrace 脚本的第二次全量拷贝把已完成的减法
（9 模块删除 + 11 处接线编辑）整体还原，导致 commit `aada4074` 及之前的代码实际为
纯净 monogs-ours，与 PROVENANCE 描述不符（冒烟 A/B 当时是"纯净 vs 纯净"，无鉴别力）。
commit `15c99e2c` 重做手术并以真手术版重验：pytest 284 passed、冒烟 A/B
ATE Δ=0.0137cm（vs 同一纯净参照 0.7458）、parity 复检通过。
**教训已固化**：今后任何 manifest 重拷后必须重跑 config_parity_check.py + 门禁。

## 冒烟 A/B 与离线轨补记

- **（勘误）**下文首次 A/B 记录于"重拷还原事故"期间，当时仓内代码=纯净源，
  该对照无鉴别力，仅作 CUDA 噪声量级参考。**有效记录 = 事故修复后（commit
  `15c99e2c`）的真手术版对照：ATE RMSE 0.7321 vs 0.7458 cm（Δ=0.0137cm，噪声量级），
  KF-ATE 0.8947 vs 0.8743——减法未改变管线行为。**
- **冒烟 A/B（首次，勘误见上）**：`configs/experiments/paper2_fulltable/r33_rebase_baseline_balloon.yaml`，
  `--max-frames 40 --seed 0`，同机同卡（RTX 2060）各一次，参照 = monogs-ours@31b0f0367
  纯净副本。ATE RMSE 0.7208 vs 0.7458 cm（Δ=0.025cm）、KF-ATE 0.8885 vs 0.8743、
  per-frame 均值 0.6469 vs 0.6689——Δ 低于同配置跨批噪声地板（0.18–0.62cm）一个量级，
  与 RoGS-SLAM 的 A/B（Δ=0.022cm）同量级。**判定：PASS。**
- **离线轨单点**：rd_harness 于冒烟 run 自产 PLY 上全链路（codec 编码→重建→渲染→分区
  指标）：13.80 B/prim，ratio 5.80×，PSNR 18.077 / static 30.578——裁剪仓内 codec 线完整可用。
- **Release 底图资产**：`tools/derive_release_runs.py` 从证据 json 反推出 **63 个底图 run**
  （RD 腿 legacy baseline + 修复腿 r33 baseline 7×3，盘上 0 缺失）；
  `tools/package_release_assets.sh` 逐 run 打包三判据件并出 sha256 清单
  （`tools/release_assets.sha256`）；`scripts/download_assets.sh` 下载+校验+还原。

## 归档原则（2026-11-04 登记；用户指令，适用于每一个仓库）

- **工作区永远只留最新**：过时的版本/草稿/历史快照一律移入本仓 `archive/`（就近归档，
  命名 `{语义}_{YYYY-MM-DD}`），不散落工作区顶层。
- **归档 ≠ 删除**：归档件是证据键，账本指针不追改；每处归档配 `README.md` 并在仓内
  索引登记。
- **本仓独立性**：实验一律回 monogs-ours 做，本仓只收"已判据确认"的成果快照
  （四步同步见 monogs-ours `/data/master-thesis/WORKFLOW.md`）；本仓自持门禁与
  PROVENANCE，不依赖 monogs-ours 工作区即可复验。
- **里程碑触发同步**：只在判决落地/投稿等里程碑做 manifest 重灌 + gate 全跑 +
  PROVENANCE 登记；平时不同步（避免快照漂移）。
