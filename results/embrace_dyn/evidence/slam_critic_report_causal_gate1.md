# slam-critic 审查报告：embrace_dyn 因果批（关卡①，第 2 轮）
日期：2026-09-18  审查者：slam-critic（只读）

## 审查对象
- 待落地因果裁决书 `results/embrace_dyn/evidence/verdict_dyn_probe_causal.md`（2026-09-19 02:27，**未提交**）；
  一审增量 = 因果批 + 真损坏子集补遗；母批整改仅抽查（manifest 已记 gate_1=PASSED）。
- 判据机输出 `evidence/dyn_probe_verdict.json`（02:26，`causal_judgments`）、`evidence/dyn_probe_report.md`（02:26 因果节）。
- 原始数据 `evidence/dyn_probe_causal_results.json`（02:21）、`evidence/dyn_probe_results.json`（02:16 重生成）、`_rep2.json`（00:55）。
- 预注册 `prereg_dyn_probe_causal.md`（01:58）、补遗 `prereg_dyn_probe_badsubset_addendum.md`（02:11）。
- 工具 `scripts/02_analysis/dyn_probe.py`、`analyze_dyn_probe.py`、`tests/embrace_dyn/test_dyn_probe.py`（三者均 ` M` 未提交）。
- 分支 dev/v2；工作区 HEAD = e19d0a28；**manifest.json 记 `head` = "bc67143a"**（与裁决书标注不同）。

## 机械事实（先读 health_check）
- health_check 本轮未跑（离线判据工具，不涉在线配置门控；P26 的边界不适用于本轮——本轮无门控阈值项，C1b/C5 阈值均为离线判据常数）。
- **D1 实测通过**：`/data/conda_envs/monogs-ours/bin/python -m pytest tests/embrace_dyn/test_dyn_probe.py -q` → **26 passed, 2 warnings in 4.24s**（测试文件 ` M`，+81 行未提交）。
- 复算一致（亲自算，全部对得上）：C1b = (27.0843−20.1814)/(27.0843−15.3025)=0.5859（baseline 0.5890）；C1 = 4.6387/7.927=0.5852；C2 = 17.3328/14.1003=1.2293；C3 d_static = 22.9798−23.7598=−0.78；C5 = 18.6178/14.1003=1.3204；F1 bad 比值 15.3025/27.0843=0.5650（15.4664/27.8768=0.5548）、ΔPSNR 10.7362/11.0020；F2 PSNR 保留率 1.2766/10.7362=0.1189、baseline 0.1304。
- 配对性成立：`dyn_bad_px` 逐帧对 P1/P2/C-/P4 完全相同（16 帧均值 17747.125；15 帧 18314.47），M_bad 由 `bad_mask_of(p1_depth.get(idx),…)` 统一生成（dyn_probe.py:679/711/741/756/828）→ **不间接偏袒某一臂**（已验证）。
- `dt_kf` 全部 = 5；`dt_eval` ∈ {1,2,3,4}（15 帧）→ 与 prereg_causal.md:17-19 的跑前陈述一致。
- **309 ∉ KF 列表**（KF = 5,10,…,565，共 113 个）；P2c 在 f309 的 `kf=305, dt_eval=4`（该帧 P2c dyn_dl1 26.766 = 15 帧最差）。故"P2c 与 P2 在 f309 应完全相同"的预设**不成立**（309 非 KF，二者插入源不同）；若被审方在任何位置声称过该等价，即为事实错误。

## 问题清单

### 致命
- **[致命] 测量代码未提交，且裁决书与 manifest 标注的 HEAD 都不含测量代码 ⇒ 标注 commit 无法复算本批任何因果数字**
  证据：`git show e19d0a28:scripts/02_analysis/dyn_probe.py | grep -c bad_mask_of` → **0**、`grep -c P2cv` → **0**；`git show e19d0a28:scripts/02_analysis/analyze_dyn_probe.py | grep -c analyse_causal` → **0**；`git status` 两者均 ` M`，`git diff --stat` = dyn_probe.py +139/−、analyze_dyn_probe.py +134/−；`verdict_dyn_probe_causal.md:7` 写 "**HEAD：`e19d0a28`（测量提交）**"，而 `manifest.json` 的 `head` = **"bc67143a"**（与 e19d0a28 不同）。工件内无任何 git 哈希字段（因果 JSON 仅记 config/prereg 路径）。
  依据：D4（代码必须完全一致）/ D5（最小单元提交）/ D12（可追溯）；P25（跨版本比较须锁 commit）。
  反驳通道：提交当前工作区并给出新 commit；把裁决书 §头部与 manifest.head 改为同一 commit；若 bc67143a 确为含该代码的提交，提供 `git show bc67143a --stat | grep dyn_probe` 与一次同 config 复跑末值比对。

### 重大
- **[重大] 主臂由 P2cv 改为 P2c：预注册原文的主判据被降级，工件里记录的理由是跑后文本**
  证据：`prereg_dyn_probe_causal.md:52` "**C1 因果保留率（主判据）**：retention(P2cv) ≥ 0.50"，`:61-65` 出局规则 "¬C1 ⇒ **NO-GO**"；`prereg_dyn_probe_badsubset_addendum.md:30-31` 改判 `retention_bad(P2c) ≥ 0.50`（补遗正文**未提 P2cv**，其动机只讲掩码子集）；`analyze_dyn_probe.py:191-194` 直接 `pass = ret_b["P2c"]>=0.50` 且无条件 `C1.reference_only = True`；而 `analyze_dyn_probe.py:192-193`（= `dyn_probe_report.md:85`、verdict JSON 同字段）写 "主臂 = P2c，**因 P2cv 的速度估计器被实测证伪**" —— 该理由只能在因果批跑完后书写（P2cv 是因果批新臂，02:21 才有结果）。按原预注册，本批正式读数是 **NO-GO**；裁决书 §1 未并陈"原预注册=NO-GO / 补遗修订后=PARTIAL"两种读数。
  依据：D6 / P19（不得用事后叙事包装失效机制）；预注册纪律（判据与主臂跑前锁定）。
  反驳通道：提供补遗跑前性的可核验证据（提交该文件的 commit 哈希 + 时间戳早于测量提交）并说明补遗为何要同时换主臂；在裁决书 §1 增加一句并陈读数。
- **[重大] F4 的速度数字与工件不符，"物理不可能"不是全称判断**
  证据：`verdict_dyn_probe_causal.md:67` 与 `analyze_dyn_probe.py:198` 均写 "实测速度 **0.12–0.25 m/帧**"；`dyn_probe_causal_results.json` 的 P2cv 逐帧 `v_norm` 实测为 **0.0092 – 0.3473**（15 帧：0.2847/0.0255/0.1187/0.03/0.1884/0.3473/0.1847/0.2495/0.0206/0.0469/0.0092/0.1283/0.0119/0.03/0.2197；中位 0.1187、均值 0.1264）。低端 0.0092 m/帧 ≈ 0.28 m/s（按 30 Hz）属**正常步行**，高端 0.3473 ≈ 10.4 m/s 才不可能 ⇒ 应表述为"估计值散布 30 倍且高端物理不可能"，而非"实测速度 0.12–0.25"。且 m/s 换算所依赖的 30 Hz 未在任何工件中声明。
  依据：数字必须与工件一致（D12）；P1/P4/P29（口径与转录）。
  反驳通道：给出 0.12–0.25 的取数口径（若是分位数请写明分位）与帧率来源；或改为直接引 v_norm 极值/中位数。
- **[重大] 保留率的分子/分母帧集不一致（16 帧 vs 15 帧直接相除），且文档声称"天然不计入"对 P1/P2 项不成立**
  证据：`analyze_dyn_probe.py:170` 逐臂过滤 `good = [r for r in arms[a] if r.get("dyn_psnr") is not None]` ⇒ P2c/P2cv/C-c 丢冷启动帧得 n=15，P1/P2 仍 n=16（JSON `causal_judgments.*.means` 的 `n` 字段可证）；`:179-181/:186-188` 用 16 帧的 P1/P2 与 15 帧的 P2c 相除；而 `:162` docstring 写 "冷启动帧…**天然不计入**"。统一 15 帧复算：C1b = **0.5938/0.6072**（报 0.5859/0.5890）、C1 = **0.5901/0.5830**（报 0.5852/0.5757）。
  依据：D12（口径一致）/ P1 / P29（跨口径混引）；结论方向仍 PASS（更稳），但报出的数不是同帧集估计量。
  反驳通道：说明冷启动帧保留在 oracle/P1 分母中的理由，或按 15 帧重算并同步裁决书 §2 全部保留率与表格表头。
- **[重大] F1 的推断"剔除复制像素后收益更大 ⇒ 复制项不构成结论来源"不成立为推断（跨像素集的 dB 增益不可比）**
  证据：`verdict_dyn_probe_causal.md:46-52`；同一 JSON `criteria.1_ceiling` 的 P1 `dyn_bad_psnr` 20.5542 低于 P1 `dyn_psnr` 20.8388（子集是按 P1 误差挑选的，基线更差 ⇒ dB 增益机械变大）；口径一致的可比量是**深度比值** 0.5647 vs 0.5768（相对差 ~2%）。补遗 `:37-39` 的解释规则要求"分离量化复制项"，但被剔除的那 ~44%（M_good）上的增益**从未报告**，`verdict:51` 的"约 44% 的掩码像素属此类"只是**计数**不是增益 ⇒ 复制项大小实际上没有被量化。
  依据：D12；P6（用更细的采样/口径支撑判定性结论）。
  反驳通道：补报 M_good 上的 P2−P1 增益（同帧集均值口径）；把主比较改为深度比值/保留率并只把 dB 增益列为描述量。
- **[重大] M_bad 的深度指标混入 50 cm 惩罚常数，构成 PASS 的未分离风险（待证，非已证错误）**
  证据：`dyn_probe.py:376-378` 的 `dyn_bad_dl1_cm` 用 `penalized_depth_l1_cm(..., 50.0)`；而 M_bad 的定义（`bad_mask_of`，:325-338）**包含"P1 渲染深度无效"的像素** ⇒ 这部分像素对 P1 的贡献是人工 50 cm 常数而非实测误差，C1b 的分子/分母因此部分由常数决定。补遗 `:20` 称 M_bad "不含任何结果指标"，对**子集定义**成立、对**其衍生指标**不成立。
  依据：D9/D12（指标成分须可分解）。
  反驳通道：给出 M_bad 中"P1 深度无效"像素占比，并补报剔除这些像素后的 `dyn_bad_dl1` 比值与 C1b（一条命令即可）。

### 次要
- **[次要] PARTIAL / INSTRUMENT-INVALID 不在因果预注册的出局规则词表内** 证据：`prereg_dyn_probe_causal.md:61-65` 只有 GO / NO-GO / 仪器失效；`analyze_dyn_probe.py:212-220` 新增 PARTIAL 分支；`verdict:17` 直接采用。依据：D16（文档与判决同步）/ 预注册纪律。反驳：在裁决书 §1 标注"PARTIAL 系补遗后引入的第三类读数"。
- **[次要] 跑完未读列 + 因果节缺 dyn_cov 无效声明** 证据：因果臂产出 `kf/dt_eval/dt_kf/v_norm/cold_start`（`dyn_probe.py:832`）与 `dyn_cov`，但 `analyse_causal` 的 means（`analyze_dyn_probe.py:173-175`）不聚合它们，因果表（`dyn_probe_report.md:327-334`）不含这些列；母批在 `criteria.desc_dyn_cov` 声明过"恒 1.000 无判别力"，因果节（`dyn_probe_report.md:83-111`）无对应声明。manifest 已自承"produced-but-unread columns（第 4 次）"，但裁决书 §4 未写。依据：D9（静默组件须落盘证据并纳入清单）。反驳：在因果节加一行 dyn_cov 无效声明与"因果专列仅诊断用"说明。
- **[次要] 补遗"跑前锁定"缺可核验证据，只有 mtime** 证据：`_rep2.json`（00:55）中 `grep -c dyn_bad_px` = **0** ⇒ 损坏子集代码在 00:55 尚不存在；含 M_bad 统计的工件（母批 02:16、因果 02:21）**均晚于**补遗（02:11），补遗动机引用的 55.6% 与 17.7%–98% 无独立可核工件；`manifest.json.process_defects_selfdisclosed` 自承"四阶段在同一秒提交 ⇒ git 时间戳无法证明 prereg-before-results（仅 mtime 证据）"。裁决书 §4 未带该 caveat。依据：可追溯性（D12/D16）。反驳：把补遗单独提交并给出时间戳早于结果文件的 commit，或在裁决书 §4 明写"跑前性仅 mtime 支持"。
- **[次要] 55.6% 与 17,747 px 口径不一；17.7%–98% 实为 baseline 图范围** 证据：`verdict:47` 同时引用 17747 px（16 帧均值 → 占图 5.78%）与 55.6%（= 15 帧比值 18314.47/32961.2 = 0.5556）；`addendum:5-7` 的 17.7%−98% 与 baseline 逐帧范围一致（0.1773–0.9802），gate 图为 0.2208–0.9529。依据：P1/P29（口径混引）。反驳：统一为单一帧集口径并写明两图各自的逐帧范围。
- **[次要] L2 声明偏窄（三 run 而非两 run）** 证据：`configs/experiments/embrace_dyn/probe_pt2_causal.yaml` 注释称 P1/P2 重测"构成又一次 L2 数据点"；三工件 gate 的 P2 `dyn_psnr` = **31.1250**（母批）/ **31.1316**（rep2）/ **31.1362**（因果），极差 0.0112 dB，为 `manifest.json.reproducibility_L2.max_abs_delta_dyn_psnr_db` = 0.0055 dB 的 2 倍（P1 三 run 完全一致 20.8388）。量级可忽略（≪10.3 dB 效应），但"两次一致"的 L2 表述与三 run 事实不符。依据：D12 L2。反驳：更新 L2 段为三 run 口径并给出对应工件。
- **[次要] 两地图不是独立复现** 证据：gate/baseline 为不同 SLAM 臂的**不同地图**（`meta.gate.n_static`=55174 vs `baseline`=84162；run_dir 分别为 r33_rebase_**gate**/**baseline**_person_tracking2_seed0），同序列同 seed 的不同方法产物 ⇒ 一致只证明"地图鲁棒"，不能计为 2 个独立观测。依据：D8/D11。反驳：在 §4 明写该限制（"非同条件重复，不得作为样本量"）。
- **[次要] 冷启动/空分支记录形态不齐** 证据：`P2c` 帧 f2 记录 = `{"frame":2,"cold_start":true}`，而 `P2cv/C-c` 同帧 = `{"cold_start":1}`（布尔 vs 数值）；`dyn_probe.py:780` 的冷启动记录与 "empty" 分支（`{"empty":true}`，无 dyn_psnr）都会被 `:170` 的过滤静默丢弃 ⇒ `n` 缩小时无告警。依据：D9（静默路径须可见）。反驳：统一记录类型并在 n≠预期帧数时打印告警。

## 无法验证清单
1. **补遗的跑前性**：无 commit/哈希/独立诊断工件，仅 mtime + 自述；缺"早于结果文件的提交"或"产生 55.6% 的诊断脚本落盘"。→ 结论中必须保留该 caveat（见次要 3）。
2. **P2c 主臂替换的决定时点**：同上，无法区分"跑前已在补遗中锁定"与"跑后回写"；可确证的是**理由字段**（"因 P2cv 被实测证伪"）系跑后书写。
3. **M_bad 中 P1 深度无效像素占比**：需 per-pixel 中间量，未落盘（见重大 6）。
4. **30 Hz 帧率**：pt2 帧率未在任何工件中声明，m/s 换算无法核。
5. **KF 清单第二来源**：PLY 无 KF 字段（`dyn_probe.py:453-462`），单源 consolelog —— 预注册已声明为已知限制，本轮接受，但任何"KF 清单错误"类反例都无法用人造第二来源排除。
6. **D14/D17**：本轮为离线渲染，未核 GPU 型号/占用与监视器配置（离线短任务，影响有限）。
7. **远程数据覆盖（P28）**：本轮被审陈述中无"数据缺失/只有 N 个观测"型断言，故 P28 差集检查 N/A。

## 审稿结论
**Reject**（关卡① 不可落地）。阻塞项 = 致命 1（测量代码未提交 + HEAD 标注自相矛盾且不含测量代码）。重大 1-6 中，重大 1（主臂替换的理由系跑后文本、NO-GO/PARTIAL 双读数未并陈）与重大 2（F4 速度范围与工件不符）为**必须改文本**项；重大 3/4/6 为**必须补一条复算或一句口径**项（我给出的复算值可直接用：15 帧统一口径 C1b = 0.5938/0.6072，方向不变）。**本轮结论不推翻方向**（C1b 在两帧集口径下均 PASS；M_bad 配对性成立；D1 pytest 26 passed）：这是"改文本 + 补一条命令 + 提交代码"的清障清单，不是方向否决。
