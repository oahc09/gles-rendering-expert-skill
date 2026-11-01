// SPDX-License-Identifier: MIT
// Deterministic GLES scene correctness lab. Wall time is NOT GPU timing.
#include <EGL/egl.h>
#include <GLES3/gl31.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
static void require(bool p, const char *m) {
  if (!p)
    throw std::runtime_error(m);
}
static void check(const char *m) {
  if (glGetError() != GL_NO_ERROR)
    throw std::runtime_error(m);
}
static std::string quote(const char *p) {
  std::string s = "\"";
  for (char c : std::string(p ? p : "unknown")) {
    if (c == '"' || c == '\\')
      s += '\\';
    s += (c >= 32 ? c : ' ');
  }
  return s + '"';
}
struct Context {
  EGLDisplay d = EGL_NO_DISPLAY;
  EGLContext c = EGL_NO_CONTEXT;
  EGLSurface s = EGL_NO_SURFACE;
  Context() {
    d = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    EGLint a, b, n;
    require(eglInitialize(d, &a, &b), "EGL initialize");
    require(eglBindAPI(EGL_OPENGL_ES_API), "EGL bind");
    EGLConfig cfg;
    const EGLint ca[] = {EGL_SURFACE_TYPE,
                         EGL_PBUFFER_BIT,
                         EGL_RENDERABLE_TYPE,
                         EGL_OPENGL_ES3_BIT,
                         EGL_RED_SIZE,
                         8,
                         EGL_GREEN_SIZE,
                         8,
                         EGL_BLUE_SIZE,
                         8,
                         EGL_NONE};
    require(eglChooseConfig(d, ca, &cfg, 1, &n) && n == 1, "EGL config");
    const EGLint sa[] = {EGL_WIDTH, 1, EGL_HEIGHT, 1, EGL_NONE};
    s = eglCreatePbufferSurface(d, cfg, sa);
    const EGLint cc[] = {EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE};
    c = eglCreateContext(d, cfg, EGL_NO_CONTEXT, cc);
    require(s != EGL_NO_SURFACE && c != EGL_NO_CONTEXT &&
                eglMakeCurrent(d, s, s, c),
            "EGL current");
    GLint ma, mi;
    glGetIntegerv(GL_MAJOR_VERSION, &ma);
    glGetIntegerv(GL_MINOR_VERSION, &mi);
    require(ma > 3 || (ma == 3 && mi >= 1),
            "BLOCKED_BY_CAPABILITY: GLES 3.1 required; CPU fallback is not "
            "silently substituted");
  }
  ~Context() {
    eglMakeCurrent(d, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
    eglDestroyContext(d, c);
    eglDestroySurface(d, s);
    eglTerminate(d);
  }
};
static GLuint shader(GLenum type, const std::string &code) {
  GLuint s = glCreateShader(type);
  const char *p = code.c_str();
  glShaderSource(s, 1, &p, nullptr);
  glCompileShader(s);
  GLint ok;
  glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
  if (!ok) {
    char log[4096];
    glGetShaderInfoLog(s, 4096, nullptr, log);
    glDeleteShader(s);
    throw std::runtime_error(log);
  }
  return s;
}
static GLuint program(const std::string &vs, const std::string &fs) {
  GLuint p = glCreateProgram(), v = shader(GL_VERTEX_SHADER, vs),
         f = shader(GL_FRAGMENT_SHADER, fs);
  glAttachShader(p, v);
  glAttachShader(p, f);
  glLinkProgram(p);
  glDeleteShader(v);
  glDeleteShader(f);
  GLint ok;
  glGetProgramiv(p, GL_LINK_STATUS, &ok);
  if (!ok) {
    char log[4096];
    glGetProgramInfoLog(p, 4096, nullptr, log);
    glDeleteProgram(p);
    throw std::runtime_error(log);
  }
  return p;
}
struct Target {
  GLuint f = 0, t = 0, z = 0;
  int w, h;
  bool hdr = false;
  Target(int width, int height, bool depth = false, bool half = false)
      : w(width), h(height) {
    glGenFramebuffers(1, &f);
    glBindFramebuffer(GL_FRAMEBUFFER, f);
    glGenTextures(1, &t);
    glBindTexture(GL_TEXTURE_2D, t);
    glTexStorage2D(GL_TEXTURE_2D, 1, half ? GL_RGBA16F : GL_RGBA8, w, h);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D,
                           t, 0);
    hdr = half;
    if (depth) {
      glGenTextures(1, &z);
      glBindTexture(GL_TEXTURE_2D, z);
      glTexStorage2D(GL_TEXTURE_2D, 1, GL_DEPTH_COMPONENT24, w, h);
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
      glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D,
                             z, 0);
    }
    require(glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE,
            "FBO unsupported (including half-float renderability)");
    check("target allocation");
  }
  void bind() {
    glBindFramebuffer(GL_FRAMEBUFFER, f);
    glViewport(0, 0, w, h);
  }
  ~Target() {
    glDeleteTextures(1, &t);
    if (z)
      glDeleteTextures(1, &z);
    glDeleteFramebuffers(1, &f);
  }
  Target(const Target &) = delete;
  Target &operator=(const Target &) = delete;
};
const std::string head = "#version 310 es\nprecision highp float;\n";
const std::string fullscreen = head + R"(
out vec2 uv;void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=p;gl_Position=vec4(p*2.-1.,0.,1.);})";
static void tex(GLuint p, const char *name, GLuint t, int unit) {
  glActiveTexture(GL_TEXTURE0 + unit);
  glBindTexture(GL_TEXTURE_2D, t);
  glUniform1i(glGetUniformLocation(p, name), unit);
}
static void pass(Target &out, const std::string &fs, GLuint a = 0,
                 GLuint b = 0) {
  out.bind();
  GLuint p = program(fullscreen, head + fs);
  glUseProgram(p);
  tex(p, "image", a, 0);
  tex(p, "extra", b, 1);
  glDrawArrays(GL_TRIANGLES, 0, 3);
  glDeleteProgram(p);
  check("fullscreen pass");
}
static void clear(Target &out) {
  out.bind();
  glDisable(GL_BLEND);
  glDisable(GL_DEPTH_TEST);
  glDisable(GL_STENCIL_TEST);
  glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
  glDepthMask(GL_TRUE);
  glClearColor(.025f, .045f, .085f, 1);
  glClearDepthf(1);
  glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
}
static void background(Target &out) {
  out.bind();
  glEnable(GL_DEPTH_TEST);
  GLuint p = program(fullscreen, head + R"(
in vec2 uv;out vec4 color;void main(){float ridge=.15*sin(uv.x*21.)*cos(uv.y*17.);color=vec4(.12+.13*uv.x,.22+.3*uv.y,.3+ridge,1);gl_FragDepth=.58+.25*uv.y;})");
  glUseProgram(p);
  glDrawArrays(GL_TRIANGLES, 0, 3);
  glDeleteProgram(p);
  glDisable(GL_DEPTH_TEST);
}
// Instance attributes: center.xy, size, phase. Independent fixed-seed LCG.
static std::vector<float> instances(int count, unsigned seed, float size) {
  std::vector<float> a;
  for (int i = 0; i < count; i++) {
    auto random = [&]() {
      seed = 1664525u * seed + 1013904223u;
      return float((seed >> 8) & 65535) / 65535.f;
    };
    a.push_back(random() * 1.8f - .9f);
    a.push_back(random() * 1.6f - .8f);
    a.push_back(size * (.65f + random() * .7f));
    a.push_back(random() * 6.2831853f);
  }
  return a;
}
const std::string instanced = head + R"(
layout(location=0)in vec4 data;out vec2 uv;out float phase;uniform float zvalue;
const vec2 corners[6]=vec2[6](vec2(-1,-1),vec2(1,-1),vec2(-1,1),vec2(-1,1),vec2(1,-1),vec2(1,1));
void main(){vec2 q=corners[gl_VertexID];uv=q*.5+.5;phase=data.w;gl_Position=vec4(data.xy+q*data.z,zvalue+data.w*.05,1);})";
static void draw_instances(const std::string &vertex,
                           const std::string &fragment, int count, float size,
                           GLuint image = 0, GLuint depth = 0,
                           unsigned seed = 1337, float z = 0,
                           bool orphan = true) {
  auto a = instances(count, seed, size);
  GLuint b, p = program(vertex, head + fragment);
  glGenBuffers(1, &b);
  glBindBuffer(GL_ARRAY_BUFFER, b);
  glBufferData(GL_ARRAY_BUFFER,
               static_cast<GLsizeiptr>(a.size() * sizeof(float)),
               orphan ? nullptr : a.data(), GL_STREAM_DRAW);
  if (orphan) {
    glBufferSubData(GL_ARRAY_BUFFER, 0,
                    static_cast<GLsizeiptr>(a.size() * sizeof(float)),
                    a.data());
  }
  glEnableVertexAttribArray(0);
  glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 4 * sizeof(float), nullptr);
  glVertexAttribDivisor(0, 1);
  glUseProgram(p);
  glUniform1f(glGetUniformLocation(p, "zvalue"), z);
  tex(p, "image", image, 0);
  tex(p, "extra", depth, 1);
  glDrawArraysInstanced(GL_TRIANGLES, 0, 6, count);
  glDisableVertexAttribArray(0);
  glVertexAttribDivisor(0, 0);
  glDeleteBuffers(1, &b);
  glDeleteProgram(p);
  check("instanced workload");
}
static void alpha() {
  glEnable(GL_BLEND);
  glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
}
static void cards(Target &out, int n, bool control, bool degraded) {
  clear(out);
  GLuint atlas;
  glGenTextures(1, &atlas);
  glBindTexture(GL_TEXTURE_2D, atlas);
  glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA8, 16, 16);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
  std::vector<GLubyte> pixels(16 * 16 * 4, 180);
  glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 16, 16, GL_RGBA, GL_UNSIGNED_BYTE,
                  pixels.data());
  std::array<GLubyte, 4 * 4 * 4> patch{};
  patch.fill(245);
  for (int y = 0; y < 16; y += 4) {
    for (int row = y; row < y + 4; row++) {
      for (int col = y; col < y + 4; col++) {
        for (int channel = 0; channel < 4; channel++) {
          pixels[(row * 16 + col) * 4 + channel] = 245;
        }
      }
    }
    if (control) {
      glTexSubImage2D(GL_TEXTURE_2D, 0, y, y, 4, 4, GL_RGBA, GL_UNSIGNED_BYTE,
                      patch.data());
    } else {
      glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 16, 16, GL_RGBA, GL_UNSIGNED_BYTE,
                      pixels.data());
    }
  }
  alpha();
  if (degraded)
    glDisable(GL_BLEND);
  draw_instances(
      instanced,
      R"(in vec2 uv;in float phase;uniform sampler2D image;out vec4 color;void main(){vec3 tint=.45+.4*cos(vec3(0,2,4)+phase);color=vec4(tint*texture(image,uv).r,.24+.18*uv.y);})",
      n, .22f, atlas);
  glDisable(GL_BLEND);
  glDeleteTextures(1, &atlas);
}
static void water(Target &out, int n, bool control, bool degraded) {
  Target seabed(out.w, out.h, true);
  clear(seabed);
  background(seabed);
  alpha();
  draw_instances(
      instanced,
      R"(in vec2 uv;in float phase;out vec4 color;void main(){color=vec4(.1,.5+.2*sin(phase),.3,.3);})",
      n / 4 + 1, .1f);
  glDisable(GL_BLEND);
  clear(out);
  pass(
      out,
      std::string("in vec2 uv;uniform sampler2D image;uniform sampler2D "
                  "extra;out vec4 color;void main(){") +
          (control ? "highp " : "mediump ") +
          R"(vec2 normal=vec2(sin(uv.y*30.+.7),cos(uv.x*24.-.4))*.012;float depth=texture(extra,uv).r;vec3 bed=texture(image,uv+)" +
          (degraded ? "normal*12." : "normal") +
          R"().rgb;float caustic=pow(abs(sin((uv.x+normal.x)*41.)*sin((uv.y+normal.y)*37.)),12.);color=vec4(mix(bed,vec3(.02,.35,.5),depth*.45)+caustic*.25*(1.-depth),1);})",
      seabed.t, seabed.z);
}
static void particles(Target &out, int n, bool control, bool degraded) {
  Target scene(out.w, out.h, true);
  clear(scene);
  background(scene);
  clear(out);
  pass(
      out,
      R"(in vec2 uv;uniform sampler2D image;out vec4 color;void main(){color=texture(image,uv);})",
      scene.t);
  alpha();
  std::string fs =
      R"(in vec2 uv;in float phase;uniform sampler2D extra;out vec4 color;void main(){float r=length(uv-.5)*2.;float d=texture(extra,gl_FragCoord.xy/vec2()" +
      std::to_string(out.w) + "," + std::to_string(out.h) +
      R"()).r;float soft=clamp((d-.65)*12.,0.,1.);color=vec4(1.,.45+.2*sin(phase),.1,(1.-smoothstep(.2,1.,r))*)" +
      (degraded ? "1." : "soft") + R"(*.45);})";
  draw_instances(instanced, fs, n, .09f, 0, scene.z, 1337, 0, !control);
  glDisable(GL_BLEND);
}
static bool has_extension(const char *wanted) {
  GLint n;
  glGetIntegerv(GL_NUM_EXTENSIONS, &n);
  for (GLint i = 0; i < n; i++)
    if (std::string(reinterpret_cast<const char *>(
            glGetStringi(GL_EXTENSIONS, i))) == wanted)
      return true;
  return false;
}
static void bloom(Target &out, int n, bool control, bool degraded) {
  bool half = has_extension("GL_EXT_color_buffer_half_float") ||
              has_extension("GL_EXT_color_buffer_float");
  require(half, "BLOCKED_BY_CAPABILITY: HDR scene needs half-float color "
                "attachment support");
  Target source(out.w, out.h, false, true),
      small(std::max(1, out.w / 2), std::max(1, out.h / 2), false, true),
      blur(std::max(1, out.w / 4), std::max(1, out.h / 4), false, true);
  clear(source);
  draw_instances(
      instanced,
      R"(in vec2 uv;in float phase;out vec4 color;void main(){float glow=exp(-dot(uv-.5,uv-.5)*15.);color=vec4((2.+2.*cos(vec3(0,2,4)+phase))*glow,1);})",
      n / 4 + 1, .12f);
  pass(
      small,
      R"(in vec2 uv;uniform sampler2D image;out vec4 color;void main(){color=vec4(max(texture(image,uv).rgb-1.,0.),1);})",
      source.t);
  if (!control)
    pass(
        blur,
        R"(in vec2 uv;uniform sampler2D image;out vec4 color;void main(){vec2 d=1./vec2(textureSize(image,0));vec3 s=texture(image,uv).rgb*.4;for(int i=0;i<4;i++){vec2 o=vec2((i&1)==0?-1.:1.,(i&2)==0?-1.:1.);s+=texture(image,uv+o*d*2.).rgb*.15;}color=vec4(s,1);})",
        small.t);
  clear(out);
  pass(
      out,
      std::string(
          R"(in vec2 uv;uniform sampler2D image;uniform sampler2D extra;out vec4 color;void main(){vec3 x=texture(image,uv).rgb+texture(extra,uv).rgb*.6;vec3 mapped=x/(1.+x);color=vec4()") +
          (degraded ? "mapped" : "pow(mapped,vec3(1./2.2))") + R"(,1);})",
      source.t, control ? small.t : blur.t);
}
static void msaa(Target &out, int n, bool optimized, bool degraded) {
  GLint maxSamples;
  glGetIntegerv(GL_MAX_SAMPLES, &maxSamples);
  require(maxSamples >= 4, "BLOCKED_BY_CAPABILITY: MSAA4 unavailable");
  GLuint f, rb, ds;
  glGenFramebuffers(1, &f);
  glBindFramebuffer(GL_FRAMEBUFFER, f);
  glGenRenderbuffers(1, &rb);
  glBindRenderbuffer(GL_RENDERBUFFER, rb);
  glRenderbufferStorageMultisample(GL_RENDERBUFFER, 4, GL_RGBA8, out.w, out.h);
  glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                            GL_RENDERBUFFER, rb);
  glGenRenderbuffers(1, &ds);
  glBindRenderbuffer(GL_RENDERBUFFER, ds);
  glRenderbufferStorageMultisample(GL_RENDERBUFFER, 4, GL_DEPTH24_STENCIL8,
                                   out.w, out.h);
  glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT,
                            GL_RENDERBUFFER, ds);
  require(glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE,
          "MSAA completeness");
  glViewport(0, 0, out.w, out.h);
  glClearColor(.025f, .045f, .085f, 1);
  glClearDepthf(1);
  glClearStencil(0);
  glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT);
  glEnable(GL_DEPTH_TEST);
  glEnable(GL_STENCIL_TEST);
  glStencilFunc(GL_ALWAYS, 1, 0xff);
  glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE);
  const std::string fs =
      R"(in vec2 uv;in float phase;out vec4 color;void main(){color=vec4(.4+.4*sin(phase),uv.y,.7,1);})";
  if (optimized) {
    glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE);
    draw_instances(instanced, fs, n, .17f);
    glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    glDepthFunc(GL_LEQUAL);
  }
  if (degraded) {
    glDisable(GL_DEPTH_TEST);
  }
  draw_instances(instanced, fs, n, .17f);
  glDepthFunc(GL_LESS);
  glDisable(GL_DEPTH_TEST);
  glDisable(GL_STENCIL_TEST);
  glBindFramebuffer(GL_READ_FRAMEBUFFER, f);
  glBindFramebuffer(GL_DRAW_FRAMEBUFFER, out.f);
  glBlitFramebuffer(0, 0, out.w, out.h, 0, 0, out.w, out.h, GL_COLOR_BUFFER_BIT,
                    GL_NEAREST);
  if (optimized) {
    glBindFramebuffer(GL_FRAMEBUFFER, f);
    GLenum a[] = {GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT};
    glInvalidateFramebuffer(GL_FRAMEBUFFER, 2, a);
  }
  glBindFramebuffer(GL_FRAMEBUFFER, 0);
  glDeleteRenderbuffers(1, &rb);
  glDeleteRenderbuffers(1, &ds);
  glDeleteFramebuffers(1, &f);
  check("MSAA resolve");
}
static void skinning(Target &out, int n, bool control, bool degraded) {
  clear(out);
  GLuint ubo;
  glGenBuffers(1, &ubo);
  glBindBuffer(GL_UNIFORM_BUFFER, ubo);
  std::array<float, 8> bones = {std::cos(.3f),  std::sin(.3f),  0, 0,
                                std::cos(-.6f), std::sin(-.6f), 0, 0};
  if (degraded)
    bones[5] = 1.8f;
  glBufferData(GL_UNIFORM_BUFFER, sizeof(bones),
               control ? nullptr : bones.data(), GL_DYNAMIC_DRAW);
  if (control) {
    glBufferSubData(GL_UNIFORM_BUFFER, 0, sizeof(bones), bones.data());
  }
  glBindBufferBase(GL_UNIFORM_BUFFER, 0, ubo);
  std::string vs =
      head +
      R"(layout(location=0)in vec4 data;layout(std140,binding=0)uniform Bones{vec4 bone[2];};out vec2 uv;out float phase;const vec2 q[6]=vec2[6](vec2(-1,-1),vec2(1,-1),vec2(-1,1),vec2(-1,1),vec2(1,-1),vec2(1,1));void main(){vec2 p=q[gl_VertexID]*vec2(.35,1);uv=q[gl_VertexID]*.5+.5;phase=data.w;float w=uv.y;mat2 a=mat2(bone[0].x,bone[0].y,-bone[0].y,bone[0].x),b=mat2(bone[1].x,bone[1].y,-bone[1].y,bone[1].x);p=mix(a*p,b*p,w);gl_Position=vec4(data.xy+p*data.z,0,1);})";
  draw_instances(
      vs,
      R"(in vec2 uv;in float phase;out vec4 color;void main(){color=vec4(uv.y,.5+.4*sin(phase),1.-uv.y,1);})",
      n, .17f);
  glBindBufferBase(GL_UNIFORM_BUFFER, 0, 0);
  glDeleteBuffers(1, &ubo);
}
static void compute_draw(Target &out, int n, bool optimized, bool degraded) {
  clear(out);
  GLuint data, indirect;
  glGenBuffers(1, &data);
  glBindBuffer(GL_SHADER_STORAGE_BUFFER, data);
  glBufferData(GL_SHADER_STORAGE_BUFFER, n * 4 * sizeof(float), nullptr,
               GL_DYNAMIC_DRAW);
  glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, data);
  glGenBuffers(1, &indirect);
  glBindBuffer(GL_SHADER_STORAGE_BUFFER, indirect);
  const std::array<GLuint, 4> command = {6, static_cast<GLuint>(n), 0, 0};
  glBufferData(GL_SHADER_STORAGE_BUFFER, sizeof(command), command.data(),
               GL_DYNAMIC_DRAW);
  glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, indirect);
  if (optimized) {
    std::vector<float> a;
    for (int i = 0; i < n; i++) {
      a.insert(a.end(), {float(i % 16) / 8.f - .94f, float(i / 16) / 8.f - .85f,
                         .045f, float(i) * .1f});
    }
    glBindBuffer(GL_SHADER_STORAGE_BUFFER, data);
    glBufferSubData(GL_SHADER_STORAGE_BUFFER, 0, a.size() * sizeof(float),
                    a.data());
  } else {
    std::string code =
        head +
        R"(layout(local_size_x=64)in;layout(std430,binding=0)buffer Positions{vec4 position[];};layout(std430,binding=1)buffer Indirect{uint count;uint instances;uint first;uint baseInstance;};uniform uint amount;void main(){uint i=gl_GlobalInvocationID.x;if(i<amount)position[i]=vec4(float(i%16u)/8.-.94,float(i/16u)/8.-.85,.045,float(i)*.1);if(i==0u){count=6u;instances=amount;first=0u;baseInstance=0u;}})";
    GLuint s = shader(GL_COMPUTE_SHADER, code), p = glCreateProgram();
    glAttachShader(p, s);
    glLinkProgram(p);
    GLint ok;
    glGetProgramiv(p, GL_LINK_STATUS, &ok);
    require(ok, "compute link");
    glUseProgram(p);
    glUniform1ui(glGetUniformLocation(p, "amount"), n);
    glDispatchCompute((n + 63) / 64, 1, 1);
    glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT | GL_COMMAND_BARRIER_BIT);
    glDeleteProgram(p);
    glDeleteShader(s);
  }
  if (degraded) {
    // API-side buffer updates must wait for prior shader writes, not only draws.
    glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT);
    glBindBuffer(GL_DRAW_INDIRECT_BUFFER, indirect);
    GLuint zero = 0;
    glBufferSubData(GL_DRAW_INDIRECT_BUFFER, sizeof(GLuint), sizeof(GLuint),
                    &zero);
  }
  std::string vs =
      head +
      R"(layout(std430,binding=0)readonly buffer Positions{vec4 position[];};out vec2 uv;out float phase;const vec2 q[6]=vec2[6](vec2(-1,-1),vec2(1,-1),vec2(-1,1),vec2(-1,1),vec2(1,-1),vec2(1,1));void main(){vec4 d=position[gl_InstanceID];uv=q[gl_VertexID]*.5+.5;phase=d.w;gl_Position=vec4(d.xy+q[gl_VertexID]*d.z,0,1);})";
  GLuint p = program(
      vs,
      head +
          R"(in vec2 uv;in float phase;out vec4 color;void main(){color=vec4(uv,.5+.4*sin(phase),1);})");
  glUseProgram(p);
  glBindBuffer(GL_DRAW_INDIRECT_BUFFER, indirect);
  glDrawArraysIndirect(GL_TRIANGLES, nullptr);
  glBindBuffer(GL_DRAW_INDIRECT_BUFFER, 0);
  glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, 0);
  glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, 0);
  glDeleteProgram(p);
  glDeleteBuffers(1, &data);
  glDeleteBuffers(1, &indirect);
  check("compute to draw");
}
static void gaussian(Target &out, int n, bool control, bool degraded) {
  clear(out);
  alpha();
  draw_instances(
      instanced,
      std::string(
          R"(in vec2 uv;in float phase;out vec4 color;void main(){mediump vec2 q=(uv-.5)*2.;mediump float a=exp(-dot(q,q)*5.);)") +
          (control ? "if(a<.001)discard;" : "") +
          R"(color=vec4(.5+.4*cos(vec3(0,2,4)+phase),a*)" +
          (degraded ? ".85" : ".13") + R"();})",
      n * 4, .2f);
  glDisable(GL_BLEND);
}
int main(int argc, char **argv) {
  try {
    require(argc >= 5, "usage: scene-lab S01 output.ppm size instances "
                       "[baseline|control|degraded]");
    std::string id = argv[1], path = argv[2],
                variant = argc > 5 ? argv[5] : "baseline";
    int w = std::stoi(argv[3]), n = std::stoi(argv[4]);
    require(w >= 16 && w <= 2048 && n >= 16 && n <= 4096,
            "bounded dimensions/workload");
    require(variant == "baseline" || variant == "control" ||
                variant == "degraded",
            "variant");
    Context ctx;
    GLuint vao;
    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);
    Target out(w, w);
    bool degraded = variant == "degraded", control = variant == "control";
    auto start = std::chrono::steady_clock::now();
    if (id == "S01")
      cards(out, n, control, degraded);
    else if (id == "S02")
      water(out, n, control, degraded);
    else if (id == "S03")
      particles(out, n, control, degraded);
    else if (id == "S04")
      bloom(out, n, control, degraded);
    else if (id == "S05")
      msaa(out, n, control, degraded);
    else if (id == "S06")
      skinning(out, n, control, degraded);
    else if (id == "S07")
      compute_draw(out, n, control, degraded);
    else if (id == "S08")
      gaussian(out, n, control, degraded);
    else
      throw std::runtime_error("unknown scene");
    out.bind();
    std::vector<GLubyte> rgba(w * w * 4);
    glReadPixels(0, 0, w, w, GL_RGBA, GL_UNSIGNED_BYTE, rgba.data());
    check("scene readback");
    double ms = std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - start)
                    .count();
    std::ofstream f(path, std::ios::binary);
    require(bool(f), "output open");
    f << "P6\n" << w << ' ' << w << "\n255\n";
    for (int y = w - 1; y >= 0; y--)
      for (int x = 0; x < w; x++)
        f.write(reinterpret_cast<char *>(&rgba[(y * w + x) * 4]), 3);
    require(bool(f), "output write");
    std::cout
        << "{\"scene\":" << quote(id.c_str())
        << ",\"variant\":" << quote(variant.c_str())
        << ",\"seed\":1337,\"size\":" << w << ",\"instances\":" << n
        << ",\"renderer\":"
        << quote(reinterpret_cast<const char *>(glGetString(GL_RENDERER)))
        << ",\"version\":"
        << quote(reinterpret_cast<const char *>(glGetString(GL_VERSION)))
        << ",\"cpu_wall_including_compile_readback_ms\":" << ms
        << ",\"gpu_time_ms\":null,\"hardware_performance\":\"NOT_MEASURED\"}\n";
    glDeleteVertexArrays(1, &vao);
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return std::string(e.what()).find("BLOCKED_BY_CAPABILITY:") == 0 ? 3 : 1;
  }
}
