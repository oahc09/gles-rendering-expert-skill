# v1.0.9 traceability

| Plan | Implementation / test command | Scope |
|---|---|---|
| W0 | baseline-gap.md, inherited-gates.json; tools/check_v109_gates.py | Baseline/source CI/tag audit, unchanged predecessor gates |
| W1 | tools/workload_fingerprint.py; benchmarks/workloads/test_binding_contracts.py | Metadata and source-bound exports; no authenticity inference |
| W2 | tools/estimate_gpu_cost.py; tools/test_attachment_lifecycle.py | Legacy bounds plus explicit event lifecycle/conditional FBO model; not DRAM |
| W3 | benchmarks/shader_ab/ | Finite actual shader/packing/rebind/sampling/fusion controls; see completion matrix |
| W4 | benchmarks/overlap_scenes/projected.py and advanced.py | Projected proxies, covariance, LOD and finite refraction with CPU goldens |
| W5 | tools/rendergraph_optimizer.py; benchmarks/pipeline | Bounded advice and finite quality oracle; see matrix for semantic scope |
| W6 | benchmarks/texture_access and benchmarks/texture_streaming | Actual KTX/texture controls and synchronous budgeted eviction/reload |
| W7 | tools/optimization_advisor.py; tools/optimization_experiments.py | Evidence-bound decisions, executable registry and ranking; authenticity external |
| W8 | benchmarks/device_portability/protocol.py | Grouped validation protocol; physical device captures missing |
| W9 | benchmarks/agent/cases-v1.0.9.json; score_v109.py | 30 unique paired tasks, executable scoring CLI; no provider outputs |
| W10 | validation.yml; research/rolling and review files | 1319 metadata candidates; ten selected full-content AI reviews, not corpus acceptance |

No source release is evidence of a GLES optimization benefit. No synthetic label,
software timer, pair agreement or raw-file hash authenticates physical GPU data.
All performance claims require independently reviewed real capture provenance.

Second increment: W3 `benchmarks/shader_ab/advanced.py` (dual-driver CPU-golden
UBO/SSBO/compute/depth/discard); W4 `benchmarks/overlap_scenes/projected.py`
(64×64, 4 scenes, 3 camera views, 3 arms, pixel/heatmap ZIPs); W6
`benchmarks/texture_access/mechanisms.py` (14 actual texture mechanism controls).
`tools/check_v109_evidence.py` guards public evidence. These supersede the initial
4×4-only scope descriptions above, not the real hardware/provider release gates.


Third increment: W1 frame distributions; W4 `overlap_scenes/advanced.py` covariance,
LOD and finite refraction; W5 registered `pipeline/postfx_quality.py` and explicit
sidecar (recommendation only); W6 `texture_access/ktx2_experiment.py` actual KTX
conversion and strict bounded `ktx2_container.py`. `scene-coverage.json` separates
all eight scene dimensions and `check_v109_scene_coverage.py` rejects false acceptance.


Fourth increment closes finite software gaps: S05 `hdr_controls/run.py` performs
float HDR attachment and sampled SDR conversion; source-informed `shader_ab/packing.py`
and `attachment_controls/run.py` link actual reviewed patches to bounded local
oracles without asserting exact upstream reproduction. Texture KTX tests now include
an official pinned independent CPU ETC2 block decoder and a separate quality-decision
gate. Selected release/implementation review files are AI analysis, not independent
human approval, complete corpus review or performance evidence.


Fifth increment: `particle_controls/run.py` realizes finite S04 compute→SSBO→vertex
rendering; `rollback_controls/run.py` realizes finite S08 program/texture/FBO/VAO
rebind with clear/redraw/readback; `shader_ab/rebind.py` follows the reviewed storage
barrier source with bounded multi-resource controls. `tools/run_v109_regression.py`
uses `test-manifest.json` for a reproducible full host-unit summary; missing/zero
tests or skips fail and raw machine logs are not included in the summary artifact.
