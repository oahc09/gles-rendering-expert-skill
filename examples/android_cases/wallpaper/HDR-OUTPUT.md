# BT.2020/PQ surface diagnostic with conservative SDR fallback

This implements **one conditional BT.2020/PQ output path**, not all HDR/WCG formats.
Display-P3, scRGB, HLG, Dolby Vision, HDR10+ and float surfaces are deliberately not
selected. Wide-color capability is recorded, never confused with HDR10 support.
No SMPTE2086 mastering-display or CTA861.3 content-light metadata is authored/set:
this is **not a mastered HDR10 delivery pipeline**. The successful label is
`BT2020_PQ_RGB10A2_REQUEST_ACCEPTED`, always accompanied by
`physicalHDR=NOT_VERIFIED`. Accepted EGL attributes do not prove panel luminance,
wallpaper compositor policy, absence of tone mapping or display mode behavior.

## Decision and ownership

* Android29+ uses the wallpaper **Engine's display context**, not the service's
  default display. API34+ queries the current `Display.Mode` HDR types; earlier
  supported APIs use `Display.HdrCapabilities`. API26–28 cannot use this reliable
  Engine display-context route and conservatively stay SDR.
* Reprobe on surface attach and foreground. Preview/home/secondary-display Engine
  instances own independent capability snapshots, contexts, programs and surfaces.
  They share only a reference-counted EGLDisplay lifetime: `WallpaperEglDisplay`
  initializes the default display once and terminates it only after the last
  cooperative Engine lease is closed. A PQ fallback cannot terminate another
  Engine's live display. `SharedLease` serializes acquire/release, makes close
  idempotent and does not count failed initialization. This protects this example's
  cooperative owners, not unrelated EGL clients outside the lease policy.
  A visible display-mode change without a surface/visibility callback is not yet
  actively listened for; physical output transitions remain device acceptance work.
* HDR10 display support plus exact `EGL_KHR_gl_colorspace` and
  `EGL_EXT_gl_colorspace_bt2020_pq` tokens permits an **attempt**. Enumerate configs
  and require exact 10/10/10/2 channel sizes, ES3 and window capability. No config
  support is inferred from a function pointer or wide-color flag.
* Request `EGL_GL_COLORSPACE_BT2020_PQ_EXT`; make current; query the actual EGL
  surface colorspace and default framebuffer encoding. PQ must report the requested
  colorspace and `GL_LINEAR` attachment encoding. Creating the surface is the
  compatibility test; the extension supplies no advance config/colorspace query.
* Any HDR config/context/surface/verification/shader failure falls back to a fresh
  RGBA8 config/context, not relabeling a PQ buffer as SDR. That retry is bounded by
  `forceSdr`. Failure of the SDR path stops rendering with an error instead of falsely
  claiming success. The borrowed SurfaceHolder Surface is never released by us.

## Transfer functions

The shader's authored scene values are linear Rec.709/sRGB primaries. The PQ branch
converts primaries to BT.2020, scales relative scene white to **203 cd/m²**, clamps
this diagnostic to 1000 cd/m², and applies ST2084 inverse EOTF with the standard
10000 cd/m² normalization. EGL does **not** apply PQ for us. There is no sRGB
encoding on this path.

SDR uses a simple bounded `x/(1+x)` tone map. If the actual attachment is GL_LINEAR,
the shader applies sRGB encoding once; if it is GL_SRGB, it emits linear mapped
values for the hardware encoding. Unknown attachment encoding is rejected. These
artistic tone-map/white choices are demonstration policy, not a universal mastering
recommendation. Bloom, gamut-volume mapping and display-specific calibration are
outside this small diagnostic.

## Tests and boundaries

```sh
python3 examples/android_cases/wallpaper/tests/run_policy_tests.py
python3 -m unittest discover -s examples/android_cases/wallpaper/tests -p 'test_*.py' -v
python3 examples/android_cases/validate_shaders.py
```

The plain Java helper test executes 18 assertions: missing display/HDR support,
missing/substring extensions, exact config channels and surface/encoding mismatch.
A separate Java lease test executes 14 assertions, including eight simultaneous
owners, idempotent close, last-owner disposal and failed initialization.
The six Python tests are **source contracts and reference transfer-function math**,
not Java execution or GPU pixels. The shared GLSL checker compiles/links the actual
embedded shader, while API35 `javac --release17` is a Java source/API check, not an APK
build. See checked-in policy validation; Android EGL, compositor and panel tests are
**NOT_RUN** until a real device report is attached.

Required device checks: HDR-capable and SDR displays; PQ extension absent; unsupported
10-bit config; forced surface-query mismatch; resize/preview/home/foreground;
unsupported-mode transition; error/fallback logs; neutral/near-black/100/1000-nit
patches compared with a verified reference and instrumentation. Android screenshots
may tone-map HDR and cannot alone verify emitted luminance. Also verify no double
encoding and that high-contrast touch highlights survive the SDR fallback.

## Primary references

* [Khronos combined BT.2020 colorspace specification](https://registry.khronos.org/EGL/extensions/EXT/EGL_EXT_gl_colorspace_bt2020_linear.txt): the PQ extension is defined in this combined file, not a separate `*_pq.txt` file; dependency, enums, application PQ encoding and config failure semantics.
* [KHR_gl_colorspace](https://registry.khronos.org/EGL/extensions/KHR/EGL_KHR_gl_colorspace.txt): framebuffer encoding and default LINEAR colorspace.
* [Wallpaper Engine display context](https://developer.android.com/reference/android/service/wallpaper/WallpaperService.Engine#getDisplayContext()): API29, corresponding display.
* [Display.HdrCapabilities](https://developer.android.com/reference/android/view/Display.HdrCapabilities): HDR types and API34 current-mode replacement.
* [Android wide color](https://developer.android.com/training/wide-color-gamut): WCG is independently capability-gated; no claim of P3 rendering here.

* [eglInitialize](https://registry.khronos.org/EGL/sdk/docs/man/html/eglInitialize.xhtml) / [eglTerminate](https://registry.khronos.org/EGL/sdk/docs/man/html/eglTerminate.xhtml): repeated initialization is not an independent per-Engine display lifetime.
