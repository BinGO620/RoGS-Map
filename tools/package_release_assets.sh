#!/usr/bin/env bash
# package_release_assets.sh — 打包论文2离线轨底图为 GitHub Release 资产。
#
# 用法（在本仓根目录）：
#   bash tools/package_release_assets.sh
# 产物：tools/dist/<name>.tar.gz + tools/release_assets.sha256 + tools/release_asset_index.tsv
# 上传：gh release create base-maps-v1 tools/dist/*.tar.gz --generate-notes
#      （或网页：Releases → Draft a new release → 拖入 tools/dist/ 下所有文件）
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=${MONOGS_OURS:-/data/monogs-ours}
DIST=tools/dist
mkdir -p "$DIST"
: > tools/release_assets.sha256
: > tools/release_asset_index.tsv
n=0
while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    exp=$(basename "$rel")
    # run 根下每个 datasets_*/…/seed_N/<时间戳>/ 就是一次实际运行
    for cfg in $(find "$SRC/$rel" -name config.yml | sort); do
        tsdir=$(dirname "$cfg")
        ts=$(basename "$tsdir")
        seed=$(basename "$(dirname "$tsdir")")
        name="${exp}__${seed}_${ts}"
        tmp=$(mktemp -d)
        if ! (cd "$tsdir" && cp --parents config.yml plot/trj_full_final.json \
                 point_cloud/final/point_cloud.ply "$tmp" 2>/dev/null); then
            echo "skip（缺判据件）: $exp/$seed/$ts"
            rm -rf "$tmp"; continue
        fi
        tar -C "$tmp" -czf "$DIST/${name}.tar.gz" .
        rm -rf "$tmp"
        printf '%s\t%s\n' "$name" "$rel" >> tools/release_asset_index.tsv
        sha256sum "$DIST/${name}.tar.gz" | sed "s|$DIST/||" >> tools/release_assets.sha256
        n=$((n+1))
    done
done < tools/release_asset_runs.txt
echo "共 $n 个资产包于 $DIST/"
echo "上传：gh release create base-maps-v1 $DIST/*.tar.gz --generate-notes"
echo "     （或网页 Releases → Draft → 拖入全部 .tar.gz）"
