# L3 范围报告 —— 「codec 联动」缺口（2026-10-08）

> **性质**：**呈报项**（判据/范围本体解释问题）。**不新增判据、不改已锁条文**。
> **触发**：L2 泛化 9/9 达标（D1-035）⇒ 按 prereg §6 有资格进 L3；§6 的 L3 定义 =
> 「**全 7 序列 × 3 seed + codec 联动**」。
> **结论**：**「全 7 序列 × 3 seed」= 已锁、可执行、本批已派**；**「codec 联动」= 未定义占位**
> （无设计档、无接口、无判据）⇒ **本批不含**，缺口单列，**默认处置见 §4**。

## 1. 事实（可复核）

「codec 联动」在仓内的**全部**出现（grep `codec 联动`，4 处、同一来源）：

| # | 位置 | 文本 |
|---|---|---|
| 1 | `results/dynport_offline/evidence/prereg_dynport_offline_L1.md:148`（**源头**） | `≥2/3 泛化 ⇒ L3（全 7 序列 × 3 seed + codec 联动）⇒ 写作轨（贡献栏三条定稿）` |
| 2 | `results/dynport_offline/evidence_L2/verdict_dynport_offline_L2_2026-10-08.md:40` | 同上括号（机写复制） |
| 3 | `scripts/dynport_offline/write_verdict_L2.py:79` | 上行的生成器（复制源） |
| 4 | `DECISIONS.md`（D1-035 状态列） | `下一步 L3（全 7 序列 × 3 seed + codec 联动）` |

**无任何定义/设计/接口落点**：
- 唯一的离线算子设计档 `resources/notes/dynport_offline_design_2026-10-06.md`：`codec`/`压缩` **零命中**（L1/L2 机制、臂、判据、S0–S6 全无 codec）。
- 无 `resources/notes/*L3*`、无 dynport 侧 L3 设计档；`next_step_plan_2026-09-25/27.md` 早于 DynPort。
- 无脚本把 codec（`rd_harness.py`/`rd_sweep.py`）跑在修复图/动态层上。
- 在线 prereg（`results/dynport/evidence/prereg_dynport_L1.md:29-30`）明文把 codec 与 DynPort 机制**隔墙**：
  「本机制（瞬态保留管理）」vs「（codec/代价刻画）不变」。

⇒ 「codec 联动」是从 L1 prereg 单点注入、被判决生成器**机械复制**的**两词占位**，从未被定义。

## 2. 为什么它不是"跑一下就行"

A 线 codec 的设计面 = **单张最终地图 PLY**（`scripts/gs_compress/gs_codec.py`）：
- 读 `ALL_FIELDS` = 14 渲染字段 + 6 记账字段（`🥇` 与合并 PLY **schema 恰好一致** ⇒ 机制上可读）；
- `rd_harness.find_ply` 已找 `point_cloud/final_after_opt/point_cloud.ply` ⇒ **代码上能跑**。

**实测（本报告，`/tmp` 冒烟，已清理）**：对 L3 冒烟修复图的合并 PLY 跑 `rd_harness --bits 8,4,4,4,4`
⇒ OK（ratio_full 13.35×，PSNR 15.94）。**但**：

| DynPort 输出形态 | 语义 | codec 能否消费 | DynPort 判决状态 |
|---|---|---|---|
| **output②** 单张合并 PLY | 底图 + **单帧末层** | **能**（schema 相容） | **FAIL**（L1 v4 §3：B 口径单 PLY 静态被末帧层时切片伪影遮挡） |
| **output①** 逐 KF 4D 层序列（`dynport_causal/frame_*.npz`） | 每 KF 动态层 + 位姿 | **无通路**（codec 无动态层/多帧概念） | **PASS**（J3∧J1∧J2；用户批准的交付形态） |

⇒ 「codec 联动」若要**科学上有意义**，须先回答一个**未锁的问题**：
**压哪个形态？**（压 output② 会把 FAIL 形态端进 R-D 表；压 output① 需要 codec 侧**新增** 4D/多帧压缩通路 = 新机制研发，非"联动"）。

且**判据本身缺失**：联动要报什么量（动态区 R-D？静态区非退化？率的分母？）、门槛多少、与 A 线主表（`prereg_struct_codec_2026-10-05.md`）如何不混引——**均未定义**。

## 3. 与已锁叙事的关系

`papers/paper2/NARRATIVE_v2_system_2026-10-05.md` 贡献栏 = **2 条 + 背景**（① 地图 codec；② 地图侧代价刻画），
**无 DynPort 方法腿**（DynPort 是 D2-027 后加的方法腿；今 L1/L2/L3 是它的证据）。§6 括号里的
「贡献栏三条定稿」与锁定叙事（2 条）**也不一致** ⇒ §6 该括号整体**陈旧**，非仅「codec 联动」一词。

## 4. 默认处置（**建议**，待用户确认）

**默认 = 本批 L3 只跑已锁网格（全 7 序列 × 3 seed），「codec 联动」作为**独立缺口**另立呈报，不在本批强行实装。** 理由：

1. **判据先锁**：联动无判据/无接口 ⇒ 现在实装 = **事后选判据**（违纪：判据先于结果）。正解是先出**联动设计档 + prereg 条目**（含"压哪个形态"的裁定），过 G1，再跑。
2. **风险隔离**：把未定义的联动塞进已达标（L1/L2 PASS）的方法腿批，会**污染方法腿的干净证据链**。
3. **默认不阻塞**：L1+L2+L3 网格已是可写论文的完整泛化证据；联动属**增量**，可后补（同 L2 补 G2 的模式）。

**若用户要推进联动**，最小合规路径（三选一，均须先锁设计）：
- **甲（推荐）**：联动 = **对 output② 合并 PLY 跑 A 线 codec**，**仅作描述性 R-D 读数**（明标"该形态在 DynPort 判决下 FAIL，此处只测压缩率/PSNR 结构"），**不作贡献、不入主表**。
- **乙**：联动 = **新增 output① 4D 层压缩通路**（codec 侧新研发）⇒ 属**新机制**，须独立立项 + prereg + G1（**超出"联动"语义**）。
- **丙**：**撤销** §6 的「codec 联动」括注（更正为「L3 = 全 7 序列 × 3 seed」），缺口关闭——**若叙事上不需要地图×动态的交叉点**。

## 5. 工件

- 本报告：`results/dynport_offline/L3/report_L3_scope_2026-10-08.md`
- 源头：`results/dynport_offline/evidence/prereg_dynport_offline_L1.md:148`
- codec 接口：`scripts/gs_compress/gs_codec.py`（`ALL_FIELDS`, `read_map`）、`scripts/gs_compress/rd_harness.py`（`find_ply`）
- 算子设计档（无 codec）：`resources/notes/dynport_offline_design_2026-10-06.md`
- 冒烟（已清理，非工件）：codec 读修复合并 PLY OK（ratio_full 13.35×）
