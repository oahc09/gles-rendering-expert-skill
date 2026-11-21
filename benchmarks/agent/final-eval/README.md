# v1.1.0 final evaluation: frozen authoring, not a provider result

100 new AI-authored tasks, five classes × 20: version/extension, code generation, review, EGL/driver diagnosis, performance/quality. Unique scenarios were authored separately from the iterative corpus; exact prompt-overlap checker runs against existing `cases*.json`. This is **not proof of semantic deduplication, independent expert review, provider non-contamination, or certified heldout status**. No answers have been used to modify the skill. The rubric is in the frozen corpus and excluded from provider requests by the existing runner. Do not edit the corpus to improve reported scores; revisions require a separately versioned evaluation and explicit contamination accounting.

## Commands

From repository root:

```sh
python3 benchmarks/agent/final-eval/evaluate.py validate
python3 benchmarks/agent/final-eval/evaluate.py capture --skill SKILL.md --output /tmp/final-eval-capture
# No adapter: exit 2, BLOCKED_BY_PROVIDER, zero responses, no inferred metrics.
python3 benchmarks/agent/final-eval/evaluate.py score --run /tmp/final-eval-capture --adjudications benchmarks/agent/final-eval/empty-reviews.json --output /tmp/final-eval-score.json
python3 -m unittest discover -s benchmarks/agent/final-eval -p 'test_*.py' -v
```

Real capture uses explicit operator-supplied `--adapter COMMAND --provider-label MODEL_CONFIG --protocol protocol.json`. No credential search or automatic external call occurs. Same single adapter/config is used for both modes by shared `benchmarks/agent/run.py`; adapter must honor the identical model, token/time budget, temperature/seed settings frozen in protocol. These are a contract, **not a claim that an untrusted remote provider obeyed**. Store provider response usage/config records for independent audit. The wrapper hash-binds protocol and skill snapshots in the run summary. Raw requests/responses are retained by the original runner. Original `score_v109.score_files` verifies captured corpus and response hashes plus compile/runtime artifacts/logs before counting tests.

## Blind judging / prerequisites

1. Before any provider run, an independent reviewer must check all100 scenarios, factual rubrics against relevant version/extension specification, ambiguous assumptions, and semantic overlap. Current status NOT_RUN. The broad spec URLs are starting references, not proof that every boundary was independently reviewed.
2. Freeze skill, evaluator, corpus and protocol before capture. Do not improve the skill using final-eval answers. An operationally blind coordinator assigns opaque response IDs and withholds condition labels/skill attachment from judge; map back only after locked judgments. Current repository does not certify personnel separation or blind execution.
3. Judge true-positive IDs from `expected_findings`, unsupported findings, rejected legal controls, severity and rationale, not keyword similarity. `p0_api_illegal` is a boolean/null per response with reviewer rationale; a missing judgment cannot mean false. Each code response must be actually compiled and executed with independent numeric/visual oracle. Repaired retries are not first-run success. Diagnose `debug_complete` alone is not reproduced diagnosis: reproduction also needs actual first_run evidence.
4. Follow original scorer adjudication schema; stages compile/first_run/numeric/visual need actual files/hashes/command/environment; numeric/visual need independent `criteria_reference`. Keep secret paths/credentials out of public artifacts. Review identity is a declaration, not authenticated human independence.
5. Report separate no-skill/with-skill denominators and paired case count. Wilson95 intervals are marginal binomial intervals, not a claim of independent sampling or causal significance. No untested compile/runtime is included as PASS. Current 0/0 yields null, not zero accuracy.
6. Required suggestions: zero P0 illegal generation on this set, >=90% valid first-run, <=5% legal-control false positives. Cannot accept with missing responses/reviews or independent review unverified. `release_acceptance` remains NOT_EVALUATED; a reviewer must independently establish all gates. Raw failures and evidence are preserved, not rewritten.

## Costs

Wall elapsed seconds captured by original runner are **not provider token cost**. Optional `--usage usage.json --evidence-root DIR` accepts currency and rows `{case_id,condition,response_sha256,cost,receipt_file,receipt_sha256}`. Finite nonnegative amounts, unique response bindings and receipt hashes are required. This is receipt-bound reporting, not verification of provider billing or completeness unless all200 responses accounted. No receipt means UNKNOWN/null, not zero.

## Current evidence

`evidence/no-provider/summary.json` is an actual no-adapter execution. `evidence/summary.json` is the corresponding shared scorer result: BLOCKED_BY_PROVIDER, zero raw responses and null quality/cost. There is no raw model output or model failure analysis to publish because no provider ran. Fixtures in tests establish evaluator rejection behavior only. No credentials were inspected.
