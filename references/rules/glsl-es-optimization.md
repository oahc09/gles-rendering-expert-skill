# GLSL ES Precision Control & Shader Optimization Rules

## 1. Version & Precision Declaration (Mandatory)

### 1.1 Version Directive
Every GLSL ES shader **MUST** begin with a version directive on the very first line:

```glsl
#version 300 es   // For OpenGL ES 3.0 (GLSL ES 3.00)
#version 320 es   // For OpenGL ES 3.2 (GLSL ES 3.20)
```

- No blank lines or comments before `#version`.
- Use `300 es` as default; use `320 es` only when geometry/tessellation shaders or advanced features are needed.

### 1.2 Precision Qualifiers

| Shader Stage | Requirement |
|:---|:---|
| Vertex | `highp` is default for float. No explicit declaration needed but recommended. |
| Fragment | **MUST** declare: `precision mediump float;` (minimum). No default exists. |
| Compute (3.1+) | `highp` is default. Declare if using lower precision. |

### 1.3 Precision Selection Guide

| Data Type | Recommended Precision | Rationale |
|:---|:---|:---|
| Vertex positions (`gl_Position`) | `highp` | Avoid jitter at large world coordinates |
| Depth values | `highp` | Prevent Z-fighting |
| Texture coordinates | `mediump` | Sufficient for 0-1 UV range; saves ALU on Mali |
| Color values (RGB/RGBA) | `mediump` or `lowp` | 8-bit output doesn't need 32-bit math |
| Normal vectors | `mediump` | Upgrade to `highp` only if banding visible |
| Light direction / position | `mediump` | Usually normalized, range [-1,1] |
| Time / animation accumulators | `highp` | Large values accumulate precision errors |
| Matrix multiplications (MVP) | `highp` | Compound error in 4×4 multiply |

### 1.4 Precision Syntax

```glsl
#version 300 es
precision highp float;      // Vertex shader default (implicit but explicit is good)
precision highp int;

// Per-variable override
uniform highp mat4 u_MVP;
uniform mediump vec3 u_LightDir;
in mediump vec2 v_TexCoord;
out mediump vec4 fragColor;
```

---

## 2. Shader Input/Output Layout

### 2.1 Vertex Shader

```glsl
#version 300 es
precision highp float;

// Explicit location bindings — mandatory for maintainability
layout(location = 0) in vec3 a_Position;
layout(location = 1) in vec3 a_Normal;
layout(location = 2) in vec2 a_TexCoord;

// UBO for matrices (16-byte aligned)
layout(std140) uniform Matrices {
    highp mat4 u_Model;
    highp mat4 u_View;
    highp mat4 u_Projection;
    highp mat3 u_NormalMatrix;
};

out mediump vec3 v_WorldNormal;
out mediump vec2 v_TexCoord;
out highp vec3 v_WorldPos;

void main() {
    highp vec4 worldPos = u_Model * vec4(a_Position, 1.0);
    v_WorldPos = worldPos.xyz;
    v_WorldNormal = normalize(u_NormalMatrix * a_Normal);
    v_TexCoord = a_TexCoord;
    gl_Position = u_Projection * u_View * worldPos;
}
```

### 2.2 Fragment Shader

```glsl
#version 300 es
precision mediump float;
precision highp int;

layout(location = 0) out vec4 outColor;

in mediump vec3 v_WorldNormal;
in mediump vec2 v_TexCoord;
in highp vec3 v_WorldPos;

uniform mediump vec3 u_CameraPos;
// ...
```

### 2.3 Rules
- **Always** use `layout(location = N)` for attributes and fragment outputs.
- **Never** rely on `glGetAttribLocation` for attribute binding in production code.
- Use `in`/`out` keywords (GLES 3.0+); never `attribute`/`varying` (GLES 2.0 legacy).
- **Varying precision MUST match between vertex and fragment shader.** The precision
  qualifier on a vertex shader `out` variable must be identical to the fragment
  shader's corresponding `in` variable. ANGLE silently zeros mismatched varyings
  (no compile/link error) — this manifests as black surfaces or missing lighting
  that is extremely hard to diagnose.

  ```glsl
  // ✅ Vertex: out mediump vec3 v_Normal;
  // ✅ Fragment: in mediump vec3 v_Normal;  ← same precision

  // ❌ Vertex: out highp vec3 v_Normal;
  // ❌ Fragment: in mediump vec3 v_Normal;  ← ANGLE zeros this!
  ```

---

## 3. Uniform Buffer Objects (UBO)

### 3.1 std140 Layout Rules

```glsl
layout(std140) uniform LightBlock {
    vec4 position;      // offset 0,  size 16
    vec4 color;         // offset 16, size 16
    float intensity;    // offset 32, size 4
    float radius;       // offset 36, size 4
    // 8 bytes padding to align next member to 16
    vec4 direction;     // offset 48, size 16
};
```

**Alignment rules (std140)**:
- `float`: 4-byte aligned
- `vec2`: 8-byte aligned
- `vec3` / `vec4`: 16-byte aligned
- `mat4`: treated as 4 × `vec4`, each 16-byte aligned
- Arrays: each element rounded up to `vec4` size (16 bytes)

### 3.2 UBO Best Practices
- Group frequently-changing uniforms (per-frame: matrices, time) in one UBO.
- Group rarely-changing uniforms (per-material: colors, roughness) in another.
- Bind UBOs to explicit binding points: `layout(binding = 0) uniform Matrices { ... };`
- Update with `glBufferSubData` or `glMapBufferRange` — avoid `glBufferData` every frame (reallocates).

---

## 4. Fragment Shader Optimization

### 4.1 Avoid Dynamic Branching

```glsl
// ❌ BAD: Divergent branch causes both paths to execute on GPU (SIMD)
if (v_TexCoord.x > 0.5) {
    color = texture(u_TexA, v_TexCoord);
} else {
    color = texture(u_TexB, v_TexCoord);
}

// ✅ GOOD: Branchless selection
mediump float selector = step(0.5, v_TexCoord.x);
mediump vec4 texA = texture(u_TexA, v_TexCoord);
mediump vec4 texB = texture(u_TexB, v_TexCoord);
color = mix(texB, texA, selector);
```

**Exception**: Uniform branches (same for all fragments in a warp/wavefront) are fine:
```glsl
// ✅ OK: Uniform branch — all fragments take same path
if (u_UseNormalMap) {
    normal = texture(u_NormalMap, v_TexCoord).xyz * 2.0 - 1.0;
}
```

### 4.2 Minimize Texture Fetches

```glsl
// ❌ BAD: Fetching in a loop with dynamic index
for (int i = 0; i < u_LightCount; i++) {
    color += texture(u_ShadowMaps[i], shadowCoord[i]);  // Dynamic indexing!
}

// ✅ GOOD: Fixed iteration with constant bounds
const int MAX_LIGHTS = 4;
for (int i = 0; i < MAX_LIGHTS; i++) {
    if (i >= u_LightCount) break;  // Uniform break — OK
    color += CalculateLight(i);
}
```

### 4.3 Use Built-in Functions

```glsl
// ❌ Manual implementation
float result = clamp(dot(N, L), 0.0, 1.0);
float edge = (x < a) ? 0.0 : (x > b) ? 1.0 : (x - a) / (b - a);

// ✅ Use optimized built-ins
float result = max(dot(N, L), 0.0);  // saturate pattern
float edge = smoothstep(a, b, x);    // Hardware-optimized on most GPUs
```

### 4.4 Precompute & Pass via Varying
- Move expensive per-fragment calculations to vertex shader when possible (per-vertex lighting for non-critical lights).
- Pass precomputed values via `out`/`in` varyings (interpolated for free by hardware).

---

## 5. Compute Shader Rules (GLES 3.1+)

### 5.1 Structure

```glsl
#version 310 es
layout(local_size_x = 64, local_size_y = 1, local_size_z = 1) in;

layout(std430, binding = 0) buffer ParticleBuffer {
    Particle particles[];
};

uniform uint u_ParticleCount;
uniform float u_DeltaTime;

void main() {
    uint idx = gl_GlobalInvocationID.x;
    if (idx >= u_ParticleCount) return;
    
    // Update particle...
    particles[idx].position += particles[idx].velocity * u_DeltaTime;
}
```

### 5.2 Compute Best Practices
- Choose `local_size` as multiples of warp/wavefront size (32 for Adreno, 16 for Mali).
- Use `shared` memory for workgroup-local data reuse (guaranteed ≥ 16 KiB;
  uninitialized and non-persistent). It can collapse a bandwidth-heavy multi-pass
  fragment algorithm into a single compute pass that keeps intermediates on-chip.
- Avoid excessive SSBO reads/writes — batch data access patterns for coalescing.

### 5.3 SSBO Data Layout — Prefer std430
- Use **`layout(std430)` for SSBOs**, not `std140`. `std140` pads scalar array
  elements to `vec4` (4× memory waste); `std430` packs them tightly. `std430` is
  SSBO-only. SSBOs must guarantee ≥ 128 MiB (vs. 16 KiB UBOs) and allow an
  **unsized trailing array** (`float data[];`, query with `.length()`).
- Bind with `glBindBufferBase(GL_SHADER_STORAGE_BUFFER, binding, buffer)` and
  match `layout(std430, binding = N)`.

### 5.4 Shader Images from Compute
- Bind with `glBindImageTexture(unit, tex, level, layered, layer, access, format)`;
  declare `layout(FORMAT, binding = UNIT) uniform image2D img;`.
- The shader **format qualifier must match** the `glBindImageTexture` format arg.
- **Never** bind image units with `glUniform1i` — use `layout(binding = UNIT)`.
- Textures used as images **must be immutable** (`glTexStorage*`, never
  `glTexImage2D`). Use `imageLoad` / `imageStore` / `imageSize`.

### 5.5 Synchronization — Correctness Rules (Critical)
Compute memory is **weakly ordered**; cross-thread ordering is NOT guaranteed.
- **Within a work group**, to share data you MUST pair a memory barrier with an
  execution barrier, and issue the memory barrier **first**:
  ```glsl
  memoryBarrierShared(); // flush shared writes so peers can see them
  barrier();             // wait until every thread reaches this point
  ```
  Do NOT assume `barrier()` alone synchronizes `shared` memory — the spec does
  not guarantee it. Only call `barrier()` in **dynamically-uniform** control flow
  (e.g. branch on a uniform); a divergent `barrier()` deadlocks.
- **Across GL commands**, compute writes to SSBOs/images/atomics are NOT auto-
  synchronized (unlike render-to-texture, which the driver handles). Call
  `glMemoryBarrier(<BITS>)` describing how the data is *read next*. Example:
  compute writes a buffer, then it is drawn as a VBO:
  ```cpp
  glDispatchCompute(groups, 1, 1);              // write SSBO
  glMemoryBarrier(GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT); // sync for VBO read
  glDrawElements(GL_TRIANGLES, ...);            // read as vertex data
  ```

### 5.6 Tile-Friendly Fragment Compute (TBDR)
- Prefer **`glMemoryBarrierByRegion()`** over `glMemoryBarrier()` for fragment
  image load/store when consumers only read data written for the *same* pixel.
  A full `glMemoryBarrier()` forces the whole tile buffer to flush to DRAM;
  the by-region variant only orders within a framebuffer region (as small as one
  pixel), avoiding that flush.
- Add **`layout(early_fragment_tests) in;`** to a fragment shader that writes to
  images/SSBOs/atomics but does not modify `gl_FragDepth`. Side effects normally
  disable early-Z; this restores it and reclaims overdraw rejection.

### 5.7 Multiview in Shaders (VR / stereo, GL_OVR_multiview)
- Single-pass stereo: render to array-texture layers via
  `layout(num_views = N) in;` and index per-view data with `gl_ViewID_OVR`.
  `num_views` must equal the FBO layer count.
- Use **`GL_OVR_multiview2`** when anything besides `gl_Position` depends on the
  view (view-dependent lighting/specular). Multiview cannot be combined with
  geometry or tessellation shaders. See `mali-arm-best-practices.md` §2.

---

## 6. Shader Compilation & Linking

### 6.1 Error Handling Pattern

```cpp
GLuint CompileShader(GLenum type, const char* source) {
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);
    
    GLint compiled = 0;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &compiled);
    if (!compiled) {
        GLint logLen = 0;
        glGetShaderiv(shader, GL_INFO_LOG_LENGTH, &logLen);
        std::string log(logLen, '\0');
        glGetShaderInfoLog(shader, logLen, nullptr, log.data());
        LOGE("Shader compile error: %s", log.c_str());
        glDeleteShader(shader);
        return 0;
    }
    return shader;
}

GLuint LinkProgram(GLuint vert, GLuint frag) {
    GLuint program = glCreateProgram();
    glAttachShader(program, vert);
    glAttachShader(program, frag);
    glLinkProgram(program);
    
    GLint linked = 0;
    glGetProgramiv(program, GL_LINK_STATUS, &linked);
    if (!linked) {
        GLint logLen = 0;
        glGetProgramiv(program, GL_INFO_LOG_LENGTH, &logLen);
        std::string log(logLen, '\0');
        glGetProgramInfoLog(program, logLen, nullptr, log.data());
        LOGE("Program link error: %s", log.data());
        glDeleteProgram(program);
        return 0;
    }
    // Shaders can be detached & deleted after successful link
    glDetachShader(program, vert);
    glDetachShader(program, frag);
    glDeleteShader(vert);
    glDeleteShader(frag);
    return program;
}
```

### 6.2 Program Pipeline (GLES 3.1+ Separate Shader Objects)
```cpp
// Enable separable programs
glProgramParameteri(program, GL_PROGRAM_SEPARABLE, GL_TRUE);

// Use program pipeline for independent vertex/fragment updates
GLuint pipeline;
glGenProgramPipelines(1, &pipeline);
glUseProgramStages(pipeline, GL_VERTEX_SHADER_BIT, vertProgram);
glUseProgramStages(pipeline, GL_FRAGMENT_SHADER_BIT, fragProgram);
glBindProgramPipeline(pipeline);
```

---

## 7. Precision-Related Pitfalls

| Issue | Cause | Fix |
|:---|:---|:---|
| Vertex jitter at large coordinates | `mediump` position in vertex shader | Use `highp` for all position math |
| Texture coordinate seams | `mediump` UV on large textures (4096+) | Upgrade to `highp` for UVs on large textures |
| Z-fighting | `mediump` depth or near/far too close | Use `highp` depth; adjust near/far ratio |
| Color banding in gradients | `lowp` color interpolation | Use `mediump` for gradient colors |
| Normal map artifacts | `mediump` normal after multiple transforms | Use `highp` for normal matrix multiplication |
| Time-based animation stutter | `mediump` time uniform overflows | Use `highp` for time; wrap with `mod()` |
| Black surfaces / missing lighting | Varying precision mismatch (VS `out highp` ≠ FS `in mediump`) | Ensure identical precision on all `out`/`in` pairs |

---

## 7.5 Numerical Stability (Critical for Mobile mediump)

Mobile GPUs typically implement `mediump` as FP16 (range ±65504, ~3.3 decimal digits).
Built-in functions that divide or normalize can produce NaN/Inf on degenerate input.

### 7.5.1 Rules

- **Guard `normalize()` / `inversesqrt()` against zero-length input.**
  `normalize(vec3(0))` is undefined (division by zero). Always clamp:
  ```glsl
  mediump vec3 safeNormalize(mediump vec3 v) {
      mediump float len2 = dot(v, v);
      return (len2 > 1e-8) ? v * inversesqrt(len2) : vec3(0.0, 0.0, 1.0);
  }
  ```

- **Guard `pow(x, y)` where x may be zero or negative.**
  `pow(0.0, 0.0)` is undefined in GLSL ES. Use `max(x, epsilon)` as base:
  ```glsl
  mediump float specular = pow(max(NdotH, 1e-4), shininess);
  ```

- **Screen-space derivatives `dFdx()`/`dFdy()` can be zero on triangle edges.**
  When used for bump mapping, LOD selection, or anti-aliasing, always provide a
  fallback when the derivative magnitude is near zero:
  ```glsl
  mediump vec2 dx = dFdx(v_TexCoord);
  mediump vec2 dy = dFdy(v_TexCoord);
  mediump float derivLen = max(dot(dx, dx) + dot(dy, dy), 1e-8);
  // Use derivLen for LOD bias or mip selection
  ```

- **Avoid subtracting nearly-equal values in mediump.**
  `a - b` where `a ≈ b` loses all precision in FP16. Restructure the math
  (e.g., use `fma()` or factor the expression) or promote to `highp` locally.

- **`atan(y, x)` is undefined when both arguments are zero.**
  Wrap: `atan(y, x + 1e-8)` or guard with a zero check.

---

## 8. GLSL ES vs Desktop GLSL Quick Reference

| Feature | GLSL ES 3.00 | Desktop GLSL 4.x |
|:---|:---|:---|
| Precision qualifiers | **Required** in fragment | Optional (ignored) |
| `#version` | `300 es` / `320 es` | `330` / `430` / `460` |
| Default float precision (frag) | **None** — must declare | `highp` |
| `gl_FragColor` | Removed — use `out` variable | Removed in 330+ too |
| `texture2D()` | Removed — use `texture()` | Same |
| Geometry shader | GLES 3.2 only | 150+ |
| Tessellation | GLES 3.2 only | 400+ |
| Compute shader | GLES 3.1+ (`#version 310 es`) | 430+ |
| `layout(binding=N)` for UBO | GLES 3.0+ | 420+ |
| SSBO | GLES 3.1+ | 430+ |
| `#extension` directive | Required for vendor extensions | Same pattern |
