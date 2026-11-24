# PROVENANCE — how this repository relates to monogs-ours

- **Source**: `/data/monogs-ours` @ `31b0f03670a4366e8c6a5a7012963962a8203663` (branch
  `feat/bpw-densification`). monogs-ours is not split or modified; it serves as the
  backup repository.
- **How it was built**: manifest copy (`/data/monogs-export/manifests/rogs_map.yaml`)
  → subtraction → overlay patch → verification. Every step can be rebuilt
  deterministically from the backup repository.

## Organization principles

Same as RoGS-Densify/PROVENANCE.md (subtraction never renames, explicit inventory,
same-origin core, explicit inheritance, criterion artifacts in-repo).

## Code subtraction (changes to the core files)

### Removed modules (11)

- **Paper-3 densification** (2): `utils/{densification_selection, selective_densification}.py`
- **SWBA family** (5): `utils/{swba, loop_closure, place_recognition, mast3r_verify, dba_lite}.py`
  — rationale: the R33 same-batch re-test judged net harm (every SWBA-bearing arm
  +1.27~1.99 cm, `results/paper2_fulltable/README.md`); narrative red line "SWBA /
  LoopClosure never appear" (`papers/paper2/R2_NARRATIVE.md:111`); the storage claim
  that depended on the gate arm was withdrawn (D2-031). Run data for the
  `final`/`gate`/`swbaonly` arms is retained for audit only.
- **Kept**: `dyn_port_{buffer,online,offline}.py` + `dynport_causal_log.py` (§7 temporal
  placement comparison; the online column is part of the paper's evidence chain).

### Wiring changes (monogs-ours source line numbers)

| File | Source lines | Content |
|---|---|---|
| `slam.py` | 41–47 | loop_closure/dba_lite imports |
| `slam.py` | 419–461 | DBA/LoopClosure closing three-arm block (the DynPort causal-save block is kept) |
| `utils/slam_backend.py` | 142–164 | dba_lite/selective_densification/densification_selection/static_prob imports |
| `utils/slam_backend.py` | 354–364 | FDose event-ordinal reset |
| `utils/slam_backend.py` | 406–445 | init-site vector dispatch → pure-scalar `densify_and_prune` |
| `utils/slam_backend.py` | 798–822 | selective residual-EMA ledger block |
| `utils/slam_backend.py` | 829–873 | map-site vector dispatch + log_sel_dens_state → pure scalar |
| `utils/slam_backend.py` | 1595–1601 | P2a DBA diagnostic block |
| `utils/slam_frontend.py` | 52 | swba import |
| `utils/slam_frontend.py` | 413–415 | Route B SWBA init |
| `utils/slam_frontend.py` | 2928–2962 | Route B SWBA health gate and call block |

Equivalence: under every paper-2 arm configuration the removed branches are
inactive; `compute_per_gaussian_knobs`/`log_sel_dens_state` return early with zero
side effects when disabled (no RNG consumed), so the scalar path is bitwise
identical (same verification as RoGS-SLAM).

## Results selection (criterion-artifact policy)

- **paper2_fulltable**: keep `r33_rebase_*` (four arms, 84-run live batch; the single
  source of truth for the main table is `evidence/manifest_r33.json`), `effctl*`
  (Tab.4 same-code timing batch, D1-027), `render_compare*` (Tab.2r/3s render sources),
  and `evidence/`. **Discarded**: the superseded r29/r30/r31/r32/v2 batches (219
  directories, ~108 MB) and the legacy `{seq}_{arm}_seed*`; the verdict/erratum chain
  is complete in the individual verdict markdowns.
- **paper2_rollout**: keep `r34_*` (needed by the fingerprint cross-batch equivalence
  gate G2-S1) + `evidence/` (R34 ATE is not entered into the paper table; the
  conclusion is carried by the verdict) + the top-level diagnostic markdowns.
- **lifecycle_paper2**: evaluation instrument library; keep `evidence/`.
- **Trajectory policy**: keep `plot/trj_full_final.json` (needed for the sim3 positive
  control and offline base-map reproduction); per-KF `trj_N/stats_N` and images are
  not tracked. PLYs are never tracked (base maps are delivered via Release).

## Paper 2 live source (papers/paper2/)

This repo is the **authoritative copy** of `papers/paper2/` (tex/tables/figures/
supplement, 39 MB; the archive version snapshot, 79 MB, is not included). This
resolves the earlier duplication between monogs-ours and biyelunwen. The thesis
repository will henceforth reference it or take snapshots.

## Test selection (honest account)

All reproduction/gate tests are kept (284, all green). **Four monorepo-governance
gates were removed** (unrelated to reproducibility; they depend on the backup
repository's git history and `archive/closed_families`):

- In `tests/embrace_dyn/test_dyn_probe.py`:
  `test_causal3_measurement_code_committed_before_run` /
  `test_causal3_analysis_provenance_recorded` (they hard-code monogs-ours commit SHAs
  and assert ancestry, which a rebuilt repository structurally cannot satisfy;
  pre-registration provenance is carried by the monogs-ours history and the evidence
  file dates);
- `tests/lifecycle_paper2/test_gate1_class_sweep.py`,
  `tests/lifecycle_paper2/test_sweep_citation_claims.py` (whole-repository text /
  archived-family sweeps — development discipline, not reproduction gates).

Overlay mechanism: the revised `test_dyn_probe.py` lives in
`/data/monogs-export/overlays/` and is copied over after.

## Verification record

| Item | Result |
|---|---|
| AST import closure | complete (only namespace-package false positives) |
| `py_compile` slam.py / slam_frontend.py / slam_backend.py | pass |
| Full pytest gates | **284 passed, 0 failed** (gs_compress/dynport/dynport_offline/embrace_dyn/paper2_fulltable/lifecycle_paper2/test_config_valid) |
| Submodule pins | `diff-gaussian-rasterization@43e21bff`, `simple-knn@44f764299` |
| 2060 smoke A/B (40 frames, r33 baseline balloon) | see below |
| Offline-track rd_harness single point | see below |

## Numeric verification matrix (paper PDF ↔ table tex ↔ generator ↔ run CSV, full chain)

| Paper table (\input) | Content | Full-chain verification |
|---|---|---|
| tab_baseline | 11 methods x BONN system comparison (incl. the Prior RGB-D stack row) | pytest gate (generator == committed tex) + **PDF 103/103 cells hit** |
| tab2r_render / tab3s_static | rendering / static metrics | gate + **PDF 14/14, 22/22 hit** |
| tab4_efficiency | same-code timing, two FPS columns | gate (non-degradation + median recompute) + **PDF 14/14 hit** |
| tab_rd | R-D main table, 42 maps | gate + **PDF 58/58 hit** |
| tab4d_ablation / tab_dyncost_seq / tab_dynport | 4D ablation / anti-dynamic cost / placement comparison | gate + **PDF 10/10, 10/10, 8/8 hit** |
| R33 four-arm main table (tab1_main; audit only, not \input by the paper) | baseline/swbaonly/final/gate | pytest coverage 7x4 all valued + sim3 positive control 60+ samples, both paths agree |
| §5 generalization boundary (rollout) | R34, ATE not entered into the table | carried by the evidence verdict |

**PDF spot-check = 239/239 numbers across 8 tables, 100% hit** (pdftotext full-text
search, 2026-11-01). Config parity: 347 YAMLs byte-identical to
monogs-ours@31b0f0367 (parity check).
The core's differences from RoGS-SLAM are exactly the expected per-paper delta: the
four dynport files (§7 online comparison column) plus two wiring files
(`slam.py`/`slam_backend.py`); the frontend is byte-identical to RoGS-SLAM.

## Incident record (2026-11-01; found and fixed by the parity machine check)

`copy_by_manifest` is an overwriting copy: a second full copy added while
supplementing the embrace scripts reverted the completed subtraction (9 module
deletions + 11 wiring edits), so commit `aada4074` and everything before it was
actually clean monogs-ours, contradicting the PROVENANCE description (the smoke A/B
at that time compared clean vs clean and had no discriminating power).
Commit `15c99e2c` redid the surgery and re-verified with the real surgical version:
pytest 284 passed, smoke A/B ATE Δ = 0.0137 cm (vs the same clean reference 0.7458),
parity re-check passed.
**Lesson recorded**: after any manifest re-copy, always re-run
`config_parity_check.py` + the gates.

## Smoke A/B and offline-track note

- **(Erratum)** The first A/B record below was taken during the "re-copy revert
  incident", when the in-repo code was the clean source; that comparison has no
  discriminating power and serves only as a CUDA-noise reference. **The valid record
  is the real surgical comparison after the fix (commit `15c99e2c`): ATE RMSE 0.7321
  vs 0.7458 cm (Δ = 0.0137 cm, noise level), KF-ATE 0.8947 vs 0.8743 — the
  subtraction did not change pipeline behavior.**
- **Smoke A/B (first run; erratum above)**:
  `configs/experiments/paper2_fulltable/r33_rebase_baseline_balloon.yaml`,
  `--max-frames 40 --seed 0`, same machine and card (RTX 2060), one run each;
  reference = the clean copy at monogs-ours@31b0f0367. ATE RMSE 0.7208 vs 0.7458 cm
  (Δ = 0.025 cm), KF-ATE 0.8885 vs 0.8743, per-frame mean 0.6469 vs 0.6689 — the Δ
  is an order of magnitude below the same-config cross-batch noise floor
  (0.18–0.62 cm) and the same order as RoGS-SLAM's A/B (Δ = 0.022 cm).
  **Verdict: PASS.**
- **Offline-track single point**: rd_harness on the PLY the smoke run produced, full
  chain (codec encode → reconstruct → render → partitioned metrics): 13.80 B/prim,
  ratio 5.80x, PSNR 18.077 / static 30.578 — the codec line in the pruned repo is
  complete and usable.
- **Release base-map assets**: `tools/derive_release_runs.py` derives **63 base-map
  runs** from the evidence JSON (RD-legacy baseline + repair-leg r33 baseline 7x3;
  zero missing on disk); `tools/package_release_assets.sh` packages the three
  criterion artifacts per run and emits a sha256 manifest
  (`tools/release_assets.sha256`); `scripts/download_assets.sh` downloads + verifies
  + restores.

## Archiving policy (registered 2026-11-04; user instruction, applies to every repo)

- **Keep only the latest in the working area**: outdated versions, drafts, and
  historical snapshots all move into this repo's `archive/` (archive in place, named
  `{semantic}_{YYYY-MM-DD}`), never left scattered at the top level.
- **Archive ≠ delete**: archived items are evidence keys; ledger pointers are not
  rewritten; every archive location gets a `README.md` and is registered in the
  in-repo index.
- **Repo independence**: experiments are always run back in monogs-ours; this repo
  only takes "criterion-confirmed" result snapshots (the four-step sync is in
  monogs-ours `/data/master-thesis/WORKFLOW.md`). This repo carries its own gates and
  PROVENANCE, so it can be re-verified without the monogs-ours working area.
- **Milestone-triggered sync**: only re-run the manifest and full gates and update
  PROVENANCE at milestones (verdict landed, submission, etc.); do not sync routinely
  (to avoid snapshot drift).
