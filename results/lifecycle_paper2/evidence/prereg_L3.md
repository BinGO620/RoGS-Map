# prereg_L3.md — exit/carve **L3 幸存者正式批**预注册（A 档；D2-003 = C→A）

**日期**：2026-09-20 ｜ **状态**：**已过目（2026-09-20）**——用户三点按建议拍板（全 9 序列 / fill 仅 2 序列 / 帧集按修正案），**帧集与仪器见 `prereg_L3_amendment_1_frameset.md`（判据不变）**；待派发
**上位**：`DECISIONS.md` D2-003（C→A）｜ `verdict_L1.md` §8（L1 判决与整改）｜ `crowd_judgeability_confirm.md`（C 步裁决）
｜ `prereg_L3_amendment_1_frameset.md`（**帧集修正案**；逐序列帧号见 `l3_framesets.json`）
｜ `resources/lit_dyn_mapping/occupancy_recheck_2026-09-20.md` §3（**措辞收窄**）

## 1. 一句话

把 exit/carve 的**限定域**主张放到 Bonn 7 + box 族共 **9 序列 × 3 seed × {off, exit}** 上做正式批，
主判据用 C 步验证过的**离线密帧仪器**，出三件套与论文表。

## 2. 阶梯位置（R7）

- **L1**：15 run，{mvnobox, balloon2, crowd2}（`verdict_L1.md`）——mvnobox ✅、balloon2 口径/仪器冲突须并陈。
- **L2（泛化）**：由 **C 步**承担（crowd 族由"不可判"→"可判且方向为负"，3 对同码复制，诊断级）。
- **L3 = 本批**（幸存者正式批）。**层级偏离如实登记**：L2 未单独立批（以 C 步替代），原因是 crowd 族的问题
  是**仪器功率**而非机制泛化。

## 3. 序列与臂（**待用户确认**）

| 项 | 取值 |
|---|---|
| 序列（9） | **Bonn 7**：balloon / balloon2 / crowd / crowd2 / crowd3 / person_tracking / person_tracking2；**box 族**：moving_nonobstructing_box（=mvnobox） / moving_nonobstructing_box2（=mvnobox2） |
| 臂 | **主批**：`off` / `exit`（各 3 seed）；**定向臂**：`exit_fill` **仅** {mvnobox, balloon2} × 3 seed |
| seed | 0, 1, 2 |
| run 数 | 9×3×2 = **54**（主）+ 2×3 = **6**（fill）= **60 run** |
| 成本估计 | ~20 min/run ⇒ **≈20 GPU-小时**（双卡 ≈ **10–11 h** 挂机）+ 渲染 ~20 min；**低于** R4 的"单批 ≥3 GPU-天 ⇒ 升 D2"阈值 |

## 4. 仪器（**锁定**；理由见下）

| 项 | 取值 |
|---|---|
| 主仪器 | **离线密帧**：`render_compare --frames <l3_framesets.json 的逐序列 17 个帧号> --vacated-window-frames 30 --max-scale-m 0.5 --skip-unrenderable --ply final_after_opt`。**帧集公式与逐 id 清单以 `prereg_L3_amendment_1_frameset.md` 为唯一权威**（绝对网格 50..850 对 4/9 序列不成立；修正后 4/9 与已锁网格逐点一致，含 crowd2） |
| 主读数 | `mean_freshvac_ghost_excess_depth_l1_cm`（负 = 残影更小） |
| 副读数 | 污染代理 `mean_ghost_excess_depth_l1_cm`（仅描述，**不作判据**） |
| 运行期列 | **次要**：mvnobox/balloon2 的 61 列 CSV 有 `static_freshvac_*`，如实并陈；crowd 族仅 32 列（无 static 段） |
| 理由 | crowd 族**无运行期 static 列** ⇒ 若用运行期口径则该族无法进 L3；离线密帧仪器经 C 步在**三族**上均验证可用、且对称（护栏剔除 0.3–0.4%、无臂间偏差） |
| 禁止 | **跨仪器/跨口径绝对比较**（`verdict_L1.md` §2/§6/§8 C9） |

## 5. 判据（**跑前锁定**；机械应用）

1. **逐序列主判据**：3-seed 配对 Δᵢ = exitᵢ − offᵢ（freshvac）；
   **PASS ⟺ ≥2/3 同号（预期为负）且 |mean(Δ)| > 门槛**，门槛 = `max(1.19cm, 该序列 off 臂 3 seed 的组内 sd)`。
2. **批级判定**：**≥6/9 序列 PASS 且无序列越 ATE 门** ⇒ 机制按"**限定域**"成立（措辞见 §7）；
   否则按逐序列结果如实写（不放大、不隐藏）。
3. **约束门（逐序列，任一越门 ⇒ 该序列标注"越门"）**：ATE Δ ≤ **+0.5cm** 且 ≤ **+5%**；
   static PSNR ≥ **−0.25dB**（L1 沿用；L1 已有 mvnobox s1 = −0.2676dB 的前例，故须逐序列披露）。
4. **如实入表（不作门）**：基元增幅、护栏剔除数、跳过帧数、运行期 `alpha_exit_reset_total`/`alpha_carve_total`。
5. **交付（三件套/序列）**：渲染指标表 + 跟踪指标表 + **渲染图 vs 原图**（重点帧）。

## 6. 流程与闸门

- 本预注册**先提交**（本文件），**再**经用户过目确认 → 才派发（D2-003 承诺）；
- 派发前 `sync_to_remote.sh` 三方一致；两卡并行（按序列分 worker），派发后 2 分钟内查活；
- 收口：判决书 `verdict_L3.md` → **关卡①**（独立审查）→ **关卡②**（数字入表前）；
- **失败分支**：若 <6/9 PASS ⇒ 机制退回"**box 族限定域**"写法（回 D2 重议），不追加 run（R2：每族一次）。

## 7. 与文献占位的对应（占用复核 §3 的收窄措辞，写作时必须遵守）

主张措辞 = "**在线 RGB-D SLAM 环路内、无检测/无掩码/无资产库的基元级退场清理 + ATE/vacated 分区评测**"；
**正面引用并区分 CubifyGS**（arXiv:2606.28720，物体级、需检测器+资产库、GT 位姿无 ATE）；**禁用**"首次提出鬼影清理"类措辞。

## 8. 三点确认记录（**已过目 2026-09-20**；其余按上表执行）

| # | 事项 | 用户答复 | 落定 |
|---|---|---|---|
| 1 | **规模**：60 run / ~10–11 h 双卡（含 fill 定向臂） | **按建议** | 全 9 序列（不砍 `crowd3` / `person_tracking*`） |
| 2 | **fill 臂**：只做 {mvnobox, balloon2} 两序列（而非全 9） | **按建议** | 2 序列 × 3 seed = 6 run |
| 3 | **主仪器**：离线密帧作为**全序列统一**主判据（运行期列降为并陈） | **按建议** | 帧集按 `prereg_L3_amendment_1_frameset.md`（绝对网格对 4/9 序列不成立，已修正为上界 `min(850, N−2)` 的 17 帧；**判据不变**） |
