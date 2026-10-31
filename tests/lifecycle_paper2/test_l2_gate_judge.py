"""test_l2_gate_judge.py — L2 gate 泛化批判据机门禁。

覆盖（prereg_L2_gate.md §3 的判据形状契约）：
① --selftest 合成数四重校验（负方向 / 幅度地板 / 对调两臂 / 确认分支同号）通过；
② judge_seq 的判据形状：见效 ⟺ Δ<0 ∧ |Δ|>max(1.19, off_sd)（合成数据直验，不接渲染工件）；
③ 缺失渲染工件时判真实批返回 rc=2（不报假判）。
"""
import statistics
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "02_analysis"))

import l2_gate_judge as L2  # noqa: E402
import l1b_gate_judge as L1B  # noqa: E402


def test_selftest_rc0():
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "02_analysis" /
                                            "l2_gate_judge.py"), "--selftest"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "selftest OK" in r.stdout


def test_judge_seq_shape_on_synthetic(tmp_path, monkeypatch):
    """用合成 render 工件直验判据形状（方向分支 + 幅度地板），不经真实渲染目录。"""
    import json
    root = tmp_path / "lifecycle_paper2"
    root.mkdir(parents=True)

    def w(tpl, freshvac):
        d = root / tpl.format(seed=0)
        d.mkdir(parents=True, exist_ok=True)
        (d / "render_metrics.json").write_text(json.dumps(
            {"mean_freshvac_ghost_excess_depth_l1_cm": freshvac,
             "mean_static_psnr": 20.0, "n_frames": 17}))

    seq = "person_tracking2"
    # off 3 seed（阈值 sd 源）：sd ≈ 0.5 ⇒ 门槛 = 地板 1.19
    for s, v in zip((0, 1, 2), (4.0, 4.5, 5.0)):
        w(f"render_L3_{seq}_off_s{s}_canon", v)
    w(f"render_L3_{seq}_exit_s0_canon", 4.0)
    monkeypatch.setattr(L1B, "ROOT", str(root))

    # 正例：Δ = −2.0 ⇒ 见效
    w(f"render_L2_{seq}_gate_s0_canon", 2.0)
    r = L2.judge_seq(seq, [0])
    assert r["judgeable"] and r["effect"] is True
    assert abs(r["threshold"] - max(1.19, statistics.stdev([4.0, 4.5, 5.0]))) < 1e-9

    # 负对照 1：方向反（gate 更差）⇒ 不见效
    w(f"render_L2_{seq}_gate_s0_canon", 6.0)
    r = L2.judge_seq(seq, [0])
    assert r["judgeable"] and r["effect"] is False and r["sign_ok"] is False

    # 负对照 2：方向对但幅度不足（Δ = −0.5 < 地板）⇒ 不见效
    w(f"render_L2_{seq}_gate_s0_canon", 3.5)
    r = L2.judge_seq(seq, [0])
    assert r["judgeable"] and r["effect"] is False and r["mag_ok"] is False


def test_missing_artifacts_rc2(monkeypatch, tmp_path):
    """缺渲染工件时必须报缺（rc=2），不得给出任何判定。

    2026-09-22 前本测试依赖"本地尚无 L2 工件"的环境状态；工件拉回后改为
    monkeypatch ROOT 指向空目录，对缺工件分支做确定性测试（不再随环境漂移）。
    """
    (tmp_path / "lifecycle_paper2").mkdir()
    monkeypatch.setattr(L1B, "ROOT", str(tmp_path / "lifecycle_paper2"))
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "02_analysis" /
                                            "l2_gate_judge.py")],
                       capture_output=True, text=True)
    # 子进程不受 monkeypatch 影响 ⇒ 直接调函数验证分支（子进程级断言退化为冒烟）
    rc = L2.run_batch()
    assert rc == 2
    assert r.returncode in (0, 2)  # 冒烟：子进程能跑（本地有工件则 0）
