# v1.0.9 optimization benchmark

30 new distinct tasks, A173–A202, append unchanged 172 v1.0.7 tasks. v1.0.8 has a separate repair corpus and is not overwritten or renumbered. The generated combined corpus is `cases-v1.0.9.json`; regenerate with `python3 benchmarks/agent/build_v109_cases.py`.

Use the existing paired runner:

```
python3 benchmarks/agent/run.py --cases benchmarks/agent/cases-v1.0.9.json --output /tmp/v109-provider-run
```

With no adapter this deliberately exits 2, records `BLOCKED_BY_PROVIDER`, and never fabricates responses. A real authorized provider adapter and label are required for paired calls. Existing `request_for` hides the expected labels and rubric from the provider.

`score_v109.score` reuses existing hash-bound independent adjudication and adds separately denominated diagnosis accuracy, false positives, compile success, runtime success, quality pass, measured improvement, and unsupported-gain-claim rates. Null means unreviewed, never zero. Raw build/run/image evidence identities are mandatory for execution metrics. A physical-device, multi-round, trace-bound comparison is mandatory for measured improvement. Reviewer identities still need independent authentication outside the local contract; declared strings alone are not that authentication.

## Failure analysis / current status

- Corpus construction and runner compatibility: tested locally, not model-quality results.
- Provider responses, independent adjudication, measured model gains: `BLOCKED_BY_PROVIDER`.
- Mobile physical GPU performance/power/thermal evidence: `BLOCKED_BY_HARDWARE`.
- The corpus requires independent content review before release.
- Preserved inherited score semantics; the new scorer does not change old corpus files or scoring code.
