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
   a 3×3 hardware-filtered PCF before reaching for expensive kernels.
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

## Code pattern (depth texture + hardware compare)

```cpp
// Shadow FBO setup
glGenTextures(1, &shadowDepthTex);
glBindTexture(GL_TEXTURE_2D, shadowDepthTex);
glTexStorage2D(GL_TEXTURE_2D, 1, GL_DEPTH_COMPONENT24, 1024, 1024);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_COMPARE_REF_TO_TEXTURE);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_FUNC, GL_LEQUAL);

glBindFramebuffer(GL_FRAMEBUFFER, shadowFbo);
glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D,
                       shadowDepthTex, 0);
glDrawBuffer(GL_NONE);   // depth-only; no color on a depth-only FBO in GLES
glReadBuffer(GL_NONE);
```

```glsl
// Main pass: hardware-PCF shadow sample
#version 300 es
precision mediump float;
uniform highp sampler2DShadow u_ShadowMap;
uniform highp mat4 u_LightSpace;
in highp vec4 v_LightSpacePos;

mediump float ShadowFactor() {
    highp vec3 proj = v_LightSpacePos.xyz / v_LightSpacePos.w * 0.5 + 0.5;
    if (proj.z > 1.0) return 1.0;             // outside light frustum
    // 3x3 hardware-filtered PCF
    mediump float s = 0.0;
    float texel = 1.0 / 1024.0;
    for (int x = -1; x <= 1; ++x)
        for (int y = -1; y <= 1; ++y)
            s += texture(u_ShadowMap, vec3(proj.xy + vec2(x, y) * texel, proj.z));
    return s / 9.0;
}
```

## Common pitfalls

| Pitfall | Symptom | Fix |
|:---|:---|:---|
| No bias | Shadow acne (stripes) | constant + slope bias via `glPolygonOffset` |
| Too much bias | Peter-panning (shadow detached) | Reduce bias, tighten light frustum |
| Depth renderbuffer instead of texture | Cannot sample in main pass | Depth **texture** attachment |
| Sampling shadow map with `sampler2D` + manual compare | No hardware filtering, more taps | `sampler2DShadow` + compare mode |
| Forgetting `glDrawBuffer(GL_NONE)` on depth-only FBO | INVALID_OPERATION on some drivers | Set draw/read buffer to NONE |
| Shadow pass interleaved far from consumer | Extra FBO switch cost spread out | Order shadow pass adjacent to consumer |
