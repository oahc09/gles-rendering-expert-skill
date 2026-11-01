// SPDX-License-Identifier: MIT
#pragma once
#include <EGL/egl.h>
#include <GLES3/gl3.h>
#include <array>
#include <cstdint>
#include <map>
#include <mutex>
#include <stdexcept>
#include <string>
#ifdef __ANDROID__
#include <android/native_window.h>
#endif
// One EGL share group, up to four window/pbuffer surfaces, serialized entry
// points. Contexts are always unbound before handing the mutex to another owner.
// This supports one scheduler or per-surface schedulers, not parallel GL calls.
class MultiSurface {
 inline static std::mutex displayMutex_;
 inline static EGLDisplay sharedDisplay_=EGL_NO_DISPLAY;
 inline static unsigned displayUsers_=0;
 static EGLDisplay acquireDisplay(){std::lock_guard<std::mutex> lock(displayMutex_);if(displayUsers_==0){auto d=eglGetDisplay(EGL_DEFAULT_DISPLAY);require(d!=EGL_NO_DISPLAY&&eglInitialize(d,nullptr,nullptr),"display initialize");sharedDisplay_=d;}++displayUsers_;return sharedDisplay_;}
 static void releaseDisplay(){std::lock_guard<std::mutex> lock(displayMutex_);if(displayUsers_>0&&--displayUsers_==0){eglTerminate(sharedDisplay_);sharedDisplay_=EGL_NO_DISPLAY;}}
 struct Entry { EGLSurface surface=EGL_NO_SURFACE;EGLContext context=EGL_NO_CONTEXT;GLuint vao=0;bool paused=false,retired=false;int width=16,height=16;
#ifdef __ANDROID__
 ANativeWindow* window=nullptr;
#endif
 };
 std::mutex mutex_;EGLDisplay display_=EGL_NO_DISPLAY;EGLConfig config_{};EGLSurface rootSurface_=EGL_NO_SURFACE;EGLContext root_=EGL_NO_CONTEXT;
 GLuint texture_=0,program_=0;std::map<uint64_t,Entry> entries_;uint64_t next_=1,generation_=0;
 static void require(bool x,const char*m){if(!x)throw std::runtime_error(m);}
 static GLuint shader(GLenum type,const char*s){GLuint h=glCreateShader(type);glShaderSource(h,1,&s,nullptr);glCompileShader(h);GLint ok=0;glGetShaderiv(h,GL_COMPILE_STATUS,&ok);if(!ok){glDeleteShader(h);throw std::runtime_error("multisurface shader compile");}return h;}
 EGLContext context(){EGLint a[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};return eglCreateContext(display_,config_,root_,a);}
 EGLSurface surface(Entry&e){
#ifdef __ANDROID__
 if(e.window){EGLint visual=0;if(!eglGetConfigAttrib(display_,config_,EGL_NATIVE_VISUAL_ID,&visual)||ANativeWindow_setBuffersGeometry(e.window,0,0,visual)!=0)return EGL_NO_SURFACE;return eglCreateWindowSurface(display_,config_,e.window,nullptr);}
#endif
 EGLint a[]={EGL_WIDTH,e.width,EGL_HEIGHT,e.height,EGL_NONE};return eglCreatePbufferSurface(display_,config_,a);
 }
 void unbind(){eglMakeCurrent(display_,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);}
 void rootCreate(){
  EGLint ca[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};root_=eglCreateContext(display_,config_,EGL_NO_CONTEXT,ca);EGLint sa[]={EGL_WIDTH,1,EGL_HEIGHT,1,EGL_NONE};rootSurface_=eglCreatePbufferSurface(display_,config_,sa);
  require(root_!=EGL_NO_CONTEXT&&rootSurface_!=EGL_NO_SURFACE&&eglMakeCurrent(display_,rootSurface_,rootSurface_,root_),"root context");
  const char* vs="#version 300 es\nprecision highp float;out vec2 uv;void main(){vec2 p=vec2(float((gl_VertexID<<1)&2),float(gl_VertexID&2));uv=p;gl_Position=vec4(p*2.-1.,0,1);}";
  const char* fs="#version 300 es\nprecision highp float;in vec2 uv;uniform sampler2D tex;out vec4 color;void main(){color=texture(tex,uv);}";
  GLuint v=shader(GL_VERTEX_SHADER,vs),f=shader(GL_FRAGMENT_SHADER,fs);program_=glCreateProgram();glAttachShader(program_,v);glAttachShader(program_,f);glLinkProgram(program_);glDeleteShader(v);glDeleteShader(f);GLint ok=0;glGetProgramiv(program_,GL_LINK_STATUS,&ok);require(ok,"root program link");
  glGenTextures(1,&texture_);glBindTexture(GL_TEXTURE_2D,texture_);const std::array<unsigned char,4> pixel{31,127,223,255};glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,1,1,0,GL_RGBA,GL_UNSIGNED_BYTE,pixel.data());glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
  require(glGetError()==GL_NO_ERROR,"root resources");glFinish();unbind();++generation_;
 }
 void entryDestroy(Entry&e,bool live){
  if(live&&e.context!=EGL_NO_CONTEXT&&e.surface!=EGL_NO_SURFACE&&eglMakeCurrent(display_,e.surface,e.surface,e.context)){if(e.vao)glDeleteVertexArrays(1,&e.vao);glFinish();}
  e.vao=0;unbind();if(e.context!=EGL_NO_CONTEXT)eglDestroyContext(display_,e.context);if(e.surface!=EGL_NO_SURFACE)eglDestroySurface(display_,e.surface);e.context=EGL_NO_CONTEXT;e.surface=EGL_NO_SURFACE;
 }
 void rootDestroy(bool live){if(live&&root_!=EGL_NO_CONTEXT&&rootSurface_!=EGL_NO_SURFACE&&eglMakeCurrent(display_,rootSurface_,rootSurface_,root_)){if(texture_)glDeleteTextures(1,&texture_);if(program_)glDeleteProgram(program_);glFinish();}texture_=program_=0;unbind();if(root_!=EGL_NO_CONTEXT)eglDestroyContext(display_,root_);if(rootSurface_!=EGL_NO_SURFACE)eglDestroySurface(display_,rootSurface_);root_=EGL_NO_CONTEXT;rootSurface_=EGL_NO_SURFACE;}
 void rebuild(bool live){for(auto&x:entries_)entryDestroy(x.second,live);rootDestroy(live);rootCreate();for(auto&x:entries_){auto&e=x.second;if(e.retired)continue;e.context=context();e.surface=surface(e);require(e.context!=EGL_NO_CONTEXT&&e.surface!=EGL_NO_SURFACE,"rebuild entry");}}
 uint64_t add(Entry e){
  require(entries_.size()<4,"maximum four surfaces");e.context=context();e.surface=surface(e);if(e.context==EGL_NO_CONTEXT||e.surface==EGL_NO_SURFACE){entryDestroy(e,true);
#ifdef __ANDROID__
 if(e.window)ANativeWindow_release(e.window);
#endif
 throw std::runtime_error("surface/context create");}auto id=next_++;entries_.emplace(id,e);return id;
 }
 public:
 MultiSurface(){display_=acquireDisplay();
#ifdef __ANDROID__
 constexpr EGLint types=EGL_WINDOW_BIT|EGL_PBUFFER_BIT;
#else
 constexpr EGLint types=EGL_PBUFFER_BIT;
#endif
 EGLint a[]={EGL_SURFACE_TYPE,types,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_NONE};EGLint n=0;try{require(eglBindAPI(EGL_OPENGL_ES_API),"bind GLES");require(eglChooseConfig(display_,a,&config_,1,&n)&&n,"config");rootCreate();}catch(...){rootDestroy(true);releaseDisplay();throw;}}
 ~MultiSurface(){std::lock_guard<std::mutex> lock(mutex_);for(auto&x:entries_){entryDestroy(x.second,true);
#ifdef __ANDROID__
 if(x.second.window)ANativeWindow_release(x.second.window);
#endif
 }rootDestroy(true);releaseDisplay();}
 MultiSurface(const MultiSurface&)=delete;MultiSurface&operator=(const MultiSurface&)=delete;
 uint64_t pbuffer(int w,int h){std::lock_guard<std::mutex>lock(mutex_);require(w>0&&h>0,"positive size");Entry e;e.width=w;e.height=h;return add(e);}
#ifdef __ANDROID__
 uint64_t window(ANativeWindow*w){std::lock_guard<std::mutex>lock(mutex_);require(w,"window null");require(entries_.size()<4,"maximum four surfaces");ANativeWindow_acquire(w);Entry e;e.window=w;return add(e);}
#endif
 void remove(uint64_t id){std::lock_guard<std::mutex>lock(mutex_);auto i=entries_.find(id);if(i==entries_.end())return;entryDestroy(i->second,true);
#ifdef __ANDROID__
 if(i->second.window)ANativeWindow_release(i->second.window);
#endif
 entries_.erase(i);}
 void pause(uint64_t id,bool paused){std::lock_guard<std::mutex>lock(mutex_);auto i=entries_.find(id);if(i!=entries_.end())i->second.paused=paused;}
 void surfaceLost(uint64_t id){std::lock_guard<std::mutex>lock(mutex_);auto i=entries_.find(id);if(i!=entries_.end()){i->second.retired=true;entryDestroy(i->second,true);}}
 void forceRebuild(){std::lock_guard<std::mutex>lock(mutex_);rebuild(true);}
 uint64_t generation(){std::lock_guard<std::mutex>lock(mutex_);return generation_;}
 bool render(uint64_t id,bool verify=false){std::lock_guard<std::mutex>lock(mutex_);auto i=entries_.find(id);if(i==entries_.end()||i->second.paused)return false;auto&e=i->second;if(e.context==EGL_NO_CONTEXT||e.surface==EGL_NO_SURFACE)return false;
  if(!eglMakeCurrent(display_,e.surface,e.surface,e.context)){EGLint error=eglGetError();if(error==EGL_CONTEXT_LOST){rebuild(false);return false;}if(error==EGL_BAD_SURFACE||error==EGL_BAD_NATIVE_WINDOW){e.retired=true;entryDestroy(e,true);return false;}throw std::runtime_error("makeCurrent failed");}
  struct Unbind {MultiSurface*self;~Unbind(){self->unbind();}} guard{this};
  EGLint w=0,h=0;require(eglQuerySurface(display_,e.surface,EGL_WIDTH,&w)&&eglQuerySurface(display_,e.surface,EGL_HEIGHT,&h),"surface dimensions");if(w<=0||h<=0)return false;
  if(!e.vao){glGenVertexArrays(1,&e.vao);}glBindVertexArray(e.vao);glViewport(0,0,w,h);glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glUseProgram(program_);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,texture_);glUniform1i(glGetUniformLocation(program_,"tex"),0);glDrawArrays(GL_TRIANGLES,0,3);
  if(verify){std::array<unsigned char,4>p{};glReadPixels(w/2,h/2,1,1,GL_RGBA,GL_UNSIGNED_BYTE,p.data());require(p==std::array<unsigned char,4>{31,127,223,255},"shared texture pixel mismatch");}require(glGetError()==GL_NO_ERROR,"render GL error");
  if(!eglSwapBuffers(display_,e.surface)){EGLint error=eglGetError();if(error==EGL_CONTEXT_LOST){unbind();rebuild(false);return false;}if(error==EGL_BAD_SURFACE||error==EGL_BAD_NATIVE_WINDOW){e.retired=true;entryDestroy(e,true);return false;}throw std::runtime_error("swap failed");}return true;
 }
};
