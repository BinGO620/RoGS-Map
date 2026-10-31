# embrace_online — P0 离线因果侦察（D2-014；prereg 见 evidence/）

> **实验 ID**：`embrace_online`（V2 形态 = 在线生命周期地图；P0 = 探针层离线仿真，零训练）。
> **预注册**：`evidence/prereg_P0_embrace_online.md`（判据先锁；硬顶 2026-09-29，实际 09-25 完成）。
> **执行计划**：`resources/notes/embrace_online_p0_plan_2026-09-25.md`。
> **状态**：✅ P0 已判决 = **FAIL（出口 3）**——见 `evidence/verdict_P0_embrace_online.md`；
> 呈报分流 = **D2-016**（甲 = 乙 单独 L1【默认建议】/ 乙 = 丙 纯写作边界；R3 默认不实装不派批）。

## 1. 本地冒烟（2026-09-25，2060，debug 件已删——**非权威，不入判读**）

截断帧集（t0=205，走帧 11 帧，gate 图）验证代码路径，产出三件标定事实：

1. **代码路径通**：五臂（P1/P2/P0o/P0n/C-o）全出数；canonical 掩码加载正常
   （`mask=dynamic_mask`）；C-o 对照臂响应正常（PSNR 9.17→7.01）。
2. **canonical M_bad 与 GTMC 时代量级不同**：M_bad ≈ 42.6k px（GTMC 时代 17.7k）；
   P1 基线 M_bad PSNR ≈ 5.8 dB（GTMC 时代 20.55）；P2 oracle 锚 Δ ≈ +22 dB（GTMC +10.7）。
   ⇒ 历史阈值不可裸移植，须同批自锚（P2/C- 已入臂清单）。
3. **插入率 ≈ 2.0–2.5k 基元/帧**（体素 0.02m 去重后）：11 走帧缓冲 27,667 ⇒ 60k 护栏预计在
   走帧 ~24 帧后钉死（J4 成本线必超，出口上限 = 边界——预注册机制如实生效）；
   ρ 中位数随走帧下降（0.882→0.862，先验在起作用）。
4. **prereg §9 修订**（正式批前）：J7 拆分 J7a（VOID 出口项）/ J7b（C- 锚标定诊断）——
   1.15 深度比值阈值系 GTMC 仪器历史值，canonical 仪器未标定（冒烟 C-o 深度比值 0.90，
   但 C- 锚可重标定）。

## 2. 正式批（远程 3090）

- configs：`configs/experiments/embrace_online/probe_pt2_online.yaml`（主域）+
  `probe_balloon_online.yaml`（泛化）；臂 [P1, P2, C-, P0o, P0n, C-o]。
- 判据机：`scripts/embrace_dyn/judge_p0.py`（两份 results + configs → `evidence/p0_online_judgments.json`）。
- 读数与判决：跑批后由判据机程序化产出；verdict 落盘**前**过关卡①（DISCIPLINE 收口审查关卡 1）。

## 3. 产物清单（跑批后补齐）

- `evidence/p0_probe_pt2_results.json` / `p0_probe_balloon_results.json`（cmd_render 原始输出）
- `evidence/p0_online_judgments.json`（判据机）
- `evidence/verdict_P0_embrace_online.md` + `manifest.json`（关卡① 后落盘）
- 三件套：分区表 + 静态区表 + 对比图（`render_compare.py` 重点帧）
