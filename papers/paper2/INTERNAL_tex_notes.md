# paper2_cvm.tex 头部内部注释（移出记录）

> **来源**：`papers/paper2/paper2_cvm.tex` 头部 1–19 行注释，2026-10-15 按用户决定**原样移入**本文件；
> tex 头已精简为最小必要注释（4 行）。
> **原因**：原注释含机制禁语字样（见下方 verbatim 块），PDF 无影响，但 camera-ready 交付 LaTeX 源码时会泄露。
> **边界**：本文件是仓库内部记录，**不进入投稿件**——`scripts/paper2_fulltable/build_paper2.sh`
> 只打包 tex / tables / figs / template_cvm 四类，不含本目录其它 .md。

## 原样移出的注释块（verbatim）

```
% paper2_cvm.tex — 论文 2（CVM 2027 投稿，匿名版）Phase 3 新稿骨架
% Phase 3 重写完成（2026-10-12 全部 8 节落笔，10 页）。skeleton 标记已移除，
% 守护测试（test_paper2_dynport_section / test_paper2_figures_committed）恢复终稿断言。
% 守护测试（test_paper2_dynport_section / test_paper2_figures_committed）自动恢复终稿断言。
% 目标：CVM 2027（CCF-C）摘要 2026-10-23 / 全文 2026-10-26，AoE；<=14 页含参考文献。
% 叙事锁定 v3：R2_NARRATIVE.md（地图为主 + 系统横比背书）；逐节讨论稿 R2_sections/*.md。
%
% 骨架（2026-10-12 结构校准：按 CVM 2026 "3D Gaussian and SLAM" 同场论文（MGS-SLAM/GPS-SLAM）
%   惯例收至 7 顶级节；§8 Measurement 拆散入 §3 全局协议段 + 各研究块自带协议；Discussion 并入
%   Conclusion）：
%   §1 Introduction → §2 Related Work → §3 System and Comparison（含 11 方法横比表 tab_baseline
%   + 全局评测协议段）→ §4 Map anatomy → §5 Codec → §6 Anti-dynamic cost → §7 Offline repair
%   → §8 Discussion and Conclusion（合稿）
%
% 数字纪律：正文所有测量数字带 "% gate2:" 工件键注释；表格 `\input` 仅在关卡② 通过后
% （tab_baseline.tex 已过关卡② 2026-10-11，80525138c）。
% 匿名：提交版不得含单位/致谢/项目号；前作栈以 `Prior RGB-D stack` 出现，不出现于正文与 biblio。
% 禁语（R2_NARRATIVE §7）：SWBA / LoopClosure 一字不提；禁自爆句；§6 不与论文 1 栈比较；
% 不设单独 Limitations 节。
```
