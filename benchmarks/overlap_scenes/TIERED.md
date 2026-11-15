# Bounded grouping and reduced-resolution capability gates

Run `python3 benchmarks/overlap_scenes/tiered.py --config DRIVER_JSON --output REPORT_JSON`.
`--require-harness-only` is an explicit CI mode checking the rejection/fallback
contract only; it does not alter the JSON status or baseline-quality failures.
By default exit status remains nonzero if any baseline fails the original CPU quality gate.
`harness_contract=PASS` means rejection/fallback bookkeeping behaved correctly,
**not** that rejected baselines have become acceptable. CI may assert this separate
contract and the reported supported tiers, but must preserve baseline failures.

Three authored 8/24/48 Gaussian-alpha billboard tiers, three translating cameras,
64x64 targets. Each camera executes baseline, disjoint-group material sorting,
32x32 render + actual GLES nearest blit to 64x64, and deliberate foreground removal.
36 actual image readbacks and nine blits per driver. A CPU independent reference
and spatial layer heatmap are retained. All RGBA arrays and heatmaps are in each
report's deterministic ZIP; unzip beside report. These are not trained 3DGS assets.

Grouping is allowed only when conservative projected bounds of separate material
groups do not overlap. It preserves within-group depth order. Actual tint uniform
updates decrease from N to two. Draw count and estimated pixel coverage do not
change; no hardware speedup is inferred. Both software drivers produce exactly
identical baseline/grouped pixels in all nine views.

The half-resolution candidate is rejected in every view by the unchanged quality
limits (RGBA max 4 codes, silhouette disagreement <=2 pixels, alpha-centroid error
<=0.1 pixels). Baseline fallback is selected, but it is **not accepted** when the
baseline itself exceeds the CPU gate. This is the reduced-resolution layer
mechanism and rejection test; selective far-only composition with separately
preserved foreground is still unimplemented, not implied by this module.

Mesa: only tier 8 is acceptable across all three cameras. Tier 24 maximum CPU
color error is 5–6 codes; tier 48 is 7–11, with up to three silhouette pixels.
Overall `status=FAIL`, `harness_contract=PASS`. ANGLE: all tiers baseline CPU error
zero, `HOST_PASS`. Both drivers reject all nine foreground-removal negatives.
The Mesa accumulated blending/reference discrepancy is **not yet root-caused**;
no driver bug or incorrect CPU oracle is asserted and no threshold is relaxed.

No GPU timings, physical hardware, million-scale workload, performance improvement,
or general transparency reordering equivalence is claimed. Tier limits describe
only these authored inputs. Full tiered cost/throughput acceptance remains open.
