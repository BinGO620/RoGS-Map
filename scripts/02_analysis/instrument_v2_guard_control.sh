#!/usr/bin/env bash
# instrument_v2_guard_control.sh — 守卫路径阳性对照（可复跑工件，关卡① 上轮 #4 整改）。
#
# 目的：证明 2864c997（缺全域静态空集守卫）→ 5695bc94（加守卫）的改动**只改可判性、不改数值**。
# 方法：取 2864c997 的测量脚本副本，在同一 crowd run 上重跑，与现行读数逐帧比对：
#       ① 两臂皆有效的帧 → 数值必须逐位一致；
#       ② 新码判 None 的帧 → 旧码必须产出 NaN（而非数值）；
#       ③ 真不一致数必须为 0。
# 用法：PY=<python> bash scripts/02_analysis/instrument_v2_guard_control.sh [render_name]
#       默认 render_name = render_L3_crowd_off_s0_canon（crowd 族：守卫必触发）
# **前提**：需在**数据侧机器（远程 3090）**跑——run_dir 为仓库相对路径且需 GPU 渲染；
#         本地无该 run 的 PLY ⇒ 本地不可复跑。2026-09-24 远程实跑 rc=0（真不一致 0）。
set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PY:-/data/conda_envs/monogs-ours/bin/python}"
NAME="${1:-render_L3_crowd_off_s0_canon}"
OLD_SHA="${OLD_SHA:-2864c997}"
CTL_DIR="$REPO/results/lifecycle_paper2/instrument_v2/control"
DEVICE="${DEVICE:-cuda:0}"

mkdir -p "$CTL_DIR"
TMP_OLD="$REPO/scripts/02_analysis/_old_rescore_tmp.py"
trap 'rm -f "$TMP_OLD"' EXIT

git -C "$REPO" show "$OLD_SHA:scripts/02_analysis/instrument_v2_rescore.py" > "$TMP_OLD"
ARGS=$("$PY" - "$REPO" "$NAME" <<'PYEOF'
import json, sys
repo, name = sys.argv[1], sys.argv[2]
m = json.load(open(f"{repo}/results/lifecycle_paper2/instrument_v2/rescore_batch_manifest.json"))
v = m[name]
print(v["run_dir"] + "\n" + v["frames"])
PYEOF
)
RD=$(echo "$ARGS" | sed -n 1p)
FR=$(echo "$ARGS" | sed -n 2p)
echo "[ctl] run=$NAME old_sha=$OLD_SHA"
echo "[ctl] run_dir=$RD"

"$PY" "$TMP_OLD" --run-dir "$RD" --frames "$FR" \
  --out "$CTL_DIR/old_${NAME}_${OLD_SHA}.json" --device "$DEVICE" > "$CTL_DIR/old_${NAME}_${OLD_SHA}.log" 2>&1
echo "[ctl] old-code rc=$?"

"$PY" - "$REPO" "$NAME" "$OLD_SHA" "$CTL_DIR" <<'PYEOF'
import json, math, sys, os
repo, name, old_sha, ctl = sys.argv[1:5]
old = json.load(open(f"{ctl}/old_{name}_{old_sha}.json"))
new = json.load(open(f"{repo}/results/lifecycle_paper2/instrument_v2/rescore/rescore_{name.replace('render_','')}.json"))
of = {f["frame"]: f for f in old["per_frame"]}
nf = {f["frame"]: f for f in new["per_frame"]}
same = newnone_oldnan = both_none = 0
bad = []
KEYS = ("exc_full_cm", "exc_ring_cm", "exc_m3_cm")
for fr in sorted(set(of) & set(nf)):
    for k in KEYS:
        a, b = of[fr].get(k), nf[fr].get(k)
        a_nan = isinstance(a, float) and math.isnan(a)
        if b is None:
            if a is None:
                both_none += 1
            elif a_nan:
                newnone_oldnan += 1
            else:
                bad.append((fr, k, f"new=None old={a:.4f}"))
        else:
            if a is None or a_nan:
                bad.append((fr, k, f"new={b:.4f} old={a}"))
            elif abs(a - b) > 1e-9:
                bad.append((fr, k, f"old={a:.4f} new={b:.4f}"))
            else:
                same += 1
lines = [
    f"# 守卫路径阳性对照 — {name}（旧码 {old_sha} vs 现行码）\n",
    "> **复跑前提**：需在数据侧机器（远程 3090）执行（run_dir 为仓库相对路径 + 需 GPU 渲染）；",
    "> 本地无该 run 的 PLY ⇒ 本地不可复跑。生成脚本：`scripts/02_analysis/instrument_v2_guard_control.sh`。",
    f"- 运行件：`old_{name}_{old_sha}.json`（旧码输出）、`../rescore/rescore_{name.replace('render_','')}.json`（现行码输出）",
    f"- 逐帧逐参照比对（3 参照 × {len(set(of) & set(nf))} 帧）：",
    f"  - 两臂皆有效且**逐位一致**：**{same}**",
    f"  - 新码 `None` 而旧码 `NaN`：**{newnone_oldnan}**（守卫把不可判帧从 NaN 转为 None）",
    f"  - 两侧皆缺：{both_none}",
    f"  - **真不一致：{len(bad)}**",
    "",
    f"**结论**：{'✅ 守卫只改可判性、不改数值（真不一致 = 0）' if not bad else '❌ 存在数值差异，守卫改动非纯可判性'}\n",
]
if bad:
    for x in bad[:10]:
        lines.append(f"- 不一致：{x}")
open(f"{ctl}/control_report.md", "w").write("\n".join(lines))
print("\n".join(lines))
sys.exit(1 if bad else 0)
PYEOF
rc=$?
echo "[ctl] comparison rc=$rc (0 = 通过)"
exit $rc
