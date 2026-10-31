# CVM 2027 审稿状态（v8.15）

**最后更新**: 2026-10-20  
**论文版本**: v8.15 (sha256: `6fbc0095...`)  
**补充材料**: v8.13 (sha256: `fe294411...`)

---

## 📊 审稿轮次总览

### Round 6 (2026-10-19) - GLM-5.3 独立面板
**位置**: `archive/reviews/glm-5.3-panel-2026-10-19/`
- R1 (SLAM系统): Borderline 3.0/5
- R2 (3DGS/压缩): Weak Accept 3.5/5
- R3 (通才怀疑派): Weak Reject 2.5/5
- AC元评审: **Borderline 3.0/5**
- 视觉复核: 10项新发现（含1个证据缺陷）

**最终判决**: **MAJOR REVISION**  
**预期修订后**: 3.5/5 (Weak Accept)

---

## 🎯 修订优先级（基于GLM面板共识）

### P0级（摘要前必修，2工作日，+0.4分）
1. ✅ §7因果机制改为观察性描述（R3 blocking）
2. ✅ §6深度残差标注（GT-depth oracle vs sensor probe）
3. ✅ §3 "14-20 dB"订正为6.97-22.14
4. ✅ 协议异构性声明（解决DA-C1）

### P1级（全文投稿前，再1-2天，+0.3分）
5. Held-out Bonn序列具名
6. §6覆盖范围说明（5/7序列，种子）
7. Fig. S1 row 2修复（证据失效：repaired=erased）
8. Table 1脚注`d`拆分
9. 数值一致性修正（"+6.8"、"18 to 22"等）

### P2级（可选，需额外实验，2天，+0.2分）
10. Table 4添加PSNR实测lossy baseline
11. 表格化C−控制和oracle分解

---

## 🚨 关键问题裁决

### DA CRITICAL问题
- **DA-C1** (协议非独立性): ✅ VALIDATED → 阻止接受
- **DA-C2** (30%常量=表示失配): ⚠️ 部分成立，措辞修复
- **DA-C3** (离线修复边界窄): ✅ 不阻接受（已充分披露）

### 7项共识关切
所有问题均为**报告/标注/framing层**，无测量有效性问题。

---

## 📅 时间线

- **Abstract提交**: 2026-10-23 (剩4天) → 需完成P0
- **Full paper提交**: 2026-10-26 (剩7天) → 需完成P0+P1

---

## 📁 相关文件

- GLM面板: `archive/reviews/glm-5.3-panel-2026-10-19/`
- Claude R6: `archive/reviews/CVM_REVIEW_v8.15_2026-10-19.md`
- 编辑决策: `archive/reviews/CVM_EDITORIAL_DECISION_v8.15_2026-10-20.md`
- 当前论文: `paper2_cvm.pdf` (v8.15)
- 补充材料: `supplement/supplement.pdf` (v8.13)
