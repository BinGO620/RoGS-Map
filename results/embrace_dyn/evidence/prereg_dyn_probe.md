# 预注册：embrace_dyn 建图/渲染侧生死筛（dyn_probe）

> **账本登记（2026-09-25 追补，D2-015 同例；原文零改动）**：本预注册属账本设立前的文书，决策留痕见 `NOTES.md` 实验清单与 git 历史；本轮由 health_check H5 扩表（`prereg_*` 纳入覆盖面）后检出为“未挂账本号”，按机制登记补入本指针，不追改正文。

**落盘时间**：2026-09-19（**在任何渲染指标被计算之前**——`materials` 阶段只产出内容判据：
掩码面积与残影盘点，不含 dyn_psnr/depth-L1 等结果指标）
**实验 ID**：`embrace_dyn`
**性质**：**离线探针（screen）**。单序列、单 seed、离线指标、无训练；
**结论不得作为论文数字**，只用于裁定方向生死与论文定位。晋级（≥2 序列 + held-out + 3 seed）
须另立预注册并过关卡③。

---

## 1. 问题（要回答的三个数）

现行系统是"反动态"范式（`combined_prune/method.yaml`：`SemanticMask.mask_mapping: true`
且 `mask_insertion: true`）⇒ 动态像素既不进建图损失也不进插入。渲染面对照图
（`evidence/fig_render_compare_person_tracking2.png`）显示：动态物体**要么消失、要么留残影**。

**问题 P**：若把动态物体"建出来"（而不是抹掉），建图/渲染面的数字能变好多少？运动建模是否必需？

## 2. 材料检查（跑前已完成，内容判据）

- **掩码面积（7 序列，`materials_dyn_probe.json`）**：pt2 `dynamic_mask_gtmc` 中位覆盖 **3.0%**、
  83% 帧非零；crowd3 `seg_mask` 中位 **19.5%**（人群场景）；balloon/balloon2 2–3.5%；
  **pt1/pt2 的 `seg_mask` 几乎为空（中位 0.0%）⇒ pt 家族只能用 gtmc**。
- **冻结地图残影盘点（pt2 gate/baseline，投影 5.5万/8.4万高斯）**：
  投影进掩码的点 **12–13%**（多为人物身后的背景），但**真正挡在 GT 表面之前**（残影候选）
  仅 **2–1016 点/帧**（均值 83(gate)/157(baseline)，< 地图 0.2%）。
  ⇒ **交接笔记中"只对掩码内已有高斯拟合形变"的最小形式在这张地图上无料可做**，
  必须以"从观测新建"为最小形式（本探针的 P2/P4 臂）。

## 3. 序列与地图（锁定）

| 项 | 值 |
|---|---|
| 序列 | `person_tracking2`（单人走动 + 相机环绕；掩码覆盖够大且已验证） |
| 主地图 | `r33_rebase_gate_person_tracking2_seed0`（部署形态；PLY=`final_after_opt`，55,174 高斯） |
| 鲁棒地图 | `r33_rebase_baseline_person_tracking2_seed0`（论文 1 栈；84,162 高斯） |
| 掩码 | `dynamic_mask_gtmc`（冻结、方法无关；三级匹配 depth stem → RGB stem → 最近邻 ts） |
| 位姿 | 该 run 的 `plot/trj_full_final.json` 的 `trj_est`（C2W）；渲染用其逆 |

**评估帧（内容判据锁定，不看任何结果指标）**：掩码覆盖 ≥ 非零帧中位数（3.44%）的帧中，
按帧序等距取 16 帧：

```
[2, 93, 122, 141, 178, 197, 243, 282, 309, 329, 347, 398, 421, 439, 512, 561]
```
**烘焙参考帧 t0 = 309**（所选帧中掩码覆盖最大者，cov=0.362）。

## 4. 四臂定义（同一冻结地图、同位姿、同帧 ⇒ **配对比较**，无 seed 噪声）

| 臂 | 定义 | 回答 |
|---|---|---|
| **P1 erase** | 冻结地图原样渲染（现状） | 反动态范式的代价 |
| **P2 逐帧瞬态插入** | 用**该帧自身**的 掩码∧有效深度 像素反投影建瞬态基元 + 局部拟合（预算见 §5） | 该族机制在我们栈上的**天花板** |
| **P4 烘焙** | 只在 t0 插入并拟合（同预算），之后**冻结**渲染全部帧 | 朴素做法（插一次不动）的鬼影代价 |
| **C− 错位对照** | P2 拟合结果沿**相机系横向**平移 0.30m 后渲染（**拟合之后**施加，拟合无机会纠正） | **仪器判别力自检**（阴性对照） |

**插入约定（不得手调）**：沿用仓库自身的 `GaussianModel._gaussians_from_points`
（KNN 尺度 + `Dataset.point_size=0.01` + RGB2SH + 反 sigmoid(0.5) 不透明度）；
掩码像素按 **stride=3** 下采样（所有臂同值）。

## 5. 拟合预算与超参（所有臂相同，锁定）

`fit_iters=300`；Adam 分组学习率：`xyz 5e-4 / log_scale 5e-3 / rot 1e-3 / opa 5e-2 / dc 5e-3`；
损失 = **掩码内 RGB L1 + 0.1 × 掩码内深度 L1(m)**。种子固定 0。
落盘证据（DISCIPLINE #9 生效验证）：每帧记录 `loss_first/loss_last/opa_mean_before/after`。

## 6. 指标口径（DISCIPLINE #12）

| 指标 | 定义 | 参考协议 |
|---|---|---|
| `dyn_psnr` (dB) | 掩码 ∧ 有效 GT 深度 像素上的 PSNR（`utils/static_eval.masked_psnr`） | **DynaGSLAM 的 DynaPSNR 协议**的我们实现（arXiv 2503.11979："PSNR only for dynamic objects within 2D motion masks"）；差异：我们额外要求 GT 深度有效 |
| `dyn_dl1_cm` (**主判据**) | 掩码内的**惩罚式**深度 L1（洞按 d_max=50cm 计罚） | 与项目 P-A 同函数 `penalized_depth_l1_cm` |
| `dyn_cov` | 掩码内渲染覆盖率（不透明度 ≥ 0.5） | `static_coverage`（同函数换掩码） |
| `full_psnr` (dB) | 全图 PSNR（`gt_image>0` 像素） | 与 `render_compare.py` 完全同口径 |
| `static_psnr` | 静态区 PSNR（`M_static` = 有效深度 ∧ ¬动态） | `static_background_metrics`（同源） |
| `ghost_excess_cm` | vacated 区对比残影 | `vacated_contrast_metrics`（同源） |
| `n_dyn` | 插入基元数（成本） | — |

**已声明的局限**：① P2 用被评估帧自身的观测建物体 ⇒ **构造性乐观上限**，不是可部署数字；
② 掩码用离线冻结 gtmc（在线为 MaskRCNN），差异未量化；③ pt2 的 ATE≈12cm，位姿误差进入渲染
误差——但**所有臂共用同一位姿**，配对差分即隔离动态内容贡献。

## 7. 判据（跑前锁定；全部用均值，配对同帧）

1. **天花板（P2 vs P1）**：`mean_dyn_dl1` 比值 **≤ 0.70** 且 `mean_dyn_psnr` 差 **≥ +2.0 dB**
2. **运动必要性（P4 vs P2，仅 |frame − t0| ≥ 50 的帧）**：`mean_dyn_dl1(P4) / mean_dyn_dl1(P2)` **≥ 1.30**
   （没有这条 ⇒ "插进去冻住"就够 ⇒ 4D/瞬态运动机制无卖点）
3. **无伤（P2 vs P1）**：`|Δ static_psnr| ≤ 0.25 dB` 且 `full_psnr` 不降 > 0.25 dB
4. **成本**：`mean_n_dyn ≤ 50% × n_static`
5. **仪器有效（阴性对照）**：`mean_dyn_dl1(C−) / mean_dyn_dl1(P2)` **≥ 1.15**；
   若不满足 ⇒ **判仪器失效（不是 NO-GO）**，先修工具再判
6. **阳性对照**：P1 的 `full_psnr` 必须与既有 `render_compare` 结果在同一帧上一致
   （同口径不同实现的一致性检验；允许因采样帧不同而只做区间核对）

**出局规则**：
- 判据 1 不满足 ⇒ **NO-GO**（该族在可知范围内无翻盘空间；如实入负结果，并写明改善路径已穷尽的证据）
- 判据 1 满足但判据 2 不满足 ⇒ **PARTIAL**（机制必要性不成立，需用户拍板是否够 CVM）
- 1/2/3/4 全满足 ⇒ **GO**（进入机制实现阶段：代码保护例外流程①-⑤ + 3090 正式批）
- 5/6 不满足 ⇒ 探针无效，先修工具，**不得**据此下任何方向结论

## 8. 描述性产出（不作判据）

- P4 vs P1：朴素保留动态是否**反而更差**（鬼影代价的量化）；
- P2 的 `n_dyn` 占地图比例与 `full_psnr` 变化（成本/收益比）；
- baseline 地图上的同套臂（鲁棒性：结论不得只在 gate 臂成立）。

## 9. 关联与分析后纪律

- 分析器：`cmd_render` 自带聚合；结果写 `results/embrace_dyn/evidence/dyn_probe_results.json`，
  报告写 `.md`（由脚本或人工从 JSON 生成，**不得手改数字**）。
- 判决落盘（`verdict.md`/`manifest.json`）前须过 **slam-critic 关卡①**（独立子智能体）。
- 本探针产物只能作**筛选证据**：任何"保留动态更好"的主张进论文前须
  ① 扩到 ≥2 序列（含一条非 pt 序列）② 机制版本实现（非离线 oracle 式插入）③ 过关卡②/③。
