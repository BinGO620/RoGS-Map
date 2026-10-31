#!/usr/bin/env bash
# run_probe_5seq.sh — B-1 反动态代价探针跨序列批（prereg_dyn_probe_5seq_2026-10-05.md）。
# 5 序列 × 2 臂（探针自身对每 map 跑 P1/P2/C-/P4/P2c）。
# 阶段：冒烟测 1 图计时 -> 按 prereg §4 时间盒定规模 -> 跑批 -> 聚合。
# 用法（远程 3090）: PY=... bash scripts/embrace_dyn/run_probe_5seq.sh [--smoke-only]
set -u
cd "$(dirname "$0")/../.."
PY=${PY:-/data/conda_envs/monogs-ours/bin/python}
LOG=results/embrace_dyn/evidence/probe_5seq_batch.log
EV=results/embrace_dyn/evidence
SMOKE_ONLY=0
[ "${1:-}" = "--smoke-only" ] && SMOKE_ONLY=1

echo "probe_5seq start $(date) PY=$PY smoke_only=$SMOKE_ONLY" | tee -a "$LOG"

# ---- 冒烟测：1 图（crowd2，含 5 臂 16 帧）计时 ----
echo "=== SMOKE: crowd2 (baseline+gate, 5 arms) ===" | tee -a "$LOG"
t0=$(date +%s)
$PY scripts/02_analysis/dyn_probe.py render --config configs/experiments/embrace_dyn/probe_5seq_crowd2.yaml \
    >> "$LOG" 2>&1
rc=$?
t1=$(date +%s)
smoke_s=$((t1 - t0))
echo "SMOKE crowd2 rc=$rc elapsed=${smoke_s}s ($((smoke_s/60))min)" | tee -a "$LOG"

# ---- 时间盒决策（prereg §4）----
# smoke 含 2 图；单图 ≈ smoke/2。全量 5 序列(10 图) 估 ≈ smoke*5；砍批 3 序列(6 图) 估 ≈ smoke*3。
per_map=$((smoke_s / 2))
est_full=$((per_map * 10))
if [ "$per_map" -le 1200 ]; then
  SEQS="crowd crowd2 crowd3 balloon2 person_tracking"   # 单图 <=20min -> 全量
  echo "DECISION: per_map=${per_map}s <=1200s -> FULL 5 sequences (10 maps), est $((est_full/60))min" | tee -a "$LOG"
else
  SEQS="crowd2 crowd3 balloon2"                          # >20min -> 砍到 3 序列
  echo "DECISION: per_map=${per_map}s >1200s -> CUT to 3 sequences (6 maps), est $((per_map*6/60))min" | tee -a "$LOG"
fi

if [ "$SMOKE_ONLY" = "1" ]; then echo "smoke-only: stop." | tee -a "$LOG"; exit 0; fi

# ---- 批 ----
for seq in $SEQS; do
  out="$EV/dyn_probe_5seq_${seq}_results.json"
  if [ -f "$out" ]; then echo "DONE $seq (cached)" | tee -a "$LOG"; continue; fi
  echo "RUN  $seq $(date)" | tee -a "$LOG"
  $PY scripts/02_analysis/dyn_probe.py render --config "configs/experiments/embrace_dyn/probe_5seq_${seq}.yaml" \
      >> "$LOG" 2>&1
  echo "  $seq rc=$?" | tee -a "$LOG"
done
echo "probe_5seq all done $(date)" | tee -a "$LOG"
