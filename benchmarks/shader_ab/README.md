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
material/precision distributions and matched physical capture orchestration remain incomplete.
The initial 16 pairs now have per-pair executable counterexamples and a bounded
legacy Variant/Trace adapter, described below. No GPU speedup,
physical timing/counters or temperature validation is claimed.


## Initial 16 controls: CPU golden, independent negatives, Variant/Trace

`run.py` now validates each of 48 executed fragment variants through the existing
v1.0.7 `benchmarks/pipeline/variants.py` validator. Each pair also executes its own
wrong transformation from `counterexamples.py` and compares all three outputs to
an independent scalar CPU RGBA8 reference with the existing one-code tolerance.
The two deliberately failing original A/B pairs remain failing controls, not
newly claimed equivalent optimizations. The precision negative is explicit coarse
quantization, **not** evidence that mediump itself fails on these drivers.

`evidence/initial16-controls-{mesa,angle}.json` records actual software execution:
48 arithmetic readbacks per driver; 30 valid baseline/candidate comparisons pass,
2 original wrong candidates fail, and 16 additional independent wrong variants
fail. Four original overlap proxies add 8 readbacks (56 total per driver).
No performance capture was supplied; `variant_trace.status=NOT_MEASURED`.

Optional `--trace-bundle BUNDLE_JSON` connects licensed exported captures to the
existing v1.0.4 `benchmarks/traces/analyze.py`, including its artifact hash, units,
provenance and range checks. Bundle shape:

```json
{"bindings":[{"case":"branch-select","arm":"a","source_sha256":"EXECUTED_FRAGMENT_SHA256","manifest":"capture/trace-manifest.json"}]}
```

Paths must remain within the bundle directory; known arm (`a`, `b`, `negative`),
exact source hash and unique binding are mandatory. The public summary contains
only source hash, provenance, hypothesis categories and missing metrics, not
raw device identities or file paths. Synthetic trace fixtures test plumbing only;
they never become hardware captures or measured improvement. This adapter does
not acquire traces, prove capture-to-execution authenticity, match/interleave
physical repetitions, reuse binary caches or accept performance candidates.
Variant validation is real reuse, not full v1.0.7 cache orchestration. A rejected
quality candidate stays rejected regardless of any trace hypothesis.
