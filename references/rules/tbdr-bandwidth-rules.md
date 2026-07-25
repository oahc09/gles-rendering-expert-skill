# TBDR Bandwidth & Mobile GPU Optimization Rules

## 1. TBDR Architecture Overview

Mobile GPUs (ARM Mali, Qualcomm Adreno, Imagination PowerVR) use **Tile-Based Deferred Rendering (TBDR)**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        TBDR Pipeline                             │
├─────────────────────────────────────────────────────────────────┤
│  Vertex Shading → Tiling/Binning → Per-Tile Fragment → Writeback│
│  (all geometry)   (sort into tiles)  (Tile Memory)    (→ DRAM)  │
└─────────────────────────────────────────────────────────────────┘
```

- **Tile Memory**: Small on-chip SRAM (16×16 to 64×64 pixels). Extremely fast, zero DRAM bandwidth cost.
- **System Memory (DRAM)**: Off-chip. Every Load/Store between Tile Memory ↔ DRAM costs **significant bandwidth and power**.
- **Key Insight**: Minimize DRAM reads/writes. Keep data in Tile Memory as long as possible.

---

## 2. FBO Lifecycle Rules (Critical for TBDR)

### 2.1 RenderPass Start — SHOULD Clear or Invalidate

```cpp
// ✅ BEST: Clear signals driver that prior tile content is disposable (Load Op = DONT_CARE)
glBindFramebuffer(GL_FRAMEBUFFER, fbo);
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
// ... draw calls ...
```

```cpp
// ⚠️ CAUTION: Missing clear forces driver to load old DRAM content into tiles
glBindFramebuffer(GL_FRAMEBUFFER, fbo);
// No glClear — driver must perform expensive DRAM → Tile load!
glDrawArrays(GL_TRIANGLES, 0, vertexCount);
```

**Why**: Without `glClear`, the GPU must load previous frame's pixel data from DRAM into Tile Memory to preserve it (Load Op = LOAD). With `glClear`, the driver knows tiles start fresh (Load Op = DONT_CARE), saving one full-screen DRAM read per attachment.

**Exceptions where omitting Clear is acceptable**:
- Full-screen post-process pass that overwrites every pixel (e.g. blit, tone-map) — driver can deduce no load is needed.
- Attachment loaded from `glBlitFramebuffer` or `glInvalidateFramebuffer` immediately prior.
- Debug / read-back passes that intentionally read back prior contents.

In ambiguous cases, calling `glInvalidateFramebuffer` before drawing provides the same Load Op = DONT_CARE hint without clearing to a fixed color.

### 2.2 RenderPass End — MUST Invalidate Unused Attachments

```cpp
// ✅ CORRECT: After rendering, depth/stencil no longer needed
GLenum discardAttachments[] = { GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 2, discardAttachments);
// Switch to next FBO or present
```

```cpp
// ❌ WRONG: Depth buffer written back to DRAM even though never read again
glBindFramebuffer(GL_FRAMEBUFFER, nextFbo);  // Implicit flush of depth to DRAM!
```

**Why**: `glInvalidateFramebuffer` tells the driver "Store Op = DONT_CARE" for those attachments. The GPU skips writing tile depth/stencil data back to DRAM, saving one full-screen write per attachment.

### 2.3 Full FBO Lifecycle Pattern

```cpp
void RenderShadowPass(GLuint shadowFbo, GLsizei width, GLsizei height) {
    glBindFramebuffer(GL_FRAMEBUFFER, shadowFbo);
    glViewport(0, 0, width, height);
    
    // START: Clear to avoid DRAM → Tile load
    glClear(GL_DEPTH_BUFFER_BIT);  // Color not attached for shadow map
    
    // DRAW: Render scene from light's perspective
    DrawSceneFromLight();
    
    // END: Depth is consumed later as texture, so do NOT invalidate it.
    // But if there were stencil, invalidate it:
    // GLenum discards[] = { GL_STENCIL_ATTACHMENT };
    // glInvalidateFramebuffer(GL_FRAMEBUFFER, 1, discards);
    
    glBindFramebuffer(GL_FRAMEBUFFER, 0);  // or next FBO
}

void RenderMainPass(GLuint mainFbo) {
    glBindFramebuffer(GL_FRAMEBUFFER, mainFbo);
    
    // START: Clear all attachments
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT);
    
    // DRAW: Full scene
    DrawScene();
    
    // END: Depth & Stencil not needed after main pass (no post-process reads them)
    GLenum discards[] = { GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT };
    glInvalidateFramebuffer(GL_FRAMEBUFFER, 2, discards);
    // Color is presented to screen — do NOT invalidate color
}
```

---

## 3. Bandwidth Reduction Techniques

### 3.1 NEVER: Synchronous glReadPixels

```cpp
// ❌ CATASTROPHIC: Stalls entire GPU pipeline, forces full tile resolve
glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, cpuBuffer);
```

```cpp
// ✅ CORRECT: PBO double-buffered async readback
class AsyncReadback {
    GLuint pbos_[2] = {};
    int current_ = 0;
    GLsizei size_ = 0;
public:
    void Init(GLsizei w, GLsizei h) {
        size_ = w * h * 4;  // RGBA8
        glGenBuffers(2, pbos_);
        for (auto& pbo : pbos_) {
            glBindBuffer(GL_PIXEL_PACK_BUFFER, pbo);
            glBufferData(GL_PIXEL_PACK_BUFFER, size_, nullptr, GL_STREAM_READ);
        }
    }
    
    void RequestReadback(GLsizei w, GLsizei h) {
        glBindBuffer(GL_PIXEL_PACK_BUFFER, pbos_[current_]);
        glReadPixels(0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
        current_ ^= 1;  // Ping-pong
    }
    
    void* GetPreviousFrameData() {
        glBindBuffer(GL_PIXEL_PACK_BUFFER, pbos_[current_]);
        void* ptr = glMapBufferRange(GL_PIXEL_PACK_BUFFER, 0, size_,
                                     GL_MAP_READ_BIT);
        return ptr;
    }
    
    void Unmap() {
        glBindBuffer(GL_PIXEL_PACK_BUFFER, pbos_[current_]);
        glUnmapBuffer(GL_PIXEL_PACK_BUFFER);
        glBindBuffer(GL_PIXEL_PACK_BUFFER, 0);
    }
};
```

### 3.2 NEVER: glFinish in Render Loop

```cpp
// ❌ Blocks CPU until ALL GPU work completes — destroys pipelining
glFinish();
```

```cpp
// ✅ Use fence sync for targeted synchronization
GLsync fence = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0);
GLenum result = glClientWaitSync(fence, GL_SYNC_FLUSH_COMMANDS_BIT, timeoutNs);
if (result == GL_CONDITION_SATISFIED) {
    // GPU work done
}
glDeleteSync(fence);
```

### 3.3 Minimize FBO Switches

Each FBO switch on TBDR may trigger:
1. **Resolve**: Current tile content written to DRAM (Store).
2. **Load**: New FBO content loaded from DRAM to tiles (Load).

**Rule**: Batch all draws targeting the same FBO together. Sort render passes to minimize target switches.

```
Optimal:   [FBO_A draws...] → [FBO_B draws...] → [FBO_A draws...]  // 2 switches
Worst:     [FBO_A] → [FBO_B] → [FBO_A] → [FBO_B] → ...           // N switches
```

---

## 4. Framebuffer Fetch (Tile-Local Read)

### 4.1 Concept
`GL_EXT_shader_framebuffer_fetch` allows fragment shaders to read the **current value in the framebuffer** (from Tile Memory) without a texture fetch from DRAM.

### 4.2 Use Cases
- **Deferred shading**: Read G-Buffer data written in the same pass (no DRAM round-trip).
- **Blending**: Custom blend operations that read destination color.
- **Post-processing chains**: Multiple effects in a single pass reading previous results.

### 4.3 GLSL Usage (GL_EXT_shader_framebuffer_fetch)
```glsl
#version 300 es
#extension GL_EXT_shader_framebuffer_fetch : require
precision mediump float;

// 'gl_LastFragData' contains current framebuffer value (Tile Memory read)
layout(location = 0) inout vec4 fragColor;

void main() {
    vec4 existing = fragColor;  // Read from Tile Memory — ZERO bandwidth cost
    fragColor = mix(existing, vec4(1.0, 0.0, 0.0, 1.0), 0.5);
}
```

### 4.4 Vendor Support
| Vendor | Extension | Notes |
|:---|:---|:---|
| ARM Mali | `GL_ARM_shader_framebuffer_fetch` / `GL_EXT_shader_framebuffer_fetch` | Broad support on Mali-T6xx+ |
| Qualcomm Adreno | `GL_EXT_shader_framebuffer_fetch` | Adreno 3xx+ |
| PowerVR | `GL_EXT_shader_framebuffer_fetch` | Series 6+ |

### 4.5 Pixel Local Storage (PLS) — Keep the Entire G-Buffer On-Tile

`GL_EXT_shader_pixel_local_storage` exposes tile memory as **persistent per-pixel
storage that survives across draw calls within a render pass but is NEVER written
to DRAM**. This is ARM's recommended way to do deferred shading / translucency on
mobile without a fat MRT G-Buffer.

```glsl
#version 300 es
#extension GL_EXT_shader_pixel_local_storage : require
precision highp float;

// Entire G-Buffer lives in tile memory — zero DRAM round-trip.
// Pack aggressively to fit the per-pixel tile budget (~128 bits).
__pixel_localEXT FragDataLocal {
    layout(rgb10_a2) vec4 lighting;    // accumulated light
    layout(rg16f)    vec2 minMaxDepth; // view-space depth range
    layout(rgb10_a2) vec4 albedo;      // color + packed normal sign bit
    layout(rg16f)    vec2 normalXY;    // reconstruct normal.z from xy
} storage;
```

**Rules**:
- Prefer PLS over MRT G-Buffers for deferred shading, decals, translucency, and
  any intermediate consumed within the same frame and never needed afterward.
- Pack storage tightly (`rgb10_a2`, `rg16f`; store `normal.xy`, reconstruct `z`).
  The tile budget is limited — a fat `rgba32f` layout will exhaust it.
- Combine with the **stencil buffer** to skip lighting on pixels with no relevant
  geometry (tag geometry with a stencil ID, then stencil-test the shading pass).
- PLS is undefined at pass start and lost at pass end — treat it exactly like
  tile memory; never read it back on the CPU.
- Fallback order when PLS is unavailable: framebuffer fetch (§4.3) → MRT G-Buffer
  with `glInvalidateFramebuffer` on every transient attachment.

---

## 5. Overdraw & Fill-Rate Optimization

### 5.1 Front-to-Back Sorting
- On TBDR, early-Z rejection happens per-tile. Draw opaque objects **front-to-back** to maximize early-Z culling.
- Draw transparent objects **back-to-front** (required for correct blending).

### 5.2 Avoid Redundant Full-Screen Passes
- Each full-screen pass costs: `width × height × bytesPerPixel` bandwidth (read + write).
- Merge post-processing passes where possible (e.g., bloom + tone mapping + FXAA in one shader).

### 5.3 MSAA Considerations on TBDR
- TBDR GPUs resolve MSAA **within Tile Memory** — much cheaper than desktop.
- **Use 4x MSAA by default.** On Mali, on-tile MSAA resolve is highly efficient
  (typically low single-digit percent overhead on G7x+; varies by generation,
  resolution, and shader complexity). ARM explicitly recommends it over no AA.
- **Avoid 8x/16x MSAA** for real-time content: 16x can cost **>50%** performance
  for diminishing quality returns.
- Use `GL_EXT_multisampled_render_to_texture` (or `glRenderbufferStorageMultisample`
  + on-tile resolve) for implicit resolve — no explicit blit needed.
- Avoid loading multisample textures from DRAM; render and resolve in-place, then
  `glInvalidateFramebuffer` the multisampled attachment so it is never stored.
- **Never** add a manual full-screen resolve pass when a tile-resolve path exists
  — it reintroduces the DRAM traffic on-tile MSAA was designed to avoid.

### 5.4 EGL Swap Behavior
- Keep the default **`EGL_SWAP_BEHAVIOR = EGL_BUFFER_DESTROYED`** — the driver may
  discard the back buffer after `eglSwapBuffers`, which is optimal on TBDR (no
  DRAM→tile reload of the previous frame).
- Only set `EGL_BUFFER_PRESERVED` when you must accumulate on the back buffer
  across frames; it forces an expensive per-frame DRAM→tile reload. Prefer
  redrawing the full frame each swap instead.

---

## 6. GPU-Specific Notes

### ARM Mali
- Tile size: typically 16×16 pixels.
- `glInvalidateFramebuffer` is **critical** — Mali driver heavily optimizes based on discard hints.
- Avoid `GL_DEPTH_COMPONENT16` on Mali-T7xx+; use `GL_DEPTH_COMPONENT24` for better performance.
- Forward rendering with framebuffer fetch is preferred over deferred (limited render targets in tile memory).

### Qualcomm Adreno
- Tile size: varies (32×32 to 128×128 depending on format count).
- Supports `GL_QCOM_tiled_rendering` for explicit tile control (advanced).
- FlexRender: driver dynamically chooses between TBDR and immediate mode.
- `glInvalidateFramebuffer` still beneficial for bandwidth.

### Imagination PowerVR
- True deferred renderer: hidden surface removal (HSR) before fragment shading.
- Overdraw has near-zero fragment shader cost (HSR eliminates it), but bandwidth still matters.
- `glInvalidateFramebuffer` essential for eliminating write-back.
- PVRTC / ASTC compression reduces texture bandwidth significantly.

---

## 7. Bandwidth Estimation Formula

```
Per-attachment per-frame bandwidth = width × height × bytesPerPixel × (loads + stores)

Example: 1080×1920, RGBA8 (4 bytes), 1 load + 1 store:
= 1080 × 1920 × 4 × 2 = ~16.6 MB per attachment per frame

At 60 FPS: ~995 MB/s per attachment
With depth (4 bytes) + stencil (1 byte) invalidated: saves ~20.7 MB/frame = ~1.2 GB/s
```

**Always calculate and communicate bandwidth impact when generating FBO-related code.**
