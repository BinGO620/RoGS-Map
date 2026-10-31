#!/usr/bin/env bash
# build_nied_c3dgs_env.sh — Niedermayr c3dgs（Compressed 3DGS, CVPR'24）运行环境（方案 A′ 第二基线）。
# 路线同 build_sogs_env.sh：venv（monogs-ours 的 python 3.10）+ 国内镜像 + cu118（与系统 nvcc 11.8 匹配）。
#
# 两机通用：以下四项可用环境变量覆盖（默认=本机 cb 口径）。
#   远程 3090（jiangwenheng）示例（注意：该机 /usr/local/cuda-11.8 是空壳，只有 nsight；
#   真 nvcc 11.8 在 conda 环境 nvcc118 里 ⇒ CUDA_HOME 必须指向它）：
#     PY_BASE=/home/jiangwenheng/anaconda3/envs/monogs-ours-3090/bin/python \
#     VENV=/home/jiangwenheng/cron/monogs-ours/.venvs/nied-c3dgs \
#     REPO=/home/jiangwenheng/cron/monogs-ours/submodules/compressed-3dgs-niedermayr \
#     CUDA_HOME=/home/jiangwenheng/anaconda3/envs/nvcc118 \
#       bash scripts/gs_compress/build_nied_c3dgs_env.sh
set -euo pipefail
SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY_BASE="${PY_BASE:-/data/conda_envs/monogs-ours/bin/python}"
VENV="${VENV:-/data/conda_envs/nied-c3dgs}"
REPO="${REPO:-$SELF_REPO/submodules/compressed-3dgs-niedermayr}"
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-11.8}"
ALI=https://mirrors.aliyun.com/pytorch-wheels/cu118

echo "=== PY_BASE=$PY_BASE"; echo "=== VENV=$VENV"; echo "=== REPO=$REPO"; echo "=== CUDA_HOME=$CUDA_HOME"
[ -d "$REPO" ] || { echo "缺少 $REPO（先 rsync 第三方克隆）"; exit 2; }

[ -x "$VENV/bin/python" ] || "$PY_BASE" -m venv "$VENV"
PIP="$VENV/bin/pip"
"$PIP" install --upgrade pip
"$PIP" install "numpy<2" "plyfile==0.8.1" tqdm pillow pyyaml
echo "=== torch 2.4.1+cu118 ==="
"$PIP" install "$ALI/torch-2.4.1%2Bcu118-cp310-cp310-linux_x86_64.whl" "$ALI/torchvision-0.19.1%2Bcu118-cp310-cp310-linux_x86_64.whl"
echo "=== torch-scatter（pyg 索引；vq.py 硬依赖） ==="
"$PIP" install torch-scatter -f https://data.pyg.org/whl/torch-2.4.0+cu118.html || echo "WARN: torch-scatter 安装失败"
echo "=== 两个 CUDA 扩展（indexed rasterizer / weighted_distance） ==="
"$PIP" install setuptools wheel ninja pybind11
export CUDA_HOME
export PATH="$CUDA_HOME/bin:$PATH"
"$PIP" install --no-build-isolation "$REPO/submodules/diff-gaussian-rasterization" "$REPO/submodules/weighted_distance"

NIED_REPO="$REPO" "$VENV/bin/python" - <<'EOF'
import os, sys, torch
print("torch", torch.__version__, "| avail", torch.cuda.is_available())
sys.path.insert(0, os.environ["NIED_REPO"])
import diff_gaussian_rasterization, weighted_distance
try:
    import torch_scatter
    print("torch_scatter OK")
except Exception as e:
    print("torch_scatter MISSING:", e)
print("NIED-IMPORT-BASE-OK")
EOF
echo NIED-BUILD-DONE
