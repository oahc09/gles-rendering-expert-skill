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
**GLES Equivalent**: `GL_TRIANGLES`, `GL_TRIANGLE_STRIP`, `GL_TRIANGLE_FAN` only. For wireframe, use barycentric coordinate technique in shader or geometry shader (GLES 3.2).

### 2.6 Draw Buffer / Read Buffer
```
glDrawBuffer(GL_BACK) / glReadBuffer(GL_FRONT)  // Desktop single-buffer selection
```
**GLES Equivalent**: `glDrawBuffers(n, bufs)` for MRT (GLES 3.0+). Default read buffer is implementation-defined for default FBO; use `glReadBuffer` only on GLES 3.0+ named FBOs.

### 2.7 Miscellaneous Desktop-Only
```
glPushAttrib / glPopAttrib
glPushClientAttrib / glPopClientAttrib
glLineWidth(width > 1.0)  // GLES guarantees only 1.0
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
- **Always** use `glTexStorage2D` (immutable) over `glTexImage2D` (mutable) when mipmap levels are known upfront — better driver optimization.
- For `glTexImage2D`, the `internalformat` parameter in GLES must match the `format` parameter (e.g., `GL_RGBA`, not `GL_RGBA8` for GLES 2.0 compat; for 3.0+, sized formats are allowed in `glTexStorage2D`).
- ETC2 (`GL_COMPRESSED_RGB8_ETC2`, `GL_COMPRESSED_RGBA8_ETC2_EAC`) is mandatory in GLES 3.0. ASTC is mandatory in GLES 3.2.

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
- Query `GL_MAX_COLOR_ATTACHMENTS` (minimum 4 in GLES 3.0).
- Use `glDrawBuffers(n, attachments)` to enable MRT.
- Fragment shader outputs: `layout(location = 0) out vec4 outColor0;`

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
- `GL_KHR_debug` — Debug output callback
