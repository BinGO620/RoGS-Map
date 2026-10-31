#!/usr/bin/env bash
# run_learned_nied_l3_cpu.sh — 重跑 L3（36 张），用 data_device='cpu' 绕开 6GB 卡的显存墙。
#
# 起因（2026-10-16 exp52）：L3 的 6 张 `f3_office_*` 在 2060（5.78 GiB）上全部
# `torch.OutOfMemoryError`。根因：其 `Scene` 构建相机时把**每张训练图**都放到 data_device 上
# （`scene/cameras.py:39` `image.to(self.data_device)`），而 f3_office 是
# `freiburg3_long_office_household`、**2515 帧**（其余 L3 序列 590–1315 帧），
# 2515 × 640×480×3×float32 ≈ 9.3 GB ⇒ 必炸。
#
# 修法：`--data-device cpu`。**语义不变**——全仓 `original_image` 只有三处消费者：
#   finetune.py:51  每步 `viewpoint_cam.original_image.cuda()`（自己搬）
#   compress.py:107 走 test 相机（cfg_args 里 eval=False ⇒ test 集为空，该路径不执行）
#   render.py       独立脚本，compress.py 不调用
#   灵敏度扫描（compress.py:61）只渲染、不读 GT 图。
# 所以只是把图像驻留位置从显存挪到内存，数学完全一致。中性性另用单图对照验证过。
#
# 复用：已有 npz 的 30 张只做解码+渲染（渲染确定 ⇒ 数字不变）；6 张 f3_office 重新压缩。
# 用法：bash scripts/gs_compress/run_learned_nied_l3_cpu.sh
set -uo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY=/data/conda_envs/nied-c3dgs/bin/python

echo "=== [L3 cpu] start $(date) ==="
"$PY" "$R/scripts/gs_compress/learned_nied_c3dgs_baseline.py" \
  --split L3 --iters 5000 --device cuda:0 --data-device cpu
rc=$?
echo "=== [L3 cpu] end rc=$rc $(date) ==="
echo "L3-CPU-DONE $(date)"
