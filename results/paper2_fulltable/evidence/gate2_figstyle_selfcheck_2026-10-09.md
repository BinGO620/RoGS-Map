# G2/G4 自核销 — 其余 8 图样式统一重构轮（2026-10-09 深夜）

- **G2 审查**：slam-critic 判决档，报告 `/tmp/slam_critic_g2_figstyle_2026-10-09.md`，
  结论 **Reject（1 致命 + 5 重大 + 4 次要）**；审查对象 `5dfbcb69e`。
- **G4 复核**：同 critic，结论 **Accept-with-conditions（无致命；2 重大 + 2 次要）**；
  整改 commit `86781a486`/`e3db21948`。

## 致命（1）销项

| # | 问题 | 整改 | 验证 |
|---|---|---|---|
| C1 | 字号门声称不实：以**错栏宽**（双栏 495pt）算，实测 fig3/4/5 是**单栏图**（栏宽 3.28in），native 远大于槽宽被缩小，fig4 字实印仅 2.71–4.64pt << 5pt | ① 单栏图 native 收到槽宽（fig3 4.0→3.0in、fig5 4.6→3.1in、fig4 纵向堆叠 3.1×3.3in）⇒ 缩放≈1；② 新建**可复跑字号门** `paper2_fig_textsize_audit.py`（按真实栏宽复算：双栏=6.875in、单栏=3.28125in）；③ 测试绑定 `test_figure_text_size_meets_floor` | 9 图全 PASS，min effective = **5.25pt**（fig4）；critic 负对照：旧 fig4 复算 2.86pt ⇒ FAIL（门有效） |

## 重大（5）销项

| # | 问题 | 整改 |
|---|---|---|
| M1 | `paper2_figstyle.py` 未入库即被三生成器 import ⇒ 分 commit 落库会 ImportError | 入库 + `test_shared_figstyle_is_importable` 守护 |
| M2 | programmatic 回退锚点写入受守护的 evidence/figs/ 且未入 MIRRORS ⇒ 跑一次弄脏 git | 改写图工作区 `figures/fig1_pipeline/fig1_pipeline_programmatic_backup.*` + 从 `__main__` 摘出；evidence/figs 无残留 |
| M3 | "字号门 PASS"无可复跑工件 | = C1 脚本，入库 + 测试绑定 |
| M4 | fig1 字体族 DejaVuSans 与其余 8 图 LiberationSans 不一致 | fig1_overview.py 并入 `_fs.FONT_STACK`；**G4 复议发现：改了生成器但没重出图（成品仍 DejaVuSans）⇒ 重出图后 9 图 pdffonts 全 LiberationSans**（G4 条件②） |
| M5 | fig3 单面板加 (a)、fig_storage 不加，标号规则不一致 | fig3 去单面板 (a)；仅多面板图（fig4/fig_rd）加标号 |

## 次要（4）

S1 线宽 >1pt：RC 默认改 1.0 + **显式强调线 1.1/1.3/1.4 全收 ≤1.0**（G4-③）✅ /
S2 fig6 图内列标题与图注重复：图注改"Columns (labelled in-figure)" ✅ /
S3 fig4/fig_rd 加 (a)(b) 但图注写 left/right：图注改 (a)/(b) ✅ /
S4 build 脚本 undefined_ref 指标失真：非本轮引入，**不处置**（登记）。

## G4 新发现（G2 级）处置

- **[重大] 碰撞门无可复跑工件**（与 C1 同属"声明 vs 工件"类，同轮第二次）：审计器随仓入库
  `scripts/02_analysis/vendor/audit_figure_collisions.py` + 门包装 `paper2_fig_collision_audit.py`
  + 测试绑定 `test_figure_collisions_pass` ⇒ 碰撞 9/9 PASS 有工件可复跑。
- **[次要②]** 编译门 fig2/3/5 与提交副本差异仅 PDF `/CreationDate`：不处置（元数据，非内容）。

## 本轮顺修（既存缺陷，非 G2 要求）

- 图例白底 + 移出数据区（网格线/数据线穿图例文字，旧版即 FAIL）
- x 轴序列标签旋转 45° 防相邻重叠（fig4/fig_storage）

## 门（整改后自跑）

编译 **14 页（=上限）/ 0 overfull / 0 undefined ref**；字号门 **9 图 PASS（min 5.25pt）**；
碰撞门 **9/9 PASS**；守护 **10 测**；全量 **590 passed**；health 0 FAIL；三方一致 `e3db21948`。

## 数据完整性（critic 已核 PASS）

fig2(15)/fig2b(15)/fig6(20) 内嵌位图 pdfimages md5 与旧版全等；曲线图仅样式路径；
fig6 frames.json 同源 ⇒ 样式重构**未触碰任何数据像素**。
