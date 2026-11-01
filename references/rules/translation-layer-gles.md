# GLES over Translation Layers — ANGLE, MobileGL, SwiftShader

> Distilled from the ANGLE behavior notes (v1.0.1 Windows work) and the
> [MobileGL](https://github.com/MobileGL-Dev/MobileGL) project (a GL→Vulkan /
> GL→GLES translation layer targeting desktop GL 4.2 core, incomplete).
> Translation layers are invaluable for testing on host, but they *translate*,
> not *emulate GPU architecture* — treat what you measure there with care.

---

## 1. What a translation layer is (and is not)

| Layer | Translates | Backend | Status |
|:---|:---|:---|:---|
| **ANGLE** | GLES 2.0/3.0/3.1 | D3D11 / Vulkan / desktop GL | mature, used by Chrome/Edge |
| **MobileGL** | desktop GL 4.2 core | Vulkan / GLES | incomplete / experimental |
| **SwiftShader** | GLES | CPU software raster | CPU fallback, very slow |

All three expose a GLES-conformant API surface; none reproduces the target
mobile GPU's TBDR bandwidth/tiling behavior.

## 2. Rules

1. **Functional testing on a translation layer is valid; performance testing
   is not.** ANGLE/SwiftShader costs differ radically from Mali/Adreno/PowerVR.
   Measure bandwidth / fill-rate on real hardware.
2. **Pin the ANGLE backend explicitly** (`EGL_ANGLE_platform_angle`) — default
   backend selection differs across machines and reproduces bugs differently.
3. **ANGLE-specific behaviors to test around**:
   - Do not assume varying precision differences are errors or universally zeroed; ES 3.00 permits them. As an engineering consistency policy, keep
     VS `out` and FS `in` precision identical.
   - Some desktop-GL habits pass on ANGLE that fail on device (e.g. relaxed
     format-type pairing); do not treat "runs on ANGLE" as spec-correct.
4. **Translation layers expose only the API they implement** — extension
   strings differ (ANGLE exposes `GL_ANGLE_*`; vendor extensions like
   `GL_QCOM_*` / `GL_EXT_shader_pixel_local_storage` are absent), so
   runtime-extension-gate every vendor path and keep fallbacks.
5. **SwiftShader is for correctness-only headless runs** (CI smoke tests);
   never use it for perf, and expect very slow execution.
6. **MobileGL is experimental** — useful for research on desktop-GL→GLES/Vulkan
   translation, not for production; prefer ANGLE for anything shipping.
7. Keep an **`eglQueryString(EGL_EXTENSIONS)` / `glGetString(GL_EXTENSIONS)`
   diff tool** in the test harness so backend capability gaps are explicit,
   not discovered at runtime on device.

## 3. Host-vs-device testing matrix

| What | ANGLE host | Emulator | Real device |
|:---|:---|:---|:---|
| API correctness | ✅ good | ✅ ok | ✅ authoritative |
| Shader compile | ✅ catches syntax | ok | ✅ authoritative |
| Visual output | ok | ok | ✅ authoritative |
| Bandwidth / fill-rate | ❌ not representative | ❌ host-backed | ✅ authoritative |
| Vendor extensions | ❌ absent | partial | ✅ |

## Common pitfalls

| Pitfall | Consequence | Fix |
|:---|:---|:---|
| Trusting ANGLE perf numbers | Wrong perf conclusions | Measure on real device |
| Relying on default ANGLE backend | Machine-dependent bugs | Pin backend explicitly |
| Assuming `runs on ANGLE == spec correct` | Device-only failures | Keep spec-conformant code paths |
| Using vendor extensions on host without fallback | Host crash | Extension-gate + fallback |
| SwiftShader for perf | Garbage numbers | CPU fallback is correctness-only |
