# Adjacent duplicate background profile compaction: bounded A/B

`python3 benchmarks/overlap_scenes/background_merge.py --config DRIVER_JSON --output REPORT_JSON`

A deliberately strict merge candidate combines only adjacent background pairs
with identical position, depth, radius, RGB/alpha and Gaussian profile, depth >=4.
Foreground objects are never touched. For identical source color, ideal
source-over composition has alpha `1-(1-a)^2`; the replacement fragment evaluates
this exact nonlinear alpha profile. It is **not** one Gaussian with averaged
parameters, arbitrary splat clustering or trained 3DGS compression. Fixed-point
per-layer RGBA8 rounding means the ideal identity is not generally pixel exact.

Four background duplicate pairs and three foreground UI billboards run at three
translated cameras. Actual GLES baseline11 draws, compacted7 draws, and an
incorrect single-alpha/drop-copy variant are read back. CPU goldens remain the
original per-layer RGBA8 scene. Foreground ROI max error and existing full-image
color, alpha silhouette, centroid and cross-camera parallax gates are unchanged.
CPU geometric covered-fragment sample estimates are reported separately from
actual draw counts; neither is a hardware bandwidth/performance measurement.

## Actual outcomes: both reports intentionally FAIL

Each driver executes nine image readbacks. All three drop-copy negatives fail
as expected (color errors64–65). Foreground ROI error is <=2 codes on Mesa and
<=1 on ANGLE, but this does not excuse background silhouettes:

- Mesa baseline at camera -0.3 has max color5 >4. Merged at -0.3 and0 has three
  silhouette mismatches >2; +0.3 passes. No strategy passes the full tested camera
  set, so **global policy UNAVAILABLE**, not an accepted baseline fallback.
- ANGLE baseline passes all cameras. Merged at -0.3 has three silhouette
  mismatches >2, while0 and+0.3 pass. **Global policy keeps baseline** across all
  cameras and rejects the candidate globally.

Per-view records are diagnostics only, not runtime choices. There is no
camera-dependent strategy switching that could introduce flicker. A single
strategy must pass all tested cameras and parallax; unseen views remain unproven.
The report preserves failures and the CLI returns nonzero; this is not a newly
passing optimization or a reason to widen tolerances. Earlier scene evidence
is unchanged. This experiment supplies an actual merge mechanism plus a useful
counterexample to assuming algebraic alpha equivalence implies UNORM image
acceptance. More general merge and selective far-resolution composition remain
open.

Evidence JSON includes authored scene inputs, source hashes, all metrics and
global policy. Deterministic ZIP retains full actual/CPU64×64 RGBA8 images and
baseline layer coverage. Extract beside the report. Physical performance remains
NOT_MEASURED; fewer draws and mathematical layers alone do not establish speedup.

`--require-contract-only` allows CI to check complete GL readback, rejection of
all negative controls and the fixed global policy while preserving report FAIL.
Default CLI still fails on visual failures. An invalid baseline always makes
the strategy UNAVAILABLE, even if a merge candidate happens to pass.
