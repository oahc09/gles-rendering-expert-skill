# v1.0.8 adversarial repair fixtures

Status: **HOST_FIXTURE_ONLY**, provider **BLOCKED_BY_PROVIDER**. This is a
recovered implementation increment, not completion of the full W7 DoD.

`cases.json` contains 36 bounded, deterministic tasks: six each for graph alias
safety, captured material ABI rejection, application cache lifetime, resource
admission, ESSL 300 compile/link repair, and differential-output classification.
Inputs reuse the actual W1–W5 modules. Each task has a frozen input, failure
predicate, repair-size ceiling and hidden oracle. `request()` excludes the hidden
oracle. The existing `benchmarks/agent/run.py` adapter protocol remains the
reference for capturing real provider responses; no model/provider is invoked
by this directory, no credentials are read, and no model-authored code is run.

## Replay

```sh
python3 benchmarks/agent/v108/repair.py --output /tmp/v108-cases.json
python3 -m unittest discover -s benchmarks/agent/v108 -p 'test_*.py' -v
```

The 30 nonshader tasks are executable structured fixture oracles. Graph repairs
remove unsafe aliasing while preserving all passes/resources. ABI tasks require
rejecting incompatible cached programs, never modifying captured reflection.
Lifecycle tasks exercise the existing injected-fault model and corrected model;
these are not actual EGL errors or resets. Resource tests reject before any
allocation. Differential observations are explicitly authored fixtures, not new
driver captures or evidence of a driver defect.

Shader repair runs the preexisting bounded real compiler wrapper when available;
compile/link success is **COMPILE_ONLY_PASS**, never semantic/runtime acceptance.
Missing toolchain, unchanged source, altered stage inventory, version change,
quota breach, and compiler crash cannot produce a fixture pass. Shader patches
require independent rendering/semantic-preservation review before W7 completion.

`score_provider()` only ingests complete paired, hash-bound provider captures and
independent reviews with artifact/log/suite/environment evidence. It rejects
synthetic runs, missing responses, duplicate cases, mismatched review hashes,
unequal regression environments/suites, and claimed correct fixes with failed
regressions. Its counts are reviewed outcomes, not unreviewed model claims.
Actual evidence files still need external audit: the function does not prove that
an arbitrary supplied hash refers to a genuine run.

## Remaining W7 acceptance

- Capture actual authorized no-Skill/with-Skill provider runs. No score is reported
  here, and no fixture score may substitute for them.
- Extend to arbitrary source patches with isolated compile/run, same-defect
  minimization, actual host differential verification and regression controls.
- Populate the strict `score_v3` diagnosis, false-positive, minimization fidelity
  and evidence-completeness metrics with genuine independently reviewed runs.
- Integrate provider request capture with this narrow structured patch protocol.

No prior corpora, scoring rules, or release gates were changed.

## Narrow real-source repair pipeline

`shader_pipeline.py` adds a separately gated path for four CPU-oracle SSBO
arithmetic cases (`ssbo-add`, `ssbo-multiply`, `ssbo-divide`, `ssbo-sqrt`). It reuses
W1's bounded compiler processes and exact-diagnostic reducer, and W5's isolated
Mesa/ANGLE processes and numeric readback oracle. The shader interface, single
invocation, buffer declaration and main envelope are frozen; only a ≤256-character
numeric arithmetic/sqrt expression may change. No model command or arbitrary OS
program is executed. This is deliberately not an arbitrary GLSL repair runner.

```sh
python3 benchmarks/agent/v108/shader_pipeline.py \
  --case ssbo-add --patch /path/to/repaired.comp \
  --compiler /path/to/glslangValidator \
  --config /path/to/two-driver-config.json --output /tmp/new-w7-report
```

Config must contain exactly `mesa` and `angle`, with existing absolute `egl` and
`gles` library paths; ANGLE also requires an existing `icd` path. Use trusted,
previously installed driver/toolchain files only. Reports contain original/patch
source hashes, actual compiler outcomes, original-diagnostic-preserving reduction,
three independent repeat compiles, and all three original/baseline/patch outcomes
on both drivers. A missing toolchain/driver, skip, failed oracle, or incomplete
minimality proof cannot produce `HOST_PASS`. GPU work is one bounded software
invocation, subject to the inherited W5 process quotas.

Even `HOST_PASS` means authored-host validation only. Provider remains
`BLOCKED_BY_PROVIDER`, model quality `NOT_EVALUATED`; physical GPU and general
semantic/visual preservation are not implied. These four cases do not complete
all W7 metrics or the 36-case arbitrary-code execution workflow.

### Fresh 2026-11-14 execution

`evidence/2026-11-14-host/` records **four HOST_PASS** real pipelines on llvmpipe
and ANGLE/SwiftShader: add, multiply, divide and sqrt. Each includes actual
compile-invalid reproduction, same-diagnostic 1-minimal reduction, three repeat
compiles, and two-implementation CPU-oracle SSBO readback. The explicit wrong
repair (`9.0` for expected `5.0`) compiles on both but correctly returns **FAIL**
on numeric verification. These are authored control patches, not Agent output.
Initial ANGLE initialization failures remain in `evidence/2026-11-14/` as historical
blocked runs and are not counted as passed. No image rendering or device/model
acceptance is claimed by numeric SSBO readback.

## Strict paired review metrics (`score_v3`)

The legacy `score_provider` API is unchanged. The new function takes the frozen
corpus, schema-v3 provider-capture manifest, complete independent adjudications,
and an in-memory `SHA256 → UTF-8 content` evidence map. It performs **no file,
credential, network or provider access**. All supplied content hashes are checked,
with 1 MiB per artifact, 16 MiB total and 2,048 artifact limits. The manifest must
bind the exact corpus hash and explicitly mark the run non-synthetic. Both paired
conditions must cover every unique case, with nonempty response text and matching
response hashes. Synthetic test invocations validate the interface only and do
not emit a model-quality report.

Each review additionally requires:

- `diagnosis`: unique expected-failure IDs, unsupported findings, rejected legal
  controls, rationale, and evidence hashes. The expected ID is the frozen case's
  `oracle.failure`. Unknown true positives/control IDs are rejected. The three
  explicit control IDs are `valid_baseline_must_remain_valid`,
  `unavailable_evidence_is_not_pass`, and `fixtures_are_not_model_results`.
- Explicit boolean `repair_attempted`, existing `correct_fix` and regression
  outcomes. A correct-fix claim cannot accompany a failed regression or missing
  reproduce/patch/compile-run/differential/report PASS evidence.
- `stage_evidence` for all seven workflow stages, including explicit `NOT_RUN`
  or reasoned `NOT_APPLICABLE`. PASS/FAIL requires supplied artifact content;
  unmeasured stages cannot present measurement artifacts.
- `minimization`: matching stage status, original/reduced failure IDs and hashes,
  replay log and rationale. Original artifact must match the frozen case input's
  canonical JSON hash. PASS requires identical failure identity, while FAIL
  requires a different identity. Unmeasured fields must be null, not fabricated.

Rates retain their denominators:

| Metric | Definition |
|---|---|
| Diagnosis accuracy | Exact expected finding, no unsupported finding/control rejection / reviewed cases |
| Diagnosis recall | True positives / expected findings |
| False-repair rate | Attempted but not correct repairs / repair attempts |
| False-positive control rate | Rejected legal controls / reviewed legal controls |
| False-discovery rate | Unsupported findings + rejected controls / all positive findings |
| Minimization fidelity | Same-failure reproductions / measured minimizations |
| Minimization coverage | Measured / applicable minimizations |
| Evidence completeness | Measured PASS/FAIL stages / applicable stages |

Zero denominators produce `null`, not zero or one. `NOT_RUN` lowers coverage;
failures stay in denominators. Counts of missing and nonapplicable stages remain
visible. Both condition metrics and `with_skill - no_skill` deltas are returned,
with null deltas when either side is unmeasured. Test fixtures are not results.

Hash checking detects altered or absent evidence, **not fabricated provenance**.
Provider identity, independent reviewer identity, and the truth of their
interpretation still require external audit. No genuine provider data has been
captured here; the project remains **BLOCKED_BY_PROVIDER / NOT_EVALUATED**.

## Actual API call-source repair controls

`api_pipeline.py` parses a single literal-argument GL call, never arbitrary C++
or shell code. Seven API misuse repairs (viewport, scissor, pack alignment,
enable enum, clear mask, buffer and texture targets) reproduce the exact original
GL error three times on each real driver and verify the corrected intended
operation is error-free. Error-free no-ops are rejected against frozen intent.
This is actual parsed-source-to-GL execution, not C++ compilation, EGL context
reset recovery or general source equivalence. Four tests plus an inventory test
cover parser injection, ranges/arity, no-op misuse and missing-driver rejection.
Run `python3 benchmarks/agent/v108/api_pipeline.py --config CONFIG --output OUT`.

## Actual non-arithmetic image repairs

See [IMAGE_PIPELINE.md](IMAGE_PIPELINE.md): four finite-domain fragment-source
repairs (UV and color swizzle, premultiplied alpha, output alpha), each with the
original defect and a compilable wrong repair. 24 actual Mesa/ANGLE draws are
checked against independent 4×4 CPU RGBA goldens and peer outputs. Compilation
alone cannot pass; both equally wrong drivers cannot pass. This adds image
coverage, but does not claim arbitrary source equivalence or real Agent scores.
