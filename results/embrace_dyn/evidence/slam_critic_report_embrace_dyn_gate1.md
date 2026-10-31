# 审查报告：embrace_dyn / dyn_probe 判决草稿（关卡①）

审查对象：results/embrace_dyn/evidence/verdict_dyn_probe.md（未提交工作区）
HEAD=bc67143a（dev/v2）


## 检查块1：锁定性与 commit 时间
- 四个 commit（521b01b0 探针 → e243b311 预注册 → 507775e4 判据机 → bc67143a 结果）**时间戳完全相同** 2026-09-19 00:42:31（`git log --format='%h %ad' -4`）⇒ 一批提交，git 无法证明"预注册先于结果"；仅文件 mtime 支持（prereg 00:27 < results 00:40），且 4 个 commit 同秒 = 攒批（D5）。
- verdict_dyn_probe.md / manifest.json mtime 00:43 **早于** control_p1_vs_render_compare.json 00:45 ⇒ 判决落地时阳性对照尚未完成。
- 判据机只实现 5 条判据（analyze_dyn_probe.py:52-77），预注册 §7 有 6 条；⑥ 阳性对照未进判据机、未进 verdict 表、未进 report.md，而 verdict 写"五项预注册判据全过"。
- L2 复现声明（verdict_dyn_probe.md:44）在 evidence/ 下**无第二个结果工件**（ls 只有单个 dyn_probe_results.json）。
- 未读列：dyn_px / vacated_px / shift_cam_m 在每条记录中产出（json 记录键），判据机 means 只取 7 键（analyze_dyn_probe.py:40-42）。
- dyn_cov 全 1.000 含 P1(n_dyn=0)。

## 检查块2：健康检查（本地 --json）
```
7cde0408
37691a2a
7cde0408 文献调研可写区补任务书 PROMPT.md（自包含：铁律边界/机制级深读卡模板/会场标定/接口问题）
9efbf2e6 embrace_dyn: 判决草稿（关卡① 待过，文件头显式声明）+ manifest 可追溯元数据 + 实验 README
b804afa6 embrace_dyn: 阳性对照落盘——探针 P1 全图 PSNR 与既有 render_compare 8/8 帧逐位一致（max|Δ|=0.0003dB）
ee04ee0a tests: embrace_dyn 门禁 13 项（判据机四态/配置-预注册一致/证据自洽/几何工具正确性）
bc67143a embrace_dyn: 探针结果（materials + 四臂阶梯两地图）+ 判据机报告（两地图均 GO）
507775e4 analyze_dyn_probe: 确定性判据机（阈值取自预注册 §7，输出逐臂均值+两项远 t0 子集+判决）
```
## 检查块3：判据机忠实性（逐字对照 prereg §7）
- TH 七值（analyze_dyn_probe.py:23-26）与 prereg §7 逐字一致：0.70/2.0/1.30/gap50/0.25/0.25/0.50/1.15 全对。
- ① 用 16 帧全均值（:53-56）✓；② 子集 abs(frame-t0)>=50（:44）、P4/P2（:59-61）✓ n=12 复算=12（帧表算出）✓；③ 双侧 abs(ds)<=0.25 且 df>=-0.25（:63-66）**忠实于 prereg 字面**✓；④ P2 mean_n_dyn/n_static（:70）✓；⑤ C-/P2（:73）✓。
- 判据机**只实现 5 条**：prereg §7 有 6 条（⑥ 阳性对照，prereg 第 93-94 行），analyzer 无 ⑥；verdict 表 5 行、README:41 写"五项预注册判据"。
- 判据机静默默认：`res["config_t0"] = res.get("t0_frame") or 309`（analyze_dyn_probe.py:100）；`cfg = ...`（:99）取出后**从未使用** ⇒ 判据机不校验结果 JSON 的 config/frames/t0 是否等于预注册。（注：实测 results JSON 回写 t0_frame=309/frames/16f/fit_iters=300/lrs/unproj_stride=3/control_shift=[0.3,0,0]，与 config/prereg 一致 ✓）
- 独立复算（本审查用 python 复算）：gate P2/P1 dl1=10.8082/18.7390=0.5768 ✓、Δpsnr=10.2943 ✓、C-/P2=1.7696 ✓、P4/P2(far)=19.1491/10.4910=1.8253 ✓、cost=3532.06/55174=0.0640 ✓；baseline 全对。n_static 独立核 PLY 头 `element vertex 55174` ✓（baseline 未核 PLY，仅核 JSON 与 materials 一致=84162）。

## 检查块4：证据完整性与"跑完未读"
- P2 16/16 记录含 fit{iters:300,loss_first,loss_last,opa_before/after} ✓（D9 生效验证在 P2 成立）；**P4 16/16 无 fit 键、C- 亦无**（json 实测 with_fit=0）⇒ verdict:77 "每帧拟合均落盘" 只对 P2 成立。
- verdict:77 引用的数（gate 0.140→0.029、opa 0.50→0.71；baseline 0.150→0.033、0.50→0.78）**与 JSON 中 P2 逐帧均值不符**：实测 gate 0.1130→0.0270、opa 0.5000→0.7578；baseline 0.1127→0.0267、0.5000→0.7709。无来源标注。
- `dyn_px`（dyn_probe.py:340）、`vacated_px`（:369）每记录产出，全仓库**无任何消费者**（grep 仅命中写入行）；报告/verdict 均无这两列 ⇒ ghost_excess 行的支撑像素数无处可查（NOTES:419 的"跑完未读"第 4 例）。
- `dyn_cov`：128/128 记录恒为 1.0（含 P1 n_dyn=0）⇒ 该预注册指标（prereg §6）在本设定下**零判别力**（掩码内背景高斯已满足 opacity≥0.5）；它仍出现在 dyn_probe_report.md 表里，verdict 表把它静默删了（未说明原因）。
- 阳性对照工件：control_p1_vs_render_compare.json（max_abs_delta_db=0.0003，8 帧 0/80/160/240/325/405/485/565，config=/tmp/debug_probe_control.yaml）；帧集 ≠ 锁定 16 帧；未进 manifest.artifacts、未进 tools、未提交（git status: ??）。

## 检查块5：地图/口径/结论核对
- 残影盘点（materials_dyn_probe.json ghost_inventory，23 帧抽样@每25帧）：n_in_mask_front gate min=1/max=335/mean=82.9；baseline min=2/max=1016/mean=157.2 ⇒ prereg:26-27 与 verdict:57 的"2–1016 点/帧"**取的是 baseline 区间**（gate 最小为 1）；"<0.2% 高斯"=**均值**(0.150%/0.187%)，而区间上端 1016/84162=**1.21%**（gate 335/55174=0.61%）。均值为真、区间上端超出所述上界 6 倍。
- "投影进掩码 12–13%"：复核 mean(share_in_mask)=0.1289(gate)/0.1209(baseline) ✓ 成立。
- 判据② 的 P4 臂 n_dyn=11906（3.37× P2 的 3532）且只在 t0（cov 最大帧）插入 ⇒ P4 vs P2 的"运动必要性"未配平成本/插入时刻；conclusion 2 的"朴素保留动态比抹掉更差"与"损伤静态区 −1.17dB"针对的是**这一个**朴素变体。
- "两地图"= 同一序列/同一 seed/同一 16 帧/同一掩码的两套地图栈（gate=部署形态、baseline=论文1栈），**非独立复现**；verdict:65、README:67、manifest limitations 均已写"两张同批地图"，未发现越界表述。
- P2 非因果性：verdict:62-63、README:64-66、manifest limitations[0] 三处均显式限定，且 verdict:63 明确"不说我们能在线达到 31 dB" ✓。
- 判据③ prereg 文本缺陷（双侧 |Δ|）已在 verdict:68-70、README:70-71、manifest limitations 如实登记，未追溯改判 ✓。
- 未在 limitations 出现的一条：**动态基元进入在线损失/BA 对 ATE 的影响未测**（本项目红线=ATE 第一验收标准，且 ATE 与 PSNR 反相关），verdict:87-88 却已把建图/渲染侧升级为"有方法贡献的空间"。
- health_check 本地：FAIL「Sync 本地≠origin」（见检查块2 输出）；INFO「embrace_dyn 四件套 缺少 scripts」；WARN 简化臂外推（paper2_fulltable，即本探针两地图的来源实验）与本探针无直接冲突。

## 无法验证清单
1. DynaPSNR 归因完备性：prereg §6:72 / manifest metrics 称与 DynaGSLAM arXiv 2503.11979 的"唯一差异=额外要求 GT 深度有效"；未核原文（缺论文定义原文/截图）。若还有其它差异（峰值、掩码膨胀、是否排除预热帧），归因不成立。
2. L2 复现：evidence/ 下**只有一份** dyn_probe_results.json，无第二次运行的落盘；"P1/C- 逐位一致；含拟合臂偏差 ≤0.0088dB/0.0224cm"（verdict:44、README:48、manifest reproducibility_L2）不可复算；且 C- 由 P2 拟合结果平移得到（prereg §4），拟合非确定时 C- 不可能"逐位一致"——须提供两次运行原始 JSON/log。
3. 非确定性归因"rasterizer 反向原子加"无实验证据（dyn_probe.py:381 仅 torch.manual_seed(0)，未见 determinism 开关或对照跑）。
4. 16 帧选择规则"掩码覆盖 ≥ 非零帧中位数 3.44%"不可复算：materials JSON 只存 cov_mean/cov_med/cov_max/frac_nz，无逐帧覆盖率向量；t0=309 的 cov=0.362 亦不可复算（materials gtmc cov_max=0.416 是别的帧集）。
5. 拟合"生效"的语义未验证：无 loss 曲线/不透明度分布，仅有首末两点；且 P4 无任何 fit 落盘（见上）。
6. 残影盘点是 23 帧（每 25 帧）抽样，而评估帧是另一组 16 帧，两集合几乎不重叠 ⇒ "每帧 2–1016"是抽样外推，代表性未论证。
7. P2 插入的深度有效范围 dmin=0.2/dmax=8.0（dyn_probe.py:246 默认值，调用点 :590/:626 只传 stride）未写入 prereg。
8. baseline 地图 PLY 顶点数未独立核对（仅 JSON 自报 84162 与 materials 一致）。
