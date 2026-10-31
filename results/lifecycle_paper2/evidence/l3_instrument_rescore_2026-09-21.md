# L3 仪器修正案 2 + 重评（2026-09-21，阶段 0 预检产物）

**性质**：仪器修正 + 判据机械重应用（DECISIONS §2 R1：判据不变，换有效仪器源重算）。
**触发**：L1b gate 立项的阶段 0 预检（运行期掩码召回审计）发现参照掩码病态 → 追查发现
L3 主判据仪器（freshvac 的冻结动态掩码）在 8/9 序列上无效。
**本文件不改任何预注册判据**；旧读数不删改（`verdict_L3.md` 原文保留，头部已加带日期指针）。

## 1. 发现链（全部工件可回查）

1. **运行期掩码召回审计**（`evidence/l1b_mask_recall_audit.json`；脚本 `scripts/02_analysis/l3b_mask_recall_audit.py`）：
   对 person_tracking 的 KF 网格（`evidence/l1b_audit_kf_grid.json`，exit 三 seed alpha-ledger KF 并集 153 帧）
   离线重算运行期 MaskRCNN 掩码（`compute_semantic_dynamic_mask`，SemanticMask 块逐字段取自
   `configs/experiments/combined_prune/method.yaml`），对 gtmc 冻结人物区域算召回：
   **mean_recall=0.110、median=0.0**——病态。
2. **三方交叉仲裁**证明**错的是 gtmc 参照，不是运行期掩码**：
   - **shipped `seg_mask/`（2026-06-28 已存在于 /data/Datasets/Bonn，生成方早于本仓；
     `build_person_seg_mask.py` 只建过 crowd3）是 ADE20K 式 150 类 0 起语义分割，
     person = cls12**（ADE20K 0 起：12=person；经验验证：crowd/crowd2/pt 上 cls12 与
     MaskRCNN person 检出重叠 0.98–1.00，`scripts/02_analysis/l3_frozen_mask_audit.py`）。
   - 运行期 MaskRCNN 对 **cls12 人物区域的召回 = 0.995**（61/61 人在场 KF，min 0.980，
     max 1.000；帧 0–305 人在场、306+ 离场——与 gtmc 306 后空掩码、MaskRCNN 306 后零检出一致）。
   - frame 5 反例定性：gtmc 标右缘小团（≈4.9k px），而 MaskRCNN 0.9995 检出全身人形
     （box 250–361×9–425）与 cls12（29k px @(314,209)）与深度突出体（box 内 p10=1.73m vs
     场景中位 2.58m）三方一致——gtmc 漏检了人。
3. **gtmc 全序列失效**（`evidence/l3_frozen_mask_audit.json`，纯 CPU 只读审计，帧步 10）：
   对 6 条用过 gtmc 的序列，gtmc 对人物区域召回 0.12–0.39；30 帧并集与人物 30 帧扫掠区
   重叠仅 4–49%（主体=静态结构 FP，NOTES P9"误标背景家具"模式的规模化形态）；
   对近场移动者代理（人邻域 ∧ depth<0.8×中位）召回 0.10–0.34。pt 另有 5 帧半幅炸裂
   （gt_frac>0.25，最大 49% 画面）。
4. **crowd/crowd2 用错类**：L3 渲染 `--mask-class 15`（VOC 惯例默认），但其自带 seg_mask
   是 ADE20K 0 起编号——**15=table ≠ person**。crowd3 例外：其 seg_mask 是本仓
   MaskRCNN 生成（只有 0/15 两值，15=person 正确）。

## 2. 修正重渲染（判据/帧集/护栏一字不差，仅换掩码源）

- 脚本 `scripts/lifecycle_paper2/rerender_L3_seg12.sh`（远程 3090 单卡 cuda:0，
  `CUDA_DEVICE_ORDER=PCI_BUS_ID`；24/24 rc=0、n_frames 全 17，`l3_seg12_render.done`）。
- 仅对**有人专用掩码可用**的 4 条序列：person_tracking / person_tracking2 / crowd / crowd2，
  `--mask-subdir seg_mask --mask-class 12`。balloon/balloon2/mvnobox/mvnobox2 **不在本批**
  （气球/箱子无语义类，gtmc 又失效 ⇒ 读数悬置，见 §4）。
- 工件：`results/lifecycle_paper2/render_L3_<tag>_seg12dense/render_metrics.json`（24 个，已入仓）。
- 仪器语义自检（pt off s0）：有效 freshvac 帧 = 50–314 共 9 帧（=人在场窗口；支撑 20–53k px
  =人物新鲜轨迹），347+ 人已离场 ⇒ 窗口空 ⇒ None 不入均值——正是"新鲜腾空区"的预注册语义。
  同 seed 两臂支撑逐位相同（冻结掩码、臂无关）。

## 3. 重评数字（freshvac Δ(exit−off)，3-seed 配对；旧 = verdict_L3 附录 A）

| 序列 | 旧 Δ（旧仪器） | 旧判 | **新 Δ（cls12）** | 新逐 seed | 新判（同一判据） |
|---|---|---|---|---|---|
| person_tracking | −0.204 | ❌ 功效不足 | **−0.338** | −1.50 / +0.23 / +0.25 | ❌（1/3 负，\|mean\|<1.19） |
| person_tracking2 | −0.277 | ❌ 功效不足 | **−0.162** | +0.76 / −1.27 / +0.02 | ❌（1/3 负） |
| crowd | +0.548 | ❌ 方向不支持 | **+0.164** | −0.02 / −0.29 / +0.80 | ❌（1/3 负） |
| crowd2 | **−2.674** | ✅ PASS Tier2 | **−0.254** | −0.99 / +0.77 / −0.54 | ❌（1/3 负——**旧 PASS 为错类掩码伪影**） |
| crowd3 | +2.089 | ❌ | **+2.089（沿用，仪器本就正确）** | — | ❌（不变） |
| balloon / balloon2 / mvnobox / mvnobox2 | −2.4 / −2.6 / −1.2 / −1.4（全部 ✅） | — | **悬置**（无有效移动者掩码） | — | **读数失效待重建仪器** |

**核心结论**：
1. **有效仪器下，人群族 5 序列（pt/pt2/crowd/crowd2/crowd3）无一显示 exit 的 freshvac 效应**
   （|mean Δ| ≤ 0.34、符号混合）——与机制诊断（verdict_L3 §9：pt 的 carve 因 α 钉死从未触发，
   alpha_carve_total=0 ⇒ exit≈off）**自洽**：off 臂在人物轨迹区有真实残影（pt off = 3.96–5.01cm），
   exit 没有动它。
2. **box/balloon 族的 4 个旧 PASS 全部悬置**：其掩码支撑 = gtmc FP 闪烁并集（与移动者重叠
   4–49%），读数不测"移动者腾空区残影"。"box 族阶段性表述"（用户 2026-09-21 方向之一）
   的**事实基础已不成立**，须待有效移动者掩码重建后重评（气球/箱子无 ADE20K 语义类，
   cls40=box 在 mvnobox 掩码中零出现、cls75/33 均为家具——缺席测试：人不在场时仍在场）。
3. **不受影响的证据线**：ATE 约束门（无掩码参与）；机制计数器/α 账本（臂内工件，
   `tables/efficiency_raw.csv`）；§9 机制诊断（consolelog + 计数器）；off 臂全零负对照；
   60/60 rc=0 训练批次本身。

## 4. 影响面外溢（登记，逐项重审属后续工作）

| 受影响工件 | 用了什么 | 状态 |
|---|---|---|
| `verdict_L3.md` 附录 A freshvac 全表 | gtmc（6 序列）+ cls15（crowd/crowd2） | **§3 重评替代**；crowd3 行沿用 |
| `crowd_judgeability_confirm.md`（C 步）+ `verdict_L1.md` crowd2 行 | crowd2 seg_mask cls15（错类） | crowd2 可判性结论**失效**（"Δ 全负 mean −3.74"为错类伪影） |
| R33/R34 静态区/残影读数（static PSNR/ghost_excess，48+24 读数） | 同类掩码 | gtmc 序列的"static 区"≈全图（掩码近空）⇒ "static PSNR 中性"部分是伪影；ghost_excess 为 FP 区对比噪声。**"渲染不退化/残影弱正面"结论降级为未证** |
| 预注册门槛地板 1.19cm 的出处（balloon2 off 跨 seed sd，L1 期） | 旧 freshvac 仪器 | 数字来源已失效；作为**保守地板常数**沿用（新仪器 pt off sd=0.584 < 1.19，不改变任何门的取值），出处缺陷在此登记 |
| **L3 全部 60 run 的 `tables/mapping_raw.csv` `mask_type='static'` 行**（每 run 61 个 `static_*` 列） | `Results.static_bg_mask_subdir=dynamic_mask_gtmc`（`combined_prune/method.yaml:47`） | 同为 gtmc 口径 ⇒ **一并作废**（2026-09-21 补登记）。抽查：`L3_person_tracking_exit_s0` static_psnr=24.4603/116 帧、`L3_balloon_exit_s0` 23.7456/88 帧、`L3_crowd_exit_s0` 无 static 行（磁盘无 gtmc ⇒ 静默跳过，**不报错**）。该行是"跑完未读的 CSV 列"第 4 例的同族形态（NOTES 已记）。**L1b 批已显式 `static_bg_mask_subdir: null` 关闭该行**（prereg 修正案 2）。 |
| **运行期 P-A 路径的类别支持缺口** | `utils/eval_utils.py:763` 用 `load_frozen_mask`（>127 布尔） | 只支持 gtmc 的 0/255 图；把 `static_bg_mask_subdir` 指向 `seg_mask` 会得到"几乎全空、仅 128–149 类像素为真"的掩码——**静默错、不报错**。⇒ 若将来要让运行期 P-A 也吃类别掩码，须先补 `--mask-class` 等价支持（离线 `render_compare` 已支持）。 |
| **论文 1（MMM RoGS-SLAM 投稿版）** | pdftotext 全文核验（独立会话） | **正文无影响**：`vacated/excess/clean/static background/frozen mask/GT-pose/oracle` 均未出现；唯一表格为 ATE；§5.7 渲染读数为全图 PSNR/Depth-L1（论文自述 "PSNR is read as map self-consistency, never trajectory evidence"）；ghost 图为定性图；论文中的掩码是**在线 MaskRCNN**（Fig.6 干预=硬掩码 10→100 步）。⇒ **投稿版不需更正**；残留仅为上一条"未报告的 static 行"。 |
| **"12 = person" 的第二法独立验证** | 免模型免 GT、只读 PNG（独立会话） | cls12 bbox 高宽比中位 **2.81/1.33/2.08**（pt/crowd/crowd2）= 竖长剪影；cls15 为 **0.41/0.77/0.71** = 横宽矮块；三序列内最大标签值均 = **146** ⇒ 0 起 150 类集合（VOC-21 会封顶 20）。与 MaskRCNN 0.98–1.00 重叠**互为独立佐证**。 |
| **seg12 重评数字的独立重算** | 第二路会话独立计算 | pt −0.338 / pt2 −0.162 / crowd +0.164 / crowd2 −0.254 —— 与本文件 §3 **逐位吻合** ⇒ 该判决级重评现为**双次独立计算**。 |

## 5. 对 L1b（gate 立项）的含义（→ `prereg_L1b_gate.md` / D2 一页纸）

- **gate 的输入掩码无碍**：运行期 MaskRCNN 对人物区域召回 0.995（本文件 §1.2）。
- **L1b 判据仪器换 cls12 freshvac**（pt）：基线 = 本文件 §2 的 exit（3.505/4.265/4.216）与
  off（5.007/4.033/3.961，sd 0.584）；门槛 = max(1.19, 0.584) = **1.19cm**（同 L3 结构）。
- gate L1b 的定位从"人群族改进快筛"升级为**机制的判决性测试**：exit 在 pt 上 carve 被阻断
  ⇒ exit≈off；gate 若解锁 carve，应把人物轨迹区残影（≈4–5cm）压掉 >1.19cm——修正后的
  仪器恰好直接测这个区域。

## 6. 边界

- 本重评为**机械重应用**（判据逐字未动）；关卡② 未过 ⇒ 任何数字仍不得进论文；
- balloon/balloon2/mvnobox/mvnobox2 的重评**前置条件** = 建立有效移动者冻结掩码
  （几何/运动重建，需独立验证）——是否投入 = D2；
- crowd3 沿用旧读数的依据：其掩码生成本就正确（`build_person_seg_mask.py`，person=15）。


## 附录 A：掩码类号/源"静默默认值"清单与处置（2026-09-21，辅助会话审计 + 本会话处置）

| 位置 | 默认值 | 风险 | 处置 |
|---|---|---|---|
| `render_compare.py:115` `--mask-class` | `15`（帮助文本还断言 "Bonn PASCAL person=15"） | 错类静默 | **已改**：默认 `None` + 由 `utils/dynamic_mask_spec` 按序列解析（**默认拒**）；帮助文本更正 |
| `render_compare.py:197` `--mask-subdir auto` | 优先 `dynamic_mask_gtmc` | 失效仪器静默 | **已改**：auto 走 spec；显式用 gtmc 需 `--allow-unvalidated-mask`，产物记 `mask_validity=invalid-known` |
| `render_metrics.json` 无 `mask_class` 字段 | — | 错类无法从产物发现 | **已改**：新增 `mask_class` / `mask_validity` 字段 |
| `geom_selfconsist.py:274`、`diag_f3_probe.py:55`、`diag_f3_geom.py:157`、`dyn_probe.py:96` | `--mask-class 15` | 同上 | **未改**（诊断脚本，非判据链）；登记为待改 |
| `geom_selfconsist.py:83`、`diag_f3_probe.py:56`、`dyn_probe.py:132` | auto 优先 gtmc | 同上 | **未改**（同上）；登记 |
| `scripts/build_person_seg_mask.py` | `--out-subdir seg_mask`（覆盖 shipped ADE20K 参照，不可逆） | 毁掉唯一人参照 | **已改**：默认 `dynamic_mask_person/`；已有 PNG 则拒；指名 `seg_mask` 需 `--i-know-this-overwrites-shipped`；manifest 中被证伪的"同口径 person=15"断言已更正 |
| `utils/semantic_mask.py:131/158` | `model="deeplabv3"` + `dynamic_classes=[15]` | — | **保留**（VOC 口径对 deeplabv3 正确，且 tum/replica base_config 仍用）；它**不是**"Bonn 自带 seg_mask 是 VOC"的错源——错的是把两套约定混用 |
| `configs/experiments/{embrace_dyn,transient_map}/*` 硬绑 gtmc 的 7 个配置 | gtmc | 重跑会用失效仪器 | **保留**（已跑批的可复现记录），但重跑前须换源并标注"仪器已知失效" |
| `combined_prune/method.yaml:47` `static_bg_mask_subdir` | `dynamic_mask_gtmc` | L3 全批 static 行作废 | **保留默认**（改动会影响历史复现），但 L1b 配置显式 `null`；消费方须核 `mask_type='static'` 行的口径 |


---

# 附录 B：掩码体系重构 v2 后的重评（2026-09-22，canonical 掩码）

**背景**：用户在 2026-09-21 指示重构掩码体系（详见 `mask_system_refactor_v2_2026-09-21.md`）。
canonical 评估掩码 = `<seq>/dynamic_mask/`（0/255 布尔，人物区域，MaskRCNN 源，9 序列全过验证）。
本轮用 canonical 掩码**重渲染 63 run**（`rerender_all_canon.sh`，帧集/护栏/PLY 与原渲染一字不差，
仅换掩码源）并机械重应用两个判据。**判据未改**。

## B.1 L3 主判据（freshvac）三种仪器口径对照

| 序列 | 历史 gtmc/cls15 口径 | 中途 cls12 口径 | **canonical v2** | canonical 判定 |
|---|---|---|---|---|
| balloon | −2.437 ✅ | （未做） | **−0.112**（2/3 负） | ❌ |
| balloon2 | −2.615 ✅ | （未做） | **−2.066**（3/3 负） | ✅ Tier2 |
| crowd | +0.548 ❌ | +0.164 | **+0.720**（0/3 负） | ❌ |
| crowd2 | −2.674 ✅ | −0.254 | **−0.329**（2/3 负） | ❌ |
| crowd3 | +2.089 ❌ | （沿用） | **+1.556**（0/3 负） | ❌ |
| person_tracking | −0.204 ❌ | −0.338 | **−0.084**（1/3 负） | ❌ |
| person_tracking2 | −0.277 ❌ | −0.162 | **−0.073**（2/3 负） | ❌ |
| mvnobox | −1.238 ✅ | （未做） | **−1.669**（3/3 负） | ✅ Tier2 |
| mvnobox2 | −1.391 ✅ | （未做） | **−2.028**（3/3 负） | ✅ Tier2 |

- **canonical 批级 = 3/9 PASS**（门 ≥6/9）⇒ 批级仍不过。
- **存活的 3 条**：mvnobox、mvnobox2（box 族，3/3 负、Tier 2）+ balloon2（3/3 负、Tier 2）。
  历史口径下 PASS 的 balloon、crowd2 在 canonical 下不过。
- **人群族 5 序列**在 canonical 下仍全不过（与中途 cls12 口径**结论一致**：人群族无 exit 效应）。
- 约束门（ATE 列）与历史**逐字相同**（ATE 来自 run 表，与掩码无关）⇒ 越门集合不变
  `['crowd','person_tracking','person_tracking2','mvnobox']`；PSNR 列随掩码更新
  （例：crowd +0.635 → **+1.601**、mvnobox −0.358 → **−0.384**）。
- **口径声明（必须随数字并陈）**：canonical 掩码覆盖**人物区域**。对 box/balloon 序列，
  气球/箱子不在掩码内 ⇒ 这 3 条 PASS 的语义 = **"人物轨迹区残影被显著压低"**，
  **不是**"箱子/气球残影被清掉"（覆盖缺口见重构文件 §4）。

## B.2 L1b 主判据对仪器更换的稳健性

| 仪器 | Δ = gate − exit（3 seed） | mean Δ | 门槛 | PASS |
|---|---|---|---|---|
| 中途 cls12 | −1.054 / −1.838 / −2.788 | −1.893 | 1.19 | ✅ Tier2 |
| **canonical v2** | −0.466 / −1.510 / −2.335 | **−1.437** | 1.19 | ✅ Tier2（ratio 1.21） |

⇒ **主判据在两个独立掩码口径下同为 PASS**（3/3 负、幅度均过门）；约束门同为越门
（ATE +1.357cm 由 s0 单点主导、PSNR −1.74/−1.81dB）。机制计数器与掩码无关，结论不变
（capped 18.8–22k、`carve≈0`、α 钉死 0.2199）。**判决稳健。**

## B.3 对 D2 的含义（更新）

1. **box 族**：canonical 口径下 mvnobox/mvnobox2 均为 3/3 负、Tier 2 ⇒ "box 族可作阶段性表述"
   **重获有效仪器支撑**（此前因 gtmc 失效而悬置）；但措辞须限定为**人物轨迹区残影**，
   且 balloon（同族）在 canonical 下不过 ⇒ 族内不一致，只能写"box 亚族"。
2. **人群族**：三种口径一致显示无 exit 效应 ⇒ 用户方向（"人群族仍是要解决的问题"）**不变**；
   L1b gate 是首个在人群族出现的可复制正效应（−1.44/−1.89cm，3/3 负），但带 ATE/PSNR 代价
   且机制路径未证实（carve 未解锁）。
3. **数字仍不得进论文**（关卡② 未过）；canonical 重评尚未经关卡① 审查。
