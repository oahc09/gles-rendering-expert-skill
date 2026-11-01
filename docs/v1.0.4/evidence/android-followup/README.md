# Android implementation follow-up

This directory records the post-Draft-PR implementation and validation of the
previously missing explicit AHardwareBuffer import and HDR output paths. Earlier
candidate records are historical, not deleted or retroactively promoted to PASS.

Primary API contracts checked on 2026-11-01:

- [Android NDK AHardwareBuffer](https://developer.android.com/ndk/reference/group/a-hardware-buffer): API 26 allocation, format/usage/stride, reference ownership and synchronous `unlock(buffer, nullptr)` completion. The deterministic CPU producer is not a camera decoder, asynchronous fence importer, or zero-copy performance measurement.
- [EGL_ANDROID_get_native_client_buffer](https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_get_native_client_buffer.txt): exact extension and entry-point checks; format support is implementation-specific.
- [EGL_ANDROID_image_native_buffer](https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_image_native_buffer.txt): `EGL_NATIVE_BUFFER_ANDROID` creation uses `EGL_NO_CONTEXT`; allocation does not imply successful image import.
- [EGL_EXT_gl_colorspace_bt2020](https://registry.khronos.org/EGL/extensions/EXT/EGL_EXT_gl_colorspace_bt2020_linear.txt): the combined specification defines PQ/HLG/linear tokens. PQ encoding belongs in the application; EGL config/color-space compatibility must be tested by surface creation, not guessed from the extension string.
- [Android wide color](https://developer.android.com/training/wide-color-gamut): display capability, requested mode, EGL configuration and actual presentation are different evidence levels.

Compilation is not device execution. Even a successful Android-target native link
and Java compilation cannot prove gralloc import support, HDR compositor/display
behavior, Surface lifecycle correctness, pixel goldens or physical-device performance.
The v1.0.3 and v1.0.4 release gates remain blocked.

Actual build commands, toolchain provenance and the Gradle networking blocker are
recorded in [TOOLCHAIN.md](TOOLCHAIN.md). `source-compile.json` contains final source
hashes and 9 compile/link check groups. Earlier candidate no-toolchain statements
are not the final follow-up status. Native target binaries were linked, not executed.
