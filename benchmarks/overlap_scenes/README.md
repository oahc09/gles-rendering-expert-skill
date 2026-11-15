# W4 projected overlap scenes (host implementation; physical performance unmeasured)

```sh
python3 -m unittest discover -s benchmarks/overlap_scenes -v
python3 benchmarks/overlap_scenes/projected.py --config DRIVER_JSON --output REPORT_JSON
```

Uses the existing differential GLES Host with an operator-provisioned single-driver JSON. The executable returns nonzero unless all expected positive/negative image controls and camera-shift checks pass. Public reports contain only scene/source/pixel evidence, not environment metadata or library fingerprints.

## Actual scene/render implementation

Four 64×64 RGBA8 perspective-projected scenes render separately submitted billboard quads at varying world depths with back-to-front alpha compositing:

- 18 Gaussian-alpha splat proxies (exp radial kernel), plus 2 offscreen objects.
- 15 disk particles, plus 2 offscreen objects.
- 8 overlapping tinted glass plates with position-dependent opacity, plus 2 offscreen objects.
- 10 layered rectangular UI cards, plus 2 offscreen objects.

The camera translates along X at -0.3, 0 and +0.3. Perspective scaling causes depth-dependent parallax. These are runnable analytic scenes, **not trained anisotropic 3DGS, refractive glass, a complete particle engine or full UI renderer**.

Each view runs baseline, conservative offscreen-object culling, and an intentionally unsafe foreground-drop counterexample. Culling reduces two draw submissions and must preserve every output pixel; it does not claim reduced fragment coverage, because removed objects were already outside the viewport. The unsafe candidate must fail the CPU golden. No speedup, bandwidth or power claim is made.

## Independent reference and evidence

CPU scalar pinhole projection, pixel-centre coverage, Gaussian/disc/glass alpha and per-layer RGBA8 quantized blending generate an independent reference. GLSL expands the raster quad by one pixel and reconstructs local coordinates from gl_FragCoord and the projected rectangle; analytic clipping owns the shape boundary; the reference does not consume rendered pixels. Every view stores CPU reference bytes, actual RGBA8 bytes and a 64×64 spatial layer-count heatmap. The heatmap is an analytical coverage estimate, not a GPU counter. Images use bottom-up raw RGBA8 (64×64×4 bytes).

Acceptance uses maximum RGBA8 error ≤4 (accumulated quantization across up to 18 translucent layers), ≤2 alpha-silhouette disagreements at alpha >12/255, and alpha-centroid discrepancy ≤0.1 pixel. Across the extreme camera positions, rendered centroid motion must agree with CPU motion within 0.1 pixel and exceed one pixel. Source hashes, image hashes, individual metrics and CPU refs are in `evidence/mesa.json`. Each of Mesa and ANGLE execution produced 36 images: 24 correct baseline/culling outputs and 12 rejected foreground-drop outputs, all as expected. Maximum correct-output color discrepancies were Mesa 4 and ANGLE 1 code values; silhouette disagreements were zero. Maximum camera-shift error was below 0.006 pixel on both implementations. Twelve structural/reference unit tests also passed.

These finite tests establish host correctness for authored scenes, not arbitrary simplification validity. Dynamic camera samples cover three viewpoints, not continuous animation or disocclusion exhaustiveness. Full anisotropic 3DGS, view-dependent color, actual glass refraction, LOD/background Gaussian merging, perceptual budgets and physical-device timing/counters remain unverified. W4 is still PARTIAL against the full plan.

## Artifact packaging

`evidence/mesa.zip` and `evidence/angle.zip` are deterministic ZIP archives with every actual image, CPU golden and heatmap. Extract beside the corresponding JSON before resolving its relative image paths:

```sh
cd benchmarks/overlap_scenes/evidence
unzip mesa.zip
unzip angle.zip
```

The JSON's artifact_archive records the archive SHA-256. All 36 actual images plus 12 CPU goldens and 12 heatmaps per implementation are retained. Archives were reopened and every reported image hash checked against its bytes.

## Boundary failure and fix

The first ANGLE run failed particle/UI CPU comparisons: maximum discrepancies reached 97 RGBA8 codes and UI silhouette disagreement reached 11 pixels. It also failed the 0.1-pixel camera-shift threshold. `pre-fix-angle.zip` retains the original complete failed report and pixels under `pre-fix/`; this failure was not overwritten or counted as PASS.

The initial implementation relied on a rasterized quad edge and interpolated local coordinates to define analytic shape coverage. That couples the CPU exact pixel-centre oracle to implementation-specific interpolation/subpixel rasterization at hard boundaries. The repaired implementation expands each raster quad by one pixel and applies the exact analytic projected shape test from gl_FragCoord inside the fragment shader. This separates conservative raster coverage from semantic clipping and removes interpolation from shape evaluation. Scene radii, positions, camera samples and acceptance thresholds remain unchanged. Both drivers then passed the same independent CPU reference and bad-foreground-drop controls. This is a harness portability repair, not a claim that ANGLE violates the GLES specification.
