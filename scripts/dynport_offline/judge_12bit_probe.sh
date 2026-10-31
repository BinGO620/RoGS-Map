#!/bin/bash
# judge_12bit_probe.sh — 4D 层序列 codec 12bit 工作点判据机（2026-10-13）
# 判据：J1 ≥ +2.5 dB ∧ J2 ≤ 0.70 ∧ J3 ∈ ±0.25（与 L1/L2/L3 同判据机同口径，samepose）
# 用法：bash scripts/dynport_offline/judge_12bit_probe.sh
set -u
PY=/data/conda_envs/monogs-ours/bin/python
REPO=/data/monogs-ours
EVID=/data/monogs-ours/results/dynport_offline/evidence_4d12bit

declare -A BASE=(
  [crowd2]=results/paper2_fulltable/r33_rebase_baseline_crowd2_seed0/datasets_bonn/r33_rebase_baseline_crowd2/seed_0/2026-09-16-06-54-45
  [crowd]=results/paper2_fulltable/r33_rebase_baseline_crowd_seed0/datasets_bonn/r33_rebase_baseline_crowd/seed_0/2026-09-16-04-45-31
  [balloon2]=results/paper2_fulltable/r33_rebase_baseline_balloon2_seed0/datasets_bonn/r33_rebase_baseline_balloon2/seed_0/2026-09-16-03-15-56
  [person_tracking]=results/paper2_fulltable/r33_rebase_baseline_person_tracking_seed0/datasets_bonn/r33_rebase_baseline_person_tracking/seed_0/2026-09-16-11-20-48
)

for seq in crowd2 crowd balloon2 person_tracking; do
  FRAMES=$($PY -c "
import re
c=open('$REPO/${BASE[$seq]}/console.log').read()
ids=sorted(set(int(m) for m in re.findall(r'Evaluating ATE at frame:\s*(\d+)', c)))
print(','.join(map(str,ids)))")
  echo "=== $seq 12bit judge (frames=$FRAMES) ==="
  $PY "$REPO/scripts/dynport/judge_dynport.py" \
      --arms "E=$REPO/${BASE[$seq]}" "D=$EVID/${seq}_R1" \
      --seq $seq --frames $FRAMES --device cuda:0 --samepose \
      --out "$EVID/${seq}_R1_12bit_samepose.json" 2>&1 | tail -1
done
echo "ALL 12bit judge done → $EVID"
