# 方案 B（自洽几何）R34 补充批 — 结果与异常（2026-09-18）

> 远程 CPU（nice 19）跑完 54/54：`evidence/geom_selfconsist_r34.json`。
> 逐 run 读数在 `monogs_jobs_20260918/logs/gsc_r34.out`（远程）。

## 结果分档（acc = rec→GT 均值，cm）

| 序列 | n | acc 中位 | acc max | F 中位 | 掩码源 | 判定 |
|---|---|---|---|---|---|---|
| f1_room | 9 | 6.42 | 7.01 | 69.7 | None（无掩码） | ✅ 正常 |
| f1_desk2 | 9 | 5.47 | 7.11 | 75.8 | None | ✅ 正常 |
| moving_obstructing_box | 9 | 4.62 | 5.77 | 64.4 | gtmc（411k px 排除） | ✅ 正常 |
| f3_office | 9 | **42.68** | 48.71 | 73.8 | seg_mask（2.0M px 排除） | ⚠ 偏高 |
| f3_st_rpy | 9 | **233.95** | 252.58 | 37.5 | seg_mask（**0 px 排除**） | ❌ 异常 |
| f3_wk_rpy | 9 | **215.57** | 236.99 | 33.8 | seg_mask（0 px 排除） | ❌ 异常 |

## 异常特征与初步线索（**未定论，下一会话须诊断**）

- 异常模式 = **comp（GT→rec）≈5cm 正常，但 acc（rec→GT）爆炸** →
  "GT 云被 rec 全包住、但 rec 有大量点远离 GT 云"的形态（尺度不匹配或
  rec 含远场 floaters 的典型签名）。
- 线索 1：`masked_px_skipped=0` 的 f3_st_rpy/f3_wk_rpy —— **class 15 在这两个
  TUM 序列的 seg_mask 中可能不存在**（早前抽样：sitting_rpy 13 帧无 class 15；
  walking_rpy 仅 1/13 帧 39px）→ 掩码分支事实上等于"全量融合"。但 f1 序列
  同样无掩码且正常（5-7cm）⇒ 掩码不是唯一解释。
- 线索 2：f3_office（有掩码、2M px 排除）也偏高（42cm）⇒ 更像 f3 家族的系统
  性差异（内参/深度尺度/云覆盖范围），需和 f1、mob 做同 run 对拍定位。
- **使用前必须先诊断**：当前 f1_room/f1_desk2/mob 的数字可用；
  f3_office/f3_st_rpy/f3_wk_rpy 的 acc 列不可用（F 列也受影响，因 P@5 低）。

## 诊断建议（给下一会话）

> **状态：已诊断（2026-09-18 下午）** → 见 `geom_selfconsist_r34_diagnosis.md`。
> 根因 = 参考云 `max_depth=5m` 裁剪卡在深场景（f3 depth p95 7–8m）尾部；
> `max_depth=10` 重跑后 **f3_office 完全可用**（acc 42→6.6cm，与 f1 同级），
> **f3_st_rpy/f3_wk_rpy 大幅改善但仍偏高**（234→46、216→43），仅作诊断。
> **Bonn 7 序列 0% >5m → R33/R34 已收口结论不受影响。**

原始 3 步建议（已完成，留档）：

1. 拿 1 个 f3_st_rpy run：`read_gaussian_xyz` 看 rec 坐标范围 vs 融合云范围（比值）；
2. 检查 TUM f3 seg_mask 的类别编码（`np.unique` 全帧统计，确认 person 类 id）；
3. 检查 f3 的 `depth_scale` 与融合深度中位数（对比 f1）。
