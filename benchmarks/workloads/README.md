# v1.0.9 workload triage and decision contracts

`python -m unittest discover -s benchmarks/workloads -v`

12 labelled synthetic workload inputs, 13 logical-cost boundary cases and 27
synthetic advisor contract cases. These are software tests, never GPU or model
results. `generate_fixtures.py` regenerates inputs deterministically.

CLI inputs are JSON. `tools/workload_fingerprint.py INPUT [--output FILE]`,
`tools/estimate_gpu_cost.py INPUT [--output FILE]`, and
`tools/optimization_advisor.py INPUT [--output FILE]` emit auditable JSON.
Extract the `input` member of a sample/cost case before using those CLIs.

Trace adaptation: existing `benchmarks/traces/analyze.py` validates licensed raw
CSV/JSON exports, hashes, units and provenance. Its metrics can populate fingerprint
metric records. Rule thresholds here remain explicit generic triage hypotheses,
not vendor-normalized causal classifiers. CPU/GPU intervals must share a clock;
otherwise overlap is unknown rather than adding unrelated durations.

Advisor thresholds are conservative: at least five counterbalanced AB/BA pairs,
warmup, stable thermal conditions, scoped device/build/driver metadata, quality
oracle, and SHA-256-bound raw timing JSON exactly matching the declared measurement.
The raw JSON excludes only `artifacts`. Hashes establish integrity, not authenticity;
a trusted device collector must supply the provenance. Synthetic fixtures deliberately
exercise every state but cannot support performance claims. No result mutates the
renderer automatically. Ranking is a transparent hypothesis-only score combining
estimated gain, confidence, implementation cost and risk. Physical collection,
provider runs and cryptographic device attestation are not performed here.

Independent review is mandatory before any VERIFIED/NO_GAIN/REGRESSION classification:
collector and reviewer identities must differ; review binds workload, candidate and
baseline build, exact device/driver/backend, raw capture hashes, golden and thresholds.
A separate hashed review JSON and quality artifact are required. Reviewer identity
is an ingestion trust boundary, not cryptographic authentication: this module cannot
prove a collector or reviewer is real. Production ingestion must authenticate them.
Synthetic tests exercise this protocol but never become performance evidence.
Only GPU timing pairs in milliseconds are supported; power, bandwidth improvement,
long-term thermal behavior and cross-device extrapolation remain unverified.

## Bound inputs and runnable hypotheses (sixth increment)

Optional `sampling_formats` is an array of nonempty strings, `thermal_state` a
nonempty string (use `UNKNOWN` when unavailable), and `trace_available` a strict
boolean. These fields remain descriptive; `trace_available: true` is not proof.
Synthetic fixtures retain their original contract and never need a real trace.

A `real-export` with nonempty `frame_times_ms` now requires `frame_source`:
`tool`, `clock_domain`, `sample_count`, `raw_trace` (relative path), and `sha256`.
The referenced JSON export must bind `workload_id`, `unit: "ms"`, the exact
`frame_times_ms`, `tool`, and `clock_domain`. Its bytes are hash-checked under the
input document's directory (or the Python caller's explicit `root`). Absolute,
escaping and missing paths are rejected. This is an adapter export, not a claim
that arbitrary vendor binary traces are understood. Preserve the original export
and adaptation provenance in the capture archive. Integrity binding cannot
authenticate the collector, prove physical execution or validate clock calibration.

The `advise` entry point now uses the closed registry in
`tools/optimization_experiments.py`. Registered IDs:
- `shader-advanced-v1`: finite correctness controls, not a performance measurement.
- `texture-access-v1`: finite texture A/B and deliberate quality loss controls.
- `postfx-resolution-loss-v1`: finite texture-resolution oracle, not general
  PostFX scaling equivalence.

Each binding reports the existing source path, current source hash, explicit argv,
scope and required driver configuration. The advisor never executes commands.
Unknown or unavailable entries yield `INSUFFICIENT_EVIDENCE`, even with relevant
labels; register a reviewed implementation instead of supplying arbitrary shell
text. No entry establishes a causal link or performance gain for a new workload.
The low-level `decide` function keeps its original measurement-only contract for
existing callers/tests; use `advise` for registry-validated recommendations.

`estimated_gain_range: [lower, upper]` is an optional ordered hypothesis within
[0,1], not a confidence interval. Legacy `estimated_gain` remains a degenerate
point explicitly labelled `LEGACY_POINT_NOT_INTERVAL`. Ranking uses:
`lower * confidence * (1-risk) * structural_completeness / (1+cost)`.
Completeness is the fraction of five checks: runnable binding, relevant workload
hypothesis, supported capability, nonempty fallback, and golden/threshold contract.
It is computed rather than trusted from caller input. It measures structural
availability, not authenticity. Unknown experiments rank zero. Predictions and
completeness never alter measurement/quality/reviewer acceptance gates, trigger
renderer mutation, or establish `VERIFIED_IMPROVEMENT`.

`test_binding_contracts.py` exercises metadata, hash/path/sample binding, unknown
registry entries, range validation, ranking and unchanged acceptance boundaries.
All captures in these unit tests are synthetic protocol examples.
