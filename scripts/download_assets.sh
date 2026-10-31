#!/usr/bin/env bash
# download_assets.sh — 从 GitHub Release 下载论文2离线轨底图并校验、还原。
# 还原位置以 tools/release_asset_index.tsv 为准（压缩包名 → run 目录）。
# 之后 rd_harness / repair_map 直接用 results/paper2_fulltable/<run>/… 作输入。
set -euo pipefail
cd "$(dirname "$0")/.."
REL=${1:-base-maps-v1}
if ! command -v gh >/dev/null; then
    echo "需要 gh（https://cli.github.com/）；或从 Release 网页手动下载到 tools/dist/ 后重跑本脚本"; exit 1
fi
mkdir -p tools/dist
gh release download "$REL" -D tools/dist --clobber --pattern '*.tar.gz'
sha256sum -c tools/release_assets.sha256 --quiet
echo "sha256 校验全部通过"
while IFS=$'\t' read -r name rel; do
    mkdir -p "$rel"
    tar -xzf "tools/dist/${name}.tar.gz" -C "$rel"
    echo "restored: $rel"
done < tools/release_asset_index.tsv
echo "底图就绪。验证一个 R-D 点："
echo "  python scripts/gs_compress/rd_harness.py --run-dir results/paper2_fulltable/balloon2_baseline_seed0 --tag demo --bits 16,8,8,8,8 --frames 0,60,120,180"
