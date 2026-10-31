# R34 — 拉通批同批复核

**目的**：`paper2_rollout`（论文的 held-out 通用性面板）**自有 baseline 臂
从未进面板**，补上对照后发现 6/19 条序列 |Δ|>1.5cm（5 条负作用）。
本批把其中 6 条放到**同批同码**下重测，回答两个问题：

1. **复现性**：这些 Δ 是真的组件效应，还是跨批/抽样噪声？
2. **归因**：负作用来自 SWBA、还是门控本身？

## 规模与设计

**54 run = 3 臂 × 6 序列 × 3 seed**

| 臂 | SWBA | 门控 | 回环 | 角色 |
|---|---|---|---|---|
| `r34_rb_{seq}` | 关 | 关 | 关 | 同批 baseline（固定栈） |
| `r34_sw_{seq}` | **开** | 关 | 关 | **归因臂**（rb→sw 即 SWBA 效应） |
| `r34_gate_{seq}` | 开 | 0.38 | 开 | 部署形态（rb→gate 即总效应） |

**序列（选择规则：全 19 条可比序列中 |Δ|>1.5cm，客观、非任意）**：
`f1_room` / `f1_desk2`（唯一反向对照） / `f3_st_rpy` / `f3_office` /
`moving_obstructing_box` / `f3_wk_rpy`

**为何 3 臂而非 4（省 `final`）**：R33 已同批证明 LoopClosure 唯一步长在
标准 Bonn 7 序列的 42 个 run 上为零修正、效应落在噪声内；且 gate 臂日志自带
`corrections` 行，可直接自证这 6 条序列上回环是否仍为零（若非零则补 final 臂）。
> **⚠ 该自证条件已于跑中触发**：`r34_gate_f3_st_rpy` seed0/seed2 出现
> 非零修正（10.36 / 13.23 cm，同一批 verified 对在旧批同 seed 为 0.00 ⇒
> 非确定性）。⇒ "零修正"结论**收窄为 Bonn-scoped**；`f3_st_rpy` 的回环
> 那一份效应本批三臂**拆不出**，收口时按预注册裁定是否补 `final` 臂。
> 实测与处置见 `evidence/prereg_r34.md` §2.1。

## 判据与产物

- 预注册（单一事实源）：[`evidence/prereg_r34.md`](evidence/prereg_r34.md)，
  判据 K1–K7，**已过关卡③**（slam-critic Reject → 逐条复核后全部采纳，
  记录在该文件 §七）
- 分析器（确定性）：`scripts/02_analysis/analyze_r34.py`
- config：`configs/experiments/paper2_rollout/r34_*.yaml`（18 个）
- L1 门禁：`tests/paper2_rollout/test_r34_rollout_configs.py`

## 状态

- 2026-09-17 07:24 派发（`r34.done`），远程 3090×2，4 worker；**实际 14.8h**
  （07:24 → 22:14 `batch all done`，`finished rc=0` 54/54，rc w0–w3 全 0）
- **2026-09-18 分析收口**：轻量产物已拉回并入库；`analyze_r34.py` 判定 =
  K1/K1-b/K1-c 全过、K3 全过；**K5 复现性 4/6 超限**（归因触发器①②③
  核验全干净）⇒ 3 条有害序列判「不可复现」剔除；按预注册 K6 **自动降级
  「不可复现」**。详见 `evidence/verdict_r34_draft.md` +
  `evidence/analyze_r34_output.txt`。
- ⚠ **关卡①（落 verdict 前）未完成**：slam-critic 两轮未返回结论（第 1 轮
  输出超限全损；第 2 轮被中止）。处置 = 先修复子智能体再补跑关卡①，
  通过后落盘 `verdict_r34.md`。

## ⚠️ 取数纪律（本批复核的产物）

- **一律取 `tables/tracking_raw.csv` col 8（全帧）**；col 14 仅附表并声明
- **顶层 `*.consolelog` 不是有效取数源**：已实测 3 个 run 的 consolelog
  自报 `save_dir` 与 tracking `run_id` 不同源（`prereg_r34.md` §1.2）
- 计数须用**锚定整行形状**；skip 行须用 `\s+`（rich 插入额外空格）；
  禁用 `[rel-gate skip]` 字面量（被 rich 吞掉）
