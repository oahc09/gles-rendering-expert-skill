# Evidence-preserving trace triage

`python benchmarks/traces/analyze.py trace-manifest.json --output report.json`

Input is a **licensed exported CSV/JSON** with metric, value, unit and timestamp_ms columns. The manifest declares source, license, device/GPU/driver/backend/build, time range, aggregation/sample method, missing fields and SHA256 for every raw artifact. Examples are the 12 authored fixtures, explicitly **synthetic** with ground-truth triage expectations. They are not measured Perfetto/AGI captures. `source=Perfetto` means an operator exported permitted data, not that this tool decodes protobuf traces. RenderDoc `.rdc` and proprietary/binary SDK files are unsupported: export via the corresponding official tool first.

Each hypothesis needs at least two corroborating metrics. The thresholds are deliberately documented triage assumptions, not universal vendor cutoffs. Results retain raw file/row/hash lineage and an A/B experiment, counterfactual and missing counters. A solitary high GPU utilization or GPU time never proves a bottleneck. A thermal hypothesis additionally needs repeated time alignment before a causal claim. No result claims measured improvement, even if the input is a real export. Counter units/aggregation must match; sample-level p95 cannot be reconstructed from an aggregate mean.

`python -m unittest discover -s benchmarks/traces -p 'test_*.py' -v`

Review actual target-specific counter meanings against [Perfetto trace processor](https://perfetto.dev/docs/analysis/trace-processor), [Android GPU Inspector](https://developer.android.com/agi), and the selected vendor tool. Do not compare differently normalized busy counters between GPUs. The current 12 fixtures cover eight hypothesis categories and four conservative/missing/healthy controls. Scene performance captures continue to use `benchmarks/gpu/capture.py`; this analyzer augments it rather than replacing it.
