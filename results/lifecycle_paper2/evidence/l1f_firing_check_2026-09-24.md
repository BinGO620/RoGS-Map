# L1f 点火验证（D9 组件生效验证；2026-09-24；派发后首次核）

> **性质**：prereg_L1f_obsdebt §2b 锁定的**点火计数机械验证**（关卡① P23 条件）。
> **结论：不合格 —— 判定为"实装缺陷 + 设计面过薄"，须修复后重跑；本批读数不进判决。**

## 1. 三项机械判据（prereg §2b）

| # | 判据 | balloon2 主臂 | person_tracking 主臂 | 判定 |
|---|---|---|---|---|
| ① | 账本增长（`obsdebt KF … total=` 递增） | **81 行**，total 递增至 61,668（texel 18,737） | **66 行**，递增至 938+ | ✅ **生效** |
| ② | 预算重分配（`obsdebt-fill … kept=`） | **0 行** | **0 行** | ❌ **从未触发** |
| ③ | 迭代配额（`obsdebt-boost … extra_steps=[1-9]`） | **0 行**（1 行 `skipped`） | **0 行** | ❌ **执行即崩** |

对照臂（`exit_fill_ctrl`）`obsdebt` 字样 **0 行**（default-off 干净）；两臂 `alpha-fill` 各 80/81 次，
`inserted` 总量主臂 101 / 对照 59（2/3 seed 见同量级）。

## 2. 三分归因（D9 要求）

| 类别 | 判定 | 证据 |
|---|---|---|
| 组件本身无效 | **否（尚不可判）** | 分配律从未真正运行 ⇒ 无效应数据可依 |
| **配置或依赖错误** | **是（两处）** | ③ `obsdebt-boost skipped: element 0 of tensors does not require grad`——整个 lifecycle step 包在 `with torch.no_grad():`（`utils/slam_backend.py:912`），反传被禁梯度；② 预算分支条件 `uu.size > params.fill_max_points(2000)` 在本域**结构性不成立**——实测 vacated 峰值仅 **101 px**（历史 L3 批同域 max=122 px），**差 20×** |
| 工件错位 | 否 | 账本/日志/工件均在位 |

## 3. 处置

1. **③ 实装修复（已提交）**：boost 段局部 `torch.enable_grad()`（仅本块重开梯度），
   不动 no_grad 主结构。
2. **② 属设计面过薄（登记，不在本批内改）**：`fill_max_points=2000` 是既有 fill 预算，
   本域 vacated 峰值 101 px ⇒ "超预算时按债重排"**永不发生**。这是**设计缺陷**：
   分配律设计在"预算从不紧张"的域上 = 无作用面。修法有二（**须 prereg 修正案 + 用户知悉**）：
   - **甲**：把分配律改为"**按债加权增量插入**"（高债 vacated 像素允许超出自然计数插入，
     即真正的"容量定向补回"，直接回应 D2-011 ② 的容量诉求）；
   - **乙**：承认该域预算不紧张，放弃 ②（机制只剩 ③），如实以"单分支机制"立判。
3. **本批 9 run 的位置**：**保留作"无分配律基线"**（主臂与对照在分配律未生效时行为近似，
   其差值噪声即 §5 的"零效应参照"），**不进判决**；修复后**重跑主臂 3 run**（Δ 用新 run）。

## 4. 对时间盒的影响

修复（③）+ 重跑（3 run ≈ 40 min，双卡 20 min）在硬顶 10-02 内充裕。
② 的处置属**设计选择**，按 `DISCIPLINE.md`「时间盒与硬门」与 R5 归类：**升一级**
（机制形态变更 ⇒ 须 prereg 修正案；未获答复按 R3 执行最保守可逆项 = **乙**（不扩面、单分支立判））。

## 5. 复算命令

```bash
# ① 账本增长
grep -c "obsdebt KF" <console.log>
# ② 预算重分配（应 >0 才合格）
grep -c "obsdebt-fill" <console.log>
# ③ 迭代配额（应 >0 才合格）
grep -oE "extra_steps=[0-9]+" <console.log> | grep -cv "extra_steps=0"
# vacated 峰值（② 的结构性证据）
grep -oE "vacated=[0-9]+" <console.log> | sort -t= -k2 -n | tail -1
```
