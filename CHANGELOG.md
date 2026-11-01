# Changelog

## v1.0.5 implementation candidate (not released)

- Added LongRunCapture and deterministic adaptive-quality recommendations with hysteresis, floors, disabled/background handling and visual/capability gates.
- Added actual precision/color scenes, frozen temporal goldens, multiscale/region comparisons, visual degradation rejection and unknown-performance Pareto rows.
- Added real software resource churn, PBO/fence lifecycle accounting and controlled context recreation; estimated owned resources are not physical VRAM measurements.
- Added schema-probed Perfetto SQL evidence and synthetic/real-tool fixtures, plus date-grounded research.
- Preserved prior88 Agent cases, appended24 and extended independent-review metric denominators. No model-quality gain claimed.
- Kept predecessor release gates, metadata1.0.2 and manual-only workflow; no release, physical-device optimization or automatic CI acceptance claimed.


All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - v1.0.4 implementation candidate

- Added actual eight-scene GLES lab, reviewed frozen software visual goldens, parameter sweep and retained optimization/degradation failures.
- Added shared capability/driver/backend capture contract, actual extended software EGL probe and conservative trace CSV/JSON diagnosis with twelve synthetic labeled fixtures.
- Preserved original 64 Agent cases; added 24 executed controlled failure/fix cases and evidence-bound repair scoring. No live-model score claimed.
- Added two Android projects, explicit native AHardwareBuffer/EGLImage import and capability-gated BT.2020/PQ output with SDR fallback; Java/NDK compilation is separate from still-unverified APK/device/import/HDR acceptance.
- Extended existing research updater with UTC-aware date boundaries, incomplete-source status and verified/accepted decision guards; no background scheduler enabled.
- Kept old closure/gates and metadata1.0.2; new release guard cannot hide prior blocked acceptance. Manual-only workflow remains manual.

## [Unreleased] - v1.0.3 candidate

### Added
- Exact full development plan, baseline audit, acceptance traceability and explicit release gates; metadata remains 1.0.2 pending all W0–W7 acceptance.
- Machine-readable scoped rules and 112 distinct structured positive/negative contracts; actual C++17/EGL software smoke and ESSL compiler/linker fixtures.
- 64 annotated Agent scenarios, paired no-skill/with-skill adapter, independent adjudication metrics and synthetic infrastructure tests. No live model-quality score claimed.
- Capability/backend matrices, modern-rendering and diagnosis playbooks, GPU evidence capture workflow and dated official-source research radar.
- Manual-dispatch-only validation workflow; no automatic CI or background schedule enabled.

### Fixed
- GLES3 ReadBuffer default/named FBO rules, texture format guidance, invented native_app_glue context-lost event and cross-context fence/flush/wait guidance.
- Overstated branchless/precision/vendor performance guarantees; distinguish normative correctness from conditional measured recommendations.

### Unverified / release blockers
- Android NDK target compilation and physical-device lifecycle/HDR/AHardwareBuffer/frame-pacing/performance acceptance.
- Real paired model evaluation and independent annotation review. Host Mesa software and synthetic runner tests do not satisfy these gates.

## [1.0.2] - 2026-08-30

### Added
- **Frame pacing rules** (`references/rules/frame-pacing.md` + card 19):
  `eglSwapInterval` caveats on mobile drivers, `AChoreographer` vsync-driven
  frame loop, Swappy (`games-frame-pacing`) for 60–144 Hz panels, buffer-count
  vs latency guidance, symptom→fix table.
- **HDR & wide-gamut display pipeline** (`references/rules/hdr-and-display.md`
  + card 20): WCG vs HDR axis, capability queries, `EGL_GL_COLORSPACE`
  (scRGB-linear / Display-P3), CTA-861-3 mastering metadata for HDR10,
  linear-pipeline rules and device decision table.
- **Vulkan ↔ GLES interop section** in `android-interoperability.md` §4:
  `GL_EXT_memory_object_fd` / `GL_EXT_semaphore_fd` image and sync sharing,
  format contracts, AHardwareBuffer as the interchange format.
- **16 KB memory page alignment rules** (`android-interoperability.md` §5):
  `-Wl,-z,max-page-size=16384`, `llvm-readelf` alignment check, prebuilt `.so`
  caveats, `sysconf(_SC_PAGESIZE)` discipline for Android 15+ / Play requirement.
- **Shader compilation strategy** (`glsl-es-optimization.md` §6.3): program
  binary cache keyed by source+renderer+driver, `GL_KHR_parallel_shader_compile`,
  warmup passes, time-sliced runtime compilation.
- **Shadow mapping on mobile** (`references/rules/shadow-mapping-mobile.md`
  + card 21): TBDR-adapted depth-only shadow pass (depth texture, not
  renderbuffer; `glDrawBuffer(GL_NONE)`), bias tuning, `sampler2DShadow`
  hardware PCF, cascade/atlas sizing.
- **GPU skinning** (`references/rules/gpu-skinning.md` + card 22): UBO matrix
  palette (GLES 3.0, ~64–120 bones) vs SSBO (GLES 3.1+), 4 bone influences,
  skinned-normal re-normalization, once-per-frame palette update.
- **Post-processing chains** (`references/rules/post-processing-chain.md`
  + card 23): downsample-before-blur, pass minimization, ping-pong with
  invalidate, Gaussian / Kawase / Dual / Tent filtering, 3D LUT color grading.
- **GLES translation layers** (`references/rules/translation-layer-gles.md`
  + card 24): ANGLE / MobileGL / SwiftShader host-testing rules — functional
  testing valid, performance testing not; pinned ANGLE backends; missing
  vendor extensions; real-device measurement requirement.
- **Variable Rate Shading** (`references/rules/variable-rate-shading.md`):
  cross-vendor coverage — `GL_QCOM_shading_rate` (Adreno, per Qualcomm's
  mobile-VRS announcement) and the full `GL_EXT_fragment_shading_rate` family
  per MediaTek's Dimensity developer docs: pipeline / per-primitive /
  attachment rates, combiners, per-sample-count rate queries, MSAA
  interaction, PLS/framebuffer-fetch incompatibility, `gl_ShadingRateEXT`
  debug hook. Card 14 cross-references the new doc.
- **Transform Feedback** (`references/rules/transform-feedback.md` + card 25):
  GLES 3.0 core capture of vertex/geometry outputs — varyings-before-link,
  INTERLEAVED/SEPARATE, `GL_RASTERIZER_DISCARD`, primitive-mode matching,
  `GL_TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN` queries, ping-pong particle
  pattern, ES-correct readback (`glMapBufferRange`, no `glGetBufferSubData`),
  compute-shader preference on 3.1+. Adapted from open.gl/feedback.
- **Geometry Shaders** (`references/rules/geometry-shaders.md` + card 26):
  GLES 3.2-only stage rules — input/output layout qualifiers, `max_vertices`
  budgeting (`GL_MAX_GEOMETRY_OUTPUT_VERTICES`), amplification cost model,
  instancing preference, multiview incompatibility, VRS/TF interactions.
  Adapted from open.gl/geometry for ES.
- **MRT depth** (`gles-api-standards.md` §5.2 + card 04): attachment
  consistency (size/sample-count), per-attachment tile-store bandwidth model,
  G-buffer encoding discipline (normal remap, RGBA depth packing), alpha
  channel piggybacking, PLS-over-MRT guidance, deferred-pipeline structure.
  Synthesized from the libcna MRT tutorial.
- **ARM SDK full absorption** (`mali-arm-best-practices.md` §11–§12):
  remaining sample-catalog techniques distilled — tessellation displacement,
  occlusion queries, instancing, min/max blending, integer logic, projected
  lights, skybox depth trick, metaballs, SDF text rendering, Boids, thread
  sync, multisampled FBO — plus a complete SDK-sample → skill-coverage map
  and provenance note (SDK v2.1.2, archived/MIT).
- **Texture streaming & LOD control** (`references/rules/texture-streaming-lod.md`
  + card 27): full-chain `glTexStorage2D` + per-mip `glTexSubImage2D`,
  base/max-level residency gating, PBO + shared-context worker uploads with
  fences, mid-frame `glGenerateMipmap` prohibition, anisotropic-extension
  guard, tile-array virtual-texturing emulation (no sparse textures in GLES).
- **GPU-driven culling** (`references/rules/gpu-culling.md` + card 28):
  compute predication → per-slot `DrawArraysIndirectCommand` →
  `glMultiDrawArraysIndirect` (GLES 3.1) with correct `glMemoryBarrier` bits;
  occlusion-query caveats on TBDR (tile flush, 1-frame latency,
  `GL_QUERY_RESULT_AVAILABLE`); hi-Z alternative; per-GLES-version capability
  matrix.
- **SDF/MSDF text rendering** (`references/rules/text-rendering-sdf.md`
  + card 29): R8 distance atlases (never sRGB formats), `fwidth`-based
  analytic AA with `median()` for MSDF, highp-UV thresholds, one-batched-draw
  discipline, premultiplied-alpha compositing, CJK page/LRU atlas management.
- **Clustered Forward+ lighting** (`references/rules/clustered-lighting.md`
  + card 30): 16×9×24–32 log-Z cluster grid, compute light-list culling with
  per-cluster atomic compaction and fixed CAP, `GL_SHADER_STORAGE_BARRIER_BIT`
  ordering, uint16 list bandwidth math, shadow/hero-light interaction rules,
  Mali/Adreno/PowerVR vendor notes.
- **Screen-space depth effects** (`references/rules/screen-space-effects.md`
  + card 31): SSAO / soft particles / motion blur on TBDR — depth-attachment
  feedback-loop prohibition, `R16F` linear-depth side-write bandwidth model,
  window-Z linearization in highp, half-res + bilateral upsample, hash
  hemisphere sampling, view-space soft-particle fade, velocity-buffer motion
  blur with zero-velocity early reject, MSAA depth resolve interaction.

### Changed
- **SKILL.md slimmed** (~7200 → ~5300 body tokens): the three vendor sections
  (Mali / Adreno / PowerVR) compressed into a single "Vendor Deep-Dives
  (Load On-Demand)" pointer table; Windows/ANGLE section condensed; new
  Android interop/presentation bullets; on-demand loading guide extended with
  frame pacing / HDR / Vulkan interop rows; card count 18 → 20 → 24 → 26 → 30 → 31
  (+ transform feedback, geometry shader, texture streaming, GPU culling,
  SDF text, clustered lighting, screen-space effects).
- **SKILL.md scope made explicitly cross-platform**: frontmatter description
  and role statement now cover mobile (Android), Windows (ANGLE /
  Windows-on-ARM), and Embedded Linux (GBM/EGL) — not mobile-only.
- `glsl-es-optimization.md` §8: corrected `layout(binding=N)` UBO availability
  to GLES 3.1+ (`glUniformBlockBinding` on 3.00).
- README: repository structure + capability table extended; agent configs
  register the new rule files and keywords (`frame pacing`, `Swappy`,
  `HDR display`, `Vulkan interop`, `16KB page`, ...).

### Fixed
- **External security/technical audit remediation** (7 high-risk findings):
  - `particle_simulation.comp`: `memoryBarrierShared()` now precedes
    `barrier()`; early `return` replaced with an `inBounds` guard so every
    invocation reaches every barrier (eliminated GPU-hang UB).
  - `deferred_pls.frag`: split into `PASS_GEOMETRY` / `PASS_LIGHTING` /
    `PASS_RESOLVE` `#ifdef` blocks — no compilation unit writes both PLS
    outputs and fragment color output (EXT_shader_pixel_local_storage rule).
  - `vertex_array_object.hpp` state cache: bounds-checked texture units,
    per-(unit,target) slots, EBO tracking tied to VAO, separate DRAW/READ
    FBO tracking, `kUnknown` sentinel invalidation (eliminated OOB access).
  - `offscreen_pipeline.cpp`: `glInvalidateFramebuffer` moved before the FBO
    switch; move-assignment zeroes the source handle.
  - `egl_context_manager.cpp`: check EGL return values before consuming
    `eglGetError()`, context-lost detection without re-querying error state,
    fence sync + `glFlush` after cross-thread uploads.
  - SKILL.md / shaders: corrected GLES 3.1 → `#version 310 es` mapping;
    removed `layout(binding=N)` from a GLSL ES 3.00 shader (requires 3.10).
  - `adreno/variable-rate-shading.md`: removed invalid
    `glEnable(GL_SHADING_RATE_QCOM)` and nonexistent 2X4 rate.
- 67 validation tests pass; skill-checker audit passes (0 severe; 2 soft
  quality warnings: SKILL.md body near the ~5000-token budget, nested
  `references/` layout depth — both structural, no security findings).

## [1.0.1] - 2026-08-23

### Added
- **Android interoperability rules** (`references/rules/android-interoperability.md`):
  video/camera texture pipeline (`GL_OES_EGL_image_external`), EGLImage sharing,
  and `AHardwareBuffer` ↔ GLES interop with native fence synchronization.
- **GPU profiling toolchain rules** (`references/rules/profiling-tools.md`):
  tool selection matrix (Streamline / AGI / Snapdragon Profiler / Perfetto /
  RenderDoc), per-architecture key counters, and a structured 7-step
  diagnosis workflow.
- **Knowledge cards 17–18**: Android video/buffer interoperability and GPU
  profiling toolchain (`references/cards/`).
- **Three new RAII C++17 examples** (`references/examples/`):
  - `video_texture_pipeline.cpp` — external OES video texture rendering
  - `msaa_ontile_resolve.cpp` — on-tile MSAA via `EXT_multisampled_render_to_texture`
  - `pbo_streaming_upload.cpp` — triple-buffered PBO texture streaming with fences
- **Offline texture compression pipeline** guidance (`astcenc` / `toktx` /
  KTX2 + zstd) in `gles-api-standards.md` §3.3 and card 02.
- **Feature boundary statement** (`gles-api-standards.md` §8): explicit list of
  features OpenGL ES does NOT have — ray tracing (Vulkan-only on mobile RT
  hardware), mesh shaders, bindless textures, explicit subpasses — with the
  GLES-legal alternatives.
- **Newer-generation GPU notes**: ARM Immortalis-G720/G925 (DVS), Qualcomm
  Adreno 8xx, PowerVR Series 12XE — in the respective vendor rule documents.
- Agent configs register the new rule files and trigger keywords
  (`AHardwareBuffer`, `SurfaceTexture`, `video texture`, profilers).

### Changed
- Target GPU lists extended: Mali/Immortalis through G925, Adreno 8xx,
  PowerVR Series 12XE (README).
- SKILL.md: new sections for Android video/buffer interop, profiling
  workflow, and feature boundary; card count 16 → 18; frontmatter keywords
  and `metadata.last-updated` refreshed.

### Fixed
- No correctness regressions; all 53+ validation tests pass, skill-checker
  audit clean (0 severe / 0 warnings).

## [1.0.0] - 2026-07-25

First public release of the **AI Expert Skill for OpenGL ES 3.x rendering**.
Injects precise GLES state-machine knowledge, TBDR bandwidth optimization rules,
and production-grade C++17 / GLSL ES code patterns into AI coding assistants
(Cursor, Claude Code, OpenAI Codex/GPT, Windsurf, and others).

### Added
- SKILL.md, 17 rule documents (incl. `adreno/` and `powervr/` modules),
  16 knowledge cards, 7 code examples, 2 agent configs, 53-test validation suite.

### Highlights

**API Boundary Enforcement**
- Strict OpenGL ES 3.0 / 3.1 / 3.2 API surface — zero desktop OpenGL
  contamination (`glBegin/glEnd`, `glPolygonMode`, legacy texture formats blocked).
- Per-version feature gating: compute shaders / SSBO / indirect draw require
  GLES 3.1+; tessellation / geometry shaders require GLES 3.2.
- GLSL ES 3.00 / 3.10 / 3.20 shader compliance: `#version` first line,
  precision qualifiers, varying precision matching, invariance rules.

**TBDR Bandwidth Optimization**
- Render-pass discipline for tile-based GPUs: clear-on-start (Load Op =
  DONT_CARE) and `glInvalidateFramebuffer` on pass end (Store Op = DONT_CARE),
  with documented exceptions.
- Asynchronous pixel readback via double-buffered PBO + fence sync; `glFinish`
  prohibition in render loops.
- Framebuffer fetch / Pixel Local Storage guidance for tile-local deferred
  shading without G-Buffer DRAM round-trips.

**Cross-Platform Coverage**
- **Android** — NDK toolchain notes, EGL context-lost recovery, shared-context
  resource loading.
- **Windows** — ANGLE integration with `#ifndef`-guarded ANGLE EGL platform
  tokens, pre-built DLL acquisition (Chrome/Edge extraction) with
  `dumpbin → .def → lib` import-library workflow, vcpkg alternative, and
  Windows-on-ARM (native Adreno GLES) guidance.
- **Embedded Linux** — GBM/EGL headless and DRM/KMS presentation paths.

**Vendor-Specific Rule Modules**
- **ARM Mali** — Pixel Local Storage, multiview stereo, AFBC-friendly patterns,
  forward pixel kill.
- **Qualcomm Adreno** — GMEM load/store elimination, on-tile MSAA resolve, LRZ,
  FlexRender, QCOM variable-rate shading, frame extrapolation & upscaling
  (AFME / SGSR2).
- **Imagination PowerVR** — HSR (no depth pre-pass needed), PLS deferred
  shading, IMG extensions (framebuffer downsample, texture filter cubic,
  binary shaders).

**Code Correctness Rules**
- RAII C++17 for all GPU resources — move-only wrapper classes, no raw
  `new`/`delete`, state caching to eliminate redundant GL calls.
- `glTexStorage2D` immutable textures with correct mipmap level pre-allocation
  (`levels >= 1 + floor(log2(max(w,h)))`).
- Compute shader synchronization: `memoryBarrierShared()` before `barrier()`,
  correct `glMemoryBarrier` bit selection.
- Shader numerical stability: safe `normalize`, `pow` guards, `dFdx/dFdy`
  zero-derivative fallbacks, FP16 (`mediump`) edge cases.
- EGL 1.4-compatible context attributes (`EGL_CONTEXT_CLIENT_VERSION`) for
  maximum device coverage.

### What's Included (at 1.0.0)

| Component | Count | Description |
|:---|:---|:---|
| `SKILL.md` | 1 | Core system prompt / skill entry point (Agent Skills spec compliant) |
| Rule documents | 17 | Modular deep-dive rules under `references/rules/` incl. `adreno/` and `powervr/` sub-modules |
| Knowledge cards | 16 | Quick-reference cards under `references/cards/`, one per GLES feature area |
| Code examples | 7 | RAII C++17 sources and GLSL ES 3.00/3.10 shaders under `references/examples/` |
| Agent configs | 2 | `agents/claude-code.yaml`, `agents/openai.yaml` |
| Validation tests | 53 | Structural & content validation suite (pytest) |

### Supported Targets (at 1.0.0)

- **GPUs**: ARM Mali (T6xx–G715), Qualcomm Adreno (3xx–7xx), Imagination
  PowerVR (Series 6–10), plus ANGLE-backed D3D11/Vulkan on desktop Windows.
- **APIs**: OpenGL ES 3.0 / 3.1 / 3.2, EGL 1.4+, GLSL ES 3.00 / 3.10 / 3.20.
- **Toolchains**: Android NDK (Clang), Embedded Linux (GCC), Windows
  (MSVC + ANGLE).

### Quality Assurance
- 53/53 automated validation tests passing.
- Passes `skill-checker` audit: 0 severe findings, 0 warnings.
- Multiple audit rounds covering: Khronos spec compliance, EGL portability,
  ANGLE behavior quirks (silent zeroing of precision-mismatched varyings),
  NDK Clang compatibility, and TBDR rule accuracy against vendor documentation
  (ARM OpenGL ES SDK, Adreno GPU guides, PowerVR performance recommendations).

## Unreleased — v1.0.6 candidate (2026-11-01)

Cross-API AHB/native-fence source, multi-Surface lifecycle, deterministic compute, five advanced effects, twelve precision groups, runtime KTX transcode/video guards, conditional driver records, ten authored compiler reducers and thirty new Agent cases. See [acceptance and limitations](docs/v1.0.6/acceptance.md). Actual software/compile evidence is separated from blocked physical-device/provider acceptance. Metadata remains 1.0.2; no release is claimed.
