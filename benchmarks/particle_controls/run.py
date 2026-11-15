#!/usr/bin/env python3
"""Bounded compute→SSBO barrier→vertex-consumer particle controls, no missing-barrier UB."""
import argparse,ctypes as C,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('particle_diff',ROOT/'benchmarks/differential/run.py');diff=importlib.util.module_from_spec(s);s.loader.exec_module(diff)
U,I,P,F=diff.U,diff.I,diff.P,diff.F
SIZE=32
COMPUTE='''#version 310 es
precision highp float;
layout(local_size_x=4) in;
layout(std430,binding=0) buffer Particles { vec4 particle[4]; };
uniform int frame;
void main(){uint i=gl_GlobalInvocationID.x;if(i>=4u)return;
 particle[i]=vec4(5.5+float(i%2u)*14.0+float(frame)*2.0,5.5+float(i/2u)*14.0+float(frame),float(i),1.0);}
'''
VERTEX='''#version 310 es
precision highp float;
layout(std430,binding=0) readonly buffer Particles {vec4 particle[4];};
uniform int badIndex;flat out vec4 tint;
void main(){int i=badIndex==1?0:gl_VertexID;vec4 p=particle[i];
 gl_Position=vec4(p.xy/32.0*2.0-1.0,0,1);gl_PointSize=3.0;
 vec4 palette[4]=vec4[4](vec4(1,0,0,1),vec4(0,1,0,1),vec4(0,0,1,1),vec4(1,1,0,1));tint=palette[int(p.z)];}
'''
FRAGMENT='''#version 310 es
precision highp float;flat in vec4 tint;layout(location=0) out vec4 color;
void main(){color=tint;}
'''
BARRIER=0x2000|0x200 # SHADER_STORAGE + BUFFER_UPDATE for later CPU mapping

def positions(frame):return [v for i in range(4) for v in (5.5+(i%2)*14+frame*2,5.5+(i//2)*14+frame,float(i),1.)]
def golden(frame):
 out=[0]*(SIZE*SIZE*4);palette=[[255,0,0,255],[0,255,0,255],[0,0,255,255],[255,255,0,255]]
 for i in range(4):
  x=int(5.5+(i%2)*14+frame*2);y=int(5.5+(i//2)*14+frame)
  for dy in (-1,0,1):
   for dx in (-1,0,1):
    index=((y+dy)*SIZE+x+dx)*4;out[index:index+4]=palette[i]
 return out

def compare_image(actual,expected):
 if len(actual)!=SIZE*SIZE*4 or len(expected)!=len(actual) or any(type(v)is not int or not 0<=v<=255 for v in actual):return dict(status='INVALID',mismatching_channels=None)
 n=sum(a!=b for a,b in zip(actual,expected));return dict(status='PASS' if n==0 else 'FAIL',mismatching_channels=n)

class Host(diff.Host):
 def execute(self,frame,arm):
  if not self.supports_compute:return dict(status='UNSUPPORTED',reason='GLES 3.1 compute unavailable')
  limit=I();self.fn('glGetIntegerv',None,[U,P])(0x90d6,C.byref(limit)) # MAX_VERTEX_SHADER_STORAGE_BLOCKS
  if limit.value<1:return dict(status='UNSUPPORTED',reason='vertex SSBO consumer unavailable')
  ssbo=U();fb=U();rb=U();vao=U();programs=[]
  try:
   compute,c=self.program({'shader.comp':COMPUTE});programs.append(compute);draw,d=self.program({'shader.vert':VERTEX,'shader.frag':FRAGMENT});programs.append(draw)
   if not all(x['compile'] and x['link'] for x in (c,d)):raise RuntimeError('compile/link failed')
   self.fn('glGenBuffers',None,[I,P])(1,C.byref(ssbo));self.fn('glBindBuffer',None,[U,U])(0x90d2,ssbo);self.fn('glBufferData',None,[U,C.c_ssize_t,P,U])(0x90d2,64,(F*16)(*[0]*16),0x88e8);self.fn('glBindBufferBase',None,[U,U,U])(0x90d2,0,ssbo)
   self.fn('glUseProgram',None,[U])(compute);loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(compute,b'frame');self.fn('glUniform1i',None,[I,I])(loc,frame+1 if arm=='bad-frame' else frame)
   self.fn('glDispatchCompute',None,[U,U,U])(1,1,1)
   # Consumer-specific visibility, never deliberately omit or weaken this barrier.
   self.fn('glMemoryBarrier',None,[U])(BARRIER)
   self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb);self.fn('glGenRenderbuffers',None,[I,P])(1,C.byref(rb));self.fn('glBindRenderbuffer',None,[U,U])(0x8d41,rb);self.fn('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,SIZE,SIZE);self.fn('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,rb)
   if self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO incomplete')
   for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):self.fn('glDisable',None,[U])(cap)
   self.fn('glViewport',None,[I]*4)(0,0,SIZE,SIZE);self.fn('glClearColor',None,[F]*4)(0,0,0,0);self.fn('glClear',None,[U])(0x4000);self.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));self.fn('glBindVertexArray',None,[U])(vao);self.fn('glUseProgram',None,[U])(draw)
   loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(draw,b'badIndex');self.fn('glUniform1i',None,[I,I])(loc,1 if arm=='bad-index' else 0);self.fn('glDrawArrays',None,[U,I,I])(0,0,4)
   pixels=(C.c_ubyte*(SIZE*SIZE*4))();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,SIZE,SIZE,0x1908,0x1401,pixels)
   self.fn('glBindBuffer',None,[U,U])(0x90d2,ssbo);ptr=self.fn('glMapBufferRange',P,[U,C.c_ssize_t,C.c_ssize_t,U])(0x90d2,0,64,1)
   if not ptr:raise RuntimeError('SSBO map failed')
   buffer=list(C.cast(ptr,C.POINTER(F*16)).contents);self.fn('glUnmapBuffer',U,[U])(0x90d2)
   if self.error():raise RuntimeError('GL operation failed')
   pix=list(pixels);return dict(status='EXECUTED',frame=frame,arm=arm,expected='PASS' if arm=='correct' else 'FAIL',image=compare_image(pix,golden(frame)),pixels=pix,ssbo=buffer,ssbo_matches_requested_frame=buffer==positions(frame),barrier_bits=['GL_SHADER_STORAGE_BARRIER_BIT','GL_BUFFER_UPDATE_BARRIER_BIT'],dispatch_groups=[1,1,1],draw_vertices=4)
  finally:
   self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindVertexArray',None,[U])(0)
   for prog in programs:self.fn('glDeleteProgram',None,[U])(prog)
   for obj,fn in ((ssbo,'glDeleteBuffers'),(fb,'glDeleteFramebuffers'),(rb,'glDeleteRenderbuffers'),(vao,'glDeleteVertexArrays')):
    if obj.value:self.fn(fn,None,[I,P])(1,C.byref(obj))

def run(config,output):
 h=Host(config)
 try:rows=[h.execute(frame,arm) for frame in (0,1,2) for arm in ('correct','bad-frame','bad-index')]
 finally:h.close()
 ok=all(r['status']=='EXECUTED' and r['image']['status']==r['expected'] and r['ssbo_matches_requested_frame']==(r['arm']!='bad-frame') for r in rows)
 report=dict(status='HOST_PASS' if ok else 'FAIL',scope='4 compute-updated particles, vertex SSBO read, required barriers, 3 fixed frames; no missing-barrier UB execution',dimensions=[SIZE,SIZE],format='bottom-up RGBA8',source_hashes={k:hashlib.sha256(v.encode()).hexdigest() for k,v in {'compute':COMPUTE,'vertex':VERTEX,'fragment':FRAGMENT}.items()},performance='NOT_MEASURED',physical_gpu='NOT_RUN',rows=rows,cpu_goldens={str(f):golden(f) for f in (0,1,2)})
 dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(report,separators=(',',':'))+'\n');return report
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--config',required=True);q.add_argument('--output',required=True);a=q.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
