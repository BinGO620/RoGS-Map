#!/bin/bash
# run_effctl.sh — 效率表"无竞争"重测（串行、单卡、每臂单进程）。
# 见 prereg_efficiency_ctl_2026-10-05.md。TAG_PREFIX=effctl 保证不覆盖 R33 原目录。
# 用法（远程）: bash scripts/paper2_fulltable/run_effctl.sh
set -u
REPO=/home/jiangwenheng/cron/monogs-ours
PY=/home/jiangwenheng/anaconda3/envs/monogs-ours-3090/bin/python
cd "$REPO"
OUT=results/paper2_fulltable
DONE="$OUT/effctl.done"
GPU=${GPU:-0}
mkdir -p "$OUT"

# 子集：3 序列 × 4 臂 × 1 seed（prereg §1）
SEQ=(balloon crowd2 person_tracking)
ARMS=(baseline swbaonly final gate)

echo "effctl start $(date) GPU=$GPU" >> "$DONE"
for seq in "${SEQ[@]}"; do
  for arm in "${ARMS[@]}"; do
    cfg="r33_rebase_${arm}_${seq}"
    tag="effctl_${arm}_${seq}_seed0"
    root="$OUT/$tag"
    if [ -f "$root/tables/tracking_raw.csv" ]; then echo "$tag SKIP" >> "$DONE"; continue; fi
    mkdir -p "$root"
    echo "$tag start $(date)" >> "$DONE"
    env PYTHONPATH="$REPO" MPLBACKEND=Agg CUDA_VISIBLE_DEVICES="$GPU" \
      "$PY" slam.py --config "configs/experiments/paper2_fulltable/${cfg}.yaml" \
      --seed 0 --eval --results-root "$root" > "$OUT/${tag}.consolelog" 2>&1
    echo "$tag finished rc=$? $(date)" >> "$DONE"
  done
done
echo "effctl all done $(date)" >> "$DONE"
