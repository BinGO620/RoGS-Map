# 拉通批通用性面板 (seed0, gate 臂部署机)

> **口径警告（K7）**：`baseline` 列 = 固定栈 baseline（SWBA/回环/门控全关），
> 仅作**同批对照**，不得单独作为方法对照或跨实验外推（账本事故同族）。
> - `baseline_src=r34rb3seed`：R34 **同批 3-seed 均值**（6 条已复核序列）；
> - `baseline_src=frozen1seed`：旧批 `rollbase` seed0 **冻结值**（1-seed 跨批，
>   **未经同批复核**；K5 已证 f1_room/f3_st_rpy 跨批不可复现，仅存历史参照）。
> 读数取 `tables/tracking_raw.csv` col 8；**顶层 *.consolelog 不可用于取数**
> （已实测 3 个 run 的 consolelog 与 tracking run_id 不同源，见 prereg_r34 §1.2）。
> **「8/19 负作用」表述已作废**（R34 同批复核，见 verdict_r34.md §七）。

| 序列 | 类别 | baseline ATE | gate ATE | ≤5cm |
|---|---|---|---|---|
| balloon_tracking | Bonn扩展-动态 | 6.52 | 6.93 | ✗ |
| balloon_tracking2 | Bonn扩展-动态 | 22.46 | 21.68 | ✗ |
| moving_nonobstructing_box | Bonn扩展-物体 | 2.96 | 2.37 | ✓ |
| moving_obstructing_box | Bonn扩展-物体 | 29.18 | 20.74 | ✗ |
| static | Bonn-静态 | — | — | ✗ |
| synchronous | Bonn扩展-同步 | 0.44 | 0.95 | ✓ |
| f1_desk | TUM-f1 | 1.41 | 1.69 | ✓ |
| f1_desk2 | TUM-f1 | 5.11 | 3.53 | ✓ |
| f1_room | TUM-f1 | 16.39 | 18.10 | ✗ |
| f2_person | TUM-f2 | 6.37 | 6.60 | ✗ |
| f2_xyz | TUM-f2 | 1.79 | 1.91 | ✓ |
| f3_office | TUM-f3 | 1.40 | 3.66 | ✓ |
| f3_st_hf | TUM-f3动态 | 33.52 | 34.68 | ✗ |
| f3_st_rpy | TUM-f3动态 | 5.29 | 5.85 | ✗ |
| f3_st_static | TUM-f3动态 | 0.81 | 0.83 | ✓ |
| f3_st_xyz | TUM-f3动态 | 3.08 | 3.24 | ✓ |
| f3_wk_hf | TUM-f3动态 | 3.12 | 3.66 | ✓ |
| f3_wk_rpy | TUM-f3动态 | 4.89 | 5.87 | ✗ |
| f3_wk_static | TUM-f3动态 | 0.63 | 0.68 | ✓ |
| f3_wk_xyz | TUM-f3动态 | 3.29 | 2.85 | ✓ |

- 已完成 19/20, 过 5cm 线 11/19
- 动态序列过线: 5/10
