# v1.0.9 traceability

| Plan | Implementation / test command | Scope |
|---|---|---|
| W0 | baseline-gap.md, inherited-gates.json; tools/check_v109_gates.py | Exact unchanged predecessor gates |
| W1 | tools/workload_fingerprint.py; unittest discover -s benchmarks/workloads | 12 synthetic labelled inputs; hypotheses not bottleneck proof |
| W2 | tools/estimate_gpu_cost.py; benchmarks/gpu_cost | 13 estimated boundary cases; not DRAM measurements |
| W3 | benchmarks/shader_ab/run.py | 16 finite fragment pairs; broader experiment families incomplete |
| W4 | benchmarks/shader_ab/run.py; benchmarks/overlap_scenes/README.md | 4 full-screen blend proxies; not dynamic 3DGS geometry |
| W5 | tools/rendergraph_optimizer.py; tools/test_rendergraph_optimizer.py | 14 cases; no automatic rewrites; PostFX deferred |
| W6 | benchmarks/texture_access/run.py | 8 RGBA8 coordinate controls; compression/mip/PBO incomplete |
| W7 | tools/optimization_advisor.py; benchmarks/workloads/test_workload_tools.py | 27 cases and independent-review binding controls; trusted caller authentication remains external |
| W8 | benchmarks/device_portability/protocol.py | 6 test methods; no physical device captures |
| W9 | benchmarks/agent/cases-v1.0.9.json; score_v109.py | 30 unique tasks; no provider outputs |
| W10 | validation.yml; research/ledger.json | Additive CI; two primary-source receipts, full radar review incomplete |

No source release is evidence of a GLES optimization benefit. No synthetic label,
software timer, pair agreement or raw-file hash authenticates physical GPU data.
All performance claims require independently reviewed real capture provenance.
