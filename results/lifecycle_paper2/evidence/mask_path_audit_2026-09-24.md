# 掩码路径代码审计（D2-009 Phase 0b；2026-09-24；只读）

> 问题（用户疑点）：掩码召回 0.995，人像素已被排除，**残影到底从哪来**？
> 答案：三处硬决策点**全部掩码合规**——残影不是"漏进来的人内容"。
> 与普查的颜色归属（基元色更贴背景、离人色远）互相印证。

## 1. 插图侧（insertion）

- `utils/slam_frontend.py:495-540`：`_apply_semantic_insertion_gate` ——
  `SemanticMask.mask_insertion: true` 时把当前帧**人物掩码像素的深度置 0**，
  由 `create_pcd_from_image_and_depth(project_valid_depth_only=True)` 丢弃 ⇒
  **人物像素不产生新基元**。复用 tracking 已算的缓存掩码（无额外检测器开销）。
- 生效条件核实：`configs/experiments/combined_prune/method.yaml:23` = `mask_insertion: true`，
  `mask_mapping: true`（论文 1 栈默认开）。

## 2. 建图损失侧（mapping loss）

- `utils/slam_utils.py:606-624` → `get_loss_mapping_rgbd(..., dynamic_mask=...)`：
  `mask_mapping: true` 时用**硬掩码**排除（`utils/mapping_weight.py:56`）。
- 柔性替代实现存在但**未启用**：`SemanticMask.soft_mapping`（soft floor）与
  `Mapping.mapping_ema`（逐像素滞后残差 EMA 权重）——`mapping_weight.py:44-110`
  明确互为 treatment/control；本栈两者皆 off ⇒ 建图是"硬掩码"形态（硬决策点之一）。

## 3. 延迟提交侧（deferred commit）

- `utils/deferred_commit.py:208/223/234`：`process_initial_keyframe` /
  `observe_keyframe` 均接收 `dynamic_mask` 并做 `_mask_numpy` 处理 ⇒ 掩码感知。

## 4. 审计结论

| 硬决策点 | 形态 | 掩码合规 |
|---|---|---|
| 插图 | 硬（掩码像素零化丢弃） | ✅ |
| 建图损失 | 硬（mask_mapping 排除） | ✅ |
| 延迟提交 | 掩码感知 | ✅ |
| 删除（reset/carve/gate/occ/seam） | 硬门（五批实验对象） | 判据层已由普查判定错靶（见 ghost_census） |

⇒ **残影 ≠ 漏入的人内容**。走廊区域的误差来自"占据期该区域被三处硬决策排除在
数据与优化之外"这一结构性事实（欠观测），而非某批基元"错了"。

## 5. 遗留与风险

- 未逐行核 `create_pcd_from_image_and_depth` 的 `project_valid_depth_only` 是否
  对所有插入路径（含 fill/transient 的 `insert_candidates_cam`）一致生效——
  本审计覆盖主干路径；fill 路径的深度来自 `obs[vv,uu]`（传感器深度）不经该零化，
  但 fill 只在 exit_fill 且以 vacated 像素为对象（脱离掩码语义）。
- 若后续采用"时序并集掩码"（把过去若干帧的掩码并集也用于插图排除），
  需注意其与 `mask_stability_ledger`（world-static release）的交互——两者都改写
  `viewpoint.dynamic_mask`，必须显式定优先级（审计发现，未改动）。
