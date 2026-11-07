# Executable pipeline diagnostic playbook

Run `python benchmarks/pipeline/diagnose.py` for ten JSON reports, each containing
symptom → capture → minimal reproduction → root cause → fix → regression.
`python -m unittest discover -s benchmarks/pipeline -p 'test_diagnostics.py' -v`
asserts that all broken cases fail the intended invariant and corrected cases pass.

1. Variant feature macro selects compute on GLES 3.0: capture source/macros and
   queried version; compare 3.0 rejection against the same 3.1 feature selection.
2. Driver-local program cache: capture device/source identity and link status;
   mutate driver identity and assert key invalidation, preserving identity stability.
3. Material ABI: compare packed host offset 4 with actual std140 vec4 offset 16;
   capture reflected offsets, pad the host struct and assert the corrected offset.
4. Framebuffer feedback: same-object read/write graph rejects; ping-pong/sequential
   graph succeeds. Capture actual attachments, levels, layers and draw call state.
5. Missing image-write visibility barrier: texture fetch fails the static contract;
   TEXTURE_FETCH_BARRIER_BIT succeeds. Capture dispatch/barrier/draw order.
6. Invalid MSAA resolve: unequal extents reject, equal-size NEAREST resolve passes.
   Capture source/destination samples, formats, rectangles and mask.
7. Double sRGB conversion: exact piecewise CPU transfer function demonstrates the
   midtone error; encode once. Capture texture/FBO encodings and shader conversion.
8. Premultiplied-alpha dark edge: deterministic compositing shows duplicate alpha
   multiplication; use a single multiplication and matching blend factors.
9. HDR clipping: UNORM clamp before tone mapping differs from FP intermediate;
   map 4.0 to 0.8 before encoding and check supported float renderability.
10. Cold shader compile work: cache miss invokes the actual cache helper's source
    compile callback. Capture real compile/link spans for startup latency; callback
    execution alone does not establish a latency regression or optimization gain.

These are CPU_MODEL_REPRODUCED synthetic experiments, not real driver failures.
The reports explicitly retain hardware NOT_RUN. Color equations are independent
numeric oracles, not screenshots or screen calibration. A hardware regression
requires backend/driver, GL errors, actual frame capture, golden tolerance and timing
where relevant. No negative GPU test deliberately depends on undefined feedback.
For a driver compiler failure, reuse `benchmarks/reducer/reduce.py` with its actual
compiler oracle and crash/timeout handling; do not claim these small CPU fixtures
are minimized device crashes or one-minimal shader failures.
