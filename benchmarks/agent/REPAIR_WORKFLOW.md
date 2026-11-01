# Diagnose → minimal patch → validate (v1.0.4 candidate)

The original `cases.json` stays exactly 64 cases. `cases-v1.0.4.json` contains those same cases plus A065–A088: eight real software-runtime mutations, eight actual shader reject/fix pairs, and eight scene visual regressions. These are **authored controlled defects executed on software**, not claims of 24 production-device incidents or 24 AI-generated fixes. `repair-cases.json` stores the extension; `assemble_repairs.py` binds actual failure logs and report hashes without exposing expected findings to the paired model request.

```sh
GLES_SDK_ROOT=/path/to/sdk python benchmarks/agent/reproduce_repairs.py --compiler /path/to/glslangValidator --output reports/repair-reproduction.json
python benchmarks/agent/assemble_repairs.py reports/repair-reproduction.json
python benchmarks/agent/run.py --cases benchmarks/agent/cases-v1.0.4.json --output reports/new-paired-run
```

Without an explicit provider adapter the final command exits 2 / BLOCKED_BY_PROVIDER with zero responses. Reproduction compiles/runs mutated and fixed C++/GLSL, freshly builds/runs the real scene runner, checks source/runner/binary/image hashes and keeps image/log evidence. It does not regenerate goldens. No test accepts a compiler crash as a valid shader rejection.

For live repair: provide code + failure log + capability snapshot; require evidence chain, graded root-cause confidence, minimal diff, regression command and expected versus observed GPU effect. Apply model patches only in an isolated temporary copy with an explicit file allowlist, reject path traversal/binary/unrelated edits, inspect the diff, then run existing compiler/scene/golden tests. This repository does **not** automatically execute arbitrary model-generated shell commands. Save rejected patches and failed regressions.

Use the existing `score.py` and independent adjudications. Old accuracy/false-positive/compile denominators remain unchanged. Repair cases additionally accept `root_cause_hit` and `unsupported_performance_claim` booleans or null, and `repair_regression` with PASS/FAIL/NOT_RUN plus command/environment/artifact/log hashes. CLI validates actual evidence bytes under `--evidence-root`. Output includes each denominator; missing evidence is null, not zero or success. A fixture patch passing does not prove a model produced it, and software performance is not mobile GPU performance.
