# verdict_L1c_occupancy.md — L1c 时序先验（区域占据记忆）判决书

**日期**：2026-09-23 ｜ **性质**：R7 L1 最小效果验证（D2-006 时序先验族第一个 L1；R2 计时从立项起算）
**判据权威（不得在此重新定义）**：`prereg_L1c_occupancy.md` §3（判据先锁，commit `bdad543f`，先于任何 run）
**批量**：4 run ＝ 1 occoff s0（off 一致性）＋ 3 occ s{0,1,2}（主判据臂）；**对照 = 已有 L3 exit 同 seed canonical（零新增对照 run）**
**执行**：**4/4 rc=0**（`results/lifecycle_paper2/l1c.done`，工件计数为准）；canonical 渲染 4/4 rc=0、n_frames 全 17
（`canon_render.done`，**双卡分批**：occ_s1→cuda:1、occ_s2→cuda:0 并行——44d9c4d1 改造首战）
**判据机**：`scripts/02_analysis/l1c_occupancy_judge.py`（import 复用 L1B loader；`--selftest`
负对照 3 重 + 1 正例；occ_* 计数器自 C1 整改起由判据机程序化输出，与 §3.1 表格同源）
**仪器**：freshvac / static PSNR 一律 canonical（掩码体系 v2.1）；机制代码 default-off（occ 臂 `evidence_gate: false` 显式隔离）

---

## 0. 一句话

**主判据 PASS=False（1/3 seed 负、mean Δ=+0.24 cm）→ 预锁击杀确认分支执行完毕
（补 occ+exit s{3,4,5}，0/3 对达标）⇒ 终局：时序先验族按 R2 关闭**（D2-006 立项承诺兑现）。
6-seed mean Δ=−0.22 cm 但散布 ±4 cm、无臂间信号——与 postmortem"84-run 无一致分离"同形态。
证据门控族（L1b PASS 带代价）与 exit/carve 族（box 亚族 3/9）判决均不受影响。

## 0.1 确认重判（预锁分支 §3；2026-09-23 凌晨执行）

| 对 | Δ(occ−exit) 两 seed | 同负 | 幅度>1.19 | 达标 |
|---|---|---|---|---|
| s0/s3 | +0.8904 / **−3.9936** | ✗ | ✓ | ✗ |
| s1/s4 | +0.3598 / **+3.1684** | ✗ | ✓ | ✗ |
| s2/s5 | −0.5391 / −1.2216 | ✓ | **✗（|mean|=0.88<1.19）** | ✗ |

- **0/3 对达标 ⇒ 族关闭**。6-seed Δ 全景：+0.89/+0.36/−0.54/−3.99/+3.17/−1.22
  （mean −0.22）——**双向大幅散布**，任何方向的一致信号都不存在；
  s3（−3.99）与 s4（+3.17）相邻 seed 反号且幅度对称，是管线混沌的典型形态
  （同 L1b s0 21.05 教训：单点不可归因）。
- 确认批执行件：occ_s{3,4,5} 3 run + exit_s{3,4,5} 3 run（**对照侧补齐**——prereg 未
  显式写配对对照侧补齐，属判据不变的执行必需件，commit `8f90f00d`/`5e6a42eb` 留痕）。
  全部 rc=0、双卡并行训练+渲染（`l1c_confirm.done`/`l1c_exit_confirm.done`）。
- occ 确认批计数器同型（decay 3/1/3 次、warm 6.5-6.7 万、no_mask=0）——机制持续点火
  但转化率瓶颈与主判一致，无翻盘迹象。

## 1. 主判据（程序化；`l1c_occupancy_judge.py` 逐字输出为权威）

| seed | occ freshvac | exit freshvac | Δ |
|---|---|---|---|
| 0 | 3.7597 | 2.8693 | **+0.8904** |
| 1 | 3.7897 | 3.4299 | **+0.3598** |
| 2 | 3.4038 | 3.9429 | **−0.5391** |

- 门槛 = max(1.19, off_sd=0.6699) = **1.19**；PASS=False（sign_ok=False ∧ mag_ok=False，ratio 0.20）。
- occ 三 seed（3.76/3.79/3.40）与 exit（2.87/3.43/3.94）、off 带内混叠——**无臂间分离**
  （与 postmortem 的"84-run 批无一致分离"同形态）。

## 2. 约束门（逐 seed 报告）

| seed | ATE Δ | static PSNR Δ | 判定 |
|---|---|---|---|
| 0 | −2.254 cm（−17.5%） | +0.96 dB | ✅✅ |
| 1 | −2.019 cm（−17.0%） | +0.25 dB | ✅✅ |
| 2 | +1.033 cm（+9.4%） | −0.03 dB | ❌✅（ATE 越门） |

- 2/3 seed 的 occ ATE **显著优于** exit（−2.0~−2.3 cm）——与 L1b gate 的 s0 单点爆炸形态相反，
  这里是 s2 单点越门（12.03 vs exit 11.00；带外？不，在 off 带内）。如实并陈，不改判定。

## 3. 过程验证与机制诊断（为何转化率 ~0.01%）

### 3.1 点火与正对照（prereg §4 预锁观察位全兑现）

| 读数 | s0/s1/s2 | 判读 |
|---|---|---|
| `occ_warm_prims_total` | 66,987 / 71,830 / 66,534 | ✅ 千级正对照过——机制**确实覆盖**人物轨迹区 |
| `occ_alpha_lt_guard_total` | 3,444 / 9,471 / 3,234（≈30/70/28 每 KF） | ✅ 预锁观察位（prereg §4）：α<guard 群体非零——机制**有可作用对象** |
| `occ_no_mask_kfs` | 0 / 0 / 0 | ✅ 运行期掩码全程可用 |
| `occ_decay_events_total` | **9 / 14 / 7** | ⚠️ 转化率 ~0.01% |
| `alpha_gate_capped_total` | 0（occ 臂显式关 gate） | ✅ 归因隔离成功 |
| occoff occ_*/gate_* 计数 | 全零 | ✅ off 行为面 |

### 3.2 off 一致性三门（prereg §4）

① **代码面**：`git diff be504ab0..bdad543f -- slam.py gaussian_splatting/` = **空**；
同区间机制侧新增全部在 `utils/`（occupancy_memory.py 147 行 + slam_backend.py 接线 72 行 +
alpha_lifecycle.py 25 行）——**不等于"核心零改动"**，其安全性由 **flag-gating 逐行核验**承担：
`does_occupancy_memory`/`does_evidence_gate` 默认 False（`alpha_lifecycle.py:122,132`）、
backend 消费点受其门控（`slam_backend.py:1000`）、occ config 显式 `evidence_gate: false`；
② **行为面**：occoff 的 occ_*/gate_* 计数器全零（判据机输出为证）；③ **轨迹面**：occoff
ATE=11.3209 落同序列同栈全部 L3 run 实测带 [10.37, 12.85]（off 三点 10.37–11.92、exit
三点 10.99–12.85；两种定义下均带内）。**三门全过 ⇒ 本批可比。**

### 3.3 机制-场景错配的定量诊断（consolelog 逐帧解析）

- **warm 群体 α 系统性偏高**：warm 均值 582 基元/KF，但每 KF 实测被衰减仅 9/115 ≈ **0.08 个/KF**
  ——对照 `occ_alpha_lt_guard_total`（α<guard 群体全图 ≈30/KF）可见：**问题不在 α<guard
  群体不存在（它有 ~30/KF），而在 warm ∩ (α<guard) 的交集极小**。人物刚走过的区域里，
  基元以新鲜插入（初始 α 0.3–0.7）与被再占据观测推高者为主 ⇒ **guard 护栏正确工作，
  但衰减够不到钉死群体**（0.22–0.24 在 guard 内，却极少恰好在 warm∧<guard 的时刻被命中）。
- **衰减方向正确但量级不足**：occ a_min 末段 0.228–0.232 vs occoff 0.2475（持续 −0.016 下压）；
  9 次衰减全部方向正确。
- **postmortem 的预言部分兑现**：衰减通路确实"无几何门可达"（9 次衰减验证），
  但"区域占据时序 → 低 α 群体"的**时间窗错配**是新的瓶颈——人占据时新基元 α 高；
  人离开后基元 α 已被 EMA 推高，warm 窗（10 KF）却过期了。

## 4. 边界与限制（如实登记）

1. **单序列**（pt，判决性测试设计）；n=3；机制参数（voxel 0.05/K=10/γ=0.9/guard 0.35）
   为首锁值，未做敏感性扫描（R2 纪律：改参须修正案，且本判决后仅剩确认分支一次机会）。
2. canonical 掩码覆盖人物区域 ⇒ 主张语义 = 人物轨迹区残影（口径声明随数字并陈）。
3. 关卡② 未过 ⇒ **数字不得进论文**；本判决为机制验证级。
4. off 三门全过 + 判据机负对照过 ⇒ 本批可比性与程序合规（关卡① 见 §6）。

## 5. 下一步（prereg §3 预锁分支——已执行，见 §0.1）

- ~~补 s1 三序列 3 run 双 seed 重判~~ → **已执行并终局：0/3 对达标 ⇒ 时序先验族按 R2 关闭**。
- **族关闭后的去向**（D2-006 立项时的承诺路径）：转论文写作收口——**正面主张** = box 亚族
  （L3 canonical 3/9 支撑）；negative results 按 `DISCIPLINE.md:363` 纪律**只以"边界小节/
  讨论"身份存在**（不进贡献栏、不起包装性命名、不作 headline、不称机制贡献）。

  > **2026-09-23 更正（纪律违纪登记）**：本行原写"三条通路的完整否定链**本身是可讲的
  > 贡献**"——违反 `DISCIPLINE.md:363`（负结果不进贡献栏/不称机制贡献）。该表述已撤回；
  > reset/carve 几何门、gate 带代价、occupancy 时序窗三组读数以**边界小节素材**身份存在，
  > 不作为论文的主张或贡献。
- **不做的**：不追加判据外 run；不做参数敏感性扫描（R2 已关闭）；occ+gate 叠加臂取消。

## 6. 关卡①（程序合规审查）——判决落盘**之前**已送（修正 L1b 顺序偏差）

- 审查瘦包：本判决草稿（§0–§5）+ prereg_L1c_occupancy.md + 判据机 + 计数器/ATE 工件。
- 审查重点：①判据机与 prereg §3 逐条对应（∀3 负比 L1b 的 ≥2/3 更严，selftest 已验）；
  ②off 三门证据链；③击杀分支表述与 prereg 原文一致性；④"诊断不推翻判据"的纪律
  （§3.3 只解释、不改判）。
- **结论 = Accept-with-conditions（2026-09-23，关卡先于落盘合规）**：数字 100% 复算一致、
  无致命项；2 项重大整改已清（C1 判据机补 occ_* 九键程序化输出消除"禁手抄"矛盾 /
  C2 代码面表述改为"slam.py+gaussian_splatting 零改动 + α 侧 flag-gating 逐行核验"）、
  次要项已清（lt_guard 计数行补入 + 0.08/KF 量纲修正 + 负对照措辞 3负+1正 + 轨迹带
  定义声明）。全量报告：`/tmp/l1c_gate1_report.md`。

## 7. 复算命令

```bash
PY=/data/conda_envs/monogs-ours/bin/python
$PY scripts/02_analysis/l1c_occupancy_judge.py              # 主判据 + 约束门 + 计数器（= §1–§3 权威输出）
$PY scripts/02_analysis/l1c_occupancy_judge.py --selftest   # 四重负对照（含 2-of-3 拒绝）
```

## 8. 三件套交付（R7 契约）

| # | 交付物 | 工件 |
|---|---|---|
| 1 | 渲染指标 | `render_L1c_person_tracking_{occ_s0..5,occoff_s0,exit_s3..5}_canon/render_metrics.json`（10 目录 × 17 帧，canonical 仪器） |
| 2 | 跟踪指标 | 同名 run 目录 `tables/tracking_raw.csv`（ATE col8）+ `efficiency_raw.csv`（occ_*/alpha_* 计数器，判据机程序化输出） |
| 3 | 渲染图 vs 原图 | 同目录 `cmp_f*.jpg/png`（170 张，`--jpg` 产出） |
