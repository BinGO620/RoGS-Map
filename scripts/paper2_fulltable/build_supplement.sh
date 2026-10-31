#!/usr/bin/env bash
# build_supplement.sh — 编译论文 2 补充材料（CVM 2027，匿名审稿版）为 PDF。
# 同 build_paper2.sh：tectonic（自包含引擎）；中间产物在项目内 .tmp/（已 gitignore）。
#
# 用法：bash scripts/paper2_fulltable/build_supplement.sh
# 输入：papers/paper2/supplement/{supplement.tex,tables/*.tex} +
#       results/paper2_fulltable/evidence/figs/figS_repair_person_tracking2.pdf
# 交付物：papers/paper2/supplement/supplement.pdf
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
TECTONIC="${TECTONIC:-/data/conda_envs/tex/bin/tectonic}"
SRC="$REPO/papers/paper2/supplement"
FIG="$REPO/results/paper2_fulltable/evidence/figs/figS_repair_person_tracking2.pdf"
OUT="$REPO/.tmp/supp_build"

if [ ! -f "$SRC/supplement.tex" ]; then
  echo "错误：$SRC/supplement.tex 不存在。" >&2
  exit 2
fi
if [ ! -f "$FIG" ]; then
  echo "错误：补充图缺失 $FIG（先跑 dump_repair_render.py --seq person_tracking2 --out figS_repair_person_tracking2）" >&2
  exit 2
fi

rm -rf "$OUT"; mkdir -p "$OUT/tables"
cp "$SRC/supplement.tex" "$OUT/"
cp "$SRC"/tables/*.tex "$OUT/tables/"
cp "$FIG" "$OUT/"

cd "$OUT"
"$TECTONIC" -X compile supplement.tex --keep-logs 2>&1 | \
  grep -iE "Overfull|Missing char|Output written|error" || true

echo "---"
if [ -f supplement.log ]; then
  /data/conda_envs/monogs-ours/bin/python - supplement.log <<'PY'
import re, sys
log = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
pages = re.findall(r"\((\d+) pages", log)
print(f"pages={pages[-1] if pages else '?'}  overfull={log.count('Overfull')}  "
      f"missing_char={log.count('Missing character')}")
PY
fi
cp "$OUT/supplement.pdf" "$SRC/supplement.pdf"
echo "交付 PDF：$SRC/supplement.pdf"
