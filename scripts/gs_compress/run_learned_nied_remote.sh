#!/usr/bin/env bash
# run_learned_nied_remote.sh — 在远程 3090（jiangwenheng）跑 Niedermayr c3dgs 基线（方案 A′ 第二基线）。
# 用法：bash scripts/gs_compress/run_learned_nied_remote.sh <L2|L3> [iters]
#   L2 与 L3 可并发（各占一张卡）：CUDA_VISIBLE_DEVICES=0 跑 L2、=1 跑 L3。
# 依赖：先 rsync 3 脚本 + submodule + 已缓存 npz；再 bash scripts/gs_compress/build_nied_c3dgs_env.sh 建 venv。
set -uo pipefail
SPLIT="${1:?usage: run_learned_nied_remote.sh <L2|L3> [iters]}"
ITERS="${2:-5000}"
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

export NIED_REPO="${NIED_REPO:-$R/submodules/compressed-3dgs-niedermayr}"
export PY_MONOGS="${PY_MONOGS:-/home/jiangwenheng/anaconda3/envs/monogs-ours-3090/bin/python}"
export PY_NIED="${PY_NIED:-$R/.venvs/nied-c3dgs/bin/python}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

echo "=== [$SPLIT] start $(date) | PY_NIED=$PY_NIED | CVD=$CUDA_VISIBLE_DEVICES | iters=$ITERS ==="
"$PY_NIED" "$R/scripts/gs_compress/learned_nied_c3dgs_baseline.py" \
  --split "$SPLIT" --iters "$ITERS" --device cuda:0
rc=$?
echo "=== [$SPLIT] end rc=$rc $(date) ==="
exit "$rc"
