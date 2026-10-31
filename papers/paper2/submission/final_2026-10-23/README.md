# Paper2 — CVM 2027 submission package

**Package date**: 2026-10-23
**Version**: v8.18c
**Abstract deadline**: 2026-10-23 (AoE) · **Full paper deadline**: 2026-10-26 (AoE)

## Files

| File | Pages | SHA-256 (first 16) | Bytes | Role |
|---|---|---|---|---|
| `main.pdf` | 14 | `4f684d3e3ec4ce44` | 4,223,113 | Main paper (anonymous) |
| `supplementary.pdf` | 5 | `1ea0ea186703139a` | 574,322 | Supplementary material |
| `prior_work_anonymous.pdf` | 14 | `e4c199cb4b16280c` | 369,080 | Prior-work paper, anonymised (self-citation attachment) |

## Gates

- Main: 14 pages (limit 14 incl. references) / overfull 0 / missing_char 0 / undefined_ref 0
- Supplementary: 5 pages
- `pytest tests/paper2_fulltable/ tests/gs_compress/` → 74 passed
- No `our` / `my` anywhere in the main text (template blind-review rule)
- PDF metadata carries no Author/Title; no institution, email, acknowledgement, or grant ID

## Editable title / abstract / keywords

- Title: `A Dynamic-Scene Gaussian SLAM Map: Anatomy, Compression, and Offline Repair`
- Abstract: 218 words (see `main.pdf` p.1; plain-text copy available on request)
- Keywords: `dynamic scenes, 3D Gaussian splatting, SLAM, map compression, offline repair`

## Provenance

- Live source: `papers/paper2/paper2_cvm.tex` (`6141a0df926b7f34`, 61,922 B)
- PDF snapshot: `papers/paper2/archive/pdf_snapshots/paper2_cvm_v8.18c_2026-10-23.pdf`
- Full-version snapshot: `papers/paper2/archive/v8.18c_2026-10-23/`
- Version lock and change log: `papers/paper2/VERSION_LOCK.md`
- Baseline sum: `submission/final_2026-10-22/` is superseded by this folder.

## Note on the previous package

`final_2026-10-22/main.pdf` was v8.18b. Between the two, the title/abstract/keywords did
not change in substance; the changes were framing (scope statements, overclaim cleanup)
and two numeric-range corrections in §4 (rotation interval unified to the 14-map census
basis). See `VERSION_LOCK.md` §v8.18c for the full list.
