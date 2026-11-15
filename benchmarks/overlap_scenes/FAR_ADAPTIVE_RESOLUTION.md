# 48² far reconstruction with held-out camera checks

`python3 benchmarks/overlap_scenes/far_adaptive_resolution.py --config DRIVER_JSON --output REPORT_JSON`

A new finite alternative to the old32² candidate renders actual far geometry to
48×48 RGBA8, reconstructs into64×64 through four-fetch bilinear interpolation,
and draws foreground independently at64×64. The ratio is genuinely noninteger:
`scale=64/48`, `position=fragmentCenter/scale-0.5`, not integer division. No
full-resolution far compensation, floating format, alpha bias or changed target
is used. Original64² per-layer RGBA8 CPU goldens and4/2/.1 gates stay fixed.

Besides original cameras -0.3,0,+0.3, four held-out translations
-0.45,-0.15,+0.15,+0.45 are included. A global strategy must pass all seven;
accepting only the original views would conceal a generalization failure.

## Results: more resolution is not sufficient

Actual dual-driver results preserve quality failure:

| Camera | Mesa silhouette disagreements | ANGLE disagreements |
|---|---:|---:|
| -0.45 | 1 | 1 |
| -0.30 | 0 | 0 |
| -0.15 | 4 | 4 |
| 0 | 2 | 2 |
| +0.15 | 3 | 2 |
| +0.30 | 2 | 2 |
| +0.45 | 5 | 5 |

The original three views now pass, but held-out views exceed the unchanged
2-pixel silhouette budget. Independent CPU48² reconstruction itself predicts
4 and5 mismatches at -0.15/+0.45, so this failure cannot be attributed solely
to Mesa arithmetic. Candidate selection is rejected globally on both drivers;
validated baseline remains selected for every view. No per-frame switching.

Each run performs21 image readbacks, including full baseline,48² candidate,
and deliberate foreground-drop negative in every view. Both drivers pass
mechanism-oracle correctness, baseline and rejection-contract checks. Full
visual report remainsFAIL. Actual CLI exits: default1, contract-only0 on both.
Persisted-report tests verify complete/unique seven-camera coverage, missing
holdout rejection, invalid-baseline UNAVAILABLE and unchanged gates.

## Logical cost, not speedup

Far attachment area is2304 vs baseline4096 pixels (43.75% fewer target pixels).
Far plus final RGBA8 logical storage is25600 vs32768 bytes. Both still issue
8 draws/view; reconstruction costs up to16384 source-level texel fetches and
81920 logical read/write bytes across4096 output pixels. Driver optimization,
cache, tiling, real residency and actual DRAM/GPU time are unknown. Smaller area
does not establish a measured benefit, especially when quality is rejected.

The JSON and deterministic ZIP retain every target/mechanism/actual image and
executed source hashes. Earlier32² reports remain unchanged. The experiment
shows why enlarging the far target is not a monotonic guarantee under a strict
quantized alpha-silhouette gate; it does not justify threshold tuning or choosing
a favorable camera subset. No further resolution search is promoted as success.
