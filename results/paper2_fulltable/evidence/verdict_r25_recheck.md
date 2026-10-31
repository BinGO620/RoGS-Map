# R25 代价门复核（2026-09-15，离线诊断，零 GPU）

> **账本补登（2026-09-25，D2-015 追溯登记）**：本件成文于决策账本设立（2026-09-20）之前，无当期账本号；统一追溯登记见 `DECISIONS.md` **D2-015**。

> 触发：实验 F 收口后评估"自校验式 SWBA"修复路径时，发现 R25 代价门
> （`swba_min_rel_improve`）的否决可能建立在不成立的证据上。
> 本文件为**复核记录**——不改动 R25 原始裁决文本，只登记新发现。
> 数据源：`results/paper2_fulltable/r25_gate_{crowd2,person_tracking}_seed0`
> 的 consolelog 与 tracking_raw.csv（均为既有原始输出，未重跑）。

## 一、发现 1：阈值尺度错配，门从未在有效工作点被测试

代码（`utils/swba.py:642`）：

```python
"rel_improve": (c_init - c0) / max(abs(c_init), 1e-9)   # 比值，如 0.006
```

比较（`utils/swba.py:730-731`）：

```python
min_ri = float(cfg.get("swba_min_rel_improve", 0.0))
if rel_improve < min_ri:   # skip
```

R25 config：`swba_min_rel_improve: 0.2`（= 20%，日志按 `:.1%` 打印）。

**实测信号范围**（从 R25 自身日志提取，逐 KF 的 `rel_improve`）：

| run | n | 信号范围 | 阈值 | 结果 |
|---|---|---|---|---|
| r25_gate_crowd2 | 177 | 0.0 – **4.10%** | 20% | 177 次全 skip |
| r25_gate_person_tracking | 115 | 0.0 – **4.80%** | 20% | 115 次全 skip |

阈值 20% 是信号最大值（4.8%）的 **4 倍以上** → 门恒为 skip。
日志逐行证实：`rel_improve=0.0% < 20.0% — correction not applied`（177/115 次），
`applied` 计数 = **0**。

**结论**：R25 实际测试的是"SWBA 全关"，不是"代价门在某个工作点上是否
有判别力"。代价门假设**未被有效检验**。

## 二、发现 2：裁决文本与自身日志相反

`evidence/verdict.md:58` 原文：

> 典型值都在 0.0-0.8%，门 0.2 零拦截（177/115 全应用），crowd2 退化不变。

但 consolelog 显示 177/115 次全部 `correction not applied`（**全跳过**，
非"全应用"）。ATE 交叉验证支持日志：

| crowd2 run | 全帧 ATE cm | 解读 |
|---|---|---|
| baseline（无 SWBA） | 2.22 | 参照 |
| final（SWBA 全开） | 4.16 | SWBA 有害 |
| **r25_gate（门 0.2）** | **2.01** | ≈ baseline ⇒ SWBA 实际被全关 |
| r29_framegate（门 0.38） | 2.34 | 部分放行 |

r25 = 2.01 接近 baseline 而非 final，**证实 SWBA 被全关**（与日志一致，
与"全应用"的裁决描述矛盾）。裁决的**结论**（"crowd2 退化不变"）恰好
与"全跳过"自洽——即结论偶然正确，但描述与归因错误。

## 三、发现 3：否决理由"SWBA 边无掩码"与代码不符

`evidence/verdict.md:60-62` 的机制级否决理由：

> 窗口光度代价正是被污染的信号——**SWBA 边无掩码**，拟合人物像素同样
> 降低窗口代价，"健康度"用被欺骗的信号看守自己，循环论证。

代码实证（R25 提交 `e014ddc5` 时即如此，非后续新增）：

| 位置 | 代码 | 作用 |
|---|---|---|
| `utils/dba_lite.py:91-95` | `valid = valid & (~m)` | 源侧：person 像素排除出源点集 |
| `utils/swba.py:176-178` | `m = m & (mj_s <= 0.5)` | 目标侧：person 像素排除出内点集 |
| `utils/swba.py:68` | `mask = getattr(cam, "dynamic_mask", None)` | KF 几何构建时读取 person 掩码 |

且 `SemanticMask.enabled=True`（R25 运行时 config 已核），KF 相机不清掩码
（`cleanup()` 仅作用于非关键帧）。⇒ **SWBA 边实际应用了 person 掩码**，
"边无掩码"的表述与代码不符。

（保留判断：即使掩码生效，代价门是否**有判别力**仍可能不足——两 regime
信号范围高度重叠，这是 R25 数据的真实观察。故本复核**不推翻"代价门判别
力弱"的结论**，只指出：①它从未在有效阈值下被测；②否决理由的机制表述
不成立。）

## 四、对当前工作的影响

1. **决策 #2（自校验式 SWBA）应重测，而非按"已否决"搁置**——它是原理上
   能消除阈值敏感度的路径（不依赖难度阈值，直接问"修正是否降低静态窗口
   代价"），而现有证据不足以否决它。
2. **重测零代码改动**：机制已实现（`swba_min_rel_improve`），只需把阈值
   设在信号量级（如 0.5%/1%/2%），即纯 config 实验。
3. **实验 F 的根因诊断不变**：static_conf 绝对阈值跨序列不齐（门控敏感度
   来源）是独立问题，与本节无关。

## 五、待办

- [x] 预注册自校验门重测（阈值 0.5%/1%/2% × gate 臂 × 7 序列 × 2seed）
      —— 已完成 2026-09-15（42 run rc=0），**判负**：三门未全过，
      记入已排除方向。裁决 `evidence/verdict_r31.md`，预注册
      `evidence/prereg_r31_selfcheck.md`。
- [x] 重测后更新 `evidence/verdict.md` 的 R25 段（加指向本文件的注记，
      不改原始裁决文本）—— **已完成 2026-09-15**：`verdict.md` R25 段末
      加了注记（含 177/115 全 skip 的实测计数），另在 R29 段末补了
      "跳过 56 → 实为 117"的计数勘误注记。原始文本按 D3 保留未改。
      README 口径注记同步更新。

## 证据

- `results/paper2_fulltable/r25_gate_crowd2_seed0.consolelog`（177 skip）
- `results/paper2_fulltable/r25_gate_person_tracking_seed0.consolelog`（115 skip）
- `results/paper2_fulltable/r25_gate_*_seed0/tables/tracking_raw.csv`
- 代码：`utils/swba.py:642,730-731`；`utils/dba_lite.py:91-95`；`utils/swba.py:176-178`
