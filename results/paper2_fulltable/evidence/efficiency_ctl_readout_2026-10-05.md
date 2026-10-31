# 效率表「无竞争」重测判读（Tab.4 独占锚点）— 2026-10-05

> **账本**：D2-026 写作轨；判据出处 = `prereg_efficiency_ctl_2026-10-05.md`（先锁）。
> **性质**：测量口径修正（**无通过/失败判据**，prereg §3 显式声明）；数字机写、禁手抄。
> **口径**：`online_fps = num_frames / online_time_s`（`utils/eval_utils.py:1065`）。

> **⚠ 重大更正（2026-10-05，关卡② G2 = Reject）：本件初版把「独占 vs R33 并发」的 2.2–2.6× 差
> 全归因于并发——不成立。** effctl 跑在**当前分支代码**上，而 R33 是 **2026-09-16 代码**（证据：
> effctl CSV **61 列** vs r33 **51 列**，多出的 10 列是 alpha_gate/occ/seam 等后续机制计数器；
> 同格高斯数差达 **+54%**，如 baseline/balloon 41835 vs 27174）⇒ **代码漂移与并发度是两重混杂**，
> 不能把倍率读成纯并发效应。**结论降级**：本件只保留「独占读数」作 Tab.4 的**受控锚点**；
> 「并发低估」的因果主张**撤回**（待同码并发对照 `run_effctl_conc.sh` 跑完才谈，见 §5）。

## 0. 一句话（更正后）

**本子集（当前代码、单进程单卡、3 序列 × 4 臂 × seed0）的独占在线速度为 0.83–1.28 fps。**
这是一个口径干净的受控锚点。它与 R33 原批（0.35–0.46 fps，2 进程/卡）的差**不能**归因于并发——
两批代码版本不同（见上方更正框）。

## 1. 独占读数（本次，3 序列 × 4 臂 × seed0，串行单卡）

| arm | balloon fps | crowd2 fps | person_tracking fps | 中位 fps |
|---|---|---|---|---|
| base (Paper-1 stack) | 1.162 | 1.278 | 1.128 | **1.162** |
| +SWBA | 0.847 | 0.860 | 0.844 | **0.847** |
| +SWBA+LC | 0.862 | 0.864 | 0.834 | **0.862** |
| +SWBA+LC+Gate | 0.907 | 1.139 | 0.858 | **0.907** |

- **base 最快**（≈1.2 fps）；开 SWBA 后降到 ≈0.85 fps（SWBA 窗口 BA 的代价，与已知一致）；
  门控把部分代价收回（0.86→0.91）。
- 三序列一致（同臂跨序列 ≤0.1 fps 散布，crowd2 gate 略高）。

## 2. 与 R33 原批（并发）对照（**更正：非单变量，勿作因果读**）

| arm | 原批 median fps（并发, 09-16 代码） | 本次 median fps（独占, 当前代码） | 倍率 |
|---|---|---|---|
| base | 0.456 | **1.162** | 2.55× |
| +SWBA | 0.354 | **0.847** | 2.39× |
| +SWBA+LC | 0.354 | **0.862** | 2.44× |
| +Gate | 0.415 | **0.907** | 2.19× |

**⚠ 此倍率含代码漂移 + 并发度两重混杂**（G2 致命，见顶部更正框）⇒ **不得**写成"并发使 FPS 降 2–3×"。
R33 原批 0.35–0.46 fps 仍是**那一版代码 + 2 进程/卡**的读数，本表仅作历史对照。
**诚实边界**：本子集 = **3 序列 × 1 seed**，只作 **FPS 绝对量级锚点**，不外推为全表 7×3 控制实验。

## 5. 同码并发对照（待跑，隔离并发度）

为把"并发 vs 独占"做成**单变量**（同当前代码、同子集、仅进程数不同），已备脚本
`scripts/paper2_fulltable/run_effctl_conc.sh`（2 进程/卡，tag=`effctlconc_*`）。

**✅ 已完成（2026-10-05 11:55，12/12 rc=0）**。判读件 = `evidence/effctlconc_ablation_2026-10-05.md`
（机写，脚本 `scripts/paper2_fulltable/effctlconc_ablation.py`；工件 `effctlconc_ablation_2026-10-05.json`）。
**两批同码已证**（effctl 与 effctlconc 的 `efficiency_raw.csv` 均 **61 列**）。

**结论**：并发（2 进程/卡）对在线 FPS 的代价 = **1.02×–1.83×**（12 格中位 **1.45×**），
**远小于**初版跨版本读出的 2.2–2.6×。⇒ **确认 D1-027**：初版倍率**主要来自代码版本漂移**，
并发本身只在 1–2× 量级，且随臂变化（gate 臂代价最小 1.02–1.64×，+SWBA+LC 最大 1.55–1.83×）。
并发有代价但**非决定性**，不作强因果主张。

## 3. 对论文的处置（更正后）

- Tab.4 报 **两列**：`FPS (exclusive, this work)` = 本表 §1（**受控锚点**）；
  `(concurrent, R33, 09-16 code)` = 原批值（**不同代码版本，仅历史参考**）。caption 须注明两列不同码。
- **并发对照已可用**（同码单变量）：若正文要写并发代价，可引 `effctlconc_ablation` 的
  **1.0–1.8×**，**不得**再写 2–3×（那是跨版混引）。
- 高斯数/峰值显存**沿用存量**（R33 表列）——两批高斯数**不同**（代码漂移），Tab.4 的高斯数/显存列
  须**注明取 R33 存量口径**，不与 effctl 混。
- **数字入表前过关卡②**（并发对照已完成，本件 + `effctlconc_ablation` 一并送 G2 复审）。

## 4. 工件
- 判据键：`results/paper2_fulltable/effctl_*/tables/efficiency_raw.csv`（12 份，已入库）
- **并发对照键**：`results/paper2_fulltable/effctlconc_*/tables/efficiency_raw.csv`（12 份）+
  `effctlconc.done`（12/12 rc=0，2026-10-05 11:55 收工）
- 并发判读：`results/paper2_fulltable/evidence/effctlconc_ablation_2026-10-05.{md,json}`
- 驱动/prereg：`scripts/paper2_fulltable/{run_effctl.sh,run_effctl_conc.sh,collect_effctlconc.sh,
  effctlconc_ablation.py}` + `evidence/prereg_efficiency_ctl_2026-10-05.md`
- 批日志：远程 `results/paper2_fulltable/effctl.done`（12/12 rc=0，2026-10-05 08:08 收工）
