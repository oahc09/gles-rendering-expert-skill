# Precision, color and visual-safe quality changes

## Normative basis (historical context, checked 2026-11-01)

- [GLSL ES 3.00 specification, §§4.5, 8.4](https://registry.khronos.org/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf): precision qualifiers constrain range/precision; mediump/lowp are minimum guarantees, **not** a promise of a particular ALU width, register savings or performance. Query actual shader precision and test the relevant stage. Explicit half packing is a different operation from requesting mediump. This lab intentionally measures both independently.
- [GLES 3.0 specification](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf): texture storage encoding and shader arithmetic precision are separate. `GL_SRGB8_ALPHA8` sampling decodes RGB; alpha is not gamma encoded. Choose linear-space blending unless a documented artistic contract says otherwise. Floating-point color renderability must be checked; allocating RGBA16F does not prove FBO completeness.
- [GLES 3.1 specification](https://registry.khronos.org/OpenGL/specs/es/3.1/es_spec_3.1.pdf): the numeric probe uses compute SSBO writes and `GL_BUFFER_UPDATE_BARRIER_BIT` before API mapping. This is a GLES 3.1 experiment, not a GLES 3.0 compatibility claim.

No source above demonstrates a vendor-specific performance improvement. No recent-publication claim is made.

## Decision sequence

1. Record backend (native GLES versus ANGLE), GL renderer/version, shader precision queries, shader/asset hashes, target format, encoding, render scale and timestamp/seed.
2. Define reference expression or image, absolute numerical tolerance, per-region color error and temporal difference tolerance before optimization. See `benchmarks/visual_quality/thresholds.json` (`NumericErrorSpec-1`).
3. Keep long elapsed-time calculations highp or rebase/modulo time on a suitable high-precision CPU clock. Reducing precision of a large clock before range reduction can lose the motion increment. This lab uses deterministic 10,000-second snapshots plus an independent 1,024-addition accumulation test; it is not a 10,000-second live run.
4. Normalize normals at the needed precision; inspect specular peaks, silhouettes and rapidly changing water highlights separately. Do not infer precision quality from flat-color screenshots.
5. Check format and blend semantics independently: straight alpha expects SRC_ALPHA, ONE_MINUS_SRC_ALPHA; premultiplied content requires a compatible producer and blend equation. RGBA8 clips HDR values before tonemapping; RGBA16F renderability is capability-gated.
6. Dynamic resolution must actually resize the intermediate render target and reconstruct into fixed output. The lab's `scale` argument does this. Image tests can reject a scale, but cannot establish its speed, power saving, perceptual acceptability or thermals.
7. A pass at one GPU/driver does not certify another. Freeze reviewed per-platform goldens instead of automatically replacing the reference after a failure. Preserve a failing capture/heatmap and identify whether the cause is shader math, color management, intended artistic change or driver variation.

## Fallback / dual gate

If precision change fails any numeric/region/multiscale/temporal gate, retain highp or the known-good target/scale. If HDR target is unsupported, report capability blockage and choose an explicitly reviewed SDR path; never silently compare SDR against HDR as equivalent. If visual correctness passes but device timing/power is absent, result is `NEEDS_DEVICE_PERFORMANCE_AND_ART_REVIEW`, not automatic optimization approval. Backend-specific benefits require separate measurement.

The host baseline here is Mesa llvmpipe software GLES. It is L1 correctness evidence only. Mali, Adreno, PowerVR, ANGLE and Android physical-device visual/performance acceptance remain `NOT_RUN_DEVICE` / `BLOCKED_BY_HARDWARE`.
