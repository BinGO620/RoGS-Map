# 掩码体系重构（v2）记录 — 2026-09-21/22

**性质**：D1 级（工具/仪器重构 + 判据机械重应用）；用户 2026-09-21 明确指示"重构、彻底解决、
重跑在所不惜"。**本文件是重构的权威说明**；历史读数不删改（保留 `_dense`/`_seg12dense` 目录作审计痕迹）。

## 1. 旧体系坏在哪（三源、两约定、三处静默默认）

| 来源 | 是什么 | 问题 |
|---|---|---|
| `dynamic_mask_gtmc/` | 本仓 GT 位姿"运动一致性"掩码 | **实测失效**：6 序列移动者召回 0.10–0.39，30 帧并集 51–96% 为静态结构误标 |
| `seg_mask/` | **项目作者用 OneFormer(ADE20K-150) 生成**（非数据集自带）；person = **cls12**（0 起编号） | 与下一条**同名不同口径** |
| `seg_mask/`（crowd3） | 本仓 MaskRCNN 生成，VOC 口径 person = **15** | 同一目录名混装两套类号 |
| 运行期 MaskRCNN | 方法输入（跟踪/建图降权、L1b 门控） | 本身正确（对人物区召回 0.995），但与评估链混用会**循环** |

三处静默默认把上述问题放大成**整批指标测错区域**：
`render_compare --mask-class` 默认 15、`--mask-subdir auto` 优先 gtmc、
`combined_prune/method.yaml:47` 的 `static_bg_mask_subdir: dynamic_mask_gtmc`。
（事故全貌：`l3_instrument_rescore_2026-09-21.md`）

## 2. 新体系（只有两条链，名字与用途分开）

```
① 方法输入（在线）   utils/semantic_mask.compute_semantic_dynamic_mask（MaskRCNN）
                     方法自己用；不是评估参照。

② 评估参照（离线冻结） <seq>/dynamic_mask/<depth_stem>.png
                     uint8 0=静态 / 255=动态，**没有类号**，按 depth stem
                     由 scripts/build_dynamic_mask.py 构建（唯一 builder）
                     解析入口 utils/dynamic_mask_spec.resolve_eval_mask_dir（**默认拒**）
```

- **消费方彻底没有类号**（v1 曾试图"把类号登记得更仔细"，v2 直接把类号删掉）。
- **默认拒**：缺 `dynamic_mask/` ⇒ 报错，**不回落**到 seg_mask/gtmc。历史来源须显式
  `allow_legacy=True`（render_compare 的 `--allow-legacy-mask`），产物记 `mask_validity=legacy`。
- 产物一律记 `mask_source` / `mask_kind` / `mask_class` / `mask_validity`，使"用错口径"可自动检查。

### 构建器内置三门验证（不过则不写盘、非零退出；逻辑抽为纯函数 `evaluate_gates`，有单测）

> ⚠️ **2026-09-22 更新（v2.1）：独立验证参照由 OneFormer 改为 deeplabv3，OneFormer 退出本链路。**
> deeplabv3（VOC person）与 OneFormer（ADE20K cls12）实测一致 recall 0.88–0.96 / precision 0.93–0.94，
> 且 (a) 在本仓环境内（torchvision 自带权重），(b) 全 9 序列可用（含 crowd3——它的 OneFormer 参照
> 已被本仓 2026-09-18 的构建覆盖），(c) 与本方法用的 MaskRCNN **不同架构 + 不同训练集**，
> 独立性不变。`seg_mask/` 现在只是**项目作者自己的 DGS-SLAM 复现资产**，本 builder 默认不读它
>（`--ref-source oneformer` 可选）。掩码内容不变（两侧 sha256 与 v2.0 逐字一致——参照只影响验证门，不影响掩码）。

1. **独立参照一致性**：vs deeplabv3 person(VOC 15) 的逐帧召回均值 ≥ 0.80
2. **炸裂护栏（比率判据）**：有参照帧用 `area/ref_matched ≤ 3.0`（**形态对齐**：参照也按同一
   dilate_px 膨胀后比——否则"膨胀掩码/紧参照"系统性抬高比值）且**超界帧占比 ≤ 2%**；
   无参照帧退化为绝对占比 < 0.90
3. **空掩码率**：参照说有人而掩码为空的帧占比 ≤ 0.50

**门②的三轮定标史（每轮都是被自己的门误杀后用实测数据修的，教训见 NOTES 坑区）**：
① 绝对面积 ≤0.5 → 误杀密集人群（crowd 参照本身占 57% 画面、precision 0.84–0.90）；
② 改相对比值 ≤1.5 → 误杀单帧 1.54 的正常膨胀 → 实测 8 序列定标放宽到 3.0；
③ deeplabv3 参照下又误杀 → **形态对齐**（参照同膨胀）+ 逐帧核实超界帧是**参照塌陷/检测器过渡差异**
（那些帧 recall=1.0）→ **改比率判据 ≤2%**。判据本身的教训：**验证门必须先用实测分布定标、
再对离群帧鲁棒（用比率不用单帧硬门）**。

## 3. 已建成（9 序列 / 6447 帧，均通过验证）

| 序列 | 帧数 | 召回 vs OneFormer | area/ref | 空掩码率 | sha256(前 10) |
|---|---|---|---|---|---|
| person_tracking | 580 | 0.9949 | 1.54 | 0.000 | eea05b2a4a |
| person_tracking2 | 567 | 0.9907 | 1.74 | 0.000 | 553d16b0cd |
| crowd | 928 | 0.9766 | 1.73 | 0.002 | a95095bab2 |
| crowd2 | 895 | 0.9818 | 2.37 | 0.005 | ed3fced54f |
| **crowd3** | 854 | **0.9867（v2.1 deeplabv3 参照）** | 0.67(绝对) | 0.000 | 3236e37f00 |
| balloon | 439 | 0.9782 | 1.91 | 0.006 | 81dce492c5 |
| balloon2 | 469 | 0.9893 | 2.13 | 0.000 | 262f1652bd |
| moving_nonobstructing_box | 778 | 0.9468 | 1.39 | 0.019 | 657ae217d8 |
| moving_nonobstructing_box2 | 937 | 0.9542 | 1.44 | 0.026 | 72f4d7ddf7 |

Manifest（含逐帧统计与 sha256）入仓：`results/lifecycle_paper2/dynamic_mask_manifests/`。
掩码 PNG 本体在数据集侧（`/mnt/app/datasets/Bonn/<seq>/dynamic_mask/`，与 gtmc/seg_mask 同处）。

## 4. 覆盖范围与已知缺口（**如实**）

- **覆盖 = 人物区域**。这对 pt/pt2/crowd/crowd2/crowd3 就是全部移动者；对 balloon 与 mvnobox
  序列，**气球/箱子不在掩码内**（它们是主要移动物）。后果：这些序列的 freshvac 语义 =
  **人物轨迹区的残影**，不是箱子/气球残影。
- 为什么覆盖不了（本次实测，两条路都堵）：
  * **语义**：COCO 只在个别帧把气球误检成 `sports ball`(0.84)、把箱子误检成 `book`(0.52–0.90)；
    OneFormer 的 ADE20K-150 亦无 balloon，box(cls40) 在实际掩码中**零出现**。
  * **流阈值**（`utils/flow_mask_baseline.py`）：Bonn 是**手持相机**，`|f_obs|` 被自运动主导——
    实测 flow-only 对人物召回仅 0.001–0.84、多出的区域大半远离人 ⇒ 不可用（除非做 GT 位姿补偿残差流）。
- ~~crowd3 无独立参照~~ → **v2.1 已解决**：参照换 deeplabv3 后 crowd3 实测召回 0.9867。
  （其 `seg_mask/` 仍疑似被本仓 2026-09-18 的构建覆盖过——该操作不可逆，正是新护栏要防的。）
- ~~OneFormer 环境不可用~~ → **不再阻塞**：本链路已不依赖 OneFormer（`seg_mask/` 归还为
  项目作者自己的 DGS-SLAM 资产，保留/删除均不影响我们）。

## 5. 退场与保留

| 来源 | 处置 |
|---|---|
| `dynamic_mask_gtmc/` | **退出评估链**（文件保留；消费方默认拒）。历史 config 若显式引用，重跑前须换源 |
| `seg_mask/` | **降级为只读验证参照**（不删——它是目前唯一独立人物参照；且用户授权删除但删除不可逆，按保守默认保留）。所有消费方不再默认读它 |
| `build_person_seg_mask.py` | 保留为工具，默认输出改 `dynamic_mask_person/`，加覆盖护栏（双锁） |
| 历史渲染目录 `render_*_dense/`、`render_*_seg12dense/` | 保留作审计痕迹；新读数在 `render_*_canon/` |

## 6. 重跑与重评（本轮）

- **canonical 重渲染**：`scripts/lifecycle_paper2/rerender_all_canon.sh` —— L3 全 9 序列 ×
  {off,exit} × 3 seed（54）+ {mvnobox,balloon2} exit_fill ×3（6）+ L1b gate ×3 = **63 run**，
  帧集/护栏/PLY 与原渲染一字不差，**只换掩码源**。产出 `render_<tag>_canon/`。
- **重评**：`l3_paired_judge.py --render-tpl "render_{tag}_canon"`；
  `l1b_gate_judge.py --render-suffix _canon`。
- 预期影响：人群族（pt/pt2/crowd/crowd2/crowd3）读数与 `_seg12dense` 近似（同一人物区域口径，
  差异来自 MaskRCNN vs OneFormer 的轮廓与膨胀）；**box/balloon 族首次获得有效（人物口径）读数**，
  悬置状态解除——但**其主张随之限定为人物轨迹区**。

## 7. 待办（不阻塞本轮）

1. box/balloon 的**非人物移动者**覆盖（方案：GT 位姿补偿的残差流，或其等价物）——须独立验证。
2. ~~crowd3 的独立参照~~（v2.1 已解决，deeplabv3 参照）。
3. `diag_f3_geom.py` 等历史审计脚本已加废弃提示；`geom_selfconsist.py`/`diag_f3_probe.py`/`dyn_probe.py`
   的 auto 已切 canonical。


## 8. 跨机可复现性（如实登记）

掩码由 MaskRCNN 推理产出，**跨机不是逐位可复现**（GPU 浮点非确定性在阈值边界翻转像素）。
实测（person_tracking 抽 10 帧，本地 2060 vs 远程 3090）：**平均 4.2 px/帧、最大 22 px**
（占画幅 0.0072%）⇒ 两侧 `sha256_over_masks` 不同属预期。

- **参考集 = 远程 `/mnt/app/datasets/Bonn/<seq>/dynamic_mask/`**（所有训练与渲染都在远程，
  论文/判决引用的读数全部基于它）；其 sha256 记录在 `dynamic_mask_manifests/*.json`。
- 本地 `/data/Datasets/Bonn/...` 另存一份供本地分析；**同序列 sha 会略有不同属已知、已量化**，不是构建失败。
- 两侧 manifest（`rgb.txt/depth.txt/associations.txt/groundtruth.txt`）**md5 完全一致**（已核）；
  本地 `rgb/` 多 10 个**未被 manifest 引用**的散帧，不影响构建（builder 迭代 association）。
