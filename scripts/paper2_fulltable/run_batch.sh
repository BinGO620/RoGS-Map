#!/bin/bash
# run_repair_par.sh — repair ladder batches, 4 fixed workers (2 per GPU).
# 2026-09-06 GPU policy: two concurrent slam.py per 3090 (fixed worker pool,
# no dynamic card selection — exp51 lesson).
#
# Usage:
#   REPAIR_CFGS="r19_verif2_pt1 r19_verif2_pt2" DONE_FILE=r19.done \
#     bash scripts/paper2_fulltable/run_batch.sh
#
# Jobs = each config x seeds 0-2 (completed runs skipped via
# tables/tracking_raw.csv existence). Log lines are APPEND-ONLY and keep the
# historic "<tag> GPU=<gpu> start|finished rc=<rc>" format so watchers and
# verdict tooling stay compatible.
set -u
REPO=/home/jiangwenheng/cron/monogs-ours
PY=/home/jiangwenheng/anaconda3/envs/monogs-ours-3090/bin/python
cd "$REPO"
OUT=results/paper2_fulltable
DONE="$OUT/${DONE_FILE:-batch.done}"
mkdir -p "$OUT"
CFGS=${REPAIR_CFGS:-}
if [ -z "$CFGS" ]; then echo "REPAIR_CFGS is empty, nothing to do" >&2; exit 1; fi

run_one() {
  local gpu="$1" cfg="$2" seed="$3"
  # TAG_PREFIX disambiguates re-runs of an existing config (e.g. concurrency
  # controls) from the original serial-era result dirs
  local tag="${TAG_PREFIX:+${TAG_PREFIX}_}${cfg}_seed${seed}"
  local root="$OUT/$tag"
  if [ -f "$root/tables/tracking_raw.csv" ]; then echo "$tag SKIP" >> "$DONE"; return 0; fi
  echo "$tag GPU=$gpu start $(date)" >> "$DONE"
  mkdir -p "$root"
  env PYTHONPATH="$REPO" MPLBACKEND=Agg CUDA_VISIBLE_DEVICES="$gpu" \
    "$PY" slam.py --config configs/experiments/${CFG_SUBDIR:-paper2_fulltable}/${cfg}.yaml \
    --seed "$seed" --eval --results-root "$root" > "$OUT/${tag}.consolelog" 2>&1
  local rc=$?
  echo "$tag GPU=$gpu finished rc=$rc $(date)" >> "$DONE"
  return 0
}

LIST=${RUN_LIST:-/tmp/repair_par_jobs.txt}  # / may be full on shared boxes — override to a /home path
: > "$LIST"
SEED_LIST=${SEEDS:-"0 1 2"}
for cfg in $CFGS; do
  for seed in $SEED_LIST; do
    tag="${TAG_PREFIX:+${TAG_PREFIX}_}${cfg}_seed${seed}"
    if [ ! -f "$OUT/$tag/tables/tracking_raw.csv" ]; then
      echo "$cfg $seed" >> "$LIST"
    fi
  done
done
echo "par-runner $(date): $(wc -l < "$LIST") jobs queued ($CFGS)" >> "$DONE"

worker() {
  local wid="$1" gpu="$2"
  while read -r cfg seed; do
    run_one "$gpu" "$cfg" "$seed"
  done < <(awk -v w="$wid" 'NR%4==w' "$LIST")
  return 0
}

worker 0 0 & w0=$!
worker 1 0 & w1=$!
worker 2 1 & w2=$!
worker 3 1 & w3=$!
wait "$w0"; r0=$?
wait "$w1"; r1=$?
wait "$w2"; r2=$?
wait "$w3"; r3=$?
echo "batch all done $(date) (rc w0=$r0 w1=$r1 w2=$r2 w3=$r3)" >> "$DONE"
