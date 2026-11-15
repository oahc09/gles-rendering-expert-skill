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
