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
- Add independently reviewed diagnosis accuracy, false positives, minimization
  fidelity and evidence completeness metrics, not just repair/regression counts.
- Integrate provider request capture with this narrow structured patch protocol.

No prior corpora, scoring rules, or release gates were changed.
