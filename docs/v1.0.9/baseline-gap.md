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

## Current audit closure (2026-11-15; separate from the initial snapshot)

The table above intentionally preserves the initial `EXISTS_UNVERIFIED` state.
The eight reused host infrastructures have since executed through the full test
manifest and hosted workflow. See `test-manifest.json`, `evidence/unit-tests-fifth.json`
(811 tests, zero skips) and exact-head CI run 43671500617 at commit
87f6756d3541b5dc4e9aa4e0913ba935a4f65722. This establishes host infrastructure execution,
not device/model acceptance, and is not claimed as CI for later commits.

Read-only tag audit (`git ls-remote --tags origin`) returned only tag `1.0.0` at
02942f16a86bf04077ca116c8c77aa85a5251a0f; no v1.0.9 tag was created.
The merged v1.0.8 PR source head af9d818078d057801d6914daf0f1fcab8aff637d
has successful run 43610518989. A direct Actions query for the baseline merge head
427225b3a4cbb498e9112c79ec7857e22421d9dd returned no workflow runs; the source-head
result is not falsely relabeled as merge-head validation. Current branch tests
exercise the inherited code and unchanged gate hashes separately.
