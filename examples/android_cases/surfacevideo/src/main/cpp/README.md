# Native AHardwareBuffer import (Android API26+)

This module adds an actual NDK/JNI path to the `surfacevideo` case, selected by:

```sh
adb shell am start -n org.example.gleslab.surfacevideo/org.example.gleslab.ExternalSurfaceActivity --ez ahb true
```

Default mode remains the SurfaceTexture producer. If the native library, required
extensions/entry points, allocation/import or deterministic pixel check fails, the
Java renderer logs the reason and falls back to that existing path. No extension is
inferred from GPU renderer substrings.

## Ownership and synchronization

| Object | Contract |
|---|---|
| EGLDisplay/EGLContext | Borrowed current GLSurfaceView owner; never terminated/destroyed here |
| AHardwareBuffer | Owned allocation reference, RGBA8 single layer; CPU_WRITE_OFTEN + GPU_SAMPLED_IMAGE + GPU_FRAMEBUFFER |
| EGLClientBuffer | Borrowed representation returned by eglGetNativeClientBufferANDROID; never freed or truncated |
| EGLImageKHR | Owned image created with EGL_NO_CONTEXT + EGL_NATIVE_BUFFER_ANDROID |
| GL_TEXTURE_2D | Owned texture backed by the image, no glTexImage redefinition |
| Java `long` | Private owner pointer, consumed exactly once by helper release, then reset to zero |

CPU producer writes a fixed four-quadrant 16×16 test image using the **returned pixel
stride**, not width×4 as an assumed row pitch. Allocation is fresh and has no prior
GPU producer; lock uses fence=-1 and CPU-only lock usage. Unlock passes nullptr,
which the NDK defines as synchronous completion. There is no outstanding CPU fence
FD to leak or close. This is deliberately blocking correctness code, not an async
pipeline or zero-bandwidth claim.

After image import the texture is attached to a temporary FBO and read back. All
RGBA bytes must equal the CPU pattern; mismatch rejects the AHB mode rather than
silently adjusting a flipped/converted result. PACK buffer/pixel-store and read/draw
FBO bindings are saved/restored. The screen path uses an ordinary sampler2D; it does
not need the external-sampler extension used by the separate SurfaceTexture path.

For normal cleanup on the original current context, glFinish waits for submitted
consumers, then texture → image → allocation-reference release occurs. On confirmed
GLSurfaceView context recreation, old GL names are **never deleted in the new context**;
the old image/allocation references are released separately. EGLImage/GL siblings
retain storage according to their own lifetimes; destroying the image does not
retroactively invalidate an existing texture sibling. Failed EGL image cleanup is
logged. This path is not a generic cross-context resource manager.

## Build and actual evidence

The app pins NDK27.0.12077973, CMake3.22.1 and c++_shared. CMake requests strict C++17
warnings, no unresolved symbols and 16KiB max-page-size alignment. AGP packages the
shared STL when building the actual APK; do not copy the standalone .so without its
runtime dependency.

```sh
python3 examples/android_cases/surfacevideo/src/main/cpp/cross_compile.py \
  --ndk /path/to/android-ndk-r27 --output /tmp/ahb-cross-compile.json
```

`cross-compile-result.json` records an **actual arm64 Android API26 shared-library
compile/link and ELF LOAD alignment checks (both sample and bundled libc++_shared.so)** with the official NDK. No generated
binary or toolchain is shipped in this repository. This is not an APK build, runtime
AHB import, device screenshot, 16KiB-device certification or performance result.
Device import/readback remains NOT_RUN until the Java log is produced by a real
device. Other ABI configurations remain NOT_RUN.

Official NDK archive used: `https://dl.google.com/android/repository/android-ndk-r27-linux.zip`,
663957918 bytes. SHA1 `5e5cd517bdb98d7e0faf2c494a3041291e71bdcc` matched Google's SDK
repository metadata. The implementation uses API26 calls, not API29-only lockPlanes
or isSupported as an undeclared minimum requirement.

## Primary contracts

- [NDK AHardwareBuffer](https://developer.android.com/ndk/reference/group/a-hardware-buffer): allocation references, CPU lock usage, returned stride, synchronous null-fence unlock.
- [EGL_ANDROID_get_native_client_buffer](https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_get_native_client_buffer.txt): client-buffer conversion and lifetime.
- [EGL_ANDROID_image_native_buffer](https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_image_native_buffer.txt): EGL_NO_CONTEXT import and implementation-specific format support.
- [GL_OES_EGL_image](https://registry.khronos.org/OpenGL/extensions/OES/OES_EGL_image.txt): imported image/texture sibling semantics.
