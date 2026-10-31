# fig_teaser 定稿 provenance（2026-10-18；用户终审选定版式 F）

- **角色**：论文首页图（Fig. 1，单栏，第 1 页右栏顶部；官方样张同款图位）。
- **类型**：**实验渲染照片拼图（真实工件）** ⇒ 红线表判定**不得用生成模型**。
- **生成器**：`scripts/02_analysis/paper2_fig_teaser.py`（matplotlib；字体族走
  `paper2_figstyle.py`；工件加载与两条机写数字聚合复用 `paper2_fig1_overview.py`）。
- **可复跑（两步）**：
  `python scripts/02_analysis/paper2_fig1_export_assets.py`（导出 `/tmp/fig1_assets/*.npy`）→
  `python scripts/02_analysis/paper2_fig_teaser.py`（重出 `fig_teaser.pdf/png`）。
- **工件**（crowd2 f621 samepose 链）：`erased` = R0 抹除态、`repaired` = R1 修复态；
  codec 对 = `results/gs_compress/render/L1_crowd2_{baseline,b16-8-8-8-8}/cmp_f00240.png` 右半。
- **机写数字**：6.0× = 42 份 `evidence/rd/L2_*_b16-8-8-8-8.json` ratio_full 均值（5.96 显示 6.0）；
  +6.8 dB = 三序列 samepose J1 median 均值（6.82 显示 6.8）。
- **版式**：上行 erased→repaired（钩子），下行 stored map→codec decode（压缩证据）；
  蓝 = 既有范式，橙 = 本文离线算子；行内箭头成链。
- **已知外观（诚实记录）**：repaired 面板近距可见个别高斯原语（尺度偏大/颜色离群）——
  §7 已登记的 fidelity 取舍，属真实渲染；印刷尺度下收敛为"人回来了"。
- **提交副本**：`papers/paper2/figs/fig_teaser.{pdf,png}`
  （`tests/paper2_fulltable/test_paper2_figures_committed.py` 逐字节镜像守护）。
