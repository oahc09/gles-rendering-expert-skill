/**
 * @file egl_context_manager.cpp
 * @brief Cross-platform EGL context initialization, lifecycle management,
 *        and multi-threaded shared context support for OpenGL ES 3.0+.
 *
 * Target: Android NDK / Linux Embedded (Wayland/X11)
 * API: EGL 1.4/1.5 + OpenGL ES 3.0
 *
 * TBDR Note: This file handles context setup only. See offscreen_pipeline.cpp
 * for FBO discard patterns critical to TBDR bandwidth optimization.
 */

#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <GLES3/gl3ext.h>

#include <string>
#include <cstring>
#include <vector>
#include <functional>
#include <mutex>
#include <thread>
#include <atomic>
#include <chrono>
#include <cassert>
#include <cstdio>

// ============================================================================
// Logging utility (replace with platform-specific logging in production)
// ============================================================================
#define LOGI(...) printf("[INFO] " __VA_ARGS__), printf("\n")
#define LOGE(...) printf("[ERROR] " __VA_ARGS__), printf("\n")

// ============================================================================
// EGL Error Checking Macro
// ============================================================================
#define EGL_CHECK(expr)                                                        \
    do {                                                                        \
        if (!(expr)) {                                                         \
            EGLint err = eglGetError();                                        \
            LOGE("EGL error 0x%04X at %s:%d — %s", err, __FILE__, __LINE__, #expr); \
            return false;                                                       \
        }                                                                      \
    } while (0)

#define GL_CHECK(expr)                                                         \
    do {                                                                        \
        expr;                                                                   \
        GLenum err = glGetError();                                             \
        if (err != GL_NO_ERROR) {                                              \
            LOGE("GL error 0x%04X at %s:%d — %s", err, __FILE__, __LINE__, #expr); \
        }                                                                      \
    } while (0)

// ============================================================================
// EGLContextManager — RAII wrapper for EGL display, context, and surface
// ============================================================================
class EGLContextManager {
public:
    struct Config {
        int redSize     = 8;
        int greenSize   = 8;
        int blueSize    = 8;
        int alphaSize   = 8;
        int depthSize   = 24;
        int stencilSize = 8;
        int samples     = 0;   // 0 = no MSAA; 4 = 4x MSAA
        int glesMajor   = 3;
        int glesMinor   = 0;
        bool surfaceless = false;  // Use EGL_KHR_surfaceless_context
    };

    EGLContextManager() = default;
    ~EGLContextManager() { Shutdown(); }

    // Non-copyable, movable
    EGLContextManager(const EGLContextManager&) = delete;
    EGLContextManager& operator=(const EGLContextManager&) = delete;
    EGLContextManager(EGLContextManager&& other) noexcept { *this = std::move(other); }
    EGLContextManager& operator=(EGLContextManager&& other) noexcept {
        if (this != &other) {
            Shutdown();
            display_ = other.display_; other.display_ = EGL_NO_DISPLAY;
            context_ = other.context_; other.context_ = EGL_NO_CONTEXT;
            surface_ = other.surface_; other.surface_ = EGL_NO_SURFACE;
            config_  = other.config_;  other.config_  = nullptr;
            initialized_ = other.initialized_; other.initialized_ = false;
        }
        return *this;
    }

    // ------------------------------------------------------------------
    // Initialize EGL with a native window
    // ------------------------------------------------------------------
    bool Initialize(EGLNativeWindowType nativeWindow, const Config& cfg) {
        cfg_ = cfg;

        // Step 1: Get default display
        display_ = eglGetDisplay(EGL_DEFAULT_DISPLAY);
        EGL_CHECK(display_ != EGL_NO_DISPLAY);

        // Step 2: Initialize EGL
        EGLint eglMajor = 0, eglMinor = 0;
        EGL_CHECK(eglInitialize(display_, &eglMajor, &eglMinor));
        LOGI("EGL %d.%d initialized", eglMajor, eglMinor);

        // Step 3: Choose framebuffer config
        EGL_CHECK(ChooseConfig());

        // Step 4: Create GLES context
        EGL_CHECK(CreateContext(EGL_NO_CONTEXT));

        // Step 5: Create window surface (or surfaceless)
        if (cfg_.surfaceless) {
            // Verify the extension is available before passing EGL_NO_SURFACE.
            const char* extensions = eglQueryString(display_, EGL_EXTENSIONS);
            if (!extensions || !strstr(extensions, "EGL_KHR_surfaceless_context")) {
                LOGE("EGL_KHR_surfaceless_context not supported; cannot use surfaceless mode");
                return false;
            }
            surface_ = EGL_NO_SURFACE;
            LOGI("Using surfaceless context (EGL_KHR_surfaceless_context)");
        } else {
            const EGLint surfAttribs[] = { EGL_NONE };
            surface_ = eglCreateWindowSurface(display_, config_, nativeWindow, surfAttribs);
            EGL_CHECK(surface_ != EGL_NO_SURFACE);
        }

        // Step 6: Make current
        EGL_CHECK(eglMakeCurrent(display_, surface_, surface_, context_));

        initialized_ = true;
        LogGLInfo();
        return true;
    }

    // ------------------------------------------------------------------
    // Create a shared context for worker threads
    // ------------------------------------------------------------------
    struct SharedContext {
        EGLContext context = EGL_NO_CONTEXT;
        EGLSurface surface = EGL_NO_SURFACE;  // Pbuffer
        EGLDisplay display = EGL_NO_DISPLAY;

        bool MakeCurrent() {
            return eglMakeCurrent(display, surface, surface, context) == EGL_TRUE;
        }
        void Release() {
            eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
        }
    };

    bool CreateSharedContext(SharedContext& out) {
        assert(initialized_ && "Main context must be initialized first");

        // Create Pbuffer surface (1x1) for the worker context
        const EGLint pbufAttribs[] = { EGL_WIDTH, 1, EGL_HEIGHT, 1, EGL_NONE };
        out.surface = eglCreatePbufferSurface(display_, config_, pbufAttribs);
        if (out.surface == EGL_NO_SURFACE) {
            LOGE("Failed to create Pbuffer for shared context");
            return false;
        }

        // Create context sharing with main context.
        // Use EGL_CONTEXT_CLIENT_VERSION (EGL 1.4 compatible path).
        const EGLint ctxAttribs[] = {
            EGL_CONTEXT_CLIENT_VERSION, cfg_.glesMajor,
            EGL_NONE
        };
        out.context = eglCreateContext(display_, config_, context_, ctxAttribs);
        if (out.context == EGL_NO_CONTEXT) {
            LOGE("Failed to create shared context: 0x%04X", eglGetError());
            eglDestroySurface(display_, out.surface);
            return false;
        }
        out.display = display_;
        return true;
    }

    void DestroySharedContext(SharedContext& sc) {
        if (display_ == EGL_NO_DISPLAY) return;
        sc.Release();
        if (sc.surface != EGL_NO_SURFACE) eglDestroySurface(display_, sc.surface);
        if (sc.context != EGL_NO_CONTEXT) eglDestroyContext(display_, sc.context);
        sc = {};
    }

    // ------------------------------------------------------------------
    // Swap buffers (present frame)
    // Returns true on success. On failure, sets contextLost_ flag if applicable.
    // ------------------------------------------------------------------
    bool SwapBuffers() {
        if (surface_ == EGL_NO_SURFACE) return true;  // Surfaceless
        if (!eglSwapBuffers(display_, surface_)) {
            EGLint err = eglGetError();
            if (err == EGL_CONTEXT_LOST) {
                LOGE("EGL_CONTEXT_LOST detected — context recovery required");
                contextLost_ = true;
                return false;
            }
            LOGE("eglSwapBuffers failed: 0x%04X", err);
            return false;
        }
        return true;
    }

    // ------------------------------------------------------------------
    // Set swap interval (VSync control)
    // ------------------------------------------------------------------
    void SetSwapInterval(int interval) {
        eglSwapInterval(display_, interval);
    }

    // ------------------------------------------------------------------
    // Shutdown — proper teardown order
    // ------------------------------------------------------------------
    void Shutdown() {
        if (display_ == EGL_NO_DISPLAY) return;

        // Unbind current context
        eglMakeCurrent(display_, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);

        if (surface_ != EGL_NO_SURFACE) {
            eglDestroySurface(display_, surface_);
            surface_ = EGL_NO_SURFACE;
        }
        if (context_ != EGL_NO_CONTEXT) {
            eglDestroyContext(display_, context_);
            context_ = EGL_NO_CONTEXT;
        }
        eglTerminate(display_);
        display_ = EGL_NO_DISPLAY;
        initialized_ = false;
        LOGI("EGL shutdown complete");
    }

    // ------------------------------------------------------------------
    // Context loss detection.
    // Uses a flag set by SwapBuffers() rather than calling eglGetError()
    // (which is consumed by the first caller and returns EGL_SUCCESS thereafter).
    // ------------------------------------------------------------------
    bool IsContextLost() const {
        return contextLost_;
    }

    // ------------------------------------------------------------------
    // Accessors
    // ------------------------------------------------------------------
    EGLDisplay GetDisplay() const { return display_; }
    EGLContext GetContext() const { return context_; }
    EGLSurface GetSurface() const { return surface_; }
    EGLConfig  GetConfig()  const { return config_; }
    bool IsInitialized()    const { return initialized_; }

private:
    bool ChooseConfig() {
        EGLint renderableType = EGL_OPENGL_ES3_BIT;  // GLES 3.0+

        std::vector<EGLint> attribs = {
            EGL_RENDERABLE_TYPE, renderableType,
            EGL_SURFACE_TYPE,    EGL_WINDOW_BIT | EGL_PBUFFER_BIT,
            EGL_RED_SIZE,        cfg_.redSize,
            EGL_GREEN_SIZE,      cfg_.greenSize,
            EGL_BLUE_SIZE,       cfg_.blueSize,
            EGL_ALPHA_SIZE,      cfg_.alphaSize,
            EGL_DEPTH_SIZE,      cfg_.depthSize,
            EGL_STENCIL_SIZE,    cfg_.stencilSize,
        };
        if (cfg_.samples > 0) {
            attribs.push_back(EGL_SAMPLE_BUFFERS);
            attribs.push_back(1);
            attribs.push_back(EGL_SAMPLES);
            attribs.push_back(cfg_.samples);
        }
        attribs.push_back(EGL_NONE);

        EGLint numConfigs = 0;
        EGL_CHECK(eglChooseConfig(display_, attribs.data(), &config_, 1, &numConfigs));
        if (numConfigs == 0) {
            LOGE("No suitable EGL config found");
            return false;
        }
        return true;
    }

    bool CreateContext(EGLContext shareWith) {
        // Use EGL_CONTEXT_CLIENT_VERSION for broadest EGL 1.4 compatibility.
        // EGL_CONTEXT_MAJOR/MINOR_VERSION requires EGL 1.5 or EGL_KHR_create_context.
        const EGLint ctxAttribs[] = {
            EGL_CONTEXT_CLIENT_VERSION, cfg_.glesMajor,
            EGL_NONE
        };
        context_ = eglCreateContext(display_, config_, shareWith, ctxAttribs);
        EGL_CHECK(context_ != EGL_NO_CONTEXT);
        return true;
    }

    void LogGLInfo() {
        LOGI("GL Renderer:   %s", glGetString(GL_RENDERER));
        LOGI("GL Vendor:     %s", glGetString(GL_VENDOR));
        LOGI("GL Version:    %s", glGetString(GL_VERSION));
        LOGI("GLSL Version:  %s", glGetString(GL_SHADING_LANGUAGE_VERSION));
    }

    EGLDisplay display_     = EGL_NO_DISPLAY;
    EGLContext context_     = EGL_NO_CONTEXT;
    EGLSurface surface_     = EGL_NO_SURFACE;
    EGLConfig  config_      = nullptr;
    Config     cfg_;
    bool       initialized_ = false;
    bool       contextLost_ = false;
};

// ============================================================================
// Example: Worker thread loading textures via shared context
// ============================================================================
class TextureLoader {
public:
    explicit TextureLoader(EGLContextManager& mgr) : mgr_(mgr) {}

    bool Start() {
        if (!mgr_.CreateSharedContext(sharedCtx_)) return false;
        running_ = true;
        thread_ = std::thread(&TextureLoader::WorkerLoop, this);
        return true;
    }

    void Stop() {
        running_ = false;
        if (thread_.joinable()) thread_.join();
        mgr_.DestroySharedContext(sharedCtx_);
    }

    // Queue a texture for async loading (simplified)
    void RequestLoad(const std::string& path, GLuint targetTexId) {
        std::lock_guard<std::mutex> lock(mutex_);
        pendingLoads_.push_back({path, targetTexId});
    }

private:
    struct LoadRequest {
        std::string path;
        GLuint texId;
    };

    void WorkerLoop() {
        // Make shared context current on THIS thread
        if (!sharedCtx_.MakeCurrent()) {
            LOGE("Worker: Failed to make shared context current");
            return;
        }
        LOGI("Worker: GL context active — %s", glGetString(GL_RENDERER));

        while (running_) {
            LoadRequest req;
            {
                std::lock_guard<std::mutex> lock(mutex_);
                if (pendingLoads_.empty()) {
                    // Sleep briefly to avoid busy-wait (use condition_variable in production)
                    std::this_thread::sleep_for(std::chrono::milliseconds(1));
                    continue;
                }
                req = pendingLoads_.front();
                pendingLoads_.erase(pendingLoads_.begin());
            }

            // Simulate texture upload
            glBindTexture(GL_TEXTURE_2D, req.texId);
            // glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
            glGenerateMipmap(GL_TEXTURE_2D);
            glBindTexture(GL_TEXTURE_2D, 0);

            // Insert fence for render thread synchronization.
            // glFlush() is REQUIRED to ensure the fence is submitted to the GPU;
            // without it the fence may never signal on some drivers.
            GLsync fence = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0);
            glFlush();

            // In production: push {texId, fence} to a thread-safe "ready" queue.
            // The render thread calls glWaitSync(fence, 0, GL_TIMEOUT_IGNORED)
            // before using the texture, then glDeleteSync(fence).
            LOGI("Worker: Texture '%s' uploaded, fence=%p inserted", req.path.c_str(), (void*)fence);

            // For this example, we wait and delete the fence here (not ideal,
            // but prevents resource leak in this simplified demo).
            glClientWaitSync(fence, GL_SYNC_FLUSH_COMMANDS_BIT, 1000000000ULL);
            glDeleteSync(fence);
        }

        sharedCtx_.Release();
    }

    EGLContextManager& mgr_;
    EGLContextManager::SharedContext sharedCtx_;
    std::thread thread_;
    std::atomic<bool> running_{false};
    std::mutex mutex_;
    std::vector<LoadRequest> pendingLoads_;
};

// ============================================================================
// Main — Demonstration
// ============================================================================
int main() {
    EGLContextManager egl;

    // On Android: nativeWindow comes from ANativeWindow
    // On Linux: from X11 Window or wl_egl_window
    EGLNativeWindowType nativeWindow = nullptr;  // Platform-specific

    EGLContextManager::Config cfg;
    cfg.glesMajor = 3;
    cfg.glesMinor = 0;
    cfg.depthSize = 24;
    cfg.stencilSize = 8;

    if (!egl.Initialize(nativeWindow, cfg)) {
        LOGE("Failed to initialize EGL");
        return -1;
    }

    // Start async texture loader
    TextureLoader loader(egl);
    loader.Start();

    // Simulate render loop
    for (int frame = 0; frame < 60; ++frame) {
        // --- Render Pass ---
        GL_CHECK(glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT));
        // ... draw scene ...

        // Present
        if (!egl.SwapBuffers()) {
            if (egl.IsContextLost()) {
                LOGE("Context lost — initiating recovery");
                // HandleContextLost() — see references/rules/egl-and-context.md
                break;
            }
        }
    }

    loader.Stop();
    egl.Shutdown();
    return 0;
}
