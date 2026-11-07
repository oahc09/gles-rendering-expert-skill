# Agent Benchmark 3.0 pipeline corpus (candidate)

`cases-v1.0.7.json` freezes all 142 earlier cases and appends A143–A172: ten
pipeline topics with three distinct tasks each, spanning Generate, Review,
Diagnose and Optimize. Run `python3 benchmarks/agent/build_v107_cases.py` to
reproduce the corpus, then the existing unittest/runner/score commands.

No live provider has been invoked. Authored annotations, static tools, software
GLES and synthetic unit tests are not model-quality evidence. The report is
`BLOCKED_BY_PROVIDER`; all unmeasured rates and costs are unknown, not zero.

## Blinded paired review

1. Freeze corpus, Skill, compiler, runtime, capability snapshot and independent
   numeric/image criteria. Use `run.py --cases benchmarks/agent/cases-v1.0.7.json`
   with an explicitly authorized adapter and a new output directory. Do not
   expose labels, findings, references-to-solutions or rubrics in model requests.
2. Randomize response identifiers and remove the condition/model label before
   separate reviewers inspect code and run it. Preserve a private mapping for
   later pairing. Do not let the generator judge its own answer.
3. Preserve raw requests/responses, hashes, compiler/linker output, first-run
   exit status, numeric and visual artifacts, elapsed time and provider-reported
   cost when available. A missing price/token receipt means cost NOT_AVAILABLE.
4. Supply `first_run`, `numeric`, `visual` evidence objects independently of
   `compile`, each with status, command, artifact/log SHA256 and environment.
   Numeric/visual additionally require an independent `criteria_reference`.
   Scoring CLI checks local evidence-file hashes under `--evidence-root`.
5. Keep failed initial runs even if a later repair succeeds. Use the existing
   same-suite baseline/repair regression contract for correct-fix and introduced
   regressions. Count illegal-control rejection as false positives. Never
   collapse software correctness, mobile performance and calibrated display
   output into one PASS.
6. Reveal pairing only after adjudication, report disagreements and denominators,
   and keep null metrics for untested dimensions. Real-device/provider evidence
   must clear the inherited release gates before any release claim.

## Current result

Corpus: 172 authored tasks, 30 new. Provider calls: 0. Paired model result:
NOT_RUN. Failed model cases: not yet observable. Executable authored failures
are separately recorded by the pipeline diagnostic/runtime labs, not labelled
as model failures.
