"""P0 embrace_online 探针门禁（prereg_P0_embrace_online.md §8 先锁的最低单测集；纯逻辑，不需 GPU）。

覆盖（prereg §8）：
  ① 体素去重正确性（同帧重插不重复计数）；
  ② ρ 梯度方向数值例（无支持 ⇒ 稀疏先验压低；有支持 ⇒ 数据梯度可抵消先验）；
  ③ 滚动窗轮转取样确定性；
  ④ 阴性对照 FAIL 例（合成"平移后仍改善"的判据机输入 ⇒ 判 VOID=仪器无效；正常对照 ⇒ 放行）；
  ⑤ 冷启动帧剔除（≤ t0 的帧不进因果配对）；
  ⑥ config 与 prereg/coverage 工件的锁定参数一致（防跑完改判据）。

用法：/data/conda_envs/monogs-ours/bin/python -m pytest tests/embrace_dyn/test_dyn_probe_online.py -v
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


probe = _load("dyn_probe", "scripts/02_analysis/dyn_probe.py")
judge_p0 = _load("judge_p0", "scripts/embrace_dyn/judge_p0.py")

EV = REPO / "results/embrace_online/evidence"
CFG_PT2 = REPO / "configs/experiments/embrace_online/probe_pt2_online.yaml"
CFG_BAL = REPO / "configs/experiments/embrace_online/probe_balloon_online.yaml"


# ── ① 体素去重 ────────────────────────────────────────────────────────────────
def test_voxel_dedup_no_reinsert_same_voxels():
    # 显式远距点（避免随机点位移后与他点原体素碰撞——那是正确去重行为，非本测项）
    pts = np.array([[0.005, 0.005, 0.005], [0.500, 0.500, 0.500],
                    [0.900, 0.100, 0.400]], dtype=np.float64)
    occ = set()
    keep1, keys1 = probe.voxel_dedup_mask(pts, occ, voxel=0.02)
    assert keep1.all(), "空占用表 ⇒ 全部保留"
    occ |= {tuple(k) for k in keys1}
    keep2, _ = probe.voxel_dedup_mask(pts, occ, voxel=0.02)
    assert not keep2.any(), "同帧重插 ⇒ 体素已占据，不得重复计数"
    keep3, _ = probe.voxel_dedup_mask(pts + 0.05, occ, voxel=0.02)
    assert keep3.all(), "位移 0.05 = 2.5 体素且点间距 ≫ 0.05 ⇒ 全部落入新体素"
    keep4, _ = probe.voxel_dedup_mask(pts + 0.001, occ, voxel=0.02)
    assert not keep4.any(), "位移 0.001 < 体素 0.02 ⇒ 同体素，去重生效"


# ── ② ρ 梯度方向 ─────────────────────────────────────────────────────────────
def _rho_after_steps(rho0, pkg_fn, gt_image, gt_depth, steps, lr=0.05, lam=0.01):
    """对合成 pkg 反复走 online_step_loss 的手动 SGD（梯度方向测试，不涉 Adam/渲染器）。"""
    import torch
    rho = torch.nn.Parameter(torch.full((4, 1), float(rho0), dtype=torch.float32))
    d = {"rho": rho}
    for _ in range(steps):
        pkg = pkg_fn(rho)
        loss = probe.online_step_loss(pkg, gt_image, gt_depth, d, lam_rho=lam)
        loss.backward()
        with torch.no_grad():
            rho -= lr * rho.grad
        rho.grad = None
    return float(torch.sigmoid(rho.detach()).mean())


def test_rho_retires_without_support_but_survives_with_support():
    import torch
    torch.manual_seed(0)
    gt = torch.zeros(1, 3, 4, 4)          # 全零 GT 图（有效像素 = 全图）
    gt[0, 0, 0, 0] = 1.0                  # 单个非零像素，避免全零退化
    gd = torch.full((4, 4), 2.0)          # 有效深度 2m（(H,W)，与渲染 squeeze 后同形；深度项恒 0）
    # 场景 A（无支持）：渲染恒等 GT ⇒ 损失只剩稀疏先验（λ 放大缩短数值行程）⇒ σ(ρ) 净下降
    pkg_const = {"render": gt.clone(), "depth": gd.clone()}
    rho_a = _rho_after_steps(probe._logit(0.9), lambda r: pkg_const, gt, gd,
                             steps=600, lr=0.05, lam=1.0)
    assert rho_a < 0.85, f"无支持时 ρ 应被稀疏先验压低（实测 {rho_a:.3f}）"
    # 场景 B（有支持）：渲染 = GT·σ(ρ)（梯度可流经渲染项；λ 取小 ⇒ 数据梯度占优）⇒ σ(ρ) 净上升
    def pkg_support(rho):
        return {"render": gt * torch.sigmoid(rho).mean(), "depth": gd.clone()}
    rho_b = _rho_after_steps(probe._logit(0.9), pkg_support, gt, gd,
                             steps=300, lr=0.05, lam=0.001)
    assert rho_b > 0.91, f"有支持时 ρ 应被数据梯度撑住（实测 {rho_b:.3f}）"


# ── ③ 滚动窗轮转确定性 ────────────────────────────────────────────────────────
def test_rolling_window_deterministic_and_covers():
    a = [probe.rolling_window_frame(j=100, t0=97, window=4, steps_pf=10, s=s) for s in range(10)]
    b = [probe.rolling_window_frame(j=100, t0=97, window=4, steps_pf=10, s=s) for s in range(10)]
    assert a == b, "同参数必须逐位一致（确定性）"
    assert set(a) == {97, 98, 99, 100}, "10 步内应覆盖整个滚动窗"
    assert a[0] == 97  # (100*10+0) % 4 = 0 ⇒ 窗内最老帧
    assert probe.rolling_window_frame(j=98, t0=97, window=4, steps_pf=10, s=0) == 97
    assert probe.rolling_window_frame(j=97, t0=97, window=4, steps_pf=10, s=0) == 97
    assert probe.rolling_window_frame(j=100, t0=100, window=4, steps_pf=10, s=0) == 100


# ── ④ 阴性对照 FAIL 例（判据机层） ────────────────────────────────────────────
def _mk_rec(frame, bad_psnr, dl1, static, px, n_dyn):
    return {"frame": frame, "dyn_bad_psnr": bad_psnr, "dyn_bad_dl1_cm": dl1,
            "static_psnr": static, "dyn_bad_px": px, "n_dyn": n_dyn}


def _mk_results(p0o_delta, ctrl_delta, ctrl_ratio=1.3, t0=10, with_anchor=False):
    """P1 基线 20 dB；P0o = 20 + p0o_delta；C-o = 20 + ctrl_delta（dl1 比值 = ctrl_ratio）。"""
    frames = [11, 12, 13, 14]
    p1 = [_mk_rec(f, 20.0, 20.0, 30.0, 500, 0) for f in frames]
    p0o = [_mk_rec(f, 20.0 + p0o_delta, 20.0 * (1 - 0.3), 30.0, 500, 900) for f in frames]
    co = [_mk_rec(f, 20.0 + ctrl_delta, 20.0 * ctrl_ratio, 29.9, 500, 900) for f in frames]
    p2 = [_mk_rec(f, 20.0 + 10.0, 10.0, 30.0, 500, 3500) for f in frames]
    arms = {"P1": p1, "P0o": p0o, "C-o": co, "P2": p2}
    if with_anchor:  # C- = P2 型臂 + 0.30m 错位（历史仪器检验形态）
        arms["C-"] = [_mk_rec(f, 20.0 + 1.0, 20.0 * 1.4, 30.0, 500, 3500) for f in frames]
    return {"t0_frame": t0, "arms": {"gate": arms},
            "meta": {"gate": {"n_static": 10000,
                              "online_vitality": {"P0o": {
                                  "inserted_total": 900, "evicted_total": 5,
                                  "cap_hits": 0, "buf_final": 895, "rho_med_final": 0.5,
                                  "log": [{"frame": 11, "rho_med": 0.89},
                                          {"frame": 14, "rho_med": 0.5}]}}}}}


def test_negative_control_that_still_improves_voids_batch():
    """合成"平移后仍 ≥+2.5dB"的输入 ⇒ 判据机必须判 VOID（仪器无效，prereg J7）。"""
    res = _mk_results(p0o_delta=3.0, ctrl_delta=3.0, ctrl_ratio=1.3)
    out = judge_p0.judge([(res, {"sequence": "person_tracking2"})])
    assert out["exit"] == "VOID", out["exit_reason"]
    m = out["per_map"]["person_tracking2:gate"]
    assert m["j7_negative_control"]["fails_main"] is False
    assert m["j7_negative_control"]["instrument_detects"] is True


def test_negative_control_that_fails_main_allows_pass():
    """冒烟标定场景（prereg §9 修订）：C-o 平移后深度比值 0.90 < 1.15（canonical M_bad 基线
    误差 41.8cm 下 0.30m 不可分辨）但 PSNR 主判 FAIL ⇒ 不得 VOID；主域+泛化门全过 ⇒ PASS。"""
    res = _mk_results(p0o_delta=3.0, ctrl_delta=0.2, ctrl_ratio=0.9, with_anchor=True)
    gen = _mk_results(p0o_delta=0.5, ctrl_delta=0.2, ctrl_ratio=0.9)
    out = judge_p0.judge([(res, {"sequence": "person_tracking2"}),
                          (gen, {"sequence": "balloon", "generality_sequence": "balloon"})])
    assert out["per_map"]["person_tracking2:gate"]["j7_negative_control"]["fails_main"] is True
    # C- 锚在 canonical 仪器上可分辨（1.4 ≥ 1.15）⇒ 仪器判别力由锚臂证明
    assert out["per_map"]["person_tracking2:gate"]["j7b_instrument_anchor_C_"]["resolves_shift"] is True
    assert out["main_tags"] == ["person_tracking2:gate"]
    assert out["generality_tags"] == ["balloon:gate"]
    assert out["exit"] == "PASS", out["exit_reason"]


def test_instrument_anchor_reported_but_not_exit_determining():
    """C- 锚分辨力不足（<1.15）⇒ 只作诊断读数，不得单独触发 VOID/FAIL。"""
    res = _mk_results(p0o_delta=3.0, ctrl_delta=0.2, ctrl_ratio=0.9, with_anchor=True)
    res["arms"]["gate"]["C-"] = [_mk_rec(f, 20.0 + 1.0, 20.0 * 0.95, 30.0, 500, 3500)
                                 for f in [11, 12, 13, 14]]
    gen = _mk_results(p0o_delta=0.5, ctrl_delta=0.2, ctrl_ratio=0.9)
    out = judge_p0.judge([(res, {"sequence": "person_tracking2"}),
                          (gen, {"sequence": "balloon", "generality_sequence": "balloon"})])
    assert out["per_map"]["person_tracking2:gate"]["j7b_instrument_anchor_C_"]["resolves_shift"] is False
    assert out["exit"] == "PASS", out["exit_reason"]


def test_judge_thresholds_match_prereg():
    assert judge_p0.MAIN_PASS_DB == 2.5 and judge_p0.BOUND_LO_DB == 1.0
    assert judge_p0.STATIC_GATE_DB == -0.65 and judge_p0.COST_LINE == 0.15
    assert judge_p0.CTRL_RATIO_MIN == 1.15


# ── ⑤ 冷启动帧剔除 ────────────────────────────────────────────────────────────
def test_cold_start_frames_excluded_from_pairing():
    res = _mk_results(p0o_delta=3.0, ctrl_delta=0.2, t0=12)
    # 原始帧 11/12 ≤ t0 ⇒ 冷启动（P0o 侧给 cold_start 记录，无指标）；再补一个 ≤t0 的 P1 记录
    res["arms"]["gate"]["P1"] += [_mk_rec(10, 20.0, 20.0, 30.0, 500, 0)]
    res["arms"]["gate"]["P0o"] += [{"frame": 10, "cold_start": True},
                                   {"frame": 11, "cold_start": True},
                                   {"frame": 12, "cold_start": True}]
    m = judge_p0.judge_map(res["arms"]["gate"], res["meta"]["gate"], t0=12, domain="main")
    assert m["n_paired"] == 2, "≤ t0 的帧（10/11/12）不得进入因果配对，只余 13/14"
    assert m["j6_judgeable"] is True


def test_evict_to_cap_preserves_all_keys():
    """回归（2026-09-25 远程批事故）：逐出重建 self.d 不得丢 "K"——否则下次 _concat KeyError。"""
    import torch
    buf = probe.OnlineBuffer.__new__(probe.OnlineBuffer)  # 绕过需要 run/pc 的 __init__
    n = 10
    buf.d = {
        "xyz": torch.nn.Parameter(torch.zeros(n, 3)), "log_scale": torch.nn.Parameter(torch.zeros(n, 1)),
        "rot": torch.nn.Parameter(torch.zeros(n, 4)), "opa": torch.nn.Parameter(torch.zeros(n, 1)),
        "dc": torch.nn.Parameter(torch.zeros(n, 1, 3)), "rest": torch.zeros(n, 3, 3),
        "rho": torch.nn.Parameter(torch.zeros(n, 1)), "K": 4,
    }
    buf.cap = 5
    buf.evicted_total = 0
    buf.cap_hits = 0
    buf.opt = None
    removed = buf._evict_to_cap()
    assert removed == 5 and buf.d["K"] == 4
    assert buf.d["xyz"].shape[0] == 5 and buf.d["rho"].shape[0] == 5
    assert buf.d["rest"].shape[0] == 5
    # 模拟 _concat 对逐出后缓冲的再插入路径（K 必须可得）
    merged_k = buf.d["K"]
    assert merged_k == 4
    assert buf.evicted_total == 5 and buf.cap_hits == 1


# ── ⑥ config 锁定一致性 ───────────────────────────────────────────────────────
@pytest.mark.parametrize("cfgp,covp", [
    (CFG_PT2, EV / "coverage_pt2_canonical.json"),
    (CFG_BAL, EV / "coverage_balloon_canonical.json"),
])
def test_config_matches_coverage_and_prereg(cfgp, covp):
    cfg = yaml.safe_load(open(cfgp))
    cov = json.load(open(covp))
    assert cfg["frames"] == cov["selected_frames"], "帧集必须 = coverage 工件（不得事后增删）"
    assert cfg["t0_frame"] == cov["t0_frame"]
    oc = cfg["online"]
    assert oc["voxel"] == 0.02 and oc["cap"] == 60000 and oc["lam_rho"] == 0.01
    assert oc["window"] == 4 and oc["steps_per_frame"] == 10 and oc["rho_init"] == 0.9
    assert oc["lr_rho"] == 5.0e-2 and oc["shift_cam_m"] == [0.30, 0.0, 0.0]
    assert cfg["lrs"] == {"xyz": 5.0e-4, "scale": 5.0e-3, "rot": 1.0e-3,
                          "opa": 5.0e-2, "dc": 5.0e-3}, "lr 沿用历史四轮（prereg §3.1）"
    assert cfg["mask_subdir"] == "auto", "P0 必须走 canonical 掩码（测量口径 #3）"
    assert cfg["unproj_stride"] == 3 and cfg["fit_iters"] == 300
    assert set(cfg["arms"]) == {"P1", "P2", "C-", "P0o", "P0n", "C-o"}, \
        "C- 锚臂必须在位（prereg §9 修订：canonical 仪器判别力读数）"


def test_prereg_and_judge_source_committed():
    assert (EV / "prereg_P0_embrace_online.md").exists()
    assert (REPO / "scripts/embrace_dyn/judge_p0.py").exists()
    assert "2.5" in (EV / "prereg_P0_embrace_online.md").read_text()
