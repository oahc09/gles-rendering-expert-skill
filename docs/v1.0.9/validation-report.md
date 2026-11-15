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
