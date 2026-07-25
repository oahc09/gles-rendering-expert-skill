# LRZ, FlexRender & Depth — Keeping Adreno's Hidden-Surface Removal Alive

> Distilled from Qualcomm's *Adreno GPU on Mobile: Best Practices* and the
> framework's scene-rendering samples.

Adreno hides two big performance features behind the driver: **LRZ** and
**FlexRender**. Writing shaders and setting state the wrong way silently
disables them, so this file is about **not breaking** them.

---

## 1. LRZ (Low Resolution Z)

LRZ is Adreno's early, coarse depth test. During the binning pass the GPU builds
a low-resolution depth summary and uses it to **reject occluded fragments before
the fragment shader runs** — the single biggest overdraw saver on Adreno.

### Rules that keep LRZ effective
- **Draw opaque geometry front-to-back.** LRZ can only reject a fragment if
  something nearer was already recorded. Roughly sort opaque draws by distance.
- **Do a depth pre-pass** for heavy scenes so the color pass shades only visible
  fragments.
- **Avoid `discard` / `texkill` in opaque shaders.** Alpha-tested/`discard`
  shaders make depth undecidable early, disabling LRZ for that draw. Use alpha
  *blend* for foliage where possible, or isolate alpha-test draws.
- **Do not write `gl_FragDepth`.** Manual depth output forces late-Z and turns
  LRZ off for the draw.
- **Keep depth test + depth write on for opaque passes.** Disabling depth write
  removes the occlusion information LRZ relies on.
- **Render transparents after opaques**, depth-test on but depth-write off.

### What disables LRZ (avoid)
`discard`, writing `gl_FragDepth`, depth-func changes mid-pass that invert
ordering, blending during the opaque pass, and disabling early depth test.

---

## 2. FlexRender (binning vs. direct)

Adreno's FlexRender lets the driver choose between **binning (tiled)** rendering
and **direct** rendering per render target. You don't call it directly, but you
influence its choice:

- **Keep render passes self-contained** (clear at start, invalidate transient
  attachments at end) so the driver can pick the optimal mode — see
  [`gmem-load-store.md`](gmem-load-store.md).
- **Minimize the number and size of attachments**; fat MRT setups push more data
  through GMEM and bias toward costlier modes.
- **Avoid mid-pass dependencies** (sampling a target you are still rendering to),
  which force flushes and defeat binning.

---

## 3. Depth / stencil format choices

- **Use the smallest depth format that works.** Prefer `GL_DEPTH_COMPONENT24`
  or `GL_DEPTH24_STENCIL8`; avoid 32F depth unless precision truly requires it —
  wider depth = more GMEM and bandwidth.
- **Combine depth+stencil** into `GL_DEPTH24_STENCIL8` rather than two separate
  attachments.
- **Invalidate depth/stencil at pass end** — they are almost always transient.
- **Reduce framebuffer resolution** (dynamic resolution) before sacrificing
  visual features when GPU-bound; pair with SGSR2 upscaling.

## 4. Quick review checklist
- [ ] Opaque draws sorted roughly front-to-back.
- [ ] No `discard` or `gl_FragDepth` in opaque materials.
- [ ] Depth test + write enabled during the opaque pass.
- [ ] Depth/stencil use a combined 24/8 format and are invalidated at pass end.
- [ ] Transparents drawn last with depth-write off.
