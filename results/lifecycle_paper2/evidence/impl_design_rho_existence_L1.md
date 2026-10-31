# impl_design_rho_existence_L1.md — 存在量 ρ 的实装设计【v2，2026-09-25 关卡① 整改后】

> **账本登记**：本实装设计属 **D2-016**（乙 存在性梯度裁定 L1）的 Phase A 产物，与 `prereg_rho_existence_L1.md` 同批（该文书 v2 已挂 D2-016）。

> **性质**：设计说明，为 Phase A 关卡① 提供"实装如何在代码层面满足 prereg"的证据。
> **判据本体 = `prereg_rho_existence_L1.md` v2**（本文件不新增判据；v1 见 git 737dfaf6d）。
> **v2 修订依据**：关卡① Reject（2 致命/7 重大/6 次要）——逐条处置见文末 §6。
> **边界**：实装位全在 `utils/` + `gaussian_splatting/`（核心保护区）⇒ 走 DISCIPLINE
> 「代码保护」例外流程全链（prereg 先锁 → default-off → 单测两态 → 关卡③ → 派发）。

## 0. 合规前置（v2 更正引证）

- **乙 的形态从未实装**：可复跑证据 = `grep -rn "rho_existence\|existence_var" utils/
  gaussian_splatting/ slam.py` ⇒ **0 命中**（2026-09-25 实测）。
- **v1 曾引 `verdict_L1f_obsdebt.md` §0/§4 的"存在性形态未试"——该措辞不在该文件中**
  （0 命中）；该句只在一页纸 `d2_onepager_next_mechanism_2026-09-25.md:25` 出现。
  v2 不再引用不存在的引证。

## 1. 关键设计决策（v2 修订项以 **v2** 标注）

### D1 【v2 重写】参数化：ρ = **独立参数坐标**，直接进渲染的不透明度

- **v1 的错误（如实登记）**：v1 主张"把 ρ 加到 opacity 的 logit 上（`σ(logit(α)+ρ)`）以解
  α≈1 处梯度冻结"。**该论证是错的**——实测（2026-09-25）：
  - v1 方案 `σ(a+ρ)` @ ρ=0, α=0.999 ⇒ ∂α/∂ρ = **1.0e-3**（= σ′(a)，与 α 通道同量级）；
  - 被 v1 否掉的乘法式 `σ(a)·σ(ρ)` ⇒ ∂α/∂ρ = **2.5e-1**（劳动健康量级）。
  ⇒ **v1 推荐的方案比它否掉的方案差 248 倍**。且 P0 的失效根本不是梯度问题（是裁决被
  逐出覆盖，见 prereg v2 §6-1）。
- **v2 采纳方案（与 prereg v2 §1 一致）**：ρ 作为**独立参数张量**（初值 0.0）进
  `GaussianModel`，**渲染时**：
  `α_eff = σ( logit(α_orig) + ρ·1[m_rho] )` —— 但**关键差异在优化侧**：
  ρ 用**独立 param_group 与独立 `rho_lr`**，使更新步长 = `rho_lr × ∂L/∂α_eff × σ′(·)`
  **不被 α 通道的饱和因子主导**；同时 `alpha_eff` 下限护栏（0.02）保证 ρ 一旦压低
  α_eff，该基元就落进"视同不存在"区间，与 §4 计数② 的"翻转"定义对接。
- **v2 的验收判据（替换 v1 的空判据）**：单测须给**数值表**——
  合成 α_orig=0.999 的基元，(i) 走 α 通道 100 步的 |Δα|；(ii) 走 ρ 通道 100 步的 |Δα|；
  断言 (ii) 在**相同损失**下 ≥ (i)（因 ρ_lr 同量级而 σ′ 不再两次相乘）；
  **且** `m_rho` 内 ρ 的 grad 非零元素数 ≥ 0.9·n_rho（prereg §6-1 计数④）。

### D2 作用面：只对"腾空区投影所及"的基元生效（prereg §1）

- `m_rho` 由**渲染深度**投影判定（prereg v2 §9-9：与 instrument_v2 的 m3 同口径，
  不用 GT 投影）⇒ 与主读数的可判域定义自洽。
- `m_rho` 恒 False ⇒ ρ 不参与任何计算（`if params.does_rho_existence and m_rho.any()`）。

### D3 【v2 定案】腾空区来源 = 候选乙（独立定义），**不挂 exit**

- **定义**：`腾空区 = past_union ∧ ¬dyn_now ∧ valid_depth`，其中 `past_union` = 最近
  `past_union_window=30` KF 的动态掩码并集（`utils/gtmc_mask` 既有工具）。
- **为何不用 v1 候选甲（复用 `detect_vacated_pixels`）**：该函数语义是"exit 前后
  opacity 差值所腾空的像素"，**需要 exit 管线** ⇒ 乙 就得挂 exit 模式 ⇒ 与 prereg v2 §2
  的 `mode: off` 对照设计冲突（对照会变成 exit_fill，不是单变量）。
- **与 exit 的关系（关卡① Q3 的回应）**：候选乙 的腾空区是**掩码时序并集**，不是 exit 的
  动作结果 ⇒ 在 `mode: off` 下 exit 不做任何事 ⇒ **不存在"把 exit 的功劳记到乙"的通道**。
- **风险（如实）**：并集口径在密人群域会吞掉大片画面（NOTES 踩坑：过判积累致 75–79%）⇒
  故 prereg v2 §3a 的**可判性门必须在同批复算落盘**（balloon2 上界 15/17 已知）。

### D4 【v2 补全】接入点（含 v1 漏掉的三处）

| 文件 | 改动 | False 时行为 |
|---|---|---|
| `utils/rho_existence.py`（新） | `RhoExistenceLedger`（并集账本 + 翻转计数状态）+ `apply_rho_to_opacity(alpha, rho, m_rho)` + `count_adjudications(alpha_prev, alpha_now, thr)`（**纯函数**，供 §4 计数②） | 不 import 即不影响 |
| `utils/alpha_lifecycle.py` | params 加 `rho_existence/rho_lr/rho_sparse_lam/rho_clamp/rho_alpha_floor` + reader + `does_rho_existence` property（照 :125-160 的 6 个 `does_*` 形状） | 默认 False |
| `gaussian_splatting/scene/gaussian_model.py` | `_rho` 张量（`torch.empty(0)`）+ `get_rho` + `training_setup` 的 param_groups 加 ρ 组（**独立 lr**）+ **`cat_tensors_to_optimizer`/`prune_points`/`densify_and_split`/`densify_and_clone` 同步 ρ** + **`densification_postfix:1119-1126` 的 `d` 字典加 `"rho"` 键**（v1 漏；`cat_tensors_to_optimizer:1073-1075` 逐 group 取键 ⇒ 漏则 KeyError）+ **`validate_runtime_state:1179` / `optimizer_names:1204` 白名单加 ρ** + PLY 导出 | 空张量 ⇒ cat/prune/validate 恒等分支 |
| `utils/slam_backend.py` | `map()` 内 `if params.does_rho_existence:` 段：① ledger 更新；② 渲染前把 ρ 合进 α（见 D1）；③ loss 加 `rho_sparse_lam·mean(σ(ρ)[m_rho])`（**只对 m_rho 内**）；④ 计数①③④ Log；⑤ `_alpha_lifecycle_step` 末尾记计数② | `does_*` 为 False ⇒ 零执行 |

**渲染路径（v1 选项③定案）**：在 `GaussianModel` 的 `get_opacity` 内做钩子——
`rho.numel()==0` 时**直接返回 `σ(_opacity)`**（不做任何算术 ⇒ 逐位一致）；非空时返回
`σ(logit(σ(_opacity)) + ρ·m_rho)`。
**v2 补风险面（关卡① Q4/次要-5）**：`get_opacity` 的消费者包括 densify 的
`select`/`prune` 门、`reset_opacity*`、PLY 导出 ⇒ **评审要求**：
① ρ 只在 `map()` 的渲染调用窗口内"激活"（用 ctx 标志，渲染后立即失效），
使 densify/prune 读到的是**原 α**；② 单测断言 `rho 激活窗口外 get_opacity` 与
`rho_existence=False` 逐位一致。

### D5 稀疏先验（v2 收范围）

`rho_sparse_lam · mean(σ(ρ))`，**只对 `m_rho` 内的基元计**（v1 未限范围 = 全局副作用），
λ = 1e-3 **常数不衰减**（prereg v2 §9-4）。

## 2. default-off 逐位一致的证明路径（**v2 更正引证**）

三条机械保证 + 单测房式：
1. `rho_existence=False` ⇒ `map()` 内 `if params.does_rho_existence` 零执行；
2. `_rho` 为 `torch.empty(0)` ⇒ cat/prune/validate 的 ρ 分支恒等；
3. `get_opacity` 钩子在 `rho.numel()==0` 或**激活窗口外**时返回原值（不做算术）。
- **房式（v2 更正）**：v1 引 `tests/lifecycle_paper2/test_l1e_seam.py:123` 的
  `test_default_off_bitwise_identity`——该测试实际只比 config 参数，**不含 3 迭代 + `torch.equal`**。
  **真正的房式 = `tests/lifecycle_paper2/test_obsdebt.py:139-143`**
  （`test_boost_grad_mask_old_prims_bitwise_frozen`，负对照断言老基元逐位冻结）。
  v2 照后者写：同 seed 两态跑 3 迭代，`torch.equal` 断言 opacity/xyz 张量。

## 3. 点火计数落点（prereg v2 §4 四项）

| # | 计数 | 纯函数/落点 | 负对照单测（P23） |
|---|---|---|---|
| ① | `n_rho` | `m_rho.sum()` | 无 m_rho ⇒ 0 |
| ② | `n_adjudicated` | `rho_existence.count_adjudications(α_prev, α_now, 0.02)` | ρ 恒零 ⇒ 0；ρ 强推 ⇒ >0 |
| ③ | `n_sparse` | `m_rho ∧ (lam>0)` 计数 | lam=0 ⇒ 0 |
| ④ | `gnz`（grad 可达性，**v2 新增**） | `(ρ.grad[m_rho] != 0).sum()`，首/末 KF 各报 | 饱和 α 下 gnz ≈ n_rho（证明独立坐标不被压缩） |

## 4. 待审查问题清单（v2；v1 七问的处置见 §6）

1. D1 v2 的"独立坐标 + 独立 lr"是否真能在数值上快于 α 通道？（要求 §1 的数值表形式）
2. D3 候选乙（past_union 口径）在 balloon2 上的腾空区面积是否落在可判域内？（须实测，
   已知风险：密人群域过判）
3. D4 的"ρ 激活窗口"设计（ctx 标志）是否真能让 densify/prune 读到原 α？有无遗漏消费者？
4. D5 只对 m_rho 计稀疏先验，是否会使非腾空区基元的 ρ 无界漂移？（护栏 \|ρ\|≤8 是否足够）
5. §3 计数 ② 的"α_eff 跨 0.02 翻转"是否会**过报**（同一基元来回穿越多次）？
   是否需要"净翻转/唯一基元"语义？
6. 基元膨胀门在 ρ 只改 α 的设计下的触发渠道（prereg v2 §4 已给处置，须确认可测）
7. （v1 Q7 时间盒）→ **已在 prereg v2 §8 重排，本设计无剩余项**

## 5. 与 P0 的机械差异（防复发对照表）

| P0 的失效 | 乙 v2 的对应设计 |
|---|---|
| 60k 上限逐出覆盖 ρ 裁决（裁决无位置） | 无数量上限；ρ 裁决由 §3-② 在自己路径上计数 |
| P0n 消融混入 FIFO（等值 argsort 退化） | 乙 无逐出机制 ⇒ 无该混淆 |
| 成本读数 = 护栏/n_static（非机制需求） | 乙 只报实测逐 KF 基元曲线 |
| 梯度通道静默衰减无前置拦截 | §3-④ `gnz` 比值门（末/首 < 0.1 ⇒ 记衰减） |

## 6. v1 → v2 整改对照（关卡① 涉及本文件的项）

| 关卡① 项 | 处置 |
|---|---|
| 致命-1（引证不存在） | §0 更正（换 grep 证据） |
| 重大-1（D1 梯度论证错） | §1 重写 + 如实登记 v1 错误 + 数值表验收 |
| 重大-2（验收空判据） | §1 末改"数值表 + gnz 断言" |
| 次要-4（引证错位 test_l1e_seam:123） | §2 更正为 `test_obsdebt.py:139-143` |
| 次要-5（D4 漏 densification_postfix / split / clone / validate 白名单） | §1 D4 表补全 |
| 次要-3（膨胀门触发渠道） | §1 D4 + prereg v2 §4 处置 |
| 次要-6（P23 三步走） | §3 表 + prereg v2 §9-7 |

## 7. 变更记录

| 日期 | 版本 | 变更 | 依据 |
|---|---|---|---|
| 2026-09-25 | v1 | 初版（737dfaf6d） | Phase A |
| 2026-09-25 | **v2** | 关卡① Reject 整改（§6 六项）；D1 参数化重写 + D3 定案候选乙 + D4 补三处漏项 + §2 房式更正 + §3 增计数④ + §5 防复发对照 | 关卡① `/tmp/slam_critic_rho_prereg_2026-09-25.md` |
