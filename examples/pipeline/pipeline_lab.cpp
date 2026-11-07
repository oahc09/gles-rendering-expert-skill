// SPDX-License-Identifier: MIT
// Reuse EGL, Target, shader compiler, strict error handling and PPM writer.
#include "../system_scenes/common.hpp"
#include <cstddef>
#include <sstream>
#include <set>

namespace pipeline {
const std::string h = "#version 300 es\nprecision highp float;\n";
const std::string vs = h + R"(out vec2 uv;
void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=p;gl_Position=vec4(p*2.-1.,0.,1.);})";
const std::string flat = "out vec4 color;void main(){color=vec4(.25,.5,.75,1);}";
std::string detail;
bool extension(const std::string& name) {
  GLint n=0;glGetIntegerv(GL_NUM_EXTENSIONS,&n);
  for(GLint i=0;i<n;++i) if(name==reinterpret_cast<const char*>(glGetStringi(GL_EXTENSIONS,GLuint(i)))) return true;
  return false;
}
void draw(Target& target,const std::string& fragment,GLuint image=0,GLuint extra=0) {
  target.bind();GLuint p=program(vs,h+fragment);glUseProgram(p);
  tex(p,"image",image,0);tex(p,"extra",extra,1);glDrawArrays(GL_TRIANGLES,0,3);
  glDeleteProgram(p);check("pipeline draw");
}
std::string cache_key(const std::string& source,const std::string& macros,const std::string& driver_override="") {
  // Length-prefixed canonical identity, not a portable binary fingerprint.
  std::ostringstream s;
  auto field=[&s](const std::string& v){s<<v.size()<<':'<<v;};
  field("backend=native-EGL-GLES");field("MaterialABI-v1:std140:baseColor@0:roughness@16:metallic@20:size32:sampler0");
  field(source);field(macros);field("GL_PROGRAM_BINARY_RETRIEVABLE_HINT=1;highp;optimization=driver-default");
  for(GLenum v:{GL_VENDOR,GL_RENDERER,GL_VERSION,GL_SHADING_LANGUAGE_VERSION}) field(reinterpret_cast<const char*>(glGetString(v)));
  field(driver_override.empty()?reinterpret_cast<const char*>(glGetString(GL_VERSION)):driver_override);
  GLint n=0;glGetIntegerv(GL_NUM_EXTENSIONS,&n);std::set<std::string> extensions;
  for(GLint i=0;i<n;++i) extensions.insert(reinterpret_cast<const char*>(glGetStringi(GL_EXTENSIONS,GLuint(i))));
  for(const auto& e:extensions) field(e);
  return s.str();
}
GLuint binary_roundtrip(bool corrupt,bool& supported,bool& fallback) {
  auto start=std::chrono::steady_clock::now();
  GLuint p=program(vs,h+flat);
  // Relink after setting retrievable hint. Hint must precede the link being cached.
  glProgramParameteri(p,GL_PROGRAM_BINARY_RETRIEVABLE_HINT,GL_TRUE);glLinkProgram(p);
  GLint linked=0;glGetProgramiv(p,GL_LINK_STATUS,&linked);require(linked==GL_TRUE,"cache source relink");
  auto compiled=std::chrono::steady_clock::now();
  GLint n=0,length=0;glGetIntegerv(GL_NUM_PROGRAM_BINARY_FORMATS,&n);glGetProgramiv(p,GL_PROGRAM_BINARY_LENGTH,&length);
  supported=n>0&&length>0&&length<=16*1024*1024;fallback=!supported;
  GLuint q=0;
  if(supported) {
    std::vector<unsigned char> bytes(static_cast<size_t>(length));GLenum format=0;GLsizei written=0;
    glGetProgramBinary(p,length,&written,&format,bytes.data());check("get binary");
    require(written>0,"empty binary");q=glCreateProgram();
    if(corrupt) { bytes.assign(16,0);written=16; }
    glProgramBinary(q,format,bytes.data(),written);
    GLint ok=0;glGetProgramiv(q,GL_LINK_STATUS,&ok);
    // Invalid blobs may generate an error OR link failure. Never draw an invalid program.
    GLenum error=glGetError();fallback=ok!=GL_TRUE||error!=GL_NO_ERROR;
    if(fallback) {glDeleteProgram(q);q=0;}
  }
  if(!q) q=program(vs,h+flat);
  auto loaded=std::chrono::steady_clock::now();glDeleteProgram(p);
  std::ostringstream s;s<<"\"binary_supported\":"<<(supported?"true":"false")<<",\"fallback\":"<<(fallback?"true":"false")
    <<",\"source_compile_link_wall_ms\":"<<std::chrono::duration<double,std::milli>(compiled-start).count()
    <<",\"binary_load_or_fallback_wall_ms\":"<<std::chrono::duration<double,std::milli>(loaded-compiled).count();detail=s.str();
  return q;
}
struct alignas(16) Material { float baseColor[4]; float roughness; float metallic; float padding[2]; };
static_assert(offsetof(Material,baseColor)==0&&offsetof(Material,roughness)==16&&offsetof(Material,metallic)==20&&sizeof(Material)==32,"std140 Material ABI");
void material(Target& out,bool inject,bool visualFault=false,bool multiple=false) {
  GLuint p=program(vs,h+R"(in vec2 uv;out vec4 color;
layout(std140) uniform Material{vec4 baseColor;float roughness;float metallic;};
uniform sampler2D baseColorTex;
void main(){color=vec4(baseColor.rgb*texture(baseColorTex,uv).rgb*(1.-.5*roughness)+vec3(.1*metallic),baseColor.a);})");
  GLuint block=glGetUniformBlockIndex(p,"Material");require(block!=GL_INVALID_INDEX,"Material missing block");
  GLint size=0;glGetActiveUniformBlockiv(p,block,GL_UNIFORM_BLOCK_DATA_SIZE,&size);require(size==32,"Material size !=32");
  const char* names[]={"baseColor","roughness","metallic"};GLuint indices[3];GLint offsets[3],types[3],sizes[3],rowMajor[3];
  glGetUniformIndices(p,3,names,indices);for(GLuint index:indices) require(index!=GL_INVALID_INDEX,"Material missing member");
  glGetActiveUniformsiv(p,3,indices,GL_UNIFORM_OFFSET,offsets);
  glGetActiveUniformsiv(p,3,indices,GL_UNIFORM_TYPE,types);
  glGetActiveUniformsiv(p,3,indices,GL_UNIFORM_SIZE,sizes);
  glGetActiveUniformsiv(p,3,indices,GL_UNIFORM_IS_ROW_MAJOR,rowMajor);
  require(offsets[0]==0&&offsets[1]==16&&offsets[2]==20,"Material reflected offsets");
  bool rejected=offsets[1]!=(inject?12:16);require(rejected==inject,"roughness injection detection");
  glUniformBlockBinding(p,block,0);GLint observedBinding=-1;glGetActiveUniformBlockiv(p,block,GL_UNIFORM_BLOCK_BINDING,&observedBinding);require(observedBinding==0,"Material binding point");glUseProgram(p);
  GLuint b,t;glGenBuffers(1,&b);glBindBuffer(GL_UNIFORM_BUFFER,b);
  Material data={{.8f,.4f,.2f,1},.4f,.5f,{0,0}};
  if(visualFault) data.baseColor[0]=.2f;
  glBufferData(GL_UNIFORM_BUFFER,sizeof(data),&data,GL_STATIC_DRAW);glBindBufferBase(GL_UNIFORM_BUFFER,0,b);
  glGenTextures(1,&t);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,t);
  const unsigned char pixel[]={128,192,255,255};glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,1,1);
  glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE,pixel);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
  GLint loc=glGetUniformLocation(p,"baseColorTex");require(loc>=0,"baseColorTex inactive");
  const char* samplerName="baseColorTex";GLuint samplerIndex;GLint samplerType=0;
  glGetUniformIndices(p,1,&samplerName,&samplerIndex);glGetActiveUniformsiv(p,1,&samplerIndex,GL_UNIFORM_TYPE,&samplerType);require(samplerType==GL_SAMPLER_2D,"baseColorTex sampler type");
  glUniform1i(loc,inject?1:0);GLint unit=-1;glGetUniformiv(p,loc,&unit);require((unit!=0)==inject,"sampler mismatch detection");
  glUniform1i(loc,0);out.bind();glDrawArrays(GL_TRIANGLES,0,3);
  if(multiple) {
    data.baseColor[0]=.2f;data.baseColor[1]=.8f;data.baseColor[2]=.6f;
    glBindBuffer(GL_UNIFORM_BUFFER,b);glBufferSubData(GL_UNIFORM_BUFFER,0,sizeof(data),&data);
    glEnable(GL_SCISSOR_TEST);glScissor(out.w/2,0,out.w/2,out.h);glDrawArrays(GL_TRIANGLES,0,3);glDisable(GL_SCISSOR_TEST);
  }
  check("material binding draw");
  detail="\"block_size\":32,\"offsets\":[0,16,20],\"block_binding\":0,\"sampler_type\":\"sampler2D\",\"sampler_unit\":0,\"checked_faults\":[\"Material.roughness expected offset16 vs12\",\"baseColorTex expected unit0 vs1\"]";
  auto triple=[](const GLint* values){return "["+std::to_string(values[0])+","+std::to_string(values[1])+","+std::to_string(values[2])+"]";};
  detail+=",\"member_types\":"+triple(types)+",\"member_sizes\":"+triple(sizes)+",\"member_row_major\":"+triple(rowMajor);
  glDeleteTextures(1,&t);glDeleteBuffers(1,&b);glDeleteProgram(p);
}
void bloom(Target& out,bool inject) {
  Target scene(out.w,out.h),bright(out.w,out.h),blur(out.w,out.h);
  draw(scene,"in vec2 uv;out vec4 color;void main(){color=vec4(uv.x,uv.x*.5,uv.x*.25,1);}");
  draw(bright,"in vec2 uv;uniform sampler2D image;out vec4 color;void main(){color=vec4(max(texture(image,uv).rgb-.4,0.),1);}",scene.t);
  draw(blur,"in vec2 uv;uniform sampler2D image;out vec4 color;void main(){vec2 d=vec2(1./32.,0);color=(texture(image,uv-d)+2.*texture(image,uv)+texture(image,uv+d))*.25;}",bright.t);
  draw(out, "in vec2 uv;uniform sampler2D image;uniform sampler2D extra;out vec4 color;void main(){color=vec4(min(texture(image,uv).rgb+"+std::string(inject?"0.":".5")+"*texture(extra,uv).rgb,1.),1);}",scene.t,blur.t);
  // No undefined read/feedback is submitted. Graph negative cases live in checker tests.
  detail="\"passes\":[\"scene\",\"bright\",\"horizontal_blur\",\"composite\"],\"injection\":\"omit_bloom_contribution\"";
}
void compute_draw(Target& out,bool inject) {
  GLint minor=0;glGetIntegerv(GL_MINOR_VERSION,&minor);require(minor>=1,"BLOCKED_BY_CAPABILITY: compute requires GLES3.1");
  GLuint b;glGenBuffers(1,&b);glBindBuffer(GL_SHADER_STORAGE_BUFFER,b);glBufferData(GL_SHADER_STORAGE_BUFFER,12*sizeof(float),nullptr,GL_DYNAMIC_DRAW);glBindBufferBase(GL_SHADER_STORAGE_BUFFER,0,b);
  GLuint cp=compute_program(R"(layout(local_size_x=1) in;layout(std430,binding=0) buffer Positions{vec4 positions[];};
void main(){positions[0]=vec4(-1,-1,0,1);positions[1]=vec4(3,-1,0,1);positions[2]=vec4(-1,3,0,1);})");
  glUseProgram(cp);glDispatchCompute(1,1,1);
  GLbitfield requested=inject?0:GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT;
  require(((requested&GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT)==0)==inject,"barrier preflight");
  // Reject missing barrier before consumption, repair, then run. Missing barriers are
  // undefined and an apparently-correct readback would NOT prove synchronization.
  glMemoryBarrier(GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT);
  GLuint p=program(h+"layout(location=0)in vec4 position;void main(){gl_Position=position;}",h+flat),vao;
  glGenVertexArrays(1,&vao);glBindVertexArray(vao);glBindBuffer(GL_ARRAY_BUFFER,b);
  glVertexAttribPointer(0,4,GL_FLOAT,GL_FALSE,16,nullptr);glEnableVertexAttribArray(0);
  out.bind();glUseProgram(p);glDrawArrays(GL_TRIANGLES,0,3);check("compute draw");
  detail="\"producer\":\"compute SSBO write\",\"consumer\":\"vertex attribute fetch\",\"required_barrier\":\"GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT\",\"negative_preflight_rejected\":"+std::string(inject?"true":"false");
  glBindVertexArray(0);glDeleteVertexArrays(1,&vao);glDeleteProgram(p);glDeleteProgram(cp);glDeleteBuffers(1,&b);
}
void msaa(Target& out,bool inject,bool visualFault=false) {
  GLint count=0;glGetInternalformativ(GL_RENDERBUFFER,GL_RGBA8,GL_NUM_SAMPLE_COUNTS,1,&count);
  require(count>0,"BLOCKED_BY_CAPABILITY: no RGBA8 MSAA samples");std::vector<GLint> samples(static_cast<size_t>(count));
  glGetInternalformativ(GL_RENDERBUFFER,GL_RGBA8,GL_SAMPLES,count,samples.data());int n=samples.back();require(n>1,"BLOCKED_BY_CAPABILITY: MSAA unavailable");
  GLuint f,r;glGenFramebuffers(1,&f);glBindFramebuffer(GL_FRAMEBUFFER,f);glGenRenderbuffers(1,&r);glBindRenderbuffer(GL_RENDERBUFFER,r);
  glRenderbufferStorageMultisample(GL_RENDERBUFFER,n,GL_RGBA8,out.w,out.h);glFramebufferRenderbuffer(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_RENDERBUFFER,r);
  require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"MSAA FBO");
  glViewport(0,0,out.w,out.h);GLuint p=program(vs,h+flat);glUseProgram(p);glDrawArrays(GL_TRIANGLES,0,3);
  GLuint blend=program(vs,h+"out vec4 color;void main(){color=vec4(.4,.1,.2,.5);}");
  glEnable(GL_BLEND);glBlendFunc(GL_ONE,GL_ONE_MINUS_SRC_ALPHA);glUseProgram(blend);glDrawArrays(GL_TRIANGLES,0,3);glDisable(GL_BLEND);glDeleteProgram(blend);
  Target resolved(out.w,out.h);glBindFramebuffer(GL_READ_FRAMEBUFFER,f);glBindFramebuffer(GL_DRAW_FRAMEBUFFER,resolved.f);
  // Validation catches the injected unequal resolve dimensions; do not execute UB.
  int proposedWidth=inject?out.w/2:out.w;require((proposedWidth!=out.w)==inject,"resolve dimensions preflight");
  glBlitFramebuffer(0,0,out.w,out.h,0,0,out.w,out.h,GL_COLOR_BUFFER_BIT,GL_NEAREST);check("MSAA resolve");
  draw(out,"in vec2 uv;uniform sampler2D image;out vec4 color;void main(){vec3 x=texture(image,uv).rgb;color=vec4("+std::string(visualFault?"x":"x/(1.+x)")+",1);}",resolved.t);
  detail="\"resolve_format\":\"RGBA8\",\"samples\":"+std::to_string(n)+",\"resolve_filter\":\"GL_NEAREST\",\"scope\":\"LDR MSAA premultiplied full-coverage blending followed by tonemap; edge coverage not certified; HDR path separate\"";
  glDeleteProgram(p);glDeleteRenderbuffers(1,&r);glDeleteFramebuffers(1,&f);
}
void alpha(Target& out,bool inject) {
  draw(out,"out vec4 color;void main(){color=vec4(.1,.2,.3,1);}");
  glEnable(GL_BLEND);glBlendFunc(GL_ONE,GL_ONE_MINUS_SRC_ALPHA);
  std::string premultiply=inject?"a*a":"a";
  draw(out,"in vec2 uv;out vec4 color;void main(){float a=.25+.5*uv.x;color=vec4(vec3(.8,.4,.2)*"+premultiply+",a);}");
  draw(out,"in vec2 uv;out vec4 color;void main(){float a=distance(uv,vec2(.5))<.25?.5:0.;color=vec4(vec3(.2,.6,1.)*a,a);}");
  glDisable(GL_BLEND);detail="\"blend\":\"premultiplied ONE,ONE_MINUS_SRC_ALPHA\",\"layers\":[\"glass_gradient\",\"particle_disk\"]";
}
void srgb(Target& out,bool inject) {
  // Source bytes are sRGB, sampled as linear. Lighting occurs before exactly one
  // fixed-function sRGB encode, then decoded on sampling for SDR output encoding.
  GLuint t,f,s;glGenTextures(1,&t);glBindTexture(GL_TEXTURE_2D,t);glTexStorage2D(GL_TEXTURE_2D,1,GL_SRGB8_ALPHA8,1,1);
  const unsigned char pixel[]={128,192,64,255};glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE,pixel);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
  glGenTextures(1,&s);glBindTexture(GL_TEXTURE_2D,s);glTexStorage2D(GL_TEXTURE_2D,1,GL_SRGB8_ALPHA8,out.w,out.h);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
  glGenFramebuffers(1,&f);glBindFramebuffer(GL_FRAMEBUFFER,f);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,s,0);
  require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"sRGB FBO");glViewport(0,0,out.w,out.h);
  GLuint p=program(vs,h+"in vec2 uv;uniform sampler2D image;out vec4 color;void main(){vec3 c=texture(image,uv).rgb*uv.x;"+std::string(inject?"c=pow(c,vec3(1./2.2));":"")+"color=vec4(c,1);}");
  glUseProgram(p);tex(p,"image",t,0);glDrawArrays(GL_TRIANGLES,0,3);
  draw(out,R"(in vec2 uv;uniform sampler2D image;out vec4 color;
vec3 encode(vec3 x){return mix(1.055*pow(x,vec3(1./2.4))-.055,12.92*x,lessThanEqual(x,vec3(.0031308)));}
void main(){color=vec4(encode(texture(image,uv).rgb),1);})",s);
  detail="\"input\":\"SRGB8_ALPHA8\",\"lighting\":\"linear\",\"intermediate\":\"SRGB8_ALPHA8 FBO\",\"readback\":\"encoded RGB8\"";
  glDeleteProgram(p);glDeleteFramebuffers(1,&f);glDeleteTextures(1,&s);glDeleteTextures(1,&t);
}
void hdr(Target& out,bool inject) {
  require(extension("GL_EXT_color_buffer_half_float")||extension("GL_EXT_color_buffer_float"),"BLOCKED_BY_CAPABILITY: half float color renderability");
  Target radiance(out.w,out.h,false,true);
  draw(radiance,"in vec2 uv;out vec4 color;void main(){vec3 x=vec3(8.*uv.x,2.*uv.x,.5*uv.x);color=vec4("+std::string(inject?"min(x,1.)":"x")+",1);}");
  draw(out,"in vec2 uv;uniform sampler2D image;out vec4 color;void main(){vec3 x=texture(image,uv).rgb;color=vec4(x/(1.+x),1);}",radiance.t);
  detail="\"intermediate\":\"RGBA16F\",\"tonemap\":\"Reinhard\",\"injection\":\"pre-tonemap HDR clamp\"";
}
}
int main(int argc,char** argv) {
 try {
  require(argc==4,"usage: pipeline-lab S01..S10|C01..C06 capture.ppm baseline|injected");
  std::string id=argv[1],mode=argv[3];require(mode=="baseline"||mode=="injected","invalid mode");bool injected=mode=="injected";
  Es30Context context;Target out(32,32);glDisable(GL_DITHER);
  using namespace pipeline;
  if(id=="S01") {
    GLint major=0,minor=0;glGetIntegerv(GL_MAJOR_VERSION,&major);glGetIntegerv(GL_MINOR_VERSION,&minor);
    std::string versions="[";int compiled=0;
    for(int version:{300,310,320}) {if(major*100+minor*10<version) continue;
      std::string header="#version "+std::to_string(version)+" es\nprecision highp float;\n";
      GLuint p=program(header+"void main(){gl_Position=vec4(0,0,0,1);}",header+flat);glDeleteProgram(p);
      if(compiled++) versions+=",";
      versions+=std::to_string(version);
    }
    bool rejected=false;try{GLuint p=program(vs,"#version 300 es\n#extension GL_NONEXISTENT_pipeline_test : require\nprecision highp float;\n"+flat);glDeleteProgram(p);}catch(const std::runtime_error&){rejected=true;}
    require(rejected,"missing extension must fail compiler");draw(out,flat);detail="\"compiled_glsl_versions\":"+versions+"],\"missing_extension_rejected\":true";
  } else if(id=="S02"||id=="S10") {
    const std::string stages="VERTEX:"+std::to_string(vs.size())+":"+vs+"FRAGMENT:"+std::to_string((h+flat).size())+":"+h+flat;
    const auto key=cache_key(stages,"QUALITY=1");require(key!=cache_key(stages+" ","QUALITY=1")&&key!=cache_key(stages,"QUALITY=2")&&key!=cache_key(stages,"QUALITY=1","changed-driver"),"cache invalidation");
    bool supported=false,fallback=false;GLuint p=binary_roundtrip(injected,supported,fallback);
    require(!injected||fallback,"bad binary failed to trigger fallback");out.bind();glUseProgram(p);glDrawArrays(GL_TRIANGLES,0,3);glDeleteProgram(p);
    if(id=="S10") {
      const std::string first=detail;std::string samples="[{"+first+"}";
      for(int trial=1;trial<4;++trial) {
        bool hasBinary=false,didFallback=false;GLuint timed=binary_roundtrip(injected,hasBinary,didFallback);
        require(!injected||didFallback,"startup corrupt cache fallback");out.bind();glUseProgram(timed);glDrawArrays(GL_TRIANGLES,0,3);glDeleteProgram(timed);
        samples+=",{"+detail+"}";
      }
      detail=first+",\"startup_trials\":"+samples+"],\"diagnosis\":"+quote(injected?"invalid binary causes source recompilation":"valid binary loaded; compare host trial distributions only");
    }
    // Simulate three stale cache envelopes: never submit a mismatching binary.
    int invalidations=0;
    for(const auto& stale:{cache_key(stages+" ","QUALITY=1"),cache_key(stages,"QUALITY=2"),cache_key(stages,"QUALITY=1","changed-driver")}) {
      if(stale!=key) {
        GLuint fresh=program(vs,h+flat);out.bind();glUseProgram(fresh);glDrawArrays(GL_TRIANGLES,0,3);glDeleteProgram(fresh);++invalidations;
      }
    }
    require(invalidations==3,"cache stale envelope source fallback");
    detail+=",\"source_macro_driver_invalidations\":3,\"timing_scope\":\"host wall clock; not GPU performance or guaranteed cold driver cache\"";
  } else if(id=="S09") {
    GLuint variant=program(vs,h+"layout(std140) uniform Material{vec4 baseColor;float metallic;float roughness;};out vec4 color;void main(){color=vec4(baseColor.rgb*roughness+metallic,1);}");
    const char* member="roughness";GLuint index;GLint offset;glGetUniformIndices(variant,1,&member,&index);glGetActiveUniformsiv(variant,1,&index,GL_UNIFORM_OFFSET,&offset);
    require(offset==20 && offset!=16,"variant ABI divergence not detected");glDeleteProgram(variant);material(out,injected,false,true);detail+=",\"variant_ABI_conflict_rejected\":true";
  } else if(id=="S03"||id=="C05") material(out,injected,id=="C05"&&injected);
  else if(id=="S04"||id=="C04") bloom(out,injected);
  else if(id=="S05") compute_draw(out,injected);
  else if(id=="S06"||id=="C06") msaa(out,injected,id=="C06"&&injected);
  else if(id=="S07"||id=="C02") alpha(out,injected);
  else if(id=="S08"||id=="C01") srgb(out,injected);
  else if(id=="C03") hdr(out,injected);
  else throw std::runtime_error("unknown scene");
  save_ppm(out,argv[2]);check("pipeline completion");
  std::cout<<"{\"status\":\"PASS\",\"scene\":"<<quote(id.c_str())<<",\"mode\":"<<quote(mode.c_str())<<",\"renderer\":"<<quote(reinterpret_cast<const char*>(glGetString(GL_RENDERER)))<<",\"version\":"<<quote(reinterpret_cast<const char*>(glGetString(GL_VERSION)))<<","<<detail<<"}\n";
 } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
