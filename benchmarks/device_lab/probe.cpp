// SPDX-License-Identifier: MIT
// Reuse the established EGL lifetime and JSON helpers without changing the old harness.
#define main established_harness_main
#include "../../examples/validation/egl_smoke.cpp"
#undef main
static bool renderable(GLenum format, GLenum type) {
    GLuint t=0,f=0;glGenTextures(1,&t);glBindTexture(GL_TEXTURE_2D,t);
    glTexImage2D(GL_TEXTURE_2D,0,static_cast<GLint>(format),4,4,0,GL_RGBA,type,nullptr);
    const bool allocated=glGetError()==GL_NO_ERROR;
    glGenFramebuffers(1,&f);glBindFramebuffer(GL_FRAMEBUFFER,f);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,t,0);
    const bool complete=glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE;
    const bool clean=glGetError()==GL_NO_ERROR;
    glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteFramebuffers(1,&f);glDeleteTextures(1,&t);
    return allocated&&complete&&clean;
}
int main() {
    try {
        EGLSession s;s.open();snapshot(s);
        GLint med[2]={},high[2]={},mp=0,hp=0,ubo=0,binaries=0,maxSamples=0;
        glGetShaderPrecisionFormat(GL_FRAGMENT_SHADER,GL_MEDIUM_FLOAT,med,&mp);
        glGetShaderPrecisionFormat(GL_FRAGMENT_SHADER,GL_HIGH_FLOAT,high,&hp);
        glGetIntegerv(GL_UNIFORM_BUFFER_OFFSET_ALIGNMENT,&ubo);
        glGetIntegerv(GL_NUM_PROGRAM_BINARY_FORMATS,&binaries);
        glGetIntegerv(GL_MAX_SAMPLES,&maxSamples);gl_ok("precision and limits");
        const bool rgba8=renderable(GL_RGBA8,GL_UNSIGNED_BYTE),rgba16=renderable(GL_RGBA16F,GL_HALF_FLOAT);
        std::cout << "{\"extended_probe\":{\"glsl_version\":" << quoted(reinterpret_cast<const char*>(glGetString(GL_SHADING_LANGUAGE_VERSION)))
        << ",\"precision\":{\"fragment_mediump\":{\"range\":["<<med[0]<<","<<med[1]<<"],\"bits\":"<<mp<<"},\"fragment_highp\":{\"range\":["<<high[0]<<","<<high[1]<<"],\"bits\":"<<hp<<"}},"
        << "\"limits\":{\"ubo_offset_alignment\":"<<ubo<<",\"program_binary_format_count\":"<<binaries<<",\"max_samples\":"<<maxSamples<<"},"
        << "\"formats\":{\"RGBA8_fbo\":"<<(rgba8?"true":"false")<<",\"RGBA16F_fbo\":"<<(rgba16?"true":"false")<<"},"
        << "\"function_entries\":{\"eglCreateImageKHR\":"<<(eglGetProcAddress("eglCreateImageKHR")?"true":"false")<<",\"eglGetNativeClientBufferANDROID\":"<<(eglGetProcAddress("eglGetNativeClientBufferANDROID")?"true":"false")<<",\"glEGLImageTargetTexture2DOES\":"<<(eglGetProcAddress("glEGLImageTargetTexture2DOES")?"true":"false")<<"},"
        << "\"runtime_import_probes\":{\"AHardwareBuffer\":null,\"external_texture\":null,\"HDR_display\":null}}}\n";
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
