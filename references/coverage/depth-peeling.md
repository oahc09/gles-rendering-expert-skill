# Bounded depth peeling: crossing layers with explicit overflow rejection

This is a new finite exact-OVER operator path; previous weighted-OIT19/28-byte failures and global-sort crossing rejections remain unchanged. No quality budget is widened.

Primary API basis: [official GLES3.0 specification](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf), depth textures/framebuffer completeness, depth testing, occlusion queries and blend state; the locally reviewed [GLES3.2 specification](https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/1cdd228e34966dd6b95bd203e9f84faba0f371a1/specs/es/3.2/es_spec_3.2.pdf) retains the relevant core mechanisms. No extension-only per-target blend is required.

## Finite geometry, depth precision and resources

Full-screen analytic layers use z=a+b*x, x at pixel centers on a4×4 grid. Two intersecting planes (.1,.2) and(.9,-.2) exchange front/back order across the image; a third green plane at .45 supplies a three-layer crossing case. Straight RGB/alpha are fixed and source-visible. Alpha composition is over transparent black.

Fragment depth is explicitly mapped to the dyadic grid `floor(z*4096+0.5)/4096`, stored in **DEPTH_COMPONENT32F**, and sampled with **highp sampler2D**. Fragment highp precision is queried and required to have at least23 fraction bits. Binary steps1/4096 are exactly representable in float32; shader comparison uses `z_quantized <= previousDepth`, **no arbitrary epsilon**. CPU preflight rejects equal quantized bins, ties, nonfinite/malformed values, and depths outside[0,1). Plane coefficients are restricted to[-1,1]. It compares CPU-double, separately rounded float32 multiply/add and fused-style float32 quantization bins, rejects disagreement and samples within .001 scaled units of a half-bin boundary. Quantized depth must stay below4096, so values rounding to the clear-depth1 are rejected before drawing. Actual fixed planes have minimum raw separation .05, much larger than a bin. This is not a guarantee about arbitrary meshes near quantization boundaries; sub-bin layers are deliberately unsupported, not silently merged.

Two ping-pong FBOs each contain a distinct RGBA8 color texture and DEPTH32F texture. Current pass samples only the previous depth texture, never its own writable depth attachment. Both formats' FBO completeness is checked. An independent RGBA8 accumulation FBO samples only the current peeled color after the geometry pass finishes. Core texture unit availability is queried.

Each pass clears depth to1 and color to0, uses LESS depth test and writable depth. The first pass chooses the nearest fragment; later passes discard depths at/before the previous peeled surface and choose the next nearest. Output is premultiplied color. Composition uses ONE_MINUS_DST_ALPHA / ONE, front to back. Normal framebuffer-write then texture-read ordering is used; no compute/image barrier is being omitted.

## Layer budget is a correctness boundary

For a budgetK, actual geometry runs **K+1** times. The extra pass uses ANY_SAMPLES_PASSED query to detect an uncomposited residual layer. Any samples on that pass reject the result as `LAYER_BUDGET_OVERFLOW`, even if an image looks plausible. No truncated image is admitted.

Missing geometry remains a separate issue: if input submission omits a layer, the overflow query cannot know it existed. The fixed experiment's independent complete CPU oracle catches the missing-layer negative; a production importer would need its own trusted completeness contract.

Ties, a same-quant-bin near pair, malformed input, a depth rounding to1 and a half-bin boundary exercise actual preflight rejection branches before issuing their geometry draws; all five record zero geometry/composition/readback operations.

## Actual results

Each Mesa and ANGLE process completed107 geometry draws,28 composition draws,38 readbacks and38 occlusion queries. CLI exit0 `HOST_PASS`.

- Three crossing layers, all6 input permutations: final max error1 byte against independent per-pixel CPU OVER; permutation difference0. Each of the3 actual peeled color stages matches an independently recomputed nearest-to-farthest premultiplied RGBA8 oracle exactly.
- Two crossing layers: max error1 byte, query sequence true,true,false.
- Three layers with budget2: true,true,true, rejected for overflow; image deviation48bytes.
- Missing middle layer: rejected by CPU quality comparison, deviation128bytes.
- Wrong-depth negative disables the peel exclusion: repeatedly captures nearest surface, deviation96bytes and overflow, rejected.

All accepted images satisfy the unchanged ≤2byte threshold. CPU OVER oracle sorts analytic depths independently and computes real-valued compositing before final UNORM conversion; it does not reuse GPU peeling logic. Intermediate color oracle separately checks every stage, so a final accidental compensation cannot hide a wrong peel.

## Initial failure and correction

`initial-attempt/` preserves the first failing source and both reports. It used the wrong blend constant (ONE_MINUS_DST_COLOR rather than ONE_MINUS_DST_ALPHA) and an implicitly low-precision depth sampler. The final implementation corrects blend state, explicitly qualifies sampler precision and uses a dyadic depth domain. No single-variable A/B was performed to assign every initial artifact to one cause; the original failure is retained rather than retrospectively called a pass.

## Cost and limits

Allocation is20bytes/pixel: two*(color4+depth4)+accumulator4, excluding driver overhead. ForN input layers and budgetK, geometry work is(K+1)*N draws plusK composition draws, K+1 color/depth clears and synchronous query/readback costs in this diagnostic. This is intentionally more work than approximate OIT and is **not a measured performance win**. No bandwidth/DRAM/tile-residency claim is made.

Finite full-coverage primitives only: no clipping, opaque occlusion, texture cutouts, MSAA per-sample ordering, refraction, arbitrary dynamic mesh bounds or context loss. Physical devices, SDK deployment and provider evaluation remain NOT_RUN. Quantized ties are rejected rather than assigned an unjustified order. Global sorted-alpha is not substituted when crossing order is unknown.

```sh
python3 benchmarks/coverage/depth-peeling/run.py --config DRIVER_CONFIG.json --output REPORT.json
python3 -m unittest discover -s benchmarks/coverage/depth-peeling -p 'test_*.py' -v
```

Eleven tests verify preflight, independent per-stage oracle, final thresholds, actual overflow/error rejection, counts, hashes and report sanitization. Reports omit local paths and OS/library fingerprints. Original weighted-OIT evidence is unchanged; the new executable is wired into candidate CI without waiving inherited gates.
