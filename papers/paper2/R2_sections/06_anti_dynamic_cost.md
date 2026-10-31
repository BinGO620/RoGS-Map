# 06 The Cost of the Anti-Dynamic Paradigm

> **状态**：已议定并落笔（2026-10-12；§7 两项按默认——fig2 保留（去 gate 行重出）+ 主数字 = 动态区 +18–22 dB 与"靠几何挽回"）。
> **上游**：`R2_NARRATIVE.md` §3 贡献②。**正文**：`paper2_cvm.tex` §6。
> **结构校准**：fig2_render 生成器 `fig_render` 加 `arms` 参数默认只画 GT|base（gate/SWBA 复合臂排除，红线）；fig2_render_crowd2 重出为两行版并镜像活区。

## 1. 这一节要讲的一句话（thesis）

反动态范式（把动的像素排除出地图）**有可测的代价**：在腾空区，保持动态内容能把该区域
PSNR 提升 ~18–22 dB、深度误差降到 15–27%；而且代价**主要靠"把几何放进地图"挽回**
（几何/外观拆解 0.80–0.93），不是靠逐帧建模运动。

> **2026-10-11（D2-031）删句**：原 thesis 末句"同时，动态处理对地图**体量**的影响是
> **跨序列异号**的（不是单向膨胀）"已随 `tab:storage` 一并删除（证据 = Base vs Gate 体量，
> gate 臂含 SWBA ⇒ 无法干净呈现；见 R2_NARRATIVE 贡献②删条注记）。

## 2. 承接/引出

- **承接 §3 横比**：§3 刚用表证明"静态方法在动态序列上崩"——直接问：为什么？因为反动态范式是必需的对策，
  但它自己也有代价。§6 把这份代价量化。
- **承接 §5 Codec**：§5 讲压缩（静态底图），§6 讲被压缩的对象"少了什么"。
- **引出 §7 Offline repair**：既然抹掉的代价这么大且主要靠几何挽回——那能不能**装回去**？

## 3. 用哪些表 / 图

| 资产 | 内容 | 为什么在这 / 复用 |
|---|---|---|
| ~~`tab:storage`~~ **已删（2026-10-11，D2-031）** | ~~Base vs Gate 地图体量（跨序列异号）~~ | gate 臂含 SWBA、题注不实（D1-028 M1）⇒ 按"只为论文 2 / 投 CVM"删表删条 |
| `tab:static`（复用 tab3s_static） | 静态区 + 腾空区 ghost excess | 抹除代价的分区量化 |
| `fig:render`（复用 fig2_render_crowd2） | GT｜base 渲染对比（腾空区 inset） | **⚠ 需去掉 gate 行**——SWBA/gate 排除，只留 GT｜base |
| — 代价数值（正文） | 5 序列 +17.9–22.2 dB / 拆解 0.80–0.93 | 机写自 `embrace_dyn/` 与 `dyn_cost_*` |

## 4. 篇幅预算

**1.5 页**。

## 5. 数字来源 / 口径

- `results/paper2_fulltable/evidence/{dyn_cost_5seq_2026-10-05, dyn_cost_decomp_2026-10-05}.{md,json}`
- `results/embrace_dyn/evidence/probe_5seq_*_results.json`
- 口径：P1(erase)/P2(preserve) 同帧配对；**跨集 dB 不可比**，只用同集内 dB 差与比值。

## 6. 红线自查

- ❌ 不得称"首次发现"；负结果/边界不作贡献主张。
- ⚠ **fig2_render_crowd2 图注现写"both render arms"**——重写后只有 base 一个臂（gate 排除），图注必须改。
- ⚠ 拆解口径（retention P2c 0.80–0.93 / P4 0.10–0.39）须与 canonical 5seq 一致（G2-M3 旧账）。

## 7. 待用户确认项（**全部落定 2026-10-12**）

1. **fig2 是否保留** → **保留**（GT｜base 两行，gate 行已从生成器排除并重出；图注改"prior stack"，无 "both render arms"）。
2. **代价主数字** → **动态区 +17.9–22.2 dB + 深度比 0.15–0.27**（§7 建议采纳），辅以"靠几何挽回 0.80–0.93 vs 冻结 0.10–0.39"；成本 6–29%（中位 22%）。
