#!/usr/bin/env python
"""test_paper2_builds.py — 论文 2 新稿 tectonic 构建门禁（2026-10-11 增设）。

存在理由（2026-10-11 教训）：生成器输出 LaTeX 片段（表/题注）与正文 tex 里的
转义/宏/字体问题，只有 tectonic 编译时才暴露（例：`\\textsuperscript` 触发 6pt
Times 字形缺失导致 XeTeX 崩溃；`\\input` 路径错；bib 缺 key）。此前这类错误
"提交后才在 build 时爆"，本测试把构建前移到 pytest 阶段。

守护的事实：
1. **新稿可编译**：`papers/paper2/paper2_cvm.tex` 用本机 tectonic（/data/conda_envs/tex）
   能产出 PDF，无致命错误（XeTeX 崩溃 / 缺文件 / bib 无 .bbl 产物则失败）。
2. **编译是幂等的**：构建在 /tmp 隔离目录进行，不污染仓库；产物可复现。

注意：
- 本测试只跑「活区新稿」（Phase 3 重写中）。v0 归档构建由 `build_paper2.sh` 手动复核。
- tectonic 首次运行会联网拉包（~分钟级）；已缓存后秒级。若网络不可用且无缓存，
  测试会失败——此时属环境问题，不是论文问题（报错信息会区分）。
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TEX = REPO / "papers/paper2/paper2_cvm.tex"
TECTONIC = Path("/data/conda_envs/tex/bin/tectonic")
BUILD = REPO / "scripts/paper2_fulltable/build_paper2.sh"

# 骨架态也构建（骨架必须能编译；§3 已在）。不存在 tex 才跳过（重写期早于骨架）。
pytestmark = pytest.mark.skipif(
    not TEX.exists(), reason="活区新稿 tex 尚未创建（Phase 3 骨架之前）")


def _build(out_dir: Path) -> subprocess.CompletedProcess:
    # NO_DELIVER=1: 只验证"能编译"，不回写受版本控制的交付 PDF。
    # 否则每跑一次本测试，papers/paper2/paper2_cvm.pdf 就变成脏改动（2026-10-28 实测：
    # 该 PDF 仅 CreationDate 变化即可造成 1 字节 diff，污染工作树）。
    env = dict(os.environ, NO_DELIVER="1")
    return subprocess.run(
        ["bash", str(BUILD), str(out_dir)],
        cwd=REPO, capture_output=True, text=True, timeout=600, env=env)


def test_new_paper_builds_with_tectonic(tmp_path):
    """新稿 tectonic 构建成功：产出 PDF、无致命错误。"""
    if not TECTONIC.exists():
        pytest.skip("tectonic 不在 /data/conda_envs/tex（构建环境未就绪）")
    proc = _build(tmp_path)
    pdf = tmp_path / "paper2_cvm.pdf"
    assert pdf.exists(), f"构建未产出 PDF。退出码 {proc.returncode}；stderr 尾：\n{proc.stderr[-1500:]}"
    assert "pages=" in proc.stdout, f"构建脚本未输出页数统计。stdout：\n{proc.stdout[-1500:]}"
    # 致命错误特征：脚本输出 error: the XeTeX engine had an unrecoverable error
    assert "unrecoverable error" not in proc.stdout + proc.stderr, \
        f"XeTeX 致命错误（转义/字体/缺文件）：\n{proc.stderr[-1500:]}"


def test_build_script_src_defaults_to_live_paper():
    """build_paper2.sh 默认 src_dir = 活区 papers/paper2（守护 Phase 3 后默认编新稿）。"""
    text = BUILD.read_text()
    assert 'P="${2:-$REPO/papers/paper2}"' in text, \
        "build_paper2.sh 默认 src 已不是活区新稿（v0 归档复核须显式传参）"


def test_build_script_default_out_is_in_repo():
    """默认 out_dir 必须在项目内（.tmp/），不得再是 /tmp（2026-10-13 用户指令）。

    守护的事实：构建产物默认落在仓库内（`.tmp/paper2_build`，已 gitignore），
    且活区构建会把 PDF 自动复制到 `papers/paper2/paper2_cvm.pdf`——
    最新成品始终在项目内，不需要手工从 /tmp 搬运。
    """
    text = BUILD.read_text()
    assert 'OUT="${1:-$REPO/.tmp/paper2_build}"' in text, \
        "build_paper2.sh 默认 out_dir 不是项目内 .tmp（用户要求最新产物放项目里）"
    assert "/tmp/paper2_build" not in text.split("OUT=", 1)[1].split("\n", 1)[0], \
        "默认 out_dir 仍指向 /tmp"
    # 交付复制逻辑在位（活区构建 → 刷新 papers/paper2/paper2_cvm.pdf）
    assert 'cp "$OUT/paper2_cvm.pdf" "$LIVE/paper2_cvm.pdf"' in text, \
        "缺少交付 PDF 自动复制逻辑（活区构建应刷新 papers/paper2/paper2_cvm.pdf）"
