# HSR (Hidden Surface Removal) and Rendering Order

> Distilled from PowerVR Performance Recommendations and Imagination developer
> guidance. The single most important architectural difference between PowerVR
> and other mobile GPUs.

## What is HSR?

PowerVR's **Image Synthesis Processor (ISP)** performs **full per-pixel Hidden
Surface Removal** for every tile before any fragment shader runs. It processes
ALL submitted primitives for a tile, determines visibility at every pixel, and
ONLY sends the final visible fragments to the shading cluster (USC).

This is fundamentally different from:
- **Desktop GPUs**: Shade everything in submission order, rely on early-Z for
  partial culling.
- **ARM Mali (FPK)**: Forward Pixel Kill — partial; best-effort kill of hidden
  fragments but not pixel-exact in all cases.
- **Qualcomm Adreno (LRZ)**: Low-Resolution Z — coarse; catches grossly hidden
  drawcalls but not pixel-level.

Under ideal conditions (no `discard`, no alpha test, depth writes enabled),
PowerVR HSR achieves **zero overdraw for opaque geometry** regardless of
submission order — every opaque pixel is shaded only once. If any condition
breaks the ISP assumptions (e.g. `discard` forces deferred shading decisions),
overdraw can reappear for affected fragments.

---

## Rules

### 1. Do NOT use a depth pre-pass

On every other GPU architecture, a depth pre-pass (render geometry with
color-write off, then re-render with depth-equal test) avoids overdraw. **On
PowerVR, HSR already achieves the same result automatically.** A depth pre-pass:
- Doubles vertex processing load (geometry submitted twice).
- Doubles parameter buffer usage (can trigger SPM partial renders).
- Provides **zero** shading benefit — HSR already eliminated hidden fragments.

```cpp
// ❌ WRONG on PowerVR: useless depth pre-pass
glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE);
drawAllOpaqueGeometry();  // pass 1: depth only
glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
glDepthFunc(GL_EQUAL);
drawAllOpaqueGeometry();  // pass 2: shading with depth-equal
glDepthFunc(GL_LESS);

// ✅ CORRECT on PowerVR: submit once, let HSR do its job
drawAllOpaqueGeometry();  // HSR ensures zero overdraw automatically
```

### 2. Avoid `discard` / alpha test

When a fragment shader uses `discard` (or the deprecated `GL_ALPHA_TEST`), the
ISP **cannot determine final visibility until after the shader runs**. This
forces the hardware to:
1. Defer the HSR decision for that fragment.
2. Run the fragment shader speculatively.
3. Potentially shade fragments that would have been killed by HSR.

**Impact**: Overdraw returns for all geometry rendered after the `discard`
drawcall within the same tile, because later fragments can no longer be
confidently culled.

**Alternatives**:
- **Alpha blend** with `depth_write = OFF`: The ISP knows blended fragments are
  always visible (they composite on top), so it can continue eliminating hidden
  opaque geometry behind them without deferral.
- **Separate pass for alpha-tested objects**: Draw ALL opaque first, then draw
  alpha-tested objects last to minimize contamination of the HSR pipeline.
- If `discard` is unavoidable, render those objects **after** all opaque
  geometry in submission order.

```glsl
// ❌ Defeats HSR — fragments behind this one cannot be culled early
if (texture(u_AlbedoMap, v_UV).a < 0.5) discard;

// ✅ Prefer alpha blend with depth write off (does NOT defeat HSR)
// Set glDepthMask(GL_FALSE) + glEnable(GL_BLEND) for this drawcall
out_Color = texture(u_AlbedoMap, v_UV);  // alpha < 1.0 blends naturally
```

### 3. Recommended draw order

Even though HSR handles opaque ordering automatically, there is still an
optimal submission order to minimize wasted ISP work and maximize HSR
efficiency for mixed content:

1. **Opaque geometry** — any order (HSR handles it). Front-to-back gives a tiny
   ISP efficiency boost but is not required.
2. **Alpha-tested / `discard`** — after all opaque. Minimize the number of
   these draws. Each one creates an "HSR break" within the tile.
3. **Skybox / background** — after opaque (guaranteed to be behind everything;
   HSR eliminates it for free).
4. **Alpha-blended / translucent** — last, back-to-front (standard blend
   ordering; depth write off).

### 4. Geometry complexity and the Parameter Buffer

All transformed geometry for the current frame is stored in the **Parameter
Buffer (PB)**, an off-chip memory allocation. If submitted geometry exceeds the
PB capacity, the hardware triggers **SPM (Smart Parameter Management)** — a
partial render that flushes current tiles early and continues. This is
extremely expensive (effectively doubles render cost).

- **Keep draw call vertex counts reasonable** — avoid million-poly scenes
  without LOD.
- **Use LOD (Level of Detail)** aggressively; PowerVR penalizes geometry
  complexity more than shader complexity.
- **Occlusion queries** can pre-cull large geometry batches before submission.

---

## Diagnostic with PVRScope / PVRTune

- **HSR efficiency** metric: should be close to 100% for opaque. If it drops,
  look for `discard` usage or missing depth test.
- **ISP Pixels Passing** vs. **ISP Pixels Processed**: ratio shows overdraw.
  For pure opaque, passing/processed ≈ 1.0.
- **Parameter Buffer usage**: if near-full or SPM events appear, geometry is too
  complex for the frame.
