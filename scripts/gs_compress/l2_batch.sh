#!/usr/bin/env bash
# l2_batch.sh — L2 主表批：baseline+final 两臂 × Bonn 7 序列 × 3 seed = 42 图 R-D 扫描。
# 用法：bash scripts/gs_compress/l2_batch.sh [device] [frames_csv]
# 零 SLAM 重跑；只读存量最终地图 -> codec -> 重建 PLY -> render_compare。
set -u
cd "$(dirname "$0")/../.."
PY=${PY:-/data/conda_envs/monogs-ours/bin/python}
DEV=${1:-cuda:0}
FRAMES=${2:-"0,60,120,180,240"}   # 固定帧集（所有点共用；短序列用 --frames 自动裁）
UNIFORM="16,8,8,8,8;12,7,7,7,7;10,6,6,6,6;8,4,4,4,4;6,3,3,3,3"

SEQ=(balloon balloon2 crowd crowd2 crowd3 person_tracking person_tracking2)
ARM=(baseline final)
SEEDS=(0 1 2)

mkdir -p results/gs_compress/l2_logs
for seq in "${SEQ[@]}"; do
  for arm in "${ARM[@]}"; do
    for seed in "${SEEDS[@]}"; do
      tag="L2_${seq}_${arm}_s${seed}"
      rd=$(ls -d results/paper2_fulltable/${seq}_${arm}_seed${seed}/datasets_bonn/*/seed_${seed}/*/ 2>/dev/null | head -1)
      if [ -z "$rd" ]; then echo "SKIP $tag (no run)"; continue; fi
      log="results/gs_compress/l2_logs/${tag}.log"
      if [ -f "results/gs_compress/evidence/rd/${tag}_rd_table.json" ]; then
        echo "DONE $tag (cached)"; continue
      fi
      echo "RUN  $tag -> $rd"
      $PY scripts/gs_compress/rd_sweep.py --run-dir "$rd" --tag "$tag" \
          --frames "$FRAMES" --device "$DEV" --uniform "$UNIFORM" \
          > "$log" 2>&1
      echo "  rc=$? $(grep -c '^\[rd_sweep\] OK\|OK ' "$log" 2>/dev/null || echo 0) points"
    done
  done
done
echo "L2 batch done."
