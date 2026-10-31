# Verdict — 3-seed 晋级主表（final+gate vs baseline，2026-09-07）

> **账本补登（2026-09-25，D2-015 追溯登记）**：本件成文于决策账本设立（2026-09-20）之前，无当期账本号；统一追溯登记见 `DECISIONS.md` **D2-015**。

> **gate 列已作废、另有替代（2026-09-16）**：本文件的 `gate(final+0.38)` 列即
> `r29_framegate` 臂，跑于 2026-09-07，**早于** `utils/swba.py` 的两次雅可比修复
> （`a21e0773`/`1150fb25`，2026-09-09），该组参照数字已被
> `results/joint_correct/README.md` §2.5c 于 09-09 宣布作废。
> **R32 已于 2026-09-16 在当前 HEAD 重测**（`r32_regate038_*`，21 run rc=0）：
> gate 列现值 = balloon 4.12 / balloon2 5.45 / crowd 2.39 / crowd2 2.57 /
> crowd3 1.83 / **pt1 8.06±0.09（−41%）** / pt2 12.16。
> **本文件的 gate 列保留为 09-07 批的历史记录（head f43788b8），不得作为当前
> 数字引用**；另注意 `final`/`baseline` 列亦为旧码（R33 批正在重基线）。
> 裁决与下游清单：`verdict_f_rebase.md`。

## 运行信息

- 批次：seed3_promotion（21 config × seeds 0-2 = 63 目录位；新跑 28 + SKIP 7
  + 已有 28），全部 rc=0，`seed3_promotion.done` 存档远程
- 时间：2026-09-07 14:24–19:04，远程 2×3090 4-worker（每卡 2 并发）
- HEAD：f43788b8（config 补齐后）；ATE 口径：tracking_raw.csv 末行权威
- 本批次相对 2-seed 筛选（R29）新增：3 个 gate config
  （balloon2/crowd/person_tracking2）+ 全表 seed2

## 3-seed 主表（ATE RMSE cm, mean±sd, s0/s1/s2）

| 序列 | baseline | final | gate(final+0.38) | gate−baseline |
|---|---|---|---|---|
| balloon | 3.12±0.17 | 4.21±0.11 | 4.06±0.19 | +0.94 (+30%) |
| balloon2 | 5.33±0.12 | 5.33±0.16 | 5.40±0.02 | +0.07 (+1%) |
| crowd | 2.29±0.11 | 2.47±0.07 | 2.25±0.17 | −0.04 (−2%) |
| crowd2 | 2.11±0.10 | 3.99±0.35 | 2.62±0.25 | +0.51 (+24%) |
| crowd3 | 1.55±0.05 | 2.58±0.13 | 1.89±0.04 | +0.34 (+22%) |
| **person_tracking** | 13.62±3.27 | 8.48±0.93 | **7.83±0.51** | **−5.78 (−42%)** |
| person_tracking2 | 11.73±0.84 | 11.61±0.42 | 11.54±0.45 | −0.19 (−2%) |

红线 ≤5cm 达标（gate 臂）：balloon、crowd、crowd2、crowd3（4/7）。

## 判决

1. **pt1 主信号在 3-seed 下成立且加强**：13.62 → 7.83（−42%），
   sd 从 3.27 收敛到 0.51（baseline 三 seed 10.60/13.15/17.09 高方差
   本身是事件型漂移的证据）。**但未过 5cm 红线，差 2.83cm——不能成稿**。
2. **gate 门控对易序列的保护在 3-seed 下复现**（vs final 臂）：
   crowd2 3.99→2.62、crowd3 2.58→1.89、balloon 4.21→4.06——
   R29 的 2-seed 结论全部存活。gate 臂相对 baseline 仍有残余退化
   （crowd2 +24%、crowd3 +22%、balloon +30%），非零成本。
3. **pt2 维持"不可区分"判决**（11.54 vs 11.73，−2%，噪声级）——
   连续型漂移对两层架构不敏感，与 R18 收口一致。
4. **balloon2 gate 5.40±0.02 vs baseline 5.33**：三 seed 方差极小，
   +1% 判定为噪声级无害，门控未伤及。

## 结论与下一步

- **主信号成立但数字未达标**：pt1 7.83cm 距红线 2.83cm。部署门控
  （SWBA+逐帧 static_conf 门）作为最终形态定型，不再迭代该家族。
- 下一步唯一已知路径 = **子图架构立项**（LCD-Splat 路线：
  MaskRCNN+NetVLAD+DUSt3R，pt 家族文献实到 1.1/1.3cm）。
  需用户决策：引入预训练组件与"零先验"品牌定位的取舍。
- balloon 残差（gate 仍 +30%）：充气变形假设未验证；操作包络/
  动态证据第二信号二选一，优先级低于子图立项。

## 逐 seed 原始值

见本目录 `evidence/manifest.json`（seed×arm×seq 全量）。
