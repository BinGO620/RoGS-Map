# Independent Review — "Dynamic-Scene Gaussian Maps: Anatomy, Compression, and Offline Repair"

- Reviewer role: anonymous CVM reviewer (RGB-D SLAM / 3D Gaussian Splatting / map compression)
- Date: 2026-10-14 (independent pass; no prior review records read)
- Materials read: `papers/paper2/paper2_cvm.tex` (785 lines), rendered PDF (14 pages,
  `pdftotext -layout`), 8 table files, figures list, discipline spec, R2_NARRATIVE.md;
  evidence spot-checks against `results/gs_compress/evidence/`, `results/paper2_fulltable/evidence/`,
  `results/dynport_offline/evidence{L1,L2,L3,v4,_4d12bit}/` (R-D working points, J1/J2/J3 21-cell
  grid, oracle decomposition, tail census, codec timing, 12-bit/4-bit points, sim3 diagnostic).
- Numbers spot-checked rather than exhaustively recomputed; no discrepancy found in any checked value.

---

## 1. Recommendation

**Minor Revision** — 主题聚焦、论证诚实、实验量扎实，但方法新意整体偏弱、codec 部分存在
"宣称与贡献不对等"的边界问题（§5 的"发现/洞见"表述超过文中证据），以及若干必须补清的口径定义，
不修则审稿人无法确认可复现性与主张范围。

## 2. Five-dimension scoring (CVM criteria)

| Dimension | Score | Basis (one sentence) |
|---|---|---|
| Novelty | 3/5 | 三个贡献在组件层面均有先例（uniform quantization+entropy 是教科书级；DynaGSLAM 的动态高斯管理是既有机制；heavy-tail 承重在 MGS-SLAM/PWAS 已有近邻），本文的 delta 是"动态 SLAM 地图这一输入分布"上的系统性刻画与离线重定位——真实但偏薄，且 §5 的"发现"式表述把新意说到证据之上。 |
| Technical soundness | 4/5 | 实验设计（同机同协议横比、held-out 面板、oracle 上限、21/21 网格、negative control、bit-identical 静态冻结、判据机）是近年投稿中少见的严谨；抽查的每个关键数字与工件一致；主要扣分点是指标 J1/J2/J3 及"通过判据"未在正文定义、online/offline 对照非单变量且带 pose confound。 |
| Significance | 3/5 | "动态场景 SLAM 地图是一等对象"的问题意识有价值，§6 的"抹除代价主要由缺几何而非缺运动构成"是一个可迁移的结论；但 codec 的绝对收益（几 MB 地图、近无损 ~6×）在工程重要性上有限，repair 输出形态（layer sequence 非 drop-in）削弱了下游可用性，整体影响落在"有价值的案例研究"档。 |
| Presentation | 4/5 | 结构清晰、四问主线贯穿、边界句（"not a result of this paper"、"honest unit"）写作成熟，图 1/2/9/11 直观；扣分：指标定义缺失（J1–J3 只在表注出现）、Fig.6 判据阈值未在正文或图注给出、§3 PSNR/FPS 段落在表格外散落、若干关键量（ΔPSNR 的掩码口径、"统计等同"的检验）未交代。 |
| Reproducibility | 4/5 | 全部数字带工件注释、声称释放 raw outputs、同机协议与补充分节、判据机与 threshold 落盘（locked thresholds 在工件中可查）——远超 CVM 一般水平；扣分：正文未给出任何"如何重跑"的线索（脚本名、批次入口），表 4 的"held-out"列没有面板组成，且 §5 声称的 7 个被淘汰方案没有任何可复算证据。 |

## 3. Strengths (numbered)

1. **问题意识与定位清晰**。把"动态场景 splatting SLAM 的地图"作为一等研究对象，四问
（里面有什么 / 能压多小 / 反动态范式在地图侧代价多大 / 抹掉的内容能否离线装回）在 Intro、
各节、Discussion 三处一致兑现；贡献栏（3 条，全地图侧）与正文一一对应，没有贡献栏承诺正文不兑现的情况。

2. **评测纪律在 CVM 投稿中罕见地严格**。全局协议段（tex L283–297）一次性声明 ATE 口径
（Horn SE(3)、三 seed）、渲染帧集差异（codec 表 vs 系统表的 PSNR 不可跨表比较）、"不同批次数字
永不混入同一表"；Tab.1 把"独立批次"的 prior stack 行与"同机复现"的 11 方法行分开标注；
发散格如实保留（Co-SLAM 10^4 cm 量级照实报）；RGD-SLAM/DynaGSLAM 组内失败也被点出
（tex L227–229），不把横比读成"全胜"。

3. **"反动态代价"一节（§6）是全篇最有骨头的内容**。oracle 上限设计（GT 深度反投影、密度按
建图所见）与几何/外观拆解（P2c 无运动 retention 0.80–0.93 vs P4 冻结 0.10–0.39，tex L602–605）
把"抹除代价主要是缺几何"这一结论钉在可检验的实验上；"+17.9–22.2 dB 集中于掩码内部、
随拥挤度单调"（tex L551–562）与工件 `dyn_cost_5seq_2026-10-05.md` 逐位对拍一致。
这是三个贡献中新颖度与可信度匹配最好的一个。

4. **repair 算子（§7）的控制实验体系完整**：负对照 C−（错位插入 → 动态区误差 1.33–2.31× 更差，
tex L689–695，工件 J7 跨 7 序列一致）、naive 对照（无生命周期/静态保护 → 静态区 −11.7~−16.7 dB，
tex L666–668）、在线对照（+95%/+89% 开销且静态受损，tex L697–700）、"21/21 全过 + 判据机
+ locked thresholds"（工件逐一核验通过）。静态层 bit-for-bit 冻结（J9/J5 两态核验落盘）是
"无静态损伤"主张的干净证据。

5. **匿名与自引合规**：全文无 our/my/单位/致谢/项目号；前作栈以 "Prior RGB-D stack" 第三人称出现，
并在 Tab.1 注、"They are not a result of this paper"（tex L207）、Discussion（tex L732–734）三处
反复切割边界；SWBA/闭环一字未提。自查规范与正文执行一致。

6. **held-out 泛化与诚实登记**：codec 主表 42 图 + 36 图留出面板（近无损 5.96× 两处完全一致）、
"位宽与范围在面板渲染前固定"（tex L460–461）、4D codec 的 12-bit 与 4-bit 点补测落盘
（含 4-bit 全破线的诚实记录）——审稿人常见的"过拟合自报"担忧在这里有实际防线。

## 4. Major issues

**M1. 指标 J1/J2/J3 与"通过判据"在正文中从未定义，读者无法独立判定 §7 的核心主张。**
证据：tex L647–652 第一次出现 J1/J2/J3 时只给了一句话描述（"J1, the dynamic-region PSNR gain over
the erased baseline"等），判据阈值（J1 ≥ 2.5 dB、J2 ≤ 0.70、J3 ∈ ±0.25）只存在于
`manifest_offline_L1_L3.json` 的 `locked_thresholds` 字段和表 8 注的"±0.25"，正文与图 6 的
"criterion broken（shaded）"没有任何数字阈值；"21/21 过"（tex L652）的判定标准读者无法核验。
为什么重大：这是 §7 全部结论（"offline repair works"）的判定函数；指标未定义 + 阈值未公布 =
核心主张不可验证。这不是"数字错误"，而是论证可检验性的缺口——按 CVM 惯例，指标应在协议段
或 §7 开头定义一次，阈值入正文或补充材料。
处置：纯文字可改（补充材料已有全部材料，把定义与阈值写进正文/附录即可）。

**M2. §5 codec 的"发现/洞见"表述超过证据：声称的机制贡献与论文自身展示的机制证据不匹配。**
证据：tex L500–510（"What each mechanism buys"）把"suppressed-primitive exclusion 是最大杠杆"
（8.12×→6.20×）、"rot3 省 0.5×"、"预测器不省字节只保精度"作为机制发现呈现，但：表 5 只对
crowd2 一个序列、一个位宽点给出消融；"排除被抑制基元"这一最大杠杆与 §5 主表（静态地图 codec）
完全无关，是 §5.2 的 4D 层 codec 专有机制；且该机制的发现史（探针报告
`probe_4d_compress_2026-10-12.md`）经历了两次 bug 修正（漏编码、链式赋值）——最终数字本身已核验
（8.12×/J1 7.63 与消融表逐位一致），但论文呈现的"洞见"语气（"two findings carry over directly",
tex L478–481）与"四个机制各司其职"的断言，在只有一个序列的消融上显得过度。为什么重大：
这是"贡献②的 delta 部分"的承重墙；若审稿人质疑单序列消融，整个 §5 的机制叙事就塌。此外
"我们系统化筛查了七个方案、无一改进"（tex L443–448）没有任何附录证据支撑，是孤证式断言。
处置：需要小规模新实验（至少把 4D 消融扩展到 2–3 个序列）或降格表述（把机制陈述改为
"on crowd2 we measure"），二选一。

**M3. 绝对 PSNR 量级完全无参照，"15 dB 全图 PSNR"既未被解释也未与任何外部工作对位。**
证据：表 4 全图 PSNR 15.38 dB（源）、§3 文本给 baselines 14–25 dB 与 prior stack 21.8 dB，
但没有任何一句解释"为什么动态序列全图 PSNR 只有 15 dB"（掩码区/空洞/渲染协议导致？），
也没有一个外部文献数字（MonoGS 原文、DGS-SLAM 原文在各自协议下的 PSNR）作为坐标系；
"统计等同"（tex L458 "statistically identical"）未给检验。为什么重大：审稿人无法判断
15 dB 是否处于该领域正常水平，进而无法判断近无损 6× 的"无损"声明的意义（在 15 dB 尺度上
0.01 dB 的损失是否真的无关紧要）；"ΔPSNR 在 15 dB 地图上的含义"是全文最需要被解释的数字
而文中恰好缺失。为什么不是 M1/M2 级别的硬伤：不涉及主张真实与否，只涉及读者能否读懂主张。
处置：纯文字可改（一段"为什么绝对 PSNR 低 + 与 MonoGS/DGS-SLAM 原文口径对位"），
不需要新实验。

**M4. §3 的 PSNR/FPS 横比段落在表外散落、无协议，且 8 个方法中有 3 个被标 "–"——选样与
覆盖准则未交代。** 证据：tex L245–260 给出 19.7–25 dB（DGS-SLAM/RGD-SLAM）、14–20 dB（其余）、
0.2–2 FPS vs 50–72 FPS 等数字，但既不在表中、也没有任何协议说明（渲染帧集？掩码？单图还是
全序列？）；"eight reproduced systems with a reported rendering path"与表 1 的 11 行之间的关系
未说明（哪 8 个？）；DynaSLAM/NGD-SLAM/ORB-SLAM3 无渲染路径被标 "–"，但表 1 中它们有 ATE——
为什么横比只选 11 个方法、为什么渲染只覆盖 8 个，选样准则没有一句话。为什么重大：
§3 是全文的"坐标系"承重墙，若 PSNR 段没有协议，读者只能把它当八卦数字；
而"系统横比是背景而非贡献"的声明（tex L206–207）依赖这段的可靠性来兑现。
处置：纯文字可改（把该段数字落进一张小表或补一句协议，说明选样准则）。

## 5. Minor issues

1. **"3.2–7.1×10^4 基元 / 2.6–5.7 MB"（tex L312–313）与工件基数不符的读法风险**：
`storage_census` 的 baseline 3-seed 均值是 3.2–7.1×10^4（对），但正文说"seven Bonn sequences"，
而 §4 的重尾普查是 14 图（2 臂×7 序列）；"all fourteen inspected maps"（tex L355）与
"the seven Bonn sequences"两个基数并存，读者需自行推断 14 = 7×2。建议在 §4 开头一句话说明
"7 序列 × baseline/final 两臂"。

2. **Fig.1 caption 的 "+6.8 dB"（tex L137）无工件键且与正文量级口径不完全对齐**：
正文 §7 报 J1 范围 5.49–8.95 dB（seed0 crowd2 是 7.95），图注用 +6.8 dB 未注明来源组合
（可能是 seed 均值或某一帧）；且图注说 "restores erased dynamic content at the same poses"
与 §7 的 samepose 口径一致，但 6.8 这个具体值在 manifest 中没有直接对应项。建议要么给
"median over crowd2 frames, seed 0"之类出处，要么用范围值。

3. **表 6 与正文对静态区的说法不一致**：表 6 caption 说 "no sequence damages the static region
(all static changes are positive, +0.04 to +0.39 dB)"，而正文 tex L616–618 说 "nine change the
static-region PSNR by +0.04 to +0.39 dB and the tenth by −0.03 dB"。表注把 −0.03 这一格抹掉了
（表格里 5 行全是正数，因为表 6 是 baseline 臂，−0.03 出现在 gate 臂 crowd2）——正文与表各说
各的、需要读者自行拼合。表注应明确"表中为 baseline 臂；gate 臂含一格 −0.03"。

4. **表 4 的 held-out 列只有三个工作点，没有面板组成**：读者无法知道 36 张图里有哪些序列
（正文 tex L456–457 提了一句五 TUM + 一 Bonn，但表里没有）；且 held-out 列的 "15.90/15.90"
（近无损）在表 4 中与源行 15.90 重复出现，容易误读为"held-out = 主表源"。建议表注列面板清单
或指向补充材料。

5. **§5 的 "cost" 段（tex L467–473）时间数字是单序列单次测量**（`codec_timing.json` 6 行、
每行 1 次 reps=3），正文以 "0.7 μs/prim at near-lossless, 7.4 μs at aggressive" 呈现，
但 aggressive 点 5.2–9.5 μs 的跨图散布是 1.8×，0.7 与 7.4 是极端值还是中位未说明。
建议给中位 ± 范围，或注明单图测量。

6. **表 3（效率）只有一行（一个中位）**：FPS 1.162/0.879、excl./conc. 1.32× 声称基于
"three sequences (balloon, crowd2, person_tracking)"，但只有中位数呈现，无逐序列值；
caption 里 "concurrency costs a factor of 1.0–1.8" 的 1.0–1.8 范围没有来源行。对 CVM 读者
这可能是最没信息量的一行——建议要么给三序列三行，要么删表留一句。

7. **术语不一致**："prior stack"（正文多处）、"Prior RGB-D stack"（表 1 行名）、
"the stack"（tex L106）混用；图 1 里 "PRIOR STACK" 大写样式与正文斜体样式不一致。
建议全文统一为 *Prior RGB-D stack*。

8. **§6 的表 6 只有 5 个序列（10 图），而 §7 是 7 序列（21 图）**：正文 tex L552 说
"five Bonn sequences (ten maps)" 且给了原因口径（canonical 掩码的 M_bad 子集），但 §6→§7
的序列集合不连续（balloon、person_tracking2 只出现在 §7），读者会问为什么 §6 的代价分析
不覆盖全部 7 序列。建议一句话说明选择口径（balloon/pt2 在 bad 子集上不可判？）。

9. **引用完整性小问题**：正文引用 27 篇（tex L144–193 全部出现于参考文献 [1]–[28]，PDF 核对
无孤儿引用）；但 §3 提到的 "supplementary material"（tex L212）在投稿 PDF 中不存在——
CVM 单盲投稿通常允许补充材料，但正文应说明其存在形式（附件？网站？），否则 "protocol is
detailed in the supplementary material" 是死引用。

10. **图 4 底部子图的序列标签在 PDF 排版中严重错位**（`pdftotext` 显示 "d2 on d3 1 2 2 d pt pt on ow ow llo ow llo cr ba cr cr ba" 乱序）——可能是文本提取伪影，但建议目检 PDF 图 4 的
x 轴标签是否可读；同样图 5 的图例（balloon/crowd/crowd3/pt2 等）在提取文本中乱序，需目检。

## 6. Actionable checklist (by priority)

### P0 — 不修必拒（2 项）
1. **M1：正文定义 J1/J2/J3 与判据阈值**（纯文字可改）。最低要求：§7 首次出现处给公式/
一句话定义 + 阈值（J1≥2.5 dB, J2≤0.70, J3∈±0.25），并把 "21/21" 的判定函数写进协议段或
补充材料标题下。不做则 §7 核心主张不可验证。
2. **M2：4D codec 机制消融扩展或降格**（需要新实验 或 纯文字可改）。二选一：
(a) 把表 5 的消融从 crowd2 扩展到至少 2–3 个序列（每个机制的去留都过判据机）——
这是首选，工作量小（脚本已存在）；(b) 若不做实验，把 "What each mechanism buys" 降格为
"on crowd2 we measure" 并删除 "The four mechanisms play different roles" 的概括语气，
同时把 7 个被淘汰方案从正文断言改为一句带过 + 补充材料引用。不做则 §5 机制叙事
（贡献②的 delta）悬空。

### P1 — 强烈建议（4 项）
3. **M3：加绝对 PSNR 参照段**（纯文字可改）：解释 15 dB 量级的成因（掩码区、渲染协议、
动态序列特性），并给 1–2 个外部文献在原文协议下的 PSNR 对位。
4. **M4：把 §3 PSNR/FPS 散落数字整理成表或补协议**（纯文字可改）：给 8 个渲染方法的
渲染协议一句话（帧集、掩码、是否全序列均值），并交代 11 选样准则。
5. **Minor 1：统一图 1 caption 的 +6.8 dB 出处**（纯文字可改）：给工件键或改为范围口径。
6. **Minor 3：修表 6 caption 与正文的静态区口径不一致**（纯文字可改）：注明表中为 baseline
臂，gate 臂含 −0.03 dB 一格。

### P2 — 打磨（6 项）
7. 表 4 held-out 列加面板组成注（纯文字可改）。
8. §5 cost 段时间数字给中位 ± 范围（纯文字可改）。
9. 表 3 效率行给逐序列值或删表留一句（纯文字可改）。
10. 统一 *Prior RGB-D stack* 术语样式（纯文字可改）。
11. §6→§7 序列集合不连续加一句说明（纯文字可改）。
12. 目检图 4/图 5 的轴标签与图例排版（纯文字可改）。

## 7. Additional observations and anticipated objections

**关于 §6 oracle vs §7 可实现的关系**：正文处理得基本到位——明确标 oracle 为 "what the erased
content is worth, not what any system achieves"（tex L599–601）、§7 主动解释 J2 范围与 oracle
残差范围重叠"是预期而非矛盾"（tex L658–660）、并把差距归因于 sensor depth + 静态保护代价。
但有一个细节值得补强：oracle 的 0.80–0.93 retention 与 §7 的 J2 0.23–0.61 之间，正文只说
"already recovers most of the recoverable error"而没有给出这两个数之间可推导的关系式
（oracle residual 0.22–0.38 vs 算子 0.23–0.61 的数值重叠其实很接近，正文的"overlap"表述
可以更具体）。建议加一句把两个数值区间直接并置。

**关于 "not a result of this paper" 声明的边界**：三个位置（tex L207、表 1 注、L732–734）都
在强调 prior stack 测量是背景。这是诚实且必要的；但审稿人视角的一个风险是"该声明反过来
削弱了论文的自我支撑"——§4/§6 的全部数据都来自这一个栈，若该栈有任何未被披露的系统性
特性（如 mask 通道、书签字段恒常数是栈的实现细节而非动态 SLAM 的普遍事实），结论的
普遍性就取决于一个不可见的黑箱。作者已用 held-out 面板覆盖 codec，但 §4 的"30% 死重"、
§6 的"+17.9–22.2 dB"都只有这一个栈的证据。建议在 Discussion 第三边界（"not a cross-system
law"，tex L754–756）处再往前半步：明示"该书签字段是本文所研究的栈的实现细节，其他动态
SLAM 栈的图是否同样含死重字段，取决于其实现"。

**如果存在历史审稿，我预期的常见异议**（我未读任何历史审稿记录，以下是我独立推导的、
审稿人最可能提出的问题，供作者对照）：
1. "压缩比是拿自己格式的 20-field float32 当基线算的，没和 HAC/Compact3D/SOG 比"——
  论文已在 L414–418 主动给出不比的理由（输入分布不同 + 参数自由），我认为该理由成立但
  审稿人一定会再问一次；建议补充"把 HAC 等直接跑在本文地图上会怎样"的一句话说明
  （不需要全量实验，说明输入格式不兼容即可）。
2. "3DGS 地图压缩的增量贡献是什么"——CGS-SLAM/DiskChunGS 是静态 SLAM 压缩，
  TC3DGS/MEGA 是动态场景压缩，本文的定位"动态 SLAM 地图 + 离线 codec"在文献矩阵中
  确实有一个空格，但审稿人会要求把对比框定得更细（特别是与 DiskChunGS 的
  chunk-based 方法与 TC3DGS 的 temporal grouping 的差异句）。
3. "修复算子的实用性"——layer sequence 不是 drop-in 的 merged map，任何下游消费者
  （重定位、回环、编辑）都用不了这个输出形态；论文 L707–716 已把这一点写成
  "design decision, not a limitation"，语气正确，但审稿人仍会问"谁能消费它"，
  建议在 Discussion 给一个具体的消费示例（如重放/动画/检索）来回答。
4. "21/21 全过是否意味着判据太松"——J1≥2.5 dB 的门对多数序列是中等门槛，审稿人可能
  质疑为什么不用更严的门（如 J1≥5 dB）；建议在补充材料给出门的设定理由
  （prereg 判据机的历史依据）。
5. "为什么在线对照只有两个序列"——L697–700 已自认（"measured on two sequences"），
  且声明非因果对照；审稿人可能仍要求把在线臂的 pose confound 说透（表 8 注已覆盖）。

## 8. Honest closing

这篇文章的立论（地图是一等对象）、测量纪律（同协议横比、oracle 上限、判据机、全网格）、
与边界表述（prior stack 非结果、比率而非字节是诚实的单位）达到了 CVM 投稿中少见的水准，
§6 的"抹除代价主要是缺几何"是可迁移的结论，§7 的对照体系（C−、naive、online、bit-identical
冻结）是教科书级的控制实验。主要弱点集中在两处：codec 的机制新意与证据规模不匹配
（单序列消融撑起"机制各司其职"的叙事），以及核心判据（J1/J2/J3 与阈值）没有进入正文——
前者需要一点实验或降格，后者只需一次文字修订。以 Minor Revision 收口是公平的：按 P0 清单
处理后可接受；若作者选择把 4D 消融扩到 3 序列、并补一段 PSNR 量级参照，这篇论文在
"地图侧研究"这个细分里会是站得住的案例。
