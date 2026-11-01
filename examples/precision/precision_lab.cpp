// SPDX-License-Identifier: MIT
// Reuse the v1.0.4 driver, resource and shader helpers without copying them.
#include <GLES3/gl31.h>
#include <cstdlib>
static void captureShaderSource(GLuint shader, GLsizei count,
                                const GLchar *const *strings,
                                const GLint *lengths);
#define glShaderSource captureShaderSource
#define main scene_lab_existing_entry
#include "../scenes/scene_lab.cpp"
#undef main
#undef glShaderSource
#include <iomanip>

// Optional exact source capture used by the offline glslang validator.
static void captureShaderSource(GLuint shader, GLsizei count,
                                const GLchar *const *strings,
                                const GLint *lengths) {
  glShaderSource(shader, count, strings, lengths);
  const char *directory = std::getenv("GLES_PRECISION_SHADER_DUMP");
  if (!directory)
    return;
  GLint type;
  glGetShaderiv(shader, GL_SHADER_TYPE, &type);
  static unsigned serial = 0;
  std::string extension = type == GL_VERTEX_SHADER     ? ".vert"
                          : type == GL_FRAGMENT_SHADER ? ".frag"
                                                       : ".comp";
  std::ofstream file(std::string(directory) + "/" + std::to_string(serial++) +
                     extension);
  require(bool(file), "shader dump open");
  for (GLsizei i = 0; i < count; ++i)
    file << std::string(strings[i],
                        lengths && lengths[i] >= 0
                            ? size_t(lengths[i])
                            : std::char_traits<char>::length(strings[i]));
  require(bool(file), "shader dump write");
}
static std::string fragment(int scene, const std::string &mode, float time) {
  const bool bad = mode == "degraded";
  std::string prefix = "in vec2 uv;out vec4 color;\n";
  prefix += "const float clockTime=" + std::to_string(time) + ";\n";
  prefix += R"(
vec3 encode(vec3 x){return mix(12.92*x,1.055*pow(max(x,vec3(0)),vec3(1./2.4))-.055,step(vec3(.0031308),x));}
float halfValue(float x){return unpackHalf2x16(packHalf2x16(vec2(x,0))).x;}
)";
  if (scene == 1) {
    // Explicit binary16 accumulation experiment is NOT a mediump emulation.
    prefix += "void main(){";
    prefix += mode == "mediump" ? "mediump float a=16.;" : "highp float a=16.;";
    prefix += "for(int i=0;i<1024;i++){a=";
    prefix += (bad || mode == "half") ? "halfValue(a+.001);" : "a+.001;";
    prefix +=
        R"(}float phase=(a-16.)*3.+clockTime*.6;color=vec4(.15+.75*vec3(.5+.5*sin(uv.x*14.+phase),.5+.5*cos(uv.y*10.+phase),.5+.5*sin(phase)),1);})";
  } else if (scene == 2) {
    prefix += "void main(){vec2 q=uv*2.-1.;vec3 "
              "n=normalize(vec3(q,sqrt(max(.01,1.-dot(q,q)))));";
    if (bad)
      prefix += "n=floor(n*3.)/3.;";
    prefix +=
        R"(float s=pow(max(0.,dot(n,normalize(vec3(.3,.4,1.)))),80.);color=vec4(encode(vec3(.04,.12,.25)+s*vec3(1,.8,.5)),1);})";
  } else if (scene == 3) {
    prefix += "void main(){vec2 q=uv;float "
              "a=sin(q.x*30.+clockTime)*cos(q.y*24.-clockTime);";
    if (bad)
      prefix += "a=floor(a*2.)/2.;";
    prefix +=
        R"(vec3 n=normalize(vec3(a*.35,cos(q.x*20.+clockTime)*.3,1));float h=pow(max(dot(n,normalize(vec3(.2,.1,1))),0.),45.);color=vec4(encode(vec3(.015,.14,.2)+h*.65),1);})";
  } else if (scene == 4) {
    prefix += "void main(){float x=uv.x;";
    if (bad)
      prefix += "x=floor(x*8.)/8.;";
    prefix += "color=vec4(encode(vec3(.01+.4*x,.02+.2*x,.03+.1*x)),1);}";
  } else if (scene == 5 || scene == 8) {
    prefix +=
        R"(void main(){float sun=10.*exp(-dot(uv-.5,uv-.5)*25.);color=vec4(vec3(.03,.1,.3)+sun*vec3(1,.45,.12),1);})";
  } else if (scene == 7) {
    prefix += "void main(){vec3 v=vec3(uv.x,.15+.5*uv.y,.25);";
    prefix += bad ? "color=vec4(v,1);}" : "color=vec4(encode(v),1);}";
  }
  return prefix;
}
static void render_precision(Target &out, int id, const std::string &mode,
                             float time) {
  clear(out);
  if (id == 7) {
    // Upload encoded texels; SRGB8_ALPHA8 sampling performs the actual decode.
    std::vector<GLubyte> source(32 * 32 * 4);
    for (int y = 0; y < 32; ++y)
      for (int x = 0; x < 32; ++x) {
        int i = (y * 32 + x) * 4;
        source[i] = GLubyte(x * 255 / 31);
        source[i + 1] = GLubyte(40 + y * 150 / 31);
        source[i + 2] = 96;
        source[i + 3] = 255;
      }
    GLuint texture;
    glGenTextures(1, &texture);
    glBindTexture(GL_TEXTURE_2D, texture);
    glTexImage2D(GL_TEXTURE_2D, 0,
                 mode == "degraded" ? GL_RGBA8 : GL_SRGB8_ALPHA8, 32, 32, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, source.data());
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    pass(
        out,
        R"(uniform sampler2D image;in vec2 uv;out vec4 color;void main(){vec3 x=texture(image,uv).rgb;vec3 encoded=mix(12.92*x,1.055*pow(max(x,vec3(0)),vec3(1./2.4))-.055,step(vec3(.0031308),x));color=vec4(encoded,1);})",
        texture);
    glDeleteTextures(1, &texture);
  } else if (id == 6) {
    // True fixed-function straight-alpha layers, versus wrong premultiplied
    // factors.
    glEnable(GL_BLEND);
    glBlendFunc(mode == "degraded" ? GL_ONE : GL_SRC_ALPHA,
                GL_ONE_MINUS_SRC_ALPHA);
    for (int i = 0; i < 8; ++i) {
      pass(out, "in vec2 uv;out vec4 color;void main(){vec2 p=uv-vec2(" +
                    std::to_string(.25 + .065 * i) +
                    ",.5);float "
                    "a=.16*(1.-smoothstep(.1,.4,length(p)));color=vec4(.12,.55,"
                    ".8,a);}");
    }
    glDisable(GL_BLEND);
  } else if (id == 5 || id == 8) {
    bool useHalf = !(id == 8 && mode == "degraded");
    Target hdr(out.w, out.h, false, useHalf);
    pass(hdr, fragment(id, mode, time));
    pass(out,
         std::string("uniform sampler2D image;in vec2 uv;out vec4 color;void "
                     "main(){vec3 c=texture(image,uv).rgb;") +
             (mode == "degraded" && id == 5 ? "c=clamp(c,0.,1.);"
                                            : "c=c/(1.+c);") +
             "color=vec4(pow(c,vec3(1./2.2)),1);}",
         hdr.t);
  } else {
    std::string source = head + fragment(id, mode, time);
    if (mode == "mediump")
      source.replace(source.find("precision highp"), 16, "precision mediump ");
    GLuint p = program(fullscreen, source);
    out.bind();
    glUseProgram(p);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    glDeleteProgram(p);
  }
  check("precision render");
}
static std::array<float, 3> numeric_probe() {
  const std::string code = head + R"(
layout(local_size_x=1)in;
layout(std430,binding=0)buffer Results{float reference;float binary16;float medium;};
void main(){highp float a=16.;highp float b=16.;mediump float c=16.;
for(int i=0;i<1024;i++){a+=.001;b=unpackHalf2x16(packHalf2x16(vec2(b+.001,0))).x;c+=.001;}
reference=a;binary16=b;medium=c;})";
  GLuint sh = shader(GL_COMPUTE_SHADER, code), p = glCreateProgram();
  glAttachShader(p, sh);
  glLinkProgram(p);
  GLint ok;
  glGetProgramiv(p, GL_LINK_STATUS, &ok);
  require(ok, "numeric compute link");
  glDeleteShader(sh);
  GLuint buffer;
  glGenBuffers(1, &buffer);
  glBindBuffer(GL_SHADER_STORAGE_BUFFER, buffer);
  glBufferData(GL_SHADER_STORAGE_BUFFER, 3 * sizeof(float), nullptr,
               GL_DYNAMIC_READ);
  glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, buffer);
  glUseProgram(p);
  glDispatchCompute(1, 1, 1);
  glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT);
  auto *mapped = static_cast<float *>(glMapBufferRange(
      GL_SHADER_STORAGE_BUFFER, 0, 3 * sizeof(float), GL_MAP_READ_BIT));
  require(mapped != nullptr, "numeric map");
  std::array<float, 3> values = {mapped[0], mapped[1], mapped[2]};
  require(glUnmapBuffer(GL_SHADER_STORAGE_BUFFER), "numeric unmap");
  glDeleteBuffers(1, &buffer);
  glDeleteProgram(p);
  check("numeric probe");
  return values;
}
int main(int argc, char **argv) {
  try {
    require(argc == 7, "usage: precision-lab P01 output.ppm size scale time "
                       "baseline|degraded|mediump|half");
    std::string label = argv[1], mode = argv[6];
    require(label.size() == 3 && label[0] == 'P', "scene ID");
    int id = std::stoi(label.substr(1)), size = std::stoi(argv[3]);
    float scale = std::stof(argv[4]), time = std::stof(argv[5]);
    require(id >= 1 && id <= 8 && size >= 32 && size <= 1024 &&
                std::isfinite(scale) && scale >= .25 && scale <= 1 &&
                std::isfinite(time) && time >= 0 && time <= 36000,
            "bounded scene arguments");
    require(mode == "baseline" || mode == "degraded" || mode == "mediump" ||
                (mode == "half" && id == 1),
            "variant");
    Context ctx;
    GLuint vao;
    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);
    int resolution = std::max(16, int(std::lround(size * scale)));
    Target internal(resolution, resolution), output(size, size);
    render_precision(internal, id, mode, time);
    pass(output,
         "uniform sampler2D image;in vec2 uv;out vec4 color;void "
         "main(){color=texture(image,uv);}",
         internal.t);
    output.bind();
    std::vector<GLubyte> pixels(size * size * 4);
    glReadPixels(0, 0, size, size, GL_RGBA, GL_UNSIGNED_BYTE, pixels.data());
    check("precision readback");
    std::ofstream f(argv[2], std::ios::binary);
    require(bool(f), "output open");
    f << "P6\n" << size << ' ' << size << "\n255\n";
    for (int y = size - 1; y >= 0; --y)
      for (int x = 0; x < size; ++x)
        f.write(reinterpret_cast<char *>(&pixels[(y * size + x) * 4]), 3);
    require(bool(f), "output write");
    auto numeric = numeric_probe();
    GLint range[2], bits;
    glGetShaderPrecisionFormat(GL_FRAGMENT_SHADER, GL_MEDIUM_FLOAT, range,
                               &bits);
    std::cout << std::setprecision(9) << "{\"scene\":" << quote(label.c_str())
              << ",\"mode\":" << quote(mode.c_str()) << ",\"scale\":" << scale
              << ",\"time_seconds\":" << time
              << ",\"seed\":1337,\"internal_size\":" << resolution
              << ",\"output_size\":" << size << ",\"mediump_range\":["
              << range[0] << ',' << range[1]
              << "],\"mediump_precision_bits\":" << bits << ",\"renderer\":"
              << quote(reinterpret_cast<const char *>(glGetString(GL_RENDERER)))
              << ",\"version\":"
              << quote(reinterpret_cast<const char *>(glGetString(GL_VERSION)))
              << ",\"numeric_highp\":" << numeric[0]
              << ",\"numeric_binary16\":" << numeric[1]
              << ",\"numeric_mediump\":" << numeric[2]
              << ",\"device_performance\":\"NOT_MEASURED\"}\n";
    glDeleteVertexArrays(1, &vao);
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return std::string(e.what()).find("BLOCKED_BY_CAPABILITY:") == 0 ? 3 : 1;
  }
}
