# scripts/embrace_dyn/

本实验无独立 run 脚本：探针工具与判据机放在共享分析目录，理由 = 两者是**离线分析**工具
（只读 `results/` 既有产物，不产生 run），与 `scripts/02_analysis/` 下其他分析器同类。

| 工具 | 位置 | 职责 |
|---|---|---|
| 探针 | `scripts/02_analysis/dyn_probe.py` | `materials`（内容判据）+ `render`（四臂阶梯 P1/P2/C−/P4） |
| 判据机 | `scripts/02_analysis/analyze_dyn_probe.py` | 按预注册 §7 逐条机器判定 + 出报告 |
| 配置 | `configs/experiments/embrace_dyn/probe_pt2.yaml` | 锁定参数（16 帧 / t0=309 / 300 步拟合） |
| 对照配置 | `configs/experiments/embrace_dyn/control_p1_vs_render_compare.yaml` | 阳性对照（P1 vs 既有 render_compare） |
| 门禁 | `tests/embrace_dyn/test_dyn_probe.py` | 判据机四态 + 配置↔预注册一致 + 证据自洽 |

用法见 `results/embrace_dyn/README.md`。
