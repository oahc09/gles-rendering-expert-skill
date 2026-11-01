# GLES Agent Benchmark (W6 candidate)

64 annotated tasks: **16 Generate, 16 Review, 16 Diagnose, 16 Optimize**.
`cases.json` is the checked-in corpus; `build_cases.py` is its editable source.
Each case includes platform/API assumptions, expected findings, legal controls,
forbidden advice, fallback, source links and compile-evidence state. C01–C12 map
to the taskbook, **not a claim that the corresponding GPU tests ran**.
Annotations require independent technical review before release. Source links are
reference material, not a claim that every performance hypothesis is normative.

## What is and is not measured

The runner calls a **user-supplied model adapter** twice per case. Each invocation
is a fresh subprocess, with the same prompt and capability snapshot. `with_skill`
adds the current `SKILL.md` text to the system prompt; `no_skill` does not. The
request never contains expected answers, legal controls, or grading annotations.
References linked from SKILL are **not automatically fetched or injected**: this
is a main-Skill-text benchmark, not a full retrieval-agent benchmark. Record that
scope in comparisons. The adapter must use isolated stateless sessions, identical
model/sampling parameters and no hidden skill retrieval for the no-Skill arm.
Pin provider model/version, temperature/seed where supported, and adapter hash.
Do not place API tokens in the command, labels, corpus, or output; supply them to
the adapter through a secure environment configured by the operator.

No model adapter is configured in this repository. The committed baseline is
**BLOCKED_BY_PROVIDER**. There are no fabricated answers, accuracy percentages,
compile results or GPU results. Infrastructure mock calls are labeled synthetic
and the scorer explicitly refuses to treat them as model quality measurements.

## Run

```sh
python3 benchmarks/agent/build_cases.py
python3 -m unittest discover -s benchmarks/agent -p 'test_*.py' -v
# Expected exit 2 and BLOCKED_BY_PROVIDER without an adapter:
python3 benchmarks/agent/run.py --output /tmp/gles-agent-blocked
# Actual operator-provided executable, not supplied by this repository:
python3 benchmarks/agent/run.py \
  --adapter 'python3 /absolute/path/provider_adapter.py' \
  --provider-label 'provider/model/version;temperature=0;seed=42' \
  --output /tmp/gles-agent-live
```

`--case A001 --case A017` selects a smoke subset without changing the corpus.
Output directories must not already exist, preventing accidental evidence loss.
The adapter reads one JSON object from stdin (`system`, `prompt`, `capabilities`,
`case_id`, `condition`) and writes the raw model response to stdout. Nonzero exit,
empty output or timeout is **ADAPTER_FAILED**, never a successful case. Each pair
records request/response SHA256, stdout, stderr, wall time, and an incremental
summary. Timing is adapter wall time, **not GPU time**. No generated code is run.
Review captured responses for secrets before sharing artifacts.

## Independent adjudication and compilation

Use `adjudication-template.json` as a row template and produce a JSON array.
A reviewer maps justified findings to the case's `expected_findings`, marks legal
controls incorrectly rejected, and lists unsupported findings. Reviewers should
be blinded to condition where practical. Record reviewer identity and rationale;
resolve disagreements before the final comparison. Do not equate keyword overlap
with correctness. Debug completeness requires the sequence specified in the case
rubric; performance completeness requires before/after methodology, actual device
and driver evidence, raw trace/counters where available, thermal controls and a
negative-result/fallback path. An honest blocked measurement is acceptable advice,
but is not a measured performance result.

Compilation is separately performed by a reviewer in an appropriately isolated
and authorized environment. **Do not automatically execute untrusted generated
code**. A compile PASS/FAIL must include command, generated artifact SHA256, log
SHA256, relative `artifact_file`/`log_file`, and compiler/target environment. Supply
`--evidence-root` to the scorer; it verifies those file hashes and rejects path
escapes. This checks evidence identity, not whether a dishonest compiler log is
truthful; independent review remains necessary. Host compile is not Android target compile;
compile is not link; link is not device correctness; none proves performance.

```sh
python3 benchmarks/agent/score.py --run /tmp/gles-agent-live \
  --adjudications /tmp/adjudications.json --output /tmp/gles-agent-metrics.json
```

The scorer checks captured-response hashes and rubric IDs. Metrics per arm:
- finding recall = TP / (TP + FN); precision = TP / (TP + FP).
- legal-control false-positive rate = incorrectly rejected legal controls / all
  assessed legal controls. This explicit denominator avoids counting every missing
  issue as a false positive.
- compile success = evidenced passes / evidenced compile attempts.
- Diagnose and Optimize rubric completeness = complete / adjudicated applicable.
- paired case count and reviewed response count reveal incomplete comparisons.

Null means **unmeasured**, not zero. A response-capture success is not correctness.
Report failed case IDs and rationales, not only aggregate averages. Repeated paired
runs and uncertainty estimates are needed for statistical quality claims; a single
64-case run is a diagnostic baseline, not proof of general capability.
