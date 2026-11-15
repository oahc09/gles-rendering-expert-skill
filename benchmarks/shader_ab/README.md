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

## Current coverage and remaining scope

The paragraph formerly stating UBO/SSBO, formats, discard/depth and dual-driver
execution were absent described the first increment only. `advanced.py`, packing,
rebind, texture_access, particle_controls and hdr_controls now provide actual
software execution of those mechanisms on Mesa and ANGLE.

See `docs/v1.0.9/completion-matrix.md` for the current original-plan assessment.
Mechanism correctness is not automatically an optimization A/B: compute→draw
production/consumption alone is not fusion, and coordinate rewriting alone is not
sample coalescing. Finite pairs do not prove general shader equivalence. Broader
material/precision distributions, per-pair executable counterexamples and unified
legacy Variant/Trace experiment adaptation remain incomplete. No GPU speedup,
physical timing/counters or temperature validation is claimed.
