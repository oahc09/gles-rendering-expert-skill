# Imagination PowerVR GPU Best Practices (Distilled)

> **Source of truth:** Imagination Technologies
> [*PowerVR Native SDK — OpenGL ES Framework*](https://github.com/powervr-graphics/Native_SDK/tree/master/framework/PVRUtils/OpenGLES)
> and the official *PowerVR Performance Recommendations* / *Introduction to PowerVR for Developers* documentation.
>
> This module distills PowerVR-specific GLES techniques into focused rule files.
> PowerVR uses a **Tile-Based Deferred Rendering (TBDR)** architecture with **full
> Hidden Surface Removal (HSR)** — a unique hardware pass that eliminates ALL
> invisible fragments before shading. This fundamentally changes rendering strategy
> compared to both desktop GPUs and even other mobile TBDR GPUs (Mali, Adreno).

## Vocabulary: PowerVR-specific terms

| PowerVR term | Meaning | Generic equivalent |
|:---|:---|:---|
| **HSR** (Hidden Surface Removal) | Hardware pass that processes ALL primitives in a tile, determines visibility, then shades ONLY visible fragments | Early-Z / LRZ (partial equivalent — HSR is more thorough) |
| **ISP** (Image Synthesis Processor) | Fixed-function unit performing HSR + depth/stencil tests before fragment shading | Rasterizer + early-Z |
| **USC** (Unified Shading Cluster) | Shader processor units | Shader cores / ALUs |
| **Parameter Buffer (PB)** | Off-chip memory storing transformed geometry for tiling | Bin buffer / tiling buffer |
| **SPM** (Smart Parameter Management) | Hardware manages PB overflow by partial renders | Binning overflow handling |
| **Tile Memory** | Fast on-chip framebuffer per tile (~32×32 pixels) | GMEM (Adreno) / Tile buffer (Mali) |
| **PVRTC** | PowerVR Texture Compression (2bpp / 4bpp); legacy, prefer ASTC/ETC2 on modern HW | — |
| **PVRScope** | PowerVR's GPU profiling tool | Streamline (Mali) / Snapdragon Profiler (Adreno) |

## Rule files in this module

| File | Topic | Maps to SDK example/doc |
|:---|:---|:---|
| [`hsr-and-rendering-order.md`](hsr-and-rendering-order.md) | HSR, no depth pre-pass, alpha test vs blend, draw order | Performance Recommendations §HSR, forum guidance |
| [`pixel-local-storage-and-deferred.md`](pixel-local-storage-and-deferred.md) | PLS for on-chip deferred rendering | `DeferredShading` example |
| [`img-extensions.md`](img-extensions.md) | IMG_framebuffer_downsample, IMG_texture_filter_cubic, binary shaders | `IMGFramebufferDownsample`, `IMGTextureFilterCubic`, `BinaryShaders` |
| [`bandwidth-and-tile-management.md`](bandwidth-and-tile-management.md) | Clear/invalidate, transient stores, parameter buffer, MSAA | `PostProcessing`, Performance Recommendations |

## Golden rules (one-line summary)

1. **Do NOT use a depth pre-pass** — PowerVR HSR already eliminates 100% of hidden opaque fragments; a depth pre-pass doubles geometry cost with zero shading benefit.
2. **Avoid `discard` / alpha test where possible** — it delays HSR, forcing the ISP to defer visibility decisions until after shading; prefer alpha blend for semi-transparent cutouts.
3. **Clear or invalidate every attachment at render-pass start** — prevents tile memory load from DRAM.
4. **Invalidate transient attachments (depth/stencil) at pass end** — prevents unnecessary tile memory store to DRAM.
5. **Use `GL_EXT_shader_pixel_local_storage` for deferred rendering** — keeps G-Buffer on-chip in tile memory, zero DRAM round-trips.
6. **Keep geometry complexity bounded** — excessive vertices overflow the Parameter Buffer, triggering partial renders (SPM) that kill performance.
