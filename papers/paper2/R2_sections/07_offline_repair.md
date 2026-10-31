# 07 Recovering Dynamic Content Offline

> **状态**：已议定并落笔（2026-10-12；§7 两项按默认——输出形态 = 4D 层序列设计决策 + 在线两序列不对称如实披露）。
> **上游**：`R2_NARRATIVE.md` §3 贡献③。**正文**：`paper2_cvm.tex` §7。
> **结构校准**：fig6_dynport_repair 改 `figure*` 跨栏（字号门修复）；tab_dynport 自带环境直接 `\input`。

## 1. thesis
把 DynaGSLAM 式动态 GS 管理**移到离线放置**（对已完成底图做后处理、静态层逐位冻结），
就能从"已抹除"的地图里把动态内容装回去：J1 5.49–8.95 dB / J2 0.23–0.61 / J3 −0.035–0.196 dB，
**21/21 过**（7 序列 × 3 seed）；而在线的同一机制 **+95%/+89%** 开销不可负担 ⇒ FAIL。

## 2. 衔接
§6 量化了"抹掉的代价大且靠几何挽回" → §7 直接把几何装回去 → §8 讲评测仪器。

## 3. 表 / 图
| 资产 | 复用 | 内容 |
|---|---|---|
| `tab:dynport`（tab_dynport） | ✅ | 时间放置对照：online FAIL / erase ref / offline PASS |
| `fig:dynport-repair`（fig6_dynport_repair） | ✅ | GT｜抹除后｜修复后，两序列两帧，动态区 inset |

## 4. 篇幅
**1.0 页**。

## 5. 数字来源
`results/dynport_offline/evidence_{v4,L2,L3}/manifest_*.json`（samepose §12 v4 口径）；
在线对照 = `results/dynport/evidence/manifest_L1_v2.json`（snapshot 口径）。

## 6. 红线自查（贡献③专属禁语）
- 机制本体归 **DynaGSLAM**（必引）；delta = 离线放置 + 冻结静态隔离 + 时间放置对照。
- ❌ 禁"首个恢复动态"/"在线系统"/"4D 重建 SOTA"。
- ⚠ **在线↔离线禁混引**（4 处共变：位姿源/静态保护/KF 日程/掩码通路）；在线行须标 snapshot 口径 + 位姿混杂注记。
- ⚠ **在线↔离线 J3 性质相反**（在线=静态被联合优化改；离线=静态逐位未动、单 PLY 合渲遮挡）——分开表述。
- ❌ 禁称"codec 联动已做"（codec 只能读 output②，读不了 output① 4D 层序列）——边界声明。

## 7. 待确认（**全部落定 2026-10-12**）

1. **输出形态（4D 层序列）怎么交代** → **写成设计决策**（"not a limitation"）：单 PLY 合并形态正是动态内容丢失的形态，放回去会抹掉增益；层序列保静态逐位不变（正文 Output form 段）。
2. **时间放置对照表不对称** → **如实披露**（tab_dynport caption 已写明：online 两序列 snapshot 口径含位姿混杂、descriptive not single-variable、4 处共变）。
