#!/usr/bin/env bash
# run_L1.sh — DynPort L1 正式批（远程 3090；prereg_dynport_L1.md §2/§5；账本 D2-027）。
#
# 规模 = 2 序列（crowd2 机制主场 + balloon2 对照）× {E, D, C−} × seed0 = 6 run。
# 判据先锁：prereg commit 03ffdee6f（先于任何正式批工件 mtime）。
# 冒烟已证单 run 可行（本机 2060 pilot）；批级硬顶见 prereg §5（按冒烟实测墙钟定规模）。
#
# 用法（远程）：setsid env PY=<python> bash <repo_abs>/scripts/dynport/run_L1.sh <repo_abs>
set -u
REPO="${1:-$HOME/cron/monogs-ours}"
PY="${PY:-$HOME/anaconda3/envs/monogs-ours-3090/bin/python}"
GPU="${GPU:-0}"
LOGDIR="$REPO/results/dynport/logs"; mkdir -p "$LOGDIR"; cd "$REPO" || exit 1
LOG="$LOGDIR/run_L1.log"
echo "[L1] start $(date -Is) HEAD=$(git rev-parse --short HEAD) gpu=$GPU" > "$LOG"
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader >> "$LOG" 2>&1 || true
rc_all=0
for seq in crowd2 balloon2; do
  for arm in E D Cneg; do
    echo "[L1] ${seq}/${arm} start $(date -Is)" >> "$LOG"
    CUDA_VISIBLE_DEVICES="$GPU" timeout "${PER_ARM_TIMEOUT:-3600}" \
      "$PY" slam.py --config "configs/experiments/dynport/L1_${seq}_${arm}.yaml" --seed 0 \
      > "$LOGDIR/L1_${seq}_${arm}.consolelog" 2>&1
    rc=$?; echo "[L1] ${seq}/${arm} rc=$rc end $(date -Is)" >> "$LOG"
    if [ "$rc" -ne 0 ]; then rc_all=$rc; fi
  done
done
echo "rc=$rc_all $(date -Is) HEAD=$(git rev-parse --short HEAD)" > "$LOGDIR/L1.done"
echo "[L1] done rc=$rc_all $(date -Is)" >> "$LOG"
exit "$rc_all"
