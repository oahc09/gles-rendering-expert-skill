#!/usr/bin/env python3
import argparse,ctypes as C,hashlib,importlib.util,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools/coverage'))
from priority_boundaries import decide
spec=importlib.util.spec_from_file_location('priority_egl',ROOT/'examples/closure/egl-lifecycle/run.py');life=importlib.util.module_from_spec(spec);spec.loader.exec_module(life)
d=life.d;U,I,P,F=d.U,d.I,d.P,d.F

def result_status(rows):
 families={'sync','eglimage','robustness','astc','msrtt','protected'}
 if len(rows)!=6 or {r.get('family') for r in rows}!=families or any(r.get('status') not in ('PASS','NOT_SUPPORTED') for r in rows):return 'FAIL'
 return 'HOST_PROBES_PASS_WITH_UNSUPPORTED' if any(r['status']=='NOT_SUPPORTED' for r in rows) else 'HOST_PASS'
def run(config,output):
 with tempfile.TemporaryDirectory() as td:prior=life.run(config,Path(td)/'egl.json')
 h=d.Host(config);rows=[]
 def proc(name,ret,args,egl=False):
  try:return h.fn(name,ret,args,egl)
  except AttributeError:
   addr=h.fn('eglGetProcAddress',P,[C.c_char_p],True)(name.encode())
   return C.CFUNCTYPE(ret,*args)(addr) if addr else None
 try:
  gl_ext=h.metadata['extensions'];egl_ext=h.fn('eglQueryString',C.c_char_p,[P,I],True)(h.d,0x3055).decode().split();version=h.fn('eglQueryString',C.c_char_p,[P,I],True)(h.d,0x3054).decode().split()[0];major=I();minor=I();h.fn('glGetIntegerv',None,[U,P])(0x821b,C.byref(major));h.fn('glGetIntegerv',None,[U,P])(0x821c,C.byref(minor));gles=f'{major.value}.{minor.value}'
  for family,ids,names,facts in [('sync',['egl-fence-sync','egl-sync-destroy'],['eglCreateSync','eglClientWaitSync','eglDestroySync'],{'current_context':True}),('eglimage',['egl-image-from-texture','egl-image-destroy','egl-image-invalid-target'],['eglCreateImage','eglDestroyImage'],{'owned_complete_2d_texture':True})]:
   passed=all(any(r['id']==i and r['status']=='PASS' for r in prior['rows']) for i in ids)
   decision=decide(family,egl=version,gl_extensions=gl_ext,egl_extensions=egl_ext,entrypoints=names,facts=facts,probe_pass=passed)
   failed=any(r['id'] in ids and r['status']=='FAIL' for r in prior['rows']);rows.append(dict(family=family,status='FAIL' if failed else 'PASS' if decision['usable'] else 'NOT_SUPPORTED',decision=decision,evidence_source_sha256=prior['source_sha256']))
  name='glGetGraphicsResetStatus' if (major.value,minor.value)>=(3,2) else 'glGetGraphicsResetStatusKHR';fn=proc(name,U,[])
  route=(major.value,minor.value)>=(3,2) or 'GL_KHR_robustness' in gl_ext
  if route and fn:
   code=fn();err=h.error();passed=code==0 and err==0;decision=decide('robustness',gles=gles,gl_extensions=gl_ext,entrypoints=[name],facts={'operation':'reset_query_only'},probe_pass=passed);rows.append(dict(family='robustness',status='PASS' if passed and decision['usable'] else 'FAIL',reset_status=code,gl_error=err,decision=decision))
  else:rows.append(dict(family='robustness',status='FAIL' if route else 'NOT_SUPPORTED',reason='advertised reset route has no exact entrypoint' if route else 'core/extension reset route absent'))
  # Only actual supported parameters are probed; no unsupported calls to manufacture errors.
  for family in ('astc','msrtt'):
   advertised=bool(set(gl_ext)&({'GL_KHR_texture_compression_astc_ldr','GL_KHR_texture_compression_astc_hdr'} if family=='astc' else {'GL_EXT_multisampled_render_to_texture'}))
   if not advertised:rows.append(dict(family=family,status='NOT_SUPPORTED'));continue
   tex=U();fb=U();h.fn('glGenTextures',None,[I,P])(1,C.byref(tex));h.fn('glBindTexture',None,[U,U])(0xde1,tex)
   try:
    if family=='astc':
     fn=h.fn('glCompressedTexImage2D',None,[U,I,U,I,I,I,I,P]);block=(C.c_ubyte*16)(0xfc,0xfd,255,255,255,255,255,255,255,255,0,0,0,0,255,255)
     fn(0xde1,0,0x93b0,4,4,0,16,block);good=h.error();fn(0xde1,0,0x93b0,4,4,0,15,block);bad=h.error();facts=dict(format=0x93b0,block_bytes=16,size=[4,4],operation='upload_only');names=['glCompressedTexImage2D'];passed=good==0 and bad==0x501;detail=dict(upload_error=good,negative_size_error=bad,decode_pixels='NOT_RUN')
    else:
     names=['glFramebufferTexture2DMultisampleEXT','glRenderbufferStorageMultisampleEXT'];attach=proc(names[0],None,[U,U,U,U,I,I]);storage=proc(names[1],None,[U,I,U,I,I]);limit=I();h.fn('glGetIntegerv',None,[U,P])(0x8d57,C.byref(limit))
     if not attach or not storage or limit.value<1 or h.error()!=0:rows.append(dict(family=family,status='FAIL',reason='advertised MSRTT entrypoint or runtime limit query invalid'));continue
     samples=min(2,limit.value);h.fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,0x8058,4,4,0,0x1908,0x1401,None)
     h.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));h.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb);attach(0x8d40,0x8ce0,0xde1,tex,0,samples);complete=h.fn('glCheckFramebufferStatus',U,[U])(0x8d40)==0x8cd5
     h.fn('glClearColor',None,[F]*4)(.25,.5,.75,1);h.fn('glClear',None,[U])(0x4000);pixel=(C.c_ubyte*4)();h.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,1,1,0x1908,0x1401,pixel);good=h.error();attach(0x8d40,0x8ce0,0xde1,tex,0,-1);bad=h.error();passed=complete and good==0 and bad==0x501 and max(abs(a-b) for a,b in zip(pixel,[64,128,191,255]))<=1;facts=dict(samples=samples,max_samples=limit.value,rgba8_2d_complete=complete);detail=dict(pixel=list(pixel),gl_error=good,negative_samples_error=bad)
    decision=decide(family,gles=gles,gl_extensions=gl_ext,entrypoints=names,facts=facts,probe_pass=passed);rows.append(dict(family=family,status='PASS' if passed and decision['usable'] else 'FAIL',decision=decision,**detail))
   finally:
    h.fn('glBindFramebuffer',None,[U,U])(0x8d40,0)
    if fb.value:h.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(fb))
    h.fn('glDeleteTextures',None,[I,P])(1,C.byref(tex))
  rows.append(dict(family='protected',status='NOT_SUPPORTED',decision=decide('protected',egl=version,egl_extensions=egl_ext,entrypoints=['eglCreateContext'],facts={},probe_pass=None),scope='No protected-resource transfer attempted; no downgrade to unprotected copy'))
 finally:h.close()
 r=dict(status=result_status(rows),rows=rows,performance='NOT_MEASURED',not_implemented=['Multiview','Framebuffer Fetch/PLS','VRS','AHardwareBuffer/native image import'],source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),policy_sha256=hashlib.sha256((ROOT/'tools/coverage/priority_boundaries.py').read_bytes()).hexdigest());p=Path(output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']=='FAIL')
