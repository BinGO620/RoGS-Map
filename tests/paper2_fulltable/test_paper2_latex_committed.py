"""论文 2 LaTeX 产物的**已提交状态**门禁（纯断言，不需 GPU）。

存在理由（关卡② 第 1 次的发现，2026-09-19）：`tests/paper2_fulltable/test_paper2_tables.py`
只测"生成器逻辑与它自己的输出"，**没有任何用例校验已提交的 `evidence/latex/*.tex`**——
于是两个真 bug 从生成一直活到审查：
  ① `round(median(fps))` 取整到 0 + `if fps_med` 真值过滤 ⇒ FPS 列退化成 "1.000" 与 "--"；
  ② LaTeX 版 Tab.3s 比 Markdown 版少一列（丢掉 `mask source`），让混用两种静态协议的表看起来同协议。

用法：/data/conda_envs/monogs-ours/bin/python -m pytest tests/paper2_fulltable -q
"""
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EV = REPO / "results/paper2_fulltable/evidence"
LATEX = EV / "latex"
PREVIEW = EV / "tables_paper2_preview.json"
ARMS = ("baseline", "swbaonly", "final", "gate")
# 2026-10-10（G2-M1 修订）：系统表 = 前作栈单列（论文 2 无新系统配置；含 SWBA 的复合臂
# 不进主表）；完整四梯在附表 tab:ladder。
MAIN_ARMS = ("baseline",)
SEQS = ("balloon", "balloon2", "crowd", "crowd2", "crowd3",
        "person_tracking", "person_tracking2")


def _preview():
    return json.loads(PREVIEW.read_text())


def test_committed_latex_is_clean_in_git():
    """产物必须已入库且工作区干净（生成器确定性 ⇒ 提交物 == 可复现物）。"""
    r = subprocess.run(["git", "status", "--porcelain", "results/paper2_fulltable/evidence"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.stdout.strip() == "", f"证据目录有未提交改动：\n{r.stdout}"


def test_fps_column_is_not_degenerate():
    """FPS 列回归 + 同码口径守护。

    历史：整数取整 + 真值过滤曾把整列压成 '1.000' 与 '--'。
    2026-10-05 更新（D1-027 整改 + 同码并发对照）：Tab.4 的两列 FPS 现为**同码**单变量
    （effctl 独占 / effctlconc 并发，3 序列中位），不再用 R33 原批（跨版本）。本测试改为
    从两批 CSV 直接复算中位并逐位比对，且守护"两列都非退化 + 比值列在场"。
    """
    import csv
    import statistics
    ROOTP = REPO / "results/paper2_fulltable"
    tex = (LATEX / "tab4_efficiency.tex").read_text()
    body = tex.split("\\midrule", 1)[1].split("\\bottomrule", 1)[0]
    prefixes = {"exclusive": "effctl", "concurrent": "effctlconc"}

    def med(prefix, arm):
        vals = []
        for f in ROOTP.glob(f"{prefix}_{arm}_*_seed0/tables/efficiency_raw.csv"):
            r = list(csv.DictReader(f.open()))[0]
            vals.append(float(r["online_fps"]))
        return statistics.median(vals) if vals else None

    for a in MAIN_ARMS:
        ex, cc = med(prefixes["exclusive"], a), med(prefixes["concurrent"], a)
        assert ex and 0 < ex < 5, f"{a} 独占 fps 退化/异常: {ex}"
        assert cc and 0 < cc < 5, f"{a} 并发 fps 退化/异常: {cc}"
        assert f"{ex:.3f}" in body, f"tab4 应含 {a} 独占 fps 中位 {ex:.3f}"
        assert f"{cc:.3f}" in body, f"tab4 应含 {a} 并发 fps 中位 {cc:.3f}"
    assert body.count("--") == 0, "FPS/显存/基元数不应出现 '--'（曾有整臂缺失）"
    # 同码守护：两批 CSV 列数一致（跨版本比较是历史致命项，见 D1-027）
    def ncol(prefix):
        p = next(iter(ROOTP.glob(f"{prefix}_baseline_*_seed0/tables/efficiency_raw.csv")), None)
        return len(open(p).readline().split(",")) if p else None
    assert ncol("effctl") == ncol("effctlconc"), \
        "Tab.4 两列必须同码（efficiency_raw 列数须一致）"


def test_tab3s_declares_mask_source_column():
    """Tab.3s 必须带 mask source 列且转义正确。

    2026-09-24 更新（D1-014 F1 整改，D2-011 轨 A）：静态键优先源已从
    "运行期 gtmc P-A + seg_mask 混用"切到 **canonical（dynamic_mask）单源**
    （`render_compare_static_canon/`，84 run 满覆盖）⇒ 本测试从"守护混用事实"
    改为"守护单源统一"（混用才是要防的回归）。
    """
    tex = (LATEX / "tab3s_static.tex").read_text()
    assert "mask source" in tex, "tab3s 须带 mask source 列"
    assert "same canonical static" in tex, "表注须声明 canonical 单源口径（2026-09-22 重算）"
    # 只禁"作为数据源引用"（\texttt{runtime\_pa} 行值）；表注里说明性提及退役史是合规的
    assert "runtime\\_pa" not in tex and "runtime_pa" not in tex, \
        "tab3s 不得再以 gtmc 运行期口径作数据源（说明性提及退役史可）"
    t = _preview()
    srcs = {t[f"baseline|{s}"]["mask_source"] for s in SEQS}
    assert srcs == {"dynamic_mask"}, \
        f"静态源应已统一为 canonical dynamic_mask，实为 {srcs}（混用 = 回归到 F1 整改前）"


def test_coverage_column_not_reintroduced_without_disclosure():
    """coverage 28/28 恒 1.000（项目已登记无判别力）⇒ 不得作为列重现。

    2026-10-22：审稿指出该列每格恒 1.000、题注自承非判别性，属无效列 ⇒ 从表中删除。
    若将来重新加回，必须同时把 "non-discriminative" 写进题注（本测试守护这条配对）。
    """
    tex = (LATEX / "tab3s_static.tex").read_text()
    t = _preview()
    covs = [t[f"{a}|{s}"]["static_cov"] for a in ARMS for s in SEQS
            if t[f"{a}|{s}"].get("static_cov") is not None]
    assert covs and all(abs(c - 1.0) < 1e-9 for c in covs), "coverage 应恒 1.000（已登记）"
    has_col = "coverage" in tex.split("\\midrule")[0]
    if has_col:
        assert "non-discriminative" in tex, "coverage 列在表内 ⇒ 题注须声明非判别性"
    else:
        assert "non-discriminative" not in tex, "coverage 列已删除 ⇒ 题注不应再提判别性"


def test_no_caption_asserts_a_withdrawn_claim():
    """图注不得陈述被撤回/已被工件否定的主张（关卡② 两条重大）。"""
    tab2r = (LATEX / "tab2r_render.tex").read_text()
    assert "no arm degrades" not in tab2r, "'the static scene does not degrade' 与 tab3s 矛盾（5/7 序列实为下降）"
    # tab2_pt_seed 表已于 2026-10-09 删除（正文零 \input 的死件；Sim(3) 列判负、图注带 WITHDRAWN）。
    # 故不再断言其图注；Sim(3) 撤回记录保留在 verdict_sim3_scale.md（工件在库）。


def test_static_psnr_degrades_on_most_sequences_and_caption_says_so():
    """把"静态不退化"这一被工件否定的说法钉死。

    2026-09-24 更新（D1-014 F1 整改后口径 = canonical）：canon 口径下 gate 低于
    baseline 的序列为 **4/7**（balloon/crowd/crowd3/person_tracking2；旧 gtmc 口径
    曾为 5/7）——方向性结论（"gate 伤静态区"）维持，格数随口径如实更新。
    """
    t = _preview()
    worse = [s for s in SEQS
             if t[f"gate|{s}"]["static_psnr"] < t[f"baseline|{s}"]["static_psnr"]]
    assert len(worse) == 4, f"预期 4/7 序列下降（canon 口径），实为 {worse}"
    assert "tab:static" in (LATEX / "tab2r_render.tex").read_text(), "全图表须指向分区表"


def test_main_table_degradation_is_disclosed_in_readme():
    """主表跨序列劣化（含"过 5cm 线集合与 baseline 相同"）必须在包 README 里披露。"""
    t = _preview()
    worse = [s for s in SEQS if t[f"gate|{s}"]["ate_mean"] > t[f"baseline|{s}"]["ate_mean"]]
    assert len(worse) == 5, f"预期 5/7 序列劣化，实为 {worse}"
    ok = lambda a: {s for s in SEQS if t[f"{a}|{s}"]["ate_mean"] <= 5.0}
    assert ok("gate") == ok("baseline"), "过 5cm 线的集合应相同"
    readme = (LATEX / "README.md").read_text()
    for token in ("5/7", "5cm"):
        assert token in readme, f"包 README 须披露 {token} 这一点"


def test_redline_mechanism_names_absent_from_submission_artifacts():
    """红线：被排除的专有机制名不得出现在任何**投稿产物**里（2026-10-15 增补，R4-P12）。

    存在理由：`papers/paper2/tables/tab5_ladder.tex`（组件阶梯附表）长期携带
    SWBA / +LC / +Gate 三个用户明确排除的机制名。它不在正文 `\\input` 列表内，
    故从未进入 PDF——但作为源码树的一部分，下一次改版即可能被误编入。
    本测试把"投稿产物零红线词"从人工检查固化为机器门。

    范围：正文 tex + `papers/paper2/tables/` 下的 .tex，**均剔除 LaTeX 注释**
    （禁语提醒本身写在注释里，注释不入 PDF）。不覆盖 `results/*/evidence/latex/`
    ——那是生成物留档区，按设计保留审计用阶梯表。
    """
    import re
    pat = re.compile(r"swba|loop[\s-]?closure", re.IGNORECASE)

    def strip_comments(text):
        """LaTeX 注释 = 未转义的 % 到行尾。"""
        return "\n".join(re.sub(r"(?<!\\)%.*$", "", ln) for ln in text.splitlines())

    targets = [REPO / "papers/paper2/paper2_cvm.tex"]
    targets += sorted((REPO / "papers/paper2/tables").glob("*.tex"))

    hits = []
    for p in targets:
        if not p.exists():
            continue
        for i, line in enumerate(strip_comments(p.read_text(errors="ignore")).splitlines(), 1):
            if pat.search(line):
                hits.append(f"{p.relative_to(REPO)}:{i}: {line.strip()[:80]}")
    assert not hits, "投稿产物出现红线机制名（SWBA / loop closure）：\n" + "\n".join(hits)
