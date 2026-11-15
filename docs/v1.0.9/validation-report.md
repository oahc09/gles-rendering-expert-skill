# v1.0.9 first implementation validation — 2026-11-15

Status: PARTIAL development candidate. This is not complete original-plan acceptance,
release approval, or a claim of mobile GPU performance improvement.

## Executed

- Baseline main: 427225b3a4cbb498e9112c79ec7857e22421d9dd, merged PR #6.
- Full local sweep: **638 unittest tests passed, zero failures, zero skips**, across
  29 directories; commands and complete output in evidence/unit-tests.json.
- Missing compiler/headers restored from official Debian trixie package index,
  checked package SHA256 and unpacked locally. No system installation/settings
  change. Receipt in evidence/toolchain-receipt.json.
- Real Mesa software GLES shader/scene/texture execution: **56 rendered outputs
  and readbacks, 184 underlying draw calls**, positive and negative controls match.
  16 finite shader pairs (14 image matches, 2 intentionally rejected), four layered
  blend proxies (CPU reference max RGBA8 errors 0/0/1/1; reversed-order controls
  rejected), eight RGBA8 texture controls (4 match, 4 correctly reject).
- 32 GLSL compile/link checks passed, source hashes and compiler diagnostics in
  benchmarks/shader_ab/evidence/glslang.json.
- Recursive predecessor gate bookkeeping passes with release_ready=false; original
  gate files remain byte-for-byte unchanged and archived by hash.

## Historical gaps after first increment (superseded below)

- W3: UBO/SSBO, texture formats, discard/depth, compute/draw fusion and broader
  precision distributions. Sixteen bounded pairs alone are not coverage of these.
- W4: real Gaussian projection/LOD, geometry, dynamic camera, silhouette/parallax,
  spatial heatmap and large-workload scale. Four full-screen proxies are foundational.
- W6: ASTC/ETC2/KTX2/mips/aniso/arrays/PBO upload and latency/residency.
- W5: PostFX scaling lacks sufficient existing semantic/quality-budget model.
- W8: physical Mali/Adreno/PowerVR and cross-backend performance NOT_RUN. Software
  correctness is not bandwidth, thermal, power or GPU speedup evidence.
- W9: real paired model calls and independently authenticated review
  BLOCKED_BY_PROVIDER. Synthetic fixtures are not model quality scores.
- W10: full 90-day deduplicated corpus and manual vendor/X review not complete.
- Final-head hosted CI remains pending until the new PR run finishes.

Advisor review records are evidence protocol inputs, not an identity service.
Only a trusted capture/review entry point may assert physical provenance; local
fixture tests never constitute VERIFIED_IMPROVEMENT claims for a real device.
All original v1.0.3–v1.0.8 gates still bind; merging earlier code did not waive them.
No version metadata change, tag, Release or merge performed.

Public evidence omits environment fingerprints, executable/library hashes and local
paths after privacy review. Source hashes, numeric pixels and correctness results
are unchanged. Original raw environment captures remain local, not published.

## Expanded second implementation — 2026-11-15

The initial remote head 936c76055b73675ae9d01dda624e6af46e2e3d24 passed
GitHub Actions run 43667173688. That result does not cover later commits.

- W3 now executes UBO, SSBO, compute→storage barrier→fragment, discard and depth
  against CPU goldens on both Mesa and ANGLE. Each driver has six correct images
  and six deliberately wrong images; all outcomes match. Missing barriers are
  rejected before execution rather than relying on undefined behavior as an oracle.
- W4 now executes four projected billboard scenes at 64×64, three camera positions
  and three arms each: 36 output images per driver, 24 positive / 12 negative.
  Both drivers pass fixed RGBA8/alpha-mask/centroid thresholds and parallax checks.
  Full pixels, CPU golden and estimated spatial coverage heatmaps are in deterministic
  ZIPs, with archive and per-image hashes. The original ANGLE boundary failure is
  retained. Fix: conservative raster quad plus analytic gl_FragCoord clipping,
  without changing the scene or relaxing thresholds. Actual projected Gaussian
  alpha proxies are still not trained anisotropic 3DGS; tinted glass is not refraction.
- W6 now executes fourteen mechanisms per driver: direct/PBO uploads, generated/
  explicit mips, arrays, R8 swizzle, RGB565, filtering, atlas guard/bleed, resolution
  loss, ETC2, conditional ASTC and anisotropy. Each driver passes twelve positive
  and two negative controls. CPU upload submission cost is explicitly distinct from
  GPU stall or benefit. Complex compressed modes and KTX2 transcoding remain untested.
- Expanded controls total 124 output readbacks across the two drivers (24 W3,
  72 W4, 28 W6), in addition to the initial bounded controls.
- Added a public-evidence hygiene check rejecting environment inventories and local
  absolute paths. Reports retain actual source hashes, numerical results and pixels.

Still incomplete: measured real-GPU A/B performance/power/bandwidth, general source
transform equivalence, learned 3DGS/culling/LOD scale and true refraction, complete
compressed-format/transcoder quality distributions and inherited/provider gates.
All work packages remain conservative PARTIAL/BLOCKED until original DoD is met.

Expanded full local regression: **669 unittest tests passed, zero failures/skips**,
31 directories. Logs: evidence/unit-tests-expanded.json. Final new-head hosted CI
is pending; only the earlier head has the successful run cited above.


## Third increment — bounded software coverage

Exact preceding remote head `da9369e1b0d68178bb9d433c1ede5b3bd3d7ac63`
passed hosted CI run [43668034493](https://github.com/oahc09/gles-rendering-expert-skill/actions/runs/43668034493).
This is prior-head evidence, not evidence of any later commit.

- W1 outputs deterministic nearest-rank p50/p95/p99, min/max/mean and sample count;
  empty samples remain null. These are supplied frame samples, not GPU timings.
- W4 adds authored 3D covariance projection (JΣJᵀ), sorted anisotropic alpha,
  bounded opacity LOD and over-budget fallback, and three refractive plates with
  actual Snell-direction background sampling. Each software driver executes 24
  images over three camera views: 15 positive and nine intentional negatives.
  Correct images max error: Mesa 3 RGBA8 code values, ANGLE 0. This is not learned
  3DGS, million-splat scale, recursive optics or physical performance evidence.
- W5 now accepts explicit PostFX UV/kernel/downstream/quality-budget contracts,
  validates a registered runnable experiment and rejects unsafe output scaling.
  The actual finite texture-resolution oracle passes on both drivers (eight total
  readbacks), but does not prove arbitrary PostFX semantics or execute a 64→32 blur.
- W6 uses checksum-pinned official KTX 4.4.2 to encode UASTC and actually convert
  to RGBA32/ETC2/ASTC, validate a bounded KTX2 container and upload/read back.
  Two gradients × three formats × two drivers = 12 readbacks. Smooth gradient
  passes fixed 32-code budget; steep gradient fails and is preserved as a rejected
  regression, not a successful optimization. Independent CPU RGBA/ASTC decode
  confirms codec-chain error rather than vertical orientation or sRGB mismatch.
  ETC2 lacks an independent CPU decoder, so its error is not attributed to a stage.
  Process elapsed includes startup/I/O and is not isolated transcoder/GPU time.
- Added S01–S08 explicit correctness/quality/performance coverage ledger and strict
  bookkeeping tests; it cannot promote software tests to physical acceptance.

The third increment adds **68 actual output readbacks** (48 W4 + 8 W5 + 12 W6).
No hardware/provider gate is waived. Public reports remain environment-sanitized.
Current limitations include physical mobile timing/counters/thermal/power, real
model paired results, trained/large-scale 3DGS, recursive optics, general KTX2 and
codec distributions, complete research review and all inherited gates.

Third-increment full local regression: **725 unittest tests passed, no failures or
skips**, 31 directories; `evidence/unit-tests-third.json`. Rolling research metadata
collection now has ten sources and 1,319 deduplicated candidates for the inclusive
90-day window ending 2026-11-15. Manual review and rule promotion remain incomplete.


## Fourth increment — selected source analysis and finite coverage

Prior exact head `01fa6970a0429746e67fd5d88d508b446ab297d2` passed CI
[43669422853](https://github.com/oahc09/gles-rendering-expert-skill/actions/runs/43669422853).
That historical run does not cover subsequent changes.

- Read six selected official release-note records and four actual ANGLE/Filament
  commit patches. These ten analyses are AI source inspection, not independent
  human approval. Empty Vulkan CTS notes are deferred; remaining corpus/vendor/X
  review remains incomplete. No performance rule promoted.
- S05 now has actual RGBA16F HDR→Reinhard→explicit sRGB→RGBA8 two-pass software
  validation. Each driver has three HDR and twelve SDR readbacks. Correct float
  and SDR results exactly match CPU golden; nine negative outputs per driver are
  rejected. HDR display/PQ/HLG/wide-gamut/device acceptance remain untested.
- Source-informed packing controls add eight cases × three variants × two drivers
  (48 actual readbacks). Fixed variants pass and deliberate negatives fail. Legacy
  expressions differ between the two implementations: diagnostic only, not exact
  upstream-bug reproduction or physical integer-width proof.
- Attachment controls add eight readbacks per driver, including real normalized→
  integer→normalized FBO replacement and sparse indexed mixed-format MRT. Five
  positive comparisons pass and three deliberate negatives fail per driver;
  normalized transition outputs remain byte-identical. Not exhaustive MRT coverage.
- KTX tests now compare ETC2 against the pinned official 4.4.2 CPU unpacker. Both
  drivers match CPU exactly for the two generated blocks; steep original-image
  error119 already exists in CPU decode. The internal ABI is narrowly pinned,
  not a portable public API or all-mode validation. Stronger DFD/KVD/truncation/range
  checks and a separate decision gate ensure rejected quality never becomes a
  verified improvement, even when the regression harness itself passes.

Fourth increment adds **94 new software readbacks** (30 HDR +48 packing +16
attachment), and reruns the previous twelve KTX outputs with independent ETC2
checks. This remains correctness evidence, not physical performance.

Fourth-increment local regression: **778 tests passed, zero failures/skips**,
33 directories. Evidence: `evidence/unit-tests-fourth.json`. Hosted CI for the
new commit must be verified separately; prior successful runs are not substituted.


## Fifth increment — finite particle pipeline and real rollback

Preceding exact head `41abfd7ccd27915ce73386392153493bdf78724d` passed
[CI 43670584989](https://github.com/oahc09/gles-rendering-expert-skill/actions/runs/43670584989).
It does not cover later source changes.

- S04 now performs compute writes to a four-record SSBO, then proper barriers and
  vertex-stage SSBO consumption. Three frames × correct/wrong-frame/wrong-index
  arms run on each software driver: 18 total image readbacks plus 18 buffer maps.
  Positive images match independent CPU golden exactly; deterministic negatives
  fail. No barrier is intentionally omitted and no invalid index is submitted.
- S08 retains actual baseline objects while trying four candidates per driver.
  Quality failures are rejected; missing evidence and correct-but-unmeasured PBO
  candidates stay unaccepted. Restore rebinds program/texture/FBO/VAO, queries GL
  bindings, clears before redraw to prevent stale-image false positives, and obtains
  byte-identical baseline pixels. Eighteen image readbacks total, not app-wide or
  context-loss recovery. The shared decision API now accepts one observation;
  no fake duplicate compression branches are manufactured to reuse a gate.
- Multi-SSBO rebind controls add 36 compute dispatches and 20 host maps including
  prime reads across both drivers. Correct bindings match CPU values; the wrong
  final binding deterministically changes two resources. All dependencies retain
  consumer-specific barriers. Internal Vulkan event tracking is not verified.
- A fixed, source-controlled full-unit manifest and one-command runner now emit
  sanitized count/status summaries. Zero tests, unrecognized results, skips or
  failed subprocesses cannot be summarized as PASS. Runtime GPU controls remain
  separate from unit tests and hardware/provider gates.

Fifth increment adds **36 finite image readbacks and 38 buffer maps** across two
software implementations. No physical speedup, complete simulation, arbitrary
application rollback or exact upstream bug reproduction is claimed.

Fifth-increment full local unit regression: **811 tests passed, zero skipped**, 35
directories. Reproduce with `python3 tools/run_v109_regression.py --output REPORT_JSON`.
Safe summary: `evidence/unit-tests-fifth.json`. Exact new-head hosted CI must still
be checked independently; software results do not close real-device/provider gates.

## Original-plan completion audit and concrete gap closure

See `completion-matrix.md` and its machine-readable JSON for W0–W10, separating
host delivery from acceptance and external evidence. This is not an all-complete
release declaration. W2/W3/W4/W6/W10 still contain specific feasible host work.

This consolidation closes missing real-export file/hash/sample binding, workload
metadata validation, executable experiment registry binding, conservative gain
interval/completeness ranking, actual sampling/fusion A/B controls, a reusable
multi-frame logical-budget LRU streaming planner with real GL eviction/reload,
and a fail-closed provider scoring CLI. The provider run remains blocked with
zero responses and null rates, not successful synthetic provider evaluation.

Both new GPU runners were independently rerun against Mesa and ANGLE and returned
HOST_PASS. Shader optimization pairs preserve finite CPU oracle equality and
reject negative arms; no compiler work reduction or physical speedup is inferred.
Streaming uses synchronous whole RGBA assets and does not claim progressive mip,
compressed async streaming, physical residency or transactional GPU rollback.

Host regression summary: `evidence/host-regression-matrix.json`. Original inherited
gates and release metadata are unchanged. Final exact-head CI is recorded in PR #7,
not inferred from any earlier successful head.

## Lifecycle, per-pair negatives, and executable graph replay
W2 now models explicit attachment event sequences and scoped FBO switch conditions,
with 18 state/boundary tests; it remains a logical conditional model, not DRAM or
authenticated driver knowledge. W3 initial 16 pairs each have CPU goldens and a
wrong shader, reuse the existing Variant validator, and optionally connect
source-bound exported Trace analysis. Actual no-capture runs say NOT_MEASURED.

W5 now copies a finite graph to a resized intermediate, verifies its closed
coherent dependency vocabulary, and executes three GLES stages. Constant input
passes; checkerboard degradation is rejected and the baseline graph selected.
Unsafe dependencies/feedback/unknown barrier declarations reject before GL.
Incoherent shader writes and general graph transformations remain out of scope.

Both updated runtime paths were rerun independently on Mesa and ANGLE: HOST_PASS.
Complete regression: **895 tests, zero skips**, 36 directories. Evidence summary:
`evidence/host-regression-lifecycle-replay.json`. Hardware/provider gates unchanged.

## Scene collector, mip refinement and tier admission
W8 now executes an actual finite scene and ingests hash-bound software records,
recalculating CPU/quality gates instead of trusting saved PASS flags. Grouping
keeps backend/workload/graph identities distinct. It remains SOFTWARE_QUALITY_ONLY;
the physical protocol still rejects these records. W6 explicitly uploads mip
levels with logical budgets, fixed max-channel32 gate, and actual restore after
rejection. It is synchronous RGBA, not compressed asynchronous streaming.

W4 adds 8/24/48 proxies across three cameras: grouping is pixel-identical and
changes tint uniform updates N to2, not draw count. Both drivers reject all
half-resolution candidates at unchanged thresholds. **Mesa baseline tiers24/48
FAIL CPU-golden tolerance** (maximum errors5–11 versus budget4), so fallback at
those tiers is not acceptable. Root cause undetermined; no threshold increase.
ANGLE passes all baseline tiers. CI explicitly tests the rejection/admission
contract, not all-tier visual acceptance; reports preserve FAIL. Evidence includes
raw pixel ZIPs and independent CPU geometric heatmaps, not physical counters.

W9 case-specific prompt-bound guidance remains AI-authored, not adjudicated model
results. W10 source-review/experiment/test hash links reject stale bindings and
unauthorized rule promotion; full corpus/vendor/X and independent review remain.

Complete host regression for this increment: **934 tests, zero skips**, 36 directories; summary `evidence/host-regression-scene-collector.json`. This does not override the explicitly failed Mesa high-tier images.

## Quantitative blend-precision investigation
RGBA8 source quantization/split-product hypotheses reduce but do not eliminate
Mesa's discrepancy; installed-driver root cause remains unconfirmed. Original
RGBA8 evidence/thresholds stay unchanged. RGBA16F and capability-gated RGBA32F
are actually rendered and compared against three explicitly different reference
contracts (original per-layer UNORM, half accumulation, ideal linear).

RGBA32F matches ideal linear RGBA8 output exactly for all nine views on both
backends and rejects deliberate object removal. It is not a lossless fix for the
original UNORM target: original-reference silhouettes can still differ.
RGBA16F retains Mesa central-view eight-object silhouette FAIL. Missing advertised
capabilities are NOT_SUPPORTED, while compile/FBO/GL errors fail rather than
being swallowed as successful skips. CI's explicit float32 contract check does
not overwrite any retained half/UNORM failure.

Independent repeated affine texture/locality runs also return HOST_PASS on both
backends, four readbacks each with zero error against their finite CPU reference.

Current complete regression: **945 tests, zero skips**, 36 directories; `evidence/host-regression-blend-precision.json`. Both final-source precision runners independently re-executed; their intentional half/UNORM failure remains distinct from the float32 contract pass.

## Precision capability, cost and fallback admission
Added a strict single-sample policy plus actual selected-format replay.
original_unorm and linear quality are separately computed; capability and size,
logical allocation and logical transfer budgets all gate selection. Among
eligible routes choose cheapest, not automatically RGBA32F. All-rejected cases
are UNAVAILABLE with zero additional replay operations. Selected candidates are
actually redrawn and quality checked, not accepted from a cached PASS flag.

For64×64×48, RGBA32F plus conversion output uses81,920 logical bytes (5× baseline)
and6,373,376 modeled transfer bytes (>4× baseline). These are not physical
residency/DRAM/time. Candidate probes are independent bounded validation overhead
before scenario admission, explicitly not a zero-cost production switcher.
Original Mesa UNORM failures are still unresolved; hardware/provider unchanged.

Current complete regression: **967 tests, zero skips**, 36 directories. Final-source admission runners independently returned HOST_PASS; Mesa34/ANGLE28 of48 policy scenarios are explicitly UNAVAILABLE, not accepted scenes.

## Integrated user-facing host chains
The workflow CLI now binds a closed authored workload to fingerprint and graph
cost estimates, executes registered actual GLES, rereads hash-bound captures,
recalculates CPU quality and calls the existing optimization_advisor.advise/decide.
Constant output is INSUFFICIENT_EVIDENCE for performance; checkerboard is
REJECTED_BY_QUALITY. Both keep baseline in production, never software VERIFIED.

Compressed streaming now connects pinned official UASTC/libktx preparation,
independent CPU quality, content cache, logical LRU budgets and actual GLES
compressed upload/eviction/readback in one run. A steep119-error compressed asset
fails budget32 and uses original lossless RGBA with zero error, not lossy decode.
CPU phase timings are separately recorded; physical stalls/residency remain null.

Added real finite rain, Beer-Lambert slice volume and rounded UI scenes over
three cameras, positive culling and negative visible-removal. Tile reports include
coverage/layers, color/alpha, depth and background transmittance estimates.
These are finite authored models, not true refractive drops/volume raymarch or
physical GPU counters. Old high-layer UNORM failures remain unchanged.

Original mandatory delivery is now separated from optional expansion in
original-scope-audit.md. Weekly/monthly radar workflow code is read-only and
artifact-only, but cannot run on this Draft branch: not an active schedule claim.

Integrated regression: **996 tests, zero skips**, 38 directories; `evidence/host-regression-integrated.json`. All three new runtime chains independently rerun on both backends. This does not close original high-layer visual, physical device, provider or independent-review gates.

## Original-plan core closure: interleaved capture and background merge

The bounded shader collector now performs real ABABABAB repetitions with fixed
source bindings and independent CPU pixel checks, rather than only accepting a
pre-filled sequence. Mesa and ANGLE each execute 104 draw/readbacks. No GPU timer,
thermal stability or physical capture is invented; good pixels remain insufficient
performance evidence and bad pixels are rejected.

The new background merge experiment preserves foreground geometry and analytically
combines only adjacent identical background alpha profiles. It reduces 11 draws to
7, but normalized-target rounding causes quality rejection across the tested camera
set. Both drivers reject the candidate globally; Mesa also has a failing baseline
view, so fallback is UNAVAILABLE, while ANGLE retains baseline. These are retained
failures, not an accepted optimization. See `BACKGROUND_MERGE.md` for exact scope.

The completion matrix, readable table and release gate now have executable
consistency checks. GitHub mergeability is a Git property, not acceptance of the
original plan. Physical/provider/independent-review and inherited gates remain.

CI run 43678855409 correctly failed the new background-merge contract because the
camera diagnostic list was left empty. The producer now populates all three camera
records; an archived-report/source-hash regression prevents this false local-pass
assumption. Both exact CLI commands subsequently returned exit 0 with visual FAIL
and contract PASS, and the complete host suite passed 1,025 tests with zero skips.
No image threshold, negative control or baseline-admission rule was relaxed.

## Independent far-resolution and integrated S03

Far-only scaling now renders a separate 32x32 background FBO, nearest-copies to a
64x64 target and composites the unchanged full-resolution foreground. Across three
cameras, the low-resolution candidate exceeds the original fixed color/silhouette
budgets; both software backends retain one full-resolution baseline strategy.
Its own CPU mechanism oracle passes and negative foreground deletion is rejected.
Default CLI returns failure for visual acceptance; contract-only mode verifies the
rejection machinery without rewriting that failure.

S03 now actually combines DEPTH24 orthographic geometry, alpha UI, independent
PostFX and screen targets. Each software backend executes 75 draws/45 readbacks
across three cameras and five variants. Independent per-stage CPU reference has a
fixed one-code budget. Equivalent shader passes; half-resolution, disabled depth
and wrong UI alpha are rejected. API-derived attachment preservation and overwrite
records are not physical tile traffic. This finite 8x8 integration does not claim
production scene coverage or physical GPU performance.
