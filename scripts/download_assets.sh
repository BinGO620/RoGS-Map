#!/usr/bin/env bash
# download_assets.sh — 从 GitHub Release 下载论文2离线轨底图并按 sha256 清单校验。
# 资产 = 每 run 一包（config.yml + plot/trj_full_final.json + point_cloud/final/*.ply），
# 解压回 results/base_runs/<run>/，供 rd_harness / repair_map 作为 --run-dir/--base-run。
set -euo pipefail
cd "$(dirname "$0")/.."
REL=${1:-base-maps-v1}
mkdir -p results/base_runs
gh release download "$REL" -D results/base_runs --clobber --pattern '*.tar.gz'
(sha256sum -c tools/release_assets.sha256 --quiet 2>/dev/null || true)
for t in results/base_runs/*.tar.gz; do
    [ -e "$t" ] || { echo "未找到资产包"; exit 1; }
    name=$(basename "$t" .tar.gz)
    rundir="results/base_runs/$(echo "$name" | tr '_' '/')"   # results_paper2_fulltable_x → results/paper2/fulltable/x 需按清单还原
    # 目录名还原以 release_asset_runs.txt 为准
    rel=$(grep -F "${name}" tools/release_asset_runs.txt || true)
    [ -z "$rel" ] && { echo "清单缺 $name"; exit 1; }
    mkdir -p "$rel"
    tar -xzf "$t" -C "$rel"
    echo "restored: $rel"
done
echo "离线轨底图就绪。示例："
echo "  python scripts/gs_compress/rd_harness.py --run-dir $(head -1 tools/release_asset_runs.txt) --tag demo --bits 16,8,8,8,8 --frames 0,60,120,180"
