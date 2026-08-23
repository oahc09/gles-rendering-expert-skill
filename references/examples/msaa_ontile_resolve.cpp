/**
 * @file msaa_ontile_resolve.cpp
 * @brief Efficient MSAA on TBDR GPUs via EXT_multisampled_render_to_texture
 *        — the resolve happens ON-TILE, never touching DRAM for MSAA samples.
 *
 * Target:   OpenGL ES 3.0+ / C++17
 * Extension: GL_EXT_multisampled_render_to_texture
 *            (Mali G7x+, Adreno 4xx+, PowerVR Series6+)
 *
 * Rules reference:
 *   - references/rules/adreno/efficient-msaa.md
 *   - references/rules/mali-arm-best-practices.md §5
 *
 * ANTI-PATTERN this example prevents:
 *   Rendering into a GL_RENDERBUFFER multisample FBO and resolving with
 *   glBlitFramebuffer — that path writes all MSAA samples to DRAM and reads
 *   them back. On TBDR it is an order of magnitude more bandwidth than the
 *   on-tile resolve path shown here.
 */

#include <GLES3/gl3.h>
#include <GLES3/gl3ext.h>
#include <EGL/egl.h>
#include <cstdio>
#include <cstring>
#include <vector>

#define LOGI(...) printf("[INFO] " __VA_ARGS__), printf("\n")
#define LOGE(...) printf("[ERROR] " __VA_ARGS__), printf("\n")

// Extension entry points (guarded; present in NDK gl3ext.h / glext.h)
#ifndef GL_EXT_multisampled_render_to_texture
#define GL_RENDERBUFFER_SAMPLES_EXT 0x8CAB
#define GL_FRAMEBUFFER_INCOMPLETE_MULTISAMPLE_EXT 0x8D56
#define GL_MAX_SAMPLES_EXT 0x8D57
#endif

using PFNGLRENDERBUFFERSTORAGEMULTISAMPLEEXTPROC =
    void (*)(GLenum target, GLsizei samples, GLenum internalformat,
             GLsizei width, GLsizei height);
using PFNGLFRAMEBUFFERTEXTURE2DMULTISAMPLEEXTPROC =
    void (*)(GLenum target, GLenum attachment, GLenum textarget,
             GLuint texture, GLint level, GLsizei samples);

// ============================================================================
// RAII handles
// ============================================================================
class Renderbuffer {
public:
    ~Renderbuffer() { if (id_ != 0) glDeleteRenderbuffers(1, &id_); }
    Renderbuffer(const Renderbuffer&) = delete;
    Renderbuffer& operator=(const Renderbuffer&) = delete;

    void Create() { glGenRenderbuffers(1, &id_); }
    void StorageMultisample(GLsizei samples, GLenum fmt, GLsizei w, GLsizei h,
                            PFNGLRENDERBUFFERSTORAGEMULTISAMPLEEXTPROC fn) {
        glBindRenderbuffer(GL_RENDERBUFFER, id_);
        fn(GL_RENDERBUFFER, samples, fmt, w, h);
        glBindRenderbuffer(GL_RENDERBUFFER, 0);
    }
    GLuint Id() const { return id_; }
private:
    GLuint id_ = 0;
};

class Framebuffer {
public:
    ~Framebuffer() { if (id_ != 0) glDeleteFramebuffers(1, &id_); }
    Framebuffer(const Framebuffer&) = delete;
    Framebuffer& operator=(const Framebuffer&) = delete;

    void Create() { glGenFramebuffers(1, &id_); }
    void Bind() const { glBindFramebuffer(GL_FRAMEBUFFER, id_); }
    GLuint Id() const { return id_; }
private:
    GLuint id_ = 0;
};

class Texture2D {
public:
    ~Texture2D() { if (id_ != 0) glDeleteTextures(1, &id_); }
    Texture2D(const Texture2D&) = delete;
    Texture2D& operator=(const Texture2D&) = delete;

    /// Immutable single-sample destination of the on-tile resolve.
    bool CreateResolved(GLsizei w, GLsizei h) {
        glGenTextures(1, &id_);
        glBindTexture(GL_TEXTURE_2D, id_);
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA8, w, h);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glBindTexture(GL_TEXTURE_2D, 0);
        return id_ != 0;
    }
    GLuint Id() const { return id_; }
private:
    GLuint id_ = 0;
};

// ============================================================================
// MSAA On-Tile Pipeline
// ============================================================================
class MsaaOnTilePipeline {
public:
    /// samples: 4 recommended by default (see mali-arm-best-practices.md §5).
    /// Returns false when the extension is missing — caller falls back to
    /// single-sample rendering (never to blit-resolve).
    bool Init(GLsizei width, GLsizei height, GLsizei samples) {
        if (!HasExtension("GL_EXT_multisampled_render_to_texture")) {
            LOGE("EXT_multisampled_render_to_texture missing — use 1x rendering");
            return false;
        }
        glRenderbufferStorageMultisampleEXT_ =
            reinterpret_cast<PFNGLRENDERBUFFERSTORAGEMULTISAMPLEEXTPROC>(
                eglGetProcAddress("glRenderbufferStorageMultisampleEXT"));
        glFramebufferTexture2DMultisampleEXT_ =
            reinterpret_cast<PFNGLFRAMEBUFFERTEXTURE2DMULTISAMPLEEXTPROC>(
                eglGetProcAddress("glFramebufferTexture2DMultisampleEXT"));
        if (glRenderbufferStorageMultisampleEXT_ == nullptr ||
            glFramebufferTexture2DMultisampleEXT_ == nullptr) {
            LOGE("EXT_multisampled_render_to_texture entry points not resolvable");
            return false;
        }

        // Clamp against implementation maximum
        GLint maxSamples = 0;
        glGetIntegerv(GL_MAX_SAMPLES_EXT, &maxSamples);
        if (samples > maxSamples) samples = static_cast<GLsizei>(maxSamples);

        resolvedColor_.CreateResolved(width, height);
        msaaDepth_.Create();
        msaaDepth_.StorageMultisample(samples, GL_DEPTH_COMPONENT24, width, height,
                                      glRenderbufferStorageMultisampleEXT_);

        fbo_.Create();
        fbo_.Bind();
        // Color: single-sample TEXTURE with an implicit multisample render +
        // on-tile resolve. The driver resolves inside tile memory at pass end —
        // no DRAM round-trip for the MSAA samples.
        glFramebufferTexture2DMultisampleEXT_(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                                              GL_TEXTURE_2D, resolvedColor_.Id(),
                                              0, samples);
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
                                  GL_RENDERBUFFER, msaaDepth_.Id());

        GLenum status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
        glBindFramebuffer(GL_FRAMEBUFFER, 0);
        if (status != GL_FRAMEBUFFER_COMPLETE) {
            LOGE("MSAA FBO incomplete: 0x%04X (samples=%d)", status, samples);
            return false;
        }
        samples_ = samples;
        LOGI("On-tile MSAA ready: %dx%d @ %dx samples", width, height, samples);
        return true;
    }

    /// Render pass: bind, clear, draw. At pass end the driver resolves the
    /// multisample color ON-TILE into resolvedColor_.
    void BeginPass(GLsizei width, GLsizei height) {
        fbo_.Bind();
        glViewport(0, 0, width, height);
        // TBDR: clear at pass start → no tile load from DRAM
        glClearColor(0.05f, 0.05f, 0.08f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    }

    void EndPass() {
        // TBDR: depth is not consumed later → skip the tile store.
        const GLenum discards[] = { GL_DEPTH_ATTACHMENT };
        glInvalidateFramebuffer(GL_FRAMEBUFFER, 1, discards);
        glBindFramebuffer(GL_FRAMEBUFFER, 0);
    }

    /// The resolved single-sample texture for downstream sampling/post-FX.
    GLuint ResolvedColorTexture() const { return resolvedColor_.Id(); }
    GLsizei Samples() const { return samples_; }

private:
    static bool HasExtension(const char* name) {
        GLint count = 0;
        glGetIntegerv(GL_NUM_EXTENSIONS, &count);
        for (GLint i = 0; i < count; ++i) {
            const char* ext = reinterpret_cast<const char*>(glGetStringi(GL_EXTENSIONS, i));
            if (ext != nullptr && std::strcmp(ext, name) == 0) return true;
        }
        return false;
    }

    Texture2D resolvedColor_;
    Renderbuffer msaaDepth_;
    Framebuffer fbo_;
    PFNGLRENDERBUFFERSTORAGEMULTISAMPLEEXTPROC glRenderbufferStorageMultisampleEXT_ = nullptr;
    PFNGLFRAMEBUFFERTEXTURE2DMULTISAMPLEEXTPROC glFramebufferTexture2DMultisampleEXT_ = nullptr;
    GLsizei samples_ = 0;
};

// ============================================================================
// Usage sketch:
//
//   MsaaOnTilePipeline msaa;
//   if (msaa.Init(width, height, 4)) {
//       msaa.BeginPass(width, height);
//       DrawOpaqueScene();          // front-to-back, LRZ/HSR friendly
//       DrawTransparentScene();
//       msaa.EndPass();             // depth invalidated, color resolved on-tile
//       PostProcess(msaa.ResolvedColorTexture());
//   } else {
//       DrawSceneSingleSample();    // graceful fallback, NEVER blit-resolve
//   }
// ============================================================================

int main() {
    LOGI("msaa_ontile_resolve: reference implementation — see header comments");
    return 0;
}
