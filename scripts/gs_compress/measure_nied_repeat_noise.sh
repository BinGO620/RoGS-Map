#!/usr/bin/env bash
# measure_nied_repeat_noise.sh — 量 Niedermayr QAT 基线的**跑间噪声地板**（2026-10-16，exp52）。
#
# 起因：该 submodule **没有任何随机种子**（finetune.py 用 `randint` 采样相机、Scene 用
# `random.shuffle`，无 --seed / manual_seed / random.seed）。所以"远程 vs 本机"的差异里，
# 机器效应与跑间随机性**混在一起**，无法归因。
#
# 做法：挑若干张**同时有远程行与本机行**的地图，在本机再压一遍（第三份样本），得到：
#   远程 ↔ 本机A   = 跨机 + 跑间（混杂）
#   本机A ↔ 本机B  = 纯跑间（同机、同代码、同迭代数）
# 两者量级一对比，就能判断"机器效应"是否真实存在。
#
# 注意：会把原 npz 移到 <npz>.orig 备份（保证 .tmp 与 rd json 仍可追溯），跑完不自动恢复。
# 用法：bash scripts/gs_compress/measure_nied_repeat_noise.sh
set -uo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY=/data/conda_envs/nied-c3dgs/bin/python
OUT="$R/.tmp/nied_repeat"
TAGS="L2_crowd_baseline_s0,L2_crowd2_baseline_s0,L2_crowd3_baseline_s0"

mkdir -p "$OUT"
for t in ${TAGS//,/ }; do
  NPZ="$R/.tmp/learned_nied/$t/out_vq/point_cloud/iteration_5001/point_cloud.npz"
  if [ -f "$NPZ" ]; then mv "$NPZ" "$NPZ.orig" && echo "[repeat] 备份 $t 的 npz"; fi
done

echo "=== repeat run start $(date) tags=$TAGS ==="
"$PY" "$R/scripts/gs_compress/learned_nied_c3dgs_baseline.py" \
  --split L2 --tags "$TAGS" --iters 5000 --device cuda:0 \
  --out-json "$OUT/learned_nied_L2_repeat.json"
echo "=== repeat run end rc=$? $(date) ==="
echo "REPEAT-DONE $(date)"
