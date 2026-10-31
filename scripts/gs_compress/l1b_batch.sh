#!/usr/bin/env bash
# l1b_batch.sh — S3 乙线 L1 批：重尾感知范围量化的同码率对照（D2-025 §10.4）。
# 三图 × 三位宽点 × {v1 uniform-range, v2 robust+escape, v2 robust+clip}。
# 零 SLAM 重跑；GPU 仅用于 render_compare 离线渲染。
# 用法：bash scripts/gs_compress/l1b_batch.sh [device] [frames_csv]
set -u
cd "$(dirname "$0")/../.."
# 自动探测解释器（本地 2060 / 远程 3090 的 env 路径不同）
if [ -z "${PY:-}" ]; then
  for c in /data/conda_envs/monogs-ours/bin/python \
           /home/jiangwenheng/anaconda3/envs/monogs-ours-3090/bin/python; do
    [ -x "$c" ] && PY="$c" && break
  done
fi
PY=${PY:-python3}
DEV=${1:-cuda:0}
FRAMES=${2:-"0,60,120,180,240"}
BITSPTS="16,8,8,8,8;10,6,6,6,6;8,4,4,4,4"
Q=0.1

# (seq, arm) 三图（§10.4 先锁）
declare -a TARGETS=(
  "balloon:baseline"
  "crowd2:baseline"
  "person_tracking2:final"
)

mkdir -p results/gs_compress/l1b_logs
for t in "${TARGETS[@]}"; do
  seq="${t%%:*}"; arm="${t##*:}"
  rd=$(ls -d results/paper2_fulltable/${seq}_${arm}_seed0/datasets_bonn/*/seed_0/*/ 2>/dev/null | head -1)
  if [ -z "$rd" ]; then echo "SKIP ${seq}_${arm} (no run)"; continue; fi
  tag="L1B_${seq}_${arm}"
  # v1 + robust（escape/clip）三臂
  $PY scripts/gs_compress/rd_sweep.py --run-dir "$rd" --tag "$tag" \
      --frames "$FRAMES" --device "$DEV" \
      --uniform "$BITSPTS" --robust-q "$Q" --robust-bits "$BITSPTS" \
      > "results/gs_compress/l1b_logs/${tag}.log" 2>&1
  echo "  rc=$? $tag"
done
echo "L1B batch done."
