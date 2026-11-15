#!/usr/bin/env python3
"""Actual software EGL multi-surface/share/thread lifecycle; no platform-window claims."""
import argparse,ctypes as C,hashlib,importlib.util,json,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('egl_host',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
U,I,P,F=d.U,d.I,d.P,d.F

def run(config,output):
 h=d.Host(config);rows=[];contexts=[];surfaces=[];texture=U()
 def egl(name,ret,args):return h.fn(name,ret,args,True)
 def check(name,ok,**observed):rows.append(dict(id=name,status='PASS' if ok else 'FAIL',**observed))
 make=egl('eglMakeCurrent',U,[P,P,P,P]);error=egl('eglGetError',U,[])
 cfg=P();n=I();attrs=(I*13)(0x3033,1,0x3040,0x40,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038)
 egl('eglChooseConfig',U,[P,P,P,I,P])(h.d,attrs,C.byref(cfg),1,C.byref(n));check('config-discovery',n.value>0)
 def context(share):
  c=egl('eglCreateContext',P,[P,P,P,P])(h.d,cfg,share,(I*3)(0x3098,3,0x3038))
  if not c:raise RuntimeError('context creation failed')
  contexts.append(c);return c
 def surface(size):
  s=egl('eglCreatePbufferSurface',P,[P,P,P])(h.d,cfg,(I*5)(0x3057,size,0x3056,size,0x3038))
  if not s:raise RuntimeError('pbuffer creation failed')
  surfaces.append(s);return s
 def shared_pixel():
  fb=U();h.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));h.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb)
  h.fn('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0,0xde1,texture,0)
  pixel=(C.c_ubyte*4)();h.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,1,1,0x1908,0x1401,pixel)
  h.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);h.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(fb));return list(pixel),h.error()
 try:
  shared=context(h.c);isolated=context(None);s8=surface(8)
  h.fn('glGenTextures',None,[I,P])(1,C.byref(texture));h.fn('glBindTexture',None,[U,U])(0xde1,texture)
  rgba=(C.c_ubyte*4)(32,64,128,255);h.fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,0x8058,1,1,0,0x1908,0x1401,rgba);h.fn('glFinish',None,[])()
  check('second-surface-shared-context-current',bool(make(h.d,s8,s8,shared)))
  pixel,err=shared_pixel();check('shared-texture-readback',pixel==list(rgba) and err==0,pixel=pixel,gl_error=err)
  check('isolated-context-current',bool(make(h.d,s8,s8,isolated)))
  check('nonshared-texture-invisible',not h.fn('glIsTexture',U,[U])(texture))
  make(h.d,h.s,h.s,h.c)
  # Same context cannot be current in another thread concurrently.
  result={}
  def conflict():
   result['make']=bool(make(h.d,s8,s8,h.c));result['error']=error()
   if result['make']:make(h.d,None,None,None)
  thread=threading.Thread(target=conflict);thread.start();thread.join()
  check('cross-thread-current-conflict',not result['make'] and result['error']==0x3002,**result)
  # Shared context uses its own pbuffer on a second thread, with deterministic join.
  result={}
  def worker():
   result['make']=bool(make(h.d,s8,s8,shared))
   if result['make']:result['pixel'],result['gl_error']=shared_pixel()
   result['released']=bool(make(h.d,None,None,None))
  thread=threading.Thread(target=worker);thread.start();thread.join()
  check('dual-thread-shared-readback',result.get('pixel')==list(rgba) and result.get('gl_error')==0 and result['released'],**result)
  check('pause-release',bool(make(h.d,None,None,None)));check('resume-original-surface',bool(make(h.d,h.s,h.s,h.c)))
  check('pbuffer-swap-not-window-presentation',bool(egl('eglSwapBuffers',U,[P,P])(h.d,h.s)))
  result=egl('eglSwapBuffers',U,[P,P])(h.d,None);code=error();check('invalid-surface-fault',not result and code==0x300d,egl_error=code)
  value=I();result=egl('eglQuerySurface',U,[P,P,I,P])(h.d,h.s,0xdead,C.byref(value));code=error();check('invalid-surface-attribute',not result and code==0x3004,egl_error=code)
  check('recover-after-errors',bool(make(h.d,h.s,h.s,h.c)))
  # Pbuffer size is immutable: destroy unused surface and recreate, not pretend resize.
  check('destroy-unused-surface',bool(egl('eglDestroySurface',U,[P,P])(h.d,s8)));surfaces.remove(s8);s16=surface(16)
  check('recreated-surface-current',bool(make(h.d,s16,s16,h.c)));egl('eglQuerySurface',U,[P,P,I,P])(h.d,s16,0x3057,C.byref(value));check('resize-via-recreation',value.value==16,width=value.value)
  h.fn('glClearColor',None,[F]*4)(.25,.5,.75,1);h.fn('glClear',None,[U])(0x4000);pixel=(C.c_ubyte*4)();h.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,1,1,0x1908,0x1401,pixel)
  check('recreated-surface-pixels',max(abs(a-b) for a,b in zip(pixel,[64,128,191,255]))<=1,pixel=list(pixel))
  version=egl('eglQueryString',C.c_char_p,[P,I])(h.d,0x3054).decode();extensions=egl('eglQueryString',C.c_char_p,[P,I])(h.d,0x3055).decode().split()
  if version.startswith('1.5') or 'EGL_KHR_surfaceless_context' in extensions:
   check('surfaceless-current',bool(make(h.d,None,None,h.c)));make(h.d,s16,s16,h.c)
  else:rows.append(dict(id='surfaceless-current',status='NOT_SUPPORTED'))
  if version.startswith('1.5'):
   image=egl('eglCreateImage',P,[P,P,U,P,P])(h.d,h.c,0x30b1,P(texture.value),(C.c_ssize_t*3)(0x30bc,0,0x3038))
   check('egl-image-from-texture',bool(image))
   if image:check('egl-image-destroy',bool(egl('eglDestroyImage',U,[P,P])(h.d,image)))
   invalid=egl('eglCreateImage',P,[P,P,U,P,P])(h.d,h.c,0xdead,P(texture.value),(C.c_ssize_t*1)(0x3038));code=error();check('egl-image-invalid-target',not invalid and code==0x300c,egl_error=code)
   sync=egl('eglCreateSync',P,[P,U,P])(h.d,0x30f9,(C.c_ssize_t*1)(0x3038))
   if sync:
    waited=egl('eglClientWaitSync',I,[P,P,I,C.c_uint64])(h.d,sync,1,1000000000);check('egl-fence-sync',waited==0x30f6,result=waited);check('egl-sync-destroy',bool(egl('eglDestroySync',U,[P,P])(h.d,sync)))
   else:check('egl-fence-sync',False,egl_error=error())
  else:rows.append(dict(id='egl-fence-sync',status='NOT_SUPPORTED'))
  check('restore-original-for-cleanup',bool(make(h.d,h.s,h.s,h.c)))
 finally:
  make(h.d,h.s,h.s,h.c)
  if texture.value:h.fn('glDeleteTextures',None,[I,P])(1,C.byref(texture))
  for c in contexts:check('context-destroy',bool(egl('eglDestroyContext',U,[P,P])(h.d,c)))
  for s in surfaces:check('surface-destroy',bool(egl('eglDestroySurface',U,[P,P])(h.d,s)))
  h.close()
 r=dict(status='FAIL' if any(x['status']=='FAIL' for x in rows) else 'HOST_PASS',scope='software EGL pbuffers only; not Android/window compositor/device-reset reproduction',rows=rows,platform_gaps=['Android Java/NDK device lifecycle NOT_RUN','Windows x64/ARM64 native target NOT_RUN','GBM/Wayland/X11 windows NOT_RUN','EGLImage native import/export NOT_RUN; texture image creation/destroy tested','actual surface loss/context reset NOT_RUN'],source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest());path=Path(output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
