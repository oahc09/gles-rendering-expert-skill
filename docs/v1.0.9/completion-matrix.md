# v1.0.9 original-plan completion matrix

**Overall: not release-ready.** This is an original-plan checklist, not an inferred
percentage from test counts. `MET` below means the stated host contract is delivered;
it does not waive inherited releases or imply mobile/provider acceptance.
`completion-matrix.json` is the machine-readable companion.

## W0–W10

| Package | Host delivery | Verified deliverable | Exact remaining work |
|---|---|---|---|
| W0 audit | **MET** | Original plan/baseline, write access, eight reuse paths, unchanged predecessor hashes; current test mapping, explicit tag and baseline/source-head CI audit | No local audit gap identified. Earlier release gates remain independent. |
| W1 fingerprint | **MET, bounded contract** | 12 labelled synthetic samples, UNKNOWN/missing evidence, overlap/clock domains, frame quantiles; strict metadata and hash-bound real-export samples | File hash is not physical-source authenticity. No measured causal bottleneck claim. |
| W2 cost model | **PARTIAL** | 13 boundaries; explicit logical lower/upper model, clear/invalidate/resolve/samples, unknowns; calibration comparison function | Host: lifecycle event sequences and driver-condition model missing; supplied pass assumptions remain. Device counters/DRAM conversion unmeasured. Plan marks device calibration optional. |
| W3 shader experiments | **PARTIAL** | 16 original pairs plus real mechanisms, packing, rebind; now actual repeated-sampling coalescing and compute-intermediate→direct-fragment A/B with CPU goldens/negative controls | Host: each initial pair needs its own executable wrong candidate; old Variant/Trace unified adapter and broader material/precision inputs incomplete. Device: actual gains/regressions, thermal/timing/trace. |
| W4 overlap | **PARTIAL** | At least four runnable proxy scenes, Gaussian and layered glass, cameras, silhouettes/alpha/heatmaps, covariance/LOD and finite refraction | Host: rain/volume cases, Gaussian merge, transparent grouping, far-resolution A/B; tile color/alpha/depth/background statistics and scale tiers incomplete. Device counters absent. |
| W5 graph advice | **MET as bounded advice** | Five candidate classes, checker reuse, 37 positive/negative tests, explicit PostFX sidecar and runnable finite oracle | No candidate graph rescale/replay or automatic synchronization/semantic proof. Caller assertions remain assertions. This is advice, never automatic business-renderer modification. |
| W6 texture | **PARTIAL** | More than eight actual mechanisms, KTX conversion/CPU decoder checks, quality refusal; now reusable logical LRU/upload-budget planner and actual multi-frame reload execution | Host: compressed/asynchronous progressive mip streaming, oblique aniso/locality distributions and isolated transcode phase accounting. Device: physical residency, GPU stalls/DRAM/frame-time benefit. |
| W7 decision | **MET, bounded contract** | All states/quality refusal/hash-bound review; executable registry, gain range and structural completeness ranking; real isolated rollback | Structural completeness is not authenticated evidence. No autonomous acceptance or app-wide/context-loss rollback. Real reviewed measurements remain external. |
| W8 portability | **Protocol delivered; HARDWARE BLOCKED** | Exact device grouping, interleaved A/B/thermal/sample/trace constraints, truthful matrix | Host: complete same-scene device-collector wiring and validated strategy variants not finished. External: no physical A/B; no Mali/Adreno/PowerVR comparison. |
| W9 Agent | **Infrastructure delivered; PROVIDER BLOCKED** | 30 new tasks/172 preserved, paired runner, seven metrics; now an actual v1.0.9 scoring CLI with corpus/response/evidence checks | Corpus independent content review remains. No authenticated model pair, independent adjudication or physical measured-gain evidence. Empty provider run gives null metrics and exit 2. |
| W10 radar/CI | **PARTIAL** | Existing radar extended, 90-day ten-source/1319-candidate collection, ten selected full-content reviews, CI and deterministic unit manifest | Host/review: systematic coverage decisions and vendor/X review incomplete; script is not an established weekly/monthly schedule. Independent sign-off/inherited gates/release authorization remain absent. |

## Important original-scope distinctions

- S01–S08 are **recommended acceptance scenes**. Record their gaps, but do not invent
  an unconditional requirement for one million instances on every environment.
- W4 explicitly permits Gaussian/sprite proxies. A trained complete 3DGS engine is
  **not added here as a new mandatory DoD**. Existing proxy minimum is met; the
  actual listed scene/optimization/statistics gaps above still matter.
- Software correctness and rejected bad pixels do not stand in for negative
  **performance** results. No timing speedup is inferred from fewer source samples,
  fewer draws, fewer intermediates or compression ratios.
- `NOT_RUN`/null is not zero. Hashes establish content identity, not the authenticity
  of a device, reviewer or provider. No gate was relaxed to mark this matrix green.

## Host work actually closed in this consolidation

1. W0: audit tags and distinguish successful PR-source CI from absent merge-head CI;
   map the historical unverified table to current execution evidence.
2. W1: reject malformed metadata and bind real frame distributions to an archived
   export with hash, exact samples, workload, tool and clock.
3. W7: reject unknown experiment strings, resolve a closed runnable registry, and
   rank with declared gain bounds and calculated structural completeness.
4. W3: implement the two missing optimization A/B families, not merely another
   producer/consumer mechanism test. Scope and compiler CSE caveats are documented.
5. W6: implement a reusable multi-frame capacity/upload-budget/LRU plan and real
   texture upload/evict/reload/readback execution. Logical accounting stays separate
   from physical residency.
6. W9: expose the new scorer via CLI, preserve input/evidence binding and demonstrate
   the no-provider blocked path without fabricated quality rates.

## Recommended next work, not an assertion of completion

1. Integrate a real S03 UI+3D+PostFX scene and actual candidate PostFX replay, then
   connect legacy Variant/Trace records across the representative scenes.
2. Finish W4 listed optimization/scene/statistics coverage and W6 mip/locality and
   resource-lifecycle distributions; improve W2 lifecycle/driver assumptions.
3. Triage the remaining research corpus and vendor/X sources with explicit defer /
   reject / applicability decisions. Ten reviews are not full source coverage.
4. With separately available real devices and an authorized provider, run physical
   A/B and authentic paired-agent evaluations. These cannot be replaced by more
   host fixture tests. Independent review and explicit release authorization follow.

Current exact-head CI is reported in PR #7; historical runs in validation-report.md
are explicitly bound to their own commits. The repository itself contains no
self-referential claim that an as-yet-unpushed commit has already passed CI.
