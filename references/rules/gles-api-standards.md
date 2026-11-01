# OpenGL ES API Standards & Desktop API Prohibition Rules

## 1. Supported API Versions

| Version | GLSL ES | Key Features |
|:---|:---|:---|
| OpenGL ES 3.0 | GLSL ES 3.00 | VAO, UBO, MRT, ETC2, Transform Feedback, Instancing, PBO |
| OpenGL ES 3.1 | GLSL ES 3.10 | Compute Shader, SSBO, Image Load/Store, Indirect Draw, Separate Shader Objects |
| OpenGL ES 3.2 | GLSL ES 3.20 | Geometry Shader, Tessellation, ASTC, Debug Output, Blend Equation Advanced |

**Default target**: OpenGL ES 3.0+ with GLSL ES 3.00. Use 3.1/3.2 features only when explicitly required.

---

## 2. Desktop OpenGL Prohibited API Table

The following desktop OpenGL functions and patterns are **strictly forbidden** in any generated code. They do not exist in the OpenGL ES specification.

### 2.1 Immediate Mode (Removed in GLES entirely)
```
glBegin() / glEnd()
glVertex2f/3f/4f, glColor3f/4f, glNormal3f, glTexCoord2f
glRectf, glRecti
```
**GLES Equivalent**: Use VBO + VAO + `glDrawArrays` / `glDrawElements`.

### 2.2 Fixed-Function Pipeline State
```
glEnableClientState / glDisableClientState
glVertexPointer / glColorPointer / glNormalPointer / glTexCoordPointer
glMatrixMode / glLoadIdentity / glMultMatrixf / glOrtho / glFrustum
glLight / glMaterial / glShadeModel
glFog / glFogf / glFogi
```
**GLES Equivalent**: All handled in shaders; use UBOs for matrices and material data.

### 2.3 Display Lists
```
glGenLists / glNewList / glEndList / glCallList / glCallLists / glDeleteLists
```
**GLES Equivalent**: Pre-record draw commands into command buffers or use indirect draw (GLES 3.1+).

### 2.4 Raster & Pixel Operations
```
glBitmap / glPixelZoom / glRasterPos2f/3f
glDrawPixels / glCopyPixels
glPixelMap / glPixelTransferf
```
**GLES Equivalent**: Use textured quads or compute shaders for pixel manipulation.

### 2.5 Polygon & Primitive Modes
```
glPolygonMode(GL_FRONT_AND_BACK, GL_LINE/GL_POINT)
GL_QUADS / GL_QUAD_STRIP / GL_POLYGON primitive types
```
**GLES Equivalent**: triangles, points and line primitives are legal; use triangle lists/strips/fans to replace polygon modes. For wireframe, use barycentric coordinate technique in shader or geometry shader (GLES 3.2).

### 2.6 Draw Buffer / Read Buffer
```
glDrawBuffer(GL_BACK) / glReadBuffer(GL_FRONT)  // Desktop single-buffer selection
```
**GLES Equivalent**: `glDrawBuffers(n, bufs)` for MRT (GLES 3.0+). `glReadBuffer` is core GLES 3.0: default framebuffer accepts `GL_BACK` or `GL_NONE`; a named framebuffer accepts `GL_COLOR_ATTACHMENTi` or `GL_NONE` (within implementation limits). `GL_FRONT` is not a GLES read-buffer selector. Select a present attachment before readback.

### 2.7 Miscellaneous Desktop-Only
```
glPushAttrib / glPopAttrib
glPushClientAttrib / glPopClientAttrib
glLineStipple
glPolygonStipple
glEdgeFlag
glMap1 / glMap2 / glEvalCoord  // Evaluators
glFeedbackBuffer / glRenderMode(GL_FEEDBACK/SELECT)
glAccum
```

---

## 3. Texture Format Rules (GLES Strictness)

OpenGL ES requires **exact format-type pairing** in `glTexImage2D` / `glTexStorage2D`. Unlike desktop GL, you cannot pass arbitrary combinations.

### 3.1 Valid Sized Internal Formats (GLES 3.0+)
| Internal Format | Base Format | Type |
|:---|:---|:---|
| `GL_RGBA8` | `GL_RGBA` | `GL_UNSIGNED_BYTE` |
| `GL_SRGB8_ALPHA8` | `GL_RGBA` | `GL_UNSIGNED_BYTE` |
| `GL_RGB10_A2` | `GL_RGBA` | `GL_UNSIGNED_INT_2_10_10_10_REV` |
| `GL_RGBA16F` | `GL_RGBA` | `GL_HALF_FLOAT` |
| `GL_RGBA32F` | `GL_RGBA` | `GL_FLOAT` |
| `GL_R8` | `GL_RED` | `GL_UNSIGNED_BYTE` |
| `GL_RG8` | `GL_RG` | `GL_UNSIGNED_BYTE` |
| `GL_R16F` | `GL_RED` | `GL_HALF_FLOAT` |
| `GL_DEPTH_COMPONENT24` | `GL_DEPTH_COMPONENT` | `GL_UNSIGNED_INT` |
| `GL_DEPTH_COMPONENT32F` | `GL_DEPTH_COMPONENT` | `GL_FLOAT` |
| `GL_DEPTH24_STENCIL8` | `GL_DEPTH_STENCIL` | `GL_UNSIGNED_INT_24_8` |

### 3.2 Rules
- **SHOULD** use `glTexStorage2D` for fixed storage; it has a sized internal format and no external format/type arguments. Mutable allocation remains legal and useful for changing dimensions.
- **MUST** choose a combination from GLES 3.0 Tables 3.2–3.3 (pixel format/type combinations). `glTexImage2D(..., GL_RGBA8, ..., GL_RGBA, GL_UNSIGNED_BYTE, ...)` is legal in GLES 3.0. Only the unsized internal-format path requires matching internalformat/format. Integer storage requires integer external formats (for example `GL_RGBA8UI` / `GL_RGBA_INTEGER` / `GL_UNSIGNED_BYTE`). Allocation support does not imply filtering or framebuffer-renderability support.
- ETC2 (`GL_COMPRESSED_RGB8_ETC2`, `GL_COMPRESSED_RGBA8_ETC2_EAC`) is mandatory in GLES 3.0. ASTC is mandatory in GLES 3.2.

### 3.3 Offline Compression Asset Pipeline

Never decode PNG/JPEG at runtime for static textures — the CPU cost, memory
spike, and first-frame hitch are all avoidable. Compress offline and upload
GPU-ready blocks:

1. **Encode with `astcenc`** (ARM's official encoder). Pick the block size per
   texture role (see `mali-arm-best-practices.md` §4 / card 02 table); use
   `-thorough` quality for release builds, `-medium` for iteration. Encode
   normal maps with the `-normal` / uncorrelated flag to avoid channel crosstalk.
2. **Pack into KTX/KTX2 with `toktx`** (Khronos KTX-Software) using
   `--genmipmap` so the full mip chain ships with the asset; the runtime then
   needs no `glGenerateMipmap` at load time.
3. **Upload per-level** via `glCompressedTexImage2D` (or per-level
   `glCompressedTexSubImage2D` into a `glTexStorage2D` immutable texture whose
   `levels` count matches the packed chain). Stream large uploads through a
   PBO (`GL_PIXEL_UNPACK_BUFFER`) to avoid CPU→GPU stalls.
4. **KTX2 supercompression caveat**: zstd supercompression is safe to use
   (decode on CPU at load, then upload ASTC blocks). The basis_universal
   path requires a runtime transcoder library — in a pure-GLES codebase,
   prefer shipping native ASTC blocks + zstd over adding a transcoder.
5. Keep an ETC2 fallback in the asset pipeline for the rare pre-ASTC GLES 3.0
   devices; select at runtime via the ASTC extension check.

---

## 4. Buffer Object Rules

### 4.1 VAO Requirement (GLES 3.0+)
- **Always** use a VAO. The default VAO (name 0) is deprecated in GLES 3.0+.
- Bind VAO before setting vertex attribute pointers.

### 4.2 Buffer Usage Hints
| Hint | Use Case |
|:---|:---|
| `GL_STATIC_DRAW` | Geometry uploaded once, drawn many times |
| `GL_DYNAMIC_DRAW` | Updated every frame (e.g., particle positions) |
| `GL_STREAM_DRAW` | Updated and drawn once per frame |

### 4.3 Buffer Mapping (GLES 3.0+)
- Use `glMapBufferRange` with `GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT` for full-buffer updates (orphans old storage, avoids sync stalls).
- Use `GL_MAP_FLUSH_EXPLICIT_BIT` + `glFlushMappedBufferRange` for partial updates.
- **Never** hold a mapped pointer across frames without unmapping.

---

## 5. Framebuffer Object Rules

### 5.1 Completeness
- Always verify `glCheckFramebufferStatus() == GL_FRAMEBUFFER_COMPLETE` after FBO setup in debug builds.
- Common incompleteness causes: mismatched attachment dimensions, missing color attachment, unsupported format combinations.

### 5.2 Multiple Render Targets (GLES 3.0+)
- Query `GL_MAX_COLOR_ATTACHMENTS` (minimum 4 in GLES 3.0) and `GL_MAX_DRAW_BUFFERS` at runtime; treat 4 as a practical ceiling, not a floor.
- Enable with `glDrawBuffers(n, attachments)`; the array maps draw buffer *i* to `GL_COLOR_ATTACHMENTi` (or `GL_NONE` to leave a slot unwritten). Fragment shader outputs bind by index: `layout(location = 0) out vec4 outColor0;` — every declared `out` must have a matching enabled buffer or the draw errors.
- **All attachments in one MRT bind must share width, height, and sample count.** Mixed sizes or sample counts make the FBO incomplete. Formats may differ, but keep the set tight: each extra color attachment adds one tile store on TBDR GPUs (bandwidth = N × attachment writes), and per-attachment blending state adds driver cost. Drop any slot you do not actually write.
- Typical uses: deferred G-buffers (albedo/normal/depth+emission), SSAO inputs, velocity vectors for motion blur / TAA, OIT accumulation.
- **Encoding discipline** (from deferred-pipeline practice): normals are signed — remap `n * 0.5 + 0.5` on write, decode `* 2.0 - 1.0` on read; if depth must live in a color attachment, pack it across RGBA channels — one 8-bit channel (256 levels) is far too coarse to reconstruct world position. Prefer `RG16F`/octahedral normal packing or a real depth attachment when precision matters.
- G-buffer pack strategy: piggyback scalars into spare alpha channels (roughness into albedo alpha, metalness into normal alpha) before adding another attachment.
- **On Mali, prefer Pixel Local Storage over a DRAM G-buffer** when the intermediate data is consumed in the same render pass (`mali-arm-best-practices.md` §1); MRT G-buffers are the portable fallback — then `glInvalidateFramebuffer` every transient attachment at pass end.
- Transparencies are not handled by deferred pipelines: render transparent geometry in a separate forward pass after lighting.

### 5.3 Blit Framebuffer
- Use `glBlitFramebuffer` for resolve (MSAA → single-sample) or copy operations.
- On TBDR GPUs, blit may trigger a Tile resolve — prefer rendering directly to the target when possible.

---

## 6. Synchronization Rules

| Pattern | Recommendation |
|:---|:---|
| CPU needs GPU result | `glFenceSync` + `glClientWaitSync` (with timeout) |
| GPU waits on GPU (cross-queue) | `glWaitSync` (no CPU stall) |
| Full pipeline flush | `glFinish()` — **NEVER in render loop**, only for benchmarking |
| Buffer orphaning | `glBufferData(NULL)` or `GL_MAP_INVALIDATE_BUFFER_BIT` |
| Texture readback | PBO + `glReadPixels` to PBO, map next frame |

---

## 7. Extension Awareness

When using extensions, always:
1. Query availability via `glGetString(GL_EXTENSIONS)` or `glGetStringi(GL_EXTENSIONS, i)`.
2. Load function pointers via `eglGetProcAddress` or a loader (e.g., GLAD, GLEW for GLES).
3. Provide a fallback path if the extension is unavailable.

Key mobile extensions:
- `GL_EXT_shader_framebuffer_fetch` — Tile-local framebuffer read
- `GL_ARM_shader_framebuffer_fetch` — ARM Mali variant
- `GL_QCOM_tiled_rendering` — Qualcomm explicit tiling control
- `GL_EXT_multisampled_render_to_texture` — MSAA with implicit resolve
- `GL_OES_EGL_image_external` — Camera/video texture (Android)
- `GL_EXT_fragment_shading_rate` (family) — Variable Rate Shading (see `variable-rate-shading.md`)
- `GL_QCOM_shading_rate` — Adreno per-draw VRS
- `GL_KHR_debug` — Debug output callback

---

## 8. Feature Boundary — What OpenGL ES Does NOT Have

Never generate or suggest these features in GLES code; they do not exist in
the OpenGL ES specification on any version or vendor extension surface:

| Feature | Status in GLES | Correct answer |
|:---|:---|:---|
| **Ray tracing** (RT cores, acceleration structures) | **Not available** — mobile RT hardware (Adreno 7xx/8xx, Immortalis) is exposed via **Vulkan ray tracing extensions only**; there is no GLES RT extension | Redirect to Vulkan; in a GLES codebase use baked GI / probes / screen-space techniques |
| Mesh / task shaders | Not available (Vulkan `VK_EXT_mesh_shader` only) | Compute-shader culling + indirect draw (GLES 3.1+) |
| Bindless textures / descriptors | Not available | Bind texture units / sampler arrays; texture arrays for batching |
| Explicit subpasses (Vulkan-style) | No explicit API | Framebuffer fetch / PLS extensions (see `tbdr-bandwidth-rules.md`) |
| Geometry shader on GLES 3.0/3.1 | 3.2 only | Gate behind runtime version check |
| `glReadBuffer(GL_FRONT)` | Invalid GLES selector | Default FBO: `GL_BACK`/`GL_NONE`; named FBO: `GL_COLOR_ATTACHMENTi`/`GL_NONE` |

If a user's request implies one of these features, state the boundary explicitly
and propose the GLES-legal alternative instead of emitting fictional extensions.
