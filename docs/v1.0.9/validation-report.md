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
