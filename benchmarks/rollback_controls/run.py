#!/usr/bin/env python3
"""Bounded actual GLES texture/program rollback; never a performance acceptance."""
import argparse, ctypes as C, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'texture_access'))
import mechanisms as m
from quality_gate import observe

class RetainedHost(m.TextureHost):
 def __init__(self,config):
  self.retained=[];self.current={};super().__init__(config)
 def fn(self,name,restype,args,*extra):
  original=super().fn(name,restype,args,*extra)
  # Retain actual objects until the bounded transaction ends, instead of
  # TextureHost.execute's usual finally cleanup. Nothing is uploaded on restore.
  if name.startswith('glDelete') and name!='glDeleteShader':
   def retain(*values):
    value=values[0] if name=='glDeleteProgram' else C.cast(values[1],C.POINTER(m.U))[0]
    self.retained.append((name,int(value)))
   return retain
  if name in ('glUseProgram','glBindTexture','glBindFramebuffer','glBindVertexArray'):
   def record(*values):
    value=values[-1];value=value.value if hasattr(value,'value') else value
    if value:self.current[name]=int(value)
    return original(*values)
   return record
  return original
 def restore_read(self,snapshot):
  gl=self.fn
  gl('glBindFramebuffer',None,[m.U,m.U])(0x8d40,snapshot['glBindFramebuffer'])
  gl('glBindVertexArray',None,[m.U])(snapshot['glBindVertexArray'])
  gl('glActiveTexture',None,[m.U])(0x84c0)
  gl('glBindTexture',None,[m.U,m.U])(0xde1,snapshot['glBindTexture'])
  gl('glUseProgram',None,[m.U])(snapshot['glUseProgram'])
  gl('glViewport',None,[m.I]*4)(0,0,4,4)
  # Clear first so stale baseline framebuffer contents cannot pass rollback.
  gl('glClearColor',None,[C.c_float]*4)(.25,.25,.25,1)
  gl('glClear',None,[m.U])(0x4000)
  gl('glDrawArrays',None,[m.U,m.I,m.I])(4,0,3)
  pixels=(C.c_ubyte*64)();gl('glReadPixels',None,[m.I]*4+[m.U,m.U,m.P])(0,0,4,4,0x1908,0x1401,pixels)
  if self.error():raise RuntimeError('rollback GL error')
  # Actual GL state queries, not only Python snapshot assertions.
  checks={}
  for key,pname in [('glUseProgram',0x8b8d),('glBindTexture',0x8069),('glBindFramebuffer',0x8ca6),('glBindVertexArray',0x85b5)]:
   value=m.I();gl('glGetIntegerv',None,[m.U,m.P])(pname,C.byref(value));checks[key]=value.value==snapshot[key]
  return list(pixels),all(checks.values())
 def release(self):
  for name,value in self.retained:
   fn=super().fn(name,None,[m.U] if name=='glDeleteProgram' else [m.I,m.P])
   if name=='glDeleteProgram':fn(value)
   else:obj=m.U(value);fn(1,C.byref(obj))
  self.retained=[]

def decide(row,golden,missing=False):
 if missing:return 'INSUFFICIENT_EVIDENCE'
 observation=dict(row,status='EXECUTED',quality_budget=32)
 return observe(observation,golden)['optimization_status']

def run(config,output):
 h=RetainedHost(config);results=[]
 try:
  baseline=next(c for c in m.cases() if c['id']=='direct-upload-baseline')
  base=h.execute(baseline);snapshot=dict(h.current)
  if base['gl_error'] or base['quality']!='PASS':raise RuntimeError('invalid baseline')
  for label,mode,expr,missing,expected in [
   ('quality-rejection','lowres','texture(tex,gl_FragCoord.xy/4.0)',False,'REJECTED_BY_QUALITY'),
   ('missing-evidence','direct','texture(tex,gl_FragCoord.xy/4.0)',True,'INSUFFICIENT_EVIDENCE'),
   ('correct-unmeasured','pbo','texture(tex,gl_FragCoord.xy/4.0)',False,'INSUFFICIENT_EVIDENCE'),
   ('bad-program-output','direct','vec4(0.0,0.0,0.0,1.0)',False,'REJECTED_BY_QUALITY')]:
   c=dict(id=label,mode=mode,source=m.source(expr),golden=baseline['golden'],tolerance=32)
   row=h.execute(c);candidate=dict(h.current)
   if row['gl_error']:raise RuntimeError('candidate execution failure')
   decision=decide(row,baseline['golden'],missing)
   restored,state_match=h.restore_read(snapshot)
   ok=decision==expected and restored==base['pixels'] and state_match and candidate['glUseProgram']!=snapshot['glUseProgram'] and candidate['glBindTexture']!=snapshot['glBindTexture']
   results.append(dict(id=label,decision=decision,auto_accept=False,verified_improvement=False,candidate_pixels=row['pixels'],candidate_differs=row['pixels']!=base['pixels'],restored_pixels=restored,restored_byte_equal=restored==base['pixels'],queried_bindings_match=state_match,distinct_candidate_objects=True,status='HOST_PASS' if ok else 'FAIL'))
  result=dict(status='HOST_PASS' if all(r['status']=='HOST_PASS' for r in results) else 'FAIL',baseline_pixels=base['pixels'],transactions=results,performance_status='NOT_MEASURED',physical_hardware='BLOCKED_BY_HARDWARE',scope='One isolated GLES context; retained baseline texture/program/FBO/VAO, four candidates, explicit rebind + clear + redraw + readback. Not application-wide rollback, context-loss recovery, concurrency or GPU performance evidence.',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 finally:h.release();h.close()
 Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
