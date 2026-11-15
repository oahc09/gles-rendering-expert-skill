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
