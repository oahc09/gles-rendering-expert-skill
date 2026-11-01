// SPDX-License-Identifier: MIT
#include "common.hpp"
static void input_precision(Target &out, int id, bool bad) {
  GLuint t;
  glGenTextures(1, &t);
  glBindTexture(GL_TEXTURE_2D, t);
  float value = id == 1 ? .5002f : .503f;
  std::array<float, 4> data = {value, value, value, 1};
  if (id == 3) {
    std::array<unsigned char, 4> b = {128, 128, 128, 255};
    glTexImage2D(GL_TEXTURE_2D, 0, bad ? GL_RGBA8 : GL_SRGB8_ALPHA8, 1, 1, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, b.data());
  } else if (id == 2 && bad) {
    std::array<unsigned char, 4> b = {128, 128, 128, 255};
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, 1, 1, 0, GL_RGBA, GL_UNSIGNED_BYTE,
                 b.data());
  } else
    glTexImage2D(GL_TEXTURE_2D, 0,
                 bad ? (id == 1 ? GL_RGBA16F : GL_RGBA8) : GL_RGBA32F, 1, 1, 0,
                 GL_RGBA, GL_FLOAT, data.data());
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
  pass(out,
       "uniform highp sampler2D image;in vec2 uv;out vec4 color;void "
       "main(){vec3 "
       "x=texture(image,uv).rgb;" +
           std::string(id == 3 ? ""
                               : "x=(x-.5)*" + std::string(id == 1 ? "1000.;"
                                                                   : "100.;")) +
           "color=vec4(x,1);}",
       t);
  glDeleteTextures(1, &t);
}
static void alu_precision(Target &out, int id, bool bad) {
  std::string f =
      R"(in vec2 uv;out vec4 color;float halfValue(float x){return unpackHalf2x16(packHalf2x16(vec2(x,0))).x;}void main(){)";
  if (id == 4)
    f += std::string("float x=16.;for(int i=0;i<1024;i++)x=") +
         (bad ? "halfValue(x+.001);" : "x+.001;") +
         "color=vec4(vec3((x-16.)*.5),1);}";
  if (id == 5)
    f += std::string("float x=") +
         (bad ? "halfValue(10000.125)-halfValue(10000.);"
              : "10000.125-10000.;") +
         "color=vec4(vec3(x*4.),1);}";
  if (id == 6)
    f += std::string("vec3 n=normalize(vec3(uv-.5,1));") +
         (bad ? "n=floor(n*3.)/3.;" : "") +
         "float "
         "s=pow(max(dot(n,normalize(vec3(.1,.1,1))),0.),64.);color=vec4(vec3(s)"
         ",1);}";
  pass(out, f);
}
static void blend_precision(Target &out, int id, bool bad) {
  Target linear(out.w, out.h, false, true);
  linear.bind();
  glClearColor(0, 0, 0, 0);
  glClear(GL_COLOR_BUFFER_BIT);
  glEnable(GL_BLEND);
  glBlendFunc(id == 7   ? (bad ? GL_ONE : GL_SRC_ALPHA)
              : id == 8 ? (bad ? GL_SRC_ALPHA : GL_ONE)
                        : GL_SRC_ALPHA,
              GL_ONE_MINUS_SRC_ALPHA);
  for (int i = 0; i < 8; ++i) {
    std::string c = i % 2 ? "vec3(.8,.2,.05)" : "vec3(.05,.3,.7)";
    pass(linear,
         "in vec2 uv;out vec4 color;void main(){vec3 c=" + c + ";float a=.12;" +
             (id == 9 && bad ? std::string("c=pow(c,vec3(1./2.2));") : "") +
             (id == 8 ? std::string("c*=a;") : "") + "color=vec4(c,a);}");
  }
  glDisable(GL_BLEND);
  pass(out,
       "uniform highp sampler2D image;in vec2 uv;out vec4 color;void "
       "main(){vec3 "
       "c=texture(image,uv).rgb;" +
           std::string(id == 9 && bad ? "" : "c=pow(c,vec3(1./2.2));") +
           "color=vec4(c,1);}",
       linear.t);
}
static void attachment_precision(Target &out, int id, bool bad) {
  Target intermediate(out.w, out.h, false, !bad);
  intermediate.bind();
  glClearColor(0, 0, 0, 0);
  glClear(GL_COLOR_BUFFER_BIT);
  if (id == 10)
    pass(intermediate,
         "in vec2 uv;out vec4 color;void main(){color=vec4(vec3(uv.x*5.),1);}");
  else {
    glEnable(GL_BLEND);
    glBlendFunc(GL_ONE, GL_ONE);
    for (int i = 0; i < 64; ++i)
      pass(intermediate,
           "in vec2 uv;out vec4 color;void main(){color=vec4(" +
               std::string(id == 11 ? ".0009765625,.0009765625,.0009765625,0"
                                    : "0,0,0,.0009765625") +
               ");}");
    glDisable(GL_BLEND);
  }
  pass(out,
       "uniform highp sampler2D image;in vec2 uv;out vec4 color;void "
       "main(){vec4 "
       "c=texture(image,uv);" +
           std::string(id == 10   ? "color=vec4(c.rgb/(1.+c.rgb),1);"
                       : id == 11 ? "color=vec4(c.rgb*8.,1);"
                                  : "color=vec4(vec3(c.a*8.),1);") +
           "}",
       intermediate.t);
}
int main(int argc, char **argv) {
  try {
    require(argc == 4, "precision id[1..12] positive|negative output.ppm");
    int id = std::stoi(argv[1]);
    std::string mode = argv[2];
    require(id >= 1 && id <= 12 && (mode == "positive" || mode == "negative"),
            "arguments");
    Context ctx;
    GLuint vao;
    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);
    Target out(96, 96);
    clear(out);
    bool bad = mode == "negative";
    if (id <= 3)
      input_precision(out, id, bad);
    else if (id <= 6)
      alu_precision(out, id, bad);
    else if (id <= 9)
      blend_precision(out, id, bad);
    else
      attachment_precision(out, id, bad);
    save_ppm(out, argv[3]);
    glDeleteVertexArrays(1, &vao);
    std::cout << "{\"group\":" << id << ",\"category\":"
              << quote(id <= 3   ? "input_storage"
                       : id <= 6 ? "ALU"
                       : id <= 9 ? "blend"
                                 : "attachment")
              << ",\"mode\":" << quote(mode.c_str()) << ",\"renderer\":"
              << quote(reinterpret_cast<const char *>(glGetString(GL_RENDERER)))
              << "}\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
