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

## v1.0.9 scoring CLI

Use the v1.0.9 entrypoint, not the older scorer CLI, to obtain all seven new metrics:

```sh
python3 benchmarks/agent/score_v109.py --run RUN_DIRECTORY --cases benchmarks/agent/cases-v1.0.9.json --adjudications REVIEW_JSON --evidence-root EVIDENCE_DIRECTORY --output SCORE_JSON
```

This validates captured corpus/response hashes and old/new execution evidence paths
before scoring. The no-provider empty run returns exit 2, `BLOCKED_BY_PROVIDER`,
zero reviewed pairs and null rates, never invented model-quality scores. Raw review
identities still require trusted independent authentication outside this CLI.

## Case-specific adjudication guide
`v109-adjudication-guide.json` adds two distinct reasoning checks for each of the
30 new prompts, bound to the exact prompt hash and expected finding. This is
AI-authored review guidance, not captured provider output, an independent review,
or keyword-based automatic correctness scoring. Every verdict remains null and
independent review NOT_RUN. It does not change the original corpus or paired
capture hashes. The separate independent adjudicator must inspect actual response
and execution evidence; unsupported gain claims remain separately scored.
