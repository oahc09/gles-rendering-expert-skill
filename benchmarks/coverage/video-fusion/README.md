# Authored NV12 + UI fusion, finite GLES3 host representative

```sh
python3 benchmarks/coverage/video-fusion/run.py --config DRIVER.json --output REPORT.json
python3 -m unittest discover -s benchmarks/coverage/video-fusion -p 'test_*.py' -v
```

Reuses the matrix approach of `examples/texture_pipeline/yuv_planes.frag`, previously only source-compiled, but adds actual R8 Y / RG8 UV texture uploads, shader conversion and known UI source-over compositing. This is **authored CPU plane data**, not decoder output/native camera/AHB evidence. Original Android build/install/device blocker remains.

Exactly4×4 luma and2×2 interleaved UV, padded6-byte rows. Preflight enforces exact metadata fields, dimensions, integer stride≥rowbytes≤64, exact stride×rows storage size, byte types/range. De-padding is explicit before tight GPU uploads with UNPACK_ALIGNMENT1. Matrix BT709, limited8-bit range, centered source siting metadata, and nearest-block reconstruction are required. Fetch uses integer p/2: nearest 2×2 chroma block replication, **not a general centered chroma reconstruction filter**. Unsupported/missing metadata fails before creating Host; four fixture rejections each execute zero draws. Unit tests cover truncated/excess planes, boolean-as-byte/stride and padding independence.

Convert limited Y(16..235), chroma(16..240 centered128), then clamp nonlinear SDR RGB. UI uses fixed RGB(.8,.2,.4), alpha .25 left/.5 right. OVER is explicitly in **encoded/nonlinear RGB domain**, not physically correct linear-light blending. CPU oracle uses expanded independent BT709 inverse coefficients rather than importing GLSL or previous policy. RGBA fallback uploads CPU-converted quantized RGB then performs the same real UI shader draw. No performance superiority is asserted.

Each driver two distinct frames × four actual draws/readbacks =8/8. GPU-normal and CPU-upload fallback maximum error1, fixed acceptance budget2bytes. Wrong full-range interpretation errors10; swapped UV errors135/143, all actually rendered and rejected. No budget relaxation. All64 output bytes retained for independent checks; alpha255 is expected from opaque background OVER. Candidate corruption is deliberate test mode, never auto-selected by valid metadata.

Logical texture storage16+8+64=88bytes plus64byte RGBA output (ignores allocator padding/cache); upload payload88bytes/frame. No hardware bandwidth measurement. Performance/physical GPU/decoder/AHB/HDR/P010/protected pipelines remain NOT_RUN. No private environment metadata. Sourcehash integrity is not third-party attestation.
