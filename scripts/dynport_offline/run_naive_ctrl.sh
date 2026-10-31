#!/usr/bin/env bash
# run_naive_ctrl.sh — NaiveCtrl 朴素插入对照批（3 序列 seed0；远程 3090 单卡串行）。
# prereg = results/dynport_offline/evidence/prereg_naive_ctrl_2026-10-13.md
# 臂：Naive = 完整算子管线但跳过生命周期决策核 + S5（单变量 = 生命周期+S5）。
# R1 复用 L1_v4 存量（不重跑）；判读器 judge_naive_ctrl.py 从 samepose 判据 JSON 汇总。
#
# 用法：bash scripts/dynport_offline/run_naive_ctrl.sh <repo_root>
set -euo pipefail
REPO="${1:?repo root}"
PY="${PY:-python}"
cd "$REPO"

BASE_ROOT="results/paper2_fulltable"
OUT_ROOT="results/dynport_offline/NaiveCtrl"
SEQS=(crowd2 balloon2 person_tracking2)

mkdir -p "$OUT_ROOT"

for seq in "${SEQS[@]}"; do
  base=$(ls -d "${BASE_ROOT}/r33_rebase_baseline_${seq}_seed0"/datasets_bonn/*/seed_0/*/ | head -1)
  out="${OUT_ROOT}/${seq}_Naive"
  if [ -f "$out/repair_timing.json" ]; then
    echo "SKIP ${seq} (exists)"; continue
  fi
  echo "--- RUN ${seq} naive -> $out"
  "$PY" scripts/dynport_offline/repair_map.py \
    --base-run "$base" --out "$out" --arm Naive --enable \
    --lam-d 0.20 --cap 50000 --lmax 45 --unproj-stride 3 --fit-iters 300 \
    --lineage-base 402653184 --naive
done

echo "=== judge (samepose, R1 存量复用) ==="
"$PY" scripts/dynport_offline/judge_naive_ctrl.py \
  --root "$OUT_ROOT" --base-root "$BASE_ROOT" \
  --r1-root results/dynport_offline/L1_v4 \
  --out-dir results/dynport_offline/evidence_naivectrl \
  --seq crowd2 balloon2 person_tracking2
echo "NaiveCtrl DONE"
