# prereg: 效率表"无竞争"重测（Tab.4 FPS 锚定）— 2026-10-05

> **账本**：D2-025 写作轨（工程口径修正）；用户 2026-10-05 授权"指标按叙事需要重跑"。
> **性质**：测量协议修正（**非新实验、非机制**）。判据先锁（本文件先于派发提交）。
> **为何重跑**：R33 原批用 **4 worker（2/GPU）并发**，`efficiency_raw.csv` 的
> `online_fps` 自注 "shared-GPU concurrency ⇒ indicative only, not a controlled comparison"
> （见 `tab4_efficiency.tex` caption）。论文要报 FPS 就须给出**独占**读数锚点。

## 1. 范围（最小充分）
- **只重测 FPS 相关**；高斯数/峰值显存与并发无关（确定性计数）⇒ **沿用存量，不重跑**。
- **子集**：3 序列 × 4 臂 × 1 seed = **12 run**（代表性覆盖三 regime）：
  `balloon`（稀疏/易）、`crowd2`（拥挤）、`person_tracking`（难/大）。
- 臂 = 论文四臂：`baseline / swbaonly / final / gate`（`r33_rebase_*` 配置，**代码零改动**）。

## 2. 协议（受控，先锁）
- **独占**：**单进程 / 单卡**，串行（禁 2/GPU —— D1-024 mope 教训：并发毁 A/B）。
- **顺序**：固定 arm 顺序 baseline→swbaonly→final→gate，同 seed=0。
- 设备：远程 3090（与论文数字同机）。
- 产物落**新目录**（`TAG_PREFIX=effctl`），**不覆盖** R33 原目录。

## 3. 判据（先锁）
- **主读数** = `efficiency_raw.csv` 的 `online_fps`（fps = num_frames / online_time_s，`eval_utils.py:1065`）。
- **报告** = 逐 (seq,arm) FPS + 中位；**与 R33 并发口径并陈**，标注"独占 vs 并发"两列。
- **⚠ 显式声明（G2-M5）**：本研究**无通过/失败判据**——效率表是**如实报告**（非机制贡献），
  只有**口径洁净度要求**（独占 / 单进程 / 可复算）。本 prereg 锁的是**协议**，不是判据线；
  读数好坏不触发任何出口分支。
- **诚实边界**：本子集 **3 序列 × 4 臂 × 1 seed = 12 run**（`balloon` / `crowd2` / `person_tracking`）
  ⇒ 只作 **FPS 绝对量级锚点**；**不外推为全表 7 序列 × 3 seed 的受控实验**。
  论文 Tab.4 若报全表 FPS，须注明其来自并发批（indicative）+ 本子集独占锚点（G2-M7）。

## 4. 工件
- 脚本 `scripts/paper2_fulltable/run_effctl.sh`（串行、单卡、TAG_PREFIX=effctl）
- 产物 `results/paper2_fulltable/effctl_*_{seq}_seed0/tables/efficiency_raw.csv`（判据键，入库）
- 读表 `results/paper2_fulltable/evidence/efficiency_ctl_2026-10-05.md`（机写）

## 5. 变更记录
| 日期 | 变更 | 依据 |
|---|---|---|
| 2026-10-05 | v1 判据锁定（本文件） | 用户 2026-10-05 授权 + tab4 caption 的 indicative-only 声明 |
