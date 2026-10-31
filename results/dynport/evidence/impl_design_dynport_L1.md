# impl_design_dynport_L1.md — DynPort 在线实装设计（给执行模型的工程说明）

> **账本**：**D2-027**（DynPort 立项）。**判据本体 = `prereg_dynport_L1.md`**（本文件不新增判据）。
> **性质**：实装说明——为关卡③（G3）提供"实装如何在代码层面满足 prereg"的证据；执行模型照本文件干。
> **边界**：实装位全在核心保护区（`utils/` + `gaussian_splatting/`）⇒ 走 DISCIPLINE「代码保护」例外流程全链
> （prereg 先锁 ✓ → default-off → 单测两态 → 关卡③ → 派发）。
> **前置状态**：prereg 已锁（`03ffdee6f`）+ G1 整改（`a599caaba`）。**本文件写完后先过关卡③**，再动代码。

## 0. 一句话

把 `scripts/02_analysis/dyn_probe.py` 里**已验证**的 `DynPortBuffer` 算法（Case1 KNN 复用 + Case2 新建 +
Cond1/Cond2 删除）**移植到在线环路**：方法输入换成本仓**运行期 MaskRCNN 掩码 + 传感器深度 + 在线位姿**，
评估分区仍用 canonical `dynamic_mask/`（只读）。default-off，关闭时与主线逐位一致。

## 1. 实装原则（必须先守）

1. **default-off 逐位一致**（代码安全判据）：`DynPort.enabled` 缺席/False ⇒ 行为与 HEAD **逐位**相同。
   单测两态覆盖：`test_dynport_default_off_bit_identical`。
2. **探针≠在线**：`dyn_probe.DynPortBuffer` 用 **GT 深度 / `trj_est` 离线位姿 / canonical 掩码**；
   在线**禁止**调用探针类。在线须换 **传感器深度**（`viewpoint.depth`）/ **在线估计位姿**（前端当前位姿）/
   **运行期掩码**（`get_or_compute_dynamic_mask`）。单测守护"在线路径不 import 探针函数"。
3. **不改核心语义**：新机制走 config 开关；不改 `slam.py` 主干逻辑。
4. **最小单元提交**：每写完一个文件/一组相关文件立即 commit（显式路径，**禁 `git add -A`**），提交后
   `git show --name-only` 回读。

## 2. 五个改动点（精确到文件与函数）

### 2.1 新增 `utils/dyn_port_buffer.py`（算法本体）
- 顶部放开关三件套（仿 `utils/semantic_mask.py:75-85`）：
  ```python
  def get_dynport_config(config): return config.get("DynPort", {})
  def dynport_enabled(config): return bool(get_dynport_config(config).get("enabled", False))
  ```
- `class DynPortBuffer`：从 `dyn_probe.DynPortBuffer.d` 的 dict 结构（keys: `xyz/log_scale/rot/opa/dc/rest/K`）
  搬起，`step(...)` 保留 Case1（cKDTree 1-NN，`d_min ≤ λ_d·d̄` 替换均值）+ Case2（新建）逻辑
  （原型见 `dyn_probe.py:1101-1145`）。
- **G1-重大#9**：`cap` 默认设 **50000**（原型默认 60000），显式传参。
- **落盘计数器**：每 KF 追加一行 `frame, inserted, case1_hits, cond1_deleted, cond2_deleted, cap_hits, n_dyn`
  到 `dynport_counters.csv`（J5 生效证据；无落盘 = 静默组件，违纪）。
- 依赖 KNN：`scipy.spatial.cKDTree`（仓内已有用例）。

### 2.2 `utils/slam_frontend.py`（插入挂载）
- 在 `maybe_insert_transient` / `maybe_insert_object_transient`（`:1828/:1986`）**同位置**加
  `maybe_insert_dynport(cur_frame_idx, viewpoint, ...)`；`if not dynport_enabled(self.config): return`（默认关）。
- 输入：`viewpoint.dynamic_mask`（运行期 MaskRCNN，`slam_frontend.py:1219` 已缓存）+ `viewpoint.depth`（传感器）
  + 当前在线位姿。**禁止**读 canonical 目录、**禁止**用 GT 深度。
- 注意 `g.get_xyz` 是 `@property`（D1-021 坑）——取属性，不写 `g.get_xyz()`。

### 2.3 `utils/slam_backend.py`（生命周期 + 分优）
- mapping 循环里：动态层跑 Cond1/Cond2 删除 + 滚动窗局部拟合；动态像素继续从静态图损失剔除（沿用现通路
  `get_or_compute_dynamic_mask` + `get_loss_mapping_rgbd`），动态子图**另起一份损失**（解耦优化，防残影）。
- 参考插入点：`slam_backend.py:671/727`（现有 `dynamic_mask=...` 消费处）。

### 2.4 `gaussian_splatting/scene/gaussian_model.py`（动态子结构）
- 加 `dynamic` 子结构：复用 `_gaussians_from_points`（`:410`）建、`densification_postfix`（`:1104`）/
  `cat_tensors_to_optimizer`（`:1070`）风格 cat、`prune_points`（`:950`）风格 delete。
- **ledger 同步（坑#5）**：动 `_xyz` 时必须同步 `static_prob/lineage_id/n_obs` 等辅助字段（`prune_points` 会动它们）。
- 渲染器只读 `get_*` 属性 ⇒ **不必**给 GaussianModel 加渲染成员（`dyn_probe.render_once` 已演示只读视图可行）。

### 2.5 config
- `configs/rgbd/<dataset>/base_config.yaml` 加（默认关）：
  ```yaml
  DynPort:
    enabled: false
    lam_d: 0.05
    cap: 50000
    lmax: 45
    unproj_stride: 3
    fit_iters: 300
  ```
- 新 `configs/experiments/dynport/L1_<seq>_{E,D,Cneg}.yaml`（单变量：仅 `DynPort.enabled`；
  Cneg 另置插入错位 0.30m 的机制参数）。
- **键名统一** `unproj_stride`（G1-次#5）。

## 3. 四件套与测试
- `tests/dynport/`：① `test_dynport_default_off_bit_identical`（off ≡ 主线）；② `test_dynport_case1_reuse`
  （KNN 命中替换均值）；③ `test_dynport_cond2_delete`（寿命删除）；④ `test_dynport_no_probe_import`
  （在线路径不 import 探针函数，守"探针≠在线"）；⑤ `test_dynport_config_parse`（开关默认关）。
- 判据机：`scripts/dynport/judge_dynport.py`（仿 `scripts/embrace_dyn/judge_p0.py`；数字零手抄；
  M_bad 分区用 **canonical** 掩码，机制插入用运行期掩码——两源分离）。
- 批驱动：`scripts/dynport/run_L1.sh`（写本文件后提交；远程 3090；ATE 批可并发、计时批串行）。

## 4. 执行顺序（阶梯，禁跳）
```
1. 写 impl_design（本文件）→ 提交 → 关卡③ G3
2. G3 过 → 实装 utils/dyn_port_buffer.py + 开关 → 单测 ①⑤ → 提交
3. 挂前端 2.2 → 单测（生效计数非零）→ 提交
4. 挂后端 2.3 + 模型 2.4 → 单测 ②③④ → 提交
5. config 2.5 → 标定轮（crowd2 单 run 定 lmax）→ 落 calibration.json → 提交
6. L1 批：crowd2 + balloon2 × {E, D, C−} = 6 run（冒烟测先行，批级硬顶 ≤4h）
7. 判据机 judge_dynport → 判决 → 关卡② → 账本 D1- 新行
```

## 5. 坑清单（逐条对照；违反即事故）
| # | 坑 | 规避 |
|---|---|---|
| 1 | 跨代码版本比性能（D1-027） | 重跑主表前 HEAD 一致，新旧数字禁混引 |
| 2 | 计时并发毁 A/B（D1-024/025） | J4② 单卡串行 + 相邻配对 + 交替 + I/O 不圈进计时 |
| 3 | `get_xyz` 是 `@property`（D1-021） | 取属性，不调方法；单测桩须复制 property 语义 |
| 4 | default-off 不逐位一致 | 机制 key 缺席 ⇒ False；单测两态 |
| 5 | 动 `_xyz` 漏同步 ledger | 同步 `static_prob/lineage_id/n_obs` |
| 6 | 探针类上在线环 | 单测守"在线不 import 探针" |
| 7 | canonical 掩码当方法输入（G1-M2） | 方法输入=运行期掩码；canonical 只作评估分区 |
| 8 | 判据先锁失效 | prereg commit（03ffdee6f）< 批工件 mtime |
| 9 | 不做 | 不借 RAFT/SAM2/DynoSAM；不做持久 4D 记忆；不救 SWBA |

## 6. 交付三件套（R7）
渲染指标表 + 跟踪指标表 + 渲染图 vs 原图（`scripts/02_analysis/render_compare.py`，含重点帧放大框）。缺一件 = 未完成。

## 7. 时间盒
实装硬顶 **2026-10-09**（含单测两态）；L1 硬顶 **2026-10-13**（到点未过即止损，不追加 run）。

## 8. 实装期修正登记（2026-10-06，冒烟测抓出；DISCIPLINE #9）

设计时的 §2 是纸面推演；本机 2060 冒烟（crowd2, 120 帧, **非权威 pilot**）抓出两处 CPU 单测
覆盖不到的**真实缺陷**，均已修复（commit `fd2a105cf`）：

1. **架构修正（§2.1 之外的新事实）**：在线地图是**共享 GaussianModel**（后端 mapping 与前端
   tracking 都渲染它，经 push_to_frontend 同步）⇒ 动态基元必须插进模型才能渲染。决策核因此
   改为 `MapAccess` 协议（`utils/dyn_port_buffer.DynPortBuffer`）+ adapter
   （`utils/dyn_port_online.GaussianModelMap`），而非自持张量字典。
2. **occ_aware_visibility 尺寸脱钩崩溃**：插入/删除重排模型数组，而逐 KF 全尺寸可见性掩码
   （前端 `is_keyframe` 依赖）不同步 ⇒ 首跑 frame 5 崩（22113 vs 39595）。修：步内原始下标追踪
   （`begin_step/end_step` → `orig_map`）+ 后端 `_dynport_sync_occ` 重排。
3. **动态基元被静态管线静默清空**（DynaGSLAM「分储合渲分优」的"分优"缺失）：`densify_and_prune`
   （opacity<min_opacity）+ `reset_opacity_nonvisible` + densify clone/split 把动态基元当静态裁剪
   （KF5 插 17482 → KF10 仅 50 计数的 Cond1，其余 ~17k 无声消失）。修：`GaussianModel.dyn_lineage_base`
   （默认 0 = 逐位不变）+ `_dynport_protect` 在 densify_and_prune 豁免 lineage ≥ base；
   reset_opacity_nonvisible 同豁免。
4. **跟踪隔离口径降级（诚实登记）**：原设计"push_to_frontend 剪动态 lineage"实测**不可行**
   （与 occ 掩码脱钩）。改**经验口径**：不剪 payload，跟踪损失经 `tracking_dynamic_mask` 掩动态像素，
   J8 直接测 ATE；**不作"结构性隔离"主张**（E2 先例 prereg_E2_online §2-D 的显式退路）。

**冒烟结论（非权威）**：D 臂 rc=0、机制三件全活（case1/case2/cond1 计数正常）；E 臂 rc=0 且
**0 行 DynPort 日志**（default-off 静默成立）；pilot ATE D 0.0146 < E 0.0150 m（方向性，未到判据线）。
⇒ 机制**确认生效**，可进 G3 + 正式 L1。

