# Animation / skinning: finite GLES representative

Executable: `benchmarks/coverage/skinning/run.py`.
Tests, two CPU-authored PPM goldens and dual-software-driver full numerical reports
are colocated. This covers UBO matrix delivery, integer joint selection,
normalization of known nonunit four weights, transform-feedback position capture,
actual rasterization, CPU-pre-skinned fallback, and a stopped-pose negative.
It does not claim full animation-engine or all GLES API semantic coverage.

Mobile considerations: query uniform-block limits before choosing bone count;
std140 mat4 consumes64 bytes; matrix packing/transposition and byte layout must
match. CPU pre-skinning shifts work and vertex uploads to CPU/driver, not guaranteed
cheaper. Translation-only results do not validate normal transforms under scaling
or rotation precision on mobile hardware. Keep actual clip/hierarchy, zero-weight
and malformed joint-index handling as explicit application contracts, not inferred
from this small sample. Do not confuse captured position correctness with measured
GPU throughput. Existing original-version release gates remain binding.
