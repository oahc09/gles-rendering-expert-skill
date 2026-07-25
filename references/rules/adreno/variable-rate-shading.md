# Variable Rate Shading — `QCOM_shading_rate`

> Distilled from the `shading_rate` sample. Extension:
> [`GL_QCOM_shading_rate`](https://registry.khronos.org/OpenGL/extensions/QCOM/QCOM_shading_rate.txt).

Variable Rate Shading (VRS) lets you run the fragment shader **fewer than once
per pixel** — one invocation covers a block of pixels (e.g. 2x2 or 4x4). Depth,
stencil, and coverage stay at full resolution, so geometry edges remain crisp;
only shading frequency drops. Applied to low-detail regions this cuts fragment
cost dramatically with little to no perceptible quality loss.

---

## API

```cpp
// Per drawcall: pick a shading rate, draw, then restore full rate.
// NOTE: QCOM_shading_rate does NOT require glEnable() — the extension is
// implicitly active once confirmed via glGetString(GL_EXTENSIONS).
// Simply call glShadingRateQCOM() to change the rate.
glShadingRateQCOM(GL_SHADING_RATE_2X2_PIXELS_QCOM);
drawSkybox();
glShadingRateQCOM(GL_SHADING_RATE_1X1_PIXELS_QCOM); // back to full rate
drawCharacters();
```

**Available rates:** `1X1` (full), `1X2`, `2X1`, `2X2`, `4X4`
pixels (`GL_SHADING_RATE_<n>X<m>_PIXELS_QCOM`). Higher blocks = fewer
invocations = more savings but softer shading. Not all devices support all
rates; query `GL_SHADING_RATE_QCOM` properties and validate at runtime.

---

## Where to apply it (per-drawcall strategy)

Assign coarser rates to draws whose shading detail the eye won't miss:

- **Skyboxes, distant terrain, backgrounds** → `2X2` or `4X4`.
- **Heavily blurred / out-of-focus geometry** (DoF, motion blur targets) → `2X2`+.
- **Peripheral regions in VR** (foveated rendering) — full rate in the fovea,
  coarse toward the edges.
- **Particle / transparency fills** that are already low-frequency.

Keep full rate (`1X1`) for:
- Foreground characters and hero assets, text/UI, sharp normal-mapped surfaces,
  and anything with high-frequency specular detail.

## Rules

- **Always query support and gate behind a runtime check** — VRS is an extension
  and absent on many devices. Provide a `1X1` fallback path.
- **Drive the rate by content, not globally.** A single global coarse rate
  looks bad; per-drawcall (or attachment-mask, on capable HW) is the win.
- **Restore `1X1` after each coarse draw** so state does not leak into later
  draws.
- **Validate visually** — VRS artifacts show up as blocky shading on
  high-contrast edges lit by specular highlights; back off the rate there.
- Combine with LRZ and front-to-back ordering; VRS reduces shading cost but does
  **not** reduce overdraw — cull and depth-reject first.
