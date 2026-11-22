# W3.1 candidate: objective relevance and compatibility

The version-1 request accepts the same fields and both existing command forms:
`python3 tools/gpu_decision_v111.py request.json` or
`python3 tools/gpu_decision_v111.py < request.json`.
The original result fields and values remain, and an additive
`objective_evaluation` object explains the catalog's scope.

- `UNSUPPORTED_GOALS`: none of the positively weighted objectives is supported
  by any configured strategy. The current catalog has no startup strategy.
- `NO_RELEVANT_CANDIDATES`: at least one active objective is known to the
  catalog, but none of the workload-matched strategies contributes to it.
- `CORRECTNESS_PROBE_REQUIRED`: no experiment is eligible and at least one
  relevant candidate needs its existing correctness probe. This is not a
  capability or performance verdict.
- `RELEVANT_CANDIDATES`: inspect individual existing statuses for blocked,
  analyze-only, probe-required or experiment-required outcomes.

`supported_goals` and `unsupported_goals` list only positively weighted
objectives, in deterministic order. Mixed objective requests may propose an
experiment only for the supported portion. A relevance score is a policy
weight, not a measured improvement or likelihood of success. Relevant
candidates still cannot bypass capability, correctness, caller or review
guards. The decision digest now includes the objective-policy revision;
compare decisions with the same revision rather than expecting old digests.

This narrow correction covers F02 and the V112-D01/D02 CLI regression. It does
not claim a complete W3 strategy matrix, W2 evidence intake, measured startup
improvement or device acceptance.
