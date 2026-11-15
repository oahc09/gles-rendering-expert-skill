#!/usr/bin/env python3
"""Finite multi-SSBO sequential rebind control; not an upstream bug reproduction."""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
from pathlib import Path
SPEC=importlib.util.spec_from_file_location('rebind_diff',Path(__file__).resolve().parents[1]/'differential/run.py')
d=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(d)
U,I,P,F=d.U,d.I,d.P,d.F
COMPUTE='''#version 310 es
precision highp float;
layout(local_size_x=1) in;
layout(std430,binding=0) buffer Data {vec4 data;};
uniform vec4 value;
void main(){data=value;}
'''
PRIME='''#version 310 es
precision highp float;
layout(local_size_x=1) in;
layout(std430,binding=0) readonly buffer InputData {vec4 data;};
layout(std430,binding=1) buffer OutputData {vec4 result;};
void main(){result=data*2.0;}
'''
FIRST=[[1.5+i,3.75+i,5.0+i,12.125+i] for i in range(4)]
SECOND=[[16.0+i,32.0+i,64.0+i,128.0+i] for i in range(4)]

class RebindHost(d.Host):
 def control(self,wrong_binding=False):
  if not self.supports_compute:return {'status':'SKIP_UNSUPPORTED'}
  while self.error():pass
  buffers=(U*5)();program=prime=0
  try:
   self.fn('glGenBuffers',None,[I,P])(5,buffers)
   for buf in buffers:
    self.fn('glBindBuffer',None,[U,U])(0x90d2,buf)
    self.fn('glBufferData',None,[U,C.c_ssize_t,P,U])(0x90d2,16,(F*4)(2,2,2,2),0x88e4)
   program,compile_result=self.program({'shader.comp':COMPUTE})
   prime,prime_result=self.program({'shader.comp':PRIME})
   if not all(x['compile'] and x['link'] for x in (compile_result,prime_result)):
    return {'status':'COMPILE_FAILED','compile':compile_result,'prime_compile':prime_result}
   # Give buffer 0 a prior read history unlike buffers 1..3. This does NOT
   # establish ANGLE's internal VkEvent vs pipeline-barrier tracking histories.
   self.fn('glBindBufferBase',None,[U,U,U])(0x90d2,0,buffers[0])
   self.fn('glBindBufferBase',None,[U,U,U])(0x90d2,1,buffers[4])
   self.fn('glUseProgram',None,[U])(prime);self.fn('glDispatchCompute',None,[U,U,U])(1,1,1)
   self.fn('glMemoryBarrier',None,[U])(0x2000|0x200)
   prime_value=self.read_buffer(buffers[4])
   self.fn('glUseProgram',None,[U])(program)
   loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(program,b'value')
   for index,values in enumerate(FIRST):
    self.fn('glBindBufferBase',None,[U,U,U])(0x90d2,0,buffers[index])
    self.fn('glUniform4f',None,[I,F,F,F,F])(loc,*values)
    self.fn('glDispatchCompute',None,[U,U,U])(1,1,1)
   # Subsequent shader storage overwrites consume prior shader writes.
   self.fn('glMemoryBarrier',None,[U])(0x2000)
   binding_order=[]
   for index,values in enumerate(SECOND):
    target=0 if wrong_binding and index==3 else index
    binding_order.append(target)
    self.fn('glBindBufferBase',None,[U,U,U])(0x90d2,0,buffers[target])
    self.fn('glUniform4f',None,[I,F,F,F,F])(loc,*values)
    self.fn('glDispatchCompute',None,[U,U,U])(1,1,1)
    if wrong_binding and index==0:
     # Negative later writes buffer 0 again: keep its WAW ordered, not UB.
     self.fn('glMemoryBarrier',None,[U])(0x2000)
   # Host mapping is buffer-update access, not a shader-storage read.
   self.fn('glMemoryBarrier',None,[U])(0x200)
   values=[self.read_buffer(buffers[i]) for i in range(4)]
   error=self.error()
   equal=values==SECOND and prime_value==[4.0]*4
   return {'status':'EXECUTED','variant':'wrong_binding' if wrong_binding else 'correct_binding','compile':compile_result,'prime_compile':prime_result,'prime_readback':prime_value,'readback':values,'expected':SECOND,'binding_order':binding_order,'numeric_quality':'PASS' if equal else 'FAIL','harness_gl_error':error,'barriers':['GL_SHADER_STORAGE_BARRIER_BIT before storage overwrite','GL_BUFFER_UPDATE_BARRIER_BIT before map readback']}
  finally:
   self.fn('glUseProgram',None,[U])(0)
   self.fn('glBindBufferBase',None,[U,U,U])(0x90d2,0,0);self.fn('glBindBufferBase',None,[U,U,U])(0x90d2,1,0)
   for p in (program,prime):
    if p:self.fn('glDeleteProgram',None,[U])(p)
   self.fn('glDeleteBuffers',None,[I,P])(5,buffers)
 def read_buffer(self,buf):
  self.fn('glBindBuffer',None,[U,U])(0x90d2,buf)
  ptr=self.fn('glMapBufferRange',P,[U,C.c_ssize_t,C.c_ssize_t,U])(0x90d2,0,16,1)
  if not ptr:raise RuntimeError('Map failed')
  values=list(C.cast(ptr,C.POINTER(F*4)).contents)
  if not self.fn('glUnmapBuffer',U,[U])(0x90d2):raise RuntimeError('Unmap failed')
  return values

def run(config):
 h=RebindHost(config)
 try:rows=[h.control(False),h.control(True)]
 finally:h.close()
 ok=all(r.get('status')=='EXECUTED' and r.get('harness_gl_error')==0 for r in rows) and [r.get('numeric_quality') for r in rows]==['PASS','FAIL']
 return {'status':'HOST_PASS' if ok else 'PARTIAL_OR_FAIL','cases':rows,'source_sha256':{n:hashlib.sha256(s.encode()).hexdigest() for n,s in [('compute',COMPUTE),('prime',PRIME)]},'scope':'Four SSBOs, prior read on buffer zero, two write rounds and host map readback','mixed_history':'API-level prior read differs; internal VkEvent/pipeline history NOT_VERIFIED','upstream_bug_reproduced':False,'missing_barrier':'NOT_EXECUTED_UNDEFINED_BEHAVIOR','performance':'NOT_MEASURED'}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 result=run(json.loads(a.config.read_text()));a.output.write_text(json.dumps(result,indent=2)+'\n');print(result['status']);raise SystemExit(result['status']!='HOST_PASS')
