#!/usr/bin/env python3
"""Finite EXT timer semantics; never a software performance claim."""
import argparse,ctypes as C,hashlib,importlib.util,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('timer_host',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
U=d.U;I=d.I;P=d.P
ELAPSED=0x88bf;STAMP=0x8e28;BITS=0x8864;CURRENT=0x8865;AVAILABLE=0x8867;RESULT=0x8866;DISJOINT=0x8fbb
SIG={'glGenQueriesEXT':(None,[I,P]),'glDeleteQueriesEXT':(None,[I,P]),'glIsQueryEXT':(C.c_ubyte,[U]),'glBeginQueryEXT':(None,[U,U]),'glEndQueryEXT':(None,[U]),'glQueryCounterEXT':(None,[U,U]),'glGetQueryivEXT':(None,[U,U,P]),'glGetQueryObjectuivEXT':(None,[U,U,P]),'glGetQueryObjectui64vEXT':(None,[U,U,P])}
def valid_timing(before,after,bits,available):
 return before is False and after is False and type(bits) is int and bits==64 and available is True

def run(config,disabled=False):
 h=d.Host(config);f={};ids=(U*4)();generated=False;active=False
 r={'schema_version':1,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'execution_class':'SOFTWARE_HOST','physical_device':'NOT_RUN','performance_improvement':'NOT_MEASURED','raw_timestamps_recorded':False,'force_disabled':disabled,'status':'FAIL'}
 def clean():
  if h.error():raise RuntimeError('UNEXPECTED_GL_ERROR')
 def fallback(reason):
  row=h.execute({'id':'no-timer-safe-clear','kind':'fbo_pixels','color':[1,0,0,1]});r.update(reason=reason,fallback={'pixel_match':row['pixels']==[255,0,0,255]*16,'gl_error':row['harness_gl_error']});r['status']='SAFE_FALLBACK_PASS' if r['fallback']['pixel_match'] and not row['harness_gl_error'] else 'FAIL';return r
 def disjoint():
  value=I();h.fn('glGetIntegerv',None,[U,P])(DISJOINT,C.byref(value));clean();return bool(value.value)
 try:
  advertised='GL_EXT_disjoint_timer_query' in h.metadata['extensions'];r['extension_advertised']=advertised
  if disabled or not advertised:r['timer_entrypoint_calls']=0;return fallback('POLICY_DISABLED' if disabled else 'UNSUPPORTED_EXTENSION')
  for name,(ret,args) in SIG.items():
   ptr=h.fn('eglGetProcAddress',P,[C.c_char_p],True)(name.encode())
   if not ptr:raise RuntimeError('MISSING_EXT_ENTRYPOINT')
   f[name]=C.CFUNCTYPE(ret,*args)(ptr)
  r['entrypoints']=list(f);bits={}
  for name,target in [('elapsed',ELAPSED),('timestamp',STAMP)]:
   v=I();f['glGetQueryivEXT'](target,BITS,C.byref(v));clean();bits[name]=v.value
  r['counter_bits']=bits
  if not all(v==64 for v in bits.values()):return fallback('UNSUPPORTED_COUNTER_WIDTH_NEEDS_OVERFLOW_PROOF')
  before=disjoint();f['glGenQueriesEXT'](4,ids);generated=True;clean();r['generated_not_yet_objects']=all(not f['glIsQueryEXT'](q) for q in ids)
  f['glQueryCounterEXT'](ids[0],STAMP);f['glBeginQueryEXT'](ELAPSED,ids[1]);active=True;clean()
  cur=I();f['glGetQueryivEXT'](ELAPSED,CURRENT,C.byref(cur));r['active_query_matches']=cur.value==ids[1];clean()
  negatives=[];out=C.c_uint64()
  for name,func,args,expect in [('nested-active-target',f['glBeginQueryEXT'],(ELAPSED,ids[2]),0x502),('read-active-result',f['glGetQueryObjectui64vEXT'],(ids[1],RESULT,C.byref(out)),0x502),('counter-active-query',f['glQueryCounterEXT'],(ids[1],STAMP),0x502)]:
   func(*args);negatives.append({'case':name,'error':h.error(),'expected':expect})
  # Ordinary bounded clear/readback workload, not benchmark timing or draw speed.
  row=h.execute({'id':'timed-safe-clear','kind':'fbo_pixels','color':[1,0,0,1]});r['workload_pixel_match']=row['pixels']==[255,0,0,255]*16 and row['harness_gl_error']==0
  f['glEndQueryEXT'](ELAPSED);active=False;f['glQueryCounterEXT'](ids[3],STAMP);clean()
  for name,func,args,expect in [('end-inactive',f['glEndQueryEXT'],(ELAPSED,),0x502),('counter-wrong-target',f['glQueryCounterEXT'],(ids[2],ELAPSED),0x500),('zero-begin-id',f['glBeginQueryEXT'],(ELAPSED,0),0x502)]:
   func(*args);negatives.append({'case':name,'error':h.error(),'expected':expect})
  values=[];availability=[]
  h.fn('glFlush',None,[])();clean()
  for q in (ids[0],ids[1],ids[3]):
   a=U();f['glGetQueryObjectuivEXT'](q,AVAILABLE,C.byref(a));initial=bool(a.value)
   for attempt in range(100):
    if a.value:break
    time.sleep(.001);f['glGetQueryObjectuivEXT'](q,AVAILABLE,C.byref(a));clean()
   if not a.value:raise RuntimeError('BOUNDED_AVAILABILITY_TIMEOUT')
   v=C.c_uint64();f['glGetQueryObjectui64vEXT'](q,RESULT,C.byref(v));f['glGetQueryObjectuivEXT'](q,AVAILABLE,C.byref(a));clean();values.append(v.value);availability.append({'available_first_probe':initial,'available_at_result_read':True,'available_after_result':bool(a.value)})
  after=disjoint();r.update(disjoint_before=before,disjoint_after=after,availability=availability,negatives=negatives,objects_live=all(bool(f['glIsQueryEXT'](q)) for q in (ids[0],ids[1],ids[3])))
  r['elapsed_is_uint64_and_non_saturated']=0<=values[1]<(1<<64)-1
  accepted=r['elapsed_is_uint64_and_non_saturated'] and all(valid_timing(before,after,b,all(a['available_after_result'] for a in availability)) for b in bits.values());r['timing_validity']='API_DISJOINT_CHECKS_PASS_OVERFLOW_NOT_PROVEN' if accepted else 'REJECTED_DISJOINT_OR_UNKNOWN';r['timestamp_nondecreasing']=values[2]>=values[0] if accepted else None
  r['policy_simulations']={'injected_disjoint_rejected':not valid_timing(False,True,64,True),'unknown_disjoint_rejected':not valid_timing(None,False,64,True)}
  f['glDeleteQueriesEXT'](4,ids);generated=False;clean();r['deleted_not_objects']=all(not f['glIsQueryEXT'](q) for q in ids);clean()
  ok=r['generated_not_yet_objects'] and r['active_query_matches'] and r['objects_live'] and r['deleted_not_objects'] and r['workload_pixel_match'] and all(n['error']==n['expected'] for n in negatives) and all(a['available_after_result'] for a in availability) and (not accepted or r['timestamp_nondecreasing'])
  r['status']='HOST_PASS' if ok else 'FAIL';return r
 finally:
  if active:f['glEndQueryEXT'](ELAPSED)
  if generated:f['glDeleteQueriesEXT'](4,ids)
  h.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--disable-timer',action='store_true');a=p.parse_args()
 try:r=run(json.loads(a.config.read_text()),a.disable_timer)
 except Exception as e:r={'status':'FAIL','error_class':type(e).__name__}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(0 if r['status'] in ('HOST_PASS','SAFE_FALLBACK_PASS') else 1)
