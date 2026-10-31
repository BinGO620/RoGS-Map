"""DynPort 生命周期豁免门禁（纯 CPU）：dyn_lineage_base 两态 —— 0 = 逐位不变；>0 = 动态豁免。

对齐 DISCIPLINE「代码保护」例外流程③（新机制必须 config 开关且默认关闭时与主线逐位一致）
与 impl_design §2.4。守护 `GaussianModel.densify_and_prune`/`reset_opacity_nonvisible` 里
新增的 `_dynport_protect` 豁免（动态层 lineage ≥ dyn_lineage_base 不被静态管线裁剪）。

用最小桩对象直接调 `_dynport_protect`（不实例化 GaussianModel——它 __init__ 要 CUDA）。

用法：/data/conda_envs/monogs-ours/bin/python -m pytest tests/dynport/test_dynport_exempt.py -v
"""
import sys
from pathlib import Path

import torch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from gaussian_splatting.scene.gaussian_model import GaussianModel  # noqa: E402


class _Stub:
    """最小桩：只带 `_dynport_protect` 需要的字段。"""
    dyn_lineage_base = 0
    def __init__(self, lineage):
        self.lineage_id = torch.as_tensor(lineage, dtype=torch.int32)

    def ensure_lineage_state(self):
        pass

    # 绑定真实方法（未绑定函数）
    _dynport_protect = GaussianModel._dynport_protect


def test_base_zero_is_identity():
    """默认关（base=0）⇒ 原样返回（逐位不变）。"""
    s = _Stub([-1, 5, 10])
    m = torch.tensor([True, True, False])
    out = s._dynport_protect(m)
    assert torch.equal(out, m), "base=0 必须逐位不变"


def test_base_protects_dyn_lineage():
    """base>0 ⇒ lineage ≥ base 的条目从掩码里豁免（置 False）。

    `_dynport_protect` 同时用于 3 处（语义统一为"True=对该行动作"）：
      - densify_and_split / densify_and_clone 的 `selected_pts_mask`（True=选中致密化）⇒ 动态不 clone/split；
      - densify_and_prune 的 `prune_mask`（True=剪）⇒ 动态不剪。
    """
    s = _Stub([-1, 100, 200])
    s.dyn_lineage_base = 100
    m = torch.tensor([True, True, True])          # 全选中/全剪
    out = s._dynport_protect(m)
    assert out.tolist() == [True, False, False], "动态层(100,200)应豁免，静态(-1)仍可动"


def test_base_partial_overlap():
    s = _Stub([-1, 99, 100, 101])
    s.dyn_lineage_base = 100
    m = torch.tensor([True, True, True, False])
    out = s._dynport_protect(m)
    assert out.tolist() == [True, True, False, False], "仅 ≥100 豁免"


def test_length_mismatch_defensive():
    """lineage 与 mask 长度不符（未同步的短窗）⇒ 原样返回，不崩。"""
    s = _Stub([-1, 5])
    s.dyn_lineage_base = 100
    s.ensure_lineage_state = lambda: setattr(s, "lineage_id", torch.tensor([-1, 5, 7]))
    # ensure 后仍不符 ⇒ 原样
    s2 = _Stub([-1, 5])
    s2.dyn_lineage_base = 100
    s2.ensure_lineage_state = lambda: None      # 不修 ⇒ 长度仍 2
    m = torch.tensor([True, True, True])
    out = s2._dynport_protect(m)
    assert torch.equal(out, m), "长度不符时须原样返回（防御）"
