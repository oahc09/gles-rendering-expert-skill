# Two-bone GLES3 skinning representative (v1.1.0 W7)

```sh
python benchmarks/coverage/skinning/run.py --config DRIVER.json --output REPORT.json
python -m unittest discover -s benchmarks/coverage/skinning -v
```

Actual vertex shader uses a std140 UBO containing two column-major mat4 values
(128 bytes, queried block size checked), position VBO, four constant weights
[2,1,1,0] and integer joint indices[0,1,0,1]. The shader normalizes the weights
before linear blending. Pose0 is identity. Pose1 translates bone0 by(0.5,0) and
bone1 by(0,0.5). The independent CPU oracle reduces the known scalar weights to
translation(0.375,0.125); it does not call shader/matrix evaluation code.

Transform feedback captures all six post-skin vec4 positions from the same draw
that rasterizes into a16×16 RGBA8 FBO. Captured buffer is mapped after feedback
ends. Both poses are compared with a CPU-pre-skinned VBO fallback using another
real draw, not a simulated image. PPM goldens show the green8×8 quad in the two
positions. PPM is top-down; numeric images and GL readbacks are bottom-up.

Each driver executes7 draws: four positives (two poses×GPU/CPU fallback), three
pose1 negatives (unnormalized weights, transposed bone matrices, frozen pose0).
Mesa and ANGLE positives have position max error0 (budget1e-6) and exact pixels
(budget0). All three negatives fail both position and image validation. HOST_PASS
means those expected rejections occurred, never that bad animation was accepted.
All source hashes, numeric captured positions and complete images are retained.
No driver/OS identities, local paths, or executable fingerprints are published.

GLES3.0 fallback is CPU pre-skinning then VBO upload; no compute/SSBO or GLES3.1
requirement. A production fallback still needs CPU-cost/upload measurements.
This finite example does not support arbitrary skeleton hierarchy, imported
animation clips, interpolation, normals/tangents, nonuniform scale, dual-quaternion
skinning, morph targets, zero/negative weight policy or bone-buffer capacity
selection. Its shader epsilon protects division but is not validation of malformed
weights. Two discrete poses prove update sensitivity, not continuous animation.
GPU time, mobile power/bandwidth and physical-device accuracy remain NOT_MEASURED.
