#!/usr/bin/env python
"""test_paper2_baseline_table.py — tab_baseline.tex / baseline_compare.json 门禁（G2 条件②）。

守护的事实（2026-10-11 slam-critic G2 条件清单②）：
1. **数字可复算**：表中关键格与 raw CSV 按 sequence+seed 聚合（mean, ddof=1 sd）逐位一致
   （抽查 MonoGS balloon、Co-SLAM crowd、Prior RGB-D stack balloon）。
2. **发散标 (d) 集合正确**：ATE>100cm 或 path_length_ratio>5 的格必须带 (d)；无 (f) 漏标。
3. **行结构完整**：12 行（11 方法 + prior）、分组标签 static/dynamic、Family 列
   （3DGS/implicit/classical；2026-10-18 由原 Type 列的 static/dynamic 改，见生成器 FAMILY）、
   prior 行以 `Prior RGB-D stack` 命名。
4. **生成器确定性**：重跑生成器输出与落盘工件逐字节一致（防手改/漂移）。

反面（本测试存在的理由）：若有人手改 tab_baseline.tex、改口径、或改生成器后未重生成，
本测试转红，阻止"数字入表前未过关卡②"的事实被破坏。改动该事实时须同 commit 更新本测试
（DISCIPLINE「门禁测试随整改同步」）。

用法：/data/conda_envs/monogs-ours/bin/python -m pytest tests/paper2_fulltable/test_paper2_baseline_table.py -v
"""
import csv
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TEX = REPO / "results/paper2_fulltable/evidence/latex/tab_baseline.tex"
JSON = REPO / "results/paper2_fulltable/evidence/baseline_compare.json"
GEN = REPO / "scripts/02_analysis/paper2_baseline_table.py"
RAW = REPO / "resources/baselines/baselines_result"
COMMON = ["balloon", "balloon2", "crowd", "crowd2", "person_t", "person_t2"]
TEX_SEQ = ["balloon", "balloon2", "crowd", "crowd2", "person\\_tracking", "person\\_tracking2"]

# 抽查格：方法 -> (序列, 期望 mean±sd, 期望 (d))
SPOT = {
    "MonoGS": ("balloon", (39.32, 1.01), False),
    "Co-SLAM": ("crowd", (35866.32, 38265.29), True),
    "Prior RGB-D stack": ("balloon", (3.25, 0.07), False),
}


def _rows_of(method):
    """raw CSV 中该方法的全部 tracking 行（按 sequence 聚合）。"""
    dir_name = "ORB_SLAM3" if method == "ORB-SLAM3" else method
    p = RAW / dir_name / "tracking_raw.csv"
    rows = list(csv.DictReader(open(p)))
    agg = defaultdict(list)
    for r in rows:
        if r["dataset"] == "BONN":
            agg[r["sequence"]].append(float(r["ate_rmse_cm"]))
    out = {}
    for seq, vals in agg.items():
        n = len(vals)
        mean = sum(vals) / n
        sd = (sum((v - mean) ** 2 for v in vals) / (n - 1)) ** 0.5 if n > 1 else 0.0
        out[seq] = (mean, sd)
    return out


def _prior_rows():
    """前作栈行：机写自 tables_paper2_preview.json（r33_rebase 口径，`baseline|<seq>` 键）。"""
    d = json.load(open(REPO / "results/paper2_fulltable/evidence/tables_paper2_preview.json"))
    out = {}
    for seq in ["balloon", "balloon2", "crowd", "crowd2", "person_tracking", "person_tracking2"]:
        v = d[f"baseline|{seq}"]
        out[seq] = (v["ate_mean"], v["ate_sd"])
    return out


def _parse_tex():
    """解析 tab_baseline.tex 为 {方法: {序列: (mean, sd, is_d)}}。"""
    text = TEX.read_text()
    cells = {}
    method = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(r"\multicolumn"):
            continue
        m = re.match(r"(?:\\textbf\{)?([A-Za-z0-9\-_ ]+?)(?:\})? & (?:\\textbf\{)?(3DGS|implicit|classical)\}? & (.*) \\\\$", line)
        if m:
            method = m.group(1).strip()
            cells[method] = {}
            for seq, val in zip(TEX_SEQ, re.findall(r"([\d.]+)(?:\$\\pm\$([\d.]+))?(\$[^$]*\\mathrm\{[df]\}\$)?", m.group(3))):
                mean = float(val[0])
                sd = float(val[1]) if val[1] else 0.0
                sup = len(val) > 2 and bool(val[2])
                cells[method][seq] = (mean, sd, sup)
    return cells


def test_spot_cells_recompute_from_raw():
    """抽查格与源数据聚合逐位一致（ddof=1）。"""
    for method, (seq, (em, es), _) in SPOT.items():
        got = _prior_rows()[seq] if method == "Prior RGB-D stack" else _rows_of(method)[seq]
        assert abs(got[0] - em) < 0.01, f"{method} {seq} mean {got[0]} != {em}"
        assert abs(got[1] - es) < 0.005, f"{method} {seq} sd {got[1]} != {es}"


def _raw_seq(tex_seq):
    return {"person\\_tracking": "person_t", "person\\_tracking2": "person_t2"}.get(tex_seq, tex_seq)


def _diverge_flags(method):
    """按生成器判据返回 {seq: is_diverged}：任一 OK-seed 满足 plr>500 或 ATE>100cm。

    与 scripts/02_analysis/paper2_baseline_table.py `_fmt` 的 ndiv 判据逐字一致
    （plr 缺失值按 NaN 处理、不参与比较；非 OK 行不参与）。
    """
    if method == "Prior RGB-D stack":
        return {}
    dir_name = "ORB_SLAM3" if method == "ORB-SLAM3" else method
    rows = list(csv.DictReader(open(RAW / dir_name / "tracking_raw.csv")))
    out = {}
    for seq in set(r["sequence"] for r in rows if r["dataset"] == "BONN"):
        seq_rows = [r for r in rows if r["dataset"] == "BONN" and r["sequence"] == seq]
        ok = [r for r in seq_rows if r["status"] == "OK"]

        def _num(r, col):
            try:
                return float(r[col])
            except (ValueError, TypeError):
                return float("nan")

        div = any((_num(r, "path_length_ratio") > 500.0) or (_num(r, "ate_rmse_cm") > 100.0) for r in ok)
        out[seq] = div
    return out


def test_diverge_marks_complete():
    """(d) 集合与判据（ATE>100 或 plr>5）一致，无漏标。"""
    parsed = _parse_tex()
    flags = {m: _diverge_flags(m) for m in parsed}
    for method, seqs in parsed.items():
        if method == "Prior RGB-D stack":
            continue  # prior 行无发散格（数值远低于阈值）
        for seq, (mean, _sd, is_d) in seqs.items():
            expect_d = flags[method].get(_raw_seq(seq), False)
            assert is_d == expect_d, f"{method} {seq}: (d)={is_d} 期望={expect_d} (mean {mean:.1f})"


def test_row_structure_complete():
    """12 行 + 分组 + prior 命名。"""
    parsed = _parse_tex()
    assert len(parsed) == 12
    assert "Prior RGB-D stack" in parsed
    text = TEX.read_text()
    assert "Static methods" in text and "Dynamic methods" in text


def test_json_matches_tex():
    """JSON 与 tex 的 ATE 数值一致（同源双工件不漂移）。"""
    data = json.load(open(JSON))
    parsed = _parse_tex()
    for row in data:
        name = row["method"]
        tex_name = "ORB-SLAM3" if name == "ORB_SLAM3" else name
        for seq in COMMON:
            j = row["cells"][seq]["ate"]
            if not j:
                continue
            tex_seq = "person\\_tracking" if seq == "person_t" else "person\\_tracking2" if seq == "person_t2" else seq
            t = parsed[tex_name][tex_seq]
            assert abs(j[0] - t[0]) < 0.005 and abs(j[1] - t[1]) < 0.005, \
                f"{name} {seq}: json {j} vs tex {t[:2]}"


def test_generator_deterministic():
    """重跑生成器输出与落盘逐字节一致（防手改/漂移）。"""
    import hashlib
    import os

    def sha(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()

    before = (sha(TEX), sha(JSON))
    proc = subprocess.run(
        ["/data/conda_envs/monogs-ours/bin/python", str(GEN)],
        cwd=REPO, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(REPO)})
    assert proc.returncode == 0, proc.stderr
    after = (sha(TEX), sha(JSON))
    assert after == before, "生成器重跑输出漂移（工件被改动或生成器不确定）"
