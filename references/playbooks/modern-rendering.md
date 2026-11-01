# Modern GLES engineering scenarios (W4)

These are capability-gated integration recipes. Existing examples are linked as source, **not claimed complete Android applications**. The EGL harness is a runnable host correctness probe; real Android HDR, AHardwareBuffer producer/import, Swappy presentation and mobile performance acceptance remain `BLOCKED_BY_HARDWARE`. A fragment below is integration code only when its surrounding app/surface/media producer is explicitly required.

## 1. HDR and wide color output

**Class:** Extension + platform, not GLES core. **Requirements:** actual display HDR/WCG capability, compatible compositor/window color mode, EGL config channels and colorspace extension for the requested transfer function. WCG, floating-point render targets, HDR processing and HDR display output are four distinct capabilities. Android API 26 WCG support does not imply every display is wide gamut.

**Pipeline:** linear scene → floating target if supported → exposure/tone mapping → gamut transform → exactly one output transfer encoding. Request and check the surface color space explicitly. A complete RGBA16F FBO does not prove HDR display support. Check float-target renderability, filtering and blending separately. Never treat an unsupported colorspace `eglCreateWindowSurface` failure as success.

**Code routes:** [HDR card](../cards/20-hdr-and-display.md), [offscreen pipeline](../examples/offscreen_pipeline.cpp). Core fallback target allocation after a valid GLES 3 context:

```cpp
// Integration fragment: context current; texture/fbo are owned GLuint handles.
glBindTexture(GL_TEXTURE_2D, texture);
glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0,
             GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
glBindFramebuffer(GL_FRAMEBUFFER, fbo);
glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                       GL_TEXTURE_2D, texture, 0);
// Treat non-COMPLETE as a real allocation/config failure, not an HDR fallback success.
const bool complete = glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE;
```

**Fallback:** gamut-map and tone-map into RGBA8 SDR sRGB; do not merely clamp HDR scene values. **Visual test:** grayscale/near-black/highlight ramps, saturated patches and UI compositing; detect double gamma and clipped highlights. **Measure:** bytes per attachment, composition memory, GPU pass time and presentation on the same display; no unmeasured speed claims. **Source:** [Android WCG](https://developer.android.com/training/wide-color-gamut), [EGL colorspaces](https://registry.khronos.org/EGL/extensions/EXT/EGL_EXT_gl_colorspace_bt2020_pq.txt).

## 2. AHardwareBuffer / EGLImage / external video

**Class:** Android + EGL/GL extensions. **Requirements:** Android API 26 AHardwareBuffer API, advertised EGL_ANDROID_get_native_client_buffer plus dependency extensions, callable entries, supported buffer format/usage. External ESSL 3 sampling needs `GL_OES_EGL_image_external_essl3` in addition to its dependencies; `GL_TEXTURE_EXTERNAL_OES` is not a mandatory target for every image type.

**Flow:** retain producer buffer → wait/import producer acquire fence using an appropriate supported native-fence path → convert AHardwareBuffer to EGLClientBuffer → create EGLImage → bind supported texture target → sample → publish consumer completion/release fence → release resources only when users finish. A reference count does not replace GPU synchronization. Protected/non-CPU-readable content must not silently use CPU readback.

**Code routes:** [video pipeline](../examples/video_texture_pipeline.cpp), [video card](../cards/17-android-video-interoperability.md). ESSL 3 fragment interface when capability checks pass:

```glsl
#version 300 es
#extension GL_OES_EGL_image_external_essl3 : require
precision mediump float;
uniform samplerExternalOES frame;
in vec2 uv;
layout(location=0) out vec4 color;
void main() { color = texture(frame, uv); }
```

**Fallback:** CPU-readable unprotected YUV → explicit conversion respecting crop/stride/color range → RGBA8 ordinary 2D texture upload. Reject unsupported protected path visibly. **Visual test:** color bars, limited/full range, rotation/crop, rapidly numbered frames, producer/consumer overlap; check leaks through repeated startup/teardown. **Measure:** copy count, end-to-end frame latency, import time and memory; “zero copy” requires actual platform evidence. **Sources:** [native-client-buffer](https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_get_native_client_buffer.txt), [external ESSL3](https://registry.khronos.org/OpenGL/extensions/OES/OES_EGL_image_external_essl3.txt), [native fence sync](https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_native_fence_sync.txt).

## 3. PBO texture streaming

**Class:** GLES 3.0 core. **Requirements:** unpack-buffer support and capacity, correct row stride/alignment; synchronization separate from transfer submission.

**Flow:** choose free ring slot → wait/test previous fence before reuse → map/upload bounded bytes → unmap → `glTexSubImage2D` with byte offset while unpack PBO bound → fence after transfer → publish completion. Do not pass a CPU pointer while a PBO is bound; it is interpreted as an offset. Check failed map/unmap and buffer sizes before issuing transfer.

**Code:** [PBO streaming example](../examples/pbo_streaming_upload.cpp). **Fallback:** unbind `GL_PIXEL_UNPACK_BUFFER`; upload from live CPU memory directly. For overload, drop an obsolete video frame or use bounded backpressure rather than overwriting in-flight bytes. **Visual test:** distinct sequence number/color in every frame, odd-width input, ring wrap, stalled consumer, partial subrectangle. **Measure:** CPU copy/map/upload stalls, GPU transfer time, end-to-end latency; ring depth trades memory and latency. **Source:** [GLES 3.0 specification](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf). A PBO is not a guarantee of asynchronous transfer or speedup.

## 4. Frame pacing

**Class:** Android integration recommendation, not new GLES semantics. **Requirements:** supported Android Frame Pacing library version and valid JNI/native-window lifecycle, refresh-rate awareness. Swappy APIs are not GL calls.

**Integration:** [frame pacing card](../cards/19-frame-pacing.md). Initialize Swappy for the Activity; register the current native window; in the render loop use `SwappyGL_swap(display, surface)` instead of also calling `eglSwapBuffers`. Update for window lifecycle/refresh changes; release library state on shutdown. Keep app simulation time independent from swap duration.

**Fallback:** platform vsync-aware scheduling plus normal EGL swap, record limitations; avoid busy-spin or arbitrary fixed sleeps. **Visual test:** camera pan and input event to displayed-frame timestamps across 60/90/120 Hz where available, background/foreground and resize. **Measure:** presentation intervals, missed deadlines, CPU/GPU time, queue latency and thermals; average FPS alone can conceal bad pacing. **Source:** [official GLES integration](https://developer.android.com/games/sdk/frame-pacing/opengl). A host pbuffer cannot validate display pacing.

## 5. Shader compilation hitches

**Class:** core program compilation/binaries plus optional `GL_KHR_parallel_shader_compile`. **Requirements:** actual extension and entry points; binary formats and driver identity queried at runtime. Driver binary caches are implementation-specific, not portable assets.

**Flow:** compile needed variants during loading; check compile and link logs. If parallel compile supported, request compiler threads and poll completion before retrieving expensive status. Binary cache key includes source/defines, program inputs, GL_VENDOR/RENDERER/VERSION, binary format and backend; after `glProgramBinary`, check link success and recompile from source on failure. Cache failure must not brick startup.

**Code integration fragment:**

```cpp
// GLES 3.0 current context, valid linked-source program alternative available.
glProgramBinary(program, format, bytes, byteCount);
GLint linked = GL_FALSE;
glGetProgramiv(program, GL_LINK_STATUS, &linked);
if (linked != GL_TRUE) { /* discard cache; compile and link original source */ }
```

**Fallback:** source compile at controlled loading boundary; deduplicate only equivalent variants. **Visual test:** cold/warm cache, corrupt binary, changed driver key, extension absent, invalid shader and first-use draw. **Measure:** compile/link/first-draw CPU durations and frame-time tails separately; shared worker context alone does not ensure stutter-free driver compilation. **Sources:** [KHR parallel compile](https://registry.khronos.org/OpenGL/extensions/KHR/KHR_parallel_shader_compile.txt), [GLES 3.0](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf).

## 6. Mobile postprocessing composition

**Class:** core ping-pong FBOs; float targets/fetch/PLS are separate conditional features. **Requirements:** framebuffer completeness, matching dimensions, actual read/write dependencies, format filtering support and sampler limits.

**Flow:** scene target → downsample → blur ping-pong → composite/tone-map into output. Reuse targets only after final consumer. Invalidate dead depth/stencil after its last use, never a color target still sampled downstream. Combine passes only if math/order/precision and feedback legality are preserved. Sampling a texture while rendering into the same attached image is not a portable substitute for framebuffer fetch.

**Code:** [offscreen pipeline](../examples/offscreen_pipeline.cpp), [postprocessing card](../cards/23-post-processing-chain.md). **Fallback:** RGBA8, fewer/downscaled bloom levels, core FBO ping-pong; disable nonessential effects under measured budget pressure. **Visual test:** impulses, bright highlight bloom, edges and alpha; resize targets atomically and recheck completeness. **Measure:** passes/target switches, external load/store, attachment bytes and GPU time; merging may increase register pressure or sampled bandwidth. **Sources:** [GLES specification](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf), exact selected fetch/PLS extension from [registry](https://registry.khronos.org/OpenGL/index_es.php).
