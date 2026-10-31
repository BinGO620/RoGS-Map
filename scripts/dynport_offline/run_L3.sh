#!/usr/bin/env bash
# run_L3.sh — DynPort-Offline L3 正式批（7 序列 × 3 seed 网格补全）。
#
# §6 先锁：L3 = 全 7 序列 × 3 seed（+ codec 联动 —— 见 results/dynport_offline/L3/report_L3_scope_2026-10-08.md，
#   "codec 联动" 在 prereg 中为**未定义占位**，本批只跑已锁的网格部分；缺口另报）。
#
# 复用纪律（handoff 2026-10-08「不要重跑 L1/L2」）：
#   L1_v4 / L2 已在盘的 12 个 R1（+6 个 C−）**不重跑**；本批只补网格缺口。
#   判据机（judge）在 collect 时**统一重跑**（读存量 PLY）⇒ 跨批混跑无口径问题；
#   算子 repair_map.py 在 L1_v4 / L2 / L3 三批 HEAD 间**逐位一致**（manifest provenance 机检）。
#
# 命名（对齐既有批次，使 collect 单 root 逻辑即可跨根解析）：
#   seed0  → <seq>_R1 / <seq>_Cneg        （与 L1_v4 / L2 seed0 同）
#   seed1+ → <seq>_seed<N>_R1             （与 L2 跨 seed 同）
#   OFF    → crowd2_OFF                   （批次级接线守门，G4-C8）
#
# 用法：bash scripts/dynport_offline/run_L3.sh <repo_root>
# 计时批单卡串行（禁并发）。
set -euo pipefail
REPO="${1:?repo root}"
PY="${PY:-python}"
cd "$REPO"

BASE_ROOT="results/paper2_fulltable"
OUT_ROOT="results/dynport_offline/L3"
REUSE_ROOTS=(results/dynport_offline/L1_v4 results/dynport_offline/L2)
SEQ=(balloon balloon2 crowd crowd2 crowd3 person_tracking person_tracking2)
SEEDS=(0 1 2)

mkdir -p "$OUT_ROOT"

# 已有 R1 的复用位置（seed0 命名 <seq>_R1；跨 seed 命名 <seq>_seed<N>_R1）
# 注：函数末尾必然 return 0（缺省无匹配时 echo 空），避免 set -e 下命令替换令脚本静默中止。
find_existing() {  # <label> <arm>  -> path or empty
  local label="$1" arm="$2" r p
  for r in "${REUSE_ROOTS[@]}" "$OUT_ROOT"; do
    p="$r/${label}_${arm}"
    if [ -f "$p/repair_timing.json" ]; then echo "$p"; return 0; fi
  done
  return 0
}

run_one() {  # <seq> <seed> <label> <arm> <shift_m>
  local seq="$1" sd="$2" label="$3" arm="$4" shift_m="$5"
  local base
  base=$(ls -d "${BASE_ROOT}/r33_rebase_baseline_${seq}_seed${sd}"/datasets_bonn/*/seed_${sd}/*/ 2>/dev/null | head -1 || true)
  [ -n "$base" ] || { echo "SKIP ${label}_${arm} (no base run)"; return 0; }
  local out="${OUT_ROOT}/${label}_${arm}"
  echo "--- RUN ${label}/${arm} shift=${shift_m} -> $out"
  "$PY" scripts/dynport_offline/repair_map.py \
    --base-run "$base" --out "$out" --arm "$arm" --enable \
    --lam-d 0.20 --cap 50000 --lmax 45 --unproj-stride 3 --fit-iters 300 \
    --lineage-base 402653184 --control-shift-m "$shift_m"
}

echo "=== L3 R1 grid（reuse-aware，21 格）==="
for seq in "${SEQ[@]}"; do
  for sd in "${SEEDS[@]}"; do
    if [ "$sd" = "0" ]; then label="$seq"; else label="${seq}_seed${sd}"; fi
    ex=$(find_existing "$label" R1)
    if [ -n "$ex" ]; then echo "REUSE ${label}_R1 <- $ex"; continue; fi
    run_one "$seq" "$sd" "$label" R1 0.0
  done
done

echo "=== L3 C−（seed0，J7 阴性对照锚；补齐 7 序列）==="
for seq in "${SEQ[@]}"; do
  ex=$(find_existing "$seq" Cneg)
  if [ -n "$ex" ]; then echo "REUSE ${seq}_Cneg <- $ex"; continue; fi
  run_one "$seq" 0 "$seq" Cneg 0.30
done

echo "=== L3 批次级 OFF（crowd2；J9 接线守门，G4-C8）==="
base=$(ls -d "${BASE_ROOT}/r33_rebase_baseline_crowd2_seed0"/datasets_bonn/*/seed_0/*/ 2>/dev/null | head -1 || true)
"$PY" scripts/dynport_offline/repair_map.py --base-run "$base" \
  --out "${OUT_ROOT}/crowd2_OFF" --arm R1 --lineage-base 402653184

echo "=== L3 collect（跨根：L3 优先 + L1_v4 + L2 复用）==="
"$PY" scripts/dynport_offline/collect_L1.py \
  --root results/dynport_offline/L3 results/dynport_offline/L1_v4 results/dynport_offline/L2 \
  --base-root "$BASE_ROOT" \
  --out-dir results/dynport_offline/evidence_L3 --tag L3 \
  --seq balloon balloon_seed1 balloon_seed2 \
        balloon2 balloon2_seed1 balloon2_seed2 \
        crowd crowd_seed1 crowd_seed2 \
        crowd2 crowd2_seed1 crowd2_seed2 \
        crowd3 crowd3_seed1 crowd3_seed2 \
        person_tracking person_tracking_seed1 person_tracking_seed2 \
        person_tracking2 person_tracking2_seed1 person_tracking2_seed2
echo "L3 DONE"
