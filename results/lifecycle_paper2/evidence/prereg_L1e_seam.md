# prereg_L1e_seam — 缝隙带救援（三信号 carve + param-rescue 对照臂）

> **性质**：L1e 预注册。判据先锁、先于任何 run 提交。
> 依据 = `offline_diagnosis_2026-09-23.md`（dfb19da5）：pt 鬼影卡三堵墙——
> 几何门 5-10cm 缝隙带（reset 0.05 复位删不掉 / carve 0.10 够不着）、α 钉 0.2199>0.20、
> exit 模式无 fill。用户 2026-09-23 拍板批准（"批准计划开始执行"）。
> **时间盒**：9/26 出终局判决；两臂皆败 ⇒ C 路线（论文重定位），写作解冻不晚于 10-01。

## 1. 假设（一句话）

pt 鬼影可删，当且仅当三个独立证据同时同意：**掩码说"人最近来过但已离开"**（区域证据，
crowd3 误删的防线）∧ **几何说"它悬在观测面前 5-10cm"**（缝隙带，postmortem 的死因带）
∧ **α 说"它已经不被信任"**（<0.25，L1d 棘轮证明可压下）。三信号合取的误删天花板 =
三者同时错的概率，每个都有独立护栏（净静态 α≈1 被 α 门挡、区域外被掩码门挡、
真表面被几何带挡）。fill 走 exit_fill 现成管线（balloon2 已验证全链可用）。

## 2. 臂与成本

| 臂 | config | 形态 | 作用 |
|---|---|---|---|
| **seam（主臂）** | `l1e_person_tracking_seam.yaml` | exit_fill + **新实装** `select_seam_carve_mask`（sem_vacated ∧ in_front(0.05) ∧ α<0.25 ∧ obs≥3 → prune；default-off 新键 `seam_carve`） | 一次拆三墙 |
| **param（消融对照）** | `l1e_person_tracking_paramrescue.yaml` | exit_fill + **零新代码纯 config**：`tau_carve: 0.25` + `delta_free_m: 0.05` | 分辨"三信号必要" vs "参数本来就错"（D2-005 B 未测路径；R2 新证据 = 缝隙带诊断推翻当时否决依据） |
| 对照 | L3 exit s{0,1,2} canonical | 已入库 | 零新增对照 run |

6 run（2 臂 × 3 seed）双卡 ≈1.5h GPU + 渲染 6 tag。

## 3. 主判据（先锁）

Δ = arm − exit（freshvac，canonical 仪器，与 L1b/L1c/L1d 同源）。
**PASS ⟺ ∀3 seeds Δ<0 ∧ |mean Δ| > max(1.19, off_sd)**（off_sd 沿用 L1d 判据机的
L3 off 三 seed 程序化计算）。

## 4. 约束门 + 误删护栏（先锁）

- 约束门同 L1b：ATE ≤ +0.5cm 且 ≤ +5%；static PSNR ≥ −0.25dB。逐 seed 报告，越门不自动 FAIL。
- **误删护栏（crowd3 挖洞形态的显式防线，本批新增）**：`mean_static_coverage` 逐 seed
  不得 < 0.99（off/exit 实测 0.9998-1.0）。护栏破 ⇒ 该 run 判**无效**（挖洞形态，
  不进判决、不追加 run、如实登记）——与"计数器出口=0 是合法读数"相区分：这是
  **安全性破洞**不是无对象。

## 5. 诊断预测（预锁，不作判据；各带数据源工件键）

| # | 预测 | 工件键 |
|---|---|---|
| D① | seam 臂 carve 计数 pt 首次 >0（缝隙带救援的直接指纹） | efficiency_raw `alpha_carve_total` |
| D② | seam 臂 fill_inserted > 0（洞被补上） | `alpha_fill_inserted_total` |
| D③ | seam 的误删护栏绿（static_coverage ≥0.99）且 reset 计数形态与 exit 同型（量级 10²） | render_metrics + efficiency_raw |
| D④ | param 臂：若 carve>0 且 Δfv<0 ⇒ "参数本来就错"故事胜；若 carve>0 但护栏破/Δfv>0 ⇒ crowd3 形态复现，三信号的必要性加强 | 同上 |

## 6. 击杀分支（预锁）

任一臂非 3/3 负 ⇒ 该臂补 s{3,4,5}（3 run；对照复用，exit s3-5 已入库）。
6-seed 配对重判仍不过 ⇒ **缝隙带救援族关闭**（seam+param 双臂一并，不再有本方向变体）；
**C 路线启动**：先出一页论文重定位方案呈用户过目，写作解冻不晚于 10-01。
（关照 `DISCIPLINE.md:363`：负结果只以边界小节身份存在，不进贡献栏/不命名/不作 headline。）

## 7. 配置生效验证（四层，派发前全过）

1. 静态 diff：seam vs `l3_balloon2_exit_fill.yaml` 仅差掩码/序列/save_dir/新键；
   param vs 同上仅差两个常数键。
2. 两态实例化 pytest：seam 臂 `does_seam_carve ∧ does_fill` 双 True；param 臂
   tau_carve=0.25 ∧ delta_free_m=0.05 落进 params；off 语义不变（default-off 逐位一致）。
3. **三信号合取行为单测**：合成场景——缝隙带基元（z=obs_at−0.07）三信号齐 ⇒ 删；
   缺任一信号（区域外/深度差>0.10 已归原 carve 管/α=0.5）⇒ 不删；α≥guard(0.35) ⇒ 永不删。
4. 提交纪律：prereg+config+实装+判据机一次提交记 sha；`git status --porcelain scripts/ configs/` 空
   才派发；渲染清单**同一 commit 列全 2 臂 × s{0..5}**（NOTES 硬规则）。

行为面计数器契约（入口/出口语义照 NOTES 2026-09-23 条）：入口 = carve 发火数>0
（seam 臂新增 `alpha_seam_carve_total`）+ fill_steps>0；出口 = inserted 可为 0（合法读数）。

## 8. 流程铁律（沿用）

关卡① slam-critic 先于 verdict 落盘；判决数字指工件键（判据机程序化输出）；
verdict 头部双溯源；三件套交付（渲染指标 + 跟踪指标 + 渲染图 vs 原图）；
跑批期禁改在批脚本、禁 sync；L2/TUM 只在 L1e PASS 后另立 prereg。

## 9. 反悔方式

GPU ≈1.5h 沉没；run 数据可弃；实装 default-off 一键回退（revert 单 commit）；
用户可 R6 一句话否决。失败成本 = 2 天时间盒 + 边界小节素材 +1（论文不受损）。
