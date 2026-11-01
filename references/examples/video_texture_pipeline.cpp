/**
 * @file video_texture_pipeline.cpp
 * @brief Android video/camera frame rendering via GL_OES_EGL_image_external.
 *
 * Scenario: MediaCodec decoder (or Camera2) frames are delivered through a
 *           SurfaceTexture; each frame is sampled by an external OES texture
 *           and drawn as a full-screen quad with zero CPU copies.
 * Target:   OpenGL ES 3.0+ / C++17 / Android NDK
 *
 * Rules reference: references/rules/android-interoperability.md
 *
 * Key points demonstrated:
 *  - GL_TEXTURE_EXTERNAL_OES target with CLAMP_TO_EDGE + linear filtering
 *  - Runtime extension check (GL_OES_EGL_image_external)
 *  - Per-frame update driven by SurfaceTexture::updateTexImage() (JNI side)
 *  - Optional copy-out to a regular GL_TEXTURE_2D FBO when a CPU-readable
 *    or mappable copy is genuinely needed (never glReadPixels the external
 *    texture directly)
 */

#include <GLES3/gl3.h>
#include <GLES3/gl3ext.h>
#include <GLES2/gl2ext.h>
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <cstdio>
#include <cstring>
#include <utility>

#define LOGI(...) printf("[INFO] " __VA_ARGS__), printf("\n")
#define LOGE(...) printf("[ERROR] " __VA_ARGS__), printf("\n")

// GL_OES_EGL_image_external tokens are provided by the NDK's glext.h;
// guard for header completeness.
#ifndef GL_TEXTURE_EXTERNAL_OES
#define GL_TEXTURE_EXTERNAL_OES 0x8D65
#endif

// EGLImage handles are pointer-sized, not GLuint texture names.
using ImageTargetProc = PFNGLEGLIMAGETARGETTEXTURE2DOESPROC;

// ============================================================================
// RAII External Texture (GL_TEXTURE_EXTERNAL_OES)
// ============================================================================
class ExternalTexture {
public:
    ExternalTexture() = default;
    ~ExternalTexture() { Destroy(); }

    ExternalTexture(const ExternalTexture&) = delete;
    ExternalTexture& operator=(const ExternalTexture&) = delete;
    ExternalTexture(ExternalTexture&& o) noexcept : id_(o.id_) { o.id_ = 0; }

    /// Create the external texture with the ONLY legal sampler state:
    /// CLAMP_TO_EDGE wrap + NEAREST/LINEAR filter, no mipmaps.
    bool Create() {
        glGenTextures(1, &id_);
        if (id_ == 0) return false;
        glBindTexture(GL_TEXTURE_EXTERNAL_OES, id_);
        glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glBindTexture(GL_TEXTURE_EXTERNAL_OES, 0);
        return true;
    }

    void Bind(GLuint unit) const {
        glActiveTexture(GL_TEXTURE0 + unit);
        glBindTexture(GL_TEXTURE_EXTERNAL_OES, id_);
    }

    GLuint Id() const { return id_; }

private:
    void Destroy() {
        if (id_ != 0) { glDeleteTextures(1, &id_); id_ = 0; }
    }
    GLuint id_ = 0;
};

// ============================================================================
// RAII Program (minimal: compile + link with error logging)
// ============================================================================
class ShaderProgram {
public:
    ShaderProgram() = default;
    ~ShaderProgram() {
        if (program_ != 0) glDeleteProgram(program_);
        if (vs_ != 0) glDeleteShader(vs_);
        if (fs_ != 0) glDeleteShader(fs_);
    }
    ShaderProgram(const ShaderProgram&) = delete;
    ShaderProgram& operator=(const ShaderProgram&) = delete;

    bool Build(const char* vertSrc, const char* fragSrc) {
        vs_ = Compile(GL_VERTEX_SHADER, vertSrc);
        fs_ = Compile(GL_FRAGMENT_SHADER, fragSrc);
        if (vs_ == 0 || fs_ == 0) return false;
        program_ = glCreateProgram();
        glAttachShader(program_, vs_);
        glAttachShader(program_, fs_);
        glLinkProgram(program_);
        GLint ok = GL_FALSE;
        glGetProgramiv(program_, GL_LINK_STATUS, &ok);
        if (!ok) {
            char log[1024];
            glGetProgramInfoLog(program_, sizeof(log), nullptr, log);
            LOGE("Link failed: %s", log);
            return false;
        }
        return true;
    }

    void Use() const { glUseProgram(program_); }
    GLint Uniform(const char* name) const { return glGetUniformLocation(program_, name); }

private:
    GLuint Compile(GLenum type, const char* src) {
        GLuint s = glCreateShader(type);
        glShaderSource(s, 1, &src, nullptr);
        glCompileShader(s);
        GLint ok = GL_FALSE;
        glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
        if (!ok) {
            char log[1024];
            glGetShaderInfoLog(s, sizeof(log), nullptr, log);
            LOGE("Shader compile failed: %s", log);
            glDeleteShader(s);
            return 0;
        }
        return s;
    }
    GLuint vs_ = 0, fs_ = 0, program_ = 0;
};

// ============================================================================
// Shaders — samplerExternalOES requires the extension directive.
// #version must be the first line of each source.
// ============================================================================
static const char* kQuadVert = R"(#version 300 es
layout(location = 0) in vec2 a_Position;
layout(location = 1) in vec2 a_TexCoord;
// SurfaceTexture supplies a transform matrix (rotation/crop per device sensor)
uniform mat4 u_STMatrix;
out vec2 v_TexCoord;
void main() {
    gl_Position = vec4(a_Position, 0.0, 1.0);
    v_TexCoord = (u_STMatrix * vec4(a_TexCoord, 0.0, 1.0)).xy;
}
)";

static const char* kExternalFrag = R"(#version 300 es
#extension GL_OES_EGL_image_external_essl3 : require
precision mediump float;
uniform samplerExternalOES u_VideoFrame;
in vec2 v_TexCoord;
layout(location = 0) out vec4 o_Color;
void main() {
    // YUV->RGB conversion is done by the hardware for OES external images.
    o_Color = texture(u_VideoFrame, v_TexCoord);
}
)";

// ============================================================================
// Video Texture Pipeline
// ============================================================================
class VideoTexturePipeline {
public:
    VideoTexturePipeline() = default;
    /// Must be called with a current EGL context. Returns false when the
    /// device lacks GL_OES_EGL_image_external (no usable video path).
    bool Init() {
        if (!HasExtension("GL_OES_EGL_image_external") ||
            !HasExtension("GL_OES_EGL_image_external_essl3")) {
            LOGE("External image / ESSL3 extension unavailable — use regular 2D fallback");
            return false;
        }
        // glEGLImageTargetTexture2DOES is an OES entry point; the NDK exposes
        // it in glext.h, but resolve defensively.
        glBindTextureTarget_ = reinterpret_cast<ImageTargetProc>(
            eglGetProcAddress("glEGLImageTargetTexture2DOES"));
        if (glBindTextureTarget_ == nullptr) return false;

        if (!externalTex_.Create()) return false;
        if (!program_.Build(kQuadVert, kExternalFrag)) return false;
        CreateQuadVao();
        u_STMatrix_ = program_.Uniform("u_STMatrix");
        u_Frame_ = program_.Uniform("u_VideoFrame");
        LOGI("Video texture pipeline initialized (external tex id=%u)", externalTex_.Id());
        return true;
    }

    /// Bind the decoder/camera EGLImage to the external texture.
    /// Called when the producer switches buffers (not necessarily every frame).
    void AttachImage(EGLImageKHR image) {
        if (glBindTextureTarget_ != nullptr) {
            glBindTexture(GL_TEXTURE_EXTERNAL_OES, externalTex_.Id());
            glBindTextureTarget_(GL_TEXTURE_EXTERNAL_OES,
                                 reinterpret_cast<GLeglImageOES>(image));
            glBindTexture(GL_TEXTURE_EXTERNAL_OES, 0);
        }
    }

    /// Per-frame draw. Preconditions:
    ///   1. JNI side already called SurfaceTexture::updateTexImage()
    ///   2. SurfaceTexture::getTransformMatrix() copied into stMatrix
    void DrawFrame(const float stMatrix[16], GLint viewportW, GLint viewportH) {
        glViewport(0, 0, viewportW, viewportH);
        // Full-screen overwrite: no depth buffer needed; clear color only.
        glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        program_.Use();
        glUniformMatrix4fv(u_STMatrix_, 1, GL_FALSE, stMatrix);
        externalTex_.Bind(0);
        glUniform1i(u_Frame_, 0);

        glBindVertexArray(quadVao_);
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
        glBindVertexArray(0);
    }

    /// Optional: copy the current external frame into a plain GL_TEXTURE_2D
    /// (e.g. for later CPU readback via PBO). NEVER glReadPixels directly
    /// from an external texture.
    bool CopyOutToTexture2D(GLuint dstTex2D, GLsizei w, GLsizei h) {
        if (copyFbo_ == 0) glGenFramebuffers(1, &copyFbo_);
        glBindFramebuffer(GL_FRAMEBUFFER, copyFbo_);
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                               GL_TEXTURE_2D, dstTex2D, 0);
        if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) {
            LOGE("Copy-out FBO incomplete");
            glBindFramebuffer(GL_FRAMEBUFFER, 0);
            return false;
        }
        DrawFrame(identityMatrix_, w, h);
        glBindFramebuffer(GL_FRAMEBUFFER, 0);
        return true;
    }

    ~VideoTexturePipeline() {
        if (quadVbo_ != 0) glDeleteBuffers(1, &quadVbo_);
        if (quadVao_ != 0) glDeleteVertexArrays(1, &quadVao_);
        if (copyFbo_ != 0) glDeleteFramebuffers(1, &copyFbo_);
    }
    VideoTexturePipeline(const VideoTexturePipeline&) = delete;
    VideoTexturePipeline& operator=(const VideoTexturePipeline&) = delete;

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

    void CreateQuadVao() {
        // Full-screen quad: position (NDC) + texcoord pairs
        static const float kVerts[] = {
            -1.f, -1.f,  0.f, 0.f,
             1.f, -1.f,  1.f, 0.f,
            -1.f,  1.f,  0.f, 1.f,
             1.f,  1.f,  1.f, 1.f,
        };
        glGenVertexArrays(1, &quadVao_);
        glGenBuffers(1, &quadVbo_);
        glBindVertexArray(quadVao_);
        glBindBuffer(GL_ARRAY_BUFFER, quadVbo_);
        glBufferData(GL_ARRAY_BUFFER, sizeof(kVerts), kVerts, GL_STATIC_DRAW);
        glEnableVertexAttribArray(0);
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), nullptr);
        glEnableVertexAttribArray(1);
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float),
                              reinterpret_cast<const void*>(2 * sizeof(float)));
        glBindVertexArray(0);
    }

    ExternalTexture externalTex_;
    ShaderProgram program_;
    ImageTargetProc glBindTextureTarget_ = nullptr;
    GLuint quadVao_ = 0, quadVbo_ = 0, copyFbo_ = 0;
    GLint u_STMatrix_ = -1, u_Frame_ = -1;
    static constexpr float identityMatrix_[16] = {
        1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1
    };
};

// ============================================================================
// Host-side integration sketch (Android JNI glue, pseudo-code):
//
//   // One-time: create SurfaceTexture on the external texture id
//   jobject surfaceTexture = SurfaceTexture_new(videoPipeline.externalTexId());
//   // MediaCodec.configure(..., new Surface(surfaceTexture), ..., 0)
//
//   // Frame-arrival callback (onFrameAvailable):
//   //   SurfaceTexture_updateTexImage(surfaceTexture);
//   //   SurfaceTexture_getTransformMatrix(surfaceTexture, stMatrix);
//   //   videoPipeline.DrawFrame(stMatrix, w, h);
// ============================================================================

int main() {
    // In a real app the EGL context is created by the engine
    // (see egl_context_manager.cpp). This entry point exists only so the
    // example compiles as a translation unit for CI/audit purposes.
    LOGI("video_texture_pipeline: reference implementation — see header comments");
    return 0;
}
