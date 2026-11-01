# Android end-to-end source cases — target NOT_RUN

Two separate, pinned Gradle app modules exercise actual Android lifecycle APIs.
No Android SDK/NDK, Gradle, Java target toolchain or device is available in this
execution environment. **These sources have NOT been compiled or run on Android.**
The structural tests below do not substitute for an APK build or device validation.
Neither app claims AHardwareBuffer native import, HDR display output or real GPU
performance acceptance.

## Build on an authorized Android development environment

Install JDK17, Gradle8.9, Android SDK platform35/build-tools and platform-tools.
Android Gradle Plugin8.7.3 is pinned in the root build file; repositories are Google
and Maven Central. No binary Gradle wrapper is bundled or downloaded automatically.

```sh
cd examples/android_cases
# Set ANDROID_HOME to your installed SDK, or add untracked local.properties.
gradle :wallpaper:assembleDebug :surfacevideo:assembleDebug
adb install -r wallpaper/build/outputs/apk/debug/wallpaper-debug.apk
adb install -r surfacevideo/build/outputs/apk/debug/surfacevideo-debug.apk
adb shell am start -n org.example.gleslab.surfacevideo/org.example.gleslab.ExternalSurfaceActivity
```

Enable the wallpaper through the system wallpaper picker, selecting **GLES lifecycle
wallpaper**. User confirmation remains required; the code does not change wallpaper
or global graphics settings automatically.

## Case A: touch-driven live wallpaper / multiple Engine ownership

`IslandWallpaper` creates one HandlerThread/EGL owner per WallpaperService Engine.
Preview and actual home-screen instances do not share object names. Surface attach,
resize, destruction, visibility and touch are serialized onto that owner. Surface
destruction waits for an owner acknowledgement after cancelling frame callbacks
and releasing EGLSurface, or waits until the owner has actually exited; interruption
is preserved without returning early. Calls from the owner execute directly, and
rejected Handler posts wait for thread exit rather than assuming cleanup happened. Display
callbacks use Choreographer; invisibility suspends scheduling. This is vsync-driven
submission, **not evidence of optimal frame pacing or a replacement for measured
Swappy integration**.

The surface is borrowed from SurfaceHolder (never released by this renderer).
EGL_BAD_SURFACE/BAD_NATIVE_WINDOW waits for a new window; EGL_CONTEXT_LOST discards
old GL names, rebuilds context and shaders, and preserves only CPU state. No invented
APP_CMD_CONTEXT_LOST event is used. Errors are logged and retries are bounded by
surface/frame events rather than a busy loop. Output is explicit SDR RGBA8.

## Case B: Surface producer → SurfaceTexture/external texture → GLSurfaceView

`ExternalSurfaceActivity` creates a deterministic Canvas producer Surface and consumes
its frames through GL_TEXTURE_EXTERNAL_OES. Using a generated producer avoids camera
permission/device availability while exercising the real Android queue/texture path.
The external ESSL3 extension is checked by exact-token enumeration; absent support
shows a clear-color fallback, never an illegal sampler or claimed imported frame.
SurfaceTexture.updateTexImage runs only on the GL owner, with its supplied transform
matrix, and Android's SurfaceTexture synchronization is used rather than invented
native fence ownership. This is **not an explicit AHardwareBuffer/EGLImage importer**.

Choreographer drives the UI producer; OnFrameAvailable schedules rendering on the GL
thread. Pause stops production first and queues resource release before pausing the
view. Context preservation is disabled to exercise recreation on resume. Display HDR
and wide-color capabilities are logged, but the chosen EGL output remains SDR RGBA8;
capable hardware is not confused with an HDR-configured surface.

## Device acceptance and goldens still required

1. Build both APKs; retain Gradle/JDK/SDK versions and compile logs.
2. Native driver and (only when device policy permits) package-scoped ANGLE Vulkan
   backend: record actual GL/EGL strings/extensions and controlled backend selection.
3. Wallpaper preview+home simultaneously; resize/rotate; touch; hide/show; screen-off;
   app lifecycle; repeated context creation/destruction. Watch GL/EGL errors and leaks.
4. External Surface: moving cyan rectangle and white label must remain correctly
   oriented without stale frames; pause/resume 100 times; rotate; surface recreation.
5. Capture per-device screenshots as **device goldens after review**, not from desktop
   GL. No Android golden images exist in this repository yet: `NOT_RUN`.
6. Record CPU/GPU frame timing and thermal state before evaluating pacing, HDR or
   native/ANGLE performance. Do not use source inspection as a passing measurement.

Primary documentation: [WallpaperService.Engine](https://developer.android.com/reference/android/service/wallpaper/WallpaperService.Engine),
[SurfaceTexture](https://developer.android.com/reference/android/graphics/SurfaceTexture),
[GLSurfaceView](https://developer.android.com/reference/android/opengl/GLSurfaceView),
[Choreographer](https://developer.android.com/reference/android/view/Choreographer),
[EGL14](https://developer.android.com/reference/android/opengl/EGL14).

## Available local checks

`python3 -m unittest discover -s examples/android_cases -p "test_*.py" -v` runs ten structural safeguards only. `python3 examples/android_cases/validate_shaders.py` actually compiles and links the two embedded GLSL pairs using glslang; it does not compile Java or prove Android lifecycle behavior. `target-status.json` retains those distinctions.
