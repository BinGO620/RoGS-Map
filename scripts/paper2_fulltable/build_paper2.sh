#!/usr/bin/env bash
# build_paper2.sh — 编译论文 2（CVM 2027）为 PDF。
#
# 本地无系统 LaTeX；用 tectonic（自包含引擎，XeTeX 后端）。
# 本机 tectonic 位置：/data/conda_envs/tex/bin/tectonic（0.17.0，已验证）。
#
# 输入来源（2026-10-11 更新）：Phase 3 新稿已建 `papers/paper2/paper2_cvm.tex`，
# 本脚本默认编译**活区新稿**（`papers/paper2/`）。复核 v0 归档版面时传 src_dir =
# `papers/paper2/archive/v0_2026-10-10/`（归档副本仍可编译）。
#
# 用法：bash scripts/paper2_fulltable/build_paper2.sh [out_dir] [src_dir]
#   src_dir 默认 = papers/paper2
#   out_dir 默认 = <repo>/.tmp/paper2_build（**项目内**，已 gitignore；不再用 /tmp）
#
# 交付物（2026-10-13 增补）：编译成功后自动把 PDF 复制到 `papers/paper2/paper2_cvm.pdf`
#   （仅当 src_dir = 活区时）——**最新成品始终在项目内**，无需手工搬运。
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
TECTONIC="${TECTONIC:-/data/conda_envs/tex/bin/tectonic}"
OUT="${1:-$REPO/.tmp/paper2_build}"
P="${2:-$REPO/papers/paper2}"

if [ ! -f "$P/paper2_cvm.tex" ]; then
  echo "错误：$P/paper2_cvm.tex 不存在。" >&2
  exit 2
fi

# 防误删守卫：OUT 必须位于仓库内或 /tmp 下（脚本对 OUT 执行 rm -rf）。
case "$OUT" in
  "$REPO"/*|/tmp/*) ;;
  *) echo "拒绝：out_dir=$OUT 既不在仓库内也不在 /tmp 下（防 rm -rf 误删）" >&2; exit 2 ;;
esac
# 更严：不得是仓库根或 papers 目录本身
if [ "$OUT" = "$REPO" ] || [ "$OUT" = "$REPO/papers" ] || [ "$OUT" = "$REPO/papers/paper2" ]; then
  echo "拒绝：out_dir=$OUT 是受保护目录" >&2; exit 2
fi

rm -rf "$OUT"; mkdir -p "$OUT"
cp "$P/paper2_cvm.tex" "$OUT/"
cp -r "$P/tables" "$P/figs" "$OUT/"
cp "$REPO/papers/paper2/template_cvm/cvm.sty" "$REPO/papers/paper2/template_cvm/cvm_eso.sty" \
   "$REPO/papers/paper2/template_cvm/cvmbib.bib" "$REPO/papers/paper2/template_cvm/cvm.bst" "$OUT/"

cd "$OUT"
"$TECTONIC" -X compile paper2_cvm.tex --keep-logs 2>&1 | \
  grep -iE "Overfull|Missing char|Output written|error" || true

echo "---"
if [ -f paper2_cvm.log ]; then
  /data/conda_envs/monogs-ours/bin/python - "$OUT/paper2_cvm.log" <<'PY'
import re, sys
log = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
pages = re.findall(r"\((\d+) pages", log)
print(f"pages={pages[-1] if pages else '?'}  overfull={log.count('Overfull')}  "
      f"missing_char={log.count('Missing character')}  "
      f"undefined_ref={log.count('Reference') and log.count('undefined')}")
PY
fi

# 交付物落回项目（仅活区构建）：最新成品始终在 papers/paper2/paper2_cvm.pdf
# NO_DELIVER=1 关闭回写（测试用）：pytest 的构建门禁只验证"能编译"，不得改动
# 受版本控制的交付 PDF——否则每跑一次测试该文件就变成脏改动（2026-10-28 实测）。
LIVE="$REPO/papers/paper2"
if [ "${NO_DELIVER:-0}" != "1" ] && [ "$P" = "$LIVE" ] && [ -f "$OUT/paper2_cvm.pdf" ]; then
  cp "$OUT/paper2_cvm.pdf" "$LIVE/paper2_cvm.pdf"
  echo "交付 PDF（项目内）: $LIVE/paper2_cvm.pdf"
fi
echo "构建中间产物: $OUT/paper2_cvm.pdf"
