# Post-Processing Chains on Mobile — Bloom, Blur & Color Grading

> Distilled from the Adreno SDK PostProcessing sample lineage (separated
> Gaussian, linear-sampling optimization, Kawase blur, Dual Filter, Tent Filter)
> and LearnOpenGL's bloom chapter, adapted for TBDR bandwidth budgets.

Post-processing is N full-screen passes stacked — every extra pass costs one
full-screen read + one write. On mobile the chain design matters more than the
shader math.

---

## 1. Chain design rules

1. **Downsample first**: bloom and blur operate at reduced resolution. A
   **downsample chain** (1/2 → 1/4 → 1/8) costs far less than blurring at
   full res, and hides blur quality loss. Re-upsample with bilinear at the end.
2. **Minimize pass count**: combine where possible (e.g. bloom composite +
   tone-map + color grade in the final pass). Every saved pass is one
   full-screen read+write.
3. **Ping-pong FBOs** for separable passes (H then V); invalidate the consumed
   buffer when no longer needed.
4. **HDR buffer for the source** (`RGBA16F` or `R11F_G11F_B10F`) if doing
   HDR bloom; tone-map in the final composite. Keep intermediates `RGBA8` once
   in LDR.
5. Half-precision intermediates (`RGBA8`, `RG16F`) cut post-chain bandwidth
   versus `RGBA16F` everywhere.

## 2. Blur variants (pick by budget)

| Technique | Taps | Cost | Quality |
|:---|:---|:---|:---|
| **Gaussian (separated)** | 2×N | medium | reference quality |
| **Gaussian + linear sampling** | 2×⌈N/2⌉ | ~half taps | same quality, off-center taps |
| **Kawase blur** | 4–5 per pass | low | good for bloom, boxier up close |
| **Dual Filter** (Marius Bjørge) | 8+8 | low-medium | very good, bandwidth-friendly |
| **Tent Filter** (COD AW) | 9 | low | excellent bloom, upsampling-friendly |

- **Linear-sampling trick**: bilinear hardware filtering between two Gaussian
  taps yields one weighted tap — nearly halves tap count for the same kernel.
  Compute the two off-center tap offsets/weights once per radius.
- **Kawase/Dual/Tent are designed for downsampled buffers** — pair with the
  downsample chain; they are not full-res sharpeners.

## 3. Bloom structure

```
scene (HDR) → bright pass + downsample → blur chain (down) → blur chain (up)
            → composite + tone-map + color grade → display
```

- The bright pass can be merged into the first downsample (threshold while
  downsampling) to save a pass.
- Composite adds the blurred chain back over the source before tone-mapping.

## 4. Color grading with a 3D LUT

- Bake a **3D LUT** (e.g. 32³) from a reference strip texture and apply in the
  final pass: `texture(u_LUT, vec3(color.rgb))` (coords remapped to 0..1 with
  half-texel inset). One texture fetch replaces per-channel curve math.
- `GL_TEXTURE_3D` + `GL_RGB8`; clamp wrap; linear filtering.

## Common pitfalls

| Pitfall | Consequence | Fix |
|:---|:---|:---|
| Blurring at full resolution | 4–16× blur cost | Downsample chain first |
| Per-pass fullscreen FBO ping-pong without invalidate | Wasted stores | Invalidate consumed buffers |
| RGBA16F for every intermediate | Bandwidth blow-up | RGBA8 once in LDR |
| Manual N-tap Gaussian when taps are symmetric | 2× taps | Linear-sampling trick |
| Separate tone-map + grade + bloom passes | 3 full-screen passes | Merge in final composite pass |
