# v1.0.9 baseline audit

Baseline main 427225b3a4cbb498e9112c79ec7857e22421d9dd, PR #6 merged
2026-11-15 01:56:24Z. GitHub repository push/admin permissions verified. Clean
checkout before this development. Original Library plan retained in development-plan.md.
No metadata/tag/release change. PR merge does not close predecessor gates.

| Existing capability | Path | Reproduce | Audit |
|---|---|---|---|
| DeviceLab | benchmarks/device_lab | python3 -m unittest discover -s benchmarks/device_lab | EXISTS_UNVERIFIED |
| SceneLab | benchmarks/scenes | python3 benchmarks/scenes/run.py --output reports/scenes --sweep | EXISTS_UNVERIFIED |
| Trace SQL | benchmarks/traces/sql | python3 -m unittest discover -s benchmarks/traces/sql | EXISTS_UNVERIFIED |
| RenderGraph | benchmarks/pipeline | python3 -m unittest discover -s benchmarks/pipeline | EXISTS_UNVERIFIED |
| Shader variants | benchmarks/pipeline/shader_experiments.py | python3 benchmarks/pipeline/shader_experiments.py --output reports/shaders.json | EXISTS_UNVERIFIED |
| Agent runner | benchmarks/agent | python3 -m unittest discover -s benchmarks/agent | EXISTS_UNVERIFIED |
| Fuzz | benchmarks/fuzz | python3 -m unittest discover -s benchmarks/fuzz | EXISTS_UNVERIFIED |
| Reducer | benchmarks/reducer | python3 -m unittest discover -s benchmarks/reducer | EXISTS_UNVERIFIED |

Entries initially reflect source existence, not a new execution. Current validation
results are recorded separately rather than rewriting historical evidence.
Inherited gate snapshots and hashes are in inherited-gates.json. Physical Android,
GPU timing/bandwidth/HDR/fault/lifecycle and authenticated provider acceptance remain
separate, blocked gates. Legacy metadata remains 1.0.2 by original release contract.
