# 论文 2（CVM 2027 投稿）— 模拟审稿报告（2026-10-13）

> **性质**：三轮综合——① 独立审稿（2026-10-05，Reject/Major，v0 稿）；② 视觉模型审阅
> （图表/排板，2026-10-13）；③ 文本模型复核（本件，数字工件溯源 + 口径核对）。
> **被审对象**：`papers/paper2/paper2_cvm.tex`（751 行，14 页 PDF，12 图 8 表），HEAD `de8f85480`。
> **用途**：投稿前自查（内部预审）。本件不改任何东西；整改见方案 + 后续 commit。

---

## 0. 总评与建议

**建议：Major Revision（两处 P0 修掉后可达 Accept 门）／现稿按现状投 = Reject 风险高。**

一句话：**这是一篇"方向对、主线清、但两处核心读数口径自相矛盾"的稿子。** 10-10 重写已把
v0 的致命伤（SWBA 残留、无外部基线、标题 over-claim、salami）全部清掉，系统横比 + 地图四问的
骨架是 CVM 能收的形态；但 **§6 与 §7 在同一张"动态区收益"上用了两套不可比的口径，且 §6 的
oracle 探针恰好否定了 §7 算子的必要性**——这是审稿人一眼能看到、且无法用"诚实"辩护的硬伤。
修法不涉及新机制，只涉及口径分层与一处对照实验（已补跑）。

---

## 1. 评分表（CVM 口径）

| 维度 | 评 | 依据 |
|---|---|---|
| **Novelty** | 中（3/5） | 4D 层 codec 的"排除被抑制基元"是真洞见；重尾承重反直觉（但与 MGS-SLAM/PWAS 重叠，须收窄）；系统横比 11 方法同机复现是扎实资产 |
| **Technical soundness** | 中偏弱（2.5/5） | 单批同码、工件键齐全、判据机先行 = 本仓强项；但 §6↔§7 口径矛盾直接动摇贡献②③ |
| **Significance** | 中（3/5） | "地图是被忽视的对象"动机成立；codec 6×/15× + 离线修复 21/21 是可用的工程结论 |
| **Presentation** | 中偏强（3.5/5） | 结构清晰、图全、匿名干净；残留：Table 6 题注与表内矛盾、Fig1/Fig3 重复、末页留白 |
| **Reproducibility** | 强（4.5/5） | `% gate2:` 工件键全覆盖、判据机入库、三批 HEAD 逐位一致、机写判决——本稿最强项 |

---

## 2. 优点（先说清楚）

1. **11 方法同机复现横比是真资产**：同一机器、同一 evo Horn 协议、3 seed，静态方法在动态序列
   崩掉的实测（Co-SLAM crowd 35866 cm 发散格）直接支撑"反动态范式为何必要"的立论。
2. **4D 层 codec 的洞见是新的**：动态层 35.9% 基元 opa=−30 被抑制却撑爆量化范围 ⇒
   "先排除不可见基元再量化"（`probe_4d_compress_2026-10-12.md`），近无损 7.9–9.3×，数字诚实
   （链式赋值 bug 后已修复，J1 保持 84–96% 而非虚高的 100%）。
3. **判据纪律顶级**：§12 v4 同帧位姿口径、causal/final 诊断口径禁进出口、位姿控制 −4~−8 dB
   的实证、S5 开/关单变量对照——这些是审稿人最想看到而多数论文没有的。
4. **匿名干净**：无 our/my、无单位、无自引条目、`Prior RGB-D stack` 第三人称一致。
5. **门禁全绿**：342 tests / health 0 fail / 14 页 0 missing 0 undefined / style_tells 硬门过。

---

## 3. P0 —— 不修必拒

### 3.1 【致命】§6↔§7 读数口径自相矛盾，且 §6 否定了 §7 的必要性

- **§6 说**（`paper2_cvm.tex:598-600`）："Inserting the observed geometry once (no motion model)
  recovers **0.80–0.93** of the erased depth error"。读者会理解成"朴素插入把深度误差降到
  7–20%"。
- **实际口径**（`results/paper2_fulltable/evidence/dyn_cost_decomp_2026-10-05.json`）：
  `retention = (dl1(P1)−dl1(X))/(dl1(P1)−dl1(P2))`，其中 **P2 = 逐帧插入 + 拟合的 oracle 天花板**。
  即 0.80–0.93 是"挽回的 error 占 oracle 可挽回量的比例"，**不是**残差比。朴素臂 P2c 的真实
  残差比 **P2c/P1 = 0.22–0.38**（balloon2 0.221 / crowd2 0.293 / crowd3 0.350 / crowd 0.301 /
  person_tracking 0.378）；oracle 本身也只到 0.16–0.27。
- **§7 算子**（`manifest_offline_L1_L3.json`）：**J2 = 0.23–0.61**（同族量：残差比，越低越好），
  J1 = 5.49–8.95 dB。与 §6 的朴素臂 P2c/P1 同序列直接对比：

  | 序列 | §7 J2（完整算子） | §6 P2c/P1（朴素插入） | 胜者 |
  |---|---|---|---|
  | balloon2 | 0.227 | 0.221 | 持平 |
  | crowd2 | 0.473 | 0.293 | **朴素更好** |
  | crowd3 | 0.444 | 0.350 | **朴素更好** |
  | crowd | 0.581 | 0.301 | **朴素更好** |
  | person_tracking | 0.427 | 0.378 | **朴素更好** |

- **5 条共有序列里 4 条朴素插入优于完整算子**。§6 的桥接句（`paper2_cvm.tex:618-624`）
  "a repair that inserts that geometry should recover most of the dynamic-region error even
  without modelling motion" 恰好预言了"朴素就够了"，§7 却打不赢它。
- 审稿人必写："§7 没有被证明超过朴素基线；§6 自己否定了 §7 的必要性。"
- **口径差异（真实存在，但论文未说）**：§6 探针 = GT 深度 + unproj_stride 3 + 16 帧 + 无 S5；
  §7 算子 = 传感器深度 + MaskRCNN 掩码 + KF 日程 stride 5 + S5（投影掩码剪枝 + 尺度夹回，
  J3/J2 结构性张力已登记）。其中 S5 是 J2 变差的直接来源（v3→v4 J2 0.163→0.473）。
- **修复（已执行）**：① §6 显式标 GT 深度 oracle 天花板并给出真实残差 0.22–0.38；② §7 显式标
  可实现算子并写清差距归因；③ **同口径朴素插入对照已跑**（NaiveCtrl，§6 附录）：朴素动态区
  更好但静态区崩毁（J3 −11.7~−16.7 dB）且层膨胀 ~100× ⇒ **算子的增量 = 静态零损伤 + 层有界，
  不是动态区幅度**，§7 已改述；④ §7 主张收窄为"在可实现条件下取得实质增益 + 静态零损伤 +
  4D 层可压缩形态"。

### 3.2 【重大】Table 6 题注与表内数字矛盾

`tables/tab_dyncost_seq.tex:24` 题注："no sequence damages the static region (all static
changes are positive and **within 0.25 dB**)"；但表内静态列为 **+0.29 / +0.04 / +0.39 / +0.28 /
+0.33**（crowd2 除外全部 >0.25，最高 +0.39 = 超 56%）。§6 正文反而写对了（"nine … +0.04 to
+0.39 dB … no map degrades beyond the 0.25 dB band"）。改题注为"all static changes are
positive, +0.04 to +0.39 dB"。

---

## 4. P1 —— 强烈建议

### 4.1 【重大】PSNR 双口径并存、无一句协调

同一系统（prior stack）同一序列 balloon 出现在三处、三个 PSNR 档位：
- `tab_rd`：full **15.38** / static **21.79**（codec harness 独立协议，均值）；
- `tab2r_render`：full **21.80**（"offline rendering sampled away from keyframe grid"）；
- `tab3s_static`：static **27.68**。

审稿人对照三张表会认为数字互相矛盾。需在 §3 协议段或表注加一句"全图 PSNR 因渲染帧集与协议
不同（codec 的 fixed eval frame set vs 系统渲染的 grid-away 帧集）而不可跨表比较"，并给出两者
的帧集差异。

### 4.2 【重大】工作点命名冲突

15× 档在摘要/引言/§8 叫 "a **moderate** working point"，§5 正文与 `tab_rd` 叫
"**aggressive**"（mid 才是 8.77×）。命名须统一。

### 4.3 【重大】单系统作用域未声明

解剖/代价/修复全来自**一个**前作栈的地图（仅 codec 有 5 TUM + 1 Bonn 留出面板）。§4/§6/§7
的结论应加一句适用条件边界（"these readings are from one prior stack's maps; generalization
to other dynamic-scene systems is not established"），按纪律融入 Discussion 写成条件，不单设
Limitations。

### 4.4 【中】Fig 1 与 Fig 3 重复

`fig1_pipeline`（figure\*，p3，真实数据管线）与 `fig1_arch`（单栏，p4，示意框图）讲同一件事
（在线环路 + 两个离线操作），出现在同一区域。建议删一张（保留真实数据管线图）或让框图承载
不同信息（如标出 §4 解剖的三个发现落在哪些字段）。

### 4.5 【中】Table 3 单行却跨栏

`tables/tab4_efficiency.tex` 是 `table*`（全宽）却只有 1 行数据（47086 / 3.36 / 1.162 / 0.879 /
1.32×）。收窄为单栏。

---

## 5. P2 —— 打磨

1. **末页 ~40% 空白**：参考文献停在 p14 上部。改版可微利用（勿为凑页塞内容）。
2. **`fig_rd_curves` 图例 14 条**（5.5 pt），panel (a) 三分之一是图例；可瘦身（只标差异显著者）。
3. **四张图字效 <8pt**（纪律"字体 ≥8pt"）：`fig4_tail` 5.25 / `fig1_arch` 5.29 / `fig_rd_curves`
   5.50 / `fig2`+`fig2b` 5.90（现只过 5pt 底）。建议提升或明示项目口径与纪律一致。
4. **`fig5_accounting` 图例 "zlib removes them" 夸大**：正文自己说 20→14 字段熵编码只省 1.04×、
   不是免费增益。图例措辞改"entropy-coded to near-zero; not a free gain"。
5. **fig2/fig2b 行标 "baseline" vs 题注 "prior stack"**：内部臂名漏进图面，统一为 prior stack。
6. **孤儿图 `figs/fig_storage_accounting.pdf` 仍在活目录且含 gate 臂**（红线）；全文未引用，
   移出活目录（归档或删）。
7. **引文 `DG-SLAM` vs bib 标题 `DGS-SLAM`**：正文与表两处统一为论文正式名 DGS-SLAM。
8. **"extended in-house"**（`paper2_cvm.tex:203`）是匿名稿的自引指纹；改"extended with …"
   去掉 in-house 归属。
9. **"raw outputs are released"**（`:214, :298`）：无法在盲审中核验；改"are available upon
   request"或留待 camera-ready。

---

## 6. 附录：已执行的对照实验（P0-1 修复）

**NaiveCtrl 朴素插入对照臂**（`results/dynport_offline/evidence/prereg_naive_ctrl_2026-10-13.md`）：
与 §7 算子同口径（传感器深度 / MaskRCNN 掩码 / 同 KF 日程 / 同 fit / samepose 位姿）但
**跳过生命周期决策核与 S5** 的纯朴素插入。3 序列（crowd2/balloon2/person_tracking2）seed0，
远程 3090，3 run 全 rc=0。

**结果（机写，`evidence_naivectrl/manifest_naive_ctrl.json`）**：

| 序列 | J1 R1 | J1 Naive | J2 R1 | J2 Naive | J3 R1 (dB) | J3 Naive (dB) | n_dyn R1 | n_dyn Naive |
|---|---|---|---|---|---|---|---|---|
| crowd2 | 7.95 | **9.36** | 0.47 | **0.18** | −0.04 | **−15.93** | 43 | 1,258,111 |
| balloon2 | 6.08 | **6.92** | 0.23 | **0.19** | 0.07 | **−11.72** | 4,042 | 456,968 |
| person_tracking2 | 6.42 | **8.42** | 0.55 | **0.28** | 0.00 | **−16.66** | 0 | 287,688 |

**判读（先锁判据）**：C1（算子增益于动态区）= **False 3/3** —— 朴素插入动态区反而更好；
**C3（生命周期+S5 保护静态）= True 3/3** —— 朴素 J3 深负 −11.7~−16.7 dB，R1 全在 ±0.25 内；
朴素动态层无界膨胀（**~100×**）。⇒ **生命周期 + S5 的增量 = 静态零损伤 + 层有界（可用性），
不是动态区幅度**。P0-1 由"算子未被证明优于朴素"逆转为"算子解决了朴素做不到的静态保护与
层有界"——§7 已按此改述，引朴素数字时与 J3 同框呈现。

---

## 7. 逐条可执行清单（按优先级）

**P0**
1. §6↔§7 口径分层（oracle vs 可实现）+ 补对照实验 + 归因 S5/传感器深度。
2. Table 6 题注 0.25 dB → 实值 +0.04–0.39。

**P1**
3. PSNR 口径协调句；4. 工作点命名统一（aggressive）；5. 单系统作用域边界句；
6. Fig1/Fig3 去重；7. Table 3 收窄单栏。

**P2**
8. 图例瘦身/字效提升/fig5 措辞/fig2 行标/孤儿图移出/引文统一/in-house 措辞/release 措辞。

---

## 8. 正面结论

这篇稿子的骨架是对的：地图四问 + 系统横比 + 判据纪律，是 CVM 能收的"地图侧系统+分析"形态。
问题不是"没有贡献"，而是**把贡献砌在了两套互不兼容的口径上**。把 §6 标成 oracle、§7 标成
可实现、用对照实验把"算子是否多于朴素"讲清楚，这篇就立得住。

---

# Round 4：定稿候选复核轮（2026-10-13，全门禁通过后追加）

> **性质**：定稿候选版的独立审稿人视角对抗复核。**聚焦叙事强度 / 主张边界 / 遗漏对比 /
> 方法表述清晰度**——数字核验、合规、排版、视觉已在前三轮 + 视觉模型验收轮全过，本轮不重推。
> **被审对象**：`papers/paper2/paper2_cvm.tex`（773 行，14 页 PDF，11 图 8 表），HEAD `f94c5f42c`。
> **门禁基线（本轮核验）**：pytest **345 passed**；health **失败 0**（唯一脏 = build 重编译
> 造成的 PDF 时间戳，非新问题）；build **14 页 0 missing 0 undefined**（overfull=1 既有
> tab_baseline）；style_tells **R1 em-dash 0.0 / R4 AI 短语空**（两硬门全过）；§2-§7 全部数字
> 与工件逐位对拍通过（storage/tail/codec/rd/4d/dyn_cost/decomp/offline/naive 全部重算吻合）。
> **用途**：投稿前最后一轮自查。本件不改任何东西。

---

## 0. 总评与建议

**建议：Accept with Minor Revision（距 Accept 仅剩打磨级条目；无致命/重大项）。**

一句话：**这是一篇"方向对、主线清、数字可复现、匿名干净"的定稿候选。** 前两轮的两处 P0
（§6↔§7 口径矛盾 + Table 6 题注）已按方案修净，NaiveCtrl 对照把 §7 的贡献讲成"静态零损伤 +
层有界"的可用性增量，oracle 天花板显式化——审稿人最可能提的硬伤已不存在。本轮复核的剩余
意见全部落在 **Minor / 打磨级**：方法表述清晰度（J 指标未在正文定义、PSNR 量级无参照）、
遗漏对比的论证完整性（§5 无 3DGS 专用压缩对比，但可用文字补论证）、以及若干措辞/风格软指标。
**无一条需要新实验；无一条触及已锁叙事红线。**

评分较上轮小幅上调：Novelty 3/5 → 3/5（不变，已收窄）；Technical soundness 2.5/5 → **4/5**
（口径分层落地 + NaiveCtrl 归因）；Significance 3/5 → 3/5；Presentation 3.5/5 → **4/5**
（图/排版整改完成）；Reproducibility 4.5/5 → 4.5/5（最强项不变）。

---

## 1. 优点（先说清楚）

1. **数字可复现性是本稿最强项**：全部测量数字带 `% gate2:` 工件键，且本轮逐位对拍通过
   （例如 §6 "15–27%" = `dyn_cost_5seq_2026-10-05.json` 的 0.153–0.269 baseline 臂；
   §7 J1 5.49–8.95 / J2 0.23–0.61 / J3 −0.04~+0.20 / 21/21 = `manifest_offline_L1_L3.json`
   summary 逐 cell 聚合；§5 5.96/8.77/15.11× 由 `l2_summary.json` 14 臂重算吻合）。
   这直接回答了审稿人"数字哪来的"——在 CVM 这种以可复现性为隐性门槛的场合是稀缺优点。
2. **口径分层彻底**：§6 oracle vs §7 可实现、同框归因，NaiveCtrl 对照把"算子为何不更高增益"
   讲透（生命周期+S5 = 静态零损伤 + 层有界，不是动态区幅度）。
3. **主张边界诚实且不摆烂**：Discussion 把三条边界写成适用条件，不设忏悔清单；"not a result
   of this paper" 声明清晰。
4. **匿名干净**：正文 0 处 "our/my"；前作栈全篇 `Prior RGB-D stack` 第三人称；无单位/致谢/项目号。

---

## 2. 重大问题（Major）

**无。** 前两轮 P0 已全部落地；本轮未发现新的致命/重大项。

---

## 3. 次要问题（Minor，按可操作性排序）

### 3.1 §5 codec 无 3DGS 专用压缩对比（L173-178 仅 Related Work 提及 HAC/Compact3D/TC3DGS）

**证据**：`paper2_cvm.tex:173-178` 只在 §2 把 HAC / Compact3D / SOG / StitchGS / TC3DGS /
MEGA 列为 Related Work；§5 Rate–distortion（L401-411）的基线只有通用无损压缩器
（zlib/zstd/lzma/blosc2，1.37–1.62×）。
**审稿人视角**：3DGS 压缩是活跃赛道，同赛道论文必被问"为何不与 HAC/Compact3D 比"。
**处置（默认，纯文字补论证，不跑新实验）**：在 §5 补一句显式论证——"这些方法作用于已训练
静态或 4D 模型、需要学习式熵模型，而本文作用于动态场景 SLAM 系统的冻结地图、故意参数无关；
在此输入分布上以可复现的通用压缩器为界"。这既回应"为何不比"，又不引入不可比的新实验。

### 3.2 §7 J1/J2/J3 指标在正文无定义（首次使用 L483，定义只在 Table 8 caption）

**证据**：J1 首次出现于 L483（§5 末"J1 kept at 84–96%"），§7 L643 用 J1/J2/J3 而不解释；
J1/J2/J3 的完整定义只在 Table 8（tab_dynport.tex）caption。
**审稿人视角**：读到 §5 末 "J1" 时没有定义；CVM 双栏排版下 Table 8 在 §7 中段，读者要先跳。
**处置**：在 §7 首段（L643 前）加一句括号定义："J1 = dynamic-region PSNR gain over the erased
baseline, J2 = depth-error ratio there, J3 = static-region PSNR change; all same-pose."
纯文字，不引新数字。

### 3.3 §5 绝对 PSNR 量级无参照（L406 "15.37 vs 15.38"）

**证据**：L406 首次给出绝对 PSNR 15.37/15.38 dB，但 §3 协议段只说明 codec 表用固定帧集，
没有给读者一个"这个量级正常吗"的参照；Table 4 同表 15.38/21.95/15.90 也是首次出现。
**审稿人视角**：15 dB 的全图 PSNR 在 3DGS 文献里偏低（MonoGS 类系统报 20-30 dB），读者会
疑惑是 bug 还是协议差异。§3 已说"absolute PSNR 可比仅限表内"，但 §5 没有把这个量级的
**原因**讲清（动态场景全帧含被掩码区 + 固定帧集离 keyframe 采样）。
**处置**：L406 括号补一句"this is full-image over a fixed evaluation set, including masked
dynamic regions; see §3"，纯文字。

### 3.4 §6↔§7 区间重叠易误读（L598 oracle 残差 0.22–0.38 vs L641 算子 0.23–0.61）

**证据**：§6 "leaving the dynamic-region depth error at 0.22–0.38 of its erased value"
（L597-598）；§7 "cuts the depth error there to 0.23–0.61"（L641）。两区间高度重叠，且
§6 是 oracle（GT 深度），§7 是传感器深度——读者会问"为何 oracle 不比可实现更好"。
**审稿人视角**：区间重叠本身不是错（不同口径），但会消耗读者一次推理；§7 已有一句
"deliberately below the oracle ceiling"，可在同句加半句把重叠讲成预期："the two ratios
overlap because the oracle probe shares the same depth-error denominator and the operator
already recovers most recoverable error"。
**处置**：§7 L645-649 归因段加一句显式同框，纯文字。

### 3.5 摘要 "a small fraction" vs §7 "0.11–0.30×"（L79 vs L667）

**证据**：摘要"at a small fraction of the total mapping time"（L79）；§7 "The repair costs
0.11–0.30× of total SLAM wall-clock"（L667）。
**审稿人视角**："small fraction" 偏营销，"0.11–0.30×" 才是诚实口径；上轮已把摘要改为
"fraction of total mapping time"（与 §7 口径一致），但 "small" 仍是评价性修饰。
**处置**：摘要改为 "at a fraction of the total mapping time"（去 small），与 §7 数字严格同框。

### 3.6 style_tells 软目标：colon 105.8/10k、paren 283.9/10k（目标 <40/<80）

**证据**：`style_tells.py` 裸计数含 LaTeX 语法污染（\cite/\ref/\gate 的括号），剥离命令后
正文风格计数：colon 105.8/10k（多数是"列举引导式冒号"——"ask four questions: …"、
"two findings carry over: …"），paren 283.9/10k（多数是解释性插入语）。**R1/R4 硬门全过**
（em-dash 0.0、AI 短语空），此两条是**软目标**。
**审稿人视角**：冒号列举引导是 CVM 可接受风格；括号密度偏高是真实文风特征，但软目标。
**处置**：不强制改（避免为指标牺牲表达）；在报告登记为"已知软指标超标、判定为可接受风格"，
本轮不整改。另登记 style_tells 裸计数口径偏差（含 LaTeX 语法）——审稿人若用裸计数会误判，
建议将来给 style_tells 加命令剥离选项（本轮不动脚本）。

### 3.7 Table 4 caption "Our codec"（tab_rd.tex L30）

**证据**：正文 0 处 our/my，但 `tab_rd.tex:30` caption "Our codec is lossy and parameter-free"
有 1 处 our。
**审稿人视角**：单处 our 不是身份泄漏（匿名规则禁"our 指代前作"，此处指本文），但为全篇一致
改为 "The codec"。
**处置**：改 1 词，纯文字。

### 3.8 R2 逐条复核：9 处 "rather than" + 1 处 triad

**证据**：`grep` 得 9 处 "rather than"（L134/237/296/390/429/470/636/660/666/756 计 10 处，
其中 L429/666 在注释），1 处 triad（L64-65 "what it contains, how small …, what the …"——
这是四问列举，非典型 triad 排比，可接受）。
**审稿人视角**：R2 是逐条复核软目标；"rather than" 在对比语境下（oracle vs 可实现、
offline vs online）是本稿论述核心，机械替换会伤表达。
**处置**：逐条看后判定全部为对比必需，不改。登记留痕。

### 3.9 残留未编译表含 SWBA/LC 敏感词（tab5_ladder.tex 等）

**证据**：`papers/paper2/tables/tab5_ladder.tex:20` caption 含 "+SWBA/+LC"，但该表**未被
\input**（tex 只 \input 8 个表，L221/264/265/413/506/587/617/675）；守护测试
`test_paper_tables_are_byte_identical_to_generator_output` 强制其存在且与 evidence 同步，
故不可删。
**审稿人视角**：编译 PDF 不含 SWBA/LC（已核验 pdftotext 全文零出现），评审不可见；仅源目录
残留。属仓库卫生，非论文问题。
**处置**：**不动**（守护测试绑定；移入 archive 会破坏 M5 断言，且交接明确"既有文件不动"）。

---

## 4. 逐条可执行清单（按优先级，本轮全部为 Minor/打磨）

| # | 位置 | 问题 | 处置 | 类型 |
|---|---|---|---|---|
| 1 | §5 L401-411 | 无 3DGS 专用压缩对比 | 补一段文字论证（输入分布不同 + 参数无关） | 文字 |
| 2 | §7 L643 前 | J1/J2/J3 无定义 | 加括号定义句 | 文字 |
| 3 | §5 L406 | 绝对 PSNR 量级无参照 | 括号补协议回指 | 文字 |
| 4 | §7 L645-649 | §6↔§7 区间重叠易误读 | 归因段加显式同框半句 | 文字 |
| 5 | 摘要 L79 | "a small fraction" 偏营销 | 去 small | 文字 |
| 6 | tab_rd.tex L30 | "Our codec" 1 处 | 改 "The codec" | 文字 |
| 7 | 全篇 | colon/paren 软目标超标 | 判定可接受，登记不改 | 不整改 |
| 8 | 全篇 | "rather than" 9 处 + triad 1 处 | 判定对比必需，不改 | 不整改 |
| 9 | tables/tab5_ladder.tex | SWBA/LC 敏感词残留（未编译） | 不动（守护绑定） | 不整改 |

---

## 5. 呈报项（需用户拍板，未执行）

- **§5 3DGS 专用压缩对比**：默认建议 = 纯文字补论证（清单 #1），不跑新实验。跑 HAC/Compact3D
  同协议对比需复现其训练流程 + 熵模型，成本高且输入分布不同（静态训练模型 vs 动态 SLAM 冻结
  地图），可比性存疑。
- **匿名前作出处**：审稿人无法核实 `Prior RGB-D stack` 的具体来源（匿名稿标准做法，上轮已
  定）。维持现状。

---

## 6. 正面结论（诚实收口）

三轮整改后这篇稿子已经是一份**审稿人挑不出致命伤**的定稿候选：口径分层讲清了 oracle 与
可实现、NaiveCtrl 把贡献从"动态区幅度"归位到"静态零损伤 + 层有界"、全篇数字逐位可复现、
匿名干净、14 页顶格无冗余。剩余意见全部是可执行的打磨级条目（补论证、补定义、补参照、
去修饰），无一条需要新实验或触及已锁红线。按当前状态投，CVM 审稿人的合理判决区间是
**Accept / Minor Revision**。

---

# Round 4b：独立审稿复核（2026-10-14，独立审稿人 agent 全独立输出）

> **性质**：由**完全独立上下文的审稿 agent**（general-purpose，未读取任何历史审稿记录、
> 未采信自查结论）以 CVM 审稿人身份通读定稿候选（HEAD `32548b6ae`）独立判决。
> **完整报告**：`results/paper2_fulltable/evidence/simulated_review_independent_2026-10-14.md`（独立 agent 落盘）。
> **独立判决**：**Minor Revision**（Novelty 3 / Technical soundness 4 / Significance 3 /
> Presentation 4 / Reproducibility 4）；Major 4 条 + Minor 10 条；抽查工件全部对拍一致、未发现数字错误。

## 独立审稿 4 条 Major 的核实与处置（主会话逐条复核工件后定案）

| # | 独立审稿意见 | 主会话核实 | 处置 |
|---|---|---|---|
| M1 | J1/J2/J3 与判据阈值只在工件、正文不可验证（P0） | 属实：阈值 J1≥2.5/J2≤0.70/J3∈±0.25 仅在 `locked_thresholds`；§7 只有 "21/21 cells pass" | **§7 补判据句**（preregistered criteria + 阈值，gate2 键指向 prereg） |
| M2 | 4D codec 机制消融仅 crowd2 单序列却撑"机制叙事"；"七方案无一改进"孤证（P0） | 属实：消融表只有 crowd2；七方案句无批次限定 | **降格表述**："On crowd2, where the ablation is measured…" + "on this batch"（呈报用户未获答 → 按默认执行；补序列消融列为可选下轮项） |
| M3 | 全图 PSNR 15 dB 量级无参照（P1） | 部分已修（Round 4 补协议回指）；量级解释仍弱 | 维持 Round 4 修复 + 登记 |
| M4 | §3 PSNR/FPS 横比数字散落正文、无渲染协议、选样准则未交代（P1） | §3 已有"固定帧集 vs 网格帧集"协议段；选样准则在 `resources/baselines/01-baselines_method.md`（按方法族覆盖，非论文正文） | 登记：选样准则入正文会挤 14 页余量，维持现状（补一句可选） |

## 独立审稿额外发现 4 处（自查未覆盖）的核实与处置

| # | 独立审稿发现 | 主会话核实 | 处置 |
|---|---|---|---|
| E1 | Fig.1 caption "+6.8 dB" 与 L3 manifest crowd2 J1=7.95 不符 | **数字正确**：+6.8 = 三序列（crowd2 7.95/balloon2 6.08/person_tracking2 6.42）J1 median 均值 6.82；**gate2 注释指向错误**（误标 L3 manifest） | **修注释**：`dynport_offline_L1_{crowd2,balloon2,person_tracking2}_samepose.json` + caption 加 "mean over the three repair sequences" |
| E2 | supplementary material 死引用（投稿无附件） | 属实：L212/L287 两处 | **措辞改**："protocol is stated once in the evaluation paragraph below"（§3 协议段自含） |
| E3 | Table 6 caption "all static changes are positive" 与正文 "tenth by −0.03 dB" 口径张力 | 数据无错：表 = baseline 5 行（全正），正文 = 双臂 10 行（1 行 −0.026）；但并置会让细读审稿人困惑 | **正文补 "across the ten maps of both arms" + "the baseline arm alone is positive" 并置句** |
| E4 | Fig.4/5 轴标签排版疑似错位 | 文本层无法确认；上一轮视觉模型验收已终审 Fig.4（字号提亮 + tick 碰撞修复） | 不重复视觉验收，登记 |

## 独立审稿 vs 自查差异点（诚实记录）

1. **M1 判级差异**：自查把 "21/21" 视为核验过的事实（P2 打磨），独立审稿视为"未定义判据的不可验证主张"（P0）。独立审稿更对——审稿人眼里判据阈值是"通过"语义的一部分，已补。
2. **M2 自查未覆盖**：机制叙事 vs 证据规模的匹配度，自查没有审。已降格。
3. **E1 gate2 注释错误**：自查 Round 4 只核对了数字本身（+6.8 有 provenance），没有把注释键指向的工件与 caption 数字做逐位核对——**gate2 键与数字的映射本身也需要验证**，这是本轮学到的一条（记入 PITFALLS 候选）。
4. 数字层面两边结论一致（抽查全过，无分歧）。

---

# Round 5：外部审稿（CVM_REVIEW_REPORT.md）整改处置（2026-10-14）

> **性质**：外部 Claude 盲审（只给论文 + 会议名，审稿人视角）独立判决 **Minor Revision**
> （N3/T4/S3/P4/R3），报告 = `papers/paper2/CVM_REVIEW_REPORT.md`。本段为主会话逐条核实
> 证据 + 整改落地记录。

## 外部 5 条 Major 的核实与处置

| # | 外部意见 | 核实 | 处置 |
|---|---|---|---|
| M1 | 数据集泛化窄（仅 BONN+TUM，留出 6 序列） | 关切真实；**证据引错**（引 3.2–7.1×10⁵，正文实为 10⁴ L312） | **摘要 + Conclusion 补泛化边界句**（"established on the BONN dynamic benchmark, codec generalised to a held-out TUM panel; maps of one prior stack, not a cross-system law"）。不跑新数据集 |
| M2 | 无 learned 3DGS 压缩对比（HAC/Compact3D） | 真实（Round 4 已补文字论证仍不够） | **§5 论证加强**：学习式熵模型需 per-map 重训/适配、字段统计与训练静态场景不同、保持无学习组件使增益可归因于量化 |
| M3 | offline repair 定位不清（post-process vs online module） | 真实（Round 4b 已补作用域句仍不够） | **§7 首段加 intended use**："offline map refinement for replay/archival, not proposed as an online SLAM module" |
| M4 | "parameter-free" 措辞误导 | 真实（bit 宽度是超参非零参数） | **4 处 "parameter-free" → "no learned parameters"**；§5 Design 补 "bit widths are hyperparameters set once per map" |
| M5 | held-out 只报静态/绝对 PSNR、无 full PSNR Δ | 部分真实（数据已在盘） | **Table 4 第 8 列改为 held-out Δ**（从 L3_*_rd_table.json 机写；near-lossless −0.00 / mid −0.21 / aggressive −1.77）；守护测试同步更新 |

## 外部 10 条 Minor 的核实与处置

| # | 外部意见 | 核实 | 处置 |
|---|---|---|---|
| 1 | Δ 符号不统一 | 真实 | Table 4 caption 加 "(negative = loss)" |
| 2 | Fig.4a p99.9 虚线无标签 | **图例已有标签**（审稿人未细看）；加文本标签尝试后与直方图碰撞（审计门抓出） | **回退，登记**：图例 label "p99.9 = 0.45 m" 已满足 |
| 3 | Table 1 diverged 无细节 | 真实 | caption 加 "re-run under the same protocol with recommended settings" |
| 4 | "one-third" 不精确 | **误读**：正文 "a third of the raw bytes"=30% 通俗说法，与 Fig.3 30% 一致 | 驳回 |
| 5 | near-lossless 无定义 | 真实 | §5 加定义 "within ±0.25 dB"（与 §7 J3 判据同阈值） |
| 6 | Table 6 表头 "Bad PSNR" 不明 | 真实 | 表头改 "Dyn. gain (dB)" |
| 7 | oracle ceiling 未解释为何不完美恢复 | 真实 | §6 补 "GT depth renders with the map's own Gaussian parameters, bounds rather than reproduces" |
| 8 | Fig.9-10 图面无 erased 标注 | 真实 | fig2/fig2b 行标改 "prior stack (erased)" |
| 9 | 参考文献无 arXiv 标注 | **已满足**（cvmbib.bib 已标 arXiv preprint，外部只看 PDF 引用列表） | 驳回 |
| 10 | 匿名 "prior work" 指代 | 合规（正文 0 处 our；"not a result of this paper" 明确） | 驳回 |

## Reproducibility 3/5（外部盲审）vs 4.5/5（内部）
盲审视角合理：论文只写 "raw outputs are released" 无 code/data URL。内部 4.5 基于工件齐全。
**登记**：投稿版可加 "code/data available upon request"（匿名合规），列入可选项（本轮未加，14 页余量考虑）。

## 门禁（整改后）
- build：14 页 0 missing 0 undefined（overfull=1 既有 tab_baseline）
- pytest：344 passed + 1 fail（提交前置守护，commit 后 345）
- 碰撞 0 fail / 字号 0 fail / style_tells R1 em-dash 0.0 / R4 空
- 新守护：test_tab_rd_structure_and_numbers 更新为 held-out Δ 列断言（source=0、lossless=0、codec 行= L3 复算）

---

# Round 5b：深思熟虑修正（2026-10-14，用户指令"以最大概率 Accept 为目的，非随意见改"）

用户纠偏：改动必须服务"最大概率 Accept"，而非机械执行审阅意见。复核 Round 5 全部改动后修正 2 处：

## M1 修正：摘要边界句回退到 Discussion
- **原改动**：摘要加 "All findings are established on the BONN dynamic benchmark..."。
- **复核**：摘要职责是卖点而非免责；主动把"只测一个数据集"写进摘要会引导审稿人注意力到弱点。
  Discussion "Boundaries" 第三条已有完整边界句（"the codec's working points generalise to a
  held-out panel of six unseen sequences, but the other readings establish what holds for this
  system's maps, not a cross-system law"）——M1 关切已在正确位置完整回应。
- **决定**：摘要回退原样；Discussion 第三条保留（已足够）。外部审稿人若仍提 M1，回复指向 Discussion。

## M4 修正：恢复 "parameter-free" 主标签 + 精确边界定义
- **原改动**：4 处 "parameter-free" → "no learned parameters"（机械执行外部意见）。
- **复核**：①"parameter-free" 是论文的简洁卖点标签（审稿人引用时记 "the parameter-free codec"），
  全替换使表述变弱变啰嗦；②外部 M4 的真实关切不是这个词本身，而是"设计选择（bit 宽度/预测器/rot3）
  是否数据调的、换数据集是否失效"；③摘要 L71 已有 "no learned parameters" 括号定义。
- **决定**：主标签恢复 "parameter-free"（5 处），§5 Design 加精确边界定义
  "no learned weights anywhere, and the only choices are the five bit widths, which are
  hyperparameters set once per map"——既保住卖点，又直接回应"设计选择 vs 学习参数"的关切。

## 保留不改（复核后确认增值）
M2 论证加强 / M3 定位句 / M5 held-out Δ 列 / near-lossless 定义 / 表头 / diverged / oracle 解释 /
fig2 行标：全部为低风险清晰度或实质增强，保留。

## 数字一致性复核（正文↔表格）
- L3 源 PSNR 15.90（36 文件重算）= 正文 "15.90 dB" ✓
- held-out Δ：near-lossless 15.90−15.90=0.00 / mid 15.68−15.90=−0.21 / aggressive 14.13−15.90=−1.77
  = 表格第 8 列 ✓

---

# Round 6：外部复审（CVM_RE-REVIEW_REPORT.md）整改处置（2026-10-14）

> **性质**：外部复审判决 **Minor Revision**（明确"剩余全文本级、修掉后预期推荐接受"）。
> 报告 = `papers/paper2/CVM_RE-REVIEW_REPORT.md`（所审 = Round 5 中间版，非 v7——版本体系已建）。
> 本段为主会话逐条核实 + 整改落地记录。**整改版 = v8 快照**（sha256 0f8a37cfdc81）。

## 复审新问题 N1-N6 处置

| # | 复审意见 | 核实 | 处置 |
|---|---|---|---|
| N1 | "Three boundaries" 后列了 First/Second/Third/Fourth | **属实**（真错误） | §8 改 "Four boundaries"；Third 扩写为数据集+系统双维度（"two indoor benchmarks (BONN, TUM); held-out drawn from the same two, out-of-sequence but not out-of-benchmark"） |
| N2 | held-out ratio 未入表 + "per-map bit width" 与 "fixed before panel" 矛盾 | **属实**：held-out ratio 5.96× 与训练集巧合相等（审稿人怀疑抄的）；"per-map bit width" 措辞冲突 | §5 Design 澄清：bit 宽度 = 固定三工作点（16/8/8/8/8 等），仅量化 range 每图从数据算，"nothing fitted to the held-out panel"；Generalisation 段 "range procedure" 替换 "per-map ranges" |
| N3 | StitchGS [21] "clip attribute ranges by percentiles" 未核实 | **属实**：StitchGS 原文 = SH 能量谱剪枝 + 量化感知微调（Crossref 核实 DOI 10.3390/rs18101460），非 percentile clipping | Related Work 修正：SOG 保留 percentile、StitchGS 改 "prunes high-frequency SH parameters and quantises the rest" |
| N4 | 无 code/data 可用性声明 | 属实 | 新增 "Availability" 段："Code, evaluation harness and raw outputs are available from the authors upon request"（匿名合规） |
| N5 | 未引用 stack 的 4 个机制名是去匿名面 | 部分属实（双盲下机制专名有辨识度） | §3 措辞微调降辨识度："lineage-based lifecycle" → "lifecycle-based management" 等；维持"prior work 匿名"定位 |
| N6 | 摘要 "verified on a held-out panel" 覆盖面被高估（6 序列仅 1 条动态） | 属实 | 摘要收紧："verified on a held-out panel of unseen TUM and Bonn sequences"（scope 到 codec 工作点） |

## M1/M5 剩余项处置（复审判"部分解决"）

- **M1 数据集边界**：并入 N1（Third 扩写为数据集+系统双维度，用审稿人给的 "out-of-sequence but not out-of-benchmark" 句式）✓
- **M5 held-out ratio**：正文明确 "independently computed on the panel's 36 maps (mean 5.72--6.12 across sequences)"——数据从 L3_*_rd_table.json 机写复算（36 值 mean 5.9598），非抄训练集 ✓

## 5 条"误读指摘"裁决结果（复审）
- M1 证据（10⁵ vs 10⁴）：**审稿人撤回**（承认转录错误，10⁴ 与 2.6-5.7 MB 算术一致）
- Minor 4（one-third vs 30%）：**撤回**（不矛盾；但指出回复信"contradiction"用词过重——记录：回复信措辞应忠于原文）
- Minor 9（arXiv 标注）：**撤回**（28 条仅 [9][12] 是 preprint 且已标）；残留 [5][8][16] 缺页码——**待补**（下轮）
- Minor 10（匿名）：**撤回**（标准背景声明）
- Minor 2（Fig.4a）：**部分撤回**——审稿人看到的旋转标注 = 中间版，最终版 v7 已回退为图例（版本不一致，非论文问题）；已在复审报告头部标注版本差异

## 遗留登记
- [5] HAC / [8] TC3DGS / [16] GGD-SLAM 缺页码（审稿人 Minor 9 残留）：下轮补
- M2/M3/M4 + Minor 1/3/5/6/7/8：复审全部判 Resolved

---

# Round 7：camera-ready 收尾（2026-10-14，第三轮复审 Accept 后）

> **背景**：第三轮外部复审 **Accept**（CVM_FINAL_RE-REVIEW_REPORT.md，所审 v8.1 sha256 c4ea8bfce47e）。
> 审稿人点名三处 v7 就有的文字级旧缺陷 + 两处"残留不阻塞"观察，全部不触及结果、不需实验。
> 视觉验收（visual-judge 供应商不可用，主会话视觉模型代审）：14 页全 PASS，Table 1 "DG-SLAM" 视觉确认。

## 整改（全部文字级，v8.2 = sha256 8549d7001302）

| # | 项 | 处置 |
|---|---|---|
| 1 | Table 1 "DG-SLAM" vs 全文 "DGS-SLAM"（真实系统混淆：DG-SLAM=arXiv:2411.08373，DGS-SLAM=arXiv:2411.10722） | 生成器 LABEL 映射 `"DG-SLAM": "DGS-SLAM"`（目录键不变，显示名修正）+ 重生成 + 同步 evidence/latex + 方法文档同步 + 守护测试补目录映射 |
| 2 | Fig.1 caption "mean over the three repair sequences" 低估评测范围 | → "mean over three of the seven repair sequences" |
| 3 | §5 "mean 5.72--6.12 across sequences" 标签错（均值带区间） | → "per-map ratios span 5.72--6.12, mean 5.96"（审稿人建议句式） |
| 4 | N2 residual：§1 "uniform per-map quantisation" 歧义残留 | → "uniform per-map quantisation ranges"（§5 Design 澄清后唯一残留处） |
| 5 | range 侧信息未说明（可选不阻塞） | §5 Cost 补 "The per-map quantisation ranges are a few dozen bytes of side information carried with the bitstream" |

## 守护测试更新
- `test_diverge_marks_complete` / `test_json_matches_tex`：补 `DG-SLAM→DGS-SLAM` 目录/JSON 映射（tex 显示名 vs 数据键分离）。

## 门禁
pytest 344+1（提交前置）/ 14 页 0 missing 0 undefined / 碰撞 0 / 字号 0；视觉复查 page 3（Table 1 DGS-SLAM）排版正常。

---

# Round 8：DG-SLAM/DGS-SLAM 身份纠正（2026-10-14，用户质疑后核实）

## 错误记录（诚实登记）
**v8.2 的"DG-SLAM→DGS-SLAM 命名统一"是错误方向，v8.3 纠正。**
- 触发：用户质疑"我记得我复现的工作就是 DG-SLAM"。主会话先查证（数值对拍）后确认用户正确。
- 错误原因：①轻信外部审稿人"DG-SLAM 是笔误"的表述，未独立核实复现对象；②bib 里 DGSLAM 条目
  恰好是 2411.10722（DGS-SLAM），形成误导，未与复现数据交叉验证；③外部审稿人实际并未断言
  复现对象，只是说"表名无法通过文献解出"，是我默认了错误方向。

## 决定性证据（数值对拍）
我们复现基线（3 seeds mean） vs 两篇论文 BONN ATE：
| 序列 | 我们 | DG-SLAM 2411.08373 (Xu) | DGS-SLAM 2411.10722 (Kong) |
|---|---|---|---|
| balloon | 3.66 | **3.7** ✓ | 2.9 ✗ |
| balloon2 | 3.83 | **4.1** ✓ | 6.0 ✗ |
| person_t | 4.25 | **4.5** ✓ | 9.8 ✗ |
| person_t2 | 6.12 | **6.9** ✓ | 11.1 ✗ |
| mv_box2 | 3.56 | **3.5** ✓ | 8.8 ✗ |
**结论：复现的是 DG-SLAM（Xu 等，2411.08373）。每个序列对 DG-SLAM 论文吻合、与 DGS-SLAM 差一倍以上。**

## v8.3 纠正（sha256 b51a9a881dc0）
1. Table 1 生成器 LABEL 回退 "DG-SLAM"（数据键/显示名本就一致，无需映射）
2. bib `DGSLAM` 条目：作者/标题/arXiv 从 2411.10722 (Kong) 换成 2411.08373 (Xu)，annote 记录更正
3. 正文 L162/L250 "DGS-SLAM" → "DG-SLAM"（引用键 DGSLAM 不变）
4. 守护测试回退（test_paper2_baseline_table 两处映射删除）
5. 方法文档 01-baselines_method.md 回退 DG-SLAM

## 对审稿结论的影响
- **外部审稿人的意见本身没错**（它只说"两系统不同、表名无法解出、需统一"），错在我执行方向。
- 外部审稿人唯一可能受影响的判断：CVM_FINAL_RE-REVIEW_REPORT.md 说 [12] 是 2411.10722——
  现在 [12] 是 2411.08373，**引用内容与复现对象一致了**，反而更正确。
- Accept 结论不受影响（命名修正不触及任何结果数字）。

## 教训（PITFALLS 候选）
- 复现对象身份必须用**数值对拍**裁决（复现数据 vs 论文已发表表），不靠名字或 bib 推断。
- bib 条目可能与复现对象不符（历史条目错配）——引用前交叉验证。
- 外部审稿人意见也要独立核实，不能因其"专业"就跳过验证（本次正是跳过验证导致错误方向）。
