# v1.0.9 W3 host controls (PARTIAL)

Run from repository root:

```sh
python3 benchmarks/shader_ab/build_cases.py
python3 -m unittest discover -s benchmarks/shader_ab -v
MESA_SHADER_CACHE_DIR=/tmp/gles-cache python3 benchmarks/shader_ab/run.py --config /path/to/mesa.json --output /tmp/shader-ab.json
```

The config is a single `{"kind":"mesa","egl":"/path/to/libEGL.so.1","gles":"/path/to/libGLESv2.so.2"}` driver configuration, reusing `benchmarks/differential/run.py` Host. Only load trusted operator-provisioned drivers. Run in a fresh process per driver. No download or package installation is performed.

16 finite authored fragment A/B pairs are actually compiled/linked/drawn/read back in an RGBA8 FBO. 14 equivalent-domain controls pass within one RGBA8 code, 2 deliberately different alpha/color controls fail. `sources/` files and `cases.json` are reproducible via build_cases.py. Draw records hash the executed fragment and include compile/link diagnostics, GL errors and all 64 pixel codes. Public evidence omits environment fingerprints and local paths; full original captures remain private. This is baseline-vs-candidate image agreement, **not proof of general shader equivalence**.

The same runtime executes four overlap proxy scenes. `evidence/mesa.json` records local software execution, not timing or a physical device benchmark. 22 structural/negative unit tests are independent of the actual execution report. Test fixtures are never provider/model scores.

**Incomplete W3:** UBO/SSBO access comparisons, texture format changes, discard/depth and compute/draw fusion are not yet implemented here. Precision testing covers exact binary pixel-centre inputs, not the high dynamic range distribution. No GPU speedup is claimed. Do not mark W3 complete merely because sixteen authored pairs exist. Hardware performance, temperature, counters, cross-driver reruns and dynamic scene image validation remain NOT_RUN.
