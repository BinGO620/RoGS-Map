# R33 静态/残影证据线 — canonical 掩码重算（2026-09-22）

**性质**：D1 级（仪器修正后的机械重算）。**触发**：掩码事故影响评估
（`mask_incident_impact_2026-09-22.md` §3.2）指出 R33 的 44 个静态/残影读数用的是
已证伪的 `dynamic_mask_gtmc`（crowd/crowd2 另有 `seg_mask` cls15=错类）。
**做法**：`scripts/02_analysis/rerender_r33_static_canon.py` —— 从原 `render_metrics.json`
**逐帧恢复帧集**与 PLY 变体，除掩码源外参数一字不差；本地 32 + 远程 12 分机跑（不新增跨机混比）；
**44/44 rc=0**，产出 `render_compare_static_canon/`（不覆盖原目录）。旧口径 `mask_source`
= {seg_mask, dynamic_mask_gtmc}，新口径 = {dynamic_mask}。

## 1. 内部一致性自证（本次诊断的独立验证）

| 序列 | 旧掩码 | Δ static PSNR（新−旧） |
|---|---|---|
| crowd3 | **本仓 MaskRCNN person（本就正确）** | **+0.79 ~ +0.93 dB**（小） |
| crowd / crowd2 | seg_mask **cls15 = table（错类）** | **+6.2 ~ +7.8 dB**（大） |
| balloon / pt2 | gtmc（失效） | +2.8 ~ +4.3 dB |

⇒ **旧掩码越错、新读数抬升越大**——两条独立线索吻合，是本次整套诊断的自洽性证据。

## 2. 三条旧结论的存活判定（canonical 口径）

### ① "static PSNR 8 序列全中性（|Δ|≤0.25dB）" ⇒ **不成立**

新口径下**臂间 spread**（baseline / swbaonly / gate / final 四臂）：

| 序列 | 臂间 spread (dB) |
|---|---|
| crowd3 | 0.170 |
| crowd | 0.516 |
| person_tracking2 | 0.520 |
| crowd2 | 0.626 |
| balloon | 0.688 |

⇒ 最大 0.69 dB，是旧界 0.25 dB 的 ~2.8 倍。**"全中性"是旧掩码污染下的产物**（旧掩码把移动物留在
"静态区"里，四臂都被同一污染拖低、差异被压平）。
**另**：绝对水平普遍抬升 **+0.7 ~ +7.8 dB** ⇒ 任何引用旧绝对值的表/图必须替换。

### ② "ghost_excess gate 方向一致更优" ⇒ **不成立**

gate vs baseline（均值，序列内）：

| 序列 | gate | baseline | 判定 |
|---|---|---|---|
| balloon | **−0.161** | 3.689 | gate 优 |
| person_tracking2 | **0.631** | 2.527 | gate 优 |
| crowd | 1.971 | **1.451** | gate 劣 |
| crowd2 | 4.485 | **4.431** | 基本持平（略劣） |
| crowd3 | 5.479 | **4.539** | gate 劣 |

⇒ **2/5 优、3/5 劣**（旧口径下 crowd2 是 gate 4.31 < baseline 5.06）。方向一致性**不再成立**。
（附：`swbaonly` 在新口径下 ghost 反而最好——crowd2 −1.84、crowd 0.73、crowd3 3.44；
这与旧表 swbaonly 最优的**排序**一致，但 gate 的"挽回"不再体现为 ghost 优势。）

### ③ "SWBA 损伤静态区 / 门控挽回" ⇒ **成立**（部分存活）

- swbaonly 的 static PSNR 在 crowd2 最低（26.915 vs baseline 27.446 = **−0.53 dB**）⇒ "SWBA 损伤静态区" 复现。
- gate − swbaonly 的 static PSNR：balloon **+0.15**、crowd **+0.32**、crowd2 **+0.63**、
  person_tracking2 **+0.27**、crowd3 −0.14 ⇒ **4/5 为正** ⇒ "门控挽回" 复现。

## 3. 对论文/叙事的影响

- 论文 1（已投稿版）：**不受影响**（正文无 vacated/static/ghost 类读数，已逐字核，
  见 rescore §4 表）。
- 论文 2：**§4.4 / Tab.2r / Fig.4 的静态读数与"不退化"表述须按本文件替换**
  （关卡② 未过，相关数字本就未进表，属"未采用"而非"需更正"）。
- 叙事层：**"组件不伤渲染/静态区"这一支的证据基础变了**——不再是"全中性"，而是
  "SWBA 伤静态区、门控挽回"（更强、更可主张）；而 **ghost 优势不可再声称**。

## 4. 复算

```bash
PY=/data/conda_envs/monogs-ours/bin/python
# 本地侧（32 run，PLY 在本地）
$PY scripts/02_analysis/rerender_r33_static_canon.py --side local --dry-run   # 先干跑核对
$PY scripts/02_analysis/rerender_r33_static_canon.py --side local
# 远程侧（12 run，PLY 在远程；在远程 REPO 下跑）
$PY scripts/02_analysis/rerender_r33_static_canon.py --side remote
```
工件：`results/paper2_fulltable/render_compare_static_canon/<tag>/render_metrics.json`（44 个，已入仓）。
