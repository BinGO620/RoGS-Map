# verdict_L2_gate.md — L2 gate 泛化批判决书（人群族 gate 方向击杀确认）

**日期**：2026-09-22 ｜ **性质**：R7 L2 场景类型泛化（D2-005 用户拍板 A 的人群族部分）
**判据权威（不得在此重新定义）**：`prereg_L2_gate.md` §3–§4（判据先锁，commit `1479b516`，先于任何 L2 run）
**批量**：主判 3 run（`L2_{person_tracking2,crowd,crowd2}_gate_s0`）＋ 击杀确认分支 3 run（同序列 s1）
＝ 6 run；**对照 = 已有 L3 exit 同 seed canonical 渲染（零新增对照 run）**
**执行**：**6/6 rc=0**（`results/lifecycle_paper2/l2.done`、`results/lifecycle_paper2/l2_confirm.done`，
工件计数为准）；canonical 渲染 6/6 rc=0、`n_frames` 全 17（`canon_render.done`，`CANON_RENDER_DONE bad=0`）
**判据机**：`scripts/02_analysis/l2_gate_judge.py`（`--selftest` 四重负对照过；`--confirm`＝双 seed 重判分支）
**仪器**：freshvac/static PSNR 一律 **canonical**（`<seq>/dynamic_mask/`，掩码体系 v2.1，9 序列验证在案）

---

## 0. 一句话

**批判定 = 泛化不成立 ⇒ 按预注册 §3/§7，人群族 gate 方向击杀**：主判 1/3 见效（crowd），
预锁的击杀确认分支（补 s1 双 seed 重判）走完后**仍 1/3**——crowd 稳定见效（双 seed 同号为负、
均值 −2.15 > 门槛 1.19），pt2/crowd2 双 seed 均不见效。**不追加任何判据外 run**（prereg §7）。

## 1. 主判据（程序化；`l2_gate_judge.py --confirm` 逐字输出为权威）

| 序列 | gate（s0, s1） | exit（s0, s1） | Δ（s0, s1） | 门槛_seq | 见效 |
|---|---|---|---|---|---|
| person_tracking2 | 1.9521, 1.1805 | 1.856, 1.8155 | +0.096, **−0.635** | 1.8074（off_sd） | ❌（s1 方向对但幅度不足；s0 方向就反） |
| crowd | −0.72, 0.3844 | 1.7359, 2.226 | **−2.456, −1.842** | 1.19 | ✅（双 seed 同负、均值 −2.15，稳定） |
| crowd2 | −0.5824, −1.1166 | −1.4006, −0.3376 | +0.818, **−0.779** | 1.19 | ❌（s1 方向对但幅度不足；且 exit 本身已低于 off） |

- **批判定：见效 1/3 < 2/3 ⇒ 泛化不成立**（主判与确认重判一致；s1 只影响幅度不影响判定）。
- **结构性读数**（如实并陈，不改判定）：crowd 是唯一 exit 读数显著高于 off 的序列
  （off 均值 1.74 带 sd 0.95，exit 1.74/2.23 在带上方）⇒ gate 在 crowd 上的改善是
  "把 exit 的高残影拉回带内"；pt2/crowd2 的 exit 本身已处于带内低位 ⇒ gate 无位可降。
  与 L3 三口径结论（人群族无 exit 效应）自洽：**exit 效应的缺失正是 gate 无处发挥的原因**。

## 2. 约束门（逐序列报告，不改晋级判定）

| 序列 | ATE Δ（双 seed 均值） | static PSNR Δ | 判定 |
|---|---|---|---|
| person_tracking2 | +0.187 cm（+1.7%） | +0.47 dB | ✅✅ |
| crowd | +0.026 cm（+1.1%） | +0.93 dB | ✅✅ |
| crowd2 | +0.463 cm（**+20.5%**） | **−0.36 dB** | ❌❌ |

- 与 L1b（pt 双越门：ATE +1.36/PSNR −1.74）对照：**L1b 的代价 profile 不随泛化复现**
  ——三个 L2 序列中两个约束门双过；仅 crowd2 双越（其 exit 臂残影本就最低，改善幅度
  不足与代价越门同时出现）。
- 如实登记：约束门按 prereg §4 机械判定，crowd2 的越门不改晋级判定（晋级唯由 §1 决定）。

## 3. 过程验证（不作判据）

- **gate 全程点火**：6/6 run `capped_total` 1.6 万–6.9 万、`prevented_rise_sum` 413–2211、
  `no_mask_kfs = 0`（运行期掩码全程可用）。
- **⚠️ 偏离预注册预期（prereg §5 预先登记的观察位）**：`alpha_carve_total` 在 crowd=161/175、
  crowd2=93/117、pt2=1/0——**crowd 族 carve 显著触发**，与 L1b 在 pt 上的"α 钉死 0.2199 ⇒
  carve≈0"参数共振不同（密集场景多占据者压低了部分基元的 α）。按 prereg §5 如实登记为
  **偏离预期**，不作判据、不 retro 改判；其含义（carve 已活但效应仍 1/3）交 D2 参考。
- crowd 见效序列的 gate 读数（−0.72/0.38）为 6 run 中仅有的两个负 freshvac 值。

## 4. 边界与限制（如实登记）

1. **单 seed 对的结构**（prereg 选择）：击杀确认用 s0+s1 双 seed，但每序列只有 2 seed ⇒
   pt2/crowd2 的"不见效"结论的置信度受限于 n=2（R7 击杀路径本就要求最小化采样，不做全表陪葬）。
2. **canonical 掩码覆盖人物区域**：本判决语义 = "人物轨迹区残影"；crowd2 的箱子类移动者
   不在掩码内（口径声明随数字并陈）。
3. 关卡② 未过 ⇒ **本判决数字不得进论文/表**。
4. gateoff 一致性 run 未设（prereg §1：机制点火已由 L1b §3 确立）——本判决依赖该上游结论。

## 5. 对 D2 的含义（呈报；系统不自裁）

- **人群族 gate 方向击杀**（预注册 §7 预锁动作已自动执行完毕）：L1b 的正效应（pt 单序列）
  **未泛化**——真读数 = "crowd 一族稳定、pt 家族其余不成立"。按 prereg，**不追加 run**。
- **R2 状态**：证据门控族的**单次定位改进机会已用**（L1b 批）⇒ 族内参数重试（如 tau_carve/β）
  若无**新证据**支撑即触发"永久关闭"条款；L2 的 crowd carve 点火读数是本批新信息，可否作为
  "新证据"由 D2 裁定。
- **与既定方向的衔接**："人群族仍是要解决的问题"依旧开放，但 gate 路线已按阶梯走完并被
  击杀；剩余路径（诊断文件 §4 的 B1 参数修复 / B2 硬删 / 非门控路径 / 接受收口）的取舍
  属 D2——尤其"是否把 L2 的 carve 点火读数当作新证据再给一次机会"需要用户拍板。
- **box 亚族阶段性表述**（D2-005 A 的另一半）不受本判决牵连（其证据 = L3 canonical
  3/9 中的 mvnobox/mvnobox2，独立于 gate 路线）。

## 6. 三件套交付（R7 契约）

| # | 交付物 | 工件 |
|---|---|---|
| 1 | 渲染指标 | `render_L2_{pt2,crowd,crowd2}_gate_s{0,1}_canon/render_metrics.json`（6 目录 × 17 帧，freshvac/static PSNR，canonical 仪器） |
| 2 | 跟踪指标 | `L2_{seq}_gate_s{0,1}/tables/tracking_raw.csv`（ATE col8 口径）＋ `efficiency_raw.csv`（alpha_* 计数器） |
| 3 | 渲染图 vs 原图 | 同目录 `cmp_f*.jpg/png`（102 张，`--jpg` 产出；帧级对比随目录在仓） |

## 7. 复算命令

```bash
PY=/data/conda_envs/monogs-ours/bin/python
$PY scripts/02_analysis/l2_gate_judge.py              # 主判（s0）
$PY scripts/02_analysis/l2_gate_judge.py --confirm    # 击杀确认重判（s0+s1，本判决 §1 权威输出）
$PY scripts/02_analysis/l2_gate_judge.py --selftest   # 判据机负对照（四重）
```
