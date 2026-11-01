// SPDX-License-Identifier: MIT
#include "common.hpp"
struct State {
  float x, y, vx, vy;
};
static std::vector<State> initial(int n, bool wave) {
  std::vector<State> a(n);
  unsigned seed = 1337;
  for (int i = 0; i < n; ++i) {
    seed = seed * 1664525u + 1013904223u;
    float x = float(seed & 65535) / 65535.f;
    seed = seed * 1664525u + 1013904223u;
    float y = float(seed & 65535) / 65535.f;
    a[i] = wave ? State{(i == 8 * 16 + 8) ? 1.f : 0.f, 0, 0, 0}
                : State{x * 1.8f - .9f, y * 1.8f - .9f, (x - .5f) * .3f,
                        (y - .5f) * .3f};
  }
  return a;
}
static std::vector<State> cpu_step(const std::vector<State> &a,
                                   const std::string &type) {
  auto b = a;
  for (size_t i = 0; i < a.size(); ++i) {
    State p = a[i];
    if (type == "wave") {
      int x = int(i) % 16, y = int(i) / 16;
      auto h = [&](int xx, int yy) {
        return a[((yy + 16) % 16) * 16 + (xx + 16) % 16].x;
      };
      float lap =
          h(x - 1, y) + h(x + 1, y) + h(x, y - 1) + h(x, y + 1) - 4 * p.x;
      b[i] = {2 * p.x - p.y + .15f * lap, p.x, 0, 0};
      continue;
    }
    if (type == "particle") {
      p.vy -= .02f;
    } else {
      float sx = 0, sy = 0, vx = 0, vy = 0, count = 0, repelX = 0, repelY = 0;
      for (size_t j = 0; j < a.size(); ++j) {
        float dx = a[j].x - p.x, dy = a[j].y - p.y;
        if (i != j && dx * dx + dy * dy < .25f) {
          sx += dx;
          sy += dy;
          vx += a[j].vx;
          vy += a[j].vy;
          count += 1;
          if (dx * dx + dy * dy < .01f) {
            repelX -= dx / (dx * dx + dy * dy + .001f);
            repelY -= dy / (dx * dx + dy * dy + .001f);
          }
        }
      }
      if (count > 0) {
        p.vx +=
            (sx / count * .03f + (vx / count - p.vx) * .02f + repelX * .001f);
        p.vy +=
            (sy / count * .03f + (vy / count - p.vy) * .02f + repelY * .001f);
      }
    }
    p.x += p.vx * .05f;
    p.y += p.vy * .05f;
    if (p.x > 1 || p.x < -1) {
      p.x = std::max(-1.f, std::min(1.f, p.x));
      p.vx *= -.8f;
    }
    if (p.y > 1 || p.y < -1) {
      p.y = std::max(-1.f, std::min(1.f, p.y));
      p.vy *= -.8f;
    }
    b[i] = p;
  }
  return b;
}
static GLuint upload(GLenum target, const std::vector<State> &data) {
  GLuint b;
  glGenBuffers(1, &b);
  glBindBuffer(target, b);
  glBufferData(target, data.size() * sizeof(State), data.data(),
               GL_DYNAMIC_COPY);
  return b;
}
static std::vector<State> gpu_ssbo(std::vector<State> a,
                                   const std::string &type, int steps,
                                   bool corrupt, const std::string &capture) {
  GLuint buffers[2] = {upload(GL_SHADER_STORAGE_BUFFER, a),
                       upload(GL_SHADER_STORAGE_BUFFER, a)};
  const std::string code =
      R"(layout(local_size_x=32)in;layout(std430,binding=0)readonly buffer Src{vec4 inputState[];};layout(std430,binding=1)writeonly buffer Dst{vec4 outputState[];};
 void main(){uint i=gl_GlobalInvocationID.x;if(i>=uint(inputState.length()))return;vec4 p=inputState[i];)" +
      (type == "particle"
           ? std::string("p.w-=.02;")
           : std::string(
                 R"(vec2 center=vec2(0),velocity=vec2(0),repel=vec2(0);float n=0.;for(uint j=0u;j<uint(inputState.length());++j){vec2 delta=inputState[j].xy-p.xy;if(i!=j&&dot(delta,delta)<.25){center+=delta;velocity+=inputState[j].zw;n+=1.;if(dot(delta,delta)<.01)repel-=delta/(dot(delta,delta)+.001);}}if(n>0.)p.zw+=center/n*.03+(velocity/n-p.zw)*.02+repel*.001;)")) +
      (corrupt ? "p.xy+=p.zw*.1;" : "p.xy+=p.zw*.05;") +
      R"(if(abs(p.x)>1.){p.x=clamp(p.x,-1.,1.);p.z*= -.8;}if(abs(p.y)>1.){p.y=clamp(p.y,-1.,1.);p.w*= -.8;}outputState[i]=p;})";
  GLuint p = compute_program(code);
  glUseProgram(p);
  for (int s = 0; s < steps; ++s) {
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, buffers[s % 2]);
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, buffers[(s + 1) % 2]);
    glDispatchCompute((GLuint(a.size()) + 31) / 32, 1, 1);
    glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT);
  }
  glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT |
                  GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT);
  {
    Target preview(96, 96);
    clear(preview);
    GLuint vao;
    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);
    GLuint draw = program(
        "#version 300 es\nprecision highp float;layout(location=0)in vec4 "
        "state;void main(){gl_Position=vec4(state.xy,0,1);gl_PointSize=4.;}",
        "#version 300 es\nprecision highp float;out vec4 color;void "
        "main(){color=vec4(.15,.7,1,1);}");
    glUseProgram(draw);
    glBindBuffer(GL_ARRAY_BUFFER, buffers[steps % 2]);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, sizeof(State), nullptr);
    glDrawArrays(GL_POINTS, 0, GLsizei(a.size()));
    save_ppm(preview, capture);
    glDeleteProgram(draw);
    glDeleteVertexArrays(1, &vao);
  }
  glBindBuffer(GL_SHADER_STORAGE_BUFFER, buffers[steps % 2]);
  auto *data = static_cast<State *>(glMapBufferRange(
      GL_SHADER_STORAGE_BUFFER, 0, a.size() * sizeof(State), GL_MAP_READ_BIT));
  require(data, "SSBO readback");
  std::copy(data, data + a.size(), a.begin());
  require(glUnmapBuffer(GL_SHADER_STORAGE_BUFFER), "unmap");
  glDeleteBuffers(2, buffers);
  glDeleteProgram(p);
  check("simulation SSBO");
  return a;
}
static std::vector<State> gpu_wave(std::vector<State> a, int steps,
                                   bool corrupt, const std::string &capture) {
  GLuint textures[2];
  glGenTextures(2, textures);
  for (GLuint t : textures) {
    glBindTexture(GL_TEXTURE_2D, t);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA32F, 16, 16);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 16, 16, GL_RGBA, GL_FLOAT,
                    a.data());
  }
  GLuint p = compute_program(
      R"(layout(local_size_x=4,local_size_y=4)in;layout(rgba32f,binding=0)readonly uniform highp image2D src;layout(rgba32f,binding=1)writeonly uniform highp image2D dst;
 float h(ivec2 q){return imageLoad(src,(q+16)%16).x;}void main(){ivec2 q=ivec2(gl_GlobalInvocationID.xy);vec4 a=imageLoad(src,q);float lap=h(q+ivec2(1,0))+h(q-ivec2(1,0))+h(q+ivec2(0,1))+h(q-ivec2(0,1))-4.*a.x;imageStore(dst,q,vec4(2.*a.x-a.y+)" +
      std::string(corrupt ? ".3" : ".15") + R"(*lap,a.x,0,0));})");
  glUseProgram(p);
  for (int s = 0; s < steps; ++s) {
    glBindImageTexture(0, textures[s % 2], 0, GL_FALSE, 0, GL_READ_ONLY,
                       GL_RGBA32F);
    glBindImageTexture(1, textures[(s + 1) % 2], 0, GL_FALSE, 0, GL_WRITE_ONLY,
                       GL_RGBA32F);
    glDispatchCompute(4, 4, 1);
    glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT);
  }
  GLuint
      result = upload(GL_SHADER_STORAGE_BUFFER, a),
      reader = compute_program(
          R"(layout(local_size_x=4,local_size_y=4)in;layout(rgba32f,binding=0)readonly uniform highp image2D src;layout(std430,binding=0)buffer Result{vec4 outputState[];};void main(){ivec2 q=ivec2(gl_GlobalInvocationID.xy);outputState[q.y*16+q.x]=imageLoad(src,q);})");
  glUseProgram(reader);
  glBindImageTexture(0, textures[steps % 2], 0, GL_FALSE, 0, GL_READ_ONLY,
                     GL_RGBA32F);
  glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, result);
  glDispatchCompute(4, 4, 1);
  glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT);
  glBindBuffer(GL_SHADER_STORAGE_BUFFER, result);
  auto *data = static_cast<State *>(glMapBufferRange(
      GL_SHADER_STORAGE_BUFFER, 0, a.size() * sizeof(State), GL_MAP_READ_BIT));
  require(data, "wave map");
  std::copy(data, data + a.size(), a.begin());
  require(glUnmapBuffer(GL_SHADER_STORAGE_BUFFER), "wave unmap");
  {
    glMemoryBarrier(GL_TEXTURE_FETCH_BARRIER_BIT);
    Target preview(96, 96);
    GLuint vao;
    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);
    pass(preview,
         "uniform sampler2D image;in vec2 uv;out vec4 color;void main(){float "
         "h=texture(image,uv).r;color=vec4(.2+h*.5,.4+h*.5,.6+h*.5,1);}",
         textures[steps % 2]);
    save_ppm(preview, capture);
    glDeleteVertexArrays(1, &vao);
  }
  glDeleteBuffers(1, &result);
  glDeleteTextures(2, textures);
  glDeleteProgram(reader);
  glDeleteProgram(p);
  check("wave compute");
  return a;
}
int main(int argc, char **argv) {
  try {
    require(
        argc == 5,
        "simulation particle|boids|wave steps gpu|cpu|degraded output.json");
    std::string type = argv[1], mode = argv[3];
    int steps = std::stoi(argv[2]);
    require((type == "particle" || type == "boids" || type == "wave") &&
                steps >= 1 && steps <= 1000,
            "simulation arguments");
    require(mode == "gpu" || mode == "cpu" || mode == "degraded", "mode");
    auto seed = initial(type == "wave" ? 256 : 64, type == "wave"),
         reference = seed;
    for (int i = 0; i < steps; ++i)
      reference = cpu_step(reference, type);
    std::unique_ptr<Context> context;
    if (mode != "cpu")
      context = std::make_unique<Context>();
    auto actual = mode == "cpu" ? reference
                  : type == "wave"
                      ? gpu_wave(seed, steps, mode == "degraded",
                                 std::string(argv[4]) + ".ppm")
                      : gpu_ssbo(seed, type, steps, mode == "degraded",
                                 std::string(argv[4]) + ".ppm");
    double maxError = 0;
    for (size_t i = 0; i < actual.size(); ++i) {
      std::array<float, 4> a = {actual[i].x, actual[i].y, actual[i].vx,
                                actual[i].vy},
                           b = {reference[i].x, reference[i].y, reference[i].vx,
                                reference[i].vy};
      for (int j = 0; j < 4; ++j) {
        require(std::isfinite(a[j]), "nonfinite simulation");
        maxError = std::max(maxError, double(std::abs(a[j] - b[j])));
      }
    }
    std::ofstream f(argv[4]);
    require(bool(f), "output");
    f << std::setprecision(9) << "{\"type\":" << quote(type.c_str())
      << ",\"mode\":" << quote(mode.c_str())
      << ",\"seed\":1337,\"steps\":" << steps << ",\"count\":" << actual.size()
      << ",\"max_absolute_error\":" << maxError
      << ",\"tolerance\":0.0001,\"within_tolerance\":"
      << (maxError <= .0001 ? "true" : "false") << ",\"renderer\":"
      << quote(context
                   ? reinterpret_cast<const char *>(glGetString(GL_RENDERER))
                   : "CPU fallback; no GL context required")
      << ",\"values\":[";
    for (size_t i = 0; i < actual.size(); ++i) {
      if (i)
        f << ',';
      f << '[' << actual[i].x << ',' << actual[i].y << ',' << actual[i].vx
        << ',' << actual[i].vy << ']';
    }
    f << "]}\n";
    require(bool(f), "output write");
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
