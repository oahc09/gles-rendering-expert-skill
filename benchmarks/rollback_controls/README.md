# Bounded transactional rollback control (S08)

This is actual GLES draw/readback, not a Python state-only model. It reuses
`texture_access.mechanisms.TextureHost` and its real direct/PBO texture uploads.
An isolated context retains baseline GPU texture, program, FBO and VAO objects.
Each candidate has distinct texture and program objects. On rejection, the
baseline objects are rebound, their bindings queried through `glGetIntegerv`,
the framebuffer cleared (preventing a stale-image pass), then the baseline is
redrawn and read back. All 64 RGBA bytes must equal the original baseline.
Objects are deleted after the bounded transaction suite.

Four controls: low-resolution quality loss; absent evidence; correct PBO upload
without performance measurements; deliberately wrong shader output. The existing
strict texture quality gate single-observation helper is reused directly. No
synthetic format branches or duplicate observations are created.
Quality failure means REJECTED_BY_QUALITY; quality success without physical
performance evidence remains INSUFFICIENT_EVIDENCE. HOST_PASS is only a harness
result. No candidate is auto-accepted; all roll back, including correct ones.

```sh
python benchmarks/rollback_controls/run.py --config DRIVER.json --output report.json
python -m unittest discover -s benchmarks/rollback_controls -v
```

Run Mesa and ANGLE in separate subprocesses. Reports contain pixel data and
source hash, not environment metadata, local paths, OS or binary fingerprints.
The unit suite also checks saved dual-driver evidence and gate rejection of
inconsistent metrics. Live CLI execution needs a provisioned driver's private config. Unit tests are
GPU-independent, never silently skip; CI must run the CLI separately on both drivers.

Scope: 4×4 RGBA8 output, one context, texture unit 0, retained immutable baseline
resources, fixed viewport/program/texture/FBO/VAO. This does not restore arbitrary
application state, mutate a production scene, handle context loss/concurrency,
validate all GL bindings, or demonstrate physical GPU performance/latency.
No process crash, OOM or unsupported hardware is labeled successful recovery.
