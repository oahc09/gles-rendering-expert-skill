# HDR & Wide Color Gamut Display Pipeline

> Getting rendered HDR/wide-gamut content *to the display* on Android. The
> skill's existing examples (e.g. `offscreen_pipeline.cpp`, `pbr_brdf.frag`)
> already render in linear HDR internally; this document covers the missing
> display-output half: EGL colorspace, HDR surface metadata, and gamut queries.

---

## 1. Terminology & Pipeline Stages

```
Scene-linear HDR (RGBA16F FBO)
  → tone map / gamut map (shader)
    → swap-chain buffer with a declared colorspace (EGL)
      → compositor honoring display capability (SurfaceFlinger)
        → SDR or HDR panel
```

Two independent axes, often conflated:
- **Wide Color Gamut (WCG)** — colors beyond sRGB (usually Display-P3). Does
  NOT require an HDR panel.
- **HDR transfer function** — PQ (SMPTE ST 2084) or HLG extended luminance
  range. Requires an HDR-capable display.

---

## 2. Query Device Capability First (Rules)

1. **WCG**: `Surface.isWideColorGamut()` via JNI (Android 8+), or
   `AConfiguration_isWideColorGamut` on the resources config. Never assume.
2. **HDR display**: `Display.getMode()` HDR types (Android Q+) /
   `Display.HdrCapabilities` for supported types (HDR10 = ST 2084, HLG) and
   max luminance. Expose via JNI; there is no GLES-side query.
3. Fall back gracefully: SDR display → tone-map HDR content to sRGB;
   WCG-only display → render P3-gamut, SDR range.

---

## 3. EGL Colorspace (Rules)

`EGL_KHR_gl_colorspace` lets a surface declare how its RGBA values should be
interpreted by the compositor.

| Attribute value | Use |
|:---|:---|
| `EGL_GL_COLORSPACE_SRGB_KHR` (default) | Standard sDR sRGB output |
| `EGL_GL_COLORSPACE_LINEAR_KHR` | Linear-extended range (driver-specific support) |
| `EGL_GL_COLORSPACE_SCRGB_LINEAR_EXT` | scRGB linear: 1.0 = 80 nits, >1.0 extended range (needs `EGL_EXT_gl_colorspace_scrgb_linear`) |
| `EGL_GL_COLORSPACE_DISPLAY_P3_PASSTHROUGH_EXT` | Display-P3 gamut passthrough |

- **Check the extension strings** before using non-sRGB values:
  `EGL_EXT_gl_colorspace_scrgb_linear`, `EGL_EXT_gl_colorspace_display_p3`.
- Set the attribute at **surface creation** (`eglCreateWindowSurface`
  attrib list); it cannot be changed later.
- scRGB-linear is the practical HDR path for GLES on Android: keep linear
  lighting values, let 1.0 map to SDR white and >1.0 encode highlights.

```cpp
// ✅ HDR-capable surface (scRGB linear) — verify extension first
const EGLint attribs[] = {
    EGL_GL_COLORSPACE, EGL_GL_COLORSPACE_SCRGB_LINEAR_EXT,
    EGL_NONE
};
EGLSurface surf = eglCreateWindowSurface(dpy, cfg, win, attribs);
```

---

## 4. HDR Static Metadata (CTA-861.3)

For HDR10/HLG surfaces, the display needs mastering metadata via
`EGL_EXT_surface_CTA861_3` (`eglSurfaceAttrib`):

- `EGL_SMPTE2086_DISPLAY_PRIMARY_RX/RY/GX/GY/BX/BY_EXT` — mastering primaries
  (CIE 1931 xy, scaled ×50000 per spec)
- `EGL_SMPTE2086_WHITE_POINT_X/Y_EXT` — mastering white point
- `EGL_SMPTE2086_MAX_LUMINANCE_EXT` / `EGL_SMPTE2086_MIN_LUMINANCE_EXT`
  — max/min luminance (cd/m², max ×1, min ×10000)

Rules:
- Values must reflect the **content's mastering intent**, not the panel; the
  compositor tone-maps between the two.
- Metadata is required for HDR10 passthrough; omitting it typically forces
  SDR treatment.

---

## 5. Rendering-Side Rules

1. Keep the whole post chain in **linear extended range** (RGBA16F) until the
   final tone/gamut map into the swap-chain colorspace — never store tonemapped
   values in sRGB8 mid-chain and re-linearize.
2. The final pass must match the surface colorspace: scRGB surface → output
   linear values where 1.0 = SDR white; P3 surface → convert primaries from
   scene-referred space into Display-P3.
3. UI overlays should be rendered in the same colorspace as the scene or
   composited by the platform UI layer — mismatched UI looks washed out.
4. Test on at least one WCG device and one HDR panel; color-management bugs
   are invisible on sRGB dev hardware.

---

## 6. Technique → Rule Map

| Goal | Path |
|:---|:---|
| WCG-only device (no HDR panel) | Display-P3 colorspace surface, SDR range |
| HDR10 panel | scRGB-linear surface + CTA-861-3 metadata, linear pipeline |
| SDR fallback | sRGB surface, filmic/ACES tone map in final pass |
