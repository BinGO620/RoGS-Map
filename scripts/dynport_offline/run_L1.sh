#!/usr/bin/env bash
# run_L1.sh — DynPort-Offline L1 批驱动（远程 3090；3 序列 × {R1, C−}）。
# 判据本体 = results/dynport_offline/evidence/prereg_dynport_offline_L1.md
# 底图 = R33 rebase baseline seed0（论文 Tab.1 首列之栈的单 seed run）。
#
# 用法：bash scripts/dynport_offline/run_L1.sh <repo_root> [tag]
# 计时批单卡串行（禁并发）。
set -euo pipefail
REPO="${1:?repo root}"
TAG="${2:-}"
PY="${PY:-python}"
cd "$REPO"

BASE_ROOT="results/paper2_fulltable"
OUT_ROOT="results/dynport_offline/L1"
SEQS=(crowd2 balloon2 person_tracking2)

for seq in "${SEQS[@]}"; do
  base=$(ls -d "${BASE_ROOT}/r33_rebase_baseline_${seq}_seed0"/datasets_bonn/*/seed_0/*/ | head -1)
  echo "=== ${seq} base=${base}"
  for arm in R1 Cneg; do
    shift_m=0.0
    [ "$arm" = "Cneg" ] && shift_m=0.30
    out="${OUT_ROOT}/${seq}_${arm}"
    echo "--- ${seq}/${arm} (control_shift_m=${shift_m})"
    "$PY" scripts/dynport_offline/repair_map.py \
      --base-run "$base" --out "$out" --arm "$arm" --enable \
      --lam-d 0.20 --cap 50000 --lmax 45 --unproj-stride 3 --fit-iters 300 \
      --lineage-base 402653184 --control-shift-m "$shift_m"
  done
done

echo "=== collect"
"$PY" scripts/dynport_offline/collect_L1.py \
  --root "$OUT_ROOT" --base-root "$BASE_ROOT" \
  --out-dir results/dynport_offline/evidence ${TAG:+--tag "$TAG"}
echo "DONE"
