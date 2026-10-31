#!/usr/bin/env bash
# collect_effctlconc.sh — 拉回同码并发对照的读数（12 run 的 efficiency_raw.csv）。
# 与 effctl（独占，同码）配对 → 干净的单变量并发消融。
# 用法（本地）: bash scripts/paper2_fulltable/collect_effctlconc.sh
set -eu
REMOTE=${REMOTE:-jiangwenheng@172.16.227.24}
REPO_REMOTE=/home/jiangwenheng/cron/monogs-ours
cd "$(dirname "$0")/../.."
OUT=results/paper2_fulltable
mkdir -p "$OUT"

for arm in baseline swbaonly final gate; do
  for seq in balloon crowd2 person_tracking; do
    tag="effctlconc_${arm}_${seq}_seed0"
    mkdir -p "$OUT/$tag/tables"
    rsync -avz --partial \
      "$REMOTE:$REPO_REMOTE/$OUT/$tag/tables/efficiency_raw.csv" \
      "$OUT/$tag/tables/efficiency_raw.csv" 2>/dev/null || echo "  MISSING $tag"
  done
done
rsync -avz --partial "$REMOTE:$REPO_REMOTE/$OUT/effctlconc.done" "$OUT/effctlconc.done" 2>/dev/null || true
echo "pulled; running ablation readout"
/data/conda_envs/monogs-ours/bin/python scripts/paper2_fulltable/effctlconc_ablation.py
