# v1.0.8 baseline and coverage difference

The exact original plan is [development-plan.md](development-plan.md),205 lines,
17045 bytes, SHA2566393d04fe0f2e42b1b32563d3626a51e7db88b8b471e574ae6f48ac4bfc84cef.
It was resolved from the user's named file, not reconstructed from a title.
Its old observation that v1.0.7 was absent is superseded by current main
`b0bb57f8148e7de38ec472ee8cb87e04a53c39b8`, tree
`858bf8d33bd7286c4f67254aab568205b7dfaf3f`, which includes merged PR5.
The starting worktree was clean, current account push permission was verified,
and no open PR was present. Metadata remains1.0.2. Full baseline identities and
unchanged predecessor gate/corpus hashes are in [baseline.json](baseline.json).

| Package | Reuse | New gap / identifiers | Owning files |
|---|---|---|---|
| W0 | main/PR5, prior gates and172 Agent cases | frozen source/permissions/coverage | this document,baseline.json |
| W1 | validate_shaders.expected_result,v106 reducer.minimize |89 bounded cases,60 typed-expression mutations;300/310/320 families | tools/shader_fuzz.py;benchmarks/fuzz |
| W2 | existing reducer and EGL conventions |SM001–044;11 injected cache scenarios;HOST001–024 | benchmarks/state_machine |
| W3 | W1 process isolation |owned-resource quotas,cleanup,cancellation,retry,robustness entrypoints | benchmarks/robustness |
| W4 | actual v107 rendergraph/material/hazards/variants |AG01–24,AA01–24,AH01–10;transitive alias and explicit HB proofs | benchmarks/pipeline/adversarial |
| W5 | W1 sources,W2 API probes,v107 quantization |47 paired compile/link/API/FBO/SSBO cases,real Mesa and ANGLE | benchmarks/differential |
| W6 | Es30Context/Target/program/P6 codec,v107 cache keys |one RGB thin-film sphere,8 captures,version1↔2 migration/rollback | examples/material_upgrade;benchmarks/material_upgrade |
| W7 | existing provider request/runner/scorer and frozen172 prefix |A173–A212,40 reproducible adversarial tasks | benchmarks/agent/v108;cases-v1.0.8.json |
| W8 | manual-only workflow,recursive gate checker |source evidence ledger,final regression/negative guards | docs/v1.0.8;tools;existing workflow |

This is an incremental candidate in one integration branch/PR, with work-package
commits rather than seven mutually dependent unmerged PRs. It does not create
intermediate versions or weaken the plan's acceptance conditions. Native worker
parallelism stays in the same current environment; no separate cloud task,
scheduled execution,physical-device stress or provider access is started.

Model cases and actual GL calls have separate identifiers/evidence. Repeating
the same application ownership invariant across different object domains is not
claimed as11 distinct driver bugs. A single Mesa version override is not a second
implementation. W5 uses separate Mesa and ANGLE/SwiftShader libraries/processes.

The original v103–v107 release gates stay byte-identical. Their physical-device,
provider and release-authorization blockers are recursively inherited. Code
delivery and PR readiness do not make this an accepted1.0.8 release.
