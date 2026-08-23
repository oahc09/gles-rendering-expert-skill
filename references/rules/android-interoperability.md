# Android Interoperability — Video Textures, EGLImage & AHardwareBuffer

> Android-only integration patterns for moving camera / video / decoder frames
> into OpenGL ES with **zero CPU copies**. Everything here requires Android NDK
> and is not applicable to Windows (ANGLE) or Embedded Linux.

---

## 1. Video / Camera Texture Pipeline (`GL_OES_EGL_image_external`)

External images (camera preview, MediaCodec decoder output) cannot be uploaded
with `glTexImage2D` — they live in a vendor-private buffer format. The only
correct path is an **external OES texture** bound to an EGLImage produced by
the platform.

### Rules

1. The texture target **MUST** be `GL_TEXTURE_EXTERNAL_OES` — binding an
   external image to `GL_TEXTURE_2D` is undefined behavior on most drivers.
2. The sampler in GLSL **MUST** be `samplerExternalOES`, the shader requires
   `#extension GL_OES_EGL_image_external : require` (or
   `GL_OES_EGL_image_external_essl3` under GLSL ES 3.00), and the extension
   must be checked at runtime before use.
3. Texture wrap mode **MUST** be `GL_CLAMP_TO_EDGE` and filtering
   `GL_NEAREST` or `GL_LINEAR` (no mipmaps — external images have no mipmap
   chain; calling `glGenerateMipmap` on them is an error).
4. Update the texture content each frame with
   `glEGLImageTargetTexture2DOES(GL_TEXTURE_EXTERNAL_OES, image)` after the
   producer has released a new buffer. Re-specifying the texture with
   `glTexImage2D` detaches the EGLImage binding.
5. For **MediaCodec decoder output**, create the codec with the OES texture id
   via `AMediaCodec_createInputSurface`-style configuration (or
   `createPersistentInputSurface`), then drive frame availability through
   `SurfaceTexture` (`android.graphics.SurfaceTexture` via JNI) — call
   `updateTexImage()` on the frame's arrival before drawing.
6. **Never `glReadPixels` from an external texture** — the data is not
   linearly addressable. If a CPU copy is genuinely needed, render to a
   regular `GL_TEXTURE_2D` FBO first, then read back via PBO.

### Code pattern

```cpp
// ✅ Create external OES texture (once)
GLuint videoTex = 0;
glGenTextures(1, &videoTex);
glBindTexture(GL_TEXTURE_EXTERNAL_OES, videoTex);
glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

// Per frame: SurfaceTexture::updateTexImage() already refreshed the EGLImage
// backing this texture; just draw. No glTexImage2D / glTexSubImage2D needed.
```

Fragment shader sampling an external image:

```glsl
#version 300 es
#extension GL_OES_EGL_image_external_essl3 : require
precision mediump float;
uniform samplerExternalOES u_VideoFrame;
in vec2 v_TexCoord;
out vec4 o_Color;
void main() {
    o_Color = texture(u_VideoFrame, v_TexCoord); // YUV->RGB done by hardware
}
```

### YUV handling note
`GL_OES_EGL_image_external` performs **hardware YUV→RGB conversion** when the
producer format is YUV — do not do the conversion manually in the shader.
Only implement a manual YUV shader when consuming raw `AHardwareBuffer` planes
directly (see §3).

---

## 2. EGLImage — Cross-API / Cross-Context Buffer Sharing

`EGLImageKHR` is the generic mechanism for sharing a native buffer (gralloc
`AHardwareBuffer`, dma-buf, renderbuffer, mipmap level) across EGL contexts,
APIs (GLES ↔ Vulkan via native handles), and processes.

### Rules

1. Import a gralloc buffer with `eglCreateImageKHR(display, EGL_NO_CONTEXT,
   EGL_NATIVE_BUFFER_ANDROID, clientBuffer, attrs)` — the EGLImage must be
   destroyed with `eglDestroyImageKHR` **after** all GL textures bound to it
   are deleted, or the driver may still reference the storage.
2. One EGLImage can back multiple textures (e.g., one per context in a
   multi-thread pipeline); each texture binds it independently via
   `glEGLImageTargetTexture2DOES`.
3. EGLImages are **per-display**: an image created on one `EGLDisplay` cannot
   be used on another. For multi-display scenarios, re-import the underlying
   native buffer on each display.
4. Runtime-check `EGL_KHR_image_base` / `EGL_KHR_image` before use; on API 26+
   prefer the `AHardwareBuffer` path (§3) which wraps the same mechanism with
   stable C ABI.

---

## 3. AHardwareBuffer ↔ GLES Interop (API 26+, preferred modern path)

`AHardwareBuffer` is the NDK-native, stable replacement for raw gralloc
handles. Combined with `EGL_ANDROID_get_native_client_buffer`, it lets GLES
consume buffers produced by **any** system component (Camera2, MediaCodec,
Vulkan, another process) without JNI detours.

### Rules

1. Requires **API level 26+** and extension
   `EGL_ANDROID_get_native_client_buffer` (runtime-check both). Fall back to
   the EGLImage + gralloc path on older devices.
2. Import flow: `eglCreateNativeClientBufferANDROID` (when GLES allocates) or
   receive an `AHardwareBuffer*` → `eglGetNativeClientBufferANDROID(ahb)` →
   `eglCreateImageKHR(..., EGL_NATIVE_BUFFER_ANDROID, ...)` →
   `glEGLImageTargetTexture2DOES`.
3. **Synchronization is mandatory**: a producer writing the buffer (decoder,
   camera HAL, compute) and a GLES consumer must be ordered with
   `AHardwareBuffer_lock`/fence sync, or `glWaitSync` on an EGL fence
   (`EGL_SYNC_NATIVE_FENCE_ANDROID`). Drawing an unfinished buffer is a data
   race and renders garbage frames.
4. Keep the buffer allocation flags producer-friendly:
   `AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE | AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT`
   for render targets; add `AHARDWAREBUFFER_USAGE_CPU_READ_OFTEN` **only** if
   the CPU truly reads it (forces slower uncached layouts on some SoCs).
5. Multi-plane YUV (NV12/P010) from decoders: import **each plane** as a
   separate EGLImage/texture (`R8` for Y, `RG8` for UV) and convert in-shader
   with BT.601/BT.709 coefficients. Do not assume a single-plane layout.

### Code pattern

```cpp
// ✅ Import an AHardwareBuffer produced elsewhere (API 26+)
EGLClientBuffer clientBuffer =
    eglGetNativeClientBufferANDROID(hardwareBuffer);           // NDK C ABI
EGLint attrs[] = { EGL_IMAGE_PRESERVED_KHR, EGL_TRUE, EGL_NONE };
EGLImageKHR image = eglCreateImageKHR(display, EGL_NO_CONTEXT,
                                      EGL_NATIVE_BUFFER_ANDROID,
                                      clientBuffer, attrs);
glBindTexture(GL_TEXTURE_EXTERNAL_OES, tex);
glEGLImageTargetTexture2DOES(GL_TEXTURE_EXTERNAL_OES, image);

// Teardown order matters: texture first, then EGLImage, then AHardwareBuffer
glDeleteTextures(1, &tex);
eglDestroyImageKHR(display, image);
AHardwareBuffer_release(hardwareBuffer);
```

---

## 4. Common Pitfalls

| Pitfall | Consequence | Fix |
|:---|:---|:---|
| Binding external image to `GL_TEXTURE_2D` | Black/garbage output, driver warnings | Use `GL_TEXTURE_EXTERNAL_OES` |
| Missing `#extension` in shader | Compile error or undefined sampling | Add `GL_OES_EGL_image_external(_essl3) : require` |
| `GL_REPEAT` wrap on external texture | Undefined sampling at borders | Force `GL_CLAMP_TO_EDGE` |
| `glGenerateMipmap` on external texture | `GL_INVALID_OPERATION` | External images have no mip chain |
| Forgetting `updateTexImage()` per frame | Stale/first-frame-frozen video | Drive from frame-arrival callback |
| Destroying EGLImage before its textures | Use-after-free in driver | Delete textures first, then EGLImage |
| Drawing an AHardwareBuffer without fence sync | Tearing / garbage frames | `glWaitSync` on producer fence |
| Manual YUV conversion on OES external | Double conversion, banding | Let hardware convert; manual only for raw plane import |
