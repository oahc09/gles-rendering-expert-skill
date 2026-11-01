// SPDX-License-Identifier: MIT
#include "common.hpp"
static bool rgba16f_renderable() {
  // Test hook exercises safe failure, never masquerades as real device
  // evidence.
  if (std::getenv("GLES_TEST_FORCE_NO_RGBA16F"))
    return false;
  check("before renderability probe");
  GLint oldFramebuffer, oldTexture;
  glGetIntegerv(GL_FRAMEBUFFER_BINDING, &oldFramebuffer);
  glGetIntegerv(GL_TEXTURE_BINDING_2D, &oldTexture);
  GLuint framebuffer, texture;
  glGenFramebuffers(1, &framebuffer);
  glGenTextures(1, &texture);
  glBindTexture(GL_TEXTURE_2D, texture);
  glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA16F, 4, 4);
  glBindFramebuffer(GL_FRAMEBUFFER, framebuffer);
  glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D,
                         texture, 0);
  GLenum status = glCheckFramebufferStatus(GL_FRAMEBUFFER),
         error = glGetError();
  glBindFramebuffer(GL_FRAMEBUFFER, GLuint(oldFramebuffer));
  glBindTexture(GL_TEXTURE_2D, GLuint(oldTexture));
  glDeleteFramebuffers(1, &framebuffer);
  glDeleteTextures(1, &texture);
  return status == GL_FRAMEBUFFER_COMPLETE && error == GL_NO_ERROR;
}
static void backdrop30(Target &out) {
  clear(out);
  std::string vertex = fullscreen;
  vertex.replace(vertex.find("310"), 3, "300");
  GLuint p =
      program(vertex, "#version 300 es\nprecision highp float;in vec2 uv;out "
                      "vec4 color;void main(){float "
                      "grid=mod(floor(uv.x*16.)+floor(uv.y*16.),2.);color=vec4("
                      "mix(vec3(.05,.12,.18),vec3(.24,.4,.45),grid),1);}");
  glUseProgram(p);
  glDrawArrays(GL_TRIANGLES, 0, 3);
  glDeleteProgram(p);
}
static void backdrop(Target &out) {
  clear(out);
  glEnable(GL_DEPTH_TEST);
  pass(
      out,
      R"(in vec2 uv;out vec4 color;void main(){float grid=mod(floor(uv.x*16.)+floor(uv.y*16.),2.);color=vec4(mix(vec3(.05,.12,.18),vec3(.24,.4,.45),grid),1);gl_FragDepth=.8;})");
  glDisable(GL_DEPTH_TEST);
}
static void glass(Target &out, bool bad, float touch) {
  Target scene(out.w, out.h, true), front(out.w, out.h), back(out.w, out.h);
  backdrop(scene);
  for (int side = 0; side < 2; ++side) {
    Target &t = side ? back : front;
    pass(t, "in vec2 uv;out vec4 color;void main(){vec2 q=(uv-vec2(" +
                std::to_string(.5f + touch * .15f) +
                ",.5))*2.;float r=dot(q,q);float z=" +
                std::string(side ? ".55+.15*sqrt(max(0.,1.-r*2.))"
                                 : ".55-.15*sqrt(max(0.,1.-r*2.))") +
                ";color=vec4(z,step(r,.5),0,1);}");
  }
  out.bind();
  GLuint p = program(
      fullscreen,
      head +
          R"(uniform sampler2D image,extra,backside;in vec2 uv;out vec4 color;void main(){vec4 a=texture(extra,uv),b=texture(backside,uv);float thickness=max(0.,b.r-a.r);vec2 n=(uv-.5)*2.;vec2 offset=n*thickness*)" +
          std::string(bad ? "0." : ".22") +
          R"(;vec3 c=texture(image,clamp(uv+offset,vec2(0),vec2(1))).rgb;c*=exp(-vec3(.6,.18,.08)*thickness);color=vec4(mix(texture(image,uv).rgb,c,a.g),1);})");
  glUseProgram(p);
  tex(p, "image", scene.t, 0);
  tex(p, "extra", front.t, 1);
  tex(p, "backside", back.t, 2);
  glDrawArrays(GL_TRIANGLES, 0, 3);
  glDeleteProgram(p);
}
static std::vector<float> layer_data(int n, float touch) {
  auto a = instances(n, 1337, .24f);
  for (int i = 0; i < n; ++i) {
    a[i * 4] += .2f * touch;
    a[i * 4 + 3] = float(i) / float(n);
  }
  return a;
}
static void layers(Target &target, const std::vector<float> &data, int mode,
                   bool sand) {
  target.bind();
  GLuint b;
  glGenBuffers(1, &b);
  glBindBuffer(GL_ARRAY_BUFFER, b);
  glBufferData(GL_ARRAY_BUFFER, data.size() * sizeof(float), data.data(),
               GL_STATIC_DRAW);
  glEnableVertexAttribArray(0);
  glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 16, nullptr);
  glVertexAttribDivisor(0, 1);
  std::string fs =
      R"(in vec2 uv;in float phase;out vec4 color;void main(){vec2 q=(uv-.5)*2.;float a=)" +
      std::string(sand ? ".5*(1.-smoothstep(.1,1.,length(q*vec2(1,2))))"
                       : ".3*exp(-dot(q,q)*3.)") +
      R"(;vec3 c=)" +
      std::string(sand ? "vec3(.65+.2*phase,.32+.3*phase,.08)"
                       : ".5+.45*cos(vec3(0,2,4)+phase*6.)") +
      ";";
  if (mode == 0)
    fs += "float "
          "w=clamp(.03/"
          "(.00001+pow(phase*.8+.2,4.)),.01,30.);color=vec4(c*a*w,a*w);}";
  else if (mode == 1)
    fs += "color=vec4(a);}";
  else
    fs += "color=vec4(c,a);}";
  std::string vertex = instanced, fragmentHead = head;
  if (mode == 2) {
    vertex.replace(vertex.find("310"), 3, "300");
    fragmentHead.replace(fragmentHead.find("310"), 3, "300");
  }
  GLuint p = program(vertex, fragmentHead + fs);
  glUseProgram(p);
  glUniform1f(glGetUniformLocation(p, "zvalue"), 0);
  glDrawArraysInstanced(GL_TRIANGLES, 0, 6, GLsizei(data.size() / 4));
  glDeleteProgram(p);
  glDisableVertexAttribArray(0);
  glVertexAttribDivisor(0, 0);
  glDeleteBuffers(1, &b);
}
static void transparency(Target &out, bool sand, const std::string &mode,
                         float touch) {
  auto data = layer_data(sand ? 48 : 24, touch);
  clear(out);
  if (mode == "sorted")
    backdrop30(out);
  else
    backdrop(out);
  if (mode == "sorted") {
    std::vector<std::array<float, 4>> sorted;
    for (size_t i = 0; i < data.size(); i += 4)
      sorted.push_back({data[i], data[i + 1], data[i + 2], data[i + 3]});
    std::sort(sorted.begin(), sorted.end(),
              [](auto a, auto b) { return a[3] > b[3]; });
    for (size_t i = 0; i < sorted.size(); ++i)
      for (int c = 0; c < 4; ++c)
        data[i * 4 + c] = sorted[i][c];
    alpha();
    layers(out, data, 2, sand);
    glDisable(GL_BLEND);
    return;
  }
  require(rgba16f_renderable(),
          "BLOCKED_BY_CAPABILITY: RGBA16F color attachment unsupported; use "
          "sorted or fallback mode (ES3.0 RGBA8 path)");
  Target accumulation(out.w, out.h, false, true), reveal(out.w, out.h);
  accumulation.bind();
  glClearColor(0, 0, 0, 0);
  glClear(GL_COLOR_BUFFER_BIT);
  glEnable(GL_BLEND);
  glBlendFunc(GL_ONE, GL_ONE);
  layers(accumulation, data, 0, sand);
  reveal.bind();
  glClearColor(1, 1, 1, 1);
  glClear(GL_COLOR_BUFFER_BIT);
  glBlendFunc(GL_ZERO, GL_ONE_MINUS_SRC_ALPHA);
  layers(reveal, data, 1, sand);
  glDisable(GL_BLEND);
  // Two geometry passes avoid requiring indexed blend equations/extensions.
  GLuint p = program(
      fullscreen,
      head +
          R"(uniform sampler2D image,extra;in vec2 uv;out vec4 color;void main(){vec4 a=texture(image,uv);float r=texture(extra,uv).r;vec3 c=a.rgb/max(a.a,.0001);color=vec4(c,)" +
          std::string(mode == "degraded" ? "1." : "1.-r") + ");}");
  out.bind();
  alpha();
  glUseProgram(p);
  tex(p, "image", accumulation.t, 0);
  tex(p, "extra", reveal.t, 1);
  glDrawArrays(GL_TRIANGLES, 0, 3);
  glDeleteProgram(p);
  glDisable(GL_BLEND);
}
static void shadow_depth(Target &target, float scale, float touch) {
  clear(target);
  target.bind();
  glEnable(GL_DEPTH_TEST);
  glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE);
  pass(target,
       "in vec2 uv;out vec4 color;void main(){vec2 p=(uv-.5)*" +
           std::to_string(scale) + ";if(abs(p.x-" +
           std::to_string(touch * .15f) +
           ")>.13||abs(p.y)>.22)discard;gl_FragDepth=.3;color=vec4(0);}");
  glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
  glDisable(GL_DEPTH_TEST);
}
static void shadow_water(Target &out, bool bad, float touch) {
  Target nearMap(64, 64, true), farMap(64, 64, true), scene(out.w, out.h, true);
  shadow_depth(nearMap, 1, touch);
  shadow_depth(farMap, 2, touch);
  backdrop(scene);
  GLuint p = program(
      fullscreen,
      head +
          R"(uniform sampler2D nearDepth,farDepth,image,extra;in vec2 uv;out vec4 color;
 float pcf(sampler2D map,vec2 p){float s=0.;for(int y=-1;y<=1;++y)for(int x=-1;x<=1;++x)s+=step(.55-.01,texture(map,p+vec2(x,y)/64.).r);return s/9.;}
 void main(){bool farZone=uv.y>.6;vec2 p=farZone?(uv-.5)/2.+.5:uv;float shadow=farZone?pcf(farDepth,p):pcf(nearDepth,p);)" +
          std::string(bad ? "shadow=1.;" : "") +
          R"(vec2 wave=vec2(sin(uv.x*35.),cos(uv.y*27.))*.006;float sceneDepth=texture(extra,uv).r;float depth=max(0.,sceneDepth-.45);float caustic=pow(max(0.,sin(uv.x*45.)*cos(uv.y*37.)),6.)*.15*exp(-depth*3.);vec3 c=texture(image,uv+wave).rgb*mix(.3,1.,shadow)+vec3(caustic);c=mix(c,vec3(.03,.28,.38),depth*.6);color=vec4(c,1);})");
  out.bind();
  glUseProgram(p);
  tex(p, "nearDepth", nearMap.z, 0);
  tex(p, "farDepth", farMap.z, 1);
  tex(p, "image", scene.t, 2);
  tex(p, "extra", scene.z, 3);
  glDrawArrays(GL_TRIANGLES, 0, 3);
  glDeleteProgram(p);
}
static void forward_plus(Target &out, const std::string &mode, float touch) {
  std::vector<float> lights;
  for (int i = 0; i < 16; ++i) {
    lights.push_back(float(i % 4) / 4 + .125f + touch * .08f);
    lights.push_back(float(i / 4) / 4 + .125f);
    lights.push_back(.25f);
    lights.push_back(float(i) / 16);
  }
  if (mode == "fallback") {
    std::string vertex = fullscreen;
    vertex.replace(vertex.find("310"), 3, "300");
    const std::string fragment =
        "#version 300 es\nprecision highp float;uniform vec4 lights[16];in "
        "vec2 uv;out vec4 color;void main(){vec3 sum=vec3(.02);for(int "
        "i=0;i<16;++i){float d=length(uv-lights[i].xy);float "
        "a=max(0.,1.-d/lights[i].z);vec3 "
        "hue=.5+.45*cos(vec3(0,2,4)+lights[i].w*6.);sum+=hue*a*a;}color=vec4("
        "pow(sum/(1.+sum),vec3(1./2.2)),1);}";
    GLuint p = program(vertex, fragment);
    out.bind();
    glUseProgram(p);
    glUniform4fv(glGetUniformLocation(p, "lights[0]"), 16, lights.data());
    glDrawArrays(GL_TRIANGLES, 0, 3);
    glDeleteProgram(p);
    return;
  }
  GLuint l, b;
  glGenBuffers(1, &l);
  glBindBuffer(GL_SHADER_STORAGE_BUFFER, l);
  glBufferData(GL_SHADER_STORAGE_BUFFER, lights.size() * sizeof(float),
               lights.data(), GL_STATIC_DRAW);
  glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, l);
  glGenBuffers(1, &b);
  glBindBuffer(GL_SHADER_STORAGE_BUFFER, b);
  glBufferData(GL_SHADER_STORAGE_BUFFER, 64 * 17 * sizeof(int), nullptr,
               GL_DYNAMIC_COPY);
  glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, b);
  GLuint c = compute_program(
      R"(layout(local_size_x=8,local_size_y=8)in;layout(std430,binding=0)readonly buffer L{vec4 lights[];};layout(std430,binding=1)writeonly buffer Tiles{int ids[];};void main(){ivec2 tile=ivec2(gl_GlobalInvocationID.xy);int offset=(tile.y*8+tile.x)*17,count=0;vec2 lo=vec2(tile)/8.,hi=lo+1./8.;for(int i=0;i<16;++i){vec2 delta=lights[i].xy-clamp(lights[i].xy,lo,hi);if(dot(delta,delta)<lights[i].z*lights[i].z){ids[offset+1+count]=i;count++;}}ids[offset]=count;})");
  glUseProgram(c);
  glDispatchCompute(1, 1, 1);
  glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT);
  std::string fs =
      R"(layout(std430,binding=0)readonly buffer L{vec4 lights[];};layout(std430,binding=1)readonly buffer Tiles{int ids[];};in vec2 uv;out vec4 color;void main(){ivec2 tile=min(ivec2(uv*8.),ivec2(7));int o=(tile.y*8+tile.x)*17;vec3 sum=vec3(.02);)";
  if (mode == "fallback")
    fs += "for(int j=0;j<16;++j){int i=j;";
  else
    fs += "for(int j=0;j<ids[o];++j){int i=ids[o+1+j];";
  fs +=
      R"(float d=length(uv-lights[i].xy);float attenuation=max(0.,1.-d/lights[i].z);vec3 hue=.5+.45*cos(vec3(0,2,4)+lights[i].w*6.);sum+=hue*attenuation*attenuation;})";
  if (mode == "degraded") {
    fs += "sum*=.3;";
  }
  fs += "color=vec4(pow(sum/(1.+sum),vec3(1./2.2)),1);}";
  pass(out, fs);
  glDeleteProgram(c);
  glDeleteBuffers(1, &b);
  glDeleteBuffers(1, &l);
}
int main(int argc, char **argv) {
  try {
    require(argc == 5,
            "effects glass|sand|particle|shadowwater|forwardplus output.ppm "
            "baseline|degraded|sorted|fallback touch[-1,1]");
    std::string id = argv[1], mode = argv[3];
    float touch = std::stof(argv[4]);
    require(std::isfinite(touch) && std::abs(touch) <= 1, "touch range");
    require(mode == "baseline" || mode == "degraded" || mode == "sorted" ||
                mode == "fallback",
            "mode");
    std::unique_ptr<Context> context;
    std::unique_ptr<Es30Context> context30;
    require(mode != "sorted" || id == "sand" || id == "particle",
            "sorted only applies to transparent scenes");
    require(mode != "fallback" || id == "sand" || id == "particle" ||
                id == "forwardplus",
            "fallback scene");
    if ((id == "forwardplus" && mode == "fallback") ||
        ((id == "sand" || id == "particle") &&
         (mode == "sorted" || mode == "fallback")))
      context30 = std::make_unique<Es30Context>();
    else
      context = std::make_unique<Context>();
    GLuint vao;
    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);
    Target out(96, 96);
    clear(out);
    if (id == "glass")
      glass(out, mode == "degraded", touch);
    else if (id == "sand" || id == "particle")
      transparency(out, id == "sand", mode == "fallback" ? "sorted" : mode,
                   touch);
    else if (id == "shadowwater")
      shadow_water(out, mode == "degraded", touch);
    else if (id == "forwardplus")
      forward_plus(out, mode, touch);
    else
      throw std::runtime_error("scene ID");
    check("effects render");
    save_ppm(out, argv[2]);
    std::cout << "{\"scene\":" << quote(id.c_str())
              << ",\"mode\":" << quote(mode.c_str()) << ",\"touch\":" << touch
              << ",\"seed\":1337,\"renderer\":"
              << quote(reinterpret_cast<const char *>(glGetString(GL_RENDERER)))
              << ",\"version\":"
              << quote(reinterpret_cast<const char *>(glGetString(GL_VERSION)))
              << ",\"hardware_performance\":\"NOT_MEASURED\"}\n";
    glDeleteVertexArrays(1, &vao);
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return std::string(e.what()).find("BLOCKED_BY_CAPABILITY:") == 0 ? 3 : 1;
  }
}
