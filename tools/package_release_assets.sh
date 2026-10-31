#!/usr/bin/env bash
# package_release_assets.sh — 打包论文2离线轨底图为 GitHub Release 资产。
#
# 用法（在本仓根目录）：
#   bash tools/package_release_assets.sh            # 打包 + sha256 清单
#   gh release create base-maps-v1 tools/dist/*.tar.gz --title ... --notes ...
#
# 每 run 裁三个判据件：config.yml + plot/trj_full_final.json + point_cloud/final/*.ply
# 源 = tools/release_asset_runs.txt（相对 monogs-ours 备份库的路径，由
# tools/derive_release_runs.py 从证据 json 反推生成）。
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=/data/monogs-ours
DIST=tools/dist
mkdir -p "$DIST"
: > tools/release_assets.sha256
n=0
while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    run="$SRC/$rel"
    name=$(echo "$rel" | tr '/' '_')
    tmp=$(mktemp -d)
    (cd "$run" && cp --parents config.yml plot/trj_full_final.json point_cloud/final/*.ply "$tmp") 2>/dev/null \
        || { echo "skip（缺件）: $rel"; rm -rf "$tmp"; continue; }
    tar -C "$tmp" -czf "$DIST/${name}.tar.gz" .
    rm -rf "$tmp"
    sha256sum "$DIST/${name}.tar.gz" | sed "s|$DIST/||" >> tools/release_assets.sha256
    n=$((n+1))
    echo "packed: $rel"
done < tools/release_asset_runs.txt
echo "共 $n 个资产包于 $DIST/；上传："
echo "  gh release create base-maps-v1 $DIST/*.tar.gz --generate-notes"
echo "哈希清单：tools/release_assets.sha256（随仓提交，download_assets.sh 据此校验）"
