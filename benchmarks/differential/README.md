# W5: independent host implementations

`run.py` executes 47 reusable cases in **two real, separate processes**:
Mesa EGL / llvmpipe and Chromium ANGLE / Vulkan SwiftShader. Neither is a
physical GPU. Android-native and physical-GPU gates remain
`BLOCKED_BY_HARDWARE`; no performance claim is made.

## Replay

From the repository root:

```sh
python3 benchmarks/differential/run.py --config benchmarks/differential/host-config.json --output benchmarks/differential/evidence
python3 -m unittest discover -s benchmarks/differential -p 'test_*.py' -v
# Exact one-case replay from the captured corpus, not regenerated source:
python3 benchmarks/differential/run.py --config benchmarks/differential/evidence/implementations.json --cases benchmarks/differential/evidence/cases.json --case ssbo-divide --output /tmp/differential-replay
```

`host-config.json` records this host's local paths, not a portable installation
promise. On another host supply its actual EGL/GLES library paths and ANGLE
SwiftShader ICD path. Missing drivers, crashes, timeouts, or context failures
produce `UNKNOWN`, never PASS. No download, installation, external execution,
physical-device stress, or persistent driver-setting change is performed.

## Coverage and independently evaluated outputs

- 26 ESSL 300 shader cases directly reused from W1 `shader_fuzz.corpus(7)`:
  scalar/vector/function/UBO/sampler families with four semantics-preserving
  variants, five compile-invalid cases, one varying link-invalid case.
  Compile acceptance and link acceptance are separately recorded and tested.
- 11 valid/invalid GLES calls adapted from W2 `state_machine/host.py`: viewport,
  scissor, pack alignment, enable, clear, buffer/texture target, program unbind.
  Expected API errors are compared independently of harness errors.
- Six 4×4 RGBA8 FBO captures: black, white, primaries, fractions, clamping,
  midpoint. Independent analytic CPU goldens reuse v1.0.7 pipeline's `quantize`.
  Linear UNORM, no texture sampling/sRGB conversion; absolute tolerance of one
  8-bit code value both to golden and to the other implementation. This is not
  a claim to execute all six v1.0.7 multipass material scenarios.
- Four ESSL 310 single-invocation SSBO compute/readback cases: addition,
  multiplication, division, square root. CPU expected values, finite highp
  float tolerance `1e-6 + 1e-6 * abs(reference)`. No cross-device bitwise float
  requirement; unsupported GLES 3.1 is explicitly skipped.

Texture-filtering, color-space, mediump, and other numerical workloads need
separate, workload-specific tolerances before adding cases. Timing is explicitly
`NOT_MEASURED` and never merged with correctness.

## Evidence and status

`evidence/` contains the exact corpus/config, both complete driver reports,
JSON/Markdown summaries, and driver matrix. Reports include API/ESSL versions,
renderer/vendor, OS build, complete extension lists, loaded EGL/GLES/LLVM/
SwiftShader library hashes, Python executable hash, harness and reused source
hashes. `report.schema.json` defines the aggregate format.

`PASS`: both real hosts executed and match the independent oracle and tolerance.
`FAIL`: execution succeeded but an oracle, peer tolerance, or harness GL error
check failed. This alone is not proof of a driver defect.
`SKIP_UNSUPPORTED`: the case requires an unavailable capability.
`UNKNOWN`: missing implementation, timeout, crash or unavailable observation.
The aggregate is PASS only when every requested case passes; skips cannot satisfy
this implementation's strict complete-run acceptance gate.

Each worker uses W1 process-group isolation: 45-second timeout, CPU quota,
4 GiB address-space limit, 1 MiB output/file quota, no cores, two software CPU
threads. Each allocation is tiny; compute launches one invocation.

## Mismatch handling

Every failed comparison automatically saves the original case, exact replay
command, reducer trials and reduced source. The existing line-ddmin reducer is
reused with at most 12 oracle attempts. A reduction must reproduce both exact
original observation signatures **and** FAIL; a crash, timeout, compile failure
replacing a numeric difference, or other unrelated failure cannot satisfy it.
Shader minimization deletes lines from the first source while other inputs are
fixed. API/FBO minimization is deliberately conservative: JSON line deletion
preserving all case keys. Domain-limited `one_minimal` never asserts semantic or
global minimality, and budget exhaustion/unavailable replay is honestly retained.
The clean host run has no mismatches, so no actual-driver reduction is claimed.
Unit tests inject observation fixtures solely to validate reducer plumbing;
these are not labelled real-driver defects or runtime evidence.
