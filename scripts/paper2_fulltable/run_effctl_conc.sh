#!/bin/bash
# run_effctl_conc.sh — 效率「并发」对照（**与 effctl 同码**）：同一当前代码、同一 3 序列子集，
# 但用 2 进程/卡并发跑（复刻 R33 并发条件）。用于把「并发 vs 独占」做成单变量对照。
# 背景：effctl（独占）与 R33（并发）跑在不同代码版本 ⇒ 不能直接比（G2 致命）。
# 用法（远程，单卡双进程）: bash scripts/paper2_fulltable/run_effctl_conc.sh
set -u
REPO=/home/jiangwenheng/cron/monogs-ours
PY=/home/jiangwenheng/anaconda3/envs/monogs-ours-3090/bin/python
cd "$REPO"
OUT=results/paper2_fulltable
DONE="$OUT/effctlconc.done"
mkdir -p "$OUT"

GPU=${GPU:-0}
SEQ=(balloon crowd2 person_tracking)
ARMS=(baseline swbaonly final gate)

JOBS=()
for seq in "${SEQ[@]}"; do for arm in "${ARMS[@]}"; do JOBS+=("${arm}:${seq}"); done; done

run_one() {
  local job="$1"; local arm="${job%%:*}"; local seq="${job##*:}"
  local cfg="r33_rebase_${arm}_${seq}"
  local tag="effctlconc_${arm}_${seq}_seed0"
  local root="$OUT/$tag"
  if [ -f "$root/tables/tracking_raw.csv" ]; then echo "$tag SKIP" >> "$DONE"; return 0; fi
  mkdir -p "$root"
  echo "$tag start $(date)" >> "$DONE"
  env PYTHONPATH="$REPO" MPLBACKEND=Agg CUDA_VISIBLE_DEVICES="$GPU" \
    "$PY" slam.py --config "configs/experiments/paper2_fulltable/${cfg}.yaml" \
    --seed 0 --eval --results-root "$root" > "$OUT/${tag}.consolelog" 2>&1
  echo "$tag finished rc=$? $(date)" >> "$DONE"
}

echo "effctlconc start $(date) GPU=$GPU (2 procs/card)" >> "$DONE"
# 2 进程/卡：按奇偶分两路并行（每路内串行）
half=$(( (${#JOBS[@]} + 1) / 2 ))
( for i in $(seq 0 $((half-1))); do [ $i -lt ${#JOBS[@]} ] && run_one "${JOBS[$i]}"; done ) &
p1=$!
( for i in $(seq $half $((${#JOBS[@]}-1))); do [ $i -lt ${#JOBS[@]} ] && run_one "${JOBS[$i]}"; done ) &
p2=$!
wait "$p1"; wait "$p2"
echo "effctlconc all done $(date)" >> "$DONE"
