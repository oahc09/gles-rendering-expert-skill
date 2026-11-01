// SPDX-License-Identifier: MIT
// Correctness harness, NOT a GPU performance benchmark or Android app.
#include <EGL/egl.h>
#include <GLES3/gl32.h>
#include <algorithm>
#include <array>
#include <cstdlib>
#include <fstream>
#include <future>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#define GLES_EXAMPLE_NO_MAIN
#include "../../references/examples/pbo_streaming_upload.cpp"

static void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
static void gl_ok(const char* where) { if (glGetError() != GL_NO_ERROR) throw std::runtime_error(where); }
static std::string quoted(const char* s) {
    std::string out = "\"";
    for (const unsigned char c : std::string(s ? s : "unavailable")) {
        if (c == '"' || c == '\\') out += '\\';
        if (c >= 32) out += static_cast<char>(c); else out += ' ';
    }
    return out + '"';
}
static void pass(const char* id) { std::cout << "{\"case\":" << quoted(id) << ",\"status\":\"PASS\"}\n"; }
struct EGLSession {
    EGLDisplay display = EGL_NO_DISPLAY;
    EGLConfig config{};
    EGLContext context = EGL_NO_CONTEXT;
    EGLSurface surface = EGL_NO_SURFACE;
    EGLSurface make_surface(int size = 8) {
        const EGLint attrs[] = {EGL_WIDTH, size, EGL_HEIGHT, size, EGL_NONE};
        EGLSurface s = eglCreatePbufferSurface(display, config, attrs);
        require(s != EGL_NO_SURFACE, "eglCreatePbufferSurface"); return s;
    }
    EGLContext make_context(EGLContext shared = EGL_NO_CONTEXT) {
        const EGLint attrs[] = {EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE};
        EGLContext c = eglCreateContext(display, config, shared, attrs);
        require(c != EGL_NO_CONTEXT, "eglCreateContext GLES3"); return c;
    }
    void current() { require(eglMakeCurrent(display, surface, surface, context), "eglMakeCurrent"); }
    void release() { require(eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT), "egl release"); }
    void open() {
        display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
        EGLint major = 0, minor = 0;
        require(display != EGL_NO_DISPLAY && eglInitialize(display, &major, &minor), "eglInitialize (headless Mesa: EGL_PLATFORM=surfaceless)");
        require(eglBindAPI(EGL_OPENGL_ES_API), "eglBindAPI");
        const EGLint attrs[] = {EGL_SURFACE_TYPE, EGL_PBUFFER_BIT, EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT,
            EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8, EGL_NONE};
        EGLint count = 0;
        require(eglChooseConfig(display, attrs, &config, 1, &count) && count == 1, "eglChooseConfig");
        surface = make_surface(); context = make_context(); current();
    }
    ~EGLSession() {
        if (display != EGL_NO_DISPLAY) {
            eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
            if (surface != EGL_NO_SURFACE) eglDestroySurface(display, surface);
            if (context != EGL_NO_CONTEXT) eglDestroyContext(display, context);
            eglTerminate(display);
        }
    }
    EGLSession() = default;
    EGLSession(const EGLSession&) = delete;
    EGLSession& operator=(const EGLSession&) = delete;
};
static void snapshot(EGLSession& s) {
    GLint major=0, minor=0, maxTexture=0, maxAttachments=0, count=0;
    glGetIntegerv(GL_MAJOR_VERSION, &major); glGetIntegerv(GL_MINOR_VERSION, &minor);
    glGetIntegerv(GL_MAX_TEXTURE_SIZE, &maxTexture); glGetIntegerv(GL_MAX_COLOR_ATTACHMENTS, &maxAttachments);
    glGetIntegerv(GL_NUM_EXTENSIONS, &count);
    std::cout << "{\"CapabilitySnapshot\":{\"platform\":\"host EGL pbuffer\",\"android_api\":null,\"angle_backend\":null,"
        << "\"egl_vendor\":" << quoted(eglQueryString(s.display,EGL_VENDOR))
        << ",\"egl_version\":" << quoted(eglQueryString(s.display,EGL_VERSION))
        << ",\"egl_extensions\":" << quoted(eglQueryString(s.display,EGL_EXTENSIONS))
        << ",\"gl_vendor\":" << quoted(reinterpret_cast<const char*>(glGetString(GL_VENDOR)))
        << ",\"gl_renderer\":" << quoted(reinterpret_cast<const char*>(glGetString(GL_RENDERER)))
        << ",\"gl_version\":" << quoted(reinterpret_cast<const char*>(glGetString(GL_VERSION)))
        << ",\"gles_major\":" << major << ",\"gles_minor\":" << minor
        << ",\"max_texture_size\":" << maxTexture << ",\"max_color_attachments\":" << maxAttachments
        << ",\"glFenceSync_entrypoint\":" << (eglGetProcAddress("glFenceSync") ? "true":"false")
        << ",\"gl_extensions\":[";
    for (GLint i=0; i<count; ++i) {
        if(i) std::cout << ',';
        std::cout << quoted(reinterpret_cast<const char*>(glGetStringi(GL_EXTENSIONS,static_cast<GLuint>(i))));
    }
    std::cout << "]}}\n"; gl_ok("snapshot");
}
static void read_pixel(const std::array<GLubyte,4>& expected) {
    std::array<GLubyte,4> actual{};
    glReadPixels(0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE,actual.data());
    gl_ok("read pixel"); require(actual == expected,"pixel mismatch");
}
static void framebuffer_and_formats() {
    glBindFramebuffer(GL_FRAMEBUFFER,0); glReadBuffer(GL_BACK); gl_ok("C01 default BACK legal");
    glReadBuffer(GL_FRONT); require(glGetError()==GL_INVALID_ENUM,"C01 GL_FRONT must fail");
    GLuint tex=0,fbo=0,depth=0;
    glGenTextures(1,&tex); glBindTexture(GL_TEXTURE_2D,tex);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,4,4,0,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);
    gl_ok("C02 sized RGBA8 legal");
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8UI,4,4,0,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);
    require(glGetError()==GL_INVALID_OPERATION,"C02 integer mismatch must fail");
    glGenFramebuffers(1,&fbo); glBindFramebuffer(GL_FRAMEBUFFER,fbo);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,tex,0);
    glGenRenderbuffers(1,&depth); glBindRenderbuffer(GL_RENDERBUFFER,depth);
    glRenderbufferStorage(GL_RENDERBUFFER,GL_DEPTH_COMPONENT16,4,4);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_RENDERBUFFER,depth);
    require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"C06 complete FBO");
    glReadBuffer(GL_COLOR_ATTACHMENT0); gl_ok("C01 FBO read attachment legal");
    glReadBuffer(GL_BACK); require(glGetError()==GL_INVALID_OPERATION,"C01 FBO BACK must fail");
    glReadBuffer(GL_COLOR_ATTACHMENT0);
    glViewport(0,0,4,4); glClearColor(1,0,0,1); glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
    read_pixel({255,0,0,255});
    const GLenum discard=GL_DEPTH_ATTACHMENT;
    glInvalidateFramebuffer(GL_FRAMEBUFFER,1,&discard); gl_ok("C06 depth invalidate");
    read_pixel({255,0,0,255}); // Never inspect invalidated depth: its contents are undefined.
    glBindFramebuffer(GL_FRAMEBUFFER,0);
    glDeleteRenderbuffers(1,&depth); glDeleteFramebuffers(1,&fbo); glDeleteTextures(1,&tex);
    pass("C01-read-buffer-positive-negative"); pass("C02-format-positive-negative"); pass("C06-preserve-color-after-depth-invalidate");
}
// CPU/PBO transfer correctness, not evidence of asynchronous speedup.
static void legacy_pbo_regression() {
    GLuint texture=0,fbo=0;
    glGenTextures(1,&texture); glBindTexture(GL_TEXTURE_2D,texture);
    glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,1,1);
    glGenFramebuffers(1,&fbo); glBindFramebuffer(GL_FRAMEBUFFER,fbo);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
    require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"streaming FBO");
    glReadBuffer(GL_COLOR_ATTACHMENT0);
    {
        PboStreamingUploader uploader;
        require(uploader.Init(4),"streaming Init");
        require(!uploader.CommitUpload(texture,0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE),"reject upload without mapping");
        for(int frame=0;frame<8;++frame) {
            const std::array<GLubyte,4> expected{static_cast<GLubyte>(frame*20),128,255,255};
            void* pointer=uploader.MapWriteSlot(); require(pointer!=nullptr,"streaming map");
            std::copy(expected.begin(),expected.end(),static_cast<GLubyte*>(pointer));
            require(uploader.CommitUpload(texture,0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE),"streaming commit after unmap");
            read_pixel(expected);
        }
    } // Owned GL resources destroyed before context teardown.
    glBindFramebuffer(GL_FRAMEBUFFER,0); glDeleteFramebuffers(1,&fbo); glDeleteTextures(1,&texture);
    pass("W4-legacy-PBO-eight-frame-reuse-regression");
}
static void pbo_upload() {
    GLuint pbo=0,tex=0,fbo=0;
    const std::array<GLubyte,4> expected{0,0,255,255};
    glGenBuffers(1,&pbo); glBindBuffer(GL_PIXEL_UNPACK_BUFFER,pbo);
    glBufferData(GL_PIXEL_UNPACK_BUFFER,4,nullptr,GL_STREAM_DRAW);
    void* mapped=glMapBufferRange(GL_PIXEL_UNPACK_BUFFER,0,4,GL_MAP_WRITE_BIT|GL_MAP_INVALIDATE_BUFFER_BIT);
    require(mapped!=nullptr,"PBO map");
    std::copy(expected.begin(),expected.end(),static_cast<GLubyte*>(mapped));
    require(glUnmapBuffer(GL_PIXEL_UNPACK_BUFFER)==GL_TRUE,"PBO unmap");
    glGenTextures(1,&tex); glBindTexture(GL_TEXTURE_2D,tex);
    glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,1,1);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);
    GLsync fence=glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE,0); require(fence!=nullptr,"PBO fence");
    glFlush();
    GLenum status=GL_TIMEOUT_EXPIRED;
    // Bounded test wait. Production retains a timed-out slot for later polling.
    for(int attempt=0; attempt<100 && status==GL_TIMEOUT_EXPIRED; ++attempt)
        status=glClientWaitSync(fence,0,10000000ULL);
    require(status==GL_ALREADY_SIGNALED || status==GL_CONDITION_SATISFIED,"PBO fence timeout/failure: no reuse");
    glBindBuffer(GL_PIXEL_UNPACK_BUFFER,0);
    glGenFramebuffers(1,&fbo); glBindFramebuffer(GL_FRAMEBUFFER,fbo);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,tex,0);
    require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"PBO FBO");
    glReadBuffer(GL_COLOR_ATTACHMENT0); read_pixel(expected);
    glBindFramebuffer(GL_FRAMEBUFFER,0); glDeleteFramebuffers(1,&fbo);
    glDeleteSync(fence); glDeleteBuffers(1,&pbo); glDeleteTextures(1,&tex);
    pass("W4-PBO-map-unmap-upload-fence-pixel");
}
struct Upload { GLuint texture=0; GLsync fence=nullptr; };
static void shared_upload(EGLSession& s) {
    EGLContext workerContext=s.make_context(s.context);
    EGLSurface workerSurface=s.make_surface();
    std::promise<Upload> result; auto future=result.get_future();
    std::thread worker([&] {
        try {
            require(eglMakeCurrent(s.display,workerSurface,workerSurface,workerContext),"worker current");
            Upload u;
            glGenTextures(1,&u.texture); glBindTexture(GL_TEXTURE_2D,u.texture);
            const std::array<GLubyte,4> pixel{0,255,0,255};
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,1,1,0,GL_RGBA,GL_UNSIGNED_BYTE,pixel.data());
            u.fence=glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE,0);
            require(u.fence!=nullptr,"worker fence"); glFlush(); gl_ok("worker upload+flush");
            // Promise/future provides CPU happens-before publication of both handles.
            result.set_value(u);
        } catch (...) { result.set_exception(std::current_exception()); }
        eglMakeCurrent(s.display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);
    });
    worker.join(); // worker releases its context; the share-group objects remain alive.
    try {
        const Upload u=future.get();
        glWaitSync(u.fence,0,GL_TIMEOUT_IGNORED); glBindTexture(GL_TEXTURE_2D,u.texture);
        GLuint fbo=0; glGenFramebuffers(1,&fbo); glBindFramebuffer(GL_FRAMEBUFFER,fbo);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,u.texture,0);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"shared FBO");
        glReadBuffer(GL_COLOR_ATTACHMENT0); read_pixel({0,255,0,255});
        glBindFramebuffer(GL_FRAMEBUFFER,0); glDeleteFramebuffers(1,&fbo);
        // Blocking readback above establishes completion before lifetime cleanup in this test.
        glDeleteSync(u.fence); glDeleteTextures(1,&u.texture);
    } catch (...) {
        eglDestroySurface(s.display,workerSurface); eglDestroyContext(s.display,workerContext); throw;
    }
    eglDestroySurface(s.display,workerSurface); eglDestroyContext(s.display,workerContext);
    pass("C03-shared-context-fence-flush-wait-pixel");
}
static std::string load(const std::string& path) {
    std::ifstream input(path); require(input.good(),("missing shader "+path).c_str());
    return {std::istreambuf_iterator<char>(input),std::istreambuf_iterator<char>()};
}
static GLuint compile(GLenum stage,const std::string& source,bool expected,const std::string& name) {
    GLuint shader=glCreateShader(stage); require(shader!=0,"create shader");
    const char* p=source.c_str(); glShaderSource(shader,1,&p,nullptr); glCompileShader(shader);
    GLint ok=0; glGetShaderiv(shader,GL_COMPILE_STATUS,&ok);
    if ((ok==GL_TRUE)!=expected) {
        std::array<char,4096> log{}; glGetShaderInfoLog(shader,static_cast<GLsizei>(log.size()),nullptr,log.data());
        glDeleteShader(shader); throw std::runtime_error(name+": unexpected compile result: "+log.data());
    }
    if(!expected) { glDeleteShader(shader); return 0; }
    return shader;
}
static void shaders(const std::string& directory) {
    GLint major=0,minor=0; glGetIntegerv(GL_MAJOR_VERSION,&major); glGetIntegerv(GL_MINOR_VERSION,&minor);
    for (int version : {300,310,320}) {
        if (major*100+minor*10<version) {
            std::cout << "{\"case\":\"GLSL-"<<version<<"\",\"status\":\"UNSUPPORTED\"}\n"; continue;
        }
        const auto base=directory+"/"+std::to_string(version);
        GLuint vs=compile(GL_VERTEX_SHADER,load(base+".vert"),true,base+".vert");
        GLuint fs=compile(GL_FRAGMENT_SHADER,load(base+".frag"),true,base+".frag");
        GLuint program=glCreateProgram(); glAttachShader(program,vs); glAttachShader(program,fs); glLinkProgram(program);
        GLint linked=0; glGetProgramiv(program,GL_LINK_STATUS,&linked);
        glDeleteShader(vs); glDeleteShader(fs); glDeleteProgram(program);
        require(linked==GL_TRUE,"shader pair link");
        compile(GL_FRAGMENT_SHADER,load(base+"-invalid.frag"),false,base+"-invalid.frag");
        std::cout<<"{\"case\":\"GLSL-"<<version<<"-compile-link-and-negative\",\"status\":\"PASS\"}\n";
    }
    struct Fixture { const char* file; GLenum stage; int version; bool expected; };
    for(const Fixture f : {
        Fixture{"300-binding-invalid.frag",GL_FRAGMENT_SHADER,300,false},
        Fixture{"300-compute-invalid.comp",GL_COMPUTE_SHADER,310,false},
        Fixture{"300-ssbo-invalid.frag",GL_FRAGMENT_SHADER,300,false},
        Fixture{"310-geometry-invalid.geom",GL_GEOMETRY_SHADER,320,false},
        Fixture{"310-binding.frag",GL_FRAGMENT_SHADER,310,true},
        Fixture{"310-compute.comp",GL_COMPUTE_SHADER,310,true},
        Fixture{"310-ssbo.frag",GL_FRAGMENT_SHADER,310,true},
        Fixture{"320-geometry.geom",GL_GEOMETRY_SHADER,320,true}}) {
        if(major*100+minor*10<f.version) {
            std::cout<<"{\"case\":"<<quoted(f.file)<<",\"status\":\"UNSUPPORTED\"}\n"; continue;
        }
        GLuint shader=compile(f.stage,load(directory+"/"+f.file),f.expected,f.file);
        if(shader) glDeleteShader(shader);
        pass(f.file);
    }
    for(bool mismatch : {false,true}) {
        GLuint vs=compile(GL_VERTEX_SHADER,load(directory+"/300-precision.vert"),true,"precision vertex");
        GLuint fs=compile(GL_FRAGMENT_SHADER,load(directory+(mismatch?"/300-interface-type-mismatch.frag":"/300-precision.frag")),true,"interface fragment");
        GLuint program=glCreateProgram(); glAttachShader(program,vs); glAttachShader(program,fs); glLinkProgram(program);
        GLint linked=0; glGetProgramiv(program,GL_LINK_STATUS,&linked);
        glDeleteProgram(program); glDeleteShader(vs); glDeleteShader(fs);
        require((linked==GL_TRUE)==!mismatch,"C11 interface link expectation");
        pass(mismatch ? "C11-interface-type-mismatch-rejected":"C11-varying-precision-difference-legal");
    }
    gl_ok("shader tests");
}
static void lifecycle(EGLSession& s) {
    GLuint retained=0; glGenTextures(1,&retained); glBindTexture(GL_TEXTURE_2D,retained);
    glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,1,1); gl_ok("retained texture");
    s.release(); require(eglDestroySurface(s.display,s.surface),"destroy surface"); s.surface=EGL_NO_SURFACE;
    s.surface=s.make_surface(16); s.current();
    require(glIsTexture(retained)==GL_TRUE,"surface recreation preserves texture");
    EGLint width=0; require(eglQuerySurface(s.display,s.surface,EGL_WIDTH,&width)&&width==16,"resize query");
    glDeleteTextures(1,&retained); pass("C04-surface-recreate-resize-preserves-context");
    // Controlled teardown exercises rebuilding, but does NOT inject EGL_CONTEXT_LOST.
    s.release(); require(eglDestroyContext(s.display,s.context),"destroy context"); s.context=EGL_NO_CONTEXT;
    s.context=s.make_context(); s.current(); framebuffer_and_formats();
    pass("C04-controlled-context-rebuild-not-driver-loss");
}
int main(int argc,char** argv) {
    try {
        EGLSession session; session.open(); snapshot(session);
        framebuffer_and_formats(); shared_upload(session); pbo_upload(); legacy_pbo_regression();
        shaders(argc>1 ? argv[1] : "examples/validation/shaders"); lifecycle(session);
        std::cout << "{\"real_android_lifecycle\":\"NOT_RUN\",\"driver_context_loss\":\"NOT_INJECTED\",\"mobile_gpu_performance\":\"BLOCKED_BY_HARDWARE\"}\n";
    } catch(const std::exception& e) { std::cerr << "FAIL: "<<e.what()<<'\n'; return 1; }
    return 0;
}
