# W7 SDF / MSDF bounded representative

Implementation and primary-source rationale: [distance-text README](../../benchmarks/coverage/distance-text/README.md).
Actual experiment: `benchmarks/coverage/distance-text/run.py`.

Two scales, authored Euclidean SDF and synthetic perpendicular multichannel
rectangle atlas, linear texture sampling, median and cubic coverage, independent
CPU image oracle, complete actual pixels, goldens, and three incorrect shader
controls. An actual resolution-specific alpha-mask texture fallback is verified.
Mesa SDF32 exceeds the unchanged budget and takes that fallback; no claim that
all SDF rendering passed. HOST_PASS is the bounded rejection/fallback contract.

Remaining outside scope: real font loading, shaping/layout/kerning, edge-coloring
and arbitrary contour MSDF generation, atlas padding/packing/batching, animated
perspective and derivative footprint calibration, outlines as a supported style,
sRGB compositing, real hardware, throughput or memory-performance improvement.

Independent [precision diagnosis and costed route](../../benchmarks/coverage/distance-text/PRECISION.md) preserves that failure. On both software backends, explicit highp four-tap interpolation meets the same gate with exact finite images; changing sampler precision alone does not fix Mesa SDF32. The new route requires an explicit four-instruction budget, otherwise retaining the verified alpha fallback. Physical latency/bandwidth is unmeasured.
