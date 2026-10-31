"""test_l1d_stacked_judge.py — L1d 叠加批判据机门禁。

覆盖（prereg_L1d_stacked.md §3-§5 的判据形状契约）：
① --selftest 合成数校验（三负对照 + 诊断三形态 inert/race/fired + 非单调拒绝）；
② judge_stacked 判据形状：PASS ⟺ ∀3 seeds Δ<0 ∧ |mean|>max(1.19, off_sd)
   （合成 render 工件直验，不经真实渲染目录）；
③ 缺失渲染工件时判真实批返回 rc=2（不报假判）；
④ diagnose_ratchet 语义 = prereg §5 两种失败形态预锁判读（程序化，禁手抄）。
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "02_analysis"))

import l1d_stacked_judge as L1D  # noqa: E402
import l1b_gate_judge as L1B  # noqa: E402


def test_selftest_rc0():
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "02_analysis" /
                                            "l1d_stacked_judge.py"), "--selftest"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "selftest OK" in r.stdout


def test_judge_stacked_shape_on_synthetic(tmp_path, monkeypatch):
    """合成 render 工件直验判据形状（∀3 负分支 + 幅度地板），不经真实渲染目录。"""
    import json
    import statistics
    root = tmp_path / "lifecycle_paper2"
    root.mkdir(parents=True)

    def w(tpl, freshvac):
        d = root / tpl.format(seed=0)
        d.mkdir(parents=True, exist_ok=True)
        (d / "render_metrics.json").write_text(json.dumps(
            {"mean_freshvac_ghost_excess_depth_l1_cm": freshvac,
             "mean_static_psnr": 20.0, "n_frames": 17}))

    # off 3 seed（阈值 sd 源）：sd≈0.5 ⇒ 门槛 = 地板 1.19；exit 3 seed
    for s, v in zip((0, 1, 2), (4.0, 4.5, 5.0)):
        w(L1D.tpl_off(s), v)
        w(L1D.tpl_exit(s), v + 0.1)
    monkeypatch.setattr(L1B, "ROOT", str(root))  # load_render 经 L1B.ROOT 解析
    # exit freshvac 值
    ex = [L1B.load_render(L1D.tpl_exit(s), s)["freshvac"] for s in (0, 1, 2)]
    sd = L1D.off_sd()

    # 正例：Δ = −2.0 全 3 seed ⇒ PASS
    for s in (0, 1, 2):
        w(L1D.tpl_stacked(s), ex[s] - 2.0)
    stacked = [L1B.load_render(L1D.tpl_stacked(s), s)["freshvac"] for s in (0, 1, 2)]
    m = L1D.judge_stacked(stacked, ex, sd)
    assert m["judgeable"] and m["PASS"] is True and m["n_neg"] == 3
    assert abs(m["threshold"] - max(1.19, statistics.stdev(
        [L1B.load_render(L1D.tpl_off(s), s)["freshvac"] for s in (0, 1, 2)]))) < 1e-9

    # 负对照 1：对调两臂 ⇒ 全正 ⇒ False
    assert L1D.judge_stacked(ex, stacked, sd)["PASS"] is False
    # 负对照 2：2/3 负（差一个：seed1 Δ=+1.0 正）⇒ prereg ∀3 ⇒ False
    m23 = L1D.judge_stacked([stacked[0], ex[1] + 1.0, stacked[2]], ex, sd)
    assert m23["n_neg"] == 2 and m23["PASS"] is False
    # 负对照 3：方向对幅度不足（Δ=−0.5 < 地板）⇒ False
    for s in (0, 1, 2):
        w(L1D.tpl_stacked(s), ex[s] - 0.5)
    stacked2 = [L1B.load_render(L1D.tpl_stacked(s), s)["freshvac"] for s in (0, 1, 2)]
    m3 = L1D.judge_stacked(stacked2, ex, sd)
    assert m3["judgeable"] and m3["sign_ok"] is True and m3["mag_ok"] is False
    assert m3["PASS"] is False


def test_missing_artifacts_rc2(monkeypatch, tmp_path):
    """缺渲染工件时必须报缺（rc=2），不得给出任何判定（monkeypatch 空目录，确定性）。"""
    (tmp_path / "lifecycle_paper2").mkdir()
    monkeypatch.setattr(L1B, "ROOT", str(tmp_path / "lifecycle_paper2"))
    rc = L1D.run_batch()
    assert rc == 2


def test_diagnose_ratchet_prereg5_forms():
    """prereg §5 两种失败形态 + 点火形态的预锁判读（语义机械应用）。"""
    # 形态 inert：计数器全零
    d0 = L1D.diagnose_ratchet(
        [{"kf": 5, "capped": 0, "a_min": 0.22}],
        {"alpha_carve_total": 0, "occ_decay_events_total": 0})
    assert "combination_inert" in d0["failure_form"]
    # 形态 race：棘轮下行穿阈但 carve=0
    series = [{"kf": k, "capped": 10, "a_min": a} for k, a in
              zip((5, 10, 15, 20, 25), (0.22, 0.198, 0.178, 0.16, 0.145))]
    d1 = L1D.diagnose_ratchet(series, {"alpha_carve_total": 0})
    assert d1["D1_monotonic_cross"] and not d1["D2_carve_first_fire"]
    assert "window_race_failure" in d1["failure_form"]
    # 形态 fired：carve>0
    d2 = L1D.diagnose_ratchet(series, {"alpha_carve_total": 7})
    assert d2["D2_carve_first_fire"] and "carve_fired" in d2["failure_form"]
