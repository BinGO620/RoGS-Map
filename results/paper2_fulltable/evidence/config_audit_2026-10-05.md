# 配置审计：R33 四臂是否含"静默死组件"或配置漂移（2026-10-05，零 GPU）

> **账本**：D2-025 写作轨；回应 `health_check.py` 的 WARN「配置审计: 同实验组件不一致」。
> **触发**：用户 2026-10-05 指令——"按论文 1 教训（配置里组件/参数错了）重查"。
> **方法**：零 GPU，盘上实测（config 指纹 + 计数列 + 输出文件存在性）。数字机写。

## 0. 结论

**R33 四臂配置干净，无论文-1 式静默死组件，无配置漂移。** 唯一发现 = 一个**命名易误读**
（`reliability_calls=0` 曾疑似死组件，实为正确的"另一模块关闭"）。

## 1. 四臂 method 配置指纹（合并 method_from 后）

| 臂 | 指纹数 | 差异（相对 baseline） |
|---|---|---|
| baseline | 1 | —（全组件按 method.yaml 默认） |
| swbaonly | 1 | +`SWBA.enabled=true` |
| final | 1 | +`SWBA.enabled` + `LoopClosure.enabled` |
| **gate** | 1 | final + `SWBA.swba_max_static_conf=0.38` |

⇒ **每臂仅一种指纹**（7 序列无漂移）；**臂间差异 = 预期开关**（SWBA / 回环 / gate 阈值），
无"挂错组件"。

## 2. "静默死组件"排查（论文-1 式 bug）

CSV 列 `reliability_calls / tri_reliability_calls / reliable_tracking_calls` **全部 200 run = 0**，
初判疑似"组件没跑"。逐项查证：

| 计数列 | 读到的键 | 状态 | 判定 |
|---|---|---|---|
| `reliable_tracking_calls` | `ReliableTracking`（`reliable_tracking.py:13`） | **关** | ✅ 正确（未启用） |
| `tri_reliability_calls` | `TriReliability`（`method.yaml:6 enabled:false`） | **关** | ✅ 正确 |
| `reliability_calls` | 见下 | — | ✅ 见 §3 |

## 3. 真正启用的组件确实在跑（生效验证，非效果）

method.yaml 启用 `RobustTracking`（**注意：与 `ReliableTracking` 是两个键**，
`slam_utils.py:177` 读取 `RobustTracking` 的 huber 鲁棒损失）与 `SemanticMask`：

| 组件 | 生效证据 |
|---|---|
| SemanticMask | `semantic_timing/summary.json` 的 `total.calls = 439`（= 帧数；balloon gate 实测）✓。**注（G2 更正）**：CSV 里名为 `semantic_calls` 的列**实际存的是 time_ms**（57979.74），**不是调用次数**——初次审计误读数，已更正。 |
| RobustTracking | 无独立计数列，但 `slam_utils.py:177/222/357/459/518` 消费其配置（代码路径在） |
| ReliabilitySignal | **`reliability_signal/frames.csv` 有 438 行真实数据**（mean_w=0.66、flow_valid_frac=0.86）✓ |
| 计时目录 | gate 臂存在 `reliability/`、`tri_reliability/`、`reliable_tracking/`、`semantic_timing/` 目录 ✓ |

⇒ **无"enabled=true 但静默不跑"的组件**（论文-1 `exp23 silent-noop` 式的反面）。

### 3.1 边界（G2-M6）：LoopClosure 在 Bonn 上 ≈ no-op
- `final` 与 `swbaonly` 两臂的 `LoopClosure.enabled` 相差 true/false，
  但 Bonn 7 序列 ATE 几乎相同（如 pt1：swbaonly 8.62 vs final 8.21，差在噪声带内）
  ⇒ **LoopClosure 在标准 Bonn 上无可测效应**（与 `NARRATIVE.md` §2026-09-17 修订"回环移出贡献"一致）。
- **澄清**：这不属"静默死组件"（组件有输出、不 crash），而属**"有效但无效应"**——
  论文 Tab.1 的 "+SWBA+LC" 列**须披露**：LC 臂在 Bonn 上的增量 ≈ 0，
  **不得**把它宣传为有效组件（已入 `NARRATIVE_v2` §5 禁语 + §3 provenance 披露）。

## 4. 对论文的处置

- WARN「同实验组件不一致」= **有意多臂对照**（非漂移）⇒ 按 health_check 的 fix 建议，
  在论文/README 标注各臂组件清单。
- **无需重跑 R33**（配置已核干净）。
- 一张"组件 provenance 表"（哪个组件来自论文 1 / 哪个是本文配置）应进 §3
  （防 salami-slicing，见 `NARRATIVE_v2_system_2026-10-05.md` §1）。

## 5. 工件
- 指纹法：本件命令（可复跑）
- 计数源：`results/paper2_fulltable/r33_rebase_*/tables/efficiency_raw.csv`
- ReliabilitySignal 产物：`.../reliability_signal/frames.csv` + `summary.json`
- 关联：`health_check.py` WARN 条目；`NOTES.md:1696`（论文 1 provenance 教训）
