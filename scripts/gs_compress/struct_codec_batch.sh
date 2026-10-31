#!/usr/bin/env bash
# struct_codec_batch.sh — 「均匀量化 + 体素合并(2cm)」codec 主表批（prereg_struct_codec_2026-10-05.md）。
# 42 图（baseline+final × Bonn 7 × 3 seed）× 3 工作点（near/mid/aggressive）。
# 用法（远程 3090）: bash scripts/gs_compress/struct_codec_batch.sh [device]
# 零 SLAM 重跑；只读存量最终地图。判据键：results/gs_compress/evidence/rd/L2S_*_rd_table.json
set -u
cd "$(dirname "$0")/../.."
PY=${PY:-/data/conda_envs/monogs-ours/bin/python}
DEV=${1:-cuda:0}
FRAMES=${FRAMES:-"0,60,120,180,240"}
UNIFORM="16,8,8,8,8;10,6,6,6,6;8,4,4,4,4"   # near/mid/aggressive（主表三点）
DEDUP=0.02                                    # 2cm 体素合并（L1 §6.1(a) 实测 −18~20% 字节）
RD=results/gs_compress/evidence/rd
SEQ=(balloon balloon2 crowd crowd2 crowd3 person_tracking person_tracking2)
ARM=(baseline final)
SEEDS=(0 1 2)

mkdir -p results/gs_compress/l2s_logs
for seq in "${SEQ[@]}"; do
  for arm in "${ARM[@]}"; do
    for seed in "${SEEDS[@]}"; do
      tag="L2S_${seq}_${arm}_s${seed}"
      # run_dir 必须取自既有 L2 主表记录（同一批地图 = 单变量对照的前提；
      # 硬编码 r33_rebase 会跑到另一批地图上，跨批 = 口径事故）
      L2JSON="$RD/L2_${seq}_${arm}_s${seed}_rd_table.json"
      rd=$($PY -c "
import json,sys
d=json.load(open('$L2JSON'))
print(d['run_dir'].replace('/home/jiangwenheng/cron/monogs-ours/','').rstrip('/')+'/')
" 2>/dev/null)
      if [ -z "$rd" ] || [ ! -d "$rd" ]; then echo "SKIP $tag (no L2 run_dir)"; continue; fi
      if [ -f "$RD/L2S_${seq}_${arm}_s${seed}_b8-4-4-4-4_ded20mm.json" ]; then
        echo "DONE $tag (cached)"; continue
      fi
      log="results/gs_compress/l2s_logs/${tag}.log"
      echo "RUN  $tag -> $rd"
      # 体素合并 + 均匀量化（逐点调用 rd_harness；rd_sweep 不带 dedup 参数）
      # rd_harness 自行在 tag 后追加 _b<bits>_ded20mm
      for cfg in ${UNIFORM//;/ }; do
        $PY scripts/gs_compress/rd_harness.py --run-dir "$rd" --tag "$tag" \
            --bits "$cfg" --dedup-voxel-m "$DEDUP" \
            --frames "$FRAMES" --device "$DEV" >> "$log" 2>&1
        echo "  point $cfg rc=$?"
      done
    done
  done
done
echo "struct codec batch done."
$PY scripts/gs_compress/l2s_aggregate.py
