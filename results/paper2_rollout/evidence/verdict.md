# paper2_rollout 裁决（verdict）

> 实验：拉通扩大验证批（held-out 通用性面板，20 序列）
> 日期：2026-09-09 ~ 09-12；远程 3090×2
> 状态：定性完成（19/20 done；static 因官方 depth 缺口暂缺）

## 判据（预注册）

- 通用性主张：gate 臂在 held-out 序列上的 ATE 与标准集同量级、无系统性崩坏
- 5cm 线：动态序列过线率作为方法适用边界的描述统计（非主张）
- 失败分类（DISCIPLINE #11）：2-seed 起步抽查，区分不确定性失败 vs 机制性失效

## 结果

- **面板（seed0，gate）**：19/20 done，11/19 过 5cm，动态 5/10（PANEL.md）
- **3-seed 修正**：真 ✗ = 6（f3_st_rpy/f3_wk_rpy 单 seed 误判翻正）
- **机制级失效**：f1_room（SWBA 归因）、balloon_tracking2 /
  moving_obstructing_box（Combined-Prune 共性）、balloon_tracking /
  f2_person（略超线）
- **f3_st_hf**：双峰悬崖，干净抽样率 2/3，随机分岔（同 config
  {33.53,34.19,3.35}）

## 结论

1. **通用性成立范围**：静态/物体搬运/多数 TUM 动态过线；动态长序列与
   f1_room 未过 = 方法边界，如实进 Discussion，**不作贡献**。
2. **MonoGS 崩坏修复对照**：5-12× 系统修复（MonoGS 28-63cm vs 我方
   2.85-12.03cm），f3_st_hf 12× 反例同表呈现。
3. **f3_st_hf 悬崖**：单 seed 排序不可用；确定性分量由 mask_fix_iter
   账本处理（但账本在完整 gate 臂机制性有害，见
   results/mask_fix_iter/evidence/verdict_c4.md 末节——本批 f3_st_hf
   gate 34.68 即含该交互）。

## 遗留

- static 序列官方 depth 缺口（10000/10906），面板标注暂缺
- f3_st_hf 剩余 25% 悬崖率根因（确定性分量已定位为 mask_insertion 开局崩坏）
