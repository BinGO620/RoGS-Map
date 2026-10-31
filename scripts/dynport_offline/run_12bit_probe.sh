#!/bin/bash
# run_12bit_probe.sh — 4D 层序列 codec 12bit 工作点批量编码（2026-10-13）
# 用途：把 4 序列 R1 层序列用 12,12,12,12,12 位宽编码（排除抑制 + rot3 + xyz 预测全开），
#       输出解码快照目录供判据机 samepose 验证。零 GPU（CPU 离线）。
# 用法：bash scripts/dynport_offline/run_12bit_probe.sh
set -u
PY=/data/conda_envs/monogs-ours/bin/python
REPO=/data/monogs-ours
OUT=/data/monogs-ours/results/dynport_offline/evidence_4d12bit
mkdir -p "$OUT"

declare -A ROOTS=(
  [crowd2_R1]="$REPO/results/dynport_offline/L1_v4/crowd2_R1"
  [crowd_R1]="$REPO/results/dynport_offline/L2/crowd_R1"
  [balloon2_R1]="$REPO/results/dynport_offline/L1_v4/balloon2_R1"
  [person_tracking_R1]="$REPO/results/dynport_offline/L2/person_tracking_R1"
)

for seq in crowd2_R1 crowd_R1 balloon2_R1 person_tracking_R1; do
  echo "=== $seq 12bit encode ==="
  "$PY" "$REPO/scripts/dynport_offline/probe_4d_codec.py" \
      --snap-root "${ROOTS[$seq]}" \
      --out "$OUT/$seq" \
      --bits-cfg 12,12,12,12,12 \
      --rot3 --pred 2>&1 | tail -3
done
echo "ALL 12bit encode done → $OUT"
