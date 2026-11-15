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
| W2 cost model | **MET as bounded lifecycle model** | Legacy bounds plus explicit load/clear/discard/draw/switch/resolve/store/consume state machine; scoped driver condition, unknown propagation; 18 boundary/negative tests | Scope excludes alias/subresources and implicit driver passes. Conditions are not authenticated; physical counters unmeasured. Calibration optional in plan. |
| W3 shader experiments | **PARTIAL** | Initial 16 pairs now each have CPU goldens and executable negative arms; Variant validator and optional source-bound Trace analyzer integrated; other actual mechanisms retained | Broader input distributions and automatic interleaved capture orchestration remain. No physical timing/thermal/gain acceptance. |
| W4 overlap | **PARTIAL** | At least four runnable proxy scenes, Gaussian and layered glass, cameras, silhouettes/alpha/heatmaps, covariance/LOD and finite refraction | Host: rain/volume cases, Gaussian merge, transparent grouping, far-resolution A/B; tile color/alpha/depth/background statistics and scale tiers incomplete. Device counters absent. |
| W5 graph advice | **MET as bounded advice/replay** | Copied candidate 4×4→2×2 intermediate graph; actual three-pass replay; constant passes/checkerboard rejects; closed synchronization vocabulary rejects unsafe graphs before GL | General transforms and incoherent compute/image/SSBO synchronization excluded; no universal equivalence or performance proof. |
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
   resource-lifecycle distributions; extend beyond the bounded W2 lifecycle/driver assumptions only with explicit contracts.
3. Triage the remaining research corpus and vendor/X sources with explicit defer /
   reject / applicability decisions. Ten reviews are not full source coverage.
4. With separately available real devices and an authorized provider, run physical
   A/B and authentic paired-agent evaluations. These cannot be replaced by more
   host fixture tests. Independent review and explicit release authorization follow.

Current exact-head CI is reported in PR #7; historical runs in validation-report.md
are explicitly bound to their own commits. The repository itself contains no
self-referential claim that an as-yet-unpushed commit has already passed CI.

## Follow-up W2/W3/W5 closure

The explicit lifecycle model, all initial per-pair negatives and existing
Variant/Trace reuse, plus finite candidate graph rewrite/replay with checked
coherent synchronization, are now executable. These replace the previously
listed missing implementations, not hardware/provider acceptance. Other matrix
rows retain their unresolved host items. Candidate replay accepts constant input
and rejects checkerboard degradation without relaxing quality budgets.

## Scene collection, mip refinement and tier quality follow-up

- W4 now executes 8/24/48 proxies over three cameras, conservative disjoint
  material grouping and actual half-resolution rendering/upsampling. Grouping
  preserves pixels and reduces tint updates, not draw count/coverage. Mesa 24/48
  baseline fails the unchanged 4-code CPU-golden threshold; only tier8 is
  acceptable there. ANGLE passes all three. Cause is undetermined. Half-resolution
  candidates reject at the original quality budget. A fallback to a failed
  baseline is explicitly not acceptable. Harness-contract success is not
  full-tier visual acceptance.
- W6 now has synchronous explicit mip refinement, budget gating and actual
  rejected-candidate restore. Compressed/asynchronous streaming remains missing.
- W8 captures the actual three-stage scene, rechecks CPU quality from pixels and
  groups hash-bound software records. It does not enter the physical protocol.
- W9 adds prompt-bound case-specific reasoning guidance for all 30 tasks;
  independent reviewer/provider verdicts remain absent.
- W10 binds the four inspected source reviews to bounded experiment/test hashes.
  Integrity checks do not create independent review or promote performance rules.

## Blend precision diagnosis (original threshold unchanged)
Retained readback analysis shows layer-dependent positive error. Alternative
source-UNORM and split-product rounding models reduce the discrepancy but do not
fully explain it. GLES permits internal fixed-point blending/rounding choices;
this does not establish a bug or the installed implementation's exact cause.

Actual capability-gated RGBA32F accumulation then RGBA8 conversion matches the
independent linear reference exactly on both software backends across nine views.
It remains a **different precision contract**, not equivalence to the original
per-layer RGBA8 reference; original-reference silhouette comparisons still fail
some cases. RGBA16F also retains Mesa's 8-object central-view silhouette failure.
No original failures or budgets were changed. See blend_precision report's
original/half/linear comparisons rather than treating its float32 PASS as a
retroactive original-tier acceptance.

W6 adds finite affine oblique-gradient and same-texel locality-permutation
controls with independent CPU center references. These do not establish general
high-frequency anisotropic quality or cache/performance improvements.
