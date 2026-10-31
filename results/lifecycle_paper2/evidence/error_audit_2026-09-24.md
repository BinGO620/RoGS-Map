# error_audit_2026-09-24 — "颠覆性错误"类级审计（对标掩码事故）

> **性质**：只读审计（线索级；**每条已由主会话逐条复核原文**，非子代理转述）。
> **方法**：四轴并行取证 —— ① 指标参照与口径混引 ② 掩码语义与残余依赖 ③ 比较前提（跨批/跨机/帧集/对齐）
> ④ 仪器链自身（污染/读键/稳健性）。**对标先例**：掩码事故（`dynamic_mask_gtmc` 召回 0.10–0.39 +
> ADE20K/VOC 类别号混装 ⇒ 整批读数测错区域，见 `mask_incident_impact_2026-09-22.md`）。
> **本报告不改任何结论**；其触发的叙事改动须走关卡② 后才可入表。

## 0. 一句话结论

**未发现新的"整批测错目标区域"级事故**——掩码类根因已由 v2 体系封堵（唯一 builder + 默认拒 +
三门验证 + canonical 消费方），125/131 个 run 目录 config 齐全、帧集逐臂一致、判据机读键无口径串线。
**但发现 3 处"旧失效口径仍在活跃路径上"的传播缺口**（其中 1 处触及论文正面主张 C1 的量级、
1 处直接影响论文表生成器），以及 2 处比较前提未设门的问题。以下按"是否推翻结论"分级。

## 1. 致命级（推翻结论 / 失效口径仍在活跃路径）

| # | 发现 | 证据 | 判定 |
|---|---|---|---|
| F1 | **`paper2_tables.py` 活跃表生成器仍以 gtmc 口径静态读数优先**：`runtime_static_of()` 读 `r33_rebase_*/tables/mapping_raw.csv` 的 `mask_type=='static'` 行（docstring 自述"gtmc 冻结掩码"），且优先级**高于**批协议源（`if rt is not None and rt.get("mean_static_psnr") is not None: src = rt`） | `scripts/02_analysis/paper2_tables.py:152-156,196-215` | **未收窄**：D1-007 的 canonical 重算产物（`render_compare_static_canon/`，44 run）**无活跃消费方**；而 gtmc 掩码已于 D1-006 删除 ⇒ 生成器读的是"已废口径的历史 CSV"。**建议**：把静态键优先源切到 canonical 产物，或显式标注该列为历史口径 |
| F2 | **C1 的 box 腿量级在仪器 v2 下不成立，但论文载体仍写旧值**：NARRATIVE 写 "mvnobox 残影 Δ−4.1cm、balloon2 Δ−3.1cm（均 3/3 配对优）" | `papers/paper2/NARRATIVE.md:112-113`；对照 `verdict_instrument_v2.md` §3.1（mvnobox 三参照同号但 0.09–0.42cm **未达 0.5 阈**；balloon2 仅 s1/s2 达标，非 3/3） | **需收窄**（属 D2-010 第①项）：box 腿应表述为"方向一致、量级未达阈"；"3/3 配对优"在 v2 下不成立 |
| F3 | **crowd2 `ghost_excess 4.34cm`（gtmc 口径）仍写在写作计划中**：D1-007 已判该数非法（canon 重算替代），且 crowd2 属 v2 判定的**不可判域** | `papers/paper2/NARRATIVE.md:422`；同类见 `results/transient_map/README.md:10` | **被推翻的数字仍活跃**：替换为 canon 值或直接标"该域不可判" |

> 说明：F1–F3 都**不是新的数据事故**，而是**旧事故的传播未清算**——正是掩码事故的教训
> （"结论先入 git、表须重生成"）未完全兑现处。

## 2. 重大级（需收窄 / 补门 / 不可判）

| # | 发现 | 证据 | 判定 |
|---|---|---|---|
| M1 | **L1b gate 的 PASS 建立在单参照 mean 上**：判据机只读 `mean_freshvac_ghost_excess_depth_l1_cm`（=全域静态口径），PASS = `sign_ok ∧ mag_ok(mean)`；而 v2 三参照下该臂为混号（s0 −2.55/−1.16/−0.48；s1 **+0.44/+1.80/+0.74 符号翻转**） | `scripts/02_analysis/l1b_gate_judge.py:63,105-123`；`verdict_L1b_gate.md:23,36`；`verdict_instrument_v2.md` §3.3 | **降级**：该 PASS 应标为"单参照口径下的方向性读数"，不足以支撑机制 PASS |
| M2 | **同一帧集上并存三种掩码仪器后缀**：L3 判决用 `_dense`、L1b 用 `_seg12dense`、L1c/L1d/L1e 与本轮 v2 用 `_canon`；L1b 判决自证同帧换 canon 后 mean Δ 由 −1.893 → −1.437 | `verdict_L3.md:60,188`；`verdict_L1b_gate.md:122-124` | **需统一**：跨判决引用同名字段即构成跨仪器比较（注意：两值均过 1.19 门槛 ⇒ 该判决结论未翻） |
| M3 | **L1d 6-seed 配对的对照臂混两个批**：s0-2 取 L3 批 exit、s3-5 取 L1c 批 exit（`render_L1c_*` 前缀），判决披露了"零新增对照 run"但**未见批次等价性门** | `verdict_L1d_stacked.md:32-34` | **对负结论影响有限**（混批只增噪声，不掩盖一致信号），但该 6-seed 数值不可作跨批绝对值引用 |
| M4 | **所有判据机只报 mean**（n=3/6，无 median/IQR），违 `NOTES.md:559-560` 的"≥2 参照 + median/IQR"规则；唯一合规者恰是本轮 v2 判读机 | `l1b_gate_judge.py:108,125`、`l1c:76`、`l1d:161`、`l1e:125`、`l2_gate:87`、`l2_tum:49`、`l3_paired:91,115`；`instrument_v2_judge.py:105-109` | **规则已立但未回溯**：历史 PASS/FAIL 读数均为单参照 mean ⇒ 与 v2 结论冲突时以 v2 为准 |
| M5 | **表生成器行内静默混协议**：同一行可"PSNR 来自运行期 P-A、ghost_excess 来自批协议" | `scripts/02_analysis/paper2_tables.py:170-172,194-207` | **需逐键 provenance 登记** |
| M6 | **NARRATIVE 的 PSNR 判据界来自已被推翻的"全中性"**：§5.2 写 `PSNR 不劣化 ≤0.25dB` | `papers/paper2/NARRATIVE.md:419`；D1-007：臂间 spread 实为 0.17–0.69dB | **需改**：界值须按 canon spread 口径重设 |
| M7 | **census 跨帧污染已进活跃报告的数字**：`ghost_census_2026-09-24.md` §1（+3.19→+7.45 / +1.79→+9.92）与 `night_report_2026-09-24.md` §3b **mean 行**（+3.19/−2.95）来自被污染的逐帧归因量 | `ghost_population_census.py:286-302`（同 `no_grad` 内 3 次归因渲染）；NOTES 踩坑条目 | **方向性结论不受威胁**（由多帧中位承载），但上述**均值数字**不应作定论（本轮 v2 已给出未受污染的对应读数） |
| M8 | **config 快照缺口**：L1b/L1c/L1d 的 `config_snapshot.yaml` 为 0 个，L3 仅 TUM 臂有；L1c 判决只给 prereg commit（`bdad543f`）未给 as-run config | `find results/lifecycle_paper2 -name config_snapshot.yaml`；`verdict_L1c_occupancy.md:5` | **provenance 不足**：这些判决的"数字属哪个 config"只能靠 consolelog 推证（L2 gate 6 run 的同类缺口已登记在 D1-013） |

## 3. 次要级

- 死配置仍指向已删目录：`configs/experiments/transient_map/eval_v1_balloon.yaml:14`、`configs/experiments/embrace_dyn/*.yaml`（6 个）、`scripts/build_static_eval_mask.py:103`（默认输出名仍为 `dynamic_mask_gtmc`）。
- `render_compare.py:244-257` 的 `--max-scale-m` 删基元计数只进 console、**不写 `render_metrics.json`**（默认关，故无污染；但静默削基元不可审计）。
- frameset（`l3_framesets.json`）无 authority/hash 校验，判据机静默信任帧集。
- `results/mask_fix_iter/evidence/verdict_c4.md:244-248` 跨机并列（2060 vs 3090）FPS 读数——已标机器名，非 ATE，但结论"后端预算是主因"受"FPS 与崩溃阈值混淆"影响，宜注"仅定性"。
- 历史 `results/joint_correct/*`、`results/paper2_rollout/*` 的 config 仍写 `mask_subdir: dynamic_mask_gtmc`，无失效 banner（历史工件，未被 lifecycle 表消费）。

## 4. 已核安全项（防止只看坏消息）

| 检查 | 结果 |
|---|---|
| 帧集配对（抽 L1b/L1c/L1d/L1e/L3 各臂） | **逐臂帧号完全一致**（pt 臂 50…578；crowd 臂 50…850）⇒ 无帧集错配 |
| 判据机读键 | **无**把 `mean_ghost_excess_*`（全历史并集）当 freshvac 的情形；无 depth 当 dB（`l3_paired_judge.py:125-135` 有量纲护栏） |
| Sim(3)/绝对几何/尺度 | 无活跃结论（`paper2_cvm.tex:166` 明示 Sim(3) 不入表；`verdict_sim3_scale.md:78` 已撤回）|
| 已废掩码的活跃消费 | `seg_mask`/`flow_raft` 均无活跃误用（flow_raft 有内参门：`health_check.py:405-464`）|
| M1/M2/T3 状态 | "待复核/不得引用 T3"状态自洽（`NOTES.md:454-457,490-504` 与各 recon 文件一致）|
| 数据链 provenance | 131 个 run 目录中 125 个 config 齐全；缺口 6 个 = 已登记的 L2 gate |
| 掩码语义 vs 场景动体 | C1 的 balloon2 腿 = **人物轨迹区**口径（canonical 掩码 = MaskRCNN COCO person；本地 balloon2 `dynamic_mask/` 470 帧全有）；**无任何活跃主张把机制绑到"气球/箱子本体"**（grep 零命中）⇒ 与 skeleton:48 已写的"必须限定人物轨迹区残影"自洽 |

## 5. 建议动作（按优先级；★ = 属 D2 呈报）

1. ★ **C1 表述落地**：按 v2 把 box 腿改为"方向一致、量级未达阈"，balloon2 去掉"3/3"（并入 D2-010 第①项）。
2. **F1 表生成器切源**：`paper2_tables.py` 静态键改以 canonical 产物为优先（或标注该列口径为历史），否则论文静态表仍走失效掩码路径。
3. **F3 数字替换**：NARRATIVE:422 的 crowd2 4.34cm 换 canon 值或标"不可判"。
4. **M1/M4 判据机口径**：历史 PASS/FAIL 一律补注"单参照 mean 读数"；后续判效统一 median+IQR + ≥2 参照（v2 判读机已是合规范本）。
5. **M2/M6/M7**：统一掩码仪器后缀到 canonical 并在每份判决头标注；PSNR 判据界按 canon spread 重设；census 的 mean 行加污染标注。
6. **M8**：为 L1b/L1c/L1d 补 config 快照或显式登记"以 consolelog 为准"。
7. **M3/M5/次要**：批次等价性门 / 逐键 provenance / 死配置标注 / 删基元计数入指标 —— 择机批量清理。

## 6. 复跑命令（任一条可独立核验）

```bash
grep -n "mask_type\|runtime_static_of\|src = rt" scripts/02_analysis/paper2_tables.py
grep -n "mean_freshvac_ghost_excess_depth_l1_cm" scripts/02_analysis/l1b_gate_judge.py
sed -n '112,113p;419,422p' papers/paper2/NARRATIVE.md
sed -n '286,302p' scripts/02_analysis/ghost_population_census.py
sed -n '32,34p' results/lifecycle_paper2/evidence/verdict_L1d_stacked.md
find results/lifecycle_paper2 -name config_snapshot.yaml | wc -l
```
