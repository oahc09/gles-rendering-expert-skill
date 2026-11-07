# GLES/EGL state adversarial validation (v1.0.8 candidate)

`model.py` executes 44 explicit transition/boundary cases across Context/Surface/
Thread, texture/renderbuffer/FBO, VAO/VBO/UBO, program/pipeline, sync/query/PBO.
Each case contains its sequence, expected outcomes and oracle scope. It models
**application ownership/cache policy**, not all GL semantics. In particular,
nonshared-name misuse can refer to another local object in real GL; the model's
EXPECTED_ERROR is an application rejection, not a mandated GL error. A deleted
object's references in other contexts/containers can outlive its name. This model
checks the application's own cache, not a claim that GL deletes every reference.

11 deterministic cache invalidation defects (one per object domain) use the
existing `benchmarks/reducer/reduce.py:minimize`. Reports retain original and
reduced sequences, exact predicate, three replays, corrected control, and
operation-deletion **1-minimality**, not a globally shortest claim.

`host.py` executes 24 bounded actual EGL/GLES cases: valid and invalid binds,
allocation sizes/ranges, immutable texture storage, framebuffer completeness,
viewport/scissor/pixel-store/clear and EGL_NO_SURFACE swap. Error enums are exact.
Capability probes require both the extension and function pointers. KHR/EXT
reset status is queried without inducing a reset. KHR_debug is capability/entry
probing only. GLES 3.2 promoted core paths are not inferred from extension names.

Run all under the bounded runner:

```
python benchmarks/robustness/run.py --output /tmp/gles-w23 --gles-library /path/to/libGLESv2.so.2
python -m unittest discover -s benchmarks/state_machine -v
python benchmarks/state_machine/model.py --output /tmp/state-model.json
```

Replay: save a fault's `minimal` JSON array to `/tmp/sequence.json`, then:
`python benchmarks/state_machine/model.py --replay /tmp/sequence.json --fault texture`.
Omit `--fault` for the corrected control. No external source is executed.

UNDEFINED and IMPLEMENTATION_DEPENDENT rows have no deterministic GPU oracle;
they remain offline. EXPECTED_ERROR is not a driver failure. The parent runner
isolates host execution with 30 seconds and reports TEST_TIMEOUT without claiming
GPU hang. Child crashes without independent driver evidence are HARNESS_FAILURE.
Missing libraries/capabilities are UNSUPPORTED. Model surface/context-loss
injection is not an actual EGL_CONTEXT_LOST observation. Physical devices remain
BLOCKED_BY_HARDWARE. Host success is not CTS conformance or mobile performance.

Normative references (historical-context, not new 90-day features):
- https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf
- https://registry.khronos.org/EGL/specs/eglspec.1.5.pdf
- https://registry.khronos.org/OpenGL/extensions/KHR/KHR_robustness.txt
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_robustness.txt
- https://registry.khronos.org/OpenGL/extensions/KHR/KHR_debug.txt
