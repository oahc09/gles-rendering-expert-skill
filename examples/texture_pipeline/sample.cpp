// Original MIT host correctness harness. Reuse EGL lifetime and shader checks.
#define main established_harness_main
#include "../validation/egl_smoke.cpp"
#undef main
#include <ktx.h>
#include <fstream>
int main(int argc,char**argv){
 try{
  require(argc==3,"input KTX2, output RGBA");EGLSession session;session.open();snapshot(session);
  ktxTexture2* raw=nullptr;
  require(ktxTexture2_CreateFromNamedFile(argv[1],KTX_TEXTURE_CREATE_LOAD_IMAGE_DATA_BIT,&raw)==KTX_SUCCESS,"load KTX2");
  // Only sample the generated linear 32x32 fixture. Metadata/orientation handling
  // for general assets is deliberately outside this correctness fixture.
  require(raw->baseWidth==32&&raw->baseHeight==32&&raw->numLevels==1,"fixture extent");
  require(ktxLoadOpenGL(eglGetProcAddress)==KTX_SUCCESS,"load GL entry points");
  GLuint input=0;GLenum target=0,error=0;
  auto status=ktxTexture_GLUpload(ktxTexture(raw),&input,&target,&error);
  ktxTexture_Destroy(ktxTexture(raw));
  require(status==KTX_SUCCESS&&error==GL_NO_ERROR&&target==GL_TEXTURE_2D,"upload unsupported/failed");
  GLuint output=0,fbo=0;glGenTextures(1,&output);glBindTexture(GL_TEXTURE_2D,output);glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,32,32);
  glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,output,0);
  require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"RGBA8 output FBO");
  GLuint vs=compile(GL_VERTEX_SHADER,"#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.-1.,0,1);}",true,"texture sample vertex");
  GLuint fs=compile(GL_FRAGMENT_SHADER,"#version 300 es\nprecision highp float;uniform highp sampler2D image;out vec4 color;void main(){color=texelFetch(image,ivec2(gl_FragCoord.xy),0);}",true,"texture sample fragment");
  GLuint program=glCreateProgram();glAttachShader(program,vs);glAttachShader(program,fs);glLinkProgram(program);GLint linked=0;glGetProgramiv(program,GL_LINK_STATUS,&linked);require(linked,"sample link");
  glUseProgram(program);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,input);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);glUniform1i(glGetUniformLocation(program,"image"),0);
  glViewport(0,0,32,32);glDisable(GL_BLEND);glDisable(GL_DITHER);glDrawArrays(GL_TRIANGLES,0,3);
  std::array<unsigned char,4096> pixels{};glReadBuffer(GL_COLOR_ATTACHMENT0);glReadPixels(0,0,32,32,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());gl_ok("compressed texture sample/readback");
  std::ofstream file(argv[2],std::ios::binary);file.write(reinterpret_cast<const char*>(pixels.data()),pixels.size());require(bool(file),"output write");
  glDeleteProgram(program);glDeleteShader(vs);glDeleteShader(fs);glDeleteTextures(1,&input);glDeleteTextures(1,&output);glDeleteFramebuffers(1,&fbo);
  pass("texture-upload-sample-readback-software-only");
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}
}
