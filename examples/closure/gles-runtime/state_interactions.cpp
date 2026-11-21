// SPDX-License-Identifier: MIT
#define main inherited_smoke_main
#include "../../validation/egl_smoke.cpp"
#undef main
static unsigned checks=0;
static void expect(const char* name,GLenum error){GLenum actual=glGetError();if(actual!=error)throw std::runtime_error(std::string(name)+" expected "+std::to_string(error)+" got "+std::to_string(actual));++checks;std::cout<<"{\"case\":"<<quoted(name)<<",\"expected\":"<<error<<",\"observed\":"<<actual<<",\"status\":\"PASS\"}\n";}
int main(){try{EGLSession s;s.open();
 glPixelStorei(GL_PACK_ALIGNMENT,1);expect("pack_alignment_legal",GL_NO_ERROR);glPixelStorei(GL_PACK_ALIGNMENT,3);expect("pack_alignment_invalid",GL_INVALID_VALUE);
 glPixelStorei(GL_UNPACK_ALIGNMENT,8);expect("unpack_alignment_legal",GL_NO_ERROR);glPixelStorei(GL_UNPACK_ALIGNMENT,0);expect("unpack_alignment_invalid",GL_INVALID_VALUE);
 glPixelStorei(GL_PACK_ROW_LENGTH,4);expect("pack_row_length_legal",GL_NO_ERROR);glPixelStorei(GL_PACK_ROW_LENGTH,-1);expect("pack_row_length_negative",GL_INVALID_VALUE);glPixelStorei(GL_PACK_ROW_LENGTH,0);
 glPixelStorei(GL_UNPACK_SKIP_PIXELS,2);expect("unpack_skip_legal",GL_NO_ERROR);glPixelStorei(GL_UNPACK_SKIP_PIXELS,-1);expect("unpack_skip_negative",GL_INVALID_VALUE);glPixelStorei(GL_UNPACK_SKIP_PIXELS,0);
 GLuint b=0;glGenBuffers(1,&b);glBindBuffer(GL_ARRAY_BUFFER,b);glBufferData(GL_ARRAY_BUFFER,64,nullptr,GL_DYNAMIC_DRAW);expect("buffer_size_legal",GL_NO_ERROR);glBufferData(GL_ARRAY_BUFFER,-1,nullptr,GL_DYNAMIC_DRAW);expect("buffer_size_negative",GL_INVALID_VALUE);
 const GLuint v=1;glBufferSubData(GL_ARRAY_BUFFER,60,4,&v);expect("subdata_boundary_legal",GL_NO_ERROR);glBufferSubData(GL_ARRAY_BUFFER,61,4,&v);expect("subdata_boundary_overflow",GL_INVALID_VALUE);
 void* p=glMapBufferRange(GL_ARRAY_BUFFER,0,4,GL_MAP_WRITE_BIT);require(p,"map pointer");expect("map_access_legal",GL_NO_ERROR);glUnmapBuffer(GL_ARRAY_BUFFER);glMapBufferRange(GL_ARRAY_BUFFER,0,4,0);expect("map_no_access",GL_INVALID_OPERATION);
 p=glMapBufferRange(GL_ARRAY_BUFFER,60,4,GL_MAP_WRITE_BIT);require(p,"map boundary");expect("map_range_legal",GL_NO_ERROR);glUnmapBuffer(GL_ARRAY_BUFFER);glMapBufferRange(GL_ARRAY_BUFFER,60,5,GL_MAP_WRITE_BIT);expect("map_range_overflow",GL_INVALID_VALUE);
 glBufferData(GL_ARRAY_BUFFER,64,nullptr,GL_STREAM_DRAW);expect("buffer_usage_legal",GL_NO_ERROR);glBufferData(GL_ARRAY_BUFFER,64,nullptr,GL_LINEAR);expect("buffer_usage_invalid",GL_INVALID_ENUM);
 GLuint tex=0;glGenTextures(1,&tex);glBindTexture(GL_TEXTURE_2D,tex);glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,4,4);expect("immutable_storage_legal",GL_NO_ERROR);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,4,4,0,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);expect("immutable_redefinition_invalid",GL_INVALID_OPERATION);
 glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);expect("wrap_legal",GL_NO_ERROR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_LINEAR);expect("wrap_invalid",GL_INVALID_ENUM);
 glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);expect("mag_filter_legal",GL_NO_ERROR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR_MIPMAP_LINEAR);expect("mag_filter_mipmap_invalid",GL_INVALID_ENUM);
 GLuint samp=0;glGenSamplers(1,&samp);glSamplerParameteri(samp,GL_TEXTURE_MIN_FILTER,GL_LINEAR_MIPMAP_LINEAR);expect("sampler_min_filter_legal",GL_NO_ERROR);glSamplerParameteri(samp,GL_TEXTURE_MIN_FILTER,GL_REPEAT);expect("sampler_filter_invalid",GL_INVALID_ENUM);
 GLuint fbo=0;glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT,"empty FBO");glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,tex,0);require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"complete FBO");glReadBuffer(GL_COLOR_ATTACHMENT0);expect("named_readbuffer_legal",GL_NO_ERROR);glReadBuffer(GL_BACK);expect("named_readbuffer_back_invalid",GL_INVALID_OPERATION);glReadBuffer(GL_COLOR_ATTACHMENT0);
 GLenum draw=GL_COLOR_ATTACHMENT0;glDrawBuffers(1,&draw);expect("named_drawbuffer_legal",GL_NO_ERROR);draw=GL_BACK;glDrawBuffers(1,&draw);expect("named_drawbuffer_back_invalid",GL_INVALID_OPERATION);
 GLuint rb=0;glGenRenderbuffers(1,&rb);glBindRenderbuffer(GL_RENDERBUFFER,rb);glRenderbufferStorage(GL_RENDERBUFFER,GL_DEPTH_COMPONENT16,4,4);expect("renderbuffer_format_legal",GL_NO_ERROR);glRenderbufferStorage(GL_RENDERBUFFER,GL_RGBA_INTEGER,4,4);expect("renderbuffer_format_invalid",GL_INVALID_ENUM);
 glRenderbufferStorageMultisample(GL_RENDERBUFFER,0,GL_RGBA8,4,4);expect("multisample_zero_legal",GL_NO_ERROR);glRenderbufferStorageMultisample(GL_RENDERBUFFER,-1,GL_RGBA8,4,4);expect("multisample_negative",GL_INVALID_VALUE);
 glScissor(0,0,4,4);expect("scissor_legal",GL_NO_ERROR);glScissor(0,0,-1,4);expect("scissor_negative",GL_INVALID_VALUE);
 glViewport(0,0,4,4);expect("viewport_legal",GL_NO_ERROR);glViewport(0,0,4,-1);expect("viewport_negative",GL_INVALID_VALUE);
 glDepthFunc(GL_LEQUAL);expect("depth_func_legal",GL_NO_ERROR);glDepthFunc(GL_LINEAR);expect("depth_func_invalid",GL_INVALID_ENUM);
 glStencilOp(GL_KEEP,GL_REPLACE,GL_INCR);expect("stencil_op_legal",GL_NO_ERROR);glStencilOp(GL_KEEP,GL_LINEAR,GL_INCR);expect("stencil_op_invalid",GL_INVALID_ENUM);
 glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);expect("blend_factor_legal",GL_NO_ERROR);glBlendFunc(GL_LINEAR,GL_ONE);expect("blend_factor_invalid",GL_INVALID_ENUM);
 GLsync sync=glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE,0);require(sync,"sync");expect("fence_condition_legal",GL_NO_ERROR);glFenceSync(GL_ALWAYS,0);expect("fence_condition_invalid",GL_INVALID_ENUM);
 glClientWaitSync(sync,0,0);expect("client_wait_flags_legal",GL_NO_ERROR);glClientWaitSync(sync,2,0);expect("client_wait_flags_invalid",GL_INVALID_VALUE);
 glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteSync(sync);glDeleteRenderbuffers(1,&rb);glDeleteFramebuffers(1,&fbo);glDeleteSamplers(1,&samp);glDeleteTextures(1,&tex);glDeleteBuffers(1,&b);gl_ok("cleanup");require(checks==48,"48 distinct interactions required");std::cout<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"execution_class\":\"SOFTWARE_GLES\",\"physical_performance\":null}\n";return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
