# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-08-29

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

### Changed
- **SKILL.md slimmed** (~7200 → ~5300 body tokens): the three vendor sections
  (Mali / Adreno / PowerVR) compressed into a single "Vendor Deep-Dives
  (Load On-Demand)" pointer table; Windows/ANGLE section condensed; new
  Android interop/presentation bullets; on-demand loading guide extended with
  frame pacing / HDR / Vulkan interop rows; card count 18 → 20.
- `glsl-es-optimization.md` §8: corrected `layout(binding=N)` UBO availability
  to GLES 3.1+ (`glUniformBlockBinding` on 3.00).
- README: repository structure + capability table extended; agent configs
  register the new rule files and keywords (`frame pacing`, `Swappy`,
  `HDR display`, `Vulkan interop`, `16KB page`, ...).

### Fixed
- No correctness regressions; 53+ validation tests pass, skill-checker audit
  clean (0 severe / 0 warnings).

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
