# Paper2 CVM 2027 — 版本锁与哈希清单

> **用途**：投稿 / 模拟审稿前，先核对本表，避免拿错版本。
> **更新规则**：每次产出新快照后，同步更新本文件；旧行保留在"历史版本"区，不删。
> **最后更新**：2026-10-23（v8.18c，范围框架修正 + 过度断言清理 + 提交包 final_2026-10-23）

---

## 当前有效版本（v8.18c，投稿候选）

| 产物 | 路径 | 页数 | SHA-256（前 16 位） | 字节数 |
|---|---|---|---|---|
| **主论文 PDF（提交用）** | `papers/paper2/paper2_cvm.pdf` | 14 | `4f684d3e3ec4ce44` | 4,223,113 |
| **补充材料 PDF（提交用）** | `papers/paper2/supplement/supplement.pdf` | 5 | `1ea0ea186703139a` | 574,322 |
| 投稿附件 zip | `papers/paper2/submission/paper2_supplementary.zip` | — | `026dfe41e2acbf0e` | 943,402 |
| 论文 1 匿名版（自引附件） | `papers/paper2/submission/prior_work_anonymous.pdf` | 14 | `e4c199cb4b16280c` | 369,080 |
| 主论文 TEX | `papers/paper2/paper2_cvm.tex` | — | `6141a0df926b7f34` | 61,922 |
| 补充材料 TEX | `papers/paper2/supplement/supplement.tex` | — | `b1159b52244b4ec2` | 5,428 |

**快照副本（内容与上表活区逐字节相同）**

> ⚠️ **PDF 字节哈希每次重编译都会变**（tectonic 写入 `CreationDate`），
> 文本内容不变。核对 PDF 时以「页数 + overfull/undefined_ref + 文本 diff」为准；
> 哈希用于确认「快照 == 当时活区」，不用于跨构建复现。TEX 哈希则是稳定的。

| 快照 | 路径 | SHA-256（前 16 位） |
|---|---|---|
| 主论文 v8.18c | `archive/pdf_snapshots/paper2_cvm_v8.18c_2026-10-23.pdf` | `4f684d3e3ec4ce44` |
| 补充 v8.18（未变） | `supplement/archive/supplement_v8.18_2026-10-22.pdf` | `1ea0ea186703139a` |
| 整版目录 | `archive/v8.18c_2026-10-23/`（tex+pdf 各两份） | 同上 |

**门禁状态**：主论文 14 页 / overfull 0 / missing_char 0 / undefined_ref 0；
补充材料 5 页 / overfull 0；pytest `tests/paper2_fulltable/` + `tests/gs_compress/` 74 passed。

## v8.18c 相对 v8.18b 的改动（范围框架修正 + 过度断言清理）

起因：作者自查「摘要给人的印象是贡献/落点太窄」，并质疑「无人研究」类断言。
**本轮全部为叙述层改动，未动任何实验读数、未改任何定量结果。**

### A. 范围框架（8 处）

原稿把 findings 一律锚定为「本栈的性质」，摘要第 2 句甚至明写
「attribute the findings mainly to it rather than to the class」，与 §4–§5
实际的跨系统/held-out 验证脱节。改为「以本栈为主要研究对象 + 明确对照边界」：

1. 摘要：删「the authors' prior RGB-D stack used as-is」+ **整句删除**
   「and attribute the findings mainly to it rather than to the class」；
   改为「a dense RGB-D splatting SLAM stack with an anti-dynamic mask」。
2. 摘要：「this stack's bookkeeping fields」→「the bookkeeping overhead」。
3. §4 开头新增框架句：「The stack is the authors' prior work~\cite{RoGSSLAM},
   used here as the primary study object; a cross-system check on the anatomy only
   closes this section.」（原拟指向 `sec:generalization`，该 label 不存在，
   改为指向本节内实际的 DynaGSLAM 对照）
4. §1：「the stack's map … its」→「these maps … their … the」。
5. §3：「are produced by a system」→「come from a system」。
6. §4：「this stack's map files」→「these map files」。
7. §4：「this stack's maps」→「these maps」。
8. **保留未动**：§8 三处「one prior stack's maps」——这是主动限缩，
   删掉反而构成夸大，故保留。

### B. 摘要重写（191 → 218 词）

9. **摘要首句事实修正（关键）**：原「the maps themselves are **rarely studied**」
   与本文 §2 自相矛盾（§2 明列 HAC/SOG/Compact3D/StitchGS/TC3DGS/MEGA，
   且开篇即称 CGS-SLAM、DiskChunGS 压缩 SLAM 高斯地图）。
   改为：「Gaussian-map compression takes trained static or 4D models as input;
   the map a dynamic-scene SLAM system writes at run time has not been characterised
   as an input distribution.」——即 §2 末句「a different input distribution」的原口径。
10. 补「the same two benchmarks (BONN, TUM)」：原句无先行词（摘要全文未出现基准名）。
11. 删「used as-is throughout」：悬空修饰，§3 已有「used as-is in every experiment」。
12. 「the stored map」→「the frozen map」（对齐 §5 frozen-map 口径）。
13. 「the base run's wall-clock」→「the producing run's wall-clock」（base run 摘要内无定义）。
14. **跨系统对照与 held-out 合并至末句**：原顺序（解剖→codec→跨系统→cost→repair→
    held-out）在 codec 与 cost 之间插入跨系统段，切断主线。
15. **新增 learned-compressor 结论句**（见下方「待确认决策」）。
16. 「deliberately plain codec」→「plain codec」、「plus entropy coding」→
    「with entropy coding」等：为守住 14 页硬顶的等量删减，未删任何数字。

### C. 过度断言清理（3 处）

17. §2：「**none of the systems above** reports partitioned metrics over dynamic
    regions」→「We **additionally** report metrics partitioned over the dynamic and
    static regions throughout」。
    理由：对 11 个复现系统的全称否定，无工件支撑，且易被单反例推翻。
18. §4：「They carry no information.」→「They carry no information **in these files**.」
    理由：`static_prob=0.7` 恒定为该 writer 的实现事实，非字段语义的普适结论。
19. §1：「most static methods **fail outright** on dynamic sequences」→
    「most static methods **diverge or degrade to tens of centimetres**」。
    理由：与 Table 1 不符——balloon 上四个静态法**均未发散**
    （MonoGS 39.32 / SplaTAM 36.50 / Co-SLAM 27.10 / ORB-SLAM3 7.27 cm），
    「fail outright」仅对 crowd/crowd2 成立。§3 原文已有正确分化表述，§1 未跟上。

### F. 提交包（2026-10-23）

`papers/paper2/submission/final_2026-10-23/` 为当前可提交包（取代 `final_2026-10-22/`）：

| 文件 | 页 | SHA-256（前 16） | 字节 |
|---|---|---|---|
| `main.pdf` | 14 | `4f684d3e3ec4ce44` | 4,223,113 |
| `supplementary.pdf` | 5 | `1ea0ea186703139a` | 574,322 |
| `prior_work_anonymous.pdf` | 14 | `e4c199cb4b16280c` | 369,080 |
| `README.md` | — | — | 包内清单与哈希 |

附件 zip `submission/paper2_supplementary.zip`（`026dfe41e2acbf0e`，943,402 B）
已从新包重建，内容 = `supplementary.pdf` + `prior_work_anonymous.pdf`。

> ⚠️ **三份 PDF 为散装，未打包为单一 zip**（沿用 final_2026-10-22 的做法）。
> 投稿系统若要求单一压缩包，需另行打包 `main.pdf` 在内的三件套。

### D. 门禁

- 编译：14 页 / overfull 0 / missing_char 0 / undefined_ref 0。
- 补充材料未变（TEX/PDF 哈希与 v8.18b 相同），未重编。
- 全部改动集中在 `paper2_cvm.tex`（32 增 28 删），无表/图/工件改动。

### E. 数字核对与修正（2026-10-23，本轮新增）

对 `results/gs_compress/evidence/anatomy_census.json`（74 行 = ours_dynamic 14 +
ours_heldout 36 + dynagslam 24）逐字段复核，**DynaGSLAM 对照全部通过**：

| 论文数字 | 实测（n=24 DynaGSLAM） | 判定 |
|---|---|---|
| `0.0–0.1%` primitives qualify | min 0.0000 / max 0.0010 / mean 0.0001 | ✅ |
| median axis ratio `2.30–2.56` | 2.3026–2.5585 | ✅ |
| 本栈动态 `0.003–0.008` | 0.0027–0.0082 | ✅ |
| 非单位四元数 `96.5–98.6%` | 0.9655–0.9863 | ✅ |
| 本栈动态 iso `78–92%` | 0.7764–0.9230 | ✅ |
| 本栈静态 `52–76%`（f1_desk2 + f3_office） | 0.5244–0.7611 | ✅ |
| bookkeeping 恒定（std） | obs/unmapped/nx,ny,nz = 0.0；static_prob = 1.19e-07 | ✅ |

**修正一处陈旧口径（2 处正文）**：§4 rotation 区间原为 `88.8–93.7%`，来源
`l1_readout_2026-10-04.md` 的**三图**普查；而同一段 scale 与 §4 末的跨系统对照
已用 `anatomy_census.json` 的 **14 图**口径。两个口径并存导致段内自相矛盾
（前文上限 93.7%、后文 95%）。已统一为 14 图实测：

- §4 正文：`88.8–93.7%` → `88.8–94.7%`（工件标注同步改为 anatomy_census.json）
- §4 末：DynaGSLAM `96–99%` / 本栈 `89–95%` → `96.5–98.6%` / `88.8–94.7%`（取实测两端）

**门禁**：14 页 / overfull 0 / missing_char 0 / undefined_ref 0；
pytest `tests/paper2_fulltable/` + `tests/gs_compress/` **74 passed**。

**已知未解决（作者知悉、决定暂不写入正文）**：`ours_heldout` panel 含 `f1_room`
的 6 行数据，但该序列因 mask 构建失败（flow 误检 24.8% 帧面积超参照 3×）
**未被计入「干净静态」组**；正文「52–76%」区间不受影响（两端分别来自
`f3_office/gate` 与 `f1_desk2/rb`），但正文未解释 f1_room 的排除原因。
若审稿人追问，答复依据见本节与 `memory/handoff-state`。



**learned-compressor 结论句已入摘要，但推翻 v8.18a 的既有判断。**

- v8.18a 记录：「**未采用 learned-compressor 对照**：SOG quantised 6.53×@−0.02 dB
  实为略优于本文 5.96×@−0.01 dB，放入摘要会自曝劣势。」
- v8.18c 现文：「a post-hoc learned compressor lands within 10% of that point,
  buying little beyond the quantisation choice」（**只给结论、不给对手数字**）。
- 判断依据：§5 原文已写「within 10% of the parameter-free codec's near-lossless
  point … What a learned codec buys here is thus almost entirely its quantisation
  choice」，摘要只是把该结论前置；不带数字可避免 6.0 vs 6.53 / 0.01 vs 0.02 的
  并排劣势观感。
- **风险**：审稿人可能追问对手分数，届时数字仍须如实给出（§5 与 supp Table S6 已有）。
- **若要回退**：删除摘要中该分句即可，其余 15 处不受影响。

**未核项**：~~§4「on DynaGSLAM's maps 0.0–0.1% of primitives qualify」~~
→ **已于 2026-10-23 复核通过**，见本节 E。原结论「24 图全量统计而非子集」成立。

## v8.18b 相对 v8.18a 的改动（跨系统 + 静态对照入文）

起因：审稿质疑「结论只来自单一系统 = 没做泛化实验」。用零 GPU 普查
（`scripts/gs_compress/anatomy_census.py`，成果 `a529d9e2f`；工件
`results/gs_compress/evidence/anatomy_census.json`，74 行 = 本栈动态 14 + held-out 36
+ DynaGSLAM 24）补齐静态与跨系统对照后，实测**推翻**原稿两处陈述：

1. **§2 `the heavy-tail finding ... is specific to that regime` 是错的**。
   重尾跨系统成立：本栈动态 1.36–2.15×、本栈干净静态 1.40–1.79×、
   DynaGSLAM 1.15–1.43×。改为「not confined to that regime, so it is carried
   rather than clipped」。
2. **§4 各向同性只报 78–92%（只覆盖动态段）**。补完整斜率：干净静态 52–76%、
   walking 81–85%、坐姿 89–91%；并给跨系统对照：DynaGSLAM **0.0–0.1%**
   （24 图，中位轴比 2.30–2.56 vs 本栈动态 0.003–0.008）。
   ⇒ 近各向同性不是 3DGS 通用属性，是本栈在动态条件下的行为。
   **成因未消融**：`utils/slam_backend.py:757` 的 `10*isotropic_loss.mean()` 是候选
   机制，正文写 candidate 不写 cause。
3. **30% 簿记降调**：DynaGSLAM 是 79 字段、SH degree 3 的另一套 schema，
   30% 只对本栈 writer 成立（其亦有 20/79 恒值字段，但构成不同，不作等价宣称）。
4. **rotation**：非单位模跨系统成立（DynaGSLAM 96.6–98.6% vs 本栈 88.8–94.7%），
   但 DynaGSLAM 只存 2 个四元数分量（rot_2/rot_3 恒 0）⇒ **字节级收益不可移植**，
   正文已明写。
5. **§5 补场景类拆分**：干净静态 5.92/8.73/14.84× vs 动态 5.94/8.60/14.46×
   （ratio_full 口径，L3 rd_table）。codec 在静态序列同样成立。
6. **§8 Scope/Limitations**：解剖有跨系统对照，成本与修复仍是单系统；三处
   「one prior stack's maps」的覆盖范围已按此重写。

**版面**：14 页硬顶守住；增量靠等量删减 §8 与前文重复的收尾散文补齐，
未删任何实验主张。摘要 193 词（v8.18b 口径；v8.18c 已重写为 218 词）。

**投稿前基础项体检（2026-10-22，非论述层）**：
- 编译：14 页 / overfull 0 / missing_char 0 / undefined_ref 0 / undefined cite 0 /
  multiply-defined 0 / Float-too-large 0。
- 图表：12 图 8 表全部被引用且编号连续；10 个 tabular 列数与行内容全匹配；
  图片 216–477 ppi（216 是 Fig. 10/11 缩略图板，属有意设计）。
- 参考文献：31 条 bib 与 31 处 `\cite` 一一对应（无悬空、无未引用）；
  自引按模板 `cvmpaper_for_review.tex:82-89` 规则（盲审不要求删自引，
  只禁 my/our）——正文第三人称 + bib 匿名作者，合规。
- 匿名性：PDF 元数据无 Author/Title/Subject；全文无作者名、路径、单位、致谢。
- 术语统一：3 处 `Tab.` → `Table`（生成器 `paper2_tables.py:492` 同步改 + 重跑 + cp）。
- 源码清理：`tab1_main.tex`（与 `tab_baseline.tex` 末行重复）与 `tab_storage.tex`
  （D2-031 删表后的死件）移入 `papers/paper2/tables/archive/`；镜像测试改为
  以正文 `\input` 为唯一真源，并新增「活区不得有未 `\input` 的表」断言。

**摘要逐字核对（每个数字回原始工件，全部通过）**：

| 摘要数字 | 工件 | 实测 |
|---|---|---|
| 30% bookkeeping | `storage_census.json`（80 B/prim，6/20 字段） | ✓ |
| 6× @ ∼0.01 dB | `rd/l2_summary.json` + 42 对 rd_table | ratio 5.96；Δ mean −0.0126 / median −0.0025 dB |
| 15× aggressive | 同上 | mean 15.11（13.88–16.87） |
| ∼8× layered | `probe_4d_compress_2026-10-12.md` | 8.12× on crowd2，J1 保持 96% |
| 17.9–22.2 dB | `dyn_cost_5seq_2026-10-05.json` | 17.92–22.22（n=10） |
| 5.5–9.0 dB | `evidence_L3/*_L3_samepose.json` | 5.49–8.95（n=21） |
| ±0.25 dB | 同上 J3 | \|J3\| max 0.196（3 cell 微负 −0.035，在带内） |
| 11–30% wall-clock | `manifest_offline_L1_L3.json` J4 | 0.110–0.296（n=21） |

**摘要框架修正**：原第 2 句「report what follows as a property of that system rather
than of the class」与第 5 句「second system shows non-unit quaternions and a weaker
heavy tail」自相矛盾（后者已是跨系统论断）。改为「attribute the findings mainly to
it rather than to the class」+「Against a second dynamic GS-SLAM system, non-unit
quaternions and a weaker heavy tail survive, but this stack's bookkeeping fields and
near-isotropic scale bulk do not」。

**须知的边界（不得在 rebuttal 中夸大）**：
- 干净静态只有 2 个序列（f1_desk2、f3_office），f1_room 的 mask 构建失败
  （`/data/Datasets/TUM/rgbd_dataset_freiburg1_room/dynamic_mask_BUILD_FAILED.json`，
  flow 误检 24.8% 帧面积超参照 3×），故未计入静态类；f3_st_rpy 有坐姿的人，
  正文按「seated in view」单列，不称静态。
- 跨系统对照只有 DynaGSLAM 一家（全机扫描：其他基线无高斯地图工件）。

## v8.18a 相对 v8.18 的改动（摘要重写）

摘要 266→185 词。删 11 系统复现/逐项解剖/多工作点堆叠，只留一条主线与三个必要数字。
**「held-out panel of unseen TUM and Bonn sequences」→「further sequences from the same
two benchmarks」**：原句易读成跨基准验证，而 §8 明写 out-of-sequence but not
out-of-benchmark，属事实不一致。明示结论基于单一系统（prior stack used as-is），
与 §8「one prior stack」对齐；保留 30% 解剖一句，否则与 §1 三条贡献不符。
未采用 learned-compressor 对照：SOG quantised 6.53×@−0.02 dB 实为略优于本文
5.96×@−0.01 dB，放入摘要会自曝劣势。

## v8.18 相对 v8.17 的改动（独立审稿整改）

阅稿发现三项「名实不符」，已用代码/实验记录核实后整改：

1. **§4 结构冗余**：rot3 确在主表（B/prim 13.4 = rot 3 分量算术），
   **iso-scale 从未进 L2/L3**（`rd_harness.py` 不传 `iso_scale`，L2 全为
   `alloc=uniform`）。原文「two structural redundancies the codec can exploit」
   已拆为「rot3 已用 / iso-scale 可用但未实现（端到端仅 0.3–2.2%）」；
   删掉指向 4D 层消融（Table 5 row 2）的错位引用；scale 组节省由「34%」
   更正为跨 7 图实测 **23–48%**（随工作点变化）。
2. **§6 两个 oracle 探针**：Table 6/S7 的 0.153–0.269（GT 深度）与
   §6/§7 的 0.22–0.38（传感器深度）本是两个探针，原文共用一个 "oracle"。
   已命名 `ground-truth-depth oracle` / `sensor-depth probe`，§7 改指后者。
3. **arm 未定义**：baseline/final = 前作栈 `SWBA`+`LoopClosure` 关/开
   （`effctlconc_ablation.py:24` + 两份配置 diff 的唯一差异）。§3 补定义；
   Table 3 的 "base arm" 统一为 "baseline arm"。

其余整改：编码耗时补因果（量化索引耗时恒定，zlib 低熵流更慢，0.7/7.4 µs 未写反）；
摘要数字统一 en dash；耗时分母统一为 base run's online wall-clock；
"static methods fail outright" → "Most static methods"（并给出 ORB-SLAM3 7.27 cm 反例，
原句与 Table 1 冲突）；Table 4 题注 free ratio 1.5–1.6 → 1.4–1.6、体素合并均损
0.08 → 0.02–0.07 dB；Table 7 删 coverage 列（恒 1.000）、负号改数学模式；
Table 8 符号排版；§5 补量化公式与属性组顺序；补充材料 Fig. 6 → Fig. 12；
§8 三处 rebuttal 语体改陈述；文献列表压紧以守住 14 页。

---

## 非当前版本（勿用于投稿）

| 版本 | 位置 | 说明 |
|---|---|---|
| v8.18b | `archive/pdf_snapshots/paper2_cvm_v8.18b_2026-10-22.pdf` + `archive/v8.18b_2026-10-22/` | 跨系统/静态对照版；摘要含「attribute the findings mainly to it rather than to the class」与「rarely studied」，被 v8.18c 的范围框架修正取代 |
| v8.18a | `archive/pdf_snapshots/paper2_cvm_v8.18a_2026-10-22.pdf` | §2 `specific to that regime` 与 §4 只报高端各向同性被 2026-10-22 普查推翻；被 v8.18b 取代 |
| v8.18 | `archive/pdf_snapshots/paper2_cvm_v8.18_2026-10-22.pdf` | 摘要 266 词（密度过高/held-out 歧义），被 v8.18a 取代 |
| v8.17 | `archive/pdf_snapshots/paper2_cvm_v8.17_2026-10-21.pdf` | 上一版；§4 两冗余名实不符、§6 oracle 混名、arm 未定义（v8.18 已改） |
| v8.16 | `archive/v8.16_2026-10-21/` | 上一版；含 `unpublished/uncited` 错误表述，**不得投稿** |
| v8.15 | `archive/pdf_snapshots/paper2_cvm_v8.15_2026-10-19.pdf` | 补充材料对应 v8.13（6 页） |
| v8.13 补充 | `supplement/archive/supplement_v8.13_2026-10-19.pdf` | 6 页，Table S1 横排 |
| v7 / v8.2–v8.12 | `archive/pdf_snapshots/` | 历史快照，仅供追溯 |

---

## 版本号对齐说明

历史遗留：主论文曾到 v8.15，补充材料停在 v8.13，中间 v8.16 只在目录、未进 `pdf_snapshots`，
因此快照列表看起来"断档"。**自 v8.17 起两者同版**，此后主论文与补充材料共用同一版本号。

---

## 参考文献编号变动（v8.15 → v8.17）

插入自引 `[2] Anonymous Author(s). RoGS-SLAM... Accepted at MMM 2027` 后，按作者字母序
（`cvm.bst` 全局 `SORT`）整体后移一位：**v8.15 的 [n] ⇒ v8.17 的 [n+1]**（n ≥ 2）。

**正文引用无错位**：全文 46 处引用均为 `\cite{}`，无手写编号；已逐条核对 20 个系统名
与其编号语义一致（DynaSLAM[3]、ORB-SLAM3[4]、SplaTAM[11]、HAC[6]、Compact3D[14]、
MonoGS[18]、SOG[19]、Niedermayr[20]、Bonn[21]、TUM[22]、StitchGS[23]、RGD-SLAM[24]、
Co-SLAM[25]、DG-SLAM[26]、NGD-SLAM[30]、WildGS-SLAM[31] 等）。

⚠️ **引用旧版审稿报告时注意**：`archive/reviews/` 下报告里的 `[n]` 是按当时版本的编号
（多为 v8.15 及更早）。跨版本对照时请以**系统名**为准，不要直接用编号。

---

## 校验命令

```bash
cd /data/monogs-ours
sha256sum papers/paper2/paper2_cvm.pdf \
          papers/paper2/supplement/supplement.pdf \
          papers/paper2/submission/paper2_supplementary.zip
# 与本表前 16 位比对；不一致说明活区被重新编译过，需重新打快照
```
