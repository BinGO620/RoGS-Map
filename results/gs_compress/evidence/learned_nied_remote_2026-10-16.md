# Niedermayr c3dgs 基线：远程 3090 执行记录（2026-10-16，exp52）

> 状态：**远程执行已放弃**（GPU0 物理掉卡 → 机器重启后 sshd 未起、不可达）。
> 用户决策：**不冒险，全部 78 张改回本机 2060 产出**（原因见 §3），使 ratio 与渲染同源。
> 本文件保留远程尝试的完整过程与现场证据。

## 1. 本轮做了什么

| 步骤 | 结果 |
|---|---|
| 参数化驱动/环境脚本 | `learned_nied_c3dgs_baseline.py` 三处绝对路径（`NIED_REPO`/`PY_MONOGS`/`PY_NIED`）与 `build_nied_c3dgs_env.sh` 四项路径改为环境变量可覆盖，默认值=本机口径，两机通用 |
| rsync 同步 | 3 脚本 + `submodules/compressed-3dgs-niedermayr/`（196M，含 glm 与 DC-only 补丁）+ 已缓存 12 个 npz → `jiangwenheng:/home/jiangwenheng/cron/monogs-ours` |
| 远程建 env | venv `.venvs/nied-c3dgs`；torch 2.4.1+cu118；torch-scatter；两个 CUDA 扩展编译通过 |
| 冒烟 | `L2_crowd_baseline_s0 --iters 200`：colmap 928 帧 → 压缩 → 解码 → 渲染，全链路通（ratio 5.78×） |
| 全量派发 | L2 与 L3 各占一张卡并发（`CUDA_VISIBLE_DEVICES=0/1`），`--iters 5000` |
| 中断 | 约 12:11 远程 GPU0 掉卡，CUDA 全域不可用；机器重启后 sshd 始终未起 |

### 远程环境的两个坑（已解决，记录备查）

1. **`/usr/local/cuda-11.8` 是空壳**（只有 `nsight-systems`，无 `bin/nvcc`）。远程真 nvcc 11.8 在
   conda 环境 `nvcc118` 里 ⇒ `CUDA_HOME=/home/jiangwenheng/anaconda3/envs/nvcc118`。
   `build_nied_c3dgs_env.sh` 已支持该覆盖，脚本头写了远程示例。
2. 远程 `rsync` 是 3.0.6，不支持 `--info=stats1`。

## 2. 本轮修掉的一个真 bug（重要）

**`slam_run_to_colmap.py` 的帧集口径错了。** 原实现用 `sorted(dataset/rgb/*.png)` 原始 glob，
但 SLAM run 与 `render_compare` 走的是 `utils/dataset.py::TUMParser` 的 **rgb↔depth↔pose 关联后**
序列。TUM 序列两者不等，导致 L3 **第一张地图就断言失败**（`rgb 数 640 != trj 帧数 635`）：

| 数据集 | 原始 glob | 关联后 | 差 |
|---|---|---|---|
| Bonn `rgbd_bonn_crowd` | 928 | 928 | 0 |
| Bonn `rgbd_bonn_balloon2` | 469 | 469 | 0 |
| Bonn `moving_obstructing_box` | 590 | 590 | 0 |
| TUM `freiburg1_desk2` | 640 | 635 | 5 |
| TUM `freiburg1_room` | 1362 | 1315 | 47 |
| TUM `freiburg3_sitting_rpy` | 820 | 796 | 24 |

修法：改用 `load_dataset(...).color_paths`（与 render_compare 同源），并把 `dataset_path` 绝对化后传入。
**对 Bonn（L2）是零影响**（已验证仍 928 帧），只修 L3。若无此修复，L3 全部 36 张都会失败。

## 3. 跨机一致性核对（**只覆盖解码+渲染，不覆盖压缩**）

远程 json 覆盖了本机此前已跑的 12 张 L2 地图。逐行比对：

```
max |Δratio_full| = 0.000000      max |Δmean_psnr| = 0.0000      (12/12 tags)
```

⚠ **但这条证据的适用范围比它看起来窄，必须照实登记**：那 12 张的 npz 是本机 rsync 过去的，
远程启动时**直接复用**（远程日志行 `[nied] L2_balloon2_baseline_s2: 复用已有 npz`）。因此：

| 环节 | 是否被该核对覆盖 |
|---|---|
| 解码 + 渲染（PSNR/SSIM/LPIPS/depth 列） | ✅ 已证跨机一致（两架构、同输入、结果逐位相同） |
| ratio 列（QAT 微调 → VQ → 量化 → 熵编码的 npz 字节数） | ❌ **未验证**——12 张的 npz 本来就来自本机 |

即：**「远程数字可直接用」这个结论对渲染列成立，对 ratio 列不成立。** 风险量级上，npz 是量化+熵编码
产物，跨机浮点差异只在量化边界翻位，对字节数的影响是 ppm 级（远低于表中两位小数）；但两机的 CUDA
扩展是各自编译的（不同 SM 架构），无法在远程掉线时证否。

**结论（2026-10-16 用户决策）**：不冒险，**全部 78 张改回本机 2060 产出**，让 ratio 与渲染同源。
远程这 48 行只作为过程记录保留（`rd/partial_remote3090/`），**不入表**。

### 3b. 决定性对照：压缩这一步**确实是机器相关的**（实测，n=1 起）

本机全量重跑把这件事从"未验证"变成了"已实测"。逐张比对时要注意**哪些是有效对照**：
balloon/balloon2 那 12 张的 npz 是本机 rsync 过去的、远程只是复用 ⇒ 字节相同是必然，**不算对照**。
第一张真正的独立对照是 `L2_crowd2_baseline_s0`（远程压过、本机又压了一遍）：

| | 远程 3090 | 本机 2060 | 差 |
|---|---|---|---|
| npz 字节 | 544485 | 544774 | **+289（+0.053%）** |
| ratio\_full | 5.913302 | 5.910167 | **−3.14e−3** |
| 渲染 mean PSNR | 13.7686 | 13.7213 | **−0.047 dB** |

**⇒ 两台机器压出来的 npz 不同，渲染质量也不同。** 先前的推断（"跨机差异只在量化边界翻位，
影响 ppm 级"）被证否：实际量级 0.05%，高三个数量级。机制：5000 步 QAT 是混沌的梯度优化，
两机 CUDA 扩展各自编译（不同 SM 架构）、浮点归约顺序不同 ⇒ 轨迹发散 ⇒ 量化边界翻位远多于线性外推。

**这条把用户的决定从"保险"变成"必需"**：混机产出的表会让 ratio 列混入两个分布。
n=1 只是起点；本机全量跑完时，全部 36 张"远程压过"的地图都会有本机重压对照，
可给出 Δratio/ΔPSNR 的完整分布（待补）。

## 4. 远程已完成的部分结果（**已弃用，不入表**）

| split | 远程已完成 | 部分均值 ratio | 部分均值 PSNR | 部分均值 Δ |
|---|---|---|---|---|
| L2 | 34/42 | 6.11× | 16.29 | +0.55 dB |
| L3 | 14/36 | 6.10× | 15.39 | −0.60 dB |

两文件均无空渲染、无空 Δ，`finetune_iters=5000` 一致。归档在 `rd/partial_remote3090/`，
仅作过程记录；**Table 4 一律用本机全量结果**。

## 5. 中断根因：远程 GPU0 物理掉卡

```
nvidia-smi: Unable to determine the device handle for GPU0: 0000:67:00.0: Unknown Error
dmesg: NVRM: Xid (PCI:0000:67:00): 79, GPU has fallen off the bus.
       NVRM: Xid (PCI:0000:67:00): 154, ... Node Reboot Required
       NVRM: Xid (PCI:0000:68:00): 154, ... Node Reboot Required   # 另一张卡也被标
torch.cuda.device_count() == 0
```

- GPU0（67:00）掉总线；内核随后把**两张卡都**标记 `Node Reboot Required`。
- 无 sudo（需密码），无法 `nvidia-smi -r` 或重载内核模块；机器 up 79 天、共享机（lab906-dualGPUSystem）。

### 重启后的二次故障：机器起来了，sshd 没起来

用户重启后机器**仍不可达**。实测判定（2026-10-16 14:30 前后）：

- `172.16.227.24` ICMP 稳定应答（0% 丢包、0.6ms、TTL 62）；同网段未使用地址 `172.16.227.99`
  完全不响应 ⇒ **是这台机在应答，不是路由器代答**。
- 探测 10 个端口（22/80/443/111/631/5900/8080/2222/9418/3389）**全部「拒绝连接」**。
  拒绝而非超时 = 网络栈活着但**用户态一个服务都没起** ⇒ 系统没走完启动（或进了降级/只读状态）。
- 最可能：GPU 掉卡属非正常关机，重启触发文件系统自检修复（数据盘 2.6T、`/home` 654G）。
- 网络侧无旁路：Tailscale 上没有这台机（只有 cb/cb-windows/lwh-windows 等，chenfan 亦离线 7 天），
  DNS 无记录，无 IPMI 信息 ⇒ **远程救不回，需有人在机房看控制台**。

## 6. 最终执行方案（本机 2060 全量）

```bash
bash scripts/gs_compress/run_learned_nied_local.sh      # L2 42 + L3 36，顺序跑，--iters 5000
# 输出：results/gs_compress/evidence/rd/learned_nied_L{2,3}.json（增量落盘）
```

- **断点续跑**：驱动见 `.tmp/learned_nied/<tag>/out_vq/point_cloud/iteration_5001/point_cloud.npz`
  即跳过压缩（只重做解码+渲染）⇒ 中断（含机器休眠）后直接重跑本脚本，不会重压已完成地图。
- **防污染**：`paper2_codec_tables.py` 有完整性门禁——行数不覆盖整个 split 时该行不入表。
- 实测吞吐 ~3 min/图（person_tracking 段）；TUM 长序列更慢，全量估计 3–4 h。
- 机器休眠无法用 `systemd-inhibit` 阻止（polkit 拒绝：`Failed to inhibit: Access denied`）；
  `logind.conf` 无 `IdleAction`（systemd 空闲挂起未配置），但 GNOME 侧仍可能触发。

远程机器恢复后：npz 已缓存 48 张，若仍需远程算力可用 `run_learned_nied_remote.sh` 续跑。

## 7. 本地侧改动清单（未 commit）

- `scripts/gs_compress/learned_nied_c3dgs_baseline.py`（路径参数化 + `--tags` 白名单）
- `scripts/gs_compress/build_nied_c3dgs_env.sh`（路径参数化 + 远程 CUDA_HOME 注记）
- `scripts/gs_compress/slam_run_to_colmap.py`（**帧集口径修复**，L3 必需）
- `scripts/gs_compress/run_learned_nied_local.sh`（**新增**，本机全量跑，最终方案）
- `scripts/gs_compress/run_learned_nied_remote.sh`（新增，远程派发；远程恢复后可用）
- `scripts/gs_compress/merge_learned_nied_partial.py`（新增，混合来源时的合并工具；本机全量方案下**不用**）
- `scripts/gs_compress/paper2_codec_tables.py`（Niedermayr 行 + **完整性门禁**）
- `results/gs_compress/evidence/rd/superseded/`（陈旧的部分 json，曾一度误入表，见下）

### 附带修掉的表污染隐患

`_learned()` 读 json 时**不检查行数**，今早本机停跑留下的 `rd/learned_nied_L2.json`（12 行）
一度被静默当成完整数据写进 `tab_rd.tex`。已加门禁并把陈旧文件移到 `rd/superseded/`。
**教训：凡"从中间产物 json 聚合进表"的路径都要有行数/覆盖门禁。**
