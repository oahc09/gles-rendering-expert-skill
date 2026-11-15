#!/usr/bin/env python3
import argparse,ctypes as C,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'texture_access'))
import mechanisms as m
from planner import Planner

def run(config,output):
 h=m.TextureHost(config);gl=h.fn;objects={};vao=m.U();program=0;rows=[];seen=set();reloads=0;hits=0
 assets={k:[v for y in range(4) for x in range(4) for v in ((i*43+x*17)%256,(y*51+i*31)%256,(x*11+y*13+i*23)%256,255)] for i,k in enumerate('ABCDE')}
 p=Planner({k:64 for k in assets},192,128)
 try:
  program,check=h.program({'shader.vert':m.VERTEX,'shader.frag':m.source('texture(tex,gl_FragCoord.xy/4.0)')})
  if not check['compile'] or not check['link']:raise RuntimeError('compile/link')
  gl('glUseProgram',None,[m.U])(program);gl('glGenVertexArrays',None,[m.I,m.P])(1,C.byref(vao));gl('glBindVertexArray',None,[m.U])(vao)
  gl('glViewport',None,[m.I]*4)(0,0,4,4)
  for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):gl('glDisable',None,[m.U])(cap)
  gl('glActiveTexture',None,[m.U])(0x84c0)
  gl('glUniform1i',None,[m.I,m.I])(gl('glGetUniformLocation',m.I,[m.U,C.c_char_p])(program,b'tex'),0)
  sequence=[['A','B'],['A'],['C'],['A','D'],['B'],['A','E'],['C','D'],['A'],['B','E'],['E']]*4
  for frame,requests in enumerate(sequence):
   plan=p.plan(requests);hits+=sum(k not in plan['upload'] for k in requests)
   for k in plan['evict']:
    obj=objects.pop(k);gl('glDeleteTextures',None,[m.I,m.P])(1,C.byref(obj))
   for k in plan['upload']:
    reloads+=k in seen;seen.add(k);obj=m.U();gl('glGenTextures',None,[m.I,m.P])(1,C.byref(obj));objects[k]=obj
    gl('glBindTexture',None,[m.U,m.U])(0xde1,obj)
    for pname,value in ((0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812f),(0x2803,0x812f)):gl('glTexParameteri',None,[m.U,m.U,m.I])(0xde1,pname,value)
    raw=(C.c_ubyte*64)(*assets[k]);gl('glTexImage2D',None,[m.U,m.I,m.I,m.I,m.I,m.I,m.U,m.U,m.P])(0xde1,0,0x8058,4,4,0,0x1908,0x1401,raw)
   if h.error():raise RuntimeError('upload failed; abort without planner commit')
   samples=[]
   for k in requests:
    gl('glBindTexture',None,[m.U,m.U])(0xde1,objects[k]);gl('glClearColor',None,[C.c_float]*4)(0,0,0,0);gl('glClear',None,[m.U])(0x4000)
    gl('glDrawArrays',None,[m.U,m.I,m.I])(4,0,3);pixels=(C.c_ubyte*64)();gl('glReadPixels',None,[m.I]*4+[m.U,m.U,m.P])(0,0,4,4,0x1908,0x1401,pixels)
    if h.error() or list(pixels)!=assets[k]:raise RuntimeError('readback quality failure')
    samples.append(dict(asset=k,pixels=list(pixels),cpu_oracle_equal=True))
   p.commit(plan)
   if set(objects)!=set(p.resident):raise RuntimeError('GPU object ledger mismatch')
   rows.append(dict(frame=frame,**plan,samples=samples))
  negatives=[]
  for request in [['A','B','C','D'],['UNKNOWN']]:
   before=(dict(p.resident),p.generation,set(objects))
   try:p.plan(request);raise RuntimeError('expected rejection')
   except ValueError:pass
   negatives.append(dict(request=request,rejected=True,state_unchanged=before==(dict(p.resident),p.generation,set(objects))))
  result=dict(status='HOST_PASS',frames=rows,negative_requests=negatives,reloads=reloads,cache_hits=hits,logical_capacity_bytes=192,per_frame_upload_budget_bytes=128,physical_resident_bytes=None,gpu_upload_stall_ms=None,gpu_time_ms=None,cpu_transcode_ms=None,performance_status='NOT_MEASURED',hardware='BLOCKED_BY_HARDWARE',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='40 synchronous GLES frames; LRU logical RGBA8 bytes only, actual deletion/upload/readback. Not physical residency, async streaming, compressed mip streaming or performance proof.')
 finally:
  for obj in objects.values():gl('glDeleteTextures',None,[m.I,m.P])(1,C.byref(obj))
  if vao.value:gl('glDeleteVertexArrays',None,[m.I,m.P])(1,C.byref(vao))
  if program:gl('glDeleteProgram',None,[m.U])(program)
  h.close()
 Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(run(json.loads(Path(a.config).read_text()),a.output)['status'])
