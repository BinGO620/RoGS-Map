#!/usr/bin/env python3
"""test_l1f_obsdebt_judge.py — L1f 判据机的形状/负对照/缺件测试。

镜像 `test_l1d_stacked_judge.py` 的 fixture 风格：tmp_path 合成工件 + monkeypatch
判据机模块 ROOT。判据权威 = prereg_L1f_obsdebt §3（median-of-medians < −1.48cm 且
≥2/3 seed 为负）。**不 import utils.slam_backend**（冷导入实测 ~242s，会拖死 pytest）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "02_analysis"))
import l1f_obsdebt_judge as J  # noqa: E402

FRAMES = [50, 76, 102, 128, 154, 180]  # 合成 6 帧（真实 17 帧由帧集管，形状无关）


def _write_rescore(root: Path, rtag: str, vals: dict[int, float]) -> None:
    """写一份 rescore JSON（三参照同值，供形状/聚合测试）。Δ = arm − ctrl 由调用方设定。"""
    d = root / "instrument_v2" / "rescore"
    d.mkdir(parents=True, exist_ok=True)
    per = []
    for i, fr in enumerate(FRAMES):
        v = vals[i]
        per.append({"frame": fr, "exc_full_cm": v, "exc_ring_cm": v, "exc_m3_cm": v})
    (d / f"rescore_{rtag}_canon.json").write_text(json.dumps({
        "per_frame": per, "band_used": 0.15,
        "support_px_median": {"static_bg": 1000, "ring": 2000, "vac": 3000},
    }))


def _write_metrics(root: Path, rtag: str, psnr: float = 18.0, cov: float = 1.0,
                   n_frames: int = 17) -> None:
    d = root / f"render_{rtag}_canon"
    d.mkdir(parents=True, exist_ok=True)
    (d / "render_metrics.json").write_text(json.dumps({
        "mean_static_psnr": psnr, "mean_static_coverage": cov,
        "n_frames": n_frames, "mask_validity": "canonical",
    }))


def _write_tables(root: Path, tag: str, ate_by_seed: dict[int, float],
                  gauss_by_seed: dict[int, int] | None = None) -> None:
    d = root / tag / "tables"
    d.mkdir(parents=True, exist_ok=True)
    hdr = "method,dataset,sequence,seed,run_id,status,notes,ate_rmse_cm\n"
    rows = "".join(f"Combined-Prune,BONN,seq,{s},{s},OK,x,{v}\n" for s, v in ate_by_seed.items())
    (d / "tracking_raw.csv").write_text(hdr + rows)
    if gauss_by_seed is not None:
        h2 = "method,dataset,sequence,seed,num_gaussians\n"
        r2 = "".join(f"Combined-P,BONN,seq,{s},{g}\n" for s, g in gauss_by_seed.items())
        (d / "efficiency_raw.csv").write_text(h2 + r2)


def _write_console(root: Path, runtag: str, seed: int, text: str) -> None:
    d = root / runtag / "datasets_bonn" / "cfg" / f"seed_{seed}" / "2026-09-24-00-00-00"
    d.mkdir(parents=True, exist_ok=True)
    (d / "console.log").write_text(text)


# ────────────────────────── 纯判据（合成数）──────────────────────────
def test_judge_main_pass_three_seeds_negative():
    good = {0: [-2.0, -1.0, -3.0], 1: [-1.6, -2.2, -1.8], 2: [-1.9, -2.5, -1.5]}
    m = J.judge_main(good)
    assert m["PASS"] is True
    assert m["n_neg"] == 3
    assert m["median_of_medians"] < -J.THRESHOLD_CM
    assert m["sign_ok"] and m["mag_ok"]


def test_judge_main_negative_control_swapped_arms():
    good = {0: [-2.0, -1.0, -3.0], 1: [-1.6, -2.2, -1.8], 2: [-1.9, -2.5, -1.5]}
    m = J.judge_main({s: [-x for x in v] for s, v in good.items()})
    assert m["PASS"] is False and m["n_neg"] == 0


def test_judge_main_negative_control_magnitude_below_floor():
    # 同号（全负）但 |median-of-medians| < 1.48 ⇒ 必须 False（幅度门）
    m = J.judge_main({0: [-0.4, -0.5], 1: [-0.3, -0.6], 2: [-0.5, -0.2]})
    assert m["PASS"] is False and m["sign_ok"] is True and m["mag_ok"] is False


def test_judge_main_negative_control_mixed_direction():
    # 仅 1/3 seed 为负 ⇒ 方向门不过（prereg: ≥2/3 seed 同号）
    m = J.judge_main({0: [-2.0, -1.8], 1: [1.5, 2.0], 2: [1.2, 1.9]})
    assert m["PASS"] is False and m["n_neg"] == 1


def test_median_of_medians_reads_per_seed_then_across():
    # 逐 seed median = [−2.0, −3.0, −1.0] ⇒ mom = −2.0
    m = J.median_of_medians({0: [-1.0, -2.0, -5.0], 1: [-3.0, -3.0], 2: [-1.0, -1.0]})
    assert m["median_of_medians"] == pytest.approx(-2.0)
    assert m["seed_medians"] == [-2.0, -3.0, -1.0]


def test_leave_one_seed_out_is_fragile_when_at_floor():
    """诊断：6 seed 中恰 4 负（= 2/3 地板）⇒ 留一后 3/5 < 2/3 ⇒ PASS 崩。"""
    # 逐 seed median：4 负 2 正 ⇒ 6-seed PASS=True（mom<0 且 4≥4）
    meds = {0: [+2.0], 1: [+3.0], 2: [-2.0], 3: [-2.5], 4: [-2.2], 5: [-2.8]}
    j6 = J.judge_main(meds)
    assert j6["PASS"] is True and j6["n_neg"] == 4
    rob = J.leave_one_seed_out(meds)
    assert rob["available"] is True
    # 丢掉任一个负 seed ⇒ 3/5 不达 2/3 ⇒ PASS 变为 False
    assert rob["loo"]["2"]["PASS"] is False
    assert rob["loo"]["3"]["PASS"] is False
    assert rob["loo_pass_count"] == "2/6"      # 只剩丢正 seed 的两种情况仍 PASS
    assert rob["n_sign_flips"] == 2


def test_leave_one_seed_out_robust_when_solid():
    meds = {0: [-2.0], 1: [-2.0], 2: [-2.0], 3: [-2.0], 4: [-2.0], 5: [-2.0]}
    rob = J.leave_one_seed_out(meds)
    assert rob["loo_pass_count"] == "6/6"
    assert rob["across_seed_spread"] == 0.0


# ──────────────────── 归因诊断（关卡① 致命项：负号 vs 机制动作）────────────────────
def _console(path_root, runtag, seed, boost):
    d = path_root / runtag / "datasets_bonn" / "cfg" / f"seed_{seed}" / "ts"
    d.mkdir(parents=True, exist_ok=True)
    lines = "MonoGS: obsdebt KF 50: masked_px=1 voxels=1 table=1 total=1\n"
    if boost:
        lines += ("MonoGS: obsdebt-boost KF 95: new=1 d_hat_mean=1.000 "
                  "extra_steps=5 opt=independent-adam\n")
    (d / "console.log").write_text(lines)


def test_mechanism_active_seeds_splits_by_firing(tmp_path, monkeypatch):
    root = tmp_path / "lp2"
    root.mkdir(parents=True)
    monkeypatch.setattr(J, "ROOT", str(root))
    for s, b in [(0, True), (1, False), (2, True), (3, False)]:
        _console(root, "TAG", s, b)
    act, idle = J.mechanism_active_seeds("TAG", [0, 1, 2, 3])
    assert act == [0, 2] and idle == [1, 3]


def test_attribution_flags_noise_only_pass():
    """负号只落在零动作 seed ⇒ 机械 PASS 但 active_only 读数反向（不可归因）。"""
    # 6 seed：s0-3 机制动作、s4-5 零动作。逐 seed median：s0,s1 正、s2-s5 负
    medians = {0: +2.0, 1: +3.0, 2: -2.5, 3: -3.0, 4: -6.1, 5: -6.3}
    mech = J.judge_main({s: [v] for s, v in medians.items()})
    assert mech["PASS"] is True and mech["n_neg"] == 4      # 6-seed 机械 PASS
    active = [0, 1, 2, 3]
    act = J.judge_main({s: [medians[s]] for s in active})
    assert act["PASS"] is False                             # 限动作 seed ⇒ 翻回 FAIL
    assert act["n_neg"] == 2 and act["n_seed"] == 4          # 2/4 < 2/3


def test_attribution_ok_when_signal_on_active_seeds():
    """负号落在机制动作 seed 上 ⇒ 机械 PASS 与 active_only_PASS 同向。"""
    sub = {0: [-2.0], 1: [-2.0], 2: [1.0], 3: [-2.0]}
    mech = J.judge_main(sub)
    assert mech["PASS"] is True and mech["n_neg"] == 3
    act = J.judge_main({0: [-2.0], 1: [-2.0], 3: [-2.0]})
    assert act["PASS"] is True


# ────────────────────────── 可判性（DISCIPLINE「测量口径」2）──────────────────────────
def test_judgeability_ok_when_all_refs_available():
    a = {i: {"m3": 1.0, "full": 1.0, "ring": 1.0} for i in range(10)}
    b = dict(a)
    ok, diag = J.is_judgeable(a, b)
    assert ok is True and diag["n_common_frames"] == 10


def test_judgeability_false_when_ref_below_half():
    a = {i: {"m3": 1.0, "full": 1.0, "ring": 1.0} for i in range(10)}
    b = {i: {"m3": None, "full": 1.0, "ring": 1.0} for i in range(10)}
    ok, diag = J.is_judgeable(a, b)
    assert ok is False
    assert diag["per_ref_available"]["m3"] == "0/10"


# ────────────────────────── 点火正则（prereg §2b）──────────────────────────
def test_firing_regex_counts_only_fired_forms(tmp_path):
    p = tmp_path / "console.log"
    p.write_text(
        "MonoGS: obsdebt KF 50: masked_px=1 voxels=1 table=1 total=1\n"
        "MonoGS: obsdebt KF 55: masked_px=1 voxels=1 table=2 total=7\n"
        "MonoGS: obsdebt-boost KF 95: new=1 d_hat_mean=1.000 extra_steps=5 opt=independent-adam\n"
        "MonoGS: obsdebt-boost KF 100: SKIP -- ledger absent (obsdebt on but no debt recorded yet)\n"
        "MonoGS: obsdebt-boost skipped: element 0 of tensors does not require grad\n"
        "MonoGS: obsdebt-fill KF 60: vacated=10 kept=4 dropped=6 debt_max=3\n"
    )
    c = J.count_firing(str(p))
    assert c["ledger_lines"] == 2
    assert c["ledger_monotone"] is True
    assert c["boost_lines"] == 1          # SKIP 与 skipped 两种字面不误吞
    assert c["fill_lines"] == 1
    assert c["fill_kept_total"] == 4
    assert c["fill_kept_max"] == 4


def test_firing_all_zero_is_none(tmp_path, monkeypatch):
    root = tmp_path / "lp2"
    root.mkdir(parents=True)
    monkeypatch.setattr(J, "ROOT", str(root))
    _write_console(root, "L1f_balloon2_balloon2_exitfill_ctrl", 0, "MonoGS: nothing here\n")
    f = J.firing_of("L1f_balloon2_balloon2_exitfill_ctrl", 0)
    assert f["FIRING"] == "none"
    assert f["ledger_lines"] == 0 and f["boost_lines"] == 0 and f["fill_lines"] == 0


# ────────────────────────── 端到端（合成工件 + monkeypatch ROOT）──────────────────────────
def _seed_balloon2_fixture(root: Path, *, pass_case: bool = True) -> None:
    """合成 balloon2 主臂/对照工件；pass_case ⇒ Δ≈−2cm。"""
    for sd in (0, 1, 2):
        delta = -2.0 if pass_case else -0.4
        _write_rescore(root, f"L1f2_balloon2_obsdebt_s{sd}",
                       {i: 10.0 + delta for i in range(len(FRAMES))})
        _write_rescore(root, f"L1f_balloon2_exitfill_ctrl_s{sd}",
                       {i: 10.0 for i in range(len(FRAMES))})
        # 渲染件
        _write_metrics(root, f"L1f2_balloon2_obsdebt_s{sd}", psnr=18.0, cov=1.0)
        _write_metrics(root, f"L1f_balloon2_exitfill_ctrl_s{sd}", psnr=18.0, cov=1.0)
    _write_tables(root, J.MAIN_RUNTAG, {0: 5.3, 1: 5.4, 2: 5.2}, {0: 43000, 1: 47000, 2: 37000})
    _write_tables(root, J.CTRL_RUNTAG, {0: 5.25, 1: 5.16, 2: 5.19}, {0: 46300, 1: 54000, 2: 50000})
    for sd in (0, 1, 2):
        _write_tables(root, f"L3_balloon2_off_s{sd}", {sd: 5.4})
        _write_metrics(root, f"L3_balloon2_off_s{sd}", psnr=18.0, cov=1.0)
    # 点火日志
    for sd in (0, 1, 2):
        _write_console(root, J.MAIN_RUNTAG, sd,
                       "MonoGS: obsdebt KF 50: masked_px=1 voxels=1 table=1 total=1\n"
                       "MonoGS: obsdebt-boost KF 95: new=1 d_hat_mean=1.000 extra_steps=5 opt=independent-adam\n")
        _write_console(root, J.CTRL_RUNTAG, sd, "MonoGS: alpha-fill KF 50\n")


def test_end_to_end_pass_on_synthetic(tmp_path, monkeypatch):
    root = tmp_path / "lifecycle_paper2"
    root.mkdir(parents=True)
    monkeypatch.setattr(J, "ROOT", str(root))
    _seed_balloon2_fixture(root, pass_case=True)
    b2 = J.judge_balloon2([0, 1, 2])
    assert b2["judgeable"] is True
    assert b2["PASS"] is True
    assert b2["primary"]["median_of_medians"] == pytest.approx(-2.0)


def test_end_to_end_fail_below_threshold(tmp_path, monkeypatch):
    root = tmp_path / "lifecycle_paper2"
    root.mkdir(parents=True)
    monkeypatch.setattr(J, "ROOT", str(root))
    _seed_balloon2_fixture(root, pass_case=False)     # Δ = −0.4 ⇒ 幅度门不过
    b2 = J.judge_balloon2([0, 1, 2])
    assert b2["judgeable"] is True
    assert b2["PASS"] is False
    assert b2["primary"]["sign_ok"] is True and b2["primary"]["mag_ok"] is False


def test_end_to_end_missing_artifacts_not_judgeable(tmp_path, monkeypatch):
    root = tmp_path / "lifecycle_paper2"
    root.mkdir(parents=True)
    monkeypatch.setattr(J, "ROOT", str(root))
    b2 = J.judge_balloon2([0, 1, 2])
    assert b2["judgeable"] is False
    assert "缺失" in b2["reason"]


def test_batch_returns_rc2_when_artifacts_absent(tmp_path, monkeypatch):
    root = tmp_path / "lifecycle_paper2"
    root.mkdir(parents=True)
    monkeypatch.setattr(J, "ROOT", str(root))
    assert J.run_batch(confirm=False) == 2


def test_ate_gate_uses_seed_aware_rows(tmp_path, monkeypatch):
    """tag 级 CSV 含 3 seed 行时，必须按 seed 取（不得只读末行）。"""
    root = tmp_path / "lifecycle_paper2"
    root.mkdir(parents=True)
    monkeypatch.setattr(J, "ROOT", str(root))
    _write_tables(root, "L1f2_balloon2_obsdebt", {0: 5.0, 1: 9.0, 2: 5.1})
    got = J.load_ate("L1f2_balloon2_obsdebt")
    assert got == {0: 5.0, 1: 9.0, 2: 5.1}


def test_prim_guard_flags_inflation(tmp_path, monkeypatch):
    root = tmp_path / "lifecycle_paper2"
    root.mkdir(parents=True)
    monkeypatch.setattr(J, "ROOT", str(root))
    _write_tables(root, "L1f2_balloon2_obsdebt", {0: 5.0}, {0: 200000})
    _write_tables(root, "L1f_balloon2_balloon2_exitfill_ctrl", {0: 5.0}, {0: 50000})
    g = J.guard_prim(J.load_num_gaussians("L1f2_balloon2_obsdebt"),
                     J.load_num_gaussians("L1f_balloon2_balloon2_exitfill_ctrl"))
    assert g["ok"] is False and g["worst"] == pytest.approx(3.0)


def test_selftest_subprocess_rc0():
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "02_analysis" / "l1f_obsdebt_judge.py"),
         "--selftest"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "selftest OK" in r.stdout
