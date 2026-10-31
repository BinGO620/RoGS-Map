#!/usr/bin/env python
"""test_fulltable_configs.py — paper2_fulltable L1 门禁。

验证 7 个 final config：①继承链可解析且文件存在；②SWBA/LoopClosure
开启；③最终形态参数齐全（v3 检索/多样性配额/两段式/门 0.05）；
④基线 config 存在（combined_prune 同名序列）。
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

ROOT = Path(__file__).resolve().parents[2]
SEQS = ["balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2"]

FINAL_KEYS = {
    ("SWBA", "enabled"): True,
    ("LoopClosure", "enabled"): True,
    ("LoopClosure", "geo_score_v3"): True,
    ("LoopClosure", "geo_cell_diversity"): True,
    ("LoopClosure", "verify_block_affine"): True,
    ("LoopClosure", "verify_icp_init"): True,
}


def _update_recursive(d1, d2):
    for k, v in d2.items():
        if isinstance(v, dict) and isinstance(d1.get(k), dict):
            _update_recursive(d1[k], v)
        else:
            d1[k] = v
    return d1


def _load_merged(path):
    """Mirror utils/config_utils.load_config: inherit_from -> method_from -> local.

    An earlier version only followed inherit_from, so it silently dropped the
    method_from layer — which is where ReliabilitySignal.enabled lives. A gate
    that claims to check the *runtime* config has to include that layer
    (otherwise it would, e.g., infer "static_conf logging is off" when it is on).
    """
    cfg = yaml.safe_load(open(path))
    inh = cfg.get("inherit_from")
    base = _load_merged(ROOT / inh) if inh else {}
    mf = cfg.get("method_from")
    if mf:
        _update_recursive(base, yaml.safe_load(open(ROOT / mf)))
    _update_recursive(base, cfg)
    return base


def test_final_configs_complete():
    for seq in SEQS:
        p = ROOT / "configs/experiments/paper2_fulltable" / f"{seq}_final.yaml"
        assert p.exists(), f"missing {p}"
        cfg = _load_merged(p)
        for (sec, key), want in FINAL_KEYS.items():
            got = cfg.get(sec, {}).get(key)
            assert got == want, f"{seq}: {sec}.{key}={got}, want {want}"
        lc = cfg["LoopClosure"]
        assert lc["max_median_resid"] == 0.05
        assert lc["geo_candidates"] == 60
        assert lc["loop_weight"] == 30.0


def test_baseline_configs_exist():
    for seq in SEQS:
        p = ROOT / "configs/experiments/combined_prune" / f"{seq}.yaml"
        if seq == "balloon":
            assert p.exists()
            continue
        # crowd/crowd2/... 基线若不在 combined_prune，则必须显式记录替代来源
        if not p.exists():
            alt = ROOT / "configs/rgbd/bonn" / f"{seq}.yaml"
            assert alt.exists(), f"{seq}: no baseline config anywhere"


def test_no_sequence_special_casing():
    """通用性纪律（CLAUDE.md #8）：7 个 final config 除继承与 save_dir 外
    必须逐字段一致——不允许任何序列特判参数。"""
    bodies = []
    for seq in SEQS:
        p = ROOT / "configs/experiments/paper2_fulltable" / f"{seq}_final.yaml"
        text = open(p).read()
        text = text.split("inherit_from:")[1]  # 去掉头注释，保留结构
        text = text.replace(f"configs/rgbd/bonn/{seq}.yaml", "<SEQ>")
        text = text.replace(f"results/paper2_fulltable/{seq}_final", "<SAVE>")
        bodies.append(text)
    assert all(b == bodies[0] for b in bodies), \
        "final configs diverge beyond inheritance/save_dir — sequence special-casing?"


def test_r30_sensitivity_configs():
    """实验 F（K8 阈值敏感度扫描）：r30_conf030/045 必须与 r29_framegate
    逐字段一致，仅 swba_max_static_conf 与 save_dir 不同——保证扫描是
    单变量（阈值），无其它机制漂移。"""
    import re
    for seq in SEQS:
        for tag, thr in [("r30_conf030", 0.30), ("r30_conf045", 0.45)]:
            p = ROOT / "configs/experiments/paper2_fulltable" / f"{tag}_{seq}.yaml"
            assert p.exists(), f"missing {p}"
            cfg = _load_merged(p)
            assert cfg["SWBA"]["enabled"] is True
            assert cfg["SWBA"]["swba_max_static_conf"] == thr, \
                f"{tag}_{seq}: threshold {cfg['SWBA']['swba_max_static_conf']} != {thr}"
            assert cfg["LoopClosure"]["enabled"] is True
            # 逐字段比对 r29 与 r30（去掉头注释后）
            r29 = (ROOT / "configs/experiments/paper2_fulltable" /
                   f"r29_framegate_{seq}.yaml").read_text()
            r30 = p.read_text()
            strip = lambda t: re.sub(r"^#.*\n", "", t, flags=re.M).lstrip("\n")
            a = strip(r29).replace("0.38", "<THR>").replace(
                f"r29_framegate_{seq}", "<SAVE>")
            b = strip(r30).replace(f"{thr:.2f}", "<THR>").replace(
                f"{tag}_{seq}", "<SAVE>")
            assert a == b, f"{tag}_{seq}: diverges from r29 beyond threshold/save_dir"


def test_r31_selfcheck_configs():
    """R31 自校验式 SWBA 门：r31_selfcheck_* 必须与 r29_framegate 逐字段
    一致，仅新增 swba_min_rel_improve 与 save_dir——保证单变量（自校验门）。"""
    import re
    for seq in SEQS:
        for tag, thr in [("r31_selfcheck_0p5", 0.005),
                         ("r31_selfcheck_1", 0.01),
                         ("r31_selfcheck_2", 0.02)]:
            p = ROOT / "configs/experiments/paper2_fulltable" / f"{tag}_{seq}.yaml"
            assert p.exists(), f"missing {p}"
            cfg = _load_merged(p)
            assert cfg["SWBA"]["enabled"] is True
            assert cfg["SWBA"]["swba_max_static_conf"] == 0.38, \
                f"{tag}_{seq}: static_conf gate must stay 0.38"
            assert cfg["SWBA"]["swba_min_rel_improve"] == thr, \
                f"{tag}_{seq}: swba_min_rel_improve {cfg['SWBA'].get('swba_min_rel_improve')} != {thr}"
            assert cfg["LoopClosure"]["enabled"] is True
            # 逐字段比对 r29（去掉头注释、阈值行、save_dir 后应完全一致）
            r29 = (ROOT / "configs/experiments/paper2_fulltable" /
                   f"r29_framegate_{seq}.yaml").read_text()
            r31 = p.read_text()
            strip = lambda t: re.sub(r"^#.*\n", "", t, flags=re.M).lstrip("\n")
            norm = lambda t, tag_: (strip(t)
                                    .replace(f"  swba_min_rel_improve: {thr}\n", "")
                                    .replace(f"r29_framegate_{seq}", "<SAVE>")
                                    .replace(f"{tag_}_{seq}", "<SAVE>"))
            assert norm(r29, "r29") == norm(r31, tag), \
                f"{tag}_{seq}: diverges from r29 beyond the self-check gate"


def test_r32_regate038_configs():
    """实验 F 重基线（R32）：r32_regate038_* 是 r29_framegate（0.38 臂）在
    当前 HEAD 代码上的同 config 重跑——必须与 r29_framegate 逐字段一致，
    **仅 save_dir（含臂名）不同**，阈值保持 0.38。任何其它差异都意味着
    重基线混入了变量，敏感度曲线的可比性即不成立。"""
    import re
    for seq in SEQS:
        p = ROOT / "configs/experiments/paper2_fulltable" / f"r32_regate038_{seq}.yaml"
        assert p.exists(), f"missing {p}"
        cfg = _load_merged(p)
        assert cfg["SWBA"]["enabled"] is True
        assert cfg["SWBA"]["swba_max_static_conf"] == 0.38, \
            f"r32_regate038_{seq}: gate must stay 0.38, got {cfg['SWBA']['swba_max_static_conf']}"
        assert "swba_min_rel_improve" not in cfg["SWBA"], \
            f"r32_regate038_{seq}: self-check gate must not be present (that is R31)"
        assert cfg["LoopClosure"]["enabled"] is True
        # 逐字段比对 r29：去掉头注释、把臂名归一化后应完全一致
        r29 = (ROOT / "configs/experiments/paper2_fulltable" /
               f"r29_framegate_{seq}.yaml").read_text()
        r32 = p.read_text()
        strip = lambda t: re.sub(r"^#.*\n", "", t, flags=re.M).lstrip("\n")
        norm = lambda t, tag: strip(t).replace(f"{tag}_{seq}", "<SAVE>")
        assert norm(r29, "r29_framegate") == norm(r32, "r32_regate038"), \
            f"r32_regate038_{seq}: diverges from r29 beyond save_dir (rebase must be variable-free)"


def test_r33_rebase_arm_configs():
    """R33 重基线（final / baseline / swbaonly）：三个新臂族必须与各自的原臂
    逐字段一致、**仅 save_dir 异**——重基线不得混入任何变量，否则新旧读数
    不可比。swbaonly 的 4 个新序列由 r33_rebase_final 去掉 LoopClosure 派生
    （与既有 3 个 swbaonly 同规则）。"""
    import re
    strip = lambda t: re.sub(r"^#.*\n", "", t, flags=re.M).lstrip("\n")
    nolc = lambda t: re.sub(r"LoopClosure:\n(?:  .*\n)+\n", "", t)

    for seq in SEQS:
        # --- final ---
        p = ROOT / "configs/experiments/paper2_fulltable" / f"r33_rebase_final_{seq}.yaml"
        assert p.exists(), f"missing {p}"
        cfg = _load_merged(p)
        assert cfg["SWBA"]["enabled"] is True
        assert cfg["LoopClosure"]["enabled"] is True
        a = strip((ROOT / "configs/experiments/paper2_fulltable" / f"{seq}_final.yaml").read_text())
        b = strip(p.read_text())
        assert a.replace(f"{seq}_final", "<SAVE>") == b.replace(f"r33_rebase_final_{seq}", "<SAVE>"), \
            f"r33_rebase_final_{seq}: 与原 final 臂不一致（重基线不得含变量）"

        # --- baseline ---
        p = ROOT / "configs/experiments/paper2_fulltable" / f"r33_rebase_baseline_{seq}.yaml"
        assert p.exists(), f"missing {p}"
        cfg = _load_merged(p)
        assert "SWBA" not in cfg or not cfg.get("SWBA", {}).get("enabled"), \
            f"r33_rebase_baseline_{seq}: SWBA 必须关闭"
        a = strip((ROOT / "configs/experiments/paper2_fulltable" / f"{seq}_baseline.yaml").read_text())
        b = strip(p.read_text())
        assert a.replace(f"{seq}_baseline", "<SAVE>") == b.replace(f"r33_rebase_baseline_{seq}", "<SAVE>"), \
            f"r33_rebase_baseline_{seq}: 与原 baseline 臂不一致"

        # --- gate ---
        p = ROOT / "configs/experiments/paper2_fulltable" / f"r33_rebase_gate_{seq}.yaml"
        assert p.exists(), f"missing {p}"
        cfg = _load_merged(p)
        assert cfg["SWBA"]["enabled"] is True
        assert cfg["SWBA"]["swba_max_static_conf"] == 0.38, \
            f"r33_rebase_gate_{seq}: gate must stay 0.38"
        a = strip((ROOT / "configs/experiments/paper2_fulltable" /
                   f"r32_regate038_{seq}.yaml").read_text())
        b = strip(p.read_text())
        assert a.replace(f"r32_regate038_{seq}", "<SAVE>") == b.replace(f"r33_rebase_gate_{seq}", "<SAVE>"), \
            f"r33_rebase_gate_{seq}: 与 r32_regate038 不一致（应仅 save_dir 异 = 同 config 复制）"

        # --- swbaonly ---
        p = ROOT / "configs/experiments/paper2_fulltable" / f"r33_rebase_swbaonly_{seq}.yaml"
        assert p.exists(), f"missing {p}"
        cfg = _load_merged(p)
        assert cfg["SWBA"]["enabled"] is True
        assert "LoopClosure" not in strip(p.read_text()), \
            f"r33_rebase_swbaonly_{seq}: 不得含 LoopClosure 块（该臂=仅 SWBA）"
        old = ROOT / "configs/experiments/paper2_fulltable" / f"{seq}_swbaonly.yaml"
        if old.exists():
            a = strip(old.read_text())
            ref, ra, rb = a, f"{seq}_swbaonly", f"r33_rebase_swbaonly_{seq}"
        else:
            # 派生自同批 final：去掉 LoopClosure 后应逐字相同
            ref = nolc(strip((ROOT / "configs/experiments/paper2_fulltable" /
                              f"r33_rebase_final_{seq}.yaml").read_text()))
            ra, rb = f"r33_rebase_final_{seq}", f"r33_rebase_swbaonly_{seq}"
        b = strip(p.read_text())
        assert ref.replace(ra, "<SAVE>") == b.replace(rb, "<SAVE>"), \
            f"r33_rebase_swbaonly_{seq}: 与派生源不一致（应=final 去 LoopClosure）"


def test_baseline_is_final_minus_layers():
    """基线 = final 去掉 SWBA/LoopClosure 两块，其余逐字段一致（条件配对）。"""
    for seq in SEQS:
        final = open(ROOT / "configs/experiments/paper2_fulltable" / f"{seq}_final.yaml").read()
        base = open(ROOT / "configs/experiments/paper2_fulltable" / f"{seq}_baseline.yaml").read()
        strip = final.replace("SWBA:\n  enabled: true\n\n", "")
        import re
        strip = re.sub(r"LoopClosure:\n(?:  .*\n)+\n", "", strip)
        strip = strip.replace(f"{seq}_final", f"{seq}_baseline")
        # 头注释不同是允许的；比对结构部分
        assert strip.split("inherit_from:")[1] == base.split("inherit_from:")[1], \
            f"{seq}: baseline diverges from final beyond the two layers"
