# Executable GLES correctness validation (v1.0.3 candidate)

This directory adds real C++17/EGL builds and driver shader compilation. It is not
an Android application, a CTS substitute, or a mobile performance benchmark.

## Reproduce on a Linux host

Install a C++17 compiler and EGL/GLES development packages using your approved OS
package manager. For Debian these are `g++ libegl-dev libgles-dev` plus an EGL
implementation (Mesa). Then, from the repository root:

```sh
EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1 examples/validation/run-host.sh
```

The launcher compiles with `-std=c++17 -Wall -Wextra -Werror -pedantic`, links EGL,
GLESv2 and pthread, and exits nonzero on compile, link, GL or assertion failures.
`GLES_BUILD_DIR` selects the output directory (default `/tmp/gles-skill-validation`).
Optional `GLES_SDK_ROOT=/path/to/extracted/usr` supports a local SDK without system
installation; its current library layout is Debian x86-64. Other platforms should
provide normal compiler/linker paths instead. Mesa environment variables are not
portable EGL requirements. On a real device, do not force software rendering.

Output is NDJSON. Each passed case has an actual assertion, not an unconditional
success label. Shader versions above the actual runtime version are `UNSUPPORTED`,
not passed. Capability snapshots leave Android API and ANGLE backend unknown
rather than guessing from OS or GPU branding. Capture OS/build identity separately.

## Assertions and limits

| Case | Executed assertion | Not established |
|---|---|---|
| C01 | Default `GL_BACK`, FBO attachment legal; `GL_FRONT` and FBO `GL_BACK` rejected | All implementations/CTS conformance |
| C02 | Sized RGBA8 valid; integer/normalized format mismatch rejected | Every format/filter/renderability combination |
| C03 | Worker context uploads green pixel, fence + producer flush, synchronized future publication, consumer wait/rebind and pixel readback | Concurrent streaming stress or Android lifecycle |
| C04 | Pbuffer destruction/recreation/resize retains a texture; controlled context replacement rebuilds resources | Actual driver context loss, foreground/background or backend switching |
| C05 | Actual GLSL ES 300/310/320 compile and program link; invalid source rejected; 300 binding/SSBO/compute and 310 geometry core boundaries tested with positive upgraded pairs | Every extension grammar or target GPU shader optimizer |
| C11 | Different varying precisions link; incompatible varying types fail link | Uniform/block precision, all drivers |
| C06 | Red color remains correct before/after discarding unused depth | Bandwidth savings; invalidated depth contents are never read |
| W4 PBO | Map/unmap, upload from PBO, bounded fence wait and exact blue pixel; existing streaming uploader instantiated and checked over eight slot-reuse frames | Asynchronous throughput or multi-slot streaming performance |

Pbuffer sizes are deliberately tiny. Synchronous pixel reads are intentional
correctness assertions, not recommended hot-loop capture architecture. The harness
has bounded client waits; the outer runner should also use an OS timeout when testing
untrusted/broken drivers. Error paths terminate the process; production applications
need per-resource recovery and queued deletion on their owning context.

The legacy `references/examples/egl_context_manager.cpp` requires a native window
and is an integration sketch. It is not made runnable by this host test. Android
AHardwareBuffer/HDR/Swappy and actual context-loss integration remain independently
unverified; never convert host results into device results.

## Primary references

- [GLES 3.0.6 specification](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf): pixel formats, read-buffer selection, framebuffer invalidation, sync and shared-object visibility.
- [EGL 1.5 specification](https://registry.khronos.org/EGL/specs/eglspec.1.5.pdf): context sharing, current ownership and surface/context lifetimes.
- [Android native app glue header](https://android.googlesource.com/platform/ndk/+/master/sources/android/native_app_glue/android_native_app_glue.h): actual window/focus commands; context loss is detected via EGL errors, not an invented app command.

These are source references, not statements that CTS or Android device tests ran.

## Existing example compile/link coverage

```sh
python3 examples/validation/compile-legacy.py > legacy-host-compile.json
```

This compiles and links all five existing `.cpp` files plus the VAO header, with
strict warnings, and forces top-level C++ type construction in a wrapper. It does
**not** execute illustrative mains or claim Android target compilation. Only the
PBO uploader is additionally instantiated **and executed** by `egl_smoke.cpp`.

The check exposed missing default constructors in PBO, MSAA and video wrappers.
The video integration example also now gates the ESSL3 external-image extension
and retains the pointer-sized EGLImage handle instead of truncating it to GLuint.
Its Android import runtime remains untested. Primary contracts:
[OES_EGL_image](https://registry.khronos.org/OpenGL/extensions/OES/OES_EGL_image.txt),
[OES_EGL_image_external_essl3](https://registry.khronos.org/OpenGL/extensions/OES/OES_EGL_image_external_essl3.txt).
