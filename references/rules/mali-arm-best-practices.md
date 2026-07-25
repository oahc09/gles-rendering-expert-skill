# ARM Mali GPU Best Practices (Distilled from the OpenGL ES SDK for Android)

> Source of truth: **ARM "OpenGL ES SDK for Android"** tutorials & advanced samples
> (https://arm-software.github.io/opengl-es-sdk-for-android/). This document
> distills the vendor-recommended techniques into actionable rules for code
> generation and review. Everything here targets **ARM Mali GPUs** running a
> TBDR (Tile-Based Deferred Rendering) pipeline, but most rules generalize to
> other tile-based mobile GPUs (Qualcomm Adreno, Imagination PowerVR).

---

## 1. Pixel Local Storage (PLS) — Bandwidth-Free Deferred Shading

**Extension:** `GL_EXT_shader_pixel_local_storage` (and `GL_EXT_shader_pixel_local_storage2`).

Pixel Local Storage exposes the **on-chip tile memory** directly to fragment
shaders as persistent per-pixel storage that survives across draw calls *within
the same render pass*, but is **never written to main memory (DRAM)**. This is
the single most important Mali-specific bandwidth optimization.

### Why it matters on TBDR
Traditional deferred shading writes a fat **G-Buffer** (albedo, normal, depth,
material) to DRAM, then reads it all back in the lighting pass. On mobile this
DRAM round-trip is the dominant power/bandwidth cost. PLS keeps the entire
G-Buffer **inside the tile**, so it is allocated, consumed, and discarded
without ever touching DRAM.

### Rules
- **Prefer PLS over MRT G-Buffers** for deferred shading, decals, translucency,
  order-independent effects, and any multi-pass algorithm where an intermediate
  buffer is consumed within the same frame and never needed afterward.
- Declare storage with `__pixel_localEXT` and give each member an explicit,
  **packed layout format** to minimize tile footprint:
  ```glsl
  __pixel_localEXT FragDataLocal {
      layout(rgb10_a2) vec4 lighting;    // accumulated light
      layout(rg16f)    vec2 minMaxDepth; // view-space depth range
      layout(rgb10_a2) vec4 albedo;      // material color + packed sign bit
      layout(rg16f)    vec2 normalXY;    // reconstruct Z from XY
  } storage;
  ```
- **Keep total PLS size small.** The tile budget is limited (commonly 128 bits
  per pixel). Pack aggressively: store `normal.xy` and reconstruct `z`; pack a
  sign bit into an unused alpha channel; use `rgb10_a2` / `rg16f` rather than
  full `rgba32f`.
- Use `__pixel_local_inEXT` / `__pixel_local_outEXT` variants when a pass only
  reads or only writes storage.
- **Combine PLS with the stencil buffer** to mask work: tag geometry with a
  stencil ID in the geometry pass, then in the shading pass set the stencil test
  to skip pixels with no relevant geometry — avoiding expensive per-pixel
  lighting for empty regions.
- PLS content is **undefined at render-pass start** and **lost at render-pass
  end** — treat it exactly like tile memory. Never expect to read it back on the
  CPU or in a later framebuffer.

### Fallback
If PLS is unavailable, fall back to `GL_EXT_shader_framebuffer_fetch` /
`GL_ARM_shader_framebuffer_fetch` (read current tile color), or as a last resort
a conventional MRT G-Buffer with `glInvalidateFramebuffer` on all transient
attachments.

---

## 2. Multiview Rendering — Single-Pass Stereo / VR

**Extensions:** `GL_OVR_multiview`, `GL_OVR_multiview2`,
`GL_OVR_multiview_multisampled_render_to_texture`.

Multiview renders to **several layers of a 2D array texture in a single draw
call**, halving (or better) CPU draw-call overhead and vertex processing cost
for stereo VR and cascaded shadow maps.

### Rules
- **Always check the extension at runtime** before use (`glGetString(GL_EXTENSIONS)`),
  and resolve `glFramebufferTextureMultiviewOVR` via `eglGetProcAddress` since it
  may be missing from headers.
- Attach **array textures** (`GL_TEXTURE_2D_ARRAY`, allocated with
  `glTexStorage3D`) for both color and depth; **all attachments must have the
  same layer count** or the FBO is incomplete. Bind the FBO to
  `GL_DRAW_FRAMEBUFFER`.
- In the vertex shader, enable the extension and declare the view count; index
  per-view matrices with the built-in `gl_ViewID_OVR`:
  ```glsl
  #version 300 es
  #extension GL_OVR_multiview : enable
  layout(num_views = 2) in;
  uniform mat4 modelViewProjection[2];
  void main() {
      gl_Position = modelViewProjection[gl_ViewID_OVR] * vec4(vertexPosition, 1.0);
  }
  ```
- **`num_views` in the shader must equal the FBO's layer count**, or draw calls
  raise `INVALID_OPERATION`.
- Use **`GL_OVR_multiview2`** (not the base extension) whenever *anything besides
  `gl_Position`* must depend on the view index (e.g. view-dependent lighting,
  specular). The base `GL_OVR_multiview` only allows `gl_Position` to vary.
- **Multiview is incompatible with geometry and tessellation shaders** — do not
  combine them.
- **Foveated rendering:** render extra layers at a narrower FOV (higher effective
  resolution in the center) and blend a high-res central inset over a low-res
  full-frame image with `smoothstep`/`mix` based on distance from screen center.
  This concentrates shading where the eye is focused and slashes fragment cost.

---

## 3. Compute Shaders (OpenGL ES 3.1) — Explicit Parallelism

Compute exposes general-purpose parallel computation with explicit thread
identity, shared memory, and synchronization. Use it for particle systems,
culling, image processing, physics, and FFT.

### Work groups & thread identity
- Declare work-group size with `layout(local_size_x=.., local_size_y=.., local_size_z=..) in;`.
- Implementations guarantee **at least 128 invocations per work group**; query
  the real limit with `glGetIntegerv(GL_MAX_COMPUTE_WORK_GROUP_INVOCATIONS)`.
- Identify threads via `gl_GlobalInvocationID`, `gl_LocalInvocationID`,
  `gl_LocalInvocationIndex`, `gl_WorkGroupID`, `gl_NumWorkGroups`.
- Dispatch with `glDispatchCompute(gx, gy, gz)`; compute runs **asynchronously**
  relative to the rest of GL.

### SSBOs & data layout
- Use **SSBOs** (`GL_SHADER_STORAGE_BUFFER`, bound with `glBindBufferBase`) for
  random-access read/write. Minimum guaranteed size is **128 MiB** (vs. 16 KiB
  for UBOs).
- **Prefer `layout(std430)` for SSBOs** — it tightly packs scalar arrays, unlike
  `std140` which pads scalars to `vec4` (4× waste). `std430` is SSBO-only.
- SSBOs support **unsized trailing arrays** (`float data[];`); query length in the
  shader with `.length()`.

### Shader images (compute writes to textures)
- Bind with `glBindImageTexture(unit, tex, level, layered, layer, access, format)`
  and declare with `layout(FORMAT, binding=UNIT) uniform image2D img;`.
- The **image format layout qualifier must match** the `glBindImageTexture`
  format argument.
- **Never** bind image units via `glUniform1i` — use `layout(binding=UNIT)` in
  the shader.
- Textures used as shader images **must be immutable** — allocate with
  `glTexStorage*`, never `glTexImage2D`.
- Use `imageLoad`, `imageStore`, `imageSize`.

### Shared memory
- `shared` memory is fast on-chip scratch shared across a work group. Guaranteed
  **≥16 KiB**. It is **uninitialized and non-persistent**.
- Use it to convert bandwidth-heavy multi-pass fragment algorithms into a single
  compute pass (keep intermediates on-chip instead of flushing to textures).

### Atomics & synchronization (critical correctness rules)
- Atomic ops (`atomicAdd`, `atomicMax`, `atomicExchange`, `atomicCompSwap`, …)
  work on `uint`/`int` in SSBOs and `shared`; atomic counters use
  `GL_ATOMIC_COUNTER_BUFFER`.
- **Within a dispatch, ordering across threads is NOT guaranteed** (weakly
  ordered memory). To share data between threads you MUST pair a **memory
  barrier + execution barrier**:
  ```glsl
  memoryBarrierShared(); // make shared writes visible
  barrier();             // wait for all threads in the work group
  ```
- Always call `memoryBarrierShared()` **before** `barrier()` — do not assume
  `barrier()` alone flushes shared memory (the spec does not guarantee it).
- `barrier()` in flow control is only legal when the control flow is
  **dynamically uniform** (e.g. branch on a uniform), or every thread hits it —
  otherwise you deadlock.
- **Across GL commands**, compute writes to SSBOs/images/atomics are NOT
  auto-synchronized. Call `glMemoryBarrier(<BITS>)` describing how the data will
  be *read next* (e.g. `GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT` when a compute-written
  buffer is next used as a VBO). Render-to-texture between GL commands *is*
  auto-synchronized by the driver; compute is not.

### Tile-friendly barriers (TBDR-specific)
- **`glMemoryBarrierByRegion()`** only orders memory for fragments in the same
  framebuffer *region* (as small as one pixel). On tiled GPUs this **avoids
  flushing the whole tile buffer to DRAM** that a full `glMemoryBarrier()` would
  force. Prefer it whenever consumers only read data written for the *same*
  pixel (e.g. shader image load/store between two draws at the same location).
- **`layout(early_fragment_tests) in;`** forces early-Z when the fragment shader
  has side effects (image stores / atomics) that would otherwise disable it.
  Restores overdraw rejection — use it whenever a fragment shader writes to
  images/SSBOs but does not modify `gl_FragDepth`.

### Compute-driven techniques from the SDK
- **Particle Flow Simulation:** store particle state in SSBOs, integrate in a
  compute pass, then draw directly from the same buffer (barrier with
  `GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT`).
- **Occlusion Culling with Hierarchical-Z:** build a Hi-Z depth mip pyramid, then
  a compute pass tests each instance's bounding volume against Hi-Z in parallel
  and appends only visible instances (atomic counter) to an indirect draw buffer.
- **Ocean rendering with FFT:** run a GPU FFT (butterfly passes) in compute over
  a spectrum SSBO to synthesize height/normal maps each frame — far cheaper than
  CPU FFT plus upload.

---

## 4. Texture Compression — ASTC & ETC2

Texture bandwidth and memory are first-order mobile costs. **Always ship
compressed textures.**

### ASTC (preferred on modern Mali)
- Requires `GL_KHR_texture_compression_astc_ldr` (or `_hdr`). **Check at runtime**
  before uploading, or `glCompressedTexImage2D` fails with an invalid-format error.
- ASTC uses a **fixed 16-byte footprint per block**; the block dimensions choose
  the quality/size tradeoff. Bit rate is set by block size:

  | Block | bpp  | Typical use                          |
  |:------|:-----|:-------------------------------------|
  | 4x4   | 8.00 | highest quality (UI, hero albedo)    |
  | 6x6   | 3.56 | balanced albedo / general textures   |
  | 8x8   | 2.00 | large diffuse / low-frequency detail |
  | 12x12 | 0.89 | backgrounds / skyboxes / lowest cost |

- Choose the **largest block (lowest bpp) that still looks acceptable** for each
  texture — do not blanket-apply 4x4.
- ASTC supports **1–4 channels and uncorrelated-channel modes** ideal for
  **normal maps and mask/packed textures** (better quality than ETC for normals).
- Decoding needs data from **a single block only** → simpler cache, less
  bandwidth. PSNR is ≥ ETC1/ETC2 at comparable rates.
- Upload path: parse the ASTC header for block dims + image size, compute
  `xblocks*yblocks*zblocks*16` bytes, call `glCompressedTexImage2D`.
- Consider `GL_EXT_texture_compression_astc_decode_mode` ("ASTC low precision")
  to decode to `rgba8`/`rgb9e5` instead of `fp16` — saves bandwidth/energy when
  full precision is not needed.

### ETC2 (baseline, guaranteed in GLES 3.0+)
- ETC2 is **core in OpenGL ES 3.0** (no extension check needed) — a safe baseline
  for RGB/RGBA. Use it when ASTC is unavailable.
- For ETC1 (no alpha) handle alpha via: an atlas with a separate greyscale alpha
  region, a second compressed alpha texture, or a raw 8-bit alpha plane
  (uncompressed = larger but flexible).

### General texture rules
- **Always generate/ship mipmaps** for minified textures — reduces texture cache
  misses, bandwidth, and aliasing. Set `GL_TEXTURE_MIN_FILTER` to a mipmapped mode.
- Prefer **immutable storage** (`glTexStorage2D`) over `glTexImage2D` — enables
  driver optimizations and is required for shader images.

---

## 5. Multisample Anti-Aliasing (MSAA) on Mali

On Mali, MSAA resolves **inside tile memory**, so it is dramatically cheaper than
on immediate-mode desktop GPUs.

### Rules
- **Use 4x MSAA by default.** On Mali, on-tile MSAA resolve is highly efficient
  (typically low single-digit percent overhead on G7x+; varies by generation,
  resolution, and shader complexity). ARM explicitly recommends it over no AA.
- **Avoid 8x/16x MSAA** for real-time content: 16x can cost **>50%** performance
  for diminishing quality gains.
- Prefer **`glRenderbufferStorageMultisample` + on-tile resolve**, or
  `GL_EXT_multisampled_render_to_texture` so the multisampled buffer never
  touches DRAM.
- **Never manually resolve MSAA via an extra full-screen pass** if a tile-resolve
  path exists — that reintroduces the DRAM traffic MSAA-on-tile avoids.
- `glInvalidateFramebuffer` the multisampled attachment immediately after resolve
  so the transient MSAA buffer is never written back.

---

## 6. EGL Surface & Swap Behavior

- **`EGL_SWAP_BEHAVIOR`**: the default `EGL_BUFFER_DESTROYED` lets the driver
  discard the back buffer after `eglSwapBuffers`, which is **optimal on TBDR**
  (no need to reload previous frame into tiles). Only set
  `EGL_BUFFER_PRESERVED` when you genuinely need to accumulate on the back buffer
  across frames — it forces an expensive DRAM→tile reload every frame.
- Prefer to **redraw the full frame each time** and keep `EGL_BUFFER_DESTROYED`.

---

## 7. Geometry Upload & Streaming

- Use **VBO/VAO** for all geometry; never client-side vertex arrays. Set the
  usage hint truthfully (`GL_STATIC_DRAW` for load-once data).
- **Stream large/updating data asynchronously with PBOs** (Pixel Buffer Objects)
  — e.g. the Terrain geometry-clipmap sample uploads terrain via PBO to avoid
  stalling the render thread. Combine with `glFenceSync` to know when the upload
  is safe to consume.
- Use **2D texture arrays + instancing** to render large repeated/tiled content
  (terrain clipmaps, foliage) in few draw calls.
- **Transform Feedback** (GLES 3.0) captures vertex-stage output into a buffer —
  useful for GPU-side particle/boids updates when compute (3.1) is unavailable.

---

## 8. Move Work Down the Pipeline (Overdraw & ALU)

- **Push per-fragment work up to the vertex shader or CPU** whenever the result is
  linear across a primitive or constant per draw (the RotoZoom sample moves
  rotation/zoom math out of the fragment shader for a large speedup). Fragment
  shaders run per-pixel — minimize their cost.
- Minimize **overdraw**: sort roughly front-to-back for opaque geometry, draw
  opaque before transparent, and rely on early-Z (keep `discard` and
  `gl_FragDepth` writes rare, as they disable early-Z).
- Keep dependent texture reads and dynamic branches out of the fragment hot path;
  prefer `mix`/`step`/`smoothstep` over data-dependent `if`.

---

## 9. Quick Technique → Rule Map

| ARM SDK sample | Distilled rule |
|:---|:---|
| Advanced Shading w/ Pixel Local Storage | Keep G-Buffer on-tile with PLS; never DRAM round-trip |
| Multiview / Foveated rendering | Single-pass stereo via array-texture layers + `gl_ViewID_OVR` |
| Introduction to Compute Shaders | `std430` SSBOs, `barrier()`+`memoryBarrierShared()`, `glMemoryBarrier` across commands |
| Particle Flow / Occlusion Culling / Ocean FFT | Do heavy data-parallel work in compute; draw from SSBOs with correct barriers |
| ASTC / ETC2 textures | Ship compressed; pick largest ASTC block that looks right; runtime-check ASTC |
| AntiAlias | 4x MSAA by default (low overhead on-tile); avoid 16x |
| EGLPreserve | Keep `EGL_BUFFER_DESTROYED`; redraw full frame each swap |
| Terrain (geometry clipmaps) | Async PBO upload + texture arrays + instancing for infinite terrain |
| RotoZoom | Move fragment work to vertex/CPU when possible |
