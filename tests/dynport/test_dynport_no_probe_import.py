"""DynPort「探针≠在线」边界守护（纯 CPU）：在线模块不得 import 离线探针。

对齐 impl_design_dynport_L1.md §3（单测 ④）与坑#6。理由：`scripts/02_analysis/dyn_probe.py`
的 `DynPortBuffer` 用 GT 深度 / trj_est 离线位姿 / canonical 掩码——在线若误用它即踩本仓
反复栽过的"探针≠在线"边界（NOTES 踩坑）。

用法：/data/conda_envs/monogs-ours/bin/python -m pytest tests/dynport/test_dynport_no_probe_import.py -v
"""
import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

MOD = REPO / "utils" / "dyn_port_buffer.py"


def test_no_probe_or_run_import():
    """在线模块的 import 图里不得出现 dyn_probe / 探针路径。"""
    tree = ast.parse(MOD.read_text())
    mods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mods.append(node.module or "")
    joined = " ".join(mods)
    assert "dyn_probe" not in joined, f"在线模块不得 import 探针：{joined}"
    assert "02_analysis" not in joined, f"在线模块不得 import 探针目录：{joined}"
    # 决策核不得依赖探针的 run 对象（源码级无 `run.` 属性访问）
    src = MOD.read_text()
    assert ".frame_mask(" not in src and ".frame_data(" not in src, \
        "在线模块不得调用探针 run 的 GT 接口（frame_mask/frame_data）"


def test_only_pure_deps():
    """模块只应依赖 numpy / stdlib（scipy 惰性在函数内）；不得引入 torch 层面的重依赖到顶层。"""
    tree = ast.parse(MOD.read_text())
    top = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top.append(node.module)
    heavy = [m for m in top if m.split(".")[0] in ("torch", "cv2", "open3d")]
    assert not heavy, f"顶层不得引入重依赖：{heavy}"
