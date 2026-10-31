#!/usr/bin/env bash
# run_judge_L1.sh — 在远程（同机同码）跑 DynPort L1 判据机（双仪器）+ 汇总。
#
# 用法（远程）：setsid env PY=<python> bash <repo>/scripts/dynport/run_judge_L1.sh <repo> <tag> [before] [after]
#   tag    = v1 / v2（区分批；写入 evidence 的 json 名）
#   before = 只取 mtime ≤ 该时刻的 run（"YYYY-MM-DD HH:MM"；v1/v2 两批并存时区分）
#   after  = 只取 mtime ≥ 该时刻的 run
# 依赖：collect_L1.py（跑 judge 双仪器 + 锁定出口 + manifest）。**须在 GPU 空闲时跑**。
set -u
REPO="${1:-$HOME/cron/monogs-ours}"
TAG="${2:-v1}"
BEFORE="${3:-}"
AFTER="${4:-}"
PY="${PY:-$HOME/anaconda3/envs/monogs-ours-3090/bin/python}"
cd "$REPO" || exit 1
LOGDIR="$REPO/results/dynport/logs"; mkdir -p "$LOGDIR"
LOG="$LOGDIR/judge_${TAG}.log"
echo "[judge] start $(date -Is) HEAD=$(git rev-parse --short HEAD) tag=$TAG before='$BEFORE' after='$AFTER'" > "$LOG"
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader >> "$LOG" 2>&1 || true
ARGS=(--root results/dynport/L1 --out-dir results/dynport/evidence --seq crowd2 balloon2 --tag "$TAG")
[ -n "$BEFORE" ] && ARGS+=(--before "$BEFORE")
[ -n "$AFTER" ] && ARGS+=(--after "$AFTER")
CUDA_VISIBLE_DEVICES=0 "$PY" scripts/dynport/collect_L1.py "${ARGS[@]}" >> "$LOG" 2>&1
rc=$?
echo "[judge] rc=$rc end $(date -Is)" >> "$LOG"
echo "rc=$rc $(date -Is) HEAD=$(git rev-parse --short HEAD)" > "$LOGDIR/judge_${TAG}.done"
exit "$rc"
