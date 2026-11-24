# RoGS-Map

**Dynamic-scene Gaussian SLAM maps: anatomy, compression, and offline repair**
(research content 2; under review at CVM 2027).

An object-level study of the **map** a dynamic RGB-D 3DGS-SLAM system produces:
an 11-system comparison of reproduced SLAM methods establishes where a dynamic
scene's point map is expensive and where it falls short; an **offline codec**
then compresses it, and an **offline repair operator** puts back the dynamic
content the anti-dynamic paradigm erased. Three contributions (all map-side):

1. **Map codec** — offline, per-map adaptive, learning-free 3DGS map
   compression (near-lossless ~6x / medium ~8.8x / aggressive ~15x).
2. **Map-side cost characterization** — the measurable cost of the anti-dynamic
   paradigm (vacated region +17.9–22.2 dB), plus geometric/appearance
   decomposition, map-structure anatomy, and heavy-tail load measurement.
3. **Offline map dynamic-repair operator** — DynaGSLAM-style dynamic GS
   management moved to offline placement (static layer frozen bitwise);
   J1 5.49–8.95 dB, 21/21 pass.

The system layer (tracking/rendering/efficiency) is **background**: predecessor
stack (= paper 1's method, see RoGS-SLAM) plus an 11-method comparison.
**SWBA / LoopClosure are not part of this paper** (same-batch re-test judged net
harm, +1.27~1.99 cm; excluded on narrative grounds), and their code is not
included here. Run data for the `final`/`gate`/`swbaonly` arms is retained as
audit evidence only.

## Installation

```bash
git clone --recursive https://github.com/BinGO620/RoGS-Map.git
cd RoGS-Map
./setup_env.sh          # conda env + two CUDA extensions (SHA-pinned) + Bonn/TUM datasets
conda activate rogs-map
bash scripts/download_assets.sh   # offline base maps (GitHub Release, PLY+trajectories, sha256-checked)
```

For a full step-by-step walkthrough — requirements, CUDA checks, environment,
dataset and release-asset download, per-contribution commands, and the test
suite — see **[REPRODUCING.md](REPRODUCING.md)**.

## Usage (table → command)

| Paper location | Content | Reproduction command |
|---|---|---|
| §3 comparison, Table 1 | 11 methods x BONN ATE | `python scripts/02_analysis/paper2_baseline_table.py` (data in `resources/baselines/`) |
| §3/§8 predecessor-stack main table | baseline arm, 7 sequences x 3 seeds | `bash scripts/paper2_fulltable/run_batch.sh`, then `python scripts/02_analysis/paper2_tables.py` |
| §4 anatomy | bookkeeping dead weight / redundancy / heavy tail | `scripts/gs_compress/{anatomy,storage,tail}_census.py` |
| §5 codec R-D | 42-map R-D main table | `python scripts/gs_compress/rd_sweep.py --run-dir <base-run> ...` |
| §6 anti-dynamic cost | 5-sequence probe | `results/embrace_dyn/` (judge: `scripts/embrace_dyn/judge_p0.py`) |
| §7 placement / repair | online vs offline comparison | `python scripts/dynport_offline/repair_map.py --base-run <base-run> --arm R1 ...` |
| §5 generalization boundary | 36-map held-out | `results/paper2_rollout/evidence/` (R34; ATE not entered into the table) |

## Offline base maps (GitHub Release assets)

The codec and repair operators are **offline post-processing**: their input is a
SLAM run's final PLY plus per-frame trajectories and config (heavy assets, not
tracked in git). `scripts/download_assets.sh` downloads them from the Release and
verifies sha256. `tools/package_release_assets.sh` builds the bundles; the run
list and hashes are in `tools/release_assets.sha256`.

Both tools require `MONOGS_OURS` to point at a checkout that contains the run
directories. There is no default path — the scripts refuse to guess.

## Project Structure

```
slam.py / utils/ / gaussian_splatting/ / gui/   # runtime core (= RoGS-SLAM upstream; pruning in PROVENANCE.md)
configs/experiments/{paper2_fulltable,paper2_rollout,...}/  # experiment arms
scripts/{02_analysis,gs_compress,dynport,dynport_offline,paper2_fulltable}/
results/                                        # criterion artifacts + evidence (R33 live batch + per-family verdicts)
papers/paper2/                                  # paper 2 live source (this repo is its authoritative copy)
resources/baselines/                            # 11-method comparison (Table 1 data source)
```

## Testing

```bash
pytest tests/gs_compress tests/dynport tests/dynport_offline tests/embrace_dyn \
       tests/paper2_fulltable tests/lifecycle_paper2 tests/test_config_valid.py -q
# 284 passed
```

## Provenance

This repository was rebuilt from monogs-ours@`31b0f0367` by dependency-closure
pruning; the copy list, deletions, and verification record are in
[PROVENANCE.md](PROVENANCE.md). Three-repo relation: RoGS-SLAM (paper 1) →
this repo (paper 2) → RoGS-Densify (paper 3); `diff -r utils/` shows the
per-paper mechanism differences.

## Acknowledgements

Built on [MonoGS](https://github.com/muskie82/MonoGS) and
[3D Gaussian Splatting](https://github.com/graphdeco-inria/gaussian-splatting).

## License

Released for **non-commercial research and evaluation use only**, inherited from
the Inria/MPII Gaussian-Splatting License that covers the rasterizer submodule.
See [LICENSE](LICENSE) for the combined terms and the per-component table.

## Citation

If you use this code, please cite the paper — see [CITATION.cff](CITATION.cff).
