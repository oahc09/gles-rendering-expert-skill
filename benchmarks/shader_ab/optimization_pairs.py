#!/usr/bin/env python3
"""Two finite source optimization A/B families; no speedup or general-fusion claims."""
import argparse,ctypes as C,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('optimization_diff',ROOT/'benchmarks/differential/run.py');diff=importlib.util.module_from_spec(s);s.loader.exec_module(diff)
U,I,P,F=diff.U,diff.I,diff.P,diff.F
SIZE=8
VERT='#version 310 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}'
PURE='vec4 pureValue(ivec2 p){vec2 uv=(vec2(p)+0.5)/8.0;return vec4(0.125+uv.x*0.5,0.125+uv.y*0.5,(uv.x+uv.y)*0.25+float(frame)*0.0625,1.0);}'
COMPUTE='#version 310 es\nprecision highp float;layout(local_size_x=8,local_size_y=8) in;layout(std430,binding=0) buffer Pixels{vec4 pixels[64];};uniform int frame;'+PURE+'void main(){ivec2 p=ivec2(gl_GlobalInvocationID.xy);pixels[p.y*8+p.x]=pureValue(p);}'

def texture_pixels(pattern):
 out=[]
 for y in range(SIZE):
  for x in range(SIZE):
   if pattern=='ramp':rgba=[x*32,y*32,(x+y)*16,255]
   elif pattern=='checker':rgba=[255 if (x+y)%2 else 0,64,0 if (x+y)%2 else 255,255]
   elif pattern=='edges':rgba=[255 if x>=4 else 0,255 if y>=4 else 0,128,255]
   elif pattern=='alpha':rgba=[x*32,255-y*32,96,(x+y)*16]
   else:raise ValueError('unknown pattern')
   out.extend(rgba)
 return out

def pure_golden(frame):
 return [v for y in range(SIZE) for x in range(SIZE) for v in (int((.125+(x+.5)/8*.5)*255+.5),int((.125+(y+.5)/8*.5)*255+.5),int((((x+.5)/8+(y+.5)/8)*.25+frame*.0625)*255+.5),255)]

def fragment(family,arm):
 prefix='#version 310 es\nprecision highp float;layout(location=0)out vec4 color;'
 if family=='sampling':
  body={'baseline':'vec4 a=texture(tex,uv);vec4 b=texture(tex,uv);color=(a+b)*0.5;','optimized':'color=texture(tex,uv);','negative':'color=texture(tex,vec2(1.0-uv.x,uv.y));'}[arm]
  return prefix+'uniform sampler2D tex;void main(){vec2 uv=gl_FragCoord.xy/8.0;'+body+'}'
 if family!='fusion':raise ValueError('family')
 if arm=='baseline':return prefix+'layout(std430,binding=0)readonly buffer Pixels{vec4 pixels[64];};void main(){ivec2 p=ivec2(gl_FragCoord.xy);color=pixels[p.y*8+p.x];}'
 return prefix+'uniform int frame;'+PURE+'void main(){color=pureValue(ivec2(gl_FragCoord.xy))'+('.bgra' if arm=='negative' else '')+';}'

def compare(actual,golden):
 if len(actual)!=SIZE*SIZE*4 or len(golden)!=len(actual) or any(type(x)is not int or not 0<=x<=255 for x in actual):return {'status':'INVALID','max_error':None}
 error=max(abs(x-y) for x,y in zip(actual,golden));return {'status':'PASS' if error<=1 else 'FAIL','max_error':error}

class Host(diff.Host):
 def draw(self,family,arm,input_):
  if not self.supports_compute:return dict(status='UNSUPPORTED_GLES31')
  fb=U();rb=U();vao=U();tex=U();buf=U();programs=[];compute_dispatched=False
  try:
   if family=='fusion' and arm=='baseline':
    self.fn('glGenBuffers',None,[I,P])(1,C.byref(buf));self.fn('glBindBuffer',None,[U,U])(0x90d2,buf);self.fn('glBufferData',None,[U,C.c_ssize_t,P,U])(0x90d2,SIZE*SIZE*16,None,0x88e8);self.fn('glBindBufferBase',None,[U,U,U])(0x90d2,0,buf)
    prog,c=self.program({'shader.comp':COMPUTE});programs.append(prog)
    if not c['compile'] or not c['link']:raise RuntimeError('compute compile/link')
    self.fn('glUseProgram',None,[U])(prog);loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,b'frame');self.fn('glUniform1i',None,[I,I])(loc,input_);self.fn('glDispatchCompute',None,[U,U,U])(1,1,1);self.fn('glMemoryBarrier',None,[U])(0x2000);compute_dispatched=True
   self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb);self.fn('glGenRenderbuffers',None,[I,P])(1,C.byref(rb));self.fn('glBindRenderbuffer',None,[U,U])(0x8d41,rb);self.fn('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,SIZE,SIZE);self.fn('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,rb)
   if self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO incomplete')
   for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):self.fn('glDisable',None,[U])(cap)
   self.fn('glViewport',None,[I]*4)(0,0,SIZE,SIZE);self.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));self.fn('glBindVertexArray',None,[U])(vao)
   frag=fragment(family,arm);prog,c=self.program({'shader.vert':VERT,'shader.frag':frag});programs.append(prog)
   if not c['compile'] or not c['link']:raise RuntimeError('draw compile/link')
   self.fn('glUseProgram',None,[U])(prog)
   if family=='sampling':
    self.fn('glGenTextures',None,[I,P])(1,C.byref(tex));self.fn('glActiveTexture',None,[U])(0x84c0);self.fn('glBindTexture',None,[U,U])(0xde1,tex)
    for key,value in ((0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812f),(0x2803,0x812f)):self.fn('glTexParameteri',None,[U,U,I])(0xde1,key,value)
    pixels=(C.c_ubyte*256)(*texture_pixels(input_));self.fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,0x8058,SIZE,SIZE,0,0x1908,0x1401,pixels)
    loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,b'tex');self.fn('glUniform1i',None,[I,I])(loc,0)
   elif arm!='baseline':
    loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,b'frame');self.fn('glUniform1i',None,[I,I])(loc,input_)
   self.fn('glDrawArrays',None,[U,I,I])(4,0,3);pixels=(C.c_ubyte*256)();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,SIZE,SIZE,0x1908,0x1401,pixels)
   if self.error():raise RuntimeError('GL operation error')
   return dict(status='EXECUTED',pixels=list(pixels),fragment_sha256=hashlib.sha256(frag.encode()).hexdigest(),compute_dispatched=compute_dispatched,ssbo_intermediate_bytes=1024 if compute_dispatched else 0,barrier='GL_SHADER_STORAGE_BARRIER_BIT' if compute_dispatched else 'NOT_REQUIRED_NO_SHARED_WRITE')
  finally:
   self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindVertexArray',None,[U])(0)
   for prog in programs:self.fn('glDeleteProgram',None,[U])(prog)
   for obj,fn in ((fb,'glDeleteFramebuffers'),(rb,'glDeleteRenderbuffers'),(vao,'glDeleteVertexArrays'),(tex,'glDeleteTextures'),(buf,'glDeleteBuffers')):
    if obj.value:self.fn(fn,None,[I,P])(1,C.byref(obj))

def run(config,output):
 h=Host(config);rows=[]
 try:
  for family,inputs in [('sampling',('ramp','checker','edges','alpha')),('fusion',(0,1,2,3))]:
   for input_ in inputs:
    gold=texture_pixels(input_) if family=='sampling' else pure_golden(input_)
    draws={arm:h.draw(family,arm,input_) for arm in ('baseline','optimized','negative')}
    evaluations={arm:compare(row.get('pixels',[]),gold) for arm,row in draws.items()}
    paired=compare(draws['baseline'].get('pixels',[]),draws['optimized'].get('pixels',[]))
    rows.append(dict(family=family,input=input_,cpu_golden=gold,draws=draws,evaluations=evaluations,paired=paired,status='PASS' if all(x['status']=='EXECUTED' for x in draws.values()) and evaluations['baseline']['status']=='PASS' and evaluations['optimized']['status']=='PASS' and evaluations['negative']['status']=='FAIL' and paired['status']=='PASS' else 'FAIL'))
 finally:h.close()
 report=dict(status='HOST_PASS' if all(x['status']=='PASS' for x in rows) else 'FAIL',scope='Repeated identical sampling CSE; pure per-pixel compute intermediates versus direct fragment evaluation, not general fusion',dimensions=[SIZE,SIZE],format='RGBA8 bottom-up',source_hashes={'vertex':hashlib.sha256(VERT.encode()).hexdigest(),'compute':hashlib.sha256(COMPUTE.encode()).hexdigest()},performance='NOT_MEASURED',physical_gpu='NOT_RUN',cases=rows)
 dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--config',required=True);q.add_argument('--output',required=True);a=q.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
