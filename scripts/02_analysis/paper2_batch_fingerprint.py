#!/usr/bin/env python
"""paper2_batch_fingerprint.py — 跨批次臂等价性核验（G2-S1；零 GPU，可复跑工件）。

消费方：论文 2 写作轨（决定 R34 留出面板的 **ATE 表**能否与主表同稿引用）。
**作用域**：本工具只核 **ATE 表三臂**（`rb`/`sw`/`gate`）。**不覆盖 codec 面板**——
codec 主面板臂 = `{baseline, final}`、codec 留出面板臂 = `{rb, gate}`，两者**不可互相映射**
（`final`↔`gate` 的 `SWBA.swba_max_static_conf` 为 `None` vs `0.38`）⇒ 不得据此声称
"codec 留出检查 = 系统相同、只换序列"。改 `ARM_MAP` 或新增面板前先想清这一点。
判据出处：DISCIPLINE「测量口径」4（等价性/阳性对照须落成可复跑工件）+「比较前提」5
（跨批取对照必须补批次等价性门）。

问题：论文 2 主表用 R33 批（Bonn 7 序列 × 4 臂 × 3 seed，2026-09-16）；
R34 面板用另一批（TUM 5 + Bonn 1 序列 × 3 臂 × 3 seed，2026-09-17）。
两批能否合引，取决于**同角色臂的配置是否逐字段一致**（即 ATE 表口径的"同栈同码"）。

方法：把每个 R34 run 的 config 与主批同角色臂的 config 逐字段对比，
**排除数据集/运行实例字段**（`Dataset.*` / `Results.*` / `inherit_from` / `seed`）——
这些按设计不同（不同数据集、不同 save_dir），不构成臂差异。

臂角色映射（由 enabled 开关面判定，非按名猜）：
  R34 `rb`   ↔ 主批 `baseline`  （全关：SWBA/LoopClosure 均 false）
  R34 `sw`   ↔ 主批 `swbaonly`  （SWBA=true，LoopClosure=false）
  R34 `gate` ↔ 主批 `gate`      （SWBA=true + LoopClosure=true + swba_max_static_conf=0.38）

结论：PASS = 三个角色臂在**所有非数据集字段上逐字段一致**。

用法：
  python scripts/02_analysis/paper2_batch_fingerprint.py            # 判定 + 打印 diff 集
  python scripts/02_analysis/paper2_batch_fingerprint.py --selfcheck # 含阳性/阴性对照
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

# 数据集/运行实例字段——按设计跨批不同，排除出"臂指纹"
EXCLUDE_PREFIX = ("Dataset.", "Results.")
EXCLUDE_EXACT = {"inherit_from", "seed"}

# R34 短臂名 → 主批臂名（角色映射；正控见 --selfcheck）
ARM_MAP = {"rb": "baseline", "sw": "swbaonly", "gate": "gate"}


def _flat(d, pre=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(_flat(v, pre + k + "."))
        else:
            out[pre + k] = v
    return out


def _load(p):
    with open(p) as f:
        return yaml.safe_load(f)


def _arm_fingerprint(cfg_path):
    """非数据集字段的扁平字典（臂指纹本体）。"""
    d = _flat(_load(cfg_path))
    return {k: v for k, v in d.items()
            if not k.startswith(EXCLUDE_PREFIX) and k not in EXCLUDE_EXACT}


def _main_arm_config(arm: str) -> Path:
    """主批某臂的代表 config（seed0 任取一序列，臂内指纹应与序列无关）。"""
    hits = sorted(glob.glob(
        str(ROOT / f"results/paper2_fulltable/r33_rebase_{arm}_*_seed0/"
                    "datasets_bonn/*/seed_0/*/config.yml")))
    if not hits:
        raise FileNotFoundError(f"no main-batch config for arm {arm!r}")
    return Path(hits[0])


def _r34_configs(short: str):
    return sorted(glob.glob(
        str(ROOT / f"results/paper2_rollout/r34_{short}_*/datasets_*/*/*/*/config.yml")))


def _run_dir(p: str) -> str:
    return p.split("/")[-4]  # results/paper2_rollout/<RUNDIR>/datasets_*/*/*/config.yml


def check(verbose=True):
    """返回 (ok: bool, report: list[str])。"""
    rep = []
    ok = True
    for short, mapped in ARM_MAP.items():
        base = _arm_fingerprint(_main_arm_config(mapped))
        runs = _r34_configs(short)
        diffs = {}
        for p in runs:
            other = _arm_fingerprint(p)
            for k in sorted(set(base) | set(other)):
                if base.get(k) != other.get(k):
                    diffs.setdefault(k, set()).add(
                        (str(base.get(k)), str(other.get(k))))
        line = (f"  r34[{short}] <-> main[{mapped}]  {len(runs)} runs: "
                + ("IDENTICAL" if not diffs else f"{len(diffs)} DIFF"))
        rep.append(line)
        if verbose:
            for k, vp in sorted(diffs.items()):
                rep.append(f"      {k}: {sorted(vp)}")
        if diffs:
            ok = False
    return ok, rep


def selfcheck():
    """阳性对照：篡改一个机制开关必须被检出（证明检查非恒真）。
    阴性对照：不排除 Dataset.* 时，跨批必然误报 diff（证明排除是承重的）。"""
    short, mapped = "gate", "gate"
    base = _arm_fingerprint(_main_arm_config(mapped))
    runs = _r34_configs(short)
    assert runs, "no r34 gate runs"
    other = _arm_fingerprint(runs[0])

    # 阳性对照：把基准指纹的一个机制开关改掉 ⇒ 必须出现 diff。
    pos = dict(base)
    key = "SWBA.swba_max_static_conf"
    assert key in pos, f"positive-control key {key!r} missing from main arm"
    pos[key] = 999.0
    pos_hit = any(pos.get(k) != other.get(k) for k in set(pos) | set(other))
    print(f"[pos] mutated {key} -> detected: {pos_hit}")
    assert pos_hit, "positive control failed: mutation not detected"

    # 阴性对照：若按"全字段"比（不排除数据集字段），跨批应被误报为 diff
    # ——证明 EXCLUDE_PREFIX/EXCLUDE_EXACT 是承重的，而非摆设。
    base_full = _flat(_load(_main_arm_config(mapped)))
    other_full = _flat(_load(runs[0]))
    full_diffs = sum(1 for k in set(base_full) | set(other_full)
                     if base_full.get(k) != other_full.get(k))
    print(f"[neg] full-field compare (no exclusion) -> false diffs: {full_diffs} "
          f"(expected >0: batches differ by design in Dataset.*/Results.*)")
    assert full_diffs > 0, "negative control failed: full compare shows no diff (suspicious)"

    # 真实口径必须不含任何被排除键
    assert not any(k.startswith(EXCLUDE_PREFIX) for k in base), \
        "fingerprint must exclude Dataset.*/Results.* by construction"
    assert not (EXCLUDE_EXACT & set(base)), \
        "fingerprint must exclude inherit_from/seed by construction"
    print("[neg] real fingerprint excludes Dataset.*/Results.*/inherit_from/seed: True")


def main():
    ok, rep = check()
    print("=== paper2 cross-batch arm equivalence (R33 main <-> R34 held-out) ===")
    print("\n".join(rep))
    print("\nOVERALL:", "PASS — arms identical across batches" if ok
          else "FAIL — arm drift detected")
    if "--selfcheck" in sys.argv:
        print("\n=== controls ===")
        selfcheck()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
