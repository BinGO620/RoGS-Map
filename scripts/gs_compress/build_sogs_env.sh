#!/usr/bin/env bash
# build_sogs_env.sh — 组装 SOG 压缩基线运行环境（方案 A′）。
# 路线：venv（基于 monogs-ours 的 python 3.10）+ pip 国内镜像 + 系统 CUDA 11.8。
# 理由：conda 混合通道（pytorch/nvidia/conda-forge/defaults）求解不可控（实测 50 min 未收敛）；
#       cu118 wheel 与本机 nvcc 11.8 精确匹配，可直接编译三个 CUDA 扩展。
# 用法：bash scripts/gs_compress/build_sogs_env.sh
set -euo pipefail
PY_BASE=/data/conda_envs/monogs-ours/bin/python
VENV=/data/conda_envs/sogs
SOG=/data/monogs-ours/submodules/Self-Organizing-Gaussians
ALI=https://mirrors.aliyun.com/pytorch-wheels/cu118

test -d "$SOG/submodules/PLAS" || { echo "缺少 $SOG/submodules/PLAS"; exit 2; }
echo "=== [1/4] venv ==="
[ -x "$VENV/bin/python" ] || "$PY_BASE" -m venv "$VENV"
PIP="$VENV/bin/pip"
"$PIP" install --upgrade pip

echo "=== [2/4] torch 2.4.1+cu118（aliyun 直链） ==="
"$PIP" install \
  "$ALI/torch-2.4.1%2Bcu118-cp310-cp310-linux_x86_64.whl" \
  "$ALI/torchvision-0.19.1%2Bcu118-cp310-cp310-linux_x86_64.whl"

echo "=== [3/4] SOG 依赖（USTC PyPI；版本对齐其 environment.yml） ==="
"$PIP" install "numpy<2" plyfile==1.1 pyyaml tqdm "pandas==2.2" "scipy==1.14" \
  "hydra-core==1.3" omegaconf "kornia==0.7.*" "click==8.1.*" "screeninfo==0.8" \
  pybind11 opencv-python-headless "imagecodecs[all]==2023.9.18"

echo "=== [4/4] CUDA 扩展（simple-knn / rasterizer / PLAS）+ import 冒烟 ==="
export CUDA_HOME=/usr/local/cuda-11.8
export PATH="$CUDA_HOME/bin:$PATH"
# 注意：三个扩展的 setup.py 在解析阶段即 import torch —— 必须 --no-build-isolation
# （pip ≥ 25 默认隔离构建，隔离环境无 torch 会直接 ModuleNotFoundError）。
"$PIP" install setuptools wheel ninja
"$PIP" install --no-build-isolation \
  "$SOG/submodules/simple-knn" \
  "$SOG/submodules/diff-gaussian-rasterization" \
  "$SOG/submodules/PLAS"

"$VENV/bin/python" - <<'EOF'
import sys
import torch, imagecodecs, kornia, omegaconf, plyfile, pandas
print("torch", torch.__version__, "| cuda", torch.version.cuda, "| avail", torch.cuda.is_available())
sys.path.insert(0, "/data/monogs-ours/submodules/Self-Organizing-Gaussians")
from scene.gaussian_model import GaussianModel
from compression.compression_exp import run_single_compression, run_single_decompression
from plas import sort_with_plas
import diff_gaussian_rasterization, simple_knn._C
print("SOG-IMPORT-OK")
EOF
echo "BUILD-DONE"
