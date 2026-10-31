# CVM 2027 摘要提交清单（v8.15 刷新版，2026-10-19）

> **性质**：投稿演练材料（真正提交 = D3 用户动作）。摘要 DDL **2026-10-23 (AoE)**，全文 10-26。
> **被备对象**：v8.15（快照：主论文 `archive/pdf_snapshots/paper2_cvm_v8.15_2026-10-19.pdf` sha256 `6fbc0095`；
> 补充材料 `supplement/archive/supplement_v8.13_2026-10-19.pdf` sha256 `fe294411`）。
> v8.15 = v8.14（摘要不动）加**内容扩展**（§7 技术细节 +20 行 + Limitations 段落 +16 行；填充至 14 页 2/3）。
> v8.14 = v8.13（补充材料不动）加**摘要润色**（7 处改动：删术语负担、拆长句、加限定、具体数字；275 词→261 词）。
> v8.13 = v8.12（正文不动）加**补充材料逐字审稿整改**（7 条：Fig. S1 题注删 §7 指针改补充材料侧边界陈述；
> Protocol 段补 WildGS-SLAM 单目 RGB 说明；删防御式括注 `(not fabricated)`；S1--S8 指代分离表与图；
> 引用措辞统一 `the main paper's Table~4`；`seeds nothing`→`fixes no random seed`；
> `from`→`in the main text`；补充材料 6 页 / overfull 0）。
> v8.12 = v8.11 加**正文逐字审稿整改**（Table 1 的 Type 列 → Family 列 3DGS/implicit/classical；
> §2 NGD-SLAM 归类订正为 ORB-SLAM3/CPU；§3 补 WildGS-SLAM 单目仅 RGB；破折号 1→0、
> 冒号 13→8、paradigm→policy 统一；14 页守住）。
> v8.11 = v8.10 加**字体/加粗修复 + 去 AI 化整改 + 补充材料字体统一**（略；LOG 详尽）。
> **门禁（v8.15 已过）**：pytest 63 passed / 主论文 14 页（849 行）overfull=0 / 补充材料 6 页 overfull=0 / 摘要 261 词 / 工作区全净。
> **取代** `cvm_abstract_submission_checklist_2026-10-15.md`（v8.4 版；摘要文本与行号均已过时）。
> **摘要文本权威来源 = 论文本身**（`paper2_cvm.tex` abstract 环境）；下节摘录供提交表单粘贴。

## 提交字段

| 字段 | 值 | 来源 |
|---|---|---|
| 标题 | A Dynamic-Scene Gaussian SLAM Map: Anatomy, Compression, and Offline Repair | `paper2_cvm.tex:42` |
| 关键词 | dynamic scenes, 3D Gaussian splatting, SLAM, map compression, offline repair | `paper2_cvm.tex:74` |
| 页数 | 14（上限 = 14，顶格） | build 输出 |
| 匿名 | 审稿版：无作者栏、`\cvmPaperID{****}` 占位 | `paper2_cvm.tex:25` |
| Paper ID | 投稿系统分配后填入 `\cvmPaperID` | CVM 系统 |

## 摘要正文（提取自 v8.14 abstract，供复制粘贴）

Dynamic-scene RGB-D SLAM systems built on 3D Gaussian splatting keep moving content
out of the map, yet the maps themselves are rarely studied. We
study the map of such a system and ask what it contains, how small a plain offline
codec can make it, what erasing dynamic content costs, and whether
the erased dynamic content can be put back offline. To anchor the
study, we reproduce eleven published SLAM systems on the BONN dynamic benchmark under
a single protocol and establish the regime this paper targets. Static methods fail
outright on dynamic sequences, while dynamic methods, including the prior RGB-D
stack used as-is throughout this paper, mostly stay accurate. Examining the stack's maps
reveals 30% of their raw bytes are constant bookkeeping the rasteriser never
reads, two structural redundancies the codec can exploit, and a load-bearing heavy
tail in the attribute distributions that loses 0.7 dB of PSNR when clipped. A plain codec with
per-map quantisation ranges (uniform quantisation with entropy coding, no learned
parameters) reaches 6× at ~0.01 dB loss (near-lossless) and 15× at an aggressive
working point, verified on a held-out panel of unseen TUM and Bonn sequences. The same scheme compresses
a layered repair output to a near-lossless ~8× by exploiting temporal
smoothness and structural redundancy. Erasing dynamic content costs 18 to 22 dB in the
erased regions, most of it recoverable by inserting the dynamic geometry back into
the map. An offline repair operator restores the erased content with 5.5 to 9.0 dB
of PSNR gain and no static-region damage, at 11 to 30% of the total mapping time.

## 提交前检查（用户执行 D3 时对照）

1. [ ] CVM 系统创建账号/登录，进入 Abstract Submission（摘要 DDL 10-23 AoE）
2. [ ] 粘贴标题 / 摘要 / 关键词（上表；**以论文 abstract 环境为准**）
3. [ ] 拿到 Paper ID 后填入 `paper2_cvm.tex:25` `\def\cvmPaperID{...}`
4. [ ] 重新编译 build_paper2.sh 确认仍 14 页
5. [ ] 上传 PDF（审稿版，匿名）+ **补充材料** `supplement.pdf`（匿名，1.06MB ≤ 50MB）
6. [ ] 全文提交（10-26）时复核同上

## 备注

- **不做**：审稿版不加作者栏 / repository 链接（破坏匿名；camera-ready 阶段再加）。
- Availability（v8.7）= 逐项列产物 "map PLYs, tracking outputs, the codec, and the rendering and
  evaluation scripts" + "released at publication" + 匿名审稿期 on-request 兜底（R4 门槛 2 字面闭合）。
- R5 模拟审稿（`review_prompt_ccfc_v8.6_2026-10-17.md`）= **Accept**（2026-10-17，4/4/4/4/5；
  报告 `papers/paper2/CVM_REVIEW_v8.6_2026-10-17.md`）；非阻塞项已采纳并重建（v8.7），可直接走摘要提交。
