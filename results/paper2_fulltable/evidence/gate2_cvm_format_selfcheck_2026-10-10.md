# G2/G4 自核销 — CVM 投稿格式收口轮（2026-10-10）

- **G2 审查**：slam-critic 判决档，报告 `/tmp/slam_critic_g2_cvm_format_2026-10-10.md`，
  结论 **Reject（1 致命 + 1 重大 + 6 次要）**；审查对象 `5bb41ef07`。
- **G4 复核**：同 critic，结论 **Accept**（1 致命 + 1 重大 + 6 次要**全部核销**，
  无新致命/重大）；整改 commit `19d2b9504` / `67254a8ba`。

## 致命（1）销项

| # | 问题 | 整改 | 验证 |
|---|---|---|---|
| M1 | 主表 "+Gate" 列实为 +SWBA+LC+Gate **三组件**，题注称"只加 gate"——等于把用户明确排除的 SWBA 又带回主表（用户第 2 问的镜像；整改引入型） | **系统表降为前作栈单列**：`MAIN_ARMS=["baseline"]`；tab1/tab2r/tab3s/tab4 单列、列头改指标名、题注改 "base stack"；含 SWBA/LC 的复合臂彻底移出主表；四梯只在附表 `tab:ladder` | G4 独立复核：主表四张全单列仅 Base；全仓 `papers/paper2/tables/*.tex` 无任何 SWBA 臂（唯一含 SWBA 的 tab5_ladder 是显式消融附表）；题注与列头一致 |

## 重大（1）销项

| # | 问题 | 整改 |
|---|---|---|
| M2 | 证据包 README 表清单陈旧（tab1 写"右侧三列"，tab5 写"col14 关键帧"） | README 表清单更新（tab1=系统 ATE 单列 Base；tab5_ladder=阶梯消融表；tab4=Base 单行）+ 门禁横幅改实（已过关卡②） |

## 次要（6）处置

S1 文件名语义已变 ⇒ `tab5_keyframe.tex`→`tab5_ladder.tex`（生成器/测试/tex/README 全改，
全仓无残留引用）✅ / S2 fps 守护按单列降 1 臂 ⇒ 阶梯表另加 `test_ladder_table_has_full_arms`
（4 臂逐位==JSON）✅ / S3 5/7 披露移至附表 `tab:ladder` 题注 + README（测试仍查 README token）✅ /
S4 陈旧注释改实 ✅ / S5 NARRATIVE 加 2026-10-10 历史注 ✅ / S6 tab5 题注 keyframe 句随重写消失 ✅

## G4 新发现（4 条文档滞后，已顺手修）

N1 测试 docstring "Base+Gate 两配置"→"前作栈单列"；N2 README 门禁横幅 "未过不得 \input"→
"已过"；N3 tex "first column of the main table"→"the main table reports that stack"；
N4 README "现 Gate (ours)" 现值残留→改实。commit `67254a8ba`。

## 门（整改后自跑）

编译 **14 页（=上限）/ 0 overfull / 0 undefined ref**；全量 **591 passed**；paper2 测试 **50 passed**；
health 0 FAIL；三方一致 `67254a8ba`；PDF 存入 `papers/paper2/paper2_cvm.pdf`。

## 数据完整性

系统表单列后数字仍逐位==JSON（G4 复核 tab1 mean/sd 逐位；tab5_ladder 28 格逐位）；
生成器数据层 `build_table()` 仍按 4 臂构建（改的是呈现，非数据通路）；
paper 侧与 evidence 侧 5 个 .tex 逐字节一致。
