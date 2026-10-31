# prereg_struct_codec — 「均匀量化 + 体素合并」codec 主表（诚实版 codec 贡献）

> **账本**：D2-026 写作轨；本件 = **判据先锁**（跑批前提交，记 **commit 哈希** `2a07d9740`，
> 提交 15:12:39，**先于** L2S 首批工件 mtime 15:25 ⇒ 先锁成立）。
> **背景**：关卡② G2 已证——论文 Tab.6 的 6×/8.8×/15× = **朴素均匀量化 + zlib**
> （42 图 `alloc=uniform, iso_scale=False, range_mode=full`），**不含任何结构感知件**；
> 而正文 §4 却声称"adaptive + 结构感知"。⇒ **方法描述与数字脱节**（叙事站不住的技术根源）。
> **本批目的**：给 §4 一个**言行一致**的 codec 主表 = **均匀量化 + 体素合并(dedup 2cm)**，
> 并把结构件（iso-scale/记账剥离/robust 范围）降级为消融。

## 1. 机制（先锁，default-off，离线零污染）

codec = 逐属性均匀标量量化（global min/max range，同既有 L2 口径）+ **体素合并**
（`--dedup-voxel-m 0.02`：按 2cm 体素合并近重复基元，保留每体素最高不透明度者，
`rd_harness.py:260` 已实现）。**位宽点 = 主表三点**：near 16/8/8/8/8 / mid 10/6/6/6/6 /
aggressive 8/4/4/4/4。

## 2. 面板（与 L2 主表同批，禁止混引）

**42 图 = baseline + final 臂 × Bonn 7 序列 × 3 seed**（run_dir 取自既有
`results/gs_compress/evidence/rd/L2_*_rd_table.json` 的 `run_dir`，本地在盘，零 SLAM 重跑）。

## 3. 判据（R1 机械应用，禁手抄）

渲染指标 = `render_compare`（离线渲染，固定帧 0/60/120/180/240，与 L2 主表同帧集）。
率 = `codec_bytes / orig_full_bytes`（`orig_full_bytes = n*20*4`，与 L2 同分母）。

- **C1（主判）**：uniform+dedup 的近无损点 PSNR 损失 ≤ 0.05 dB（相对同 run baseline 渲染），
  且压缩率 ≥ 6.5×（即体素合并把 uniform 的 5.96× 抬到 ~7×，与 L1 §6.1(e) 的 7.26~7.70× 对得上）。
- **C2（边界登记，非判负）**：体素合并丢基元比例 ~18–20%（L1 §6.1(a) 实测）⇒ 如实报"省字节靠丢基元"，
  不得包装为"无损编码"。
- **C3（口径）**：体素合并是压缩文献**已有操作**（非本稿首创）⇒ 正文如实引 CGS-SLAM/DiskChunGS 的
  同类思路，**不主张机制新颖**。

## 4. 对照（A 的核心：让 R-D 表可读）

R-D 表五行坐标系（同一分母 n*20*4）：
1. `source`（1.00×，渲染上界 PSNR）
2. `raw zlib`（~1.6×，无损下限，`raw_zlib_baseline.json` 已备）
3. **uniform quant（= 朴素基线）**：5.96×/8.77×/15.11×（**既有 L2 表**，即"naive quantization"）
4. **uniform + dedup（= 本文 codec，本批）**：预期 ~7×/~9.5×/~16×
5. 激进端 uniform（15×）

⇒ 第 3 行是朴素基线、第 4 行是本文 codec——**对照 = 体素合并的增益**，这才是 §4 该主张的
（**不是**"我们造了个新量化器"）。

## 5. 出口（R1 机械）

- **C1 过** ⇒ codec 主表 = uniform+dedup（本批数字），§4 按"均匀量化 + 体素合并"改实；
  结构件（iso/robust/记账剥离）→ §5.2 消融。
- **C1 不过**（dedup 损 PSNR > 0.05 dB 或压缩率 < 6.5×）⇒ 论文 codec 退回纯 uniform（即现状），
  §4 删除所有"结构感知"措辞，体素合并也降消融。

## 6. 关门前置（G2 必查项，跑批后送 slam-critic 关卡②）

- 数字与工件逐位复算（`L2S_*_rd_table.json`）。
- 口径：分母同源（n*20*4）、同批（L2 run_dir）、同帧集（0/60/120/180/240）。
- 臂归属：baseline + final（**不是 gate**，G2-M1 已纠；本批沿用同臂）。
- 对照单变量：唯一变量 = 是否加 `--dedup-voxel-m 0.02`。

## 7. 批信息（跑批前提交）

- 批 tag：`L2S_${seq}_${arm}_s${seed}`（Struct codec 批；**不覆盖** 既有 `L2_*`）。
- 驱动：`scripts/gs_compress/struct_codec_batch.sh`（写本文件后提交）。
- 判据键：`results/gs_compress/evidence/rd/L2S_*_rd_table.json`。
- 成本预估：42 图 × 3 点 = 126 渲染调用；单图 ~1–2 min（离线渲染 5 帧）⇒ 串行 ~2–4 h；远程 3090。
