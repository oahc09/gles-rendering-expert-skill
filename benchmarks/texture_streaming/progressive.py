#!/usr/bin/env python3
"""Bounded explicit mip refinement; logical costs, fixed quality gate."""
import argparse,ctypes as C,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'texture_access'))
import mechanisms as m

class Refinement:
 def __init__(self,capacity=84,budget=64):
  if type(capacity)!=int or type(budget)!=int or min(capacity,budget)<=0:raise ValueError('invalid limits')
  self.capacity=capacity;self.budget=budget;self.loaded=set();self.active=None
 def propose(self,level):
  if type(level)!=int or level not in (0,1,2):raise ValueError('invalid mip')
  cost=4*(4>>level)**2
  if level not in self.loaded and cost>self.budget:raise ValueError('upload budget')
  if level not in self.loaded and sum(4*(4>>k)**2 for k in self.loaded)+cost>self.capacity:raise ValueError('capacity')
  return cost if level not in self.loaded else 0
 def observe(self,level,pixels,golden):
  self.propose(level)
  if len(pixels)!=64 or len(golden)!=64 or any(type(v)!=int or not 0<=v<=255 for v in pixels+golden):raise ValueError('invalid image')
  self.loaded.add(level)
  error=max(abs(a-b) for a,b in zip(pixels,golden))
  # Fixed maximum channel error, not adapted to the observed result.
  accepted=error<=32
  if accepted:self.active=level
  return dict(level=level,max_error=error,quality='PASS' if accepted else 'FAIL',selected=accepted,active_level=self.active,optimization_status='INSUFFICIENT_EVIDENCE' if accepted else 'REJECTED_BY_QUALITY')

def run(config,output):
 h=m.TextureHost(config);g=h.fn;tex=m.U();vao=m.U();program=0;r=Refinement();rows=[]
 golden=[v for y in range(4) for x in range(4) for v in (x*60,y*60,0,255)]
 data={2:[90,90,0,255],1:[v for y in range(2) for x in range(2) for v in (30+x*120,30+y*120,0,255)],0:golden}
 try:
  program,c=h.program({'shader.vert':m.VERTEX,'shader.frag':m.source('texture(tex,gl_FragCoord.xy/4.0)')})
  if not c['compile'] or not c['link']:raise RuntimeError('compile/link')
  g('glUseProgram',None,[m.U])(program);g('glGenVertexArrays',None,[m.I,m.P])(1,C.byref(vao));g('glBindVertexArray',None,[m.U])(vao)
  g('glGenTextures',None,[m.I,m.P])(1,C.byref(tex));g('glActiveTexture',None,[m.U])(0x84c0);g('glBindTexture',None,[m.U,m.U])(0xde1,tex)
  g('glUniform1i',None,[m.I,m.I])(g('glGetUniformLocation',m.I,[m.U,C.c_char_p])(program,b'tex'),0)
  for p,v in ((0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812f),(0x2803,0x812f)):g('glTexParameteri',None,[m.U,m.U,m.I])(0xde1,p,v)
  for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):g('glDisable',None,[m.U])(cap)
  g('glViewport',None,[m.I]*4)(0,0,4,4)
  def draw(level):
   for pname in (0x813c,0x813d):g('glTexParameteri',None,[m.U,m.U,m.I])(0xde1,pname,level)
   g('glClearColor',None,[C.c_float]*4)(0,0,0,0);g('glClear',None,[m.U])(0x4000);g('glDrawArrays',None,[m.U,m.I,m.I])(4,0,3)
   out=(C.c_ubyte*64)();g('glReadPixels',None,[m.I]*4+[m.U,m.U,m.P])(0,0,4,4,0x1908,0x1401,out)
   if h.error():raise RuntimeError('GL error')
   return list(out)
  for level in [2,1,0,1,0]:
   cost=r.propose(level)
   if cost:
    raw=(C.c_ubyte*len(data[level]))(*data[level]);g('glTexImage2D',None,[m.U,m.I,m.I,m.I,m.I,m.I,m.U,m.U,m.P])(0xde1,level,0x8058,4>>level,4>>level,0,0x1908,0x1401,raw)
   pixels=draw(level);row=r.observe(level,pixels,golden);row.update(upload_bytes=cost,logical_loaded_bytes=sum(4*(4>>k)**2 for k in r.loaded),pixels=pixels)
   rows.append(row)
  # Inject wrong contents into the coarse candidate only; selected mip0 is retained.
  raw=(C.c_ubyte*4)(0,0,0,255);g('glTexImage2D',None,[m.U,m.I,m.I,m.I,m.I,m.I,m.U,m.U,m.P])(0xde1,2,0x8058,1,1,0,0x1908,0x1401,raw)
  rejected=r.observe(2,draw(2),golden);restored=draw(r.active)
  if [x['max_error'] for x in rows]!=[90,30,0,30,0] or rejected['selected'] or restored!=golden:raise RuntimeError('quality/restore mismatch')
  result=dict(status='HOST_PASS',frames=rows,rejected_candidate=rejected,restored_pixels=restored,restored_exact=True,logical_capacity_bytes=84,upload_budget_bytes=64,physical_resident_bytes=None,gpu_stall_ms=None,performance_status='NOT_MEASURED',scope='Explicit synchronous 4x4/2x2/1x1 mip uploads; fixed max-channel budget32; failed coarse candidates are not presented; no async/hardware performance claim.')
 finally:
  if tex.value:g('glDeleteTextures',None,[m.I,m.P])(1,C.byref(tex))
  if vao.value:g('glDeleteVertexArrays',None,[m.I,m.P])(1,C.byref(vao))
  if program:g('glDeleteProgram',None,[m.U])(program)
  h.close()
 Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(run(json.loads(Path(a.config).read_text()),a.output)['status'])
