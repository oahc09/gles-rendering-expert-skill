# GLES pipeline contract lab

This optional standalone lab does not require migrating any application engine.
Use explicit manifests to diagnose production shader/material/pass mistakes,
then validate with a real linked program and target-driver capture.

| Tool | Inputs and result | Scope |
|---|---|---|
| `variants.py` | Feature/version/extension/quality contracts, bounded enumeration, cache callbacks | No driver-independent binary promise |
| `material.py` | std140/std430 block and sampler manifests, reflection and cross-variant ABI | Bounded supported types, distinct GL namespaces |
| `rendergraph.py` | Resource/pass JSON → stable order, errors, lifetimes and reuse hints | Whole resources; no physical allocation promise |
| `hazards.py` | Access trace → consumer barriers, feedback and context contract findings | Conservative RAW/WAW; not arbitrary WAR/race proof |
| `shader_risks.py` | GLSL text → source/stage/line hypotheses | Lexical analysis, not compiler occupancy or timings |
| `shader_experiments.py` | Eight complete A/B GLSL pairs → compiler logs/hashes | Device A/B performance NOT_RUN |
| `diagnose.py` | Ten broken/fixed authored diagnostic contracts | CPU/static reproduction, not vendor bug claims |
| `runtime.py` | Actual C++ GLES captures → independent image/reflection acceptance | Software correctness and version routing only |

Semantic APIs are importable. Standalone graph/hazard CLIs take the raw `input`
object from fixture wrappers. Version and binding errors name the affected field
or parameter. Generated schemas use JSON Schema Draft2020-12; cross-field legality
requires the Python semantic validators as well.

```sh
python3 -m pip install jsonschema==4.23.0
python3 tools/validate_pipeline.py
python3 -m unittest discover -s benchmarks/pipeline -p 'test_*.py' -v
python3 benchmarks/pipeline/diagnose.py
python3 benchmarks/pipeline/shader_experiments.py
sh examples/pipeline/build.sh
export EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1 MESA_SHADER_CACHE_DISABLE=true
python3 benchmarks/pipeline/runtime.py
python3 benchmarks/pipeline/runtime.py --mesa-version-matrix
python3 tools/check_release_gates.py --gates v1.0.7
```

See [runtime dependencies and controls](../../examples/pipeline/README.md),
[traceability and evidence](../../docs/v1.0.7-traceability.md) and
[release gates](../../docs/v1.0.7-release-gates.json). The gate command without
`--require-release` validates truthful bookkeeping, not release readiness. With
`--require-release` it must remain nonzero while hardware/provider gates are open.
