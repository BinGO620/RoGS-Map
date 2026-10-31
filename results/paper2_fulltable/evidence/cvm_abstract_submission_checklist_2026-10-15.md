# CVM 2027 摘要提交清单（2026-10-15 备料）

> **性质**：投稿演练材料（真正提交 = D3 用户动作）。摘要 DDL **2026-10-23 (AoE)**，全文 10-26。
> **被备对象**：v8.4（HEAD `f2421c3ec`，sha256 `6a805080b351b3f12080fd48fa83e078527fbf40645c32b704361302059ec75d`）。
> **门禁（提交时已过）**：pytest 345 passed / health 失败 0 / build 14 页（overfull=1 既有 tab_baseline）/ 三方一致。

## 提交字段

| 字段 | 值 | 来源 |
|---|---|---|
| 标题 | Dynamic-Scene Gaussian Maps: Anatomy, Compression, and Offline Repair | `paper2_cvm.tex:52` |
| 关键词 | dynamic scenes, 3D Gaussian splatting, SLAM, map compression, offline repair | `paper2_cvm.tex:84` |
| 页数 | 14（上限 = 14，顶格） | build 输出 |
| 匿名 | 审稿版：无作者栏、`\cvmPaperID{****}` 占位 | `paper2_cvm.tex:40` |
| Paper ID | 投稿系统分配后填入 `\cvmPaperID` | CVM 系统 |

## 摘要正文（提取自 abstract，供复制粘贴）

Dynamic-scene RGB-D SLAM systems built on 3D Gaussian splatting keep moving content
out of the map, yet the maps they produce are rarely studied on their own terms. We
study the map of such a system across four questions: what it contains, how small a
plain offline codec can make it, what the anti-dynamic paradigm costs on the map
side, and whether the erased dynamic content can be put back offline. To anchor the
study, we reproduce eleven published SLAM systems on the BONN dynamic benchmark under
a single protocol and report the regime this paper targets: static methods fail
outright on dynamic sequences, while dynamic methods, including the prior RGB-D
stack used as-is throughout this paper, stay accurate. Opening the stack's maps
shows a third of their raw bytes are constant bookkeeping the rasteriser never
reads, two structural redundancies the codec can exploit, and a load-bearing heavy
tail that loses 0.7 dB of PSNR when clipped. A deliberately plain codec with
per-map quantisation ranges (uniform quantisation with entropy coding, no learned
parameters) reaches 6× at ~0.01 dB loss (near-lossless) and 15× at an aggressive
working point, verified on a held-out panel of unseen TUM and Bonn sequences; the
same scheme compresses the repair operator's layered output to a near-lossless ~8×
by exploiting temporal smoothness and structural redundancy. The anti-dynamic
paradigm costs +18 to +22 dB in the erased regions, most of it recoverable by
inserting the dynamic geometry back into the map. An offline repair operator that
moves dynamic-content management out of the online loop restores the erased content
with 5.5 to 9.0 dB of PSNR gain and no static-region damage, at a fraction of the
total mapping time.

## 提交前检查（用户执行 D3 时对照）

1. [ ] CVM 系统创建账号/登录，进入 Abstract Submission（摘要 DDL 10-23 AoE）
2. [ ] 粘贴标题 / 摘要 / 关键词（上表）
3. [ ] 拿到 Paper ID 后填入 `paper2_cvm.tex:40` `\def\cvmPaperID{...}`
4. [ ] 重新编译 build_paper2.sh 确认仍 14 页
5. [ ] 上传 PDF（审稿版，匿名）
6. [ ] 全文提交（10-26）时复核同上

## 备注

- **不做**：审稿版不加作者栏 / repository 链接（破坏匿名；camera-ready 阶段再加）。
- Availability 维持 "upon request"（R3 审稿人 N4 接受的非阻塞形式）。
- 模拟 CCF-C 审稿（`review_prompt_ccfc_2026-10-15.md`）结果若出新意见，先处置再提交摘要。
