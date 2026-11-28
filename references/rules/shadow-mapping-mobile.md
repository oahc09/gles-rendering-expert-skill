# Shadow Mapping on Mobile GPUs

> Distilled from LearnOpenGL's shadow-mapping chapters, adapted for TBDR mobile
> GPUs. Shadow mapping is the standard real-time shadow technique in GLES; the
> mobile adaptations below are what separate a working demo from a production
> pipeline.

---

## 1. Pipeline shape

```
Pass 1 (shadow pass):  render depth-only from the light into a depth texture
Pass 2 (main pass):    sample the depth texture, compare, apply shadow factor
```

## 2. Rules

1. **Depth-only FBO for the shadow pass**: attach a depth texture (not a
   renderbuffer — you must sample it later) with `GL_DEPTH_COMPONENT24`; attach
   no color. On GLES 3.0+ you can sample a depth texture directly with a
   `sampler2D` (or use `sampler2DShadow` with `GL_TEXTURE_COMPARE_MODE =
   GL_COMPARE_REF_TO_TEXTURE` for hardware PCF).
2. **Clear the depth-only target at pass start and invalidate nothing** — the
   depth texture IS the output, so it must be stored. No color attachment means
   the store is small.
3. **Shadow map resolution is a bandwidth trade-off**: 1024² is a good mobile
   default; 2048² only for hero lights. Each cascaded map multiplies the pass
   cost. Prefer **fewer, well-placed cascades** (2–3) over many.
4. **Bias everywhere**: constant + slope-scaled bias (`glPolygonOffset(1.0,
   constant)` or shader-side) prevents shadow acne; too much bias causes
   peter-panning. Tune per light, never reuse one magic number.
5. **PCF via `sampler2DShadow` + `GL_COMPARE_REF_TO_TEXTURE`** uses hardware
   filtering — cheaper than manual multi-tap PCF. For soft shadows start with
   a small kernel. The baseline below uses nearest hardware comparisons per tap
   so the frustum edge remains explicit; use linear hardware PCF only with a
   verified interior footprint or an appropriate lit border.
6. **Tight light projection**: fit the light ortho matrix to the visible
   receiver range; a tight frustum raises effective shadow-map resolution.
7. **Cull shadow casters**: only casters render into the shadow pass; skip
   receivers-only and off-frustum objects.
8. **Do not render transparent objects into the shadow pass** (or use an
   alpha-tested variant if alpha-tested shadows are needed — remember `discard`
   disables early-Z/LRZ for that draw).
9. **Mobile-specific**: depth texture sampling from a different render pass is
   a texture fetch like any other — keep shadow sampling taps low, and remember
   the shadow pass itself is a full FBO switch (Store + Load); order it adjacent
   to the pass that consumes it where possible.

## GLES 3.0+ baseline (depth texture + nearest hardware compare)

```cpp
// Shadow FBO setup
glGenTextures(1, &shadowDepthTex);
glBindTexture(GL_TEXTURE_2D, shadowDepthTex);
glTexStorage2D(GL_TEXTURE_2D, 1, GL_DEPTH_COMPONENT24, 1024, 1024);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_COMPARE_REF_TO_TEXTURE);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_FUNC, GL_LEQUAL);

glBindFramebuffer(GL_FRAMEBUFFER, shadowFbo);
glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D,
                       shadowDepthTex, 0);
const GLenum noColor = GL_NONE;
glDrawBuffers(1, &noColor);   // depth-only; no color on a depth-only FBO in GLES
glReadBuffer(GL_NONE);
```

```glsl
// Main pass: hardware-PCF shadow sample
#version 300 es
precision mediump float;
uniform highp sampler2DShadow u_ShadowMap;
in highp vec4 v_LightSpacePos;

// Returns visibility: 1.0 is lit. The map uses conventional (not reversed) Z.
mediump float ShadowFactor() {
    if (v_LightSpacePos.w <= 0.0) return 1.0;
    highp vec3 proj = v_LightSpacePos.xyz / v_LightSpacePos.w * 0.5 + 0.5;
    if (proj.z < 0.0 || proj.z > 1.0 ||
        any(lessThan(proj.xy, vec2(0.0))) || any(greaterThanEqual(proj.xy, vec2(1.0))))
        return 1.0;

    highp ivec2 size = textureSize(u_ShadowMap, 0);
    highp ivec2 center = ivec2(floor(proj.xy * vec2(size)));
    mediump float visibility = 0.0;
    for (int y = -1; y <= 1; ++y) {
        for (int x = -1; x <= 1; ++x) {
            highp ivec2 tap = center + ivec2(x, y);
            if (any(lessThan(tap, ivec2(0))) || any(greaterThanEqual(tap, size))) {
                visibility += 1.0;
            } else {
                highp vec2 uv = (vec2(tap) + 0.5) / vec2(size);
                visibility += texture(u_ShadowMap, vec3(uv, proj.z));
            }
        }
    }
    return visibility / 9.0;
}
```

### Optional border clamp (separate capability path)

For a bound depth texture, GLES 3.2 core permits a lit border with depth 1
under the baseline's `GL_LEQUAL` compare and reference range [0,1]. The base
path above works unchanged if the branch is unavailable. Reverse-Z uses its
own compare convention and border depth (typically 0 with `GL_GEQUAL`).
A GLES 3.0/3.1 runtime can only use the extension form after checking the
advertised extension and its matching suffixed enums/functions; a header
declaration alone does not establish runtime support.

```cpp
bool TryConfigureShadowBorder(GLint esMajor, GLint esMinor) {
#if defined(GL_ES_VERSION_3_2)
    if (esMajor > 3 || (esMajor == 3 && esMinor >= 2)) {
        const GLfloat litBorder[4] = {1.0f, 1.0f, 1.0f, 1.0f};
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER);
        glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, litBorder);
        return true;
    }
#endif
    (void)esMajor;
    (void)esMinor;
    return false;
}
```

## Common pitfalls

| Pitfall | Symptom | Fix |
|:---|:---|:---|
| No bias | Shadow acne (stripes) | constant + slope bias via `glPolygonOffset` |
| Too much bias | Peter-panning (shadow detached) | Reduce bias, tighten light frustum |
| Depth renderbuffer instead of texture | Cannot sample in main pass | Depth **texture** attachment |
| Sampling shadow map with `sampler2D` + manual compare | No hardware filtering, more taps | `sampler2DShadow` + compare mode |
| Forgetting `glDrawBuffers(1, &noColor)` (with `noColor = GL_NONE`) on depth-only FBO | INVALID_OPERATION on some drivers | Set draw/read buffer to NONE |
| Shadow pass interleaved far from consumer | Extra FBO switch cost spread out | Order shadow pass adjacent to consumer |
