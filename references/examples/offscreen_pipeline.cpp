/**
 * @file offscreen_pipeline.cpp
 * @brief Offscreen FBO rendering pipeline demonstrating correct
 *        glInvalidateFramebuffer usage for TBDR bandwidth optimization.
 *
 * Scenario: Shadow map rendering + Main scene rendering with post-processing.
 * Target: OpenGL ES 3.0+ / C++17
 *
 * TBDR Critical: This example demonstrates the #1 mobile GPU optimization —
 * proper FBO clear/invalidate patterns to minimize DRAM bandwidth.
 */

#include <GLES3/gl3.h>
#include <GLES3/gl3ext.h>
#include <cstdio>
#include <vector>
#include <cassert>

#define LOGI(...) printf("[INFO] " __VA_ARGS__), printf("\n")
#define LOGE(...) printf("[ERROR] " __VA_ARGS__), printf("\n")

// ============================================================================
// RAII Framebuffer Object
// ============================================================================
class Framebuffer {
public:
    Framebuffer() = default;
    ~Framebuffer() { Destroy(); }

    Framebuffer(const Framebuffer&) = delete;
    Framebuffer& operator=(const Framebuffer&) = delete;
    Framebuffer(Framebuffer&& o) noexcept : id_(o.id_), width_(o.width_), height_(o.height_) { o.id_ = 0; }
    Framebuffer& operator=(Framebuffer&& o) noexcept {
        if (this != &o) { Destroy(); id_ = o.id_; width_ = o.width_; height_ = o.height_; o.id_ = 0; }
        return *this;
    }

    bool Create(GLsizei width, GLsizei height) {
        width_ = width;
        height_ = height;
        glGenFramebuffers(1, &id_);
        return id_ != 0;
    }

    void Bind() const { glBindFramebuffer(GL_FRAMEBUFFER, id_); }

    /// Attach a texture as color attachment
    void AttachColorTexture(GLuint texture, GLenum attachment = GL_COLOR_ATTACHMENT0) {
        Bind();
        glFramebufferTexture2D(GL_FRAMEBUFFER, attachment, GL_TEXTURE_2D, texture, 0);
    }

    /// Attach a texture as depth attachment
    void AttachDepthTexture(GLuint texture) {
        Bind();
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, texture, 0);
    }

    /// Attach a renderbuffer as depth+stencil
    void AttachDepthStencilRenderbuffer(GLuint rbo) {
        Bind();
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT,
                                  GL_RENDERBUFFER, rbo);
    }

    bool CheckComplete() const {
        Bind();
        GLenum status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
        if (status != GL_FRAMEBUFFER_COMPLETE) {
            LOGE("FBO incomplete: 0x%04X", status);
            return false;
        }
        return true;
    }

    /// TBDR CRITICAL: Invalidate specified attachments after rendering.
    /// This tells the GPU: "Don't write these tiles back to DRAM."
    void InvalidateAttachments(const std::vector<GLenum>& attachments) {
        Bind();
        glInvalidateFramebuffer(GL_FRAMEBUFFER,
                                static_cast<GLsizei>(attachments.size()),
                                attachments.data());
    }

    GLuint Id() const { return id_; }
    GLsizei Width() const { return width_; }
    GLsizei Height() const { return height_; }

    void Destroy() {
        if (id_ != 0) { glDeleteFramebuffers(1, &id_); id_ = 0; }
    }

private:
    GLuint id_ = 0;
    GLsizei width_ = 0;
    GLsizei height_ = 0;
};

// ============================================================================
// RAII Texture
// ============================================================================
class Texture2D {
public:
    Texture2D() = default;
    ~Texture2D() { Destroy(); }
    Texture2D(Texture2D&& o) noexcept : id_(o.id_) { o.id_ = 0; }
    Texture2D& operator=(Texture2D&& o) noexcept {
        if (this != &o) { Destroy(); id_ = o.id_; o.id_ = 0; }
        return *this;
    }
    Texture2D(const Texture2D&) = delete;
    Texture2D& operator=(const Texture2D&) = delete;

    bool Create(GLsizei w, GLsizei h, GLenum internalFormat, GLenum format, GLenum type) {
        glGenTextures(1, &id_);
        glBindTexture(GL_TEXTURE_2D, id_);
        // Use glTexStorage2D for immutable allocation (better driver optimization)
        glTexStorage2D(GL_TEXTURE_2D, 1, internalFormat, w, h);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glBindTexture(GL_TEXTURE_2D, 0);
        return id_ != 0;
    }

    /// Create depth texture (for shadow mapping)
    bool CreateDepth(GLsizei w, GLsizei h) {
        glGenTextures(1, &id_);
        glBindTexture(GL_TEXTURE_2D, id_);
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_DEPTH_COMPONENT24, w, h);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        // Shadow comparison mode
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_COMPARE_REF_TO_TEXTURE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_FUNC, GL_LEQUAL);
        glBindTexture(GL_TEXTURE_2D, 0);
        return id_ != 0;
    }

    void Bind(GLuint unit) const {
        glActiveTexture(GL_TEXTURE0 + unit);
        glBindTexture(GL_TEXTURE_2D, id_);
    }

    GLuint Id() const { return id_; }
    void Destroy() { if (id_) { glDeleteTextures(1, &id_); id_ = 0; } }

private:
    GLuint id_ = 0;
};

// ============================================================================
// Offscreen Rendering Pipeline with TBDR Optimization
// ============================================================================
class OffscreenPipeline {
public:
    bool Initialize(GLsizei screenWidth, GLsizei screenHeight,
                    GLsizei shadowMapSize = 1024) {
        screenWidth_ = screenWidth;
        screenHeight_ = screenHeight;

        // --- Shadow Map FBO (depth-only) ---
        if (!shadowDepthTex_.CreateDepth(shadowMapSize, shadowMapSize)) return false;
        if (!shadowFbo_.Create(shadowMapSize, shadowMapSize)) return false;
        shadowFbo_.AttachDepthTexture(shadowDepthTex_.Id());
        // No color attachment — set draw buffer to NONE
        shadowFbo_.Bind();
        glDrawBuffers(0, nullptr);  // GLES 3.0: no color output
        glReadBuffer(GL_NONE);
        if (!shadowFbo_.CheckComplete()) return false;

        // --- HDR Offscreen FBO (color + depth) ---
        if (!hdrColorTex_.Create(screenWidth, screenHeight,
                                 GL_RGBA16F, GL_RGBA, GL_HALF_FLOAT)) return false;
        if (!hdrDepthTex_.CreateDepth(screenWidth, screenHeight)) return false;
        if (!hdrFbo_.Create(screenWidth, screenHeight)) return false;
        hdrFbo_.AttachColorTexture(hdrColorTex_.Id(), GL_COLOR_ATTACHMENT0);
        hdrFbo_.AttachDepthTexture(hdrDepthTex_.Id());
        if (!hdrFbo_.CheckComplete()) return false;

        LOGI("OffscreenPipeline initialized: screen=%dx%d, shadow=%dx%d",
             screenWidth, screenHeight, shadowMapSize, shadowMapSize);
        return true;
    }

    // ==================================================================
    // PASS 1: Shadow Map Rendering
    // ==================================================================
    void RenderShadowPass(/* scene, light matrices */) {
        shadowFbo_.Bind();
        glViewport(0, 0, shadowFbo_.Width(), shadowFbo_.Height());

        // TBDR: Clear depth to avoid DRAM → Tile load of stale data
        // This is CRITICAL — without this, the GPU loads the entire
        // shadow map from DRAM into tile memory before rendering.
        glClear(GL_DEPTH_BUFFER_BIT);

        // Render scene from light's perspective
        // glUseProgram(shadowShaderProgram);
        // DrawSceneGeometry();

        // TBDR: After shadow pass, depth IS needed (as shadow map texture).
        // Do NOT invalidate depth here — it will be sampled in the main pass.
        // If we had stencil, we would invalidate it:
        // shadowFbo_.InvalidateAttachments({GL_STENCIL_ATTACHMENT});
    }

    // ==================================================================
    // PASS 2: Main Scene → HDR FBO
    // ==================================================================
    void RenderMainPass(/* scene, camera */) {
        hdrFbo_.Bind();
        glViewport(0, 0, screenWidth_, screenHeight_);

        // TBDR: Clear ALL attachments at pass start
        // Signals driver: Load Op = DONT_CARE for all attachments
        // Saves: screenWidth * screenHeight * (8 + 4) bytes of DRAM reads
        //        (RGBA16F = 8 bytes + Depth24 = 4 bytes per pixel)
        glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        // Bind shadow map from Pass 1
        shadowDepthTex_.Bind(0);  // texture unit 0

        // Render scene with shadow mapping
        // glUseProgram(mainShaderProgram);
        // glUniform1i(u_ShadowMapLocation, 0);
        // DrawSceneWithShadows();

        // TBDR CRITICAL: Invalidate depth BEFORE switching FBOs.
        // Once we switch to the default FBO, the driver flushes all HDR FBO
        // tiles (store). By invalidating depth here, the driver knows it can
        // skip writing depth tiles back to DRAM — saving bandwidth.
        hdrFbo_.InvalidateAttachments({
            GL_DEPTH_ATTACHMENT
            // Add GL_STENCIL_ATTACHMENT if stencil was attached
        });
    }

    // ==================================================================
    // PASS 3: Tone Mapping / Post-Process → Default Framebuffer (Screen)
    // ==================================================================
    void RenderPostProcess(/* post-process shader */) {
        // Switch to default framebuffer (screen)
        glBindFramebuffer(GL_FRAMEBUFFER, 0);
        glViewport(0, 0, screenWidth_, screenHeight_);

        // TBDR: Clear screen before post-process full-screen quad
        glClear(GL_COLOR_BUFFER_BIT);

        // Sample HDR color texture, apply tone mapping
        hdrColorTex_.Bind(0);
        // glUseProgram(postProcessProgram);
        // DrawFullScreenQuad();
    }

    // ==================================================================
    // Full Frame Execution
    // ==================================================================
    void RenderFrame() {
        RenderShadowPass();
        RenderMainPass();
        RenderPostProcess();
        // eglSwapBuffers() called by the caller
    }

private:
    GLsizei screenWidth_ = 0;
    GLsizei screenHeight_ = 0;

    // Shadow map resources
    Framebuffer shadowFbo_;
    Texture2D   shadowDepthTex_;

    // HDR offscreen resources
    Framebuffer hdrFbo_;
    Texture2D   hdrColorTex_;
    Texture2D   hdrDepthTex_;
};

// ============================================================================
// Bandwidth Analysis (for documentation / code review)
// ============================================================================
/*
 * TBDR Bandwidth Savings Analysis (1080×1920 @ 60 FPS):
 *
 * WITHOUT glInvalidateFramebuffer:
 *   - Shadow FBO depth load:  1024×1024×4 = 4.0 MB/frame (unnecessary load)
 *   - HDR FBO depth load:     1080×1920×4 = 7.9 MB/frame (unnecessary load)
 *   - HDR FBO depth store:    1080×1920×4 = 7.9 MB/frame (unnecessary store)
 *   Total wasted bandwidth:   ~19.8 MB/frame × 60 FPS = ~1.19 GB/s
 *
 * WITH proper clear + invalidate:
 *   - Shadow FBO: glClear eliminates load (DONT_CARE)
 *   - HDR FBO: glClear eliminates load, invalidate eliminates depth store
 *   Total saved: ~1.19 GB/s of DRAM bandwidth
 *
 * On a typical mobile GPU with ~25 GB/s peak bandwidth, this saves ~5%
 * of total bandwidth budget — often the difference between 30 and 60 FPS
 * in bandwidth-bound scenarios.
 */

// ============================================================================
// Main — Demonstration
// ============================================================================
int main() {
    // Assume EGL context is already current (see egl_context_manager.cpp)

    OffscreenPipeline pipeline;
    if (!pipeline.Initialize(1080, 1920, 2048)) {
        LOGE("Failed to initialize offscreen pipeline");
        return -1;
    }

    // Enable depth test for scene rendering
    glEnable(GL_DEPTH_TEST);
    glDepthFunc(GL_LEQUAL);  // LEQUAL for better early-Z rejection on TBDR

    // Enable back-face culling (reduces overdraw)
    glEnable(GL_CULL_FACE);
    glCullFace(GL_BACK);

    // Render loop
    for (int frame = 0; frame < 300; ++frame) {
        pipeline.RenderFrame();
        // eglSwapBuffers(display, surface);
    }

    return 0;
}
