# Trace SQL evidence and conservative diagnosis (v1.0.5 W5)

This is an adapter around the existing [`benchmarks/traces/analyze.py`](../../benchmarks/traces/analyze.py)
metric schema, units, hypotheses and A/B suggestions—not a second GPU classifier.

## Reproduce

```sh
python3 -m unittest discover -s benchmarks/traces/sql -p 'test_*.py' -v
python3 benchmarks/traces/sql/run_fixtures.py --output /tmp/sql-fixtures.json
# Actual native protobuf parsing/SQL, using an explicitly installed official tool:
python3 benchmarks/traces/sql/run_fixtures.py --processor /path/to/trace_processor_shell --output /tmp/sql-native.json
python3 benchmarks/traces/sql/adapter.py capture.pftrace --metadata capture.metadata.json \
  --processor /path/to/trace_processor_shell --output /tmp/sql-evidence
```

Without `--processor`, the input is a **read-only normalized SQLite synthetic fixture**;
it cannot claim `real-export` provenance. With it, the adapter executes the real
Perfetto Trace Processor with explicit CSV and `--no-agent` output to avoid an
ambient agent-mode environment changing the protocol. No SQL file-access option,
private counter plugin, upload, system tracing changes or root operation is enabled.
Only the checked-in SQL templates are executed. SQLite query work is bounded; all
outputs are limited to 10001 rows, with the sentinel excess rejected rather than
silently truncated into a successful diagnosis.

## Input contract

Reuse the v1.0.4 device, GPU, driver, backend, build, license and provenance metadata.
Add `raw_sha256`, `capture_complete: true`, `time_domain: trace_processor_ns`, and
`time_range: [start_ns,end_ns]`. This is a declared, normalized trace time domain,
not wall-clock milliseconds. The adapter verifies the raw bytes' hash and checks
all slice endpoints/counter timestamps against the range. A declared complete file
is not forensic proof that capture ended cleanly: parser loss/error counters and
unfinished slices are also checked. Packet-aligned data loss without an error
counter can escape detection; acquire an independently reviewed capture receipt.

## Schema first, evidence second

The adapter enumerates `sqlite_master`, then `PRAGMA table_info` for every needed
table. It does not run a data query with missing columns. Each template records
its SQL/hash, required schema, row IDs, raw rows and missing fields in `evidence.json`.
It covers RenderThread slices, CPU sched intervals, GPU work slices when present,
opt-in frequency/temperature counters, SurfaceFlinger, swap waits, shader compile
and app-defined frame/submit intervals. A table existing with zero matching rows
is **UNKNOWN**, not a zero-cost measurement. Missing frequency units are not guessed.

Names `gles.frame`, `gles.cpu_submit`, `gles.swap_wait`, `gles.shader_compile`,
`gles.gpu_frequency_mhz` (MHz), and `gles.temperature_c` (C) are this sample's
**explicit instrumentation contract**, not universal Android/Perfetto built-ins.
Sched intervals establish scheduled time; RenderThread wall slices may include
waiting. GPU work requires the actual `gpu_slice` data, not a CPU bracket relabeled
GPU time. The metadata must describe actual counter/sensor provenance on devices.

## Output and non-claims

* `observed`: source rows and query IDs only.
* `inferred`: existing threshold-based triage hypotheses, never causal facts.
  Every threshold is recomputed from only the rows in a complete, at-most
  16.667 ms window. The first qualifying window retains its bounds, per-metric
  means and exact matched row evidence; unrelated high samples cannot borrow
  a healthy overlapping pair. This rejects disjoint averages but is not a semantic frame join; variable-refresh,
  pipelined GPU work and coarse counters can require richer alignment.
* `not_measurable`: private GMEM/bandwidth percentages, watts, energy savings and
  absent measurements. No “25% bandwidth improvement” is manufactured.
* Empty, malformed, truncated, out-of-range, unit-mismatched or untrusted-clock
  input produces **UNKNOWN**, clears diagnostic hypotheses and exits 2. Missing
  table/column queries are individually UNKNOWN; other usable observations may
  yield PARTIAL_EVIDENCE. EVIDENCE_AVAILABLE never means a root cause is proven.

`normalized-metrics.json` and `normalized-manifest.json` can be replayed by the
existing analyzer. The included `legacy_analysis` hypotheses and their evidence use the same matched-window recomputation;
standalone replay through the old analyzer does not include that new guard.
`diagnosis.md` separates observation, hypothesis, excluded/unknown claims and the
next controlled experiment. Inspect raw SQL evidence, not just the prose summary.

## Validation levels

17 annotated synthetic SQLite cases include four eligible hypotheses, healthy and
missing-GPU negatives, unrelated time intervals, healthy overlap with unrelated high CPU samples, missing columns, empty and broken
files, incomplete slices, units, clocks, hash mismatch and parser loss. The fixture
report shows FP/FN against those authored labels and separately counts abstentions;
it is not independent human adjudication of real device causes.

A repository-authored native TrackEvent protobuf is also parsed by the real pinned
Perfetto v59.1 executable, with empty/truncated counterparts. This proves the native
parser/SQL integration—not Android collection, mobile GPU counters, model reasoning
or physical performance. See `benchmarks/traces/sql/fixture-validation.json` and
`native-validation/evidence.json`. No device-derived traces or private data are shipped.

Official sources: [Trace Processor](https://perfetto.dev/docs/analysis/trace-processor),
[SQL table documentation](https://perfetto.dev/docs/analysis/sql-tables),
[v59.1 release](https://github.com/google/perfetto/releases/tag/v59.1),
[pinned TrackEvent protobuf](https://github.com/google/perfetto/blob/v59.1/protos/perfetto/trace/track_event/track_event.proto).
