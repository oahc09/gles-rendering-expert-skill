# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### Added
- Initial release: SKILL.md, 17 rule documents (incl. `adreno/` and `powervr/`
  modules), 16 knowledge cards, 7 code examples, 2 agent configs, 53-test
  validation suite. See `RELEASE_NOTES.md` for the full 1.0.0 announcement.
