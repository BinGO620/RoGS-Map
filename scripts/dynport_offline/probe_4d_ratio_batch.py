"""批量：4D 压缩比（排除抑制 + 绝对量化 + zlib）对全部 R1 快照。"""
import sys
sys.path.insert(0, '/data/monogs-ours')
import numpy as np, glob, zlib
from pathlib import Path

_ATTRS = ['xyz','log_scale','rot','opa','f_dc']
def quantize(v, bits, lo, hi):
    level = (1<<bits)-1
    span = max(hi-lo, 1e-9)
    return np.round(np.clip((v-lo)/span,0,1)*level).astype(np.uint16)

roots = [
    'results/dynport_offline/L1_v4',
    'results/dynport_offline/L2',
    'results/dynport_offline/L3',
]
# 收集所有 *_R1 目录（排除 seed 变体，先 seed0 优先）
import collections
cands = collections.defaultdict(list)
for r in roots:
    for d in glob.glob(f'{r}/*_R1'):
        seq = Path(d).name.replace('_R1','')
        cands[seq].append(d)

print(f'{"序列":<22}{"快照":>5}  {"10bit":>8}  {"8bit":>8}  {"6bit":>8}')
results = {}
for seq, dirs in sorted(cands.items()):
    d = sorted(dirs)[0]  # 首个（seed0 优先，glob 顺序）
    snaps = sorted(glob.glob(f'{d}/dynport_causal/frame_*.npz'))
    if not snaps: continue
    total_raw = 0
    for s in snaps:
        dd = np.load(s)
        total_raw += sum(len(dd[a].tobytes()) for a in _ATTRS)
    row = {}
    for bits in (6,8,10):
        tb, tz = 0, 0
        for s in snaps:
            dd = np.load(s)
            opa = dd['opa'].reshape(-1)
            alive = opa > -10
            raw = np.packbits(alive).tobytes()
            if alive.sum():
                for a in _ATTRS:
                    v = dd[a][alive].astype(np.float64)
                    lo, hi = np.percentile(v,[1,99])
                    q = quantize(v, bits, lo, hi)
                    raw += q.astype(np.uint8).tobytes() if bits<=8 else q.tobytes()
            tb += len(raw); tz += len(zlib.compress(raw,6))
        row[bits] = total_raw/tz
    results[seq] = row
    print(f'{seq:<22}{len(snaps):>5}  {row[10]:>7.2f}x  {row[8]:>7.2f}x  {row[6]:>7.2f}x')
