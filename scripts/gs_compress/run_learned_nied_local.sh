#!/usr/bin/env bash
# run_learned_nied_local.sh — 在本机 2060 上完整跑 Niedermayr c3dgs 基线（78 张 = L2 42 + L3 36）。
#
# 为什么全部改本机跑（2026-10-16，用户提出）：远程 3090 与本机 2060 混产会让 ratio 列 provenance
# 不单一。远程那 48 行里有 12 张的 npz 是从本机 rsync 过去的（远程日志为「复用已有 npz」），
# 所以跨机一致性**只验证过解码+渲染那一段，没验证压缩那一段**；而两台机的 CUDA 扩展是各自编译的
# （不同 SM 架构），无法在远程掉线时证否。为免留把柄，全部改为本机产出。
#
# 断点续跑：驱动见 .tmp/learned_nied/<tag>/out_vq/point_cloud/iteration_5001/point_cloud.npz 即跳过
# 压缩（只重做解码+渲染），所以中断后（含机器休眠）直接重跑本脚本即可，不会重压已完成的地图。
#
# 输出：results/gs_compress/evidence/rd/learned_nied_L{2,3}.json（增量落盘）。
#   注意：生成器 paper2_codec_tables.py 有**完整性门禁**——行数不覆盖整个 split 时该行不入表，
#   所以中途的部分 json 不会污染 Table 4。
#
# 用法：bash scripts/gs_compress/run_learned_nied_local.sh
set -uo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY=/data/conda_envs/nied-c3dgs/bin/python

for SPLIT in L2 L3; do
  echo "=== [$SPLIT] start $(date) ==="
  "$PY" "$R/scripts/gs_compress/learned_nied_c3dgs_baseline.py" \
    --split "$SPLIT" --iters 5000 --device cuda:0
  rc=$?
  echo "=== [$SPLIT] end rc=$rc $(date) ==="
done
echo "LOCAL-FULL-DONE $(date)"
