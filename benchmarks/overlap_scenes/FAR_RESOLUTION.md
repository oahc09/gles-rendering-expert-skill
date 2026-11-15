# Independent far-resolution pass with preserved foreground

`python3 benchmarks/overlap_scenes/far_resolution.py --config DRIVER_JSON --output REPORT_JSON`

This is an actual separate-pass implementation, not whole-scene resizing or a
CPU-resampled image presented as GPU work:

1. Render four Gaussian-alpha distant billboards into a dedicated RGBA8 texture
   FBO, either64×64 baseline or32×32 candidate.
2. Bind a different64×64 target and copy the far texture with a full-screen
   `texelFetch` nearest reconstruction. The copy disables blending, preserving
   already composited premultiplied color/alpha without multiplying twice.
3. Draw all three near UI billboards at64×64 using normal source-over blending.
4. Read the final framebuffer. Far and foreground must be nonempty and strictly
   depth-separated; this is not safe for interpenetrating near/far objects.

Independent CPU scalar projection/opacity/per-layer RGBA8 quantization generates
both the fixed original64×64 target and each mechanism's own resolution oracle.
**The low-resolution oracle never replaces the full-resolution quality target.**
All foreground objects remain at full resolution in baseline and candidate.
A deliberate foreground-drop variant is a negative control, not an optimization.

Three camera translations -0.3/0/+0.3 run all three arms: nine actual readbacks,
66 scene/copy draw calls per driver. Source shaders after resolution substitution,
copy vertex, CPU dependency and runner hashes are included. JSON maps the one
selected global strategy back to each camera's retained image. No per-frame
switch between baseline and candidate is allowed.

## Results: rejected optimization, working mechanism

Both Mesa and ANGLE baseline views pass original unchanged gates. Actual GPU
output agrees with each mechanism's independent CPU oracle within the same
limits. Both drivers reject **all three** low-resolution candidates against the
original64×64 target and reject all foreground-drop negatives. Thus global policy
keeps baseline for every camera. Original visual status remains **FAIL**, not
HOST_PASS. Foreground ROI errors and camera parallax are reported separately.

`--require-contract-only` checks complete and unique camera/variant coverage,
actual complete readback, mechanism-oracle correctness, negative rejection and
valid global selection. It does not turn visual failure into success. Verified
CLI exits on both drivers: default1; contract-only0. Empty/duplicate/missing
reports cannot select a candidate; an invalid baseline makes the entire strategy
UNAVAILABLE. Saved-report unit tests verify these conditions after serialization.

The deterministic ZIP preserves complete actual, fixed-target and mechanism-
oracle images (64×64 bottom-up RGBA8). Extract beside the report. Far attachment
area is smaller but draw count is not reduced and a copy pass is added; actual
GPU time, bandwidth and physical-device benefit are NOT_MEASURED. General scene
partitioning, better reconstruction and a candidate passing original visual
acceptance remain open. Earlier failures and thresholds were not changed.

Report `thresholds` explicitly records unchanged4-code /2-silhouette /.1-pixel
centroid/parallax limits. `logical_work_comparison` records far target area
4096→1024 pixels and RGBA8 attachments32768→20480 bytes (far plus final target).
Both arms still issue8 draws and copy4096 output pixels. Full-target per-layer
work bounds and copy logical bytes are not actual invocations, residency or DRAM
traffic; cache/tiling/compression and performance remain unmeasured.
