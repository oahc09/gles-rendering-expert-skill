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

## Not complete

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
