# EGL Context Management & Multi-Thread Synchronization Rules

## 1. EGL Lifecycle Management

### 1.1 Complete Initialization Sequence

```cpp
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>

struct EGLSetup {
    EGLDisplay display = EGL_NO_DISPLAY;
    EGLContext context = EGL_NO_CONTEXT;
    EGLSurface surface = EGL_NO_SURFACE;
    EGLConfig  config  = nullptr;
    
    bool Initialize(EGLNativeWindowType nativeWindow, int majorVer = 3, int minorVer = 0) {
        // Step 1: Get Display
        display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
        if (display == EGL_NO_DISPLAY) return false;
        
        // Step 2: Initialize EGL
        EGLint eglMajor, eglMinor;
        if (!eglInitialize(display, &eglMajor, &eglMinor)) return false;
        
        // Step 3: Choose Config
        const EGLint configAttribs[] = {
            EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT,  // GLES 3.0+
            EGL_SURFACE_TYPE,    EGL_WINDOW_BIT,
            EGL_RED_SIZE,        8,
            EGL_GREEN_SIZE,      8,
            EGL_BLUE_SIZE,       8,
            EGL_ALPHA_SIZE,      8,
            EGL_DEPTH_SIZE,      24,
            EGL_STENCIL_SIZE,    8,
            EGL_NONE
        };
        EGLint numConfigs = 0;
        if (!eglChooseConfig(display, configAttribs, &config, 1, &numConfigs) 
            || numConfigs == 0) return false;
        
        // Step 4: Create Context (EGL 1.4-compatible attribute)
        // EGL_CONTEXT_CLIENT_VERSION is universally supported on EGL 1.4+.
        // For minor version control, require EGL_KHR_create_context and use
        // EGL_CONTEXT_MAJOR_VERSION_KHR / EGL_CONTEXT_MINOR_VERSION_KHR.
        const EGLint contextAttribs[] = {
            EGL_CONTEXT_CLIENT_VERSION, majorVer,
            EGL_NONE
        };
        context = eglCreateContext(display, config, EGL_NO_CONTEXT, contextAttribs);
        if (context == EGL_NO_CONTEXT) return false;
        
        // Step 5: Create Window Surface
        const EGLint surfaceAttribs[] = { EGL_NONE };
        surface = eglCreateWindowSurface(display, config, nativeWindow, surfaceAttribs);
        if (surface == EGL_NO_SURFACE) return false;
        
        // Step 6: Make Current
        if (!eglMakeCurrent(display, surface, surface, context)) return false;
        
        return true;
    }
    
    void Shutdown() {
        if (display != EGL_NO_DISPLAY) {
            eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
            if (surface != EGL_NO_SURFACE) {
                eglDestroySurface(display, surface);
                surface = EGL_NO_SURFACE;
            }
            if (context != EGL_NO_CONTEXT) {
                eglDestroyContext(display, context);
                context = EGL_NO_CONTEXT;
            }
            eglTerminate(display);
            display = EGL_NO_DISPLAY;
        }
    }
};
```

### 1.2 Error Checking Pattern

```cpp
#define EGL_CHECK(call) \
    do { \
        if (!(call)) { \
            EGLint err = eglGetError(); \
            LOGE("EGL Error 0x%04X at %s:%d", err, __FILE__, __LINE__); \
            /* Handle: EGL_BAD_DISPLAY, EGL_BAD_SURFACE, EGL_CONTEXT_LOST */ \
        } \
    } while(0)
```

### 1.3 Swap Buffers & VSync

```cpp
// Standard present
eglSwapBuffers(display, surface);

// Control swap interval (1 = VSync, 0 = uncapped)
eglSwapInterval(display, 1);
```

---

## 2. Multi-Threaded Shared Context

### 2.1 Architecture

```
┌──────────────────┐         ┌──────────────────┐
│  Render Thread   │         │  Worker Thread   │
│  (Main Context)  │◄─share─►│  (Load Context)  │
│                  │         │                  │
│  eglMakeCurrent  │         │  eglMakeCurrent  │
│  Draw scene      │         │  Upload textures │
│  Present         │         │  Decode assets   │
└──────────────────┘         └──────────────────┘
         │                           │
         └───── glFenceSync ─────────┘
              (visibility sync)
```

### 2.2 Worker Thread Context Creation

```cpp
class WorkerGLContext {
    EGLDisplay display_ = EGL_NO_DISPLAY;
    EGLContext context_ = EGL_NO_CONTEXT;
    EGLSurface surface_ = EGL_NO_SURFACE;  // Pbuffer or surfaceless
    
public:
    bool Create(EGLDisplay sharedDisplay, EGLConfig config, EGLContext shareContext) {
        display_ = sharedDisplay;
        
        const EGLint ctxAttribs[] = {
            EGL_CONTEXT_CLIENT_VERSION, 3,  // EGL 1.4-compatible
            EGL_NONE
        };
        context_ = eglCreateContext(display_, config, shareContext, ctxAttribs);
        if (context_ == EGL_NO_CONTEXT) return false;
        
        // Option A: Pbuffer surface (1x1, always available)
        const EGLint pbufAttribs[] = { EGL_WIDTH, 1, EGL_HEIGHT, 1, EGL_NONE };
        surface_ = eglCreatePbufferSurface(display_, config, pbufAttribs);
        
        // Option B: Surfaceless (requires EGL_KHR_surfaceless_context)
        // surface_ = EGL_NO_SURFACE;
        
        return true;
    }
    
    bool MakeCurrent() {
        return eglMakeCurrent(display_, surface_, surface_, context_) == EGL_TRUE;
    }
    
    void Release() {
        eglMakeCurrent(display_, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
    }
    
    void Destroy() {
        Release();
        if (display_ != EGL_NO_DISPLAY) {
            if (surface_ != EGL_NO_SURFACE) eglDestroySurface(display_, surface_);
            if (context_ != EGL_NO_CONTEXT) eglDestroyContext(display_, context_);
        }
    }
};
```

### 2.3 Cross-Thread Synchronization

```cpp
// Worker thread: after uploading texture
void WorkerThread_UploadTexture(/* ... */) {
    workerCtx.MakeCurrent();
    
    // Upload texture data
    glBindTexture(GL_TEXTURE_2D, texId);
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
    glGenerateMipmap(GL_TEXTURE_2D);
    
    // Insert fence so render thread knows upload is complete
    GLsync fence = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0);
    
    // Signal render thread (via condition variable, queue, etc.)
    renderThread.NotifyTextureReady(texId, fence);
    
    workerCtx.Release();
}

// Render thread: before using uploaded texture
void RenderThread_UseTexture(GLuint texId, GLsync fence) {
    // Wait for worker's upload to complete (GPU-side, no CPU stall if already done)
    glWaitSync(fence, 0, GL_TIMEOUT_IGNORED);
    glDeleteSync(fence);
    
    // Safe to use texture now
    glBindTexture(GL_TEXTURE_2D, texId);
    // ... draw ...
}
```

### 2.4 Shared Context Rules
- **Shared objects**: Textures, Buffers, Shaders, Programs, Samplers, Sync objects.
- **NOT shared**: VAOs, FBOs, Queries (per-context state).
- Each thread must have its own VAO/FBO even if referencing shared textures/buffers.
- `eglMakeCurrent` is **per-thread** — one context active per thread at a time.

---

## 3. Android Context Lost Handling

### 3.1 When Context Loss Occurs
- App moves to background → Android may destroy the EGLSurface.
- Screen turns off → Surface may be invalidated.
- System reclaims GPU resources under memory pressure.
- `eglSwapBuffers` returns `EGL_FALSE` with error `EGL_CONTEXT_LOST`.

### 3.2 Detection

```cpp
// In render loop — check return value first, then query error once:
if (!eglSwapBuffers(display, surface)) {
    EGLint error = eglGetError();  // consumed on read — do not call twice
    if (error == EGL_CONTEXT_LOST) {
        HandleContextLost();
    } else {
        HandleSwapError(error);  // e.g. EGL_BAD_SURFACE
    }
}
```

### 3.3 Recovery Architecture

```cpp
class ResourceRegistry {
public:
    // Register all GPU resources at creation time
    void RegisterShader(const std::string& name, ShaderSource src);
    void RegisterTexture(const std::string& name, TextureDesc desc);
    void RegisterBuffer(const std::string& name, BufferDesc desc);
    
    // Rebuild all resources after context recovery
    void RebuildAll() {
        for (auto& [name, src] : shaders_)  RecreateShader(name, src);
        for (auto& [name, desc] : textures_) RecreateTexture(name, desc);
        for (auto& [name, desc] : buffers_)  RecreateBuffer(name, desc);
    }
    
private:
    std::unordered_map<std::string, ShaderSource> shaders_;
    std::unordered_map<std::string, TextureDesc> textures_;
    std::unordered_map<std::string, BufferDesc> buffers_;
};

void HandleContextLost() {
    // 1. Destroy stale EGL objects
    eglDestroySurface(display, surface);
    eglDestroyContext(display, context);
    
    // 2. Wait for surface to be available again (Android: onSurfaceCreated callback)
    // In Android NDK: this is handled by android_native_app_glue
    
    // 3. Recreate EGL context & surface
    RecreateEGLContext();
    
    // 4. Rebuild all GPU resources from CPU-side cache
    resourceRegistry.RebuildAll();
    
    // 5. Restore GL state (viewport, blend, depth test, etc.)
    RestoreGLState();
}
```

### 3.4 Android NDK Integration

```cpp
// Using android_native_app_glue:
void HandleCmd(android_app* app, int32_t cmd) {
    switch (cmd) {
        case APP_CMD_INIT_WINDOW:
            // Surface created — initialize EGL
            InitEGL(app->window);
            break;
        case APP_CMD_TERM_WINDOW:
            // Surface destroyed — release EGL surface, keep context if possible
            ReleaseEGLSurface();
            break;
        case APP_CMD_CONTEXT_LOST:
            // Explicit context loss notification (API 31+)
            HandleContextLost();
            break;
        case APP_CMD_GAINED_FOCUS:
            // Resume rendering
            break;
        case APP_CMD_LOST_FOCUS:
            // Pause rendering
            break;
    }
}
```

---

## 4. EGL Extensions for Mobile

| Extension | Purpose |
|:---|:---|
| `EGL_KHR_surfaceless_context` | MakeCurrent without a surface (headless rendering) |
| `EGL_KHR_fence_sync` | GPU fence synchronization |
| `EGL_KHR_wait_sync` | Server-side wait (GPU waits, no CPU stall) |
| `EGL_ANDROID_image_native_buffer` | Import AHardwareBuffer as EGLImage |
| `EGL_KHR_image_base` | EGLImage for zero-copy texture sharing |
| `EGL_ANDROID_presentation_time` | Timestamp-based frame presentation |
| `EGL_KHR_swap_buffers_with_damage` | Partial screen update (power saving) |

---

## 5. Best Practices Summary

1. **Always** check EGL return values and error codes.
2. **Always** call `eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT)` before destroying a context (pass the valid `EGLDisplay`, **not** `EGL_NO_DISPLAY`).
3. **Never** share a context across threads simultaneously — one `eglMakeCurrent` per thread.
4. **Always** use `glFenceSync` for cross-thread GPU resource handoff.
5. **Design for context loss** from day one — all GPU resources must be recreatable from CPU data.
6. **Prefer** `EGL_KHR_surfaceless_context` + Pbuffer over creating dummy windows for worker threads.
7. **On Android**: Handle `APP_CMD_TERM_WINDOW` gracefully; don't call any GL/EGL functions after surface destruction until re-creation.
