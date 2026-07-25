# Pixel Local Storage and On-Chip Deferred Rendering

> Distilled from the PowerVR Native SDK `DeferredShading` example:
> *"Optimal deferred shading using Pixel Local Storage (PLS)."*
> Requires `GL_EXT_shader_pixel_local_storage` (GLES 3.0+).

## Why PLS on PowerVR?

Traditional deferred rendering writes the G-Buffer to multiple render targets
(MRT), stores those textures to DRAM, then reads them back in the lighting pass.
On a TBDR GPU this is wasteful because the G-Buffer data is already **in tile
memory** during the geometry pass.

**Pixel Local Storage** (`GL_EXT_shader_pixel_local_storage`) allows the
fragment shader to read/write per-pixel data that persists within tile memory
for the duration of a render pass — **zero DRAM round-trips for the G-Buffer**.

PowerVR's HSR makes this particularly effective: only visible fragments write
to PLS (no wasted PLS writes for occluded pixels).

---

## Rules

- **Use PLS for deferred G-Buffer on PowerVR.** Replace MRT-based deferred with
  a single render pass that fills PLS in the geometry subpass and reads it in the
  lighting subpass. This is the canonical PowerVR deferred technique.
- **Pack PLS storage tightly.** Total PLS budget is limited (~128 bits/pixel on
  most hardware). Use compact formats: `rgb10_a2` for albedo/lighting,
  `rg16f` for normal XY (reconstruct Z), `r11f_g11f_b10f` for HDR.
- **PLS data is undefined at pass start and lost at pass end** — it exists only
  within a single render pass, in on-chip tile memory. Never attempt to read PLS
  from a previous frame or pass.
- **Combine with stencil for light volumes.** Mark lit pixels via stencil during
  the light volume geometry pass, then skip unlit pixels in the shading pass.
- **Fallback chain**: PLS → `GL_EXT_shader_framebuffer_fetch` → MRT +
  `glInvalidateFramebuffer`.

## Code Pattern (from SDK `DeferredShading`)

```glsl
// Geometry pass fragment shader — write G-Buffer to PLS
#version 300 es
#extension GL_EXT_shader_pixel_local_storage : require
precision highp float;

__pixel_localEXT FragDataLocal {
    layout(rgb10_a2)    vec4 albedo;
    layout(rgb10_a2)    vec4 normal;  // XY packed, Z reconstructed
    layout(r11f_g11f_b10f) vec4 lighting;
} pls;

in vec3 v_Normal;
in vec2 v_UV;
uniform sampler2D u_Albedo;

void main() {
    pls.albedo = texture(u_Albedo, v_UV);
    pls.normal = vec4(normalize(v_Normal).xy * 0.5 + 0.5, 0.0, 1.0);
    pls.lighting = vec4(0.0);  // accumulate in lighting pass
}
```

```glsl
// Lighting pass fragment shader — read G-Buffer from PLS, accumulate
#version 300 es
#extension GL_EXT_shader_pixel_local_storage : require
precision highp float;

__pixel_localEXT FragDataLocal {
    layout(rgb10_a2)    vec4 albedo;
    layout(rgb10_a2)    vec4 normal;
    layout(r11f_g11f_b10f) vec4 lighting;
} pls;

uniform vec3 u_LightPos;
uniform vec3 u_LightColor;
uniform float u_LightRadius;

void main() {
    vec3 N = vec3(pls.normal.xy * 2.0 - 1.0, 0.0);
    N.z = sqrt(max(0.0, 1.0 - dot(N.xy, N.xy)));
    // ... compute attenuation, NdotL ...
    pls.lighting += vec4(pls.albedo.rgb * u_LightColor * NdotL * atten, 0.0);
}
```

## Anti-pattern

```cpp
// ❌ Traditional MRT deferred on PowerVR — unnecessary DRAM traffic
glBindFramebuffer(GL_FRAMEBUFFER, gBufferFbo);
glDrawBuffers(3, attachments);  // albedo, normal, depth → stored to DRAM
drawGeometry();

glBindFramebuffer(GL_FRAMEBUFFER, lightingFbo);
// ... read G-Buffer textures back from DRAM — bandwidth wasted
```

## Comparison with Mali PLS

The extension and usage are identical (`GL_EXT_shader_pixel_local_storage`).
On PowerVR, the additional benefit is that **HSR ensures only truly visible
fragments write to PLS**, so there is no wasted G-Buffer fill from occluded
geometry — a natural synergy between HSR + PLS that other GPUs cannot fully
replicate.
