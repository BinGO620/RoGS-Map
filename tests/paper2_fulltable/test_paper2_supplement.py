"""补充材料（supplement）守护（2026-10-18）：文件在位 + 表机写确定性。

存在理由：supp 表全部由 `scripts/02_analysis/paper2_supp_tables.py` 机写
（与正文同源工件；零手抄）。提交物必须 == 可复现物——同
`test_committed_latex_is_clean_in_git` 的口径（生成器确定性 ⇒ 提交后工作区须干净）。
"""
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUPP = REPO / "papers/paper2/supplement"


def test_supplement_files_exist():
    assert (SUPP / "supplement.tex").exists(), "supplement.tex 缺失"
    assert (SUPP / "supplement.pdf").exists(), "supplement.pdf 缺失（跑 build_supplement.sh）"
    tables = sorted((SUPP / "tables").glob("supp_*.tex"))
    assert len(tables) == 8, f"补充材料表数 {len(tables)} != 8：{[t.name for t in tables]}"
    fig = REPO / "results/paper2_fulltable/evidence/figs/figS_repair_person_tracking2.pdf"
    assert fig.exists(), "补充图 figS_repair_person_tracking2.pdf 缺失（dump_repair_render.py）"


def test_supplement_tables_regenerate_identically():
    r = subprocess.run(
        ["/data/conda_envs/monogs-ours/bin/python",
         str(REPO / "scripts/02_analysis/paper2_supp_tables.py")],
        cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, f"生成器失败：\n{r.stdout}\n{r.stderr}"
    g = subprocess.run(
        ["git", "status", "--porcelain", "papers/paper2/supplement/tables"],
        cwd=REPO, capture_output=True, text=True)
    assert g.stdout.strip() == "", f"补充材料表与生成器输出漂移（须重生成并提交）：\n{g.stdout}"
