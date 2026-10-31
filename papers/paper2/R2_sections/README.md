# R2_sections/ —— 论文 2 重写：逐小节讨论稿

> **用法**：每个小节一份文档，**先议后写**——先把"这节讲什么、用哪张表、用哪张图、多少字"
> 与用户过一遍，点头后主会话才动笔写正文。文档与正文一一对应，是写作轨的对话载体。
> **上游**：`papers/paper2/R2_NARRATIVE.md`（叙事锁定 v3）。
> **账本**：重写立项（见 `DECISIONS.md`）。

## 文档模板（每份都要有这几栏）

```
# NN <节名>
## 1. 这一节要讲的一句话（thesis）
## 2. 承接/引出（与上、下节的衔接）
## 3. 用哪些表（表号 / 内容 / 为什么在这）
## 4. 用哪些图（图号 / 内容 / 为什么在这）
## 5. 篇幅预算（页/半页）
## 6. 数字来源（工件路径；gate2 键）
## 7. 红线自查（禁语、口径）
## 8. 待用户确认项
```

## 小节清单（9 份文档，对应 10 节；`09_discussion.md` 合并 §9 Discussion + §10 Conclusion）

| # | 文档 | 节名 | 状态 |
|---|---|---|---|
| 01 | `01_intro.md` | Introduction | 待议 |
| 02 | `02_related.md` | Related Work | 待议 |
| 03 | `03_system_comparison.md` | System & Comparison（**新，含横比表**） | 待议 |
| 04 | `04_map_anatomy.md` | What a Dynamic-Scene Map Is Made Of | 待议 |
| 05 | `05_codec.md` | A Simple Baseline Codec | 待议 |
| 06 | `06_anti_dynamic_cost.md` | The Cost of the Anti-Dynamic Paradigm | 待议 |
| 07 | `07_offline_repair.md` | Recovering Dynamic Content Offline | 待议 |
| 08 | `08_measurement.md` | Measurement（分区协议仪器） | 待议 |
| 09 | `09_discussion.md` | Discussion + Conclusion（合稿） | 待议 |

## 可复用资产（v0 留档，见 `../archive/v0_2026-10-10/`）

- **图（9）**：fig1_pipeline（示意，需重画以去 codec/repair 之外的旧叙事）/ fig2_render_crowd2 /
  fig2b_render_person_tracking / fig3_trajectory_crowd2 / fig4_tail / fig5_accounting /
  fig6_dynport_repair / fig_rd_curves。
  （fig_storage_accounting 2026-10-13 移出活区：正文不引用、含 gate 臂红线；生成物留
  `results/gs_compress/figs/` 作 provenance。）
- **表（8）**：tab1_main / tab2r_render / tab3s_static / tab4_efficiency / tab5_ladder（**梯子，拟弃**）
  / tab_dynport / tab_rd / tab_storage，+ 新增 tab_baseline（横比，机写）。
- 复用判据：**服务新叙事**才留；梯子表 tab5_ladder 因 SWBA 排除而弃。
