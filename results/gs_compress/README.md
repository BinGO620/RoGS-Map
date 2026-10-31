# results/gs_compress — 动态场景 GS-SLAM 地图压缩（CVM 冲刺新 A 线，D2-025）

> **账本**：立项 = D2-025；判据 = `evidence/prereg_gs_compress.md`；L1 判读 = `evidence/l1_readout_2026-10-04.md`。
> **性质**：离线后处理线（不碰 SLAM 主代码、不重跑 SLAM、不进在线预算）。

## 目录

| 路径 | 内容 | 入库 |
|---|---|---|
| `evidence/prereg_gs_compress.md` | 预注册（判据先锁） | ✅ |
| `evidence/l1_readout_2026-10-04.md` | L1 判读（C1/C2 过；C3 权衡非帕累托 ⇒ claim 收窄） | ✅ |
| `evidence/rd/*.json` | 逐码率点 R-D 记录（rate=压缩码流、渲染指标、分区） | ✅ 判据键 |
| `recon/` | 压缩重建 PLY（渲染输入形态，可再生产物） | ❌ gitignore |
| `render/` | render_compare 输出（PNG + render_metrics.json） | ❌ 大件 gitignore |

## 复算

```bash
PY=/data/conda_envs/monogs-ours/bin/python
# 单点：源 run -> codec -> 重建 PLY -> render_compare 渲染 + 分区指标
$PY scripts/gs_compress/rd_harness.py --run-dir <run-ts-dir> --tag <tag> \
    --bits 16,8,8,8,8 --frames 0,60,120,180,240 --device cuda:0
# 扫描（baseline + 多码率点 + 分区臂）
$PY scripts/gs_compress/rd_sweep.py --run-dir <run-ts-dir> --tag <tag> \
    --frames 0,60,120,180,240 --uniform "16,8,8,8,8;10,6,6,6,6;8,4,4,4,4"
# 单测
$PY -m pytest tests/gs_compress/ -q
```

## 口径（禁混引，prereg §4.0）
- rate = **压缩码流字节/基元**（非解码 PLY）；对照一律**同码率 ±2%**。
- 渲染读数 = **同地图重载渲染**（`render_compare.py` 固定帧集）；**禁**与 R33 表 / run 时 eval / 跨批数字混引。
- 掩码 = canonical 冻结 `dynamic_mask/`（评测仪器，不作贡献主张）；分区标签已过 **GT 深度可见性门控**。
