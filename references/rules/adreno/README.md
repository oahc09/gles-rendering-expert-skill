# Qualcomm Adreno GPU Best Practices (Distilled)

> **Source of truth:** Snapdragon Game Studios / Qualcomm
> [*Adreno GPU OpenGL ES Code Sample Framework*](https://github.com/SnapdragonGameStudios/adreno-gpu-opengl-es-code-sample-framework)
> and the Qualcomm *Adreno GPU on Mobile: Best Practices* documentation.
>
> This module distills the vendor-recommended Adreno techniques into small,
> focused rule files (one topic per file) so they stay easy to consume during
> code generation and review. Everything here targets **Qualcomm Adreno** GPUs,
> which use a **tiled / binning** architecture; most rules also help other
> tile-based mobile GPUs (ARM Mali, Imagination PowerVR).

## Vocabulary: Adreno vs. the generic TBDR terms

| Adreno term | Meaning | Generic equivalent |
|:---|:---|:---|
| **GMEM** (Graphics Memory) | Fast on-chip tile memory | Tile memory / on-chip framebuffer |
| **GMEM Load** | Copy a tile from system memory *into* GMEM at render-pass start | Tile "load" / unresolve |
| **GMEM Store** | Write a GMEM tile *back* to system memory at render-pass end | Tile "store" / resolve |
| **Binning / FlexRender** | Pass that sorts primitives into tile bins | Tiling / deferred binning |
| **LRZ** (Low Resolution Z) | Early coarse depth rejection of hidden fragments | Hidden-surface removal / early-Z |

## Rule files in this module

| File | Topic | Maps to sample |
|:---|:---|:---|
| [`gmem-load-store.md`](gmem-load-store.md) | Avoid GMEM loads, reduce GMEM stores | `avoid_gmem_loads`, `reduce_gmem_stores` |
| [`efficient-msaa.md`](efficient-msaa.md) | On-tile MSAA resolve without a blit | `msaa` |
| [`variable-rate-shading.md`](variable-rate-shading.md) | `QCOM_shading_rate` (VRS) | `shading_rate` |
| [`lrz-and-flexrender.md`](lrz-and-flexrender.md) | LRZ, FlexRender/binning, depth choices | `hello_gltf` scenes, general arch |
| [`frame-extrapolation-and-upscaling.md`](frame-extrapolation-and-upscaling.md) | AFME, motion estimation, SGSR2 | `amfe_power_saving`, `motion_estimation`, `sgsr2` |

## Golden rules (one-line summary)

1. **Clear or invalidate every attachment at render-pass start** → kills GMEM loads.
2. **Invalidate transient attachments (depth/stencil/MSAA) at render-pass end** → kills GMEM stores.
3. **Resolve MSAA on-tile** via `EXT_multisampled_render_to_texture`, never a manual blit.
4. **Never break LRZ**: draw opaque front-to-back, avoid `discard` / fragment depth writes where possible.
5. **Spend fewer fragment invocations**: use `QCOM_shading_rate` on low-detail draws and temporal upscaling (SGSR2) instead of shading every pixel every frame.

## Newer-Generation Notes (Adreno 8xx, Snapdragon 8 Elite era)

Adreno 8xx keeps the tiled/binning architecture — **all rules in this module
still apply**. Generation-specific notes:

- **GMEM capacity grew** versus 6xx/7xx generations, so more attachments / MSAA
  samples can stay on-tile before a pass must split. Do not hard-code GMEM size
  assumptions; measure with Snapdragon Profiler and keep attachment footprints
  minimal regardless.
- **LRZ behavior remains the same contract**: opaque front-to-back, depth
  test+write on, avoid `discard` / `gl_FragDepth` in opaque materials.
- **Ray tracing** hardware is exposed via **Vulkan only** — OpenGL ES has no
  RT extension surface on Adreno. For GLES code, treat RT as out of scope.
- The `QCOM_*` extension family (shading rate, frame extrapolation, motion
  estimation) must still be **runtime-checked** per device — presence varies by
  SoC and driver even within the same generation.
