#!/usr/bin/env python3
import argparse,ctypes as C,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('image_host',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
U=d.U;I=d.I;P=d.P
TEX=0x0de1;EXT=0x8d65
VERT='#version 300 es\nvoid main(){vec2 p=vec2(float((gl_VertexID<<1)&2),float(gl_VertexID&2));gl_Position=vec4(p*2.-1.,0.,1.);}'
def pixels():return [v for y in range(4) for x in range(4) for v in (x*60,y*60,(x+y)*30,255)]
def run(config,disabled=False):
 h=d.Host(config);textures=(U*2)();image=None;destroy=None;programs=[];vao=U()
 r={'schema_version':1,'status':'FAIL','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'execution_class':'SOFTWARE_HOST','physical_device':'NOT_RUN','AHardwareBuffer':'NOT_RUN','protected_content':'NOT_RUN','cross_context_sync':'NOT_RUN','force_disabled':disabled}
 def check():
  if h.error():raise RuntimeError('GL_ERROR')
 def proc(name,ret,args):
  p=h.fn('eglGetProcAddress',P,[C.c_char_p],True)(name.encode())
  if not p:raise RuntimeError('MISSING_ENTRYPOINT')
  return C.CFUNCTYPE(ret,*args)(p)
 try:
  egl=h.fn('eglQueryString',C.c_char_p,[P,I],True)(h.d,0x3055).decode().split();gl=h.metadata['extensions'];caps={x:x in gl for x in ['GL_OES_EGL_image','GL_OES_EGL_image_external','GL_OES_EGL_image_external_essl3']};caps.update({x:x in egl for x in ['EGL_KHR_image_base','EGL_KHR_gl_texture_2D_image']});r['capabilities']=caps
  h.fn('glGenTextures',None,[I,P])(2,textures);h.fn('glBindTexture',None,[U,U])(TEX,textures[0]);raw=(C.c_ubyte*64)(*pixels());h.fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(TEX,0,0x8058,4,4,0,0x1908,0x1401,raw)
  def parameters(target):
   for pname,value in [(0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812f),(0x2803,0x812f)]:h.fn('glTexParameteri',None,[U,U,I])(target,pname,value)
  parameters(TEX);check();h.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));h.fn('glBindVertexArray',None,[U])(vao)
  def sample(external):
   directive='#extension GL_OES_EGL_image_external_essl3 : require\n' if external else ''
   frag='#version 300 es\n'+directive+'precision highp float;uniform '+('samplerExternalOES' if external else 'sampler2D')+' src;out vec4 c;void main(){c=texture(src,gl_FragCoord.xy/4.);}'
   p,info=h.program({'shader.vert':VERT,'shader.frag':frag});programs.append(p)
   if not(info['compile'] and info['link']):raise RuntimeError('SHADER_COMPILE_LINK_FAILED')
   h.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);h.fn('glViewport',None,[I,I,I,I])(0,0,4,4);h.fn('glDisable',None,[U])(0xbd0);h.fn('glDisable',None,[U])(0xbe2);h.fn('glUseProgram',None,[U])(p);loc=h.fn('glGetUniformLocation',I,[U,C.c_char_p])(p,b'src');h.fn('glUniform1i',None,[I,I])(loc,0);h.fn('glDrawArrays',None,[U,I,I])(4,0,3);out=(C.c_ubyte*64)();h.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,out);check();return {'pixels':list(out),'max_byte_error':max(abs(a-b) for a,b in zip(out,pixels())),'compile_link':True}
  r['sampler2D_fallback']=sample(False)
  if disabled or not all(caps.values()):r.update(status='SAFE_FALLBACK_PASS' if r['sampler2D_fallback']['max_byte_error']==0 else 'FAIL',external_calls=0,reason='POLICY_DISABLED' if disabled else 'UNSUPPORTED_CAPABILITY');return r
  create=proc('eglCreateImageKHR',P,[P,P,U,P,P]);destroy=proc('eglDestroyImageKHR',U,[P,P]);bind=proc('glEGLImageTargetTexture2DOES',None,[U,P]);h.fn('glFinish',None,[])();check()
  attrs=(I*5)(0x30bc,0,0x30d2,1,0x3038);image=create(h.d,h.c,0x30b1,P(textures[0]),attrs);err=h.fn('eglGetError',U,[],True)();r['create_image_success']=bool(image) and err==0x3000
  if not r['create_image_success']:raise RuntimeError('CREATE_IMAGE_FAILED')
  h.fn('glBindTexture',None,[U,U])(EXT,textures[1]);parameters(EXT);bind(EXT,image);check();r['external_before_destroy']=sample(True)
  neg=[]
  for name,fn,args in [('mipmap-min-filter',h.fn('glTexParameteri',None,[U,U,I]),(EXT,0x2801,0x2703)),('repeat-wrap',h.fn('glTexParameteri',None,[U,U,I]),(EXT,0x2802,0x2901)),('generate-mipmap',h.fn('glGenerateMipmap',None,[U]),(EXT,))]:
   fn(*args);neg.append({'case':name,'error':h.error(),'expected':0x500})
  r['negatives']=neg;r['destroy_image_success']=bool(destroy(h.d,image));image=None;r['destroy_egl_error']=h.fn('eglGetError',U,[],True)();r['external_after_destroy']=sample(True)
  r['status']='HOST_PASS' if r['destroy_image_success'] and r['destroy_egl_error']==0x3000 and all(r[k]['max_byte_error']==0 for k in ('sampler2D_fallback','external_before_destroy','external_after_destroy')) and all(n['error']==n['expected'] for n in neg) else 'FAIL';return r
 finally:
  if image and destroy:destroy(h.d,image)
  h.fn('glUseProgram',None,[U])(0)
  for p in programs:h.fn('glDeleteProgram',None,[U])(p)
  h.fn('glDeleteTextures',None,[I,P])(2,textures);h.fn('glDeleteVertexArrays',None,[I,P])(1,C.byref(vao));h.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--disable-external',action='store_true');a=p.parse_args()
 try:r=run(json.loads(a.config.read_text()),a.disable_external)
 except Exception as e:r={'status':'FAIL','error_class':type(e).__name__}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(0 if r['status'] in ('HOST_PASS','SAFE_FALLBACK_PASS') else 1)
