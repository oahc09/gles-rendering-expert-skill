# Depth-Based Screen-Space Effects on TBDR (SSAO / Soft Particles / Motion Blur)

> Effects that read geometry depth in a later pass — ambient occlusion, soft
> particle fade, motion blur, DOF, screen-space reflections. On mobile the
> shader math is the easy part; the hard part is **who stores the depth, in
> what format, and how many times it crosses DRAM**.

---

## 1. Rules

1. **Never sample the depth attachment of the framebuffer you are currently
   rendering into** — texture-FBO feedback loops are undefined behavior on
   GLES (silently device-dependent). Either render the effect into a different
   FBO that holds the depth texture as a *non-attached* input, or bind the
   pass to the default/back buffer while reading the offscreen depth.
2. **The TBDR cost model for depth reuse**: opaque pass storing depth as
   `GL_DEPTH_COMPONENT24` = 4 B/px DRAM store, then the effect pass loads it
   = 4 B/px read. Halve it: write **linear view depth packed into a color
   attachment** (`GL_R16F` or `GL_RG16F` with the extra channel for AO) at the
   tail of the opaque fragment shader — 2 B/px store + 2 B/px read, no
   fixed-function depth encoding, and `mediump`-safe reconstruction. Keep the
   real depth attachment as `GL_DEPTH_STENCIL` only if a later pass needs
   hardware tests — then invalidate it (`glInvalidateFramebuffer`) once the
   effect pass consumed its substitute.
3. **Window Z is non-linear — linearize on read, never average raw Z**:
   `viewZ = (2*n*f) / (f + n - z_ndc*(f - n))` with `z_ndc = 2*depth - 1`, or
   precompute the two-constant form. Do the reconstruction in `highp` —
   `mediump` fails past ~10 m with banding/popping (see glsl-es-optimization
   precision rules).
4. **Run SSAO at half or quarter resolution** (1/2 linear, 1/4 for cost
   budget), reconstruct normals from depth derivatives (`dFdx/dFdy` of
   linearized Z — guard the zero-derivative case at geometry silhouettes),
   then **bilateral-upsample** (weight by both distance and depth difference)
   so AO never bleeds across edges. A 1× SSAO kernel with full-res bilateral
   blur is the classic mobile perf trap.
5. **No noise texture for hemisphere sampling — hash it**: a
   `vec3 hash33(gl_FragCoord)`-style random rotation costs ~10 ALU ops; the
   RG8 rotation-texture fetch is not worth the sampler slot on tile GPUs.
   Keep samples 4–8; temporal accumulation (TAASSO) only if the engine
   already has a motion-vector + jitter story.
6. **Soft particles need view-space depth difference, not raw-Z difference**:
   `fade = clamp((zParticleView - zBufferView) / softnessRange, 0, 1)`.
   Comparing window Z (rule 3) produces hard seams far from the camera because
   raw Z precision concentrates near the far plane. Particle FS samples the
   linear-depth texture from rule 2 — meaning the opaque depth was produced
   one pass earlier (never the live attachment, rule 1).
7. **Motion blur needs a velocity signal**: per-object = store the previous
   `viewProj`, compute screen-space delta in the opaque FS into an `RG16F`
   velocity attachment (or pack to RGBA8 at 1/4 the precision budget);
   camera-only blur skips the buffer entirely (reproject with the inverse
   view-proj delta). Blur with 4–8 texel steps along the vector; normalize
   and reject zero-velocity pixels **before** sampling or you pay texture taps
   on background pixels for nothing.
8. **MSAA interaction**: a multisampled depth attachment cannot be sampled
   directly — resolve once (on-tile via
   `GL_EXT_multisampled_render_to_texture` keeps it in GMEM) or drive the
   effect from the non-MSAA linear-depth color attachment (rule 2 — another
   reason it wins on mobile).
9. **Blend discipline on TBDR**: every alpha-blended effect pass forces tiles
   to stay resident with their prior color; long blended chains (AO multiply +
   particles + blur) are best fused into **one** composited pass reading
   several small attachments, not a chain of fullscreen blits — each blit is
   a full store+load round-trip.
10. **Precision format table**: linear depth `R16F` (≤65 m with a scale
    factor), velocity `RG16F` (sub-pixel jitter needs float range), AO result
    `R8` (it's a scalar), normals-from-depth needs none — derive in-shader.
    All are filterable in GLES 3.0 core (half-float linear is core);
    `GL_R32F` filtering needs `OES_texture_float_linear` — avoid it.

## 2. Code pattern (linear-depth side-write + soft-particle read)

```glsl
// end of the OPAQUE fragment shader — one extra 2-byte store, no depth read
layout(location = 2) out mediump vec2 outLinearDepth;  // R16F attachment
// ...
highp float viewZ = -(u_View * vec4(v_WorldPos, 1.0)).z;   // highp (rule 3)
outLinearDepth = vec2(viewZ * u_DepthScale, 0.0);           // scale <= 1/65 for R16F
```

```glsl
// particle.frag — GLSL ES 3.00, soft fade against the linear-depth texture
#version 300 es
precision mediump float;
precision highp sampler2D;
uniform sampler2D u_LinearDepth;   // R16F, NEAREST (it is data, not color)
uniform sampler2D u_Albedo;
uniform mediump float u_Softness;  // 1 / range, in view-distance units
in mediump vec2 v_Uv;              // quad UV, interpolated (from VS)
in highp float v_ViewDist;         // particle view-space distance (from VS)
in vec4 v_Color;
out vec4 fragColor;

void main() {
    highp vec2 uv = gl_FragCoord.xy * u_InvResolution;
    highp float sceneDist = texture(u_LinearDepth, uv).r * u_DepthInvScale;
    mediump float fade = clamp((sceneDist - v_ViewDist) * u_Softness, 0.0, 1.0);
    if (fade <= 0.001) discard;    // scene surface in front of particle: exit early
    fragColor = vec4(texture(u_Albedo, v_Uv).rgb * v_Color.rgb, v_Color.a * fade);
}
```

## 3. Common pitfalls

| Pitfall | Symptom | Fix |
|:---|:---|:---|
| Sampling the bound depth attachment of the current FBO | Random black texels / driver-dependent | Rule 1 — separate FBOs or the rule-2 color-depth copy |
| Averaging raw window Z across the kernel | Far-plane AO bleeding into near field | Linearize first (rule 3) |
| `mediump` depth reconstruction | Banding/popping past ~10 m | Highp for Z math, mediump for AO output only |
| Full-res SSAO + full-res blur | 2x framebuffer traffic twice | 1/2–1/4 res + bilateral upsample (rule 4) |
| Soft particles comparing window Z | Hard seams on distant geometry | View-space difference (rule 6) |
| Velocity buffer taps on still pixels | Paying blur cost for the whole screen | Zero-velocity early-reject (rule 7) |
| Sampling MSAA depth directly | `INVALID_OPERATION` / garbage | Resolve or color-attachment depth (rule 8) |
| Chained fullscreen blends | Store+load per link in the chain | Fuse composite passes (rule 9) |

## 4. Cross-references

- Card 08 / `tbdr-bandwidth-rules.md` — store/load model behind rule 2
- `references/rules/glsl-es-optimization.md` — precision + derivative guards
- Card 10 + `adreno/efficient-msaa.md` — on-tile resolve for rule 8
- `references/rules/post-processing-chain.md` — where these passes sit in the frame
- `references/rules/shadow-mapping-mobile.md` — same depth-texture read mechanics
