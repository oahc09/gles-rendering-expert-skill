# Ultimate Engineering Expert: first reviewable implementation

This is an incremental v1.1.1 development candidate, not a release. The repository's existing advisor remains the evaluation path for device-bound performance evidence; this module supplies bounded hypotheses before A/B execution. It does not execute commands, call providers, resolve user-supplied paths from JSON, modify a renderer or change a gate.

## Try the offline vertical slice

```sh
python3 tools/gpu_decision_v111.py <<'JSON'
{
  "schema_version": 1,
  "as_of": "2026-11-21",
  "target": {
    "gles": "3.0",
    "extensions": [],
    "entrypoints": ["glInvalidateFramebuffer"],
    "probes": {"discard-dead-attachment": true}
  },
  "workload": {"labels": ["attachment-store"]},
  "objective": {"bandwidth": 1, "quality": 0.5}
}
JSON
python3 -m unittest discover -s tools -p test_gpu_decision_v111.py -v
```

Use [the request schema](../../references/decision/v111-request.schema.json). The CLI separately validates the JSON byte limit, duplicate keys, finite values, calendar date and permissions. Targets, probe results, profile keys and workload labels are supplied by the caller; they are not independently authenticated capture evidence. Do not set a probe true without a scoped correctness result. A matched profile key is not GPU family similarity or proof of driver identity.

The six strategies first check exact core membership against the predecessor's packaged Khronos command index, stated extension and entrypoint presence, explicit correctness probe, caller exclusions, and reviewed exact-profile counterexamples. An unknown probe requests a bounded probe, not adoption. Candidates passing these filters are ranked by a deterministic weighted relevance policy, not predicted speedup, accepted optimization, or Pareto measurement. The output includes mechanism, risk, A/B hypothesis and fallback.

The seed [experience ledger](../../references/experience/v111-cases.json) distinguishes exact supplied profile keys from related evidence, retains expired and retracted records in the result, and never lets a positive case bypass a requirement. It has three source-linked notes, not a production case corpus. Software provenance stays software: the Mesa framebuffer-fetch crash remains a scope-specific counterexample, not a device-family rule.

## Acceptance boundaries

- W0 records real main, predecessor candidate, CI, file and release-gate mapping.
- W1 reuses frozen indexes without claiming new semantic/runtime coverage.
- W3 and W5 are partial. The tested policy cases are authored expectations, not GPU truth; the thermal/power/resource policy, raw-evidence binding, portable profile capture, full case corpus and reviewed import workflow remain open.
- W2, W4 and W6–W14 retain their own gates. In particular, two physical GPU classes and same-settings blind real-provider trials are not run here. No version metadata, tag, preceding gate or release status was changed.
