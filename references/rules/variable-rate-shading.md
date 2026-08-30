# Variable Rate Shading (VRS)

> Sources:
> - MediaTek Dimensity Developer Center — "VRS GLES API 介绍"
>   (https://developer.mediatek.com/VariableRateShading/6554775458a7392014e51c52.html)
> - Qualcomm — "Variable Rate Shading has arrived on mobile"
>   (https://www.qualcomm.com/news/onq/2021/07/variable-rate-shading-has-arrived-mobile-impressive-results)
> - Adreno per-draw path: `references/rules/adreno/*.md`, card 14

VRS lets the GPU shade **groups of pixels with one fragment-shader invocation**
(e.g. one invocation per 2x2 pixel footprint), cutting fragment ALU and texture
work in low-detail regions. It reduces **shading cost only** — it does NOT
reduce framebuffer bandwidth (tile stores, blending, and depth still happen at
full rate). Pair it with the usual TBDR bandwidth rules, not instead of them.

---

## 1. Two Extension Surfaces

| Surface | Where | Shape |
|:---|:---|:---|
| `GL_QCOM_shading_rate` | Adreno (Snapdragon Elite Gaming generation onward) | Simple **per-draw** rate: `glShadingRateQCOM(GL_SHADING_RATE_2X2_PIXELS_QCOM)`. No `glEnable` needed; call directly after runtime extension check. |
| `GL_EXT_fragment_shading_rate` family | Cross-vendor full programming model (documented by MediaTek for Dimensity/Mali-class hardware) | Three rate sources + combiners: **pipeline**, **per-primitive**, and **attachment** rates. |

Always select the path by **runtime extension query** (`glGetString(GL_EXTENSIONS)`),
never by device model string.

### `GL_EXT_fragment_shading_rate` sub-extensions

- `GL_EXT_fragment_shading_rate` — base extension, **pipeline VRS**.
- `GL_EXT_fragment_shading_rate_primitive` — optional, **per-primitive VRS**.
- `GL_EXT_fragment_shading_rate_attachment` — optional, **framebuffer-attachment VRS**.

**Incompatibility (from the MediaTek docs):** the VRS extension must not be
combined with `GL_EXT_shader_pixel_local_storage`,
`GL_EXT_shader_framebuffer_fetch`, or `GL_ARM_shader_framebuffer_fetch` in the
same render pass. Choose PLS/framebuffer-fetch OR VRS per pass.

---

## 2. Query Supported Shading Rates

The set of legal rates depends on the MSAA sample count. Query it — twice
(count, then array):

```cpp
GLsizei count = 0;
glGetFragmentShadingRatesEXT(samples, 0, &count, nullptr);
std::vector<GLenum> rates(count);
glGetFragmentShadingRatesEXT(samples, count, &count, rates.data());
// entries are GL_SHADING_RATE_*_PIXELS_EXT (1x1 .. 4x4)
```

Rules:

- **Query per sample count.** E.g. a GPU may allow up to 4x4 at 1 sample but
  only up to 2x2 at 4x MSAA. Combining MSAA + VRS without querying is a bug source.
- If you request an unsupported rate, hardware **silently rounds** to the nearest
  supported rate — never assume the rate you set is the rate you get (verify via
  `gl_ShadingRateEXT`, §6).

---

## 3. Pipeline Rate (per-draw)

```cpp
glShadingRateEXT(GL_SHADING_RATE_2X2_PIXELS_EXT);  // applies to subsequent draws
drawBackground();
glShadingRateEXT(GL_SHADING_RATE_1X1_PIXELS_EXT);  // restore full rate
drawHero();
```

- Rate enums: `GL_SHADING_RATE_{1X1,1X2,1X4,2X1,2X2,2X4,4X1,4X2,4X4}_PIXELS_EXT`.
  Some are **not natively supported** on a given GPU (e.g. 1X4/4X1 on
  Mali-G715-class hardware per the MediaTek table) and get rounded (§2).
- Use coarse rates for skyboxes, distant geometry, motion-blurred / blurred
  regions, VR periphery; restore `1X1` for hero content and UI.

## 4. Per-Primitive Rate

Requires `GL_EXT_fragment_shading_rate_primitive`. The **last active shader
stage before rasterization** writes the built-in output:

```glsl
#version 310 es
#extension GL_EXT_fragment_shading_rate : require
void main() {
    gl_Position = u_mvp * a_position;
    gl_PrimitiveShadingRateEXT = 0x5;   // 2x2 rate (bitfield encoding)
}
```

Encoding: each axis is a bitfield — 1 pixel = `0b00`, 2 pixels = `0b01`,
4 pixels = `0b10`; value = `(x_bits << 2) | y_bits` (so 2x2 = `0x5`,
4x4 = `0xA`). Only the **provoking vertex's** value is used.

Stage rule (from the MediaTek docs): the writer must be the last
pre-rasterization stage — vertex shader for (VS,FS); **geometry shader** for
(VS,GS,FS); tessellation evaluation stage when present with no GS. Writing it
in the wrong stage is silently ignored.

## 5. Attachment Rate (per-region texture)

Requires `GL_EXT_fragment_shading_rate_attachment`. A rate image drives the
rate per framebuffer region:

```cpp
// 1) Query legal texel sizes (must be powers of two within min/max;
//    width/height aspect bounded; Mali-G715-class: only 8x8/16x16/32x32)
glGetIntegerv(GL_MAX_FRAGMENT_SHADING_RATE_ATTACHMENT_TEXEL_WIDTH_EXT, &texelW);
// 2) Rate texture: GL_R8UI, immutable, sized ceil(fb / texel)
glTexStorage2D(GL_TEXTURE_2D, 1, GL_R8UI, rateW, rateH);
// 3) Attach + configure combiners, then draw
glFramebufferShadingRateEXT(GL_FRAMEBUFFER, GL_SHADING_RATE_ATTACHMENT_EXT,
                            rateTex, 0, 1, texelW, texelH);
```

Texel value = same bitfield encoding as `gl_PrimitiveShadingRateEXT`. Fill the
rate map with a compute shader or CPU upload (e.g. derived from a foveation or
motion map). Costs to budget: **reading the attachment** adds per-tile work,
and updating it adds **synchronization** between the producer and the draw.

## 6. Combiners & Debugging

The effective rate = combiner(pipeline, primitive), then combiner(result,
attachment):

```cpp
glShadingRateCombinerOpsEXT(GL_FRAGMENT_SHADING_RATE_COMBINER_OP_REPLACE_EXT,  // pipeline+primitive
                            GL_FRAGMENT_SHADING_RATE_COMBINER_OP_KEEP_EXT);     // +attachment
```

Ops: `KEEP` (use A), `REPLACE` (use B), `MIN`, `MAX`, `MUL`.

- **Critical:** if you use per-primitive rate but leave the first combiner at
  `KEEP` (or attachment rate with second combiner `KEEP`), the hardware
  **ignores your rate**. Wrong combiners are the #1 "VRS does nothing" bug.
- Read the effective rate in the fragment shader via `gl_ShadingRateEXT`
  (same encoding) — visualize it to verify configuration, and branch LOD:
  `if (gl_ShadingRateEXT != 0) { /* coarse path */ }`.

---

## 7. Strategy Rules

1. VRS targets **fragment-bound** work (ALU / texture-heavy). If you are
   bandwidth- or geometry-bound, fix those first — VRS will not move the needle.
2. Natural candidates: sky/background, peripheral VR/foveated regions,
   particles, translucency stacks, post passes where quality loss is invisible.
3. Keep a per-draw rate policy table (material → rate) instead of scattering
   rate calls; always restore `1X1` before UI/HUD.
4. Measure before/after with the vendor profiler (card 18); on Adreno watch
   that LRZ/early-out behavior is unchanged.
5. On devices without any VRS surface, fall back to resolution scaling
   (render low-res + upscale) — same visual trade, different cost model.

---

## Related

- Card [14-adreno-gmem-vrs-lrz](../cards/14-adreno-gmem-vrs-lrz.md) — Adreno `GL_QCOM_shading_rate`
- `tbdr-bandwidth-rules.md` — VRS does not reduce bandwidth
- `profiling-tools.md` — verify fragment-bound before enabling VRS
