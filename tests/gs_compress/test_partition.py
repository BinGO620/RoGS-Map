"""partition.py 单测（prereg_gs_compress.md §4 的守护）。

守护的事实：
  ① GT 深度可见性门控：位于动态掩码像素、但**被更近表面遮挡**的背景基元不投票；
  ② 正对照：真正落在动态区且可见的基元被标 label=1；
  ③ 一致几何：同一相机下投影/反投影自洽。
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "gs_compress"))
_spec = importlib.util.spec_from_file_location("partition", REPO / "scripts" / "gs_compress" / "partition.py")
pt = importlib.util.module_from_spec(_spec)
sys.modules["partition"] = pt
_spec.loader.exec_module(pt)


def _world_point_in_front_of_camera(c2w, uv, z, K):
    """构造世界点：先在相机系给 (u,v,z)，再变换到世界。"""
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    x = (uv[0] - cx) / fx * z
    y = (uv[1] - cy) / fy * z
    pc = np.array([x, y, z, 1.0])
    return (c2w @ pc)[:3]


def test_occlusion_gate_excludes_background():
    H = W = 64
    K = np.array([[60.0, 0, 32.0], [0, 60.0, 32.0], [0, 0, 1.0]])
    c2w = np.eye(4)  # 相机在原点看 +z
    trj = {0: c2w}
    # 动态掩码：整幅都是动态（极端情形）
    mask = np.ones((H, W), bool)
    # GT 深度：在 (32,32) 处最近表面 z=2.0
    depth = np.full((H, W), 2.0, np.float32)
    import tempfile, os
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        dp = os.path.join(td, "0000.png")
        Image.fromarray((depth * 5000).astype(np.uint16)).save(dp)
        depth_paths = [dp]
        # 前景点 z=2.0（可见）+ 背景点 z=5.0（被遮挡）
        p_front = _world_point_in_front_of_camera(c2w, (32, 32), 2.0, K)
        p_back = _world_point_in_front_of_camera(c2w, (32, 32), 5.0, K)
        xyz = np.stack([p_front, p_back])
        res = pt.label_primitives(xyz, trj, {0: mask}, K, W, H, [0],
                                  depth_paths=depth_paths, depth_scale=5000.0,
                                  occl_tol_m=0.05)
        assert res["labels"][0] == 1          # 前景可见且动态
        assert res["labels"][1] == 0          # 背景被遮挡 ⇒ 不投票
        assert res["hit_vis"][1] == 0


def test_static_region_not_labeled():
    H = W = 64
    K = np.array([[60.0, 0, 32.0], [0, 60.0, 32.0], [0, 0, 1.0]])
    trj = {0: np.eye(4)}
    mask = np.zeros((H, W), bool)  # 全静态
    depth = np.full((H, W), 2.0, np.float32)
    import tempfile, os
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        dp = os.path.join(td, "0000.png")
        Image.fromarray((depth * 5000).astype(np.uint16)).save(dp)
        p = _world_point_in_front_of_camera(np.eye(4), (32, 32), 2.0, K)
        res = pt.label_primitives(np.stack([p]), trj, {0: mask}, K, W, H, [0],
                                  depth_paths=[dp], depth_scale=5000.0)
        assert res["labels"][0] == 0
        assert res["hit_vis"][0] == 1
