# Platform and backend matrix (W2 / C10)

This is a **test plan and capability decision table**, not a claim that these devices ran this repository. No phone, Windows-on-Arm host or Vivante board was available for this implementation. Device results remain `BLOCKED_BY_HARDWARE` until a raw snapshot and logs are attached.

| Path | Creation / identity evidence | Mandatory independent probes | Failure and fallback |
|---|---|---|---|
| Android vendor GLES | EGL-created context; OS/API/build + GL/EGL strings | Version, extensions, entries, FBO formats, limits, native window generation | Recreate surface on BAD_SURFACE; recreate context/share-group resources on CONTEXT_LOST; negotiate supported version |
| Android ANGLE | Controlled deployment per [ANGLE setup](https://github.com/google/angle/blob/main/doc/DevSetupAndroid.md), recorded revision and backend | Re-query all extensions, external-image formats, EGL configs and shader behavior; do not copy native-driver snapshot | Restart renderer with supported native GLES when product policy allows; no in-place migration of GL object names |
| Windows on Arm | Actual architecture, EGL implementation and renderer; no assumption of Adreno | Native GLES vs ANGLE backend, architecture-compatible binaries, display surface configs | Known-good supported backend; preserve distinct caches keyed by implementation and driver |
| Embedded Linux / Mesa | EGL platform (Wayland/X11/GBM/surfaceless), Mesa and kernel driver, GPU revision | Native display/window lifecycle, extension entry points, buffer import format/modifier pairs | Supported platform and RGBA staging path; headless correctness is not compositor validation |
| Software GLES / emulator | Record llvmpipe/SwiftShader/emulator identity explicitly | Useful for API/shader/FBO readback correctness only | **Never** accept as mobile bandwidth, power, thermal or presentation evidence |

## Selection algorithm

1. Decide product requirements (API floor, external/protected media, color output, memory budget), not a fashionable backend name.
2. Enumerate *available* supported paths; create one; collect `CapabilitySnapshot` after `eglMakeCurrent` succeeds.
3. Test required formats using small real FBO/import probes; version and non-null entry alone do not prove a supported operation.
4. If requirements fail, release every object belonging to this context/display before selecting the next path. Never reuse cached GL names across backend switches.
5. Gate performance preference on same-scene target-device A/B data. [Android's Vulkan guidance](https://developer.android.com/games/develop/vulkan/overview) is platform strategy, not proof that a particular GLES extension or backend is available.
6. Log the reason for a fallback; unknown backend stays `null` with evidence, rather than guessing from OS/SoC.

## Lifecycle acceptance matrix (C03 / C04)

| Trigger | Preserve | Invalidate / rebuild | Acceptance and negative check |
|---|---|---|---|
| Pause/background | CPU asset descriptions; context only if actually retained | Stop submitting to absent window | Resume without stale window access; pause is not automatically context loss |
| Surface destroyed | Context resources if context survives | Unbind and destroy surface, clear native-window reference | New surface + make-current + viewport; no draw to old generation |
| `EGL_BAD_SURFACE` | Context unless another failure proves loss | Surface/config/window validity | One bounded recreation attempt; do not delete all textures solely due to this code |
| `EGL_CONTEXT_LOST` | CPU assets | Context, share-group resources, VAO/FBO local state, outstanding sync handles | Recreate supported context, upload assets, refresh snapshot; no fictitious `APP_CMD_CONTEXT_LOST` event |
| Resize/orientation | Context and reusable assets | Viewport/scissor/projection and size-dependent targets | Nonzero dimensions; recheck FBO completeness; no old-size blits |
| Shared upload thread | Shared texture + CPU ownership metadata | Per-context bindings/VAOs/FBOs remain local | Producer upload → fence → flush → CPU-safe publish; consumer server wait → bind; fence lifetime until wait queued |
| Driver/backend update | Portable CPU assets only | Context/share group, programs/binaries, capability and performance caches | Full restart; cache keyed by driver/backend/source hash; no cross-driver binary trust |

Review [EGL 1.5 specification](https://registry.khronos.org/EGL/specs/eglspec.1.5.pdf) and [Android native-app glue commands](https://developer.android.com/ndk/reference/group/native-activity) for actual events and error handling. Android version or Play policy requirements are not GPU feature detection.
