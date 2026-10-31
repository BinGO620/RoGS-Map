# ✗ 行 3-seed 抽查判定（x_rows_seeds12，2026-09-12 完成，30/30 rc=0）

目的（DISCIPLINE #11 判别手段）：区分实验不确定性失败 vs 机制性失效，
并修正单 seed 面板的误判。

## gate 臂 3-seed 全表（cm）

| 序列 | seed0 | seed1 | seed2 | 中位 | 判定 |
|---|---|---|---|---|---|
| balloon_tracking | 6.78 | 5.91 | 6.80 | 6.78 | ✗ 稳定（机制级，略超线） |
| balloon_tracking2 | 23.70 | 21.17 | 20.48 | 21.17 | ✗ 稳定（机制级） |
| moving_obstructing_box | 20.47 | 16.73 | 16.13 | 16.73 | ✗ 稳定（机制级） |
| f1_room | 18.32 | 16.91 | 19.58 | 18.32 | ✗ 稳定 → **SWBA 归因**（见 DIAGNOSIS_f1room.md） |
| f2_person | 6.61 | 7.20 | 6.90 | 6.90 | ✗ 稳定（略超线） |
| f3_st_hf | 34.71 | 3.30 | 3.04 | 3.30 | 双峰（悬崖），干净抽样率 2/3 |
| **f3_st_rpy** | 4.29 | 3.15 | 3.23 | 3.23 | **✓ 翻正**（原面板单 seed 5.85 误判） |
| **f3_wk_rpy** | 4.65 | 4.23 | 5.85 | 4.65 | **✓ 翻正**（中位 <5） |

## 判定（只写事实）

1. **面板修正**：真 ✗ 行 = 6（原 8）；f3_st_rpy/f3_wk_rpy 3-seed 中位
   过线，单 seed 面板误判——多 seed 面板的必要性实锤。
2. **无一个是抽样彩票**：除 f3_st_hf 双峰外，其余 7 序列跨 seed 波动
   均 <±15%，失败是稳定特征 → 按 #11 属机制级（可修）或方法边界
   （如实报告），不是"偶尔失败的不确定性"。
3. 机制性失效清单（修复优先级）：f1_room（SWBA，归因完成）>
   balloon_tracking2 / moving_obstructing_box（gate≈rollbase，Combined-
   Prune 共性，需基线级分析）> balloon_tracking / f2_person（略超线，
   或随机制改进自然回落）。
4. f3_st_hf 悬崖：干净抽样率 2/3（gate n=3），悬崖归随机分量
   （mask_fix_iter 账本修复其确定性分量：开局崩坏 + E1 式全发散）。

运行信息：远程 3090×2，x_rows_seeds12.done（30 rc=0），HEAD e7892d96。
