# Release Notes — v1.0.0

**Release Date**: 2026-07-25
**License**: MIT

## 🎉 Initial Release

`gles-rendering-expert-skill` v1.0.0 is the first public release of an **AI Expert Skill for OpenGL ES 3.x rendering**. It injects precise GLES state-machine knowledge, TBDR bandwidth optimization rules, and production-grade C++17 / GLSL ES code patterns into AI coding assistants (Cursor, Claude Code, OpenAI Codex/GPT, Windsurf, and others).

## Highlights

### 🚫 API Boundary Enforcement
- Strict OpenGL ES 3.0 / 3.1 / 3.2 API surface — zero desktop OpenGL contamination (`glBegin/glEnd`, `glPolygonMode`, legacy texture formats are all blocked).
- Per-version feature gating: compute shaders / SSBO / indirect draw require GLES 3.1+; tessellation / geometry shaders require GLES 3.2.
- GLSL ES 3.00 / 3.10 / 3.20 shader compliance: `#version` first line, precision qualifiers, varying precision matching, invariance rules.

### 📉 TBDR Bandwidth Optimization
- Render-pass discipline for tile-based GPUs: clear-on-start (Load Op = DONT_CARE) and `glInvalidateFramebuffer` on pass end (Store Op = DONT_CARE), with documented exceptions.
- Asynchronous pixel readback via double-buffered PBO + fence sync; `glFinish` prohibition in render loops.
- Framebuffer fetch / Pixel Local Storage guidance for tile-local deferred shading without G-Buffer DRAM round-trips.

### 🖥️ Cross-Platform Coverage
- **Android** — NDK toolchain notes, EGL context-lost recovery, shared-context resource loading.
- **Windows** — ANGLE integration with `#ifndef`-guarded ANGLE EGL platform tokens, pre-built DLL acquisition (Chrome/Edge extraction) with `dumpbin → .def → lib` import-library workflow, vcpkg alternative, and Windows-on-ARM (native Adreno GLES) guidance.
- **Embedded Linux** — GBM/EGL headless and DRM/KMS presentation paths.

### 🎯 Vendor-Specific Rule Modules
- **ARM Mali** — Pixel Local Storage, multiview stereo, AFBC-friendly patterns, forward pixel kill.
- **Qualcomm Adreno** — GMEM load/store elimination, on-tile MSAA resolve, LRZ, FlexRender, QCOM variable-rate shading, frame extrapolation & upscaling (AFME / SGSR2).
- **Imagination PowerVR** — HSR (no depth pre-pass needed), PLS deferred shading, IMG extensions (framebuffer downsample, texture filter cubic, binary shaders).

### 🛡️ Code Correctness Rules
- RAII C++17 for all GPU resources — move-only wrapper classes, no raw `new`/`delete`, state caching to eliminate redundant GL calls.
- `glTexStorage2D` immutable textures with correct mipmap level pre-allocation (`levels >= 1 + floor(log2(max(w,h)))`).
- Compute shader synchronization: `memoryBarrierShared()` before `barrier()`, correct `glMemoryBarrier` bit selection.
- Shader numerical stability: safe `normalize`, `pow` guards, `dFdx/dFdy` zero-derivative fallbacks, FP16 (`mediump`) edge cases.
- EGL 1.4-compatible context attributes (`EGL_CONTEXT_CLIENT_VERSION`) for maximum device coverage.

## 📦 What's Included

| Component | Count | Description |
|:---|:---|:---|
| `SKILL.md` | 1 | Core system prompt / skill entry point (Agent Skills spec compliant) |
| Rule documents | 17 | Modular deep-dive rules under `references/rules/` incl. `adreno/` and `powervr/` sub-modules |
| Knowledge cards | 16 | Quick-reference cards under `references/cards/`, one per GLES feature area |
| Code examples | 7 | RAII C++17 sources and GLSL ES 3.00/3.10 shaders under `references/examples/` |
| Agent configs | 2 | `agents/claude-code.yaml`, `agents/openai.yaml` |
| Validation tests | 53 | Structural & content validation suite (pytest) |

## ✅ Quality Assurance

- 53/53 automated validation tests passing.
- Passes `skill-checker` audit: 0 severe findings, 0 warnings.
- Multiple audit rounds covering: Khronos spec compliance, EGL portability, ANGLE behavior quirks (silent zeroing of precision-mismatched varyings), NDK Clang compatibility, and TBDR rule accuracy against vendor documentation (ARM OpenGL ES SDK, Adreno GPU guides, PowerVR performance recommendations).

## 🎯 Supported Targets

- **GPUs**: ARM Mali (T6xx–G715), Qualcomm Adreno (3xx–7xx), Imagination PowerVR (Series 6–10), plus ANGLE-backed D3D11/Vulkan on desktop Windows.
- **APIs**: OpenGL ES 3.0 / 3.1 / 3.2, EGL 1.4+, GLSL ES 3.00 / 3.10 / 3.20.
- **Toolchains**: Android NDK (Clang), Embedded Linux (GCC), Windows (MSVC + ANGLE).

## 🚀 Getting Started

```bash
# Cursor IDE
cp SKILL.md .cursor/rules/gles-rendering-expert.mdc
```

For Claude Projects, ChatGPT Custom GPTs, Windsurf, and other tools, paste `SKILL.md` into the system instructions. See [README.md](README.md) for full setup guidance.

## Acknowledgments

Inspired by [vulkan-rendering-expert-skill](https://github.com/oahc09/vulkan-rendering-expert-skill) — the Vulkan counterpart to this GLES-focused skill.
