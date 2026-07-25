# Windows Platform — Developing & Running GLES on Windows

> Covers the Windows-specific realities that the Android / Embedded-Linux rules
> do not: developing Android GLES apps *on* a Windows host, running true GLES on
> Windows via **ANGLE**, Windows-on-ARM (Snapdragon / Adreno), and the
> Visual Studio / CMake toolchain.

Windows has **no native OpenGL ES driver** for most desktop GPUs. A plain WGL
context gives you **desktop OpenGL**, whose semantics differ from GLES
(no `precision` requirement, different extension set, relaxed rules). Shipping
against desktop GL and *assuming* it behaves like GLES is the #1 source of
"works on my PC, breaks on device" bugs. The supported path for real GLES on
Windows is **ANGLE**.

---

## 1. ANGLE — the GLES implementation for Windows

ANGLE (Almost Native Graphics Layer Engine) translates GLES 2.0 / 3.0 / 3.1
calls into a native backend: **D3D11** (default on Windows), **Vulkan**, or
desktop GL. It ships as two DLLs — `libEGL.dll` and `libGLESv2.dll` — that you
distribute alongside the app. Chrome, Edge, and most cross-platform engines use
it to get conformant GLES on Windows.

### Rules

- **Link against ANGLE's `libEGL` / `libGLESv2`, not the system `opengl32`.**
  Never call WGL directly if you want GLES semantics.
- **Select the backend explicitly** via `EGL_ANGLE_platform_angle`. Do not rely
  on the default; pin D3D11 or Vulkan so behavior is reproducible across
  machines.
- **Query and validate the GLES version after context creation** — ANGLE's
  GLES 3.1 support depends on the backend and driver feature level.
- **Keep all GLES-3.x + GLSL-ES rules from the other rule files.** ANGLE
  enforces GLES validation (precision qualifiers, `#version 300 es`, no desktop
  entry points), so code that passes here is far more likely to pass on device.

### EGL initialization with ANGLE

```cpp
#include <EGL/egl.h>
#include <EGL/eglext.h>

// eglGetPlatformDisplayEXT is an extension entry point — load it dynamically.
auto eglGetPlatformDisplayEXT =
    reinterpret_cast<PFNEGLGETPLATFORMDISPLAYEXTPROC>(
        eglGetProcAddress("eglGetPlatformDisplayEXT"));

// Pin the D3D11 backend for reproducible behavior.
const EGLint dispAttribs[] = {
    EGL_PLATFORM_ANGLE_TYPE_ANGLE, EGL_PLATFORM_ANGLE_TYPE_D3D11_ANGLE,
    EGL_NONE
};
EGLDisplay dpy = eglGetPlatformDisplayEXT(
    EGL_PLATFORM_ANGLE_ANGLE, EGL_DEFAULT_DISPLAY, dispAttribs);

EGLint major = 0, minor = 0;
eglInitialize(dpy, &major, &minor);

// Request a GLES 3.x context.
const EGLint ctxAttribs[] = { EGL_CONTEXT_MAJOR_VERSION, 3,
                              EGL_CONTEXT_MINOR_VERSION, 1, EGL_NONE };
EGLContext ctx = eglCreateContext(dpy, config, EGL_NO_CONTEXT, ctxAttribs);

// Verify what you actually got.
const char* ver = reinterpret_cast<const char*>(glGetString(GL_VERSION));
// e.g. "OpenGL ES 3.1 (ANGLE ...)"
```

Backend selection values:

| Backend | `EGL_PLATFORM_ANGLE_TYPE_*_ANGLE` | When to use |
|:--------|:-----------------------------------|:------------|
| D3D11 | `D3D11` | Default Windows desktop; widest coverage |
| Vulkan | `VULKAN` | Closest to mobile Vulkan drivers; WoA |
| Desktop GL | `OPENGL` | Debugging against a native GL driver |

---

## 2. Windows on ARM (Snapdragon / Adreno)

Windows-on-ARM devices (Snapdragon-based Surface, dev kits) carry a real
**Adreno GPU**. This is the one Windows case with genuine mobile-class,
tile-based hardware.

### Rules

- **All `references/rules/adreno/*` rules apply directly** — GMEM load/store avoidance,
  LRZ, `QCOM_shading_rate`, on-tile MSAA resolve. WoA is real Adreno silicon.
- **Prefer the Vulkan ANGLE backend on WoA** — it maps most faithfully onto the
  Adreno Vulkan driver, so TBDR bandwidth optimizations behave as on Android.
- **Do not assume x86 emulation performance reflects native** — test GLES/GPU
  work in a native ARM64 build, not under x64 emulation.

---

## 3. Android GLES development *on* a Windows host

Most teams write Android GLES apps on Windows machines. The host toolchain
matters even though the target is Android.

### Rules

- **Cross-compile with the Android NDK toolchain** (`android.toolchain.cmake` or
  Gradle's `externalNativeBuild`). Set `ANDROID_ABI` (e.g. `arm64-v8a`) and
  `ANDROID_PLATFORM` to match the device.
- **The Android Emulator GPU is host-backed** (it renders through the host
  driver / ANGLE / SwiftShader). Use it for **functional** testing only —
  **never trust emulator timings** for TBDR bandwidth or fill-rate tuning. Those
  numbers are meaningful only on real mobile silicon.
- **`SwiftShader` (CPU) fallback** exists when the host has no usable GPU; it is
  correctness-only and extremely slow — never a performance reference.
- **Keep TBDR optimizations in the code even though the host is immediate-mode.**
  `glInvalidateFramebuffer`, clear-at-pass-start, and MSAA-resolve-on-tile are
  no-ops or cheap on desktop GPUs but critical on the Adreno/Mali target — they
  do no harm on Windows and must not be `#ifdef`-ed out for the host build.

---

## 4. Toolchain (Visual Studio / CMake / vcpkg)

### Rules

- **Acquire ANGLE via a package manager**, e.g. `vcpkg install angle`, rather
  than hand-copying DLLs; this keeps `libEGL` / `libGLESv2` versioned and
  discoverable by CMake `find_package`.
- **Copy `libEGL.dll` and `libGLESv2.dll` next to the executable** as a post-build
  step; ANGLE is loaded at runtime and must sit on the DLL search path.
- **Use a multi-config generator (Visual Studio)** deliberately: pick Debug vs.
  Release ANGLE binaries to match, and prefer the D3D11 debug layer only in
  Debug builds.
- **Do not link `opengl32.lib`** for a GLES target — that pulls in desktop GL.

```cmake
# CMake sketch: link ANGLE, stage its DLLs beside the binary.
find_package(unofficial-angle CONFIG REQUIRED)
target_link_libraries(app PRIVATE
    unofficial::angle::libEGL
    unofficial::angle::libGLESv2)

add_custom_command(TARGET app POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        $<TARGET_FILE:unofficial::angle::libEGL>
        $<TARGET_FILE:unofficial::angle::libGLESv2>
        $<TARGET_FILE_DIR:app>)
```

---

## Review checklist

- [ ] GLES obtained through ANGLE (`libEGL`/`libGLESv2`), **not** WGL/`opengl32`.
- [ ] ANGLE backend pinned explicitly (D3D11 on desktop, Vulkan on WoA).
- [ ] GLES version verified at runtime after context creation.
- [ ] Emulator/host used for correctness only; perf measured on real device.
- [ ] TBDR/Adreno optimizations preserved (not stripped for the Windows build).
- [ ] ANGLE DLLs staged next to the executable; no `opengl32.lib` linkage.
