# v1.0.9 original-plan completion matrix

**Overall: not release-ready.** This is an original-plan checklist, not an inferred
percentage from test counts. `MET` below means the stated host contract is delivered;
it does not waive inherited releases or imply mobile/provider acceptance.
`completion-matrix.json` is the machine-readable companion.

## W0–W10

| Package | Host delivery | Verified deliverable | Exact remaining work / limits |
|---|---|---|---|
| W0 | **MET** | Original plan/baseline, write access, eight reuse paths, unchanged predecessor hashes; current test mapping, explicit tag and baseline/source-head CI audit | Inherited release gates remain independently binding. |
| W1 | **MET** | 12 labelled synthetic samples, UNKNOWN/missing evidence, overlap/clock domains, frame quantiles; strict metadata and hash-bound real-export samples | Physical capture authenticity is not established by a declared provenance label or file hash. |
| W2 | **MET_BOUNDED** | Legacy bounds plus explicit load/clear/discard/draw/switch/resolve/store/consume state machine; scoped driver condition, unknown propagation; 18 boundary/negative tests | Arbitrary aliased/subresource lifetimes and implicit driver passes are outside the explicitly bounded event model. Real comparable device-counter calibration and DRAM conversion are not measured. Device calibration is optional in the plan, not a fabricated requirement. |
| W3 | **MET_BOUNDED** | Initial 16 pairs now each have CPU goldens and executable negative arms; Variant validator and optional source-bound Trace analyzer integrated; other actual mechanisms retained; fixed-function ABAB software collector executes 104 actual draws/readbacks per driver with source-bound CPU quality controls | Interleaved capture is software quality-only: two fixed workloads, per-observation setup, four AB pairs and three samples/run. It is not a steady-state timing harness or physical protocol; broader distributions are not claimed. Interleaved GPU timing, thermal/frequency/trace evidence and actual negative performance outcomes remain unmeasured. |
| W4 | **PARTIAL** | Gaussian/glass plus actual rain/volume/UI proxies, dynamic cameras, A/B, tile coverage/layers/RGBA/depth/background stats; precision budget gate; actual bounded duplicate-background alpha merge research (draws 11 to 7), three cameras and explicit quality rejection/fallback | Original Mesa RGBA8 high-layer visual failures unresolved. Duplicate-background merge runs on both software backends (9 readbacks each) but candidates reject across the three-camera gate: Mesa has an invalid baseline view and selects UNAVAILABLE; ANGLE keeps baseline. Harness contract PASS is not visual acceptance (visual FAIL). General Gaussian merge and independently scaled far layers are not implemented. Physical overdraw/bandwidth/GPU-time results are absent. The plan allows Gaussian/sprite proxies; learned full 3DGS is not imposed as a new mandatory condition. |
| W5 | **MET_BOUNDED** | Copied candidate 4×4→2×2 intermediate graph; actual three-pass replay; constant passes/checkerboard rejects; closed synchronization vocabulary rejects unsafe graphs before GL | General graph transforms, incoherent compute/image/SSBO barriers and other candidate categories remain outside the closed sequential framebuffer-to-texture replay vocabulary. Device gains cannot be claimed from advisory candidates. |
| W6 | **MET_BOUNDED** | >8 mechanisms, KTX/CPU quality, progressive mip, oblique locality, actual compressed transcode→cache→budget→GL upload/readback chain | Arbitrary assets/high-frequency filtering and asynchronous streaming are not claimed. Async is not a separate mandatory W6 deliverable. CPU phase timing is not GPU upload-stall or residency evidence. Physical residency, GPU upload stalls, DRAM and frame-time/power benefit require real device capture. Logical bytes are not these metrics. |
| W7 | **MET** | All states/quality refusal/hash-bound review; executable registry, gain range and structural completeness ranking; real isolated rollback; actual end-to-end workflow calls shared advise/decide, constant INSUFFICIENT_EVIDENCE and checkerboard REJECTED_BY_QUALITY | Trusted physical capture/reviewer authentication remains external. Isolated finite rollback is not application-wide or context-loss recovery. |
| W8 | **MET_PROTOCOL_AND_SOFTWARE_COLLECTION** | Physical protocol/matrix plus executed three-stage software scene collector, CPU quality rejection/fallback, hash-bound software grouping; physical and software records remain separate | Physical execution adapter and measured vendor-specific strategies are unavailable; do not convert software captures into physical protocol records. Original W8 permits unavailable devices as NOT_RUN. At least one physical device A/B is absent; Mali/Adreno/PowerVR comparisons and temperature/frequency traces are NOT_RUN. |
| W9 | **MET_INFRASTRUCTURE** | 30 new tasks/172 preserved, paired runner, seven metrics; now an actual v1.0.9 scoring CLI with corpus/response/evidence checks | 30 case-specific AI-authored prompt-bound adjudication guides delivered; independent corpus-content review remains incomplete. No authenticated provider paired responses or independent adjudications. Measured-gain metric additionally requires physical GPU evidence. |
| W10 | **PARTIAL** | 90-day corpus/selected review, source-experiment-test links, complete CI, weekly/monthly read-only workflow code | Selected source reviews and experiment hash links delivered; vendor/X coverage conclusions remain incomplete. The entire1319-record corpus is not falsely labelled reviewed. Weekly/monthly read-only workflow code delivered but inactive on Draft branch; activation and observed successful scheduled execution await default-branch merge. Independent human sign-off, all inherited real-device/provider gates and explicit release authorization remain outstanding. |

## Important original-scope distinctions

- The DoD requires S01–S08 correctness/quality/performance evidence **or explicit
  NOT_RUN/blockage**. `scene-coverage.json` records all eight. Capability tiers do
  not impose one million instances on every host; they do not waive reporting.
- S03 remains PARTIAL: constant/checkerboard three-pass replay is only a bounded
  PostFX subchain, not a unified UI + 3D + PostFX scene or measured load/store capture.
  The finite end-to-end Advisor workflow does not close that full scene gap.
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

1. Candidate PostFX graph replay and a bounded end-to-end workflow are delivered.
   The workflow actually calls the shared Advisor after image validation; broader
   representative-scene integration remains outside this finite chain.
2. Resolve W4 original-reference visual failures without changing the target.
   W6 mip/locality and compressed lifecycle controls are now delivered in bounded
   form; do not silently turn arbitrary asset/async expansion into a new DoD.
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
listed missing implementations, not hardware/provider acceptance. The current table above supersedes historical missing-implementation notes. Candidate replay accepts constant input
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
  rejected-candidate restore. Compressed transcode/cache/upload/readback is also
  delivered; asynchronous streaming remains outside the bounded implementation.
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

## Precision admission/fallback cost gate
The explicit policy now requires per-target quality and format/blend capabilities,
queried renderbuffer dimension bounds, logical attachment and transfer budgets.
It selects the cheapest eligible format; when no route meets the original target
and budget it returns UNAVAILABLE, not a failed RGBA8 fallback. Actual selected
routes are redrawn and rechecked; rejected routes cause no admission replay.
Independent quality probes have separately declared finite overhead, not
production zero-cost switching. RGBA32F+conversion allocation is 5× RGBA8 here,
with >4× modeled logical transfers; no physical bandwidth/timing claim.

## Merge versus release

The implementation PR is reviewable with explicitly recorded failures, **not an
automatic merge-ready or release-ready assertion**. Check current exact-head CI,
review and branch protections externally. The release blockers are original W4
visual acceptance, authenticated provider/independent adjudication, inherited
real-device/reviewer gates, incomplete research/observed scheduled execution and
explicit release authorization. Do not require optional generalization merely to
merge honest bounded infrastructure, and do not treat a merge as passing those gates.

Consistency check: `python3 -m unittest discover -s docs/v1.0.9 -p 'test_completion_consistency.py' -v`.
The table is checked against the machine-readable rows and evidence paths; this
check does not authenticate measurements or certify remote CI.

## Bounded background-merge follow-up

The actual W4 experiment merges only adjacent duplicate background proxies with
identical color/projection/depth, using analytic alpha composition and retaining
foreground. Draws fall 11→7, not a measured performance gain. Both software
backends execute nine readbacks; UNORM blending/rounding causes candidate quality
rejection over the three-camera gate. Mesa's baseline also fails one view, so its
result is UNAVAILABLE rather than a failed fallback; ANGLE retains baseline.
The saved visual result remains FAIL while the rejection-protocol contract passes.
W4 therefore stays PARTIAL. General merging and independently scaled far layers
are not claimed, and existing image thresholds are unchanged.
