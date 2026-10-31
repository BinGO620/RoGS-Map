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

## 冒烟 A/B 与离线轨补记

（执行时填写。）
