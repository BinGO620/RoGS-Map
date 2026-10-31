# 跨批次臂等价性核验（G2-S1）：R33 主批 ↔ R34 留出批（2026-10-09，零 GPU）

> **账本**：D2-028 续轮（论文 2 写作轨）。
> **触发**：`papers/paper2/RERUN_MAP_2026-10-05.md` §1 的 held-out ATE 项标注
> 「⚠ 待核：R34 面板 ATE 是否可直接入表（G2-S1）；若否，最小补跑」。
> **判据出处**：DISCIPLINE「测量口径」4（等价性/阳性对照须落成**可复跑工件**）+
> 「比较前提」5（跨批取对照必须补**批次等价性门**）。
> **方法**：零 GPU，盘上 config 逐字段对比。可复跑工件 =
> `scripts/02_analysis/paper2_batch_fingerprint.py --selfcheck`（含阳性/阴性对照）。

## 0. 结论（**注意作用域**）

**PASS（限 ATE 表口径）——R33 主批与 R34 留出批的「ATE 表角色臂」在全部非数据集字段上
逐字段一致（54/54 run 无 diff）。** 即：`rb`↔`baseline`、`sw`↔`swbaonly`、`gate`↔`gate`。

**⚠ 作用域边界（G2-M1 修订 2026-10-09）**：本核验**只覆盖 ATE 表所用的三臂**。
**它不覆盖 codec 的面板**——codec 的两组面板臂**不同**：
- codec **主面板**臂 = `{baseline, final}`（`scripts/gs_compress/l2_batch.sh:13` `ARM=(baseline final)`）；
- codec **留出面板**臂 = `{rb, gate}`（`scripts/gs_compress/l3_batch.sh:13` `ARM=(rb gate)`）；
- 且这两个集合**不可互相映射**：`baseline`↔`rb` 一致，但 **`final`↔`gate` 不一致**
  （`SWBA.swba_max_static_conf` = `None` vs `0.38`）⇒ codec 留出面板与 codec 主面板**并非同臂配置**。
⇒ 本核验**不得**被引作"codec 泛化是纯序列泛化、系统相同"的依据（tex §Codec Generalisation
新增的等价性句已按此**删除**，见 M1 处置）。

**ATE 表的实际用途**：指纹 PASS 使 R34 的 `ate_rmse_cm`（col 8 全帧）在**口径上可比**主表；
但**最终决定不入 ATE 表**（三理由见 §5），故本件的落地价值 = 把「同栈同码」从口头声明
升级为**可复跑工件**（「测量口径」4）。

## 1. 两批是什么

| 批 | 目录 | 序列域 | 臂 | seed | run 数 | 日期 |
|---|---|---|---|---|---|---|
| **主批（R33）** | `results/paper2_fulltable/r33_rebase_*` | Bonn 7 | baseline / swbaonly / final / **gate** | 0–2 | 84 | 2026-09-16 |
| **留出批（R34）** | `results/paper2_rollout/r34_*` | TUM fr1/fr3 五场景 + Bonn `moving_obstructing_box` | `rb` / `sw` / **gate** | 0–2 | **54** | 2026-09-17 |

R34 省去 `final` 臂（依据 = R33 已同批证明回环在 Bonn 7 上恒零修正），
故留出批是 **3 臂**，主批是 **4 臂**——入表时须写明此结构差异。

## 2. 臂角色映射（由 enabled 开关面判定；**限 ATE 表口径**）

| R34 臂 | ↔ 主批臂 | SWBA | LoopClosure | swba_max_static_conf | 其余 |
|---|---|---|---|---|---|
| `rb`   | `baseline` | false | false | — | RobustTracking/ReliabilitySignal/DeferredCommit/DynamicKeyframe/SemanticMask 全 true，lifecycle=prune |
| `sw`   | `swbaonly` | **true** | false | — | 同上 |
| `gate` | `gate`     | **true** | **true** | **0.38** | 同上 |

`method=Combined-Prune`、`method_from=configs/experiments/combined_prune/method.yaml`
三臂全同（两批皆然）。

## 3. 判定（机写）

```
$ python scripts/02_analysis/paper2_batch_fingerprint.py --selfcheck
=== paper2 cross-batch arm equivalence (R33 main <-> R34 held-out) ===
  r34[rb] <-> main[baseline]  18 runs: IDENTICAL
  r34[sw] <-> main[swbaonly]  18 runs: IDENTICAL
  r34[gate] <-> main[gate]     18 runs: IDENTICAL
OVERALL: PASS — arms identical across batches

=== controls ===
[pos] mutated SWBA.swba_max_static_conf -> detected: True
[neg] full-field compare (no exclusion) -> false diffs: 17   ← 数据集字段按设计不同
[neg] real fingerprint excludes Dataset.*/Results.*/inherit_from/seed: True
```

- **口径**：指纹 = 合并后的运行时 config（`inherit_from` → `method_from` → 本层）
  逐字段比较；**排除** `Dataset.*` / `Results.*`（不同数据集/不同 save_dir，按设计不同）
  + `inherit_from`（不同数据集链）+ `seed`（种子不构成臂差异）。
- **阳性对照**：改任一机制开关（如 gate 阈值）⇒ 立即检出 DIFF（检查非恒真）。
- **阴性对照**：若不排除数据集字段，跨批会出现 17 处"假 diff" ⇒ 排除是承重的。
- **作用域限制**：`ARM_MAP` 只声明 ATE 表三臂（`rb`/`sw`/`gate`）；**不声称**覆盖 codec 面板。

## 4. CSV 口径一致性（同于 config 核验）

R34 与主批 `tables/tracking_raw.csv` **列名逐位相同**（24 列），主判列
`ate_rmse_cm`（col 8 全帧）与 `keyframe_ate_rmse_cm`（col 14）同名同义。
⇒ 口径可比（col8 全帧，非 col14 关键帧）。

## 5. held-out ATE 不入表（决定，非"漏做"）

指纹 PASS **但决定不入 ATE 表**，三条理由（slam-critic 已独立复核成立）：
1. **面板是选择性样本**：R34 六序列是从 19 条中**因 |Δ|>1.5cm 挑出**
   （`results/paper2_rollout/README_r34.md:4,20` 明载"客观、非任意"）⇒ 是**硬例复现面板**，
   不是随机泛化面板；把它的 ATE 称 cross-benchmark generalization 属**口径错**（「测量口径」①）。
2. **数据方向不利**：gate 臂在 6 条里 **4 条劣化** base（Δ(rb−gate): f1_room +8.152 / f3_st_rpy +2.602 /
   mob +10.400 / f3_wk_rpy +0.598），且 base/gate 双双仅 **2/6 <5cm**（`evidence/verdict_r34.md:41-47`）
   ⇒ 入表即自曝，不服务叙事（「组件准入=叙事服务」）。
3. **tracking 属背景**：论文已明 "make no claim of state-of-the-art tracking"（tex:630），
   held-out ATE 属 tracking 结果，不进主线。

## 6. 遗留（如实登记，不阻断）

- **运行期远程 HEAD 无硬证**（R34 侧）：`evidence/verdict_r34.md` §七 已登记
  （远程 reflog 仅回溯 09-13；以「窗口内核心提交=0 + config 逐字段 diff + 执行正控」
  组合间接证明）——本次 config 核验**复现并强化**其中的"config 逐字段 diff"一环。
- **面板结构差异**：R34 无 `final` 臂、序列域含 TUM；且**该差异正是 codec 面板不可等价映射的原因**（§0）。

## 7. 工件

- 脚本：`scripts/02_analysis/paper2_batch_fingerprint.py`（判定 + 对照）
- 测试：`tests/paper2_fulltable/test_paper2_batch_fingerprint.py`（4 测）
- 本报告：`results/paper2_fulltable/evidence/batch_fingerprint_g2s1_2026-10-09.md`
