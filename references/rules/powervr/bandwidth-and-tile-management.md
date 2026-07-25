# Bandwidth and Tile Management

> Distilled from PowerVR Performance Recommendations and Native SDK patterns
> (HelperGles.h, PostProcessing example).

PowerVR uses ~32×32 pixel tiles with fast on-chip tile memory. Like all TBDR
GPUs, the critical performance axis is **DRAM bandwidth** — how much data moves
between tile memory and system memory at the boundaries of each render pass.

---

## Rules

### 1. Clear or invalidate every attachment at render-pass start

If the driver doesn't know that prior tile contents are irrelevant, it must
**load** the old framebuffer data from DRAM into tile memory at the start of the
pass (a "tile load"). This is pure waste if you're going to overwrite it.

```cpp
// ✅ Tells the driver: tile memory contents are don't-care at start
glBindFramebuffer(GL_FRAMEBUFFER, fbo);
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT);
// ... or use glInvalidateFramebuffer before rendering begins
```

**Common mistakes that trigger unnecessary loads:**
- Clearing with scissor enabled (only partial clear → driver loads uncovered
  region).
- Blending over a target that was never cleared (driver must load prior data).
- Forgetting to clear depth/stencil when the pass uses them.

### 2. Invalidate transient attachments at render-pass end

Depth, stencil, and MSAA resolve buffers are often transient — needed during the
pass but not afterwards. If not invalidated, the driver **stores** them back to
DRAM (a "tile store") wasting bandwidth.

```cpp
// ✅ Invalidate after the pass — no need to store depth/stencil to DRAM
const GLenum discards[] = { GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 2, discards);
```

### 3. Avoid mid-frame FBO switching where possible

Every FBO switch (bind a different framebuffer while the previous one is
mid-render) can force a **full tile flush** — store all in-progress tiles of
the old FBO, then load/clear the new one. This is the single most expensive
operation on a TBDR GPU.

- **Batch all geometry for a single FBO together** before switching.
- **Never read from a texture that is also attached** to the current FBO (forces
  flush + resolve for that attachment).
- If multiple render targets are needed in one pass, use **MRT** or **PLS**
  instead of multiple FBO switches.

### 4. `glReadPixels` and `glCopyTexSubImage2D` are slow

Both force an **immediate tile flush + resolve** to make data available on the
CPU/other texture. Defer to end of frame, or use **PBO async readback**
(`GL_PIXEL_PACK_BUFFER`) to overlap the readback with next frame's rendering.

### 5. MSAA — on-tile resolve only

Use `EXT_multisampled_render_to_texture` (or `IMG_multisampled_render_to_texture`)
to keep MSAA samples in tile memory and resolve on-chip. The PowerVR SDK's
`HelperGles.h` uses this approach for all antialiased offscreen targets.

**Never** render to a separate multisample renderbuffer and `glBlitFramebuffer`
to resolve — that's a store + load round-trip through DRAM.

### 6. Parameter Buffer awareness

Unique to PowerVR: all submitted geometry for the frame is stored in the
**Parameter Buffer** until all tiles are rendered. If scene complexity exceeds
PB capacity, **SPM (Smart Parameter Management)** kicks in — the hardware does a
partial render (flush current tile progress, free PB, continue). This is very
costly.

Mitigations:
- **Aggressive LOD** for distant objects.
- **Frustum culling** on the CPU before submission.
- **Avoid redundant geometry** — don't submit objects you know are fully
  occluded (use occlusion queries or software rasterizer for visibility).
- **`glFenceSync` + `glClientWaitSync`** between frames can ensure the PB from
  frame N–1 is freed before frame N fills it. Use a fence-based throttle (not
  `glFinish`) to limit queue depth while preserving CPU/GPU overlap.

### 7. Texture compression

The PowerVR SDK supports PVRTC (2bpp/4bpp, legacy) and standard ASTC/ETC2.

- **Prefer ASTC** for new content — universally supported on GLES 3.0+ hardware
  (including PowerVR Series 8+, IMG CXT).
- **PVRTC** is only required for legacy PowerVR Series 5/6 devices. The SDK
  includes software PVRTC decompression fallback for platforms that don't
  support it natively.
- **Always use `glTexStorage2D`** (immutable storage) — avoids re-allocation
  and enables driver optimizations for tiled texture access.

---

## SDK Utility Patterns (from HelperGles.h)

| Pattern | Description |
|:---|:---|
| `checkFboStatus()` | Validate FBO completeness with human-readable error logging |
| `deleteTexturesAndZero(tex...)` | Variadic: delete + zero handle to prevent double-delete |
| `textureUpload(app, file)` | Load from PVR/KTX/TGA, auto-detect format, upload with `glTexStorage2D` |
| `throwOnGlError(note)` | Debug-build GL error check; NOP in release (`debugThrowOnApiError` macro) |
| `createSingleBuffersFromMesh(mesh, vbo, ibo)` | Interleaved VBO + IBO, `GL_STATIC_DRAW` |
| `glFenceSync` (not `glFinish`) | Used for GPU-CPU sync in ES 3.0+; `glFinish` only on ES 2.0 fallback |
