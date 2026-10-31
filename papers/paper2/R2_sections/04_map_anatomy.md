# 04 What a Dynamic-Scene Gaussian Map Is Made Of

> **状态**：已议定并落笔（2026-10-12；§7 两项按默认执行——两图都留 + crowd2 clip 代价为主）。
> **上游**：`R2_NARRATIVE.md` §3 贡献②（前半）。**正文**：`paper2_cvm.tex` §4。
> **结构校准**：按 CVM 同场论文惯例，协议段统一移入 §3（Evaluation protocol），§4 自带 2–3 句口径即可。

## 1. thesis
打开一张生长地图：①一批**从不被渲染器读取**的记账字段（~1/3 原始字节，但熵编码已吃掉大半）；
②四元数/尺度里的**可去冗余**（renderer tolerance 内无损）；③尺度分布有**重尾**，而重尾是**承重**的
——收缩量化范围把它切掉会显著毁渲染（crowded 序列超噪声带）。这是"地图不是通用压缩器想象的样子"。

## 2. 衔接
§3 给了坐标 → §4 打开地图看里面 → §5 据此设计 codec。

## 3. 表 / 图
| 资产 | 复用 | 内容 |
|---|---|---|
| `fig:accounting`（fig5_accounting） | ✅ | 每 primitive 字节构成（6 记账字段） |
| `fig:tail`（fig4_tail） | ✅ | 量化范围 vs robust range；bulk vs tail 尺度 |
| （无表） | — | 数字进正文+图 |

## 4. 篇幅
**1.5 页**。

## 5. 数字来源
`results/gs_compress/evidence/{storage_census_2026-10-05.md（权威）, tail_census,qerr_probe}_*`、
`verdict_l1b_robust_range_*`。

## 6. 红线自查
- **P0-5 收窄**：禁"首次发现大高斯承重"（MGS-SLAM 已豁免高不透明度结构基元、PWAS 已按 importance 剪）。
  delta = **动态 SLAM 生长地图的尾部形状 + 范围量化的具体后果**。
- 记账字段"惰性"须与"熵编码已吃掉大半"并陈，不夸成大增益。

## 7. 待确认（**全部落定 2026-10-12**）

1. **两图去留** → **都留**（accounting=字节构成、tail=重尾直方图+范围膨胀，信息不同源，各司其职）。
2. **重尾主数字** → **crowd2 −0.71 dB clip 代价为主**（verdict_l1b §2.2 实证、最有冲击力），infl 区间（scale 1.36–2.15×/xyz 1.25–1.53×）作支撑；infl 非可压性代理（verdict §5.2）如实并陈。
