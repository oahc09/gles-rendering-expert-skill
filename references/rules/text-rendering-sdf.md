# Text Rendering on Mobile GLES — SDF/MSDF Atlases

> Crisp, scalable text on GLES = precomputed **distance fields** in a texture
> atlas + one batched draw. Bitmap atlases blur or alias when scaled; SDF/MSDF
> shaders recover analytic edge antialiasing from derivatives. This is the
> standard for game UI and map type on Mali/Adreno/PowerVR.

---

## 1. Method selection

| Method | Atlas format | Scales cleanly? | Sharp corners? | Use |
|:---|:---|:---|:---|:---|
| Bitmap + mipmaps | `GL_RGBA8`/`GL_R8` | No (blur at 2x+) | Yes at 1x | Fixed-size HUD numerals |
| **SDF** (single channel) | `GL_R8` | Yes | Rounds acute corners | Body text, any size range |
| **MSDF** (3 edge channels) | `GL_R8` (rgb) | Yes | Preserved | Display/UI type, CJK |

Rule: default to **MSDF at 1 px/em spread ~4–8**, fall back to SDF when atlas
memory forces a smaller texture.

## 2. Rules

1. **Atlas is a plain R8/R8 RG8 texture — never an sRGB internal format.** The
   stored value is a *distance*, not color; hardware sRGB decode would corrupt
   the field math. Gamma-correct the final coverage yourself (rule 5).
2. **Edge antialiasing from screen-space derivatives**, not mipmaps:
   `float a = smoothstep(0.5 - w, 0.5 + w, dist)` with `w = fwidth(dist)`
   (clamp `w` to avoid degenerate-derivative blowups at quad seams). Do not
   mip the distance field; sampling across miplevels mixes distance scales.
   MSDF coverage = `median(r,g,b)` then the same smoothstep.
3. **Atlas UV needs `highp` on big atlases.** `mediump` float has ~10-bit
   mantissa: on a 4096-px atlas the positional error reaches several texels —
   declare atlas coords `highp` above 2048² or subdivide UV space. (`fwidth`
   is undefined inside non-uniform control flow — keep the AA math at the top
   level of `main()`, use `discard` only after computing alpha.)
4. **One draw call per atlas + style.** Pack glyph quads of an entire string
   into one dynamic VBO (`GL_DYNAMIC_DRAW` + `glMapBufferRange` with
   `GL_MAP_INVALIDATE_RANGE_BIT` ring) or draw glyph instances with
   `glDrawArraysInstanced` (per-instance: atlas rect, pen offset, size, color).
   A string rendered as N quads = N draw calls is the classic UI killer.
5. **Premultiplied-alpha output** (`rgb *= a; glBlendFunc(GL_ONE,
   GL_ONE_MINUS_SRC_ALPHA)`) — avoids the dark halo when AA edges blend over
   varied backgrounds, and composites correctly in a linear-space pipeline
   (apply the same gamma the rest of the pipeline uses AFTER coverage).
6. **Dynamic atlas management**: bake glyphs on demand into a shelf/skyline
   allocator via `glTexSubImage2D` (partial upload, PBO-staged per
   `texture-streaming-lod.md`); quantize *subpixel* offsets to 1/4 px so a
   moving camera doesn't re-bake; evict with LRU per Unicode page (CJK: one
   256-codepoint page per sheet, otherwise a 4096² atlas is not enough).
7. **SDF size range**: bake the distance spread for the smallest on-screen px
   size (~6 px cap height) — a spread of 4–8 texels at atlas resolution keeps
   both small-size AA and large-size smoothness; beyond ~8x baked size the
   field rounds strokes — swap in a higher-resolution bake tier.
8. **Color glyphs (emoji) are a separate RGBA bitmap tier** blended under the
   MSDF shape or drawn as their own quad pass; distance fields only encode
   coverage, not color.
9. **TBDR**: text is alpha-blended overdraw — keep glyph quads tight to the
   ink box (per-glyph quad from font metrics, not per-em advance squares) and
   draw UI last in the frame so blended tiles flush once.

## 3. Code pattern (MSDF sampling fragment)

```glsl
#version 300 es
precision mediump float;
// (GLSL ES default-precision statements only exist for float/int/samplers —
//  enforce highp UV with explicit declarations like v_Uv below)

uniform sampler2D u_Atlas;       // GL_R8 MSDF, CLAMP_TO_EDGE, LINEAR
in highp vec2 v_Uv;
in vec4 v_Color;
out vec4 fragColor;

float median(float r, float g, float b) {
    return max(min(r, g), min(max(r, g), b));
}

void main() {
    vec3 s = texture(u_Atlas, v_Uv).rgb;
    float sd = median(s.r, s.g, s.b) - 0.5;
    float w = max(fwidth(sd), 1e-5);                 // clamped derivative
    float a = smoothstep(-w, w, sd);
    if (a <= 0.0) discard;                           // after AA math (rule 2)
    fragColor = vec4(v_Color.rgb * a, a) * v_Color.a; // premultiplied (rule 5)
}
```

## 4. Common pitfalls

| Pitfall | Symptom | Fix |
|:---|:---|:---|
| sRGB internal format for SDF atlas | Wrong gamma, thick/thin strokes at scale | Plain `GL_R8`; gamma after coverage |
| Mipmapping the distance field | Blur/shrink at grazing LODs | No mips; `GL_TEXTURE_MAX_LEVEL 0` + LINEAR |
| `fwidth` inside `if` branch | Undefined/zero AA on some drivers | Compute AA unconditionally, `discard` after |
| `mediump` atlas UV on 4096 atlas | Glyph jitter/offsets | `highp vec2` or smaller atlas (rule 3) |
| One draw call per glyph/string | UI dominates draw-call budget | Batched VBO or instanced glyphs (rule 4) |
| Non-premultiplied blend over photos | Dark halo on AA edges | Premultiplied output + `(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)` |
| Re-baking glyphs per subpixel move | Atlas thrash + uploads | Quantize subpixel to 1/4 px; cache by (glyph, subpixel bucket) |
| Advance-width quads | 2x overdraw on every string | Shrink quad to ink bounds |

## 5. Cross-references

- Card 02 (texture formats), card 12 (batching/instancing), `texture-streaming-lod.md` (atlas uploads)
- Card 05 (precision qualifiers), `glsl-es-optimization.md` (derivative/branch rules)
