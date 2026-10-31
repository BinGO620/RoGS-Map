#!/usr/bin/env bash
# run_instrument_v2_batch.sh — 仪器 v2 全臂重评分批（prereg_instrument_v2 §2b）。
# 一次性列全终态 run（清单 = instrument_v2/rescore_batch_manifest.json，109 run）；
# JSON-only 输出；done 文件记 rc。跑批期禁改本脚本、禁 sync（NOTES 同步约定）。
set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PY:-/data/conda_envs/monogs-ours/bin/python}"
MANIFEST="$REPO/results/lifecycle_paper2/instrument_v2/rescore_batch_manifest.json"
OUTROOT="$REPO/results/lifecycle_paper2/instrument_v2/rescore"
SHARD_COUNT="${SHARD_COUNT:-1}"
SHARD_INDEX="${SHARD_INDEX:-0}"
DONE="$REPO/results/lifecycle_paper2/instrument_v2/rescore_batch_shard${SHARD_INDEX}.done"
DEVICE="${DEVICE:-cuda:0}"

mkdir -p "$OUTROOT"
N_EXPECT=$("$PY" -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$MANIFEST")
echo "[batch] manifest entries = $N_EXPECT (expect 109); shard ${SHARD_INDEX}/${SHARD_COUNT} on $DEVICE"
if [ "$N_EXPECT" -ne 109 ]; then echo "BATCH-ABORT: manifest count != 109"; exit 2; fi

: > "$DONE"
SHARD_COUNT="$SHARD_COUNT" SHARD_INDEX="$SHARD_INDEX" "$PY" - "$MANIFEST" "$OUTROOT" "$DEVICE" "$DONE" <<'PYEOF'
import json, subprocess, sys, os
manifest, outroot, device, done = sys.argv[1:5]
shard_n = int(os.environ.get('SHARD_COUNT', '1'))
shard_i = int(os.environ.get('SHARD_INDEX', '0'))
script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(done))))),
                      'scripts', '02_analysis', 'instrument_v2_rescore.py')
pairs = json.load(open(manifest))
items = sorted(pairs.items())[shard_i::shard_n]
print(f"[batch] shard {shard_i}/{shard_n}: {len(items)} runs", flush=True)
for rd_name, v in items:
    out = os.path.join(outroot, rd_name.replace('render_', 'rescore_', 1) + '.json')
    if os.path.exists(out):
        with open(done, 'a') as f: f.write(f"{rd_name} skip-exists\n")
        print(f"[batch] {rd_name}: skip-exists", flush=True); continue
    cmd = [sys.executable, script,
           '--run-dir', v['run_dir'], '--frames', v['frames'],
           '--out', out, '--device', device]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    print(f"[batch] {rd_name}: rc={r.returncode}", flush=True)
    if r.returncode != 0:
        print(r.stderr[-800:], flush=True)
    with open(done, 'a') as f:
        f.write(f"{rd_name} rc={r.returncode}\n")
n_ok = sum(1 for line in open(done) if line.split()[-1] in ('rc=0', 'skip-exists'))
print(f"[batch] shard {shard_i} complete: {n_ok}/{len(items)} ok", flush=True)
PYEOF
rc=$?
n_rc0=$(grep -c 'rc=0\|skip-exists' "$DONE" || true)
echo "[batch] shard $SHARD_INDEX done-file ok-count = $n_rc0"
exit $rc

