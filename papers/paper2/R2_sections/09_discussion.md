# 09 Discussion + 10 Conclusion

> **状态**：已议定并落笔（2026-10-12；合稿为 §8 Discussion and Conclusion）。**上游**：`R2_NARRATIVE.md` §5。
> **正文**：`paper2_cvm.tex` §8。**两项待确认均按默认落**：① 不设独立 Limitations（融入 Discussion 写成适用条件）；
> ② 论文 3 指向句 = "an online system that embraces dynamic content rather than erasing it remains future work"
> （正向有界表述，非自陈不足）。

## §9 Discussion — thesis
三件事：①**跟踪不是本文的故事**（系统是前作栈，§3 已给坐标）；②**地图值得关注的理由**
（它是被存储/装运的东西，结构上不按通用压缩器设想）；③**修复的边界** → 指向论文 3（face dynamic / 4D）。

## §10 Conclusion — thesis
收口：把地图当对象研究；codec 压小它、解剖说明字节在做什么、重尾必须留；
量化反动态范式放弃的量（大，且主要靠几何挽回）；用离线算子把内容装回，21/21 过，在线太慢。

## 衔接
§1–§8 讲完 → §9 讨论/边界 → §10 收口。

## 表 / 图
无（纯文本）。

## 篇幅
§9 **0.75 页**；§10 **0.5 页**。

## 红线自查（**v0 存量缺陷区**）
- ❌ **禁自爆句**：v0 结论有 "We claim no state-of-the-art tracking and no new compression primitive."、
  §8 有 "We claim no state-of-the-art tracking"、codec 有 "We claim no novelty..."——**全部改写**为
  正向有界表述（"我们在协议 P 下达到 X"），保留防 salami 的边界声明（"系统是前作栈 verbatim"）。
- ❌ Limitation 不单独成节（v0 有个 `\subsection{Limitations}`）——按纪律**融入 Discussion**，
  写成适用条件。（**2026-10-11 已定（D2-029 重申）**：以"不单独成节"为准；v0 的 CVM 惯例
  小节随 v0 一起弃用，新稿不设 Limitations 节，见 D2-031。）

## 待确认
1. ~~**Limitations 小节 vs 融入 Discussion**~~ **已定（2026-10-11，D2-031）**：按 D2-029
   重申的 2026-10-06 裁定——**不单独成节**，适用条件融入 §9 Discussion。
2. §9 指向论文 3 的一句怎么写而不显得"自陈不足"。
