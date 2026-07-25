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

> **Important**: The `EGL_ANGLE_*` tokens are defined by ANGLE's own headers, NOT by
> the standard Khronos `eglext.h` (e.g. from the `opengl-registry` vcpkg package).
> When building with Khronos-only headers you **must** supply the values yourself.

```cpp
#include <EGL/egl.h>
#include <EGL/eglext.h>

// --------------------------------------------------------------------------
// ANGLE extension tokens — not in standard Khronos eglext.h.
// Values from ANGLE source: include/EGL/eglext_angle.h
// --------------------------------------------------------------------------
#ifndef EGL_ANGLE_platform_angle
#define EGL_ANGLE_platform_angle 1
#define EGL_PLATFORM_ANGLE_ANGLE                   0x3202
#define EGL_PLATFORM_ANGLE_TYPE_ANGLE              0x3203
#define EGL_PLATFORM_ANGLE_TYPE_D3D11_ANGLE        0x3208
#define EGL_PLATFORM_ANGLE_TYPE_VULKAN_ANGLE       0x3450
#define EGL_PLATFORM_ANGLE_TYPE_OPENGL_ANGLE       0x320D
#endif

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

// Request a GLES 3.x context (EGL_CONTEXT_CLIENT_VERSION for EGL 1.4 compat).
const EGLint ctxAttribs[] = { EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE };
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

- **Copy `libEGL.dll` and `libGLESv2.dll` next to the executable** as a post-build
  step; ANGLE is loaded at runtime and must sit on the DLL search path.
- **Use a multi-config generator (Visual Studio)** deliberately: pick Debug vs.
  Release ANGLE binaries to match, and prefer the D3D11 debug layer only in
  Debug builds.
- **Do not link `opengl32.lib`** for a GLES target — that pulls in desktop GL.

### Acquiring ANGLE binaries

Two supported approaches (choose one):

#### Option A: Extract pre-built DLLs from Chrome/Edge (fastest)

Chrome and Edge ship conformant ANGLE builds. Copy the DLLs from the browser
installation directory:

```powershell
# Locate Edge's ANGLE DLLs (example; version folder varies):
$edgePath = "$env:ProgramFiles(x86)\Microsoft\Edge\Application\<version>"
copy "$edgePath\libEGL.dll"    .\third_party\angle\
copy "$edgePath\libGLESv2.dll" .\third_party\angle\
```

Then generate import libraries so MSVC's linker can resolve symbols at link time:

```bat
REM --- Generate .lib from .dll (Developer Command Prompt / x64 Native Tools) ---
dumpbin /exports libEGL.dll    > libEGL.exports.txt
dumpbin /exports libGLESv2.dll > libGLESv2.exports.txt

REM Create .def files (LIBRARY name + EXPORTS section):
REM   LIBRARY libEGL
REM   EXPORTS
REM       eglGetDisplay
REM       eglInitialize
REM       ...

lib /def:libEGL.def    /out:libEGL.lib    /machine:x64
lib /def:libGLESv2.def /out:libGLESv2.lib /machine:x64
```

> **Tip**: The `gendef` tool (from MinGW-w64, available via MSYS2) can auto-generate
> `.def` from a DLL in one step: `gendef libEGL.dll` → `libEGL.def`.

#### Option B: vcpkg (reproducible, but slow)

```powershell
vcpkg install angle:x64-windows
```

> **Warning**: ANGLE's vcpkg port pulls Chromium build infrastructure. Initial build
> may take 30+ minutes and requires ~20 GB of disk. Network or toolchain version
> mismatches can cause failures. Use Option A for rapid prototyping; use vcpkg for
> CI/reproducible builds.

### CMake integration

```cmake
# If using vcpkg:
find_package(unofficial-angle CONFIG REQUIRED)
target_link_libraries(app PRIVATE
    unofficial::angle::libEGL
    unofficial::angle::libGLESv2)

# If using pre-built DLLs with hand-crafted .lib:
target_include_directories(app PRIVATE ${CMAKE_SOURCE_DIR}/third_party/angle/include)
target_link_libraries(app PRIVATE
    ${CMAKE_SOURCE_DIR}/third_party/angle/libEGL.lib
    ${CMAKE_SOURCE_DIR}/third_party/angle/libGLESv2.lib)

# Either way — stage DLLs beside the binary:
add_custom_command(TARGET app POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${ANGLE_DLL_DIR}/libEGL.dll
        ${ANGLE_DLL_DIR}/libGLESv2.dll
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
