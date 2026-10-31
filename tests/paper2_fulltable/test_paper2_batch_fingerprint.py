"""paper2_batch_fingerprint.py 门禁（G2-S1 跨批次臂等价性）。

守护的事实：**R33 主批与 R34 留出批的「ATE 表角色臂」在配置上逐字段一致**
（`rb`↔`baseline` / `sw`↔`swbaonly` / `gate`↔`gate`），因而 R34 的 ATE 在
**ATE 表口径**下可与主表同稿引用。

**作用域（勿外推）**：本测试只覆盖 ATE 表三臂，**不覆盖 codec 面板**
（codec 主面板 `{baseline,final}` vs 留出面板 `{rb,gate}` 不可互相映射）——
见 `scripts/02_analysis/paper2_batch_fingerprint.py` 文件头。

反面（本测试存在的理由）：若哪天有人改了主批或 R34 批的某个机制开关/阈值，
两批会被判为不同栈 ⇒ 本测试转红，阻止"跨批数字混引"。改动该事实时须同 commit
更新本测试（DISCIPLINE「门禁测试随整改同步」）。

用法：/data/conda_envs/monogs-ours/bin/python -m pytest tests/paper2_fulltable/test_paper2_batch_fingerprint.py -v
"""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "paper2_batch_fingerprint", REPO / "scripts/02_analysis/paper2_batch_fingerprint.py")
fb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fb)


def test_batches_arm_equivalent():
    """三臂角色在全部非数据集字段上逐字段一致。"""
    ok, rep = fb.check(verbose=True)
    assert ok, "cross-batch arm drift detected:\n" + "\n".join(rep)


def test_each_arm_present():
    """每个 R34 臂都有 run（防"臂被删/改名后真空通过"）。"""
    for short in fb.ARM_MAP:
        runs = fb._r34_configs(short)
        assert runs, f"no r34 runs found for arm {short!r}"


def test_fingerprint_excludes_dataset_fields():
    """指纹口径：不含数据集/运行实例字段（否则跨批必误报）。"""
    base = fb._arm_fingerprint(fb._main_arm_config("gate"))
    assert not any(k.startswith(fb.EXCLUDE_PREFIX) for k in base)
    assert not (fb.EXCLUDE_EXACT & set(base))


def test_controls():
    """阳性（改机制开关被检出）+ 阴性（不排除数据集字段即误报）对照。"""
    fb.selfcheck()
