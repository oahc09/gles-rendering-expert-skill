# W1/W2 system lab (candidate)

## Build and run

`validate.py --ndk /official/android-ndk-r27 --jdk /jdk21 --android-jar /sdk/platforms/android-35/android.jar --output report.json` compiles actual C++17 and Java. For non-system Mesa development headers set `GLES_SDK_ROOT`. It executes software EGL pbuffers, **not** Android binaries. Seven checks are source compile/link or host runtime. There are no fabricated SDK headers.

Android app: `gradle -p examples/system_android :app:assembleDebug`, SDK35/NDK27.0.12077973/CMake3.22.1, minAPI26. Build dependencies use standard repositories. No Gradle wrapper binary or dependencies are vendored. This project's `:app:assembleDebug` was attempted in the current environment and failed resolving Android Gradle Plugin8.7.3 from the standard repositories (raw log/exit archived). **No APK was produced or executed**. Do not change security/proxy settings to bypass a blocked build.

With an authorized physical target and built APK:
```
adb install app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n org.example.systemlab/.MultiSurfaceActivity --ei surfaces 4 --ez workers true
```
`surfaces=2` is the default, `workers=false` uses one scheduler. Per-surface workers serialize native EGL sections and unbind before another owner enters; this is not a parallel GPU-performance design. Each frame queries resized dimensions. Pause removes pending callbacks; synchronous native detach joins in-flight rendering before SurfaceHolder destruction returns. Registry IDs never alias new surfaces. Display lease only covers cooperating instances in this library, not arbitrary third-party EGL users.

`multi_surface_host.cpp` performs actual 4-pbuffer rendering with shared immutable texture, context-local VAOs, interleaved remove/recreate, pause, controlled group rebuild, four scheduler threads, two simultaneous independent share groups and retired-surface isolation. Seven resource generations are deliberately recreated; this does **not** simulate or certify a real GPU reset. A retired surface remains retired across group rebuild until explicit detach/new attach. A genuine EGL_CONTEXT_LOST discards stale names rather than deleting them in replacement contexts.

## Cross-API CLI

Compile `interop_roundtrip.cpp` using the NDK API26 C++ compiler with `-lEGL -lGLESv3 -lvulkan -landroid -Wl,-z,max-page-size=16384`; Vulkan1.1 commands are loaded dynamically. Runtime needs Android API26+, GLES3, Vulkan1.1, the explicitly queried AHB/foreign-queue/SYNC_FD features, EGL native image/fence/wait and GL_OES_EGL_image.

The owned RGBA8 AHB is cleared red by Vulkan, released in GENERAL to FOREIGN, and a SYNC_FD is exported. GLES waits then validates all256 red pixels, clears green and exports a native fence. Vulkan temporarily imports it, acquires FOREIGN ownership, copies256 green pixels to HOST_VISIBLE|HOST_COHERENT memory and validates after completion. Every image usage is checked with the physical-device format query. No `GL_EXT_memory_object_fd` or `GL_EXT_semaphore_fd` assumption is used. No protected resource enters this readback lab.

Exit0=actual pixel roundtrip passed;77=unsupported capability/format and **no interop acceptance**;1=runtime validation failure. Unsupported path returns to the caller: use the existing CPU-staging AHB example or GLES-only application deliberately, not an unsynchronized implicit fallback. Staging copies add transfer/CPU costs; no timing gain is claimed.

### Ownership table

| Object | Owner / completion / destruction |
|---|---|
|AHB|Lab allocation reference; Vulkan successful import acquires its own reference; release ours after GL image and Vulkan memory are gone|
|EGLImage/texture/FBO|Lab's live EGL context; GL finish before deletion; never reuse after group loss|
|Vulkan image/memory|Dedicated imported image; queue idle before image then memory destruction|
|Vulkan export SYNC_FD|Owned fd until EGL createSync call transfers it; successful export `-1` means already signaled|
|EGL export native fd|Negative is export failure; successful Vulkan import transfers ownership, failed import leaves RAII fd owned|
|Semaphores/commands|Device-owned, queue completion before destroy/reset; temporary imported SYNC_FD payload|
|Context/surface/display|This CLI owns all; multi-surface library uses cooperative process display lease|

Targets that lack coherent readback memory return unsupported rather than pretending invalidation is unnecessary for noncoherent memory. All waits have explicit command/completion boundaries; no concurrent GPU writer is permitted.

## Physical acceptance procedure (NOT_RUN)

Record DeviceLab identity, APIs/extensions/formats and command hashes; run CLI normal and missing-extension rejection; repeat2/4Surface single/worker modes while resizing, screen locking, backgrounding, recreating Activities and controlled reset. Capture Perfetto BufferQueue/SurfaceFlinger/frame scheduling on the **same target**. Check native fd counts and resource lifetime under failure injection. Real driver context loss requires a legitimate target-specific reproduction; the UI rebuild button is only a controlled rebuild. Do not infer Vulkan pre-rotation behavior for GLES.

Sources: [EGL native fence](https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_native_fence_sync.txt), [AHB import](https://docs.vulkan.org/refpages/latest/refpages/source/VkImportAndroidHardwareBufferInfoANDROID.html), [Vulkan semaphore fd](https://docs.vulkan.org/refpages/latest/refpages/source/VkImportSemaphoreFdInfoKHR.html), [foreign queue synchronization](https://docs.vulkan.org/spec/latest/chapters/synchronization.html), [Surface destruction contract](https://developer.android.com/reference/android/view/SurfaceHolder.Callback).
