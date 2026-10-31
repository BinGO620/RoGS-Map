"""embrace_dyn 探针门禁（纯逻辑 + 工件断言，不需 GPU）。

覆盖：
  ① 判据机 `analyze_dyn_probe.py` 的规则实现（GO / NO-GO / PARTIAL / 仪器失效四态）；
  ② 探针配置 `probe_pt2.yaml` 与预注册 `prereg_dyn_probe.md` 的锁定参数一致
     （防"跑完改判据"与配置漂移）；
  ③ 已落盘证据的自洽（阳性对照 max|Δ|、判据机输出与报告一致、门禁状态未越权声明）；
  ④ 几何工具的正确性（`unproject_mask` 往返、`translate` 不就地修改、`PackedPC` 拼接形状）。

用法：/data/conda_envs/monogs-ours/bin/python -m pytest tests/embrace_dyn -v
"""
import importlib.util
import json
import re
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


analyzer = _load("analyze_dyn_probe", "scripts/02_analysis/analyze_dyn_probe.py")
probe = _load("dyn_probe", "scripts/02_analysis/dyn_probe.py")

EV = REPO / "results/embrace_dyn/evidence"
CFG = REPO / "configs/experiments/embrace_dyn/probe_pt2.yaml"
PREREG = EV / "prereg_dyn_probe.md"


# ── ①②④ 基础工具 ──

def test_translate_does_not_mutate_and_adds_delta():
    import torch
    d = {"xyz": torch.zeros(3, 3), "opa": torch.zeros(3, 1)}
    out = probe.translate(d, [0.1, 0.2, 0.3])
    assert torch.allclose(out["xyz"][0], torch.tensor([0.1, 0.2, 0.3]))
    assert torch.allclose(d["xyz"], torch.zeros(3, 3)), "translate 不得就地修改输入"
    assert out["opa"] is d["opa"], "未平移的参数应共享"


def test_dyn_tensors_ranges():
    import torch
    d = {"xyz": torch.zeros(2, 3), "log_scale": torch.zeros(2, 1),
         "rot": torch.tensor([[2.0, 0, 0, 0], [0, 3.0, 0, 0]]), "opa": torch.zeros(2, 1),
         "dc": torch.zeros(2, 1, 3), "rest": torch.zeros(2, 3, 3), "K": 4}
    t = probe.dyn_tensors(d)
    assert t["opacity"].shape == (2, 1) and float(t["opacity"].max()) < 1.0
    assert float(t["scaling"].min()) > 0
    assert torch.allclose(t["rotation"].norm(dim=1), torch.ones(2), atol=1e-6)
    assert t["features"].shape == (2, 4, 3)


def test_unproject_roundtrip_identity_pose():
    """掩码内像素 + 深度 → 世界点 → 回投，应落回原像素（单位位姿）。"""
    class DS:
        fx = fy = 100.0
        cx, cy = 160.0, 120.0
    class Run:
        dataset = DS()
        def frame_mask(self, idx):
            m = np.zeros((240, 320), bool)
            m[100:110, 150:160] = True
            return m
    import torch
    gt_depth = torch.full((240, 320), 2.0)
    gt_image = torch.ones(3, 240, 320)
    pts, cols = probe.unproject_mask(Run(), 0, gt_image, gt_depth, np.eye(4), stride=1)
    assert pts is not None and pts.shape[0] == 100
    z = pts[:, 2]
    u = DS.fx * pts[:, 0] / z + DS.cx
    v = DS.fy * pts[:, 1] / z + DS.cy
    # np.nonzero 行主序：每个 v 扫一遍 u ⇒ u 为 tile 而非 repeat
    assert np.allclose(np.round(u), np.tile(np.arange(150, 160), 10), atol=1e-3)
    assert np.allclose(z, 2.0, atol=1e-5)


# ── ② 配置 ↔ 预注册一致 ──

def _prereg_frames():
    txt = PREREG.read_text()
    m = re.search(r"\[2, 93, 122, 141, 178, 197, 243, 282, 309, 329, 347, 398, 421, 439, 512, 561\]", txt)
    assert m, "预注册里找不到帧清单"
    return m.group(0)


def test_config_frames_and_t0_match_prereg():
    import yaml
    cfg = yaml.safe_load(CFG.read_text())
    assert str(cfg["frames"]) == _prereg_frames(), "config 帧清单与预注册不一致"
    assert int(cfg["t0_frame"]) == 309
    txt = PREREG.read_text()
    assert "t0 = 309" in txt or "t0_frame: 309" in txt or "**烘焙参考帧 t0 = 309**" in txt
    assert int(cfg["fit_iters"]) == 300 and "fit_iters=300" in txt
    assert float(cfg["control_shift_cam_m"][0]) == 0.30 and "0.30m" in txt
    assert int(cfg["unproj_stride"]) == 3 and "stride=3" in txt


def test_analyzer_thresholds_match_prereg():
    txt = PREREG.read_text()
    th = analyzer.TH
    assert th["ceiling_dl1_ratio"] == 0.70 and "≤ 0.70" in txt
    assert th["ceiling_psnr_gain_db"] == 2.0 and "+2.0 dB" in txt
    assert th["motion_dl1_ratio"] == 1.30 and "1.30" in txt
    assert th["instrument_dl1_ratio"] == 1.15 and "1.15" in txt
    assert th["cost_frac"] == 0.50 and "50%" in txt


# ── ① 判据机四态 ──

def _mk(means, far=None, t0=309, n_static=50000):
    recs = {}
    for arm, m in means.items():
        n = 3
        recs[arm] = [{"frame": t0 + 100 * (i + 1), "dyn_psnr": m["dyn_psnr"], "dyn_dl1_cm": m["dyn_dl1_cm"],
                      "static_psnr": m.get("static_psnr", 24.0), "full_psnr": m.get("full_psnr", 22.0),
                      "n_dyn": m.get("n_dyn", 0), "dyn_cov": 1.0, "ghost_excess_cm": 0.0} for i in range(n)]
        if far:
            for r in recs[arm]:
                r["dyn_dl1_cm"] = far.get(arm, m["dyn_dl1_cm"])
    return {"arms": {"m": recs}, "meta": {"m": {"n_static": n_static}}, "t0_frame": t0}


GOOD = {"P1": {"dyn_psnr": 20.8, "dyn_dl1_cm": 18.7, "static_psnr": 23.8, "full_psnr": 21.3},
        "P2": {"dyn_psnr": 31.1, "dyn_dl1_cm": 10.8, "static_psnr": 23.9, "full_psnr": 23.4, "n_dyn": 3500},
        "C-": {"dyn_psnr": 18.7, "dyn_dl1_cm": 19.1, "static_psnr": 20.1, "full_psnr": 19.3, "n_dyn": 3500},
        "P4": {"dyn_psnr": 20.4, "dyn_dl1_cm": 18.8, "static_psnr": 22.6, "full_psnr": 20.8, "n_dyn": 11906}}


def test_analyzer_go():
    j = analyzer.analyse(_mk(GOOD, far={"P4": 19.2}), "m")
    assert j["outcome"] == "GO", j["criteria"]


def test_analyzer_no_go_when_ceiling_missing():
    bad = {k: dict(v) for k, v in GOOD.items()}
    # 只破坏 PSNR 增益（保持 dl1 以不扰动仪器比值）：天花板仍不成立
    bad["P2"] = dict(bad["P2"], dyn_psnr=21.0)
    assert analyzer.analyse(_mk(bad, far={"P4": 19.2}), "m")["outcome"] == "NO-GO"


def test_analyzer_partial_when_motion_not_needed():
    bad = {k: dict(v) for k, v in GOOD.items()}
    bad["P4"] = dict(bad["P4"], dyn_dl1_cm=10.9)                  # 烘焙≈逐帧
    assert analyzer.analyse(_mk(bad, far={"P4": 10.9}), "m")["outcome"] == "PARTIAL"


def test_analyzer_instrument_invalid_takes_precedence():
    bad = {k: dict(v) for k, v in GOOD.items()}
    bad["C-"] = dict(bad["C-"], dyn_dl1_cm=11.0)                  # 错位也不劣化
    assert analyzer.analyse(_mk(bad, far={"P4": 19.2}), "m")["outcome"] == "INSTRUMENT-INVALID"


def test_analyzer_covers_six_prereg_criteria():
    """关卡① 致命项回归：预注册 §7 是六条判据，判据机必须全部实现。"""
    j = analyzer.analyse(_mk(GOOD, far={"P4": 19.2}), "m")
    for k in ("1_ceiling", "2_motion_necessity", "3_no_harm", "4_cost", "5_instrument",
              "6_positive_control"):
        assert k in j["criteria"], f"判据机缺 {k}"
    txt = PREREG.read_text()
    for item in ("1. **天花板", "2. **运动必要性", "3. **无伤", "4. **成本",
                 "5. **仪器有效", "6. **阳性对照"):
        assert item in txt, f"预注册缺条目 {item}"
    assert len(re.findall(r"^\d\. \*\*", txt, flags=re.M)) == 6, "预注册判据条目数不是 6"


def test_analyzer_consumes_previously_unread_columns():
    """关卡① 重大项回归：dyn_px / vacated_px / 逐帧拟合证据必须被消费。"""
    res = _mk(GOOD, far={"P4": 19.2})
    for arm in res["arms"]["m"]:
        for r in res["arms"]["m"][arm]:
            r["dyn_px"], r["vacated_px"] = 1000, 500
    res["arms"]["m"]["P2"][0]["fit"] = {"loss_first": 0.14, "loss_last": 0.03,
                                        "opa_mean_before": 0.5, "opa_mean_after": 0.7}
    j = analyzer.analyse(res, "m")
    assert j["support"]["P2"]["mean_dyn_px"] == 1000
    assert j["support"]["P2"]["mean_vacated_px"] == 500
    assert j["fit_evidence"]["P2"]["n_frames_with_fit"] == 1
    assert j["criteria"]["desc_dyn_cov"]["discriminative"] is False, "dyn_cov 零判别力必须被显式记录"


def test_analyzer_config_consistency_check():
    """results 里的锁定参数与配置不符时必须报出来（防参数漂移）。"""
    res = json.load(open(EV / "dyn_probe_results.json"))
    assert analyzer.check_config_consistency(res, str(CFG)) == []
    assert analyzer.check_config_consistency(dict(res, fit_iters=1), str(CFG))


def test_l2_repeatability_artifact_is_honest():
    """关卡① 重大项回归：L2 声明必须有工件，且不得声称含拟合臂逐位一致。"""
    d = json.load(open(EV / "l2_repeatability.json"))
    assert d["max_abs_delta_dyn_psnr_db"] <= 0.05
    assert all("P1" in x for x in d["arm1_bit_identical"]), "只有无拟合臂可声称逐位一致"
    assert len(d["rows"]) == 8


def test_frame_selection_is_reproducible():
    """选帧规则可复算（关卡① 无法验证项 3）。"""
    d = json.load(open(EV / "frame_coverage_pt2.json"))
    import yaml
    cfg = yaml.safe_load(CFG.read_text())
    assert d["selected_frames"] == cfg["frames"]
    assert d["t0_frame"] == cfg["t0_frame"]
    assert len(d["coverage_per_frame"]) == d["n_coverage_entries"]
    assert d["n_coverage_entries"] == min(d["n_frames_rgb"], d["n_frames_depth"])


# ── ③ 已落盘证据 ──

def test_positive_control_artifact():
    d = json.load(open(EV / "control_p1_vs_render_compare.json"))
    assert d["max_abs_delta_db"] <= 0.01, "阳性对照未通过：探针与 render_compare 不同口径"
    assert len(d["rows"]) == 8


def test_verdict_and_manifest_selfconsistent():
    v = json.load(open(EV / "dyn_probe_verdict.json"))
    for tag, j in v["judgments"].items():
        assert j["outcome"] in ("GO", "NO-GO", "PARTIAL", "INSTRUMENT-INVALID")
    man = json.load(open(EV / "manifest.json"))
    assert "prereg_dyn_probe.md" in man["prereg"]
    assert man["inputs"]["t0_frame"] == 309
    assert man["judgment"]["gate_map"]["outcome"] == v["judgments"]["gate"]["outcome"]


def test_verdict_gate_status_is_honest():
    """关卡① 未过时，裁决书必须显式声明为草稿（不得被当已收口引用）。"""
    txt = (EV / "verdict_dyn_probe.md").read_text()
    if "待过" in txt or "PENDING" in txt:
        assert "不得被当作已收口判决引用" in txt
    else:
        assert "slam-critic" in txt and "✅" in txt, "宣称已过却无关卡证据"


def test_report_numbers_match_json():
    """报告里的逐臂均值必须与原始 JSON 聚合一致（禁手工改数）。"""
    res = json.load(open(EV / "dyn_probe_results.json"))
    rep = (EV / "dyn_probe_report.md").read_text()
    for tag, arms in res["aggregate"].items():
        for arm, s in arms.items():
            if s.get("mean_dyn_psnr") is None:
                continue
            assert f"{s['mean_dyn_psnr']:.2f}" in rep, f"{tag}/{arm} dyn_psnr 未在报告中出现"
            assert f"{s['mean_dyn_dl1_cm']:.2f}" in rep, f"{tag}/{arm} dyn_dl1 未在报告中出现"


# ── 因果批（预注册 prereg_dyn_probe_causal.md）──

CAUSAL_PREREG = EV / "prereg_dyn_probe_causal.md"


def _mk_causal(r):
    """r = dict(arm -> (dyn_psnr, dyn_dl1_cm, static_psnr, full_psnr, n_dyn))"""
    arms, agg = {}, {}
    for arm, (p, d, st, fu, nd) in r.items():
        recs = [{"frame": 100 + 10 * i, "dyn_psnr": p, "dyn_dl1_cm": d, "static_psnr": st,
                 "full_psnr": fu, "n_dyn": nd, "dyn_cov": 1.0, "ghost_excess_cm": 0.0} for i in range(3)]
        if arm == "P2c":
            recs.append({"frame": 2, "cold_start": True})
        arms[arm] = recs
        agg[arm] = {"n": 3, "mean_dyn_psnr": p, "mean_dyn_dl1_cm": d, "mean_static_psnr": st,
                    "mean_full_psnr": fu, "mean_n_dyn": nd}
    return {"arms": {"m": arms}, "meta": {"m": {"n_static": 50000}}, "aggregate": {"m": agg}, "t0_frame": 309}


CAUSAL_GOOD = {"P1": (20.8, 18.7, 23.8, 21.3, 0), "P2": (31.1, 10.8, 23.9, 23.4, 3500),
               "P2c": (27.5, 13.5, 23.8, 22.6, 3200), "P2cv": (28.0, 13.0, 23.8, 22.8, 3200),
               "C-c": (18.7, 19.1, 20.1, 19.3, 3200)}


def test_causal_analyzer_go():
    j = analyzer.analyse_causal(_mk_causal(CAUSAL_GOOD), "m")
    assert j is not None and j["outcome"] == "GO", j and j["criteria"]
    assert j["cold_start_frames"] == [2]
    # retention = (18.7-13.0)/(18.7-10.8) = 0.721
    assert j["criteria"]["C1_causal_retention"]["retention_P2cv"] > 0.5


def test_causal_analyzer_no_go_when_retention_low():
    bad = dict(CAUSAL_GOOD, P2cv=(20.0, 18.0, 23.8, 21.0, 3200))
    j = analyzer.analyse_causal(_mk_causal(bad), "m")
    assert j["outcome"] == "NO-GO", j["criteria"]


def test_causal_analyzer_partial_when_harmful():
    bad = dict(CAUSAL_GOOD, P2cv=(28.0, 13.0, 22.0, 22.8, 3200))   # 静态区掉 1.8dB
    j = analyzer.analyse_causal(_mk_causal(bad), "m")
    assert j["outcome"] == "PARTIAL", j["criteria"]
    assert j["criteria"]["C3_no_harm"]["pass"] is False


def test_causal_analyzer_instrument_precedence():
    bad = dict(CAUSAL_GOOD, **{"C-c": (18.7, 13.2, 20.1, 19.3, 3200)})  # 错位不再劣化
    j = analyzer.analyse_causal(_mk_causal(bad), "m")
    assert j["outcome"] == "INSTRUMENT-INVALID", j["criteria"]


def test_causal_analyzer_returns_none_without_arms():
    assert analyzer.analyse_causal(_mk_causal({"P1": CAUSAL_GOOD["P1"]}), "m") is None


def test_causal_prereg_exists_and_locks_criteria():
    txt = CAUSAL_PREREG.read_text()
    for k in ("C1 因果保留率", "C2 速度项增益", "C3 无伤", "C4 成本", "C5 仪器有效"):
        assert k in txt, f"因果预注册缺 {k}"
    assert "retention" in txt and "0.50" in txt


def test_causal_config_matches_parent_locked_params():
    import yaml
    parent = yaml.safe_load(CFG.read_text())
    causal = yaml.safe_load((REPO / "configs/experiments/embrace_dyn/probe_pt2_causal.yaml").read_text())
    for k in ("frames", "t0_frame", "fit_iters", "unproj_stride", "lrs", "control_shift_cam_m"):
        assert parent[k] == causal[k], f"因果配置与父配置在 {k} 上不一致"
    assert {"P2c", "P2cv", "C-c"} <= set(causal["arms"])
    assert all("kf_log" in m for m in causal["maps"]), "因果配置必须给每张地图的 KF 日志来源"


def test_keyframes_parsed_from_consolelog():
    p = REPO / "results/paper2_fulltable/r33_rebase_gate_person_tracking2_seed0.consolelog"
    if not p.exists():
        pytest.skip("consolelog 不在本地")
    kfs = probe.keyframes_of(str(p))
    assert len(kfs) == 113 and kfs[0] == 5 and kfs[-1] == 565
    assert all(b - a == 5 for a, b in zip(kfs, kfs[1:])), "KF 间隔应恒为 5"


def test_causal_verdict_gate_status_is_honest():
    """因果裁决书同样必须诚实标注关卡状态（第 2 轮已过须有关卡证据）。"""
    txt = (EV / "verdict_dyn_probe_causal.md").read_text()
    assert "slam-critic" in txt, "因果裁决书须点名审查者"
    if "待过" in txt:
        assert "不得被当作已收口判决引用" in txt
    else:
        assert "✅" in txt and "§7" in txt, "宣称已过须附逐条整改表"


def test_measurement_code_is_committed():
    """关卡① 致命项回归：测量代码必须已入库，且结果 JSON 注明其来源提交。"""
    import subprocess
    head = subprocess.run(["git", "log", "--oneline", "-1", "--format=%h", "--",
                           "scripts/02_analysis/dyn_probe.py"], cwd=REPO, capture_output=True, text=True)
    assert head.stdout.strip(), "dyn_probe.py 应已在 git 历史中"
    man = json.load(open(EV / "manifest.json"))
    assert man["rounds"]["round_2_causal"]["measurement_code_commit"].startswith("92af04d3")


# ── 因果轮 III（预注册 prereg_dyn_probe_causal3.md，判据 E1–E7）──
# 踩坑「判据机条目数 < 预注册条目数」的回归：文书宣称的判据集合必须与预注册逐条对齐。

CAUSAL3_PREREG = EV / "prereg_dyn_probe_causal3.md"
CAUSAL3_VERDICT = EV / "verdict_dyn_probe_causal3.md"
CAUSAL3_COMMIT = "7fddd0d7"


def _verdict_json():
    return json.loads((EV / "dyn_probe_verdict.json").read_text())


def test_causal3_prereg_locks_criteria_and_decision_rule():
    txt = CAUSAL3_PREREG.read_text()
    for k in ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "出局规则"):
        assert k in txt, f"因果轮 III 预注册缺 {k}"
    assert "0.40" in txt and "0.75" in txt and "0.90" in txt, "门槛数值应写在预注册里"


def test_causal3_judge_entries_match_prereg():
    """判据机条目集合 == 预注册条目集合（两地图各自成立），且 E7 分层读数必须落盘。"""
    prereg_ids = set(re.findall(r"\bE([1-7])\b", CAUSAL3_PREREG.read_text()))
    assert prereg_ids == {str(i) for i in range(1, 8)}, f"预注册应锁定 E1–E7，实为 {sorted(prereg_ids)}"
    c3 = _verdict_json()["causal3_judgments"]
    for map_name in ("gate", "baseline"):
        d = c3[map_name]
        judge_ids = {re.match(r"E(\d)_", k).group(1) for k in d["criteria"] if re.match(r"E\d_", k)}
        if "E7_stratified" in d:
            judge_ids.add("7")
        assert judge_ids == prereg_ids, f"{map_name}: 判据机 {sorted(judge_ids)} != 预注册 {sorted(prereg_ids)}"
        assert "outcome" in d and d["outcome"] in ("GO", "NO-GO", "PARTIAL", "INSTRUMENT-INVALID")


def test_causal3_outcome_follows_prereg_decision_rule():
    """出局规则（¬E2 ∨ ¬E3 ⇒ NO-GO）在工件上真的被套用，且判决与判据机一致。"""
    c3 = _verdict_json()["causal3_judgments"]
    for map_name in ("gate", "baseline"):
        cr = c3[map_name]["criteria"]
        e2 = cr["E2_appearance_retention"]["pass"]
        e3 = cr["E3_geometry_retention"]["pass"]
        assert not (e2 or e3), f"{map_name}: E2/E3 应双双不过"
        assert c3[map_name]["outcome"] == "NO-GO"
    assert "NO-GO" in CAUSAL3_VERDICT.read_text()


def test_causal3_stratified_readings_are_the_reported_ones():
    """裁决书 §3.2 引用的分层读数必须与工件逐位一致（防手抄/跨轮外推）。"""
    bs = _verdict_json()["causal3_judgments"]["gate"]["E7_stratified"]["by_mask_size"]
    assert bs["P2cu"]["n_dyn<med"]["dl1"] > bs["P2c"]["n_dyn<med"]["dl1"], "并集应抬起掩码差桶"
    assert bs["P2cuv"]["n_dyn>=med"]["dl1"] < bs["P2c"]["n_dyn>=med"]["dl1"], "叠加速度臂应劣于保持臂"
    txt = CAUSAL3_VERDICT.read_text()
    for v in ("0.2902", "0.1767", "0.8478", "0.6815"):
        assert v in txt, f"裁决书应逐位引用工件分层读数 {v}"


def test_causal3_no_hand_copied_out_of_artifacts():
    """决策依据数字必须能在工件里找到。

    '×6.4' 在工件里算不出来（实为 5.13×）。裁决书**可以**在"过程/订正"里提到它，
    但不允许把它当读数陈述 ⇒ 规则收到行级：凡是含该串的行必须同时带披露标记。
    """
    txt = CAUSAL3_VERDICT.read_text()
    for line in txt.splitlines():
        if "×6.4" in line:
            assert ("曾写" in line) or ("草稿" in line), f"×6.4 只能出现在订正披露里：{line[:80]}"
    m = _verdict_json()["causal3_judgments"]["gate"]["means"]
    ratio = m["P2cu"]["n_dyn"] / m["P2c"]["n_dyn"]
    assert abs(ratio - 5.1286) < 0.01, "工件比值应为 5.13×"
    assert "5.13×" in txt and "P2cu" in txt


def test_causal3_verdict_gate_status_is_honest():
    """裁决书必须诚实标注关卡① 状态，并点名审查者与全量报告落点。

    关卡状态只看**头部**（前 14 行）——§6 整改表里会引用"仍 PENDING / 无 ⏳"这类原文，
    用全文子串判断会误伤（本用例因此在整改后第一次跑就抓到了自己的粗糙）。
    """
    txt = CAUSAL3_VERDICT.read_text()
    header = "\n".join(txt.splitlines()[:14])
    assert "slam-critic" in header, "裁决书须点名审查者"
    assert "slam_critic_report_causal3_gate1.md" in txt, "须给出全量报告落点"
    if "⏳" in header or "待过" in header:
        assert "不得被当作已收口判决引用" in header
    else:
        assert "✅" in header, "宣称已过须在头部标 ✅"
        assert "关卡① 逐条整改" in txt, "宣称已过须附逐条整改表（§6）"


def test_causal3_measurement_code_committed_before_run():
    """关卡① 致命项回归（踩坑『跑批代码未提交三连』）：探针 + 判据机 + 配置 + 预注册
    必须都**先于结果提交**入库，且 manifest 注明测量代码 sha。

    注：本轮预注册落在 `c332a116`、代码+配置落在 `7fddd0d7`（两个提交），
    两者都是结果提交 `428799cc` 的祖先 ⇒ 满足"先提交后跑批"，但**不满足"一次提交"**
    （该偏离已在裁决书 §4 如实登记）。本用例只断言不变式，不替偏离背书。
    """
    import subprocess

    def run(*args):
        return subprocess.run(list(args), cwd=REPO, capture_output=True, text=True)

    results_commit = "428799cc"
    commits = {CAUSAL3_COMMIT: ["scripts/02_analysis/dyn_probe.py",
                                "scripts/02_analysis/analyze_dyn_probe.py",
                                "configs/experiments/embrace_dyn/probe_pt2_causal3.yaml"],
               "c332a116": ["results/embrace_dyn/evidence/prereg_dyn_probe_causal3.md"]}
    for sha, paths in commits.items():
        assert run("git", "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0, f"{sha} 应在 git 历史中"
        assert run("git", "merge-base", "--is-ancestor", sha, results_commit).returncode == 0, \
            f"{sha} 必须是结果提交 {results_commit} 的祖先（先提交后跑批）"
        names = run("git", "show", "--name-only", "--format=", sha).stdout
        for p in paths:
            assert p in names, f"{sha} 应含 {p}"
    r5 = json.load(open(EV / "manifest.json"))["rounds"]["round_5_causal3"]
    assert r5["measurement_code_commit"].startswith(CAUSAL3_COMMIT)
    assert r5["prereg"].endswith("prereg_dyn_probe_causal3.md")
    assert r5["verdict"] == "evidence/verdict_dyn_probe_causal3.md"


def test_causal3_measurement_count_is_anchored_to_arms():
    """计数必须锚定工件：运动变体 = 4（P2cv/P2cm/P2cr/P2cuv）+ 累积变体 1（P2cu）。

    关卡① 抓到的错误：文书曾写"五次尝试"，但从臂名只数得出 4 个。
    """
    man = json.load(open(EV / "manifest.json"))["rounds"]
    txt = man["round_5_causal3"]["motion_model_attempts"]
    assert txt.startswith("4 motion variants"), "计数须以 4 开头（4 个运动变体）"
    for arm in ("P2cv", "P2cm", "P2cr", "P2cuv"):
        assert arm in txt, f"运动变体应逐个列名，缺 {arm}"
    verdict_txt = CAUSAL3_VERDICT.read_text()
    assert "四次尝试" in verdict_txt, "裁决书须写四次尝试"
    for line in verdict_txt.splitlines():
        if "五次" in line:
            assert any(m in line for m in ("错", "成立", "整改", "订正")), \
                f"'五次'只能出现在纠错披露里：{line[:80]}"


# ── 关卡① 第 5 轮整改的回归用例（slam-critic Reject → 整改）──

CAUSAL3_PREREG_TH = {  # 预注册跑前锁定的门槛（E4 取绝对值上界；E5 在预注册里写作 50%）
    "E1": ("le", 0.90), "E2": ("ge", 0.40), "E3": ("ge", 0.75),
    "E4": ("le", 0.25), "E5": ("le", 0.50), "E6": ("ge", 1.15)}


def _c3_reading(crit, key):
    c = crit[key]
    for k in ("bad_dl1_ratio_P2cu_over_P2c", "retention_psnr_P2cuv", "retention_bad_P2cuv",
              "d_static_db", "n_dyn_frac", "bad_dl1_ratio_Cu_over_P2cuv"):
        if k in c:
            return abs(c[k]) if k == "d_static_db" else c[k]
    raise AssertionError(f"{key} 无已知读数键")


def test_causal3_criteria_thresholds_match_prereg():
    """判据机 `pass` 必须等于"用预注册门槛判读数"的结果（防跑后改判据/改门槛）。"""
    pre = CAUSAL3_PREREG.read_text()
    assert "0.90" in pre and "0.40" in pre and "0.75" in pre and "0.25" in pre
    assert "50%" in pre and "1.15" in pre, "E5/E6 门槛应写在预注册里"
    c3 = _verdict_json()["causal3_judgments"]
    for map_name in ("gate", "baseline"):
        crit = c3[map_name]["criteria"]
        for eid, (op, th) in CAUSAL3_PREREG_TH.items():
            key = next(k for k in crit if k.startswith(eid + "_"))
            val = _c3_reading(crit, key)
            want = (val <= th) if op == "le" else (val >= th)
            assert crit[key]["pass"] is want, f"{map_name}/{key}: 读数 {val} 与门槛 {op}{th} 判不一致"


def test_causal3_verdict_table_matches_artifact_cells():
    """裁决书表格六行 × 五列逐格钉到工件（防只钉 4 个数的手抄漏网）。"""
    means = _verdict_json()["causal3_judgments"]["gate"]["means"]
    txt = CAUSAL3_VERDICT.read_text()
    for arm, vals in means.items():
        cells = [f"{vals['dyn_bad_psnr']:.2f}", f"{vals['dyn_bad_dl1_cm']:.2f}",
                 f"{vals['dyn_good_dl1_cm']:.2f}", f"{vals['static_psnr']:.2f}",
                 f"{int(round(vals['n_dyn'])):,}"]
        for c in cells:
            assert c in txt, f"{arm} 的表格单元 {c} 未出现在裁决书里"


def test_causal3_baseline_buckets_are_co_reported():
    """gate 与 baseline 两地图的分桶读数都要并陈（关卡① 第 11 条）。"""
    bs = _verdict_json()["causal3_judgments"]["baseline"]["E7_stratified"]["by_mask_size"]
    txt = CAUSAL3_VERDICT.read_text()
    for arm in ("P2c", "P2cu", "P2cuv"):
        for bucket in ("n_dyn<med", "n_dyn>=med"):
            assert f"{bs[arm][bucket]['dl1']:.4f}" in txt, f"baseline {arm}/{bucket} 的 dl1 未并陈"
    assert bs["P2cuv"]["n_dyn<med"]["dl1"] < bs["P2c"]["n_dyn<med"]["dl1"]
    assert bs["P2cuv"]["n_dyn>=med"]["dl1"] < bs["P2c"]["n_dyn>=med"]["dl1"]


def test_causal3_bucket_threshold_is_recomputable():
    """分桶阈值未落盘（关卡① 第 9 条）：须能用结果 JSON 复算，并与裁决书写的一致。"""
    R = json.load(open(EV / "dyn_probe_causal3_results.json"))
    for map_name in ("gate", "baseline"):
        nd = [r["n_dyn"] for r in R["arms"][map_name]["P2c"]
              if r.get("dyn_psnr") is not None and r.get("n_dyn")]
        med = sorted(nd)[len(nd) // 2]
        assert med == 3642, f"{map_name}: 阈值应为 3642，实为 {med}"
    assert "3642" in CAUSAL3_VERDICT.read_text()


def test_causal3_aggregation_warning_is_present():
    """E2/E3（全集）与 E7（分桶）不可互换，且桶值不得再平均（关卡① 第 5 条）。

    实测：全集口径下 retention_of(means) 与 _retention_perframe 数值相同（E3 = 0.5021）。
    """
    means = _verdict_json()["causal3_judgments"]["gate"]["means"]
    pooled = analyzer.retention_of(means, "P2cuv", "bad", "dl1")
    artifact = _verdict_json()["causal3_judgments"]["gate"]["criteria"]["E3_geometry_retention"]
    assert abs(pooled - artifact["retention_bad_P2cuv"]) < 1e-9
    txt = CAUSAL3_VERDICT.read_text()
    assert "0.4459" in txt and ("再平均" in txt or "加权" in txt), "须声明桶值再平均是错的及其原因"
    assert "0.5021" in txt


def test_causal3_analysis_provenance_recorded():
    """关卡① 致命项回归：跑后修改判据机 ⇒ 分析代码 sha 必须登记，且可复算记录与当前工件一致。"""
    import hashlib
    import subprocess
    rec = json.load(open(EV / "analyzer_reproducibility.json"))
    for k, path in (("report", EV / "dyn_probe_report.md"), ("verdict", EV / "dyn_probe_verdict.json")):
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        assert rec[k]["sha256"] == got, f"{k} 的 sha256 与可复算记录不一致（交付物被改动过？）"
    sha = rec["analyzer"]["last_touch_commit"]
    assert subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=REPO).returncode == 0
    commits = json.load(open(EV / "manifest.json"))["rounds"]["round_5_causal3"]["analysis_code_commits"]
    assert sha in commits, f"manifest 须登记分析代码 sha {sha}"
    assert "POST-RUN" in commits[sha], "跑后修改须显式标注 POST-RUN"
    assert "POST-RUN" in CAUSAL3_VERDICT.read_text() or "跑后" in CAUSAL3_VERDICT.read_text()
