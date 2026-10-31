#!/usr/bin/env bash
# l3_batch.sh — L3 泛化批：R34 留出面板（6 序列 × 3 seed × {rb,gate} = 36 图）R-D 扫描。
# 用法：bash scripts/gs_compress/l3_batch.sh [device] [frames_csv]
# 零 SLAM 重跑；只读存量最终地图。
set -u
cd "$(dirname "$0")/../.."
PY=${PY:-/data/conda_envs/monogs-ours/bin/python}
DEV=${1:-cuda:0}
FRAMES=${2:-"0,60,120,180,240"}
UNIFORM="16,8,8,8,8;12,7,7,7,7;10,6,6,6,6;8,4,4,4,4"

SEQ=(f1_desk2 f1_room f3_office f3_st_rpy f3_wk_rpy moving_obstructing_box)
ARM=(rb gate)
SEEDS=(0 1 2)

mkdir -p results/gs_compress/l3_logs
for seq in "${SEQ[@]}"; do
  for arm in "${ARM[@]}"; do
    for seed in "${SEEDS[@]}"; do
      tag="L3_${seq}_${arm}_s${seed}"
      rd=$(ls -d results/paper2_rollout/r34_${arm}_${seq}_seed${seed}/datasets_*/*/seed_${seed}/*/ 2>/dev/null | head -1)
      if [ -z "$rd" ]; then echo "SKIP $tag (no run)"; continue; fi
      if [ -f "results/gs_compress/evidence/rd/${tag}_rd_table.json" ]; then
        echo "DONE $tag (cached)"; continue
      fi
      echo "RUN  $tag -> $rd"
      $PY scripts/gs_compress/rd_sweep.py --run-dir "$rd" --tag "$tag" \
          --frames "$FRAMES" --device "$DEV" --uniform "$UNIFORM" --no-static \
          > "results/gs_compress/l3_logs/${tag}.log" 2>&1
      echo "  rc=$?"
    done
  done
done
echo "L3 batch done."
