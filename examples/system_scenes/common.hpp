// SPDX-License-Identifier: MIT
#pragma once
#include <GLES3/gl31.h>
#include <cstdlib>
inline void system_shader_source(GLuint, GLsizei, const GLchar *const *,
                                 const GLint *);
#define glShaderSource system_shader_source
#define main inherited_scene_entry
#include "../scenes/scene_lab.cpp"
#undef main
#undef glShaderSource
#include <iomanip>
#include <memory>
inline void system_shader_source(GLuint shaderName, GLsizei count,
                                 const GLchar *const *strings,
                                 const GLint *lengths) {
  glShaderSource(shaderName, count, strings, lengths);
  const char *dir = std::getenv("GLES_SYSTEM_SHADER_DUMP");
  if (!dir)
    return;
  GLint type;
  glGetShaderiv(shaderName, GL_SHADER_TYPE, &type);
  static unsigned serial = 0;
  std::string ext = type == GL_VERTEX_SHADER     ? ".vert"
                    : type == GL_FRAGMENT_SHADER ? ".frag"
                                                 : ".comp";
  std::ofstream f(std::string(dir) + "/" + std::to_string(serial++) + ext);
  require(bool(f), "shader dump open");
  for (GLsizei i = 0; i < count; ++i)
    f << std::string(strings[i],
                     lengths && lengths[i] >= 0
                         ? size_t(lengths[i])
                         : std::char_traits<char>::length(strings[i]));
  require(bool(f), "shader dump write");
}
inline GLuint compute_program(const std::string &source) {
  GLuint s = shader(GL_COMPUTE_SHADER, head + source), p = glCreateProgram();
  glAttachShader(p, s);
  glLinkProgram(p);
  glDeleteShader(s);
  GLint ok;
  glGetProgramiv(p, GL_LINK_STATUS, &ok);
  if (!ok) {
    char log[4096];
    glGetProgramInfoLog(p, 4096, nullptr, log);
    throw std::runtime_error(log);
  }
  return p;
}
inline void save_ppm(Target &out, const std::string &path) {
  out.bind();
  std::vector<unsigned char> data(out.w * out.h * 4);
  glReadPixels(0, 0, out.w, out.h, GL_RGBA, GL_UNSIGNED_BYTE, data.data());
  check("readback");
  std::ofstream file(path, std::ios::binary);
  require(bool(file), "capture open");
  file << "P6\n" << out.w << ' ' << out.h << "\n255\n";
  for (int y = out.h - 1; y >= 0; --y)
    for (int x = 0; x < out.w; ++x)
      file.write(reinterpret_cast<char *>(&data[(y * out.w + x) * 4]), 3);
  require(bool(file), "capture write");
}

// ES3.0-only adapter: inherited Context intentionally requires 3.1 for old
// scenes.
struct Es30Context {
  EGLDisplay d = EGL_NO_DISPLAY;
  EGLSurface s = EGL_NO_SURFACE;
  EGLContext c = EGL_NO_CONTEXT;
  Es30Context() {
    d = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    EGLint a, b, n;
    require(eglInitialize(d, &a, &b), "EGL30 initialize");
    require(eglBindAPI(EGL_OPENGL_ES_API), "EGL30 bind");
    EGLConfig config;
    const EGLint attributes[] = {EGL_SURFACE_TYPE,
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
    require(eglChooseConfig(d, attributes, &config, 1, &n) && n == 1,
            "EGL30 config");
    const EGLint size[] = {EGL_WIDTH, 1, EGL_HEIGHT, 1, EGL_NONE},
                 version[] = {EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE};
    s = eglCreatePbufferSurface(d, config, size);
    c = eglCreateContext(d, config, EGL_NO_CONTEXT, version);
    require(s != EGL_NO_SURFACE && c != EGL_NO_CONTEXT &&
                eglMakeCurrent(d, s, s, c),
            "EGL30 current");
  }
  ~Es30Context() {
    eglMakeCurrent(d, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
    eglDestroyContext(d, c);
    eglDestroySurface(d, s);
    eglTerminate(d);
  }
};
