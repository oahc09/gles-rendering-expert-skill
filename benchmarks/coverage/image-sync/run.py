#!/usr/bin/env python3
import argparse,ctypes as C,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('sync_host',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
U=d.U;I=d.I;P=d.P
VERT='#version 300 es\nvoid main(){vec2 p=vec2(float((gl_VertexID<<1)&2),float(gl_VertexID&2));gl_Position=vec4(p*2.-1.,0.,1.);}'
PRODUCER='#version 300 es\nprecision highp float;uniform int frame;out vec4 c;void main(){float x=floor(gl_FragCoord.x),y=floor(gl_FragCoord.y);c=vec4(17.+31.*x+7.*y+float(frame)*3.,23.+11.*x+43.*y,31.+19.*x+13.*y,97.+17.*x+23.*y)/255.;}'
CONSUMER='#version 300 es\n#extension GL_OES_EGL_image_external_essl3 : require\nprecision highp float;uniform samplerExternalOES src;out vec4 c;void main(){c=texture(src,gl_FragCoord.xy/4.);}'
def golden(frame):return [v for y in range(4) for x in range(4) for v in (17+31*x+7*y+frame*3,23+11*x+43*y,31+19*x+13*y,97+17*x+23*y)]
def admit(has_fence,wait_ok):return has_fence is True and wait_ok is True

def release_owned(record,releasers):
 errors=[]
 for key in ('ext','image','sync','fb','tex'):
  if record.get(key):
   try:
    if releasers[key](record[key]) is False:raise RuntimeError('RELEASE_FAILED')
    record[key]=None
   except Exception:errors.append(key)
 if errors:raise RuntimeError('OWNED_RELEASE_FAILED')

def best_effort(steps):
 results=[]
 for step in steps:
  try:results.append(step() is not False)
  except Exception:results.append(False)
 return results

def run(config):
 h=d.Host(config);consumer=None;programs=[];owned=[];frames=[]
 r={'schema_version':1,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'execution_class':'SOFTWARE_HOST','physical_device':'NOT_RUN','performance':'NOT_MEASURED','status':'FAIL','glFinish_calls':0,'threads':1}
 def glcheck():
  if h.error():raise RuntimeError('GL_ERROR')
 def eglcheck():
  if h.fn('eglGetError',U,[],True)()!=0x3000:raise RuntimeError('EGL_ERROR')
 def current(c):
  if not h.fn('eglMakeCurrent',U,[P,P,P,P],True)(h.d,h.s,h.s,c):raise RuntimeError('MAKE_CURRENT_FAILED')
 def delete_gl(name,value):
  current(h.c);h.fn(name,None,[I,P])(1,C.byref(value));glcheck();return True
 def cleanup(record):
  release_owned(record,{'ext':lambda x:delete_gl('glDeleteTextures',x),'image':lambda x:bool(destroy(h.d,x)),'sync':lambda x:bool(free(h.d,x)),'fb':lambda x:delete_gl('glDeleteFramebuffers',x),'tex':lambda x:delete_gl('glDeleteTextures',x)})
 def proc(n,ret,args):
  p=h.fn('eglGetProcAddress',P,[C.c_char_p],True)(n.encode())
  if not p:raise RuntimeError('MISSING_ENTRYPOINT')
  return C.CFUNCTYPE(ret,*args)(p)
 try:
  ex=h.fn('eglQueryString',C.c_char_p,[P,I],True)(h.d,0x3055).decode().split();required=['EGL_KHR_image_base','EGL_KHR_gl_texture_2D_image','EGL_KHR_fence_sync','EGL_KHR_wait_sync'];r['capabilities']={n:n in ex for n in required};r['capabilities'].update({n:n in h.metadata['extensions'] for n in ['GL_OES_EGL_image_external','GL_OES_EGL_image_external_essl3']})
  if not all(r['capabilities'].values()):r['status']='UNSUPPORTED';return r
  create=proc('eglCreateImageKHR',P,[P,P,U,P,P]);destroy=proc('eglDestroyImageKHR',U,[P,P]);bind=proc('glEGLImageTargetTexture2DOES',None,[U,P]);fence=proc('eglCreateSyncKHR',P,[P,U,P]);free=proc('eglDestroySyncKHR',U,[P,P]);server=proc('eglWaitSyncKHR',I,[P,P,I]);client=proc('eglClientWaitSyncKHR',I,[P,P,I,C.c_uint64])
  configid=I();h.fn('eglQueryContext',U,[P,P,I,P],True)(h.d,h.c,0x3028,C.byref(configid));cfg=P();num=I();h.fn('eglChooseConfig',U,[P,P,P,I,P],True)(h.d,(I*3)(0x3028,configid.value,0x3038),C.byref(cfg),1,C.byref(num));consumer=h.fn('eglCreateContext',P,[P,P,P,P],True)(h.d,cfg,h.c,(I*3)(0x3098,3,0x3038));eglcheck()
  if not consumer:raise RuntimeError('SHARED_CONTEXT_FAILED')
  def program(frag):
   p,info=h.program({'shader.vert':VERT,'shader.frag':frag});programs.append(p)
   if not info['compile'] or not info['link']:raise RuntimeError('SHADER_FAILED')
   return p
  pp=program(PRODUCER);cp=program(CONSUMER)
  def setup():
   h.fn('glViewport',None,[I,I,I,I])(0,0,4,4)
   for x in [0xbd0,0xbe2,0xb71]:h.fn('glDisable',None,[U])(x)
  for route in ['server','client']:
   for frame in [0,1]:
    current(h.c);setup();record={};owned.append(record);tex=U();fb=U();h.fn('glGenTextures',None,[I,P])(1,C.byref(tex));record['tex']=tex;h.fn('glBindTexture',None,[U,U])(0xde1,tex);h.fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,0x8058,4,4,0,0x1908,0x1401,None)
    h.fn('glTexParameteri',None,[U,U,I])(0xde1,0x2801,0x2600);h.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));record['fb']=fb;h.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb);h.fn('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0,0xde1,tex,0)
    if h.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO_INCOMPLETE')
    h.fn('glUseProgram',None,[U])(pp);loc=h.fn('glGetUniformLocation',I,[U,C.c_char_p])(pp,b'frame');h.fn('glUniform1i',None,[I,I])(loc,frame);h.fn('glDrawArrays',None,[U,I,I])(4,0,3);h.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);glcheck()
    image=create(h.d,h.c,0x30b1,P(tex.value),(I*5)(0x30bc,0,0x30d2,1,0x3038));record['image']=image;eglcheck()
    if not image:raise RuntimeError('IMAGE_FAILED')
    sync=fence(h.d,0x30f9,(I*1)(0x3038));record['sync']=sync;eglcheck()
    if not sync:raise RuntimeError('FENCE_FAILED')
    h.fn('glFlush',None,[])();glcheck();current(consumer);setup()
    if route=='server':waitok=server(h.d,sync,0)==1
    else:
     status=0x30f5
     for _ in range(100):
      status=client(h.d,sync,0,1000000)
      if status!=0x30f5:break
     waitok=status==0x30f6
    eglcheck()
    if not admit(bool(sync),waitok):raise RuntimeError('WAIT_NOT_SATISFIED')
    ext=U();h.fn('glGenTextures',None,[I,P])(1,C.byref(ext));record['ext']=ext;h.fn('glBindTexture',None,[U,U])(0x8d65,ext)
    for pname,val in [(0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812f),(0x2803,0x812f)]:h.fn('glTexParameteri',None,[U,U,I])(0x8d65,pname,val)
    bind(0x8d65,image);h.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);h.fn('glUseProgram',None,[U])(cp);loc=h.fn('glGetUniformLocation',I,[U,C.c_char_p])(cp,b'src');h.fn('glUniform1i',None,[I,I])(loc,0);h.fn('glDrawArrays',None,[U,I,I])(4,0,3);out=(C.c_ubyte*64)();h.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,out);glcheck()
    frames.append({'route':route,'frame':frame,'wait_accepted':waitok,'pixels':list(out),'max_byte_error':max(abs(a-b) for a,b in zip(out,golden(frame)))})
    h.fn('glBindTexture',None,[U,U])(0x8d65,0);cleanup(record);owned.pop();eglcheck()
  r.update(frames=frames,draws=8,readbacks=4,owned_resources_released=not owned,policy_simulations={'missing_fence_rejected':not admit(False,True),'unsatisfied_wait_rejected':not admit(True,False)},status='HOST_PASS' if all(x['max_byte_error']==0 for x in frames) else 'FAIL');return r
 finally:
  try:current(h.c);has_current=True
  except Exception:has_current=False
  cleanup_results=[has_current]
  if has_current:
   cleanup_results+=best_effort([lambda record=record:cleanup(record) for record in owned])
   cleanup_results+=best_effort([lambda:h.fn('glUseProgram',None,[U])(0)]+[lambda p=p:h.fn('glDeleteProgram',None,[U])(p) for p in programs])
  else:
   # No GL calls without a valid current context. Still release EGL handles.
   for record in owned:
    for key,func in [('image',locals().get('destroy')),('sync',locals().get('free'))]:
     if record.get(key) and func:
      def release(record=record,key=key,func=func):
       ok=bool(func(h.d,record[key]))
       if ok:record[key]=None
       return ok
      cleanup_results+=best_effort([release])
  steps=[]
  if consumer:steps.append(lambda:bool(h.fn('eglDestroyContext',U,[P,P],True)(h.d,consumer)))
  steps += [lambda:bool(h.fn('eglMakeCurrent',U,[P,P,P,P],True)(h.d,None,None,None)),lambda:bool(h.fn('eglDestroySurface',U,[P,P],True)(h.d,h.s)),lambda:bool(h.fn('eglDestroyContext',U,[P,P],True)(h.d,h.c)),lambda:bool(h.fn('eglTerminate',U,[P],True)(h.d))]
  teardown=best_effort(steps);r['context_teardown_checked']=all(teardown)
  if not all(teardown+cleanup_results):raise RuntimeError('HOST_TEARDOWN_FAILED')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 try:r=run(json.loads(a.config.read_text()))
 except Exception as e:r={'status':'FAIL','error_class':type(e).__name__}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(0 if r['status']=='HOST_PASS' else 77 if r['status']=='UNSUPPORTED' else 1)
