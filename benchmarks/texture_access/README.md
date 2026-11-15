# v1.0.9 W6 texture controls (PARTIAL)

```sh
MESA_SHADER_CACHE_DIR=/tmp/gles-cache python3 benchmarks/texture_access/run.py --config /path/to/mesa.json --output /tmp/texture-ab.json
```

Eight real GLES texture sampling A/B controls upload a 2×2 RGBA8 texture then draw/read back a 4×4 framebuffer. Four exact-domain coordinate rewrites agree; transpose, mirror, atlas offset and resolution collapse deliberately fail. Exact source hashes, texture input bytes in cases(), 64 output pixel bytes per arm, compiler/linker results and actual renderer are retained. Raw local Mesa results: `evidence/mesa.json`.

This is not a compression or throughput benchmark. ASTC/ETC2/KTX2 transcoding, mip/aniso/array comparisons, PBO streaming, CPU transcode latency, upload stalls, residency and real bandwidth are not measured (null), not zero. These eight controls do not satisfy the broader W6 acceptance alone. Existing `benchmarks/texture_pipeline/` remains the source of capability-selection tests; do not infer a measured gain from those tests or compression ratios.
