# S03: bounded integrated UI + depth geometry + PostFX

This is an actual integrated GLES scene, not the earlier constant/checkerboard
PostFX-only subchain. A DEPTH24 + RGBA8 scene framebuffer renders two orthographic
3D planes at distinct clip-space depths. Near green geometry is submitted before
far red geometry: depth testing must retain the near surface despite later far
submission. Three discrete camera translations change geometry coverage. A
screen-fixed blue UI strip blends alpha 0.5 over the rendered scene with depth
disabled. A distinct texture-FBO PostFX pass swizzles RGB; a final separate FBO
presents the sampled result. Depth, UI and PostFX therefore affect the actual image.

Five variants at each camera: baseline, algebraically equivalent PostFX, half-size
PostFX plus nearest upsample, disabled-depth negative and opaque-UI negative.
Independent Python analytic coverage/depth/UNORM composition and nearest sampling
produce CPU golden pixels for **all three stages**, not a captured driver baseline.
A one-code RGBA8 threshold is fixed for CPU comparisons and final target quality.
Equivalent passes; half/depth/UI negatives reject at all cameras. A rejected
candidate selects baseline; passing finite quality is not performance acceptance.

```
python3 benchmarks/system_scenes/v109_s03/run.py --config DRIVER_JSON --output REPORT_JSON
python3 -m unittest discover -s benchmarks/system_scenes/v109_s03 -v
```

Both actual Mesa and ANGLE CLI executions exit 0 with HOST_PASS. Each executes
75 draws and 45 readbacks (15 runs × five draws and three stage readbacks). All
15 baseline/variant records retain complete bottom-up pixels, source hashes,
logical attachment events and two render-target transitions. Allocation-time FBO
binds are not counted as render-target transitions. API-derived clear, preserve,
full overwrite and later-consumer/store requirements are recorded; these are not
measured tile load/store, DRAM, bandwidth or hardware counters. No environment
fingerprints, OS metadata or local driver paths are included.

Scope: 8x8 static deterministic orthographic planes and three discrete camera
positions, unlit colors, one UI strip, channel-swizzle PostFX. This delivers a
finite integrated S03 correctness/quality chain, not production perspective meshes,
complex UI, temporal animation, blur equivalence or physical performance.
Physical timing is BLOCKED_BY_HARDWARE and release_acceptance remains false.

Global selection requires baseline validity across **all three cameras** before any
fallback is admitted. Candidates must pass all cameras; otherwise keep the valid
baseline, or mark UNAVAILABLE if the baseline itself failed. Production selection
never promotes the equivalent candidate without physical performance evidence.
