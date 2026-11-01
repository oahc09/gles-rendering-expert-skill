# Paired Agent Benchmark Report

- Status: BLOCKED_BY_PROVIDER / CAPTURED_PENDING_REVIEW / PARTIAL_REVIEW / REVIEWED
- Corpus SHA256:
- Skill SHA256 and repository HEAD:
- Adapter SHA256 and provider/model/version/configuration (no secrets):
- Date; paired cases / 64; repeats; condition blinding procedure:
- Scope: main SKILL text; linked reference documents not automatically injected.

| Metric | no_skill | with_skill | Evidence / uncertainty |
|---|---|---|---|
| Finding recall | NOT_RUN | NOT_RUN | TP / (TP+FN) |
| Finding precision | NOT_RUN | NOT_RUN | TP / (TP+FP) |
| Legal-control false-positive rate | NOT_RUN | NOT_RUN | rejected / assessed controls |
| Host compile success | NOT_RUN | NOT_RUN | compiler + artifact/log hashes |
| Target compile/link success | NOT_RUN | NOT_RUN | target toolchain; separate host |
| Debug rubric completeness | NOT_RUN | NOT_RUN | human-adjudicated Diagnose |
| Performance evidence completeness | NOT_RUN | NOT_RUN | human-adjudicated Optimize |

## Failed cases and corrections
Case ID, condition, response hash, expected finding, observed issue, severity,
reviewer rationale, minimal correction, regression artifact. Include false positives.

## Independent evidence boundaries
- Infrastructure tests: recorded separately, not model performance.
- Hardware/API runtime: NOT_RUN unless actual capture attached.
- GPU before/after performance: BLOCKED_BY_HARDWARE unless device/driver/thermal
  state, repeated timings, raw trace and available counters are attached.
- Statistical uncertainty: no general quality claim without repeated paired runs.
