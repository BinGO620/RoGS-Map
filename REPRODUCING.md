# Reproducing Paper 2 (RoGS-Map)

Step-by-step instructions to reproduce the results of *RoGS-Map: Anatomy,
Compression, and Offline Repair of Dynamic Gaussian SLAM Maps* (CVM 2027, under
review).

This paper studies the **map** produced by a dynamic RGB-D 3DGS-SLAM system. It
has three contributions, all on the map side: an offline map codec, a
map-side cost characterization of the anti-dynamic paradigm, and an offline
repair operator that puts dynamic content back. The system layer
(tracking/rendering/efficiency) is background.

Everything runs from this repository alone. The offline base maps are
downloaded as GitHub Release assets by `scripts/download_assets.sh`.

---

## 0. Requirements

| Item | Requirement |
|---|---|
| OS | Linux x86_64 |
| GPU | NVIDIA, ≥ 8 GB VRAM for the SLAM runs; codec/repair paths are CPU-capable |
| Toolchain | CUDA 11.8 (`nvcc`), `gcc`/`g++`, `git` |
| Conda | Miniconda or Anaconda |
| Disk | ~15 GB datasets + ~2 GB release assets |
| Python | provided by the conda environment (3.10) |

---

## 1. Clone with submodules

```bash
git clone --recursive https://github.com/BinGO620/RoGS-Map.git
cd RoGS-Map
```

Or, if already cloned:

```bash
git submodule update --init --recursive
git submodule status      # both lines must start with a commit hash
```

---

## 2. Create the environment

```bash
./setup_env.sh
conda activate rogs-map
```

`setup_env.sh` creates the `rogs-map` conda environment, builds the two CUDA
extensions, and fetches datasets if they are missing. It is idempotent — safe to
re-run.

If you prefer to do the steps by hand:

```bash
conda env create -f environment.yaml
conda activate rogs-map
python -m pip install ./submodules/simple-knn ./submodules/diff-gaussian-rasterization
bash scripts/download_bonn.sh
bash scripts/download_tum.sh
```

Smoke-check:

```bash
python -c "import torch, diff_gaussian_rasterization, simple_knn._C; print(torch.__version__, torch.cuda.is_available())"
```

---

## 3. Download the offline base maps

The codec and repair operators are **offline post-processing**: their input is a
SLAM run's final PLY plus per-frame trajectories and config. These are heavy
assets and are not tracked in git.

```bash
bash scripts/download_assets.sh
```

This downloads the base-map bundles from the GitHub Release and verifies sha256
against `tools/release_assets.sha256`. To build the bundles yourself from local
run directories:

```bash
MONOGS_OURS=/path/to/checkout/with/runs bash tools/package_release_assets.sh
```

`package_release_assets.sh` requires `MONOGS_OURS` to point at a checkout that
contains the run directories listed in `tools/release_asset_index.tsv`. There is
no default path: the script refuses to guess.

---

## 4. Reproduce each contribution (table → command)

| Paper location | Content | Command |
|---|---|---|
| §3 comparison, Table 1 | 11 methods × BONN ATE | `python scripts/02_analysis/paper2_baseline_table.py` (data in `resources/baselines/`) |
| §3/§8 predecessor-stack main table | baseline arm, 7 sequences × 3 seeds | `bash scripts/paper2_fulltable/run_batch.sh` then `python scripts/02_analysis/paper2_tables.py` |
| §4 anatomy | bookkeeping dead weight / redundancy / heavy tail | `scripts/gs_compress/{anatomy,storage,tail}_census.py` |
| §5 codec R-D | 42-map R-D main table | `python scripts/gs_compress/rd_sweep.py --run-dir <base-run> ...` |
| §6 anti-dynamic cost | 5-sequence probe | `results/embrace_dyn/` (judge: `scripts/embrace_dyn/judge_p0.py`) |
| §7 placement / repair | online vs offline comparison | `python scripts/dynport_offline/repair_map.py --base-run <base-run> --arm R1 ...` |
| §5 generalization boundary | 36-map held-out | `results/paper2_rollout/evidence/` (R34; ATE not entered into the table) |

### A minimal end-to-end path

If you only want to see the pipeline work before running everything:

```bash
# 1) one short SLAM run to produce a base map
python slam.py --config configs/experiments/paper2_fulltable/r33_rebase_baseline_balloon.yaml \
  --seed 0 --eval --max-frames 40

# 2) anatomy census on that run
python scripts/gs_compress/anatomy_census.py --run-dir <path-to-run>

# 3) a codec sweep on the same map
python scripts/gs_compress/rd_sweep.py --run-dir <path-to-run>
```

A 40-frame run is a pipeline check, not a paper number.

---

## 5. Run the test suite

```bash
pytest tests/gs_compress tests/dynport tests/dynport_offline tests/embrace_dyn \
       tests/paper2_fulltable tests/lifecycle_paper2 tests/test_config_valid.py -q
```

Expected: 284 tests pass. These gate the codec round-trips, the repair operators'
invariants, and the table generators.

---

## Reproducibility notes

- **What belongs to this paper.** SWBA and LoopClosure are explicitly **not**
  part of this paper (R33 same-batch re-test judged net harm, +1.27~1.99 cm);
  the code is not included here. The `final`/`gate`/`swbaonly` arms' run data is
  retained as audit evidence only, not as results.
- **Offline-first.** The codec and repair operator are offline. They do not
  modify the online SLAM pipeline; the static layer is frozen bitwise during
  repair.
- **Base-map provenance.** Every bundle in `tools/release_assets.sha256` records
  the source run directory and content hash. If a hash check fails, do not
  proceed — re-download the bundle.
- **No hidden dependency on other repos.** This repository does not read from
  the RoGS-SLAM or RoGS-Densify checkouts. `papers/paper2/` here is the
  authoritative source of the paper; the copies elsewhere are frozen snapshots.

If a step fails, open an issue with the failing command, full error text,
`nvidia-smi`, `nvcc --version`, and `conda list | grep -E "torch|numpy"`.
