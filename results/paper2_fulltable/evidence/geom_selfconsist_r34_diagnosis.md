# f3 自洽几何异常 — 根因诊断与列可用性裁决（2026-09-18）

> 承接 `geom_selfconsist_r34_note.md` 的 3 步诊断建议。本会话（2026-09-18 下午）
> 在本地 CPU + 远程 CPU（nice 19，零 GPU）完成诊断。
> 工具：`scripts/02_analysis/diag_f3_geom.py`（本地）、`scripts/02_analysis/diag_f3_probe.py`（远程探针）。
> 产物：`diag_f3_geom.json`、`diag_f3_probe_md5.json`、`diag_f3_probe_scale_sweep.json`、
> `geom_selfconsist_r34_f3_md10.json`。

## 结论先行

**根因 = 参考云（GT 深度融合）的 `max_depth=5m` 裁剪**，在**深场景**（TUM f3 家族）
上把参考云裁掉一半；而重建云（rec）覆盖超出 5m，那部分点找不到匹配 →
**accuracy（rec→GT）被远场尾巴顶爆**，而 completion（GT→rec）照常 ≈5cm。

- 这不是"尺度不匹配"（scale sweep 证明无任何尺度能救），也不是"rec 坏掉"：
  - **scale sweep**：f3_st_rpy/f3_wk_rpy 在 s∈[0.2,3.0] 全程 median ≥10cm，无最优尺度；
    f3_office 最优恰在 **s=1.0**（median 1.84cm）→ 尺度本来就对。
  - **depth-clip 对照**：`max_depth` 5→10m，参考云尺寸 6.8→12.6m，
    f3_office acc 39→**7.2**cm、f3_st_rpy 243→**44**、f3_wk_rpy 186→**37**（首测 rb/seed0）。
  - **关键限定**：Bonn 7 序列 depth **0% >5m**（R33/R34 全部结论在其上）→ **跨臂结论不受影响**；
    只有 f3 家族 depth p95 达 7–8m、5–16% 像素 >5m 才被裁。

## 三步诊断结果

### 第 1 步（原计划：rec 坐标范围 vs 融合云范围）— 已完成，改用更直接的探针

| run (rb/seed0) | rec bbox diag | ref bbox diag @md5 | ratio | acc mean | acc med | >1m |
|---|---|---|---|---|---|---|
| f3_st_rpy | 15.67 m | 6.83 m | 2.29 | 242.9 cm | 297.8 | 58.2% |
| f3_wk_rpy | 17.90 m | 6.10 m | 2.94 | 185.5 | 69.5 | 45.9% |
| f3_office | 14.18 m | 6.74 m | 2.10 | 39.0 | **1.84** | 13.8% |
| f1_room (正常) | 10.36 m | 7.84 m | 1.32 | 5.6 | 2.9 | 0.2% |
| moving (正常) | 7.15 m | 7.03 m | 1.02 | 4.1 | 2.5 | 0.0% |

- **ref 尺寸被压到 ~6.8m**，与 f3 场景真实范围（rec ~15m）不符 → 首证裁剪假设。
- f3_office 的 acc **median 仅 1.84cm**（干净核）、mean 39cm（尾巴）：典型"干净核 + 远场尾巴"双峰。

### 第 2 步（seg_mask 类别编码）— 已完成（本地全帧扫描）

- f3 `seg_mask` 用 **VOC-like 类 id（0..149）**，**class 1 全帧 0 像素** → `--mask-class 15`
  与 person 类不对应（person 在 VOC 中是 15 吗？实测 15 是"人/家具"混合的子集，稀疏）。
- 命中 class15 的帧/像素：f3_office **1160/2585 帧、4080 万 px**（真在掩）；
  f3_st_rpy **仅 31/820 帧、10.7 万 px**；f3_wk_rpy **86/910 帧、9.2 万 px**。
- f3_st_rpy 的 `masked_px_skipped=0` = **stride20 采样恰好错过极稀疏的 person 帧** → 掩码分支事实上无操作。
- **但有掩码的 f3_office 也异常**（2M px 正确排除仍 39cm）→ 掩码不是主因（与 note 线索 2 一致）。
  掩码稀疏是**次因**，只放大 rpy 两序列的残差（见"残差"）。

### 第 3 步（depth_scale 与融合深度中位）— 已完成

| 序列 | distorted | depth_scale | depth 中位 | p95 | p99 | max | **>5m 占比** |
|---|---|---|---|---|---|---|---|
| f3_office | **False** | 5000 | 1.56 | 5.13 | 7.83 | 9.87 | **5.1%** |
| f3_st_rpy | **False** | 5000 | 2.48 | 7.83 | 9.33 | 9.87 | **12.7%** |
| f3_wk_rpy | **False** | 5000 | 2.60 | 8.02 | 9.33 | 9.87 | **16.2%** |
| f1_room | True | 5000 | 1.40 | 2.91 | 3.49 | 8.39 | 0.4% |
| f1_desk2 | True | 5000 | 1.07 | 2.36 | 2.91 | 4.07 | 0.0% |
| moving | True | 5000 | 2.06 | 3.06 | 3.30 | 3.90 | 0.0% |
| **Bonn 7 全部** | — | 5000 | 2.4–3.0 | 3.1–3.9 | 3.3–5.3 | 3.9–6.75 | **0.0%**（pt2 0.13%） |

- `depth_scale` 三 f3 与 f1 完全一致（5000）→ **不是 depth_scale 问题**。
- **决定性**：`>5m 占比` 与异常完全同序——f3 三序列 5–16%，其余 0%；**5m 裁剪恰卡在 f3 分布尾部**。

## depth-clip 对照实验（决定性）

同一 4 个 run，仅改 `--max-depth`：

| max_depth | f3_st_rpy acc(med) | f3_wk_rpy acc(med) | f3_office acc(med) | ref 尺寸 |
|---|---|---|---|---|
| 5m（原协议） | 242.9 (297.8) | 185.5 (69.5) | 39.0 (1.84) | 6.8 m |
| 10m | **44.1** (14.0) | **37.0** (9.3) | **7.2** (1.86) | 12.6 m |
| 15m | 44.1 (14.0) | 37.0 (9.3) | 7.2 (1.86) | 12.6 m（饱和） |

→ **裁剪是主因**（10m 后饱和，因场景纵深 <10m）。f3_office 一步到位（acc 6.6cm，与 f1 同级）。

## 27 run 全批重跑（`max_depth=10`，`geom_selfconsist_r34_f3_md10.json`）

| 序列 | n | acc 中位 @md5 | acc 中位 @md10 | comp 中位 @md10 | 判定 |
|---|---|---|---|---|---|
| f3_office | 9 | 42.68 | **6.57** | 6.9 | ✅ **可用**（与 f1 同级） |
| f3_st_rpy | 9 | 233.95 | **46.54** | 5.8 | ⚠ 大幅改善仍偏高 → **诊断用** |
| f3_wk_rpy | 9 | 215.57 | **42.63** | 12.3 | ⚠ 大幅改善仍偏高 → **诊断用** |

- f3_office 三臂 acc 中位 6.0–7.2cm，与 f1_room（6.4）同级 → **完全可用**。
- f3_st_rpy/f3_wk_rpy 仍有残差（median 8–16cm、>1m 占比 11–23%）——这是**独立于裁剪的第二个现象**。

## 残差（st_rpy/wk_rpy 仍偏高）的初步判断 — 未定论

裁剪修好主因后，rpy 两序列残差**逐 run 稳定**（非随机噪声），候选解释（按可能性排序）：
1. **rec 真含远场 floaters**（旋转视角 rpy 序列长、覆盖大，地图边缘松）；
2. **动态掩码稀疏**（class15 只覆盖 31/86 帧）→ 运动的人留在参考云/被 rec 拟合，双向污染；
3. **深度饱和**：三 f3 序列 depth max 都恰为 9.87m（= depth_scale 截断），远处像素是无效值带。

**建议（下一会话，若要用 rpy 两序列）**：对 st_rpy/wk_rpy 做"掩码敏感性"探针
（`--no-mask` vs 用 MaskRCNN person 重做掩码），并对 rec 做 1%/99% 分位裁剪后重算。
**在此之前，f3_st_rpy/f3_wk_rpy 的 acc/F 列仅作诊断，不得入表。**

## 列可用性裁决

| 列 | f3_office | f3_st_rpy | f3_wk_rpy | 其余（f1/f2/mob/Bonn） |
|---|---|---|---|---|
| acc（rec→GT） | ✅ 可用（@md10） | ⚠ 仅诊断 | ⚠ 仅诊断 | ✅ 可用 |
| completion | ✅ | ✅ | ✅ | ✅ |
| precision/recall/F | ✅ | ⚠ 仅诊断 | ⚠ 仅诊断 | ✅ |

- **协议修正**：`geom_selfconsist.py` 默认 `--max-depth` 建议**按序列设**（深场景 ≥10m，
  或做成"取 depth p99 自动定"）；Bonn 用 5m 无碍（0% 超限）。**本次不改默认值**
  （避免重跑已收口的 84 run 结论），仅在文档声明。
- **对已收口结论的影响**：**无**。Bonn 7 序列 0% >5m，R33（84 run）与 R34（54 run）
  的跨臂判断、K5/K6 判据均不受本次发现影响。

## 证据文件

- `diag_f3_geom.json` — 本地：6 序列掩码类别/标定/深度分位 + R34 几何读数汇总
- `diag_f3_probe_md5.json` — 远程探针：rec/ref 范围、scale ratio、robust NN（md5）
- `diag_f3_probe_scale_sweep.json` — 远程：scale sweep 曲线（证明非尺度问题）
- `geom_selfconsist_r34_f3_md10.json` — 27 run 重跑结果（md10 + robust 列）
- 远程原始日志：`/home/jiangwenheng/monogs_jobs_20260918/logs/gsc_r34.out`（旧）、
  本次 `/tmp/gsc_f3_md10.out`（远程，临时）
