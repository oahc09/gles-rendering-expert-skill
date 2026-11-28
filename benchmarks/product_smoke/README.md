# Software GLES product smoke: mobile preview and translucent UI

An opt-in executable product case for the GLES skill's attachment preservation,
context-aware deletion, fragment precision, and MSAA resolve guidance. It uses
only Python 3's standard library and preinstalled Linux EGL/GLES libraries.
No device setup, dependency download, Android runtime, benchmark, or release
gate is performed. The procedure saves actual GPU-API readback bytes.

```sh
GALLIUM_DRIVER=llvmpipe python3 benchmarks/product_smoke/mobile_ui_resolve.py /tmp/gles-mesa-new
GLES_ANGLE_ROOT=/path/to/trusted-angle-software-libs \
  python3 benchmarks/product_smoke/mobile_ui_resolve.py /tmp/gles-angle-new
```

The output directory must not exist. For Mesa the host needs its surfaceless
EGL software stack. The optional ANGLE directory must contain the trusted
`libEGL.so`/GLES dependencies and `vk_swiftshader_icd.json`; select only
trusted, previously verified native binaries. The harness explicitly requests
ANGLE Vulkan with SwiftShader and checks the reported software renderer.
It does not find, fetch, or replace driver binaries. If the renderer fails
admission, do not count that lane as passed.

## Policy and controls

1. Draw an opaque depth-tested preview into an RGBA8 FBO. Draw the overlapping
   far primitive last and require the nearer pixel to survive.
2. Select 4× renderbuffer samples only when the RGBA8 capability query advertises
   4. Resolve to a separate single-sample target with an equal-size NEAREST
   color blit. A scaled MSAA blit must fail without changing the destination.
   Without 4× support, run the single-sample scene path and label the fallback.
3. Disable depth for the UI. Decode the icon's sRGB texture into linear values,
   premultiply once, then blend with `ONE, ONE_MINUS_SRC_ALPHA` in the
   single-sample linear target. Compare the 80 intended clipped pixels with the
   analytic color equation and require all 176 outside pixels unchanged
   against the scene's own readback. This includes the adjacent guard pixels.
4. Compare the alternative UI-while-multisampled path and record any changes
   to adjacent edge pixels separately from center and distant-guard checks.
   Deliberately repeat source-alpha multiplication and skip the sRGB decode to
   prove the oracle distinguishes both color mistakes. Recreate the EGL context
   and surface, release objects only while their owned context is current, and
   repeat deterministically on the same software backend.

The observed Mesa llvmpipe 4× alternative touched 19 adjacent pixels near the
lower/left clip edge, while ANGLE/SwiftShader 4× touched none in this case.
Both backends preserved all 176 outside pixels after moving the UI pass
after resolve. Mesa softpipe only exercised the explicit single-sample
fallback. The data does not establish a driver/spec violation, cross-driver
edge equivalence, forced context loss, presentation, hardware, performance,
or mobile-device acceptance.

Raw captures are bottom-left-origin tightly packed 16×16 RGBA8. JSON stdout
records individual capture hashes and the actual sample count and driver;
the center values can differ by one quantization step between drivers.

### v1.1.2 audit: documentation shader readbacks

`audit_formats_culling.py <new-report.json>` compiles the actual card/rule
code fences and checks Mesa llvmpipe readbacks. The core GLES indirect loop
renders a fixed four-sphere boundary case (outside, tangent, intersecting,
inside); the old center-only predicate is the negative control. The optional
EXT multi-draw route runs only when the current context advertises that extension
and resolves its entrypoint. Both MSDF snippets render independent RGB channels
from RGB8/RGBA8, and the R8/default-swizzle negative control fails for the same
MSDF input. Single-channel SDF is verified independently.

The [host validation workflow](../../.github/workflows/validation.yml) executes
these alongside UI resolve and odd-dimension YUV, archiving raw probe reports
and readbacks. Results are software correctness, not hardware or font-layout
certification.
