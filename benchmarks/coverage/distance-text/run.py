#!/usr/bin/env python3
"""Authored distance-atlas coverage; no font/generator conformance claim."""
import argparse,ctypes as C,hashlib,importlib.util,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('distance_host',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
U,I,P,F=d.U,d.I,d.P,d.F
VERT='#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}'
def quant(x):return int(math.floor(max(0,min(1,x))*255+.5))
def atlas(kind):
 out=[]
 for y in range(8):
  for x in range(8):
   dx=(2.3-abs(x-3.5))/4;dy=(2.3-abs(y-3.5))/4
   # Synthetic perpendicular edge distances, not an msdfgen output.
   sd=min(dx,dy) if min(dx,dy)>=0 else -math.hypot(min(dx,0),min(dy,0))
   channels=[dx,dy,min(dx,dy)] if kind=='msdf' else [sd]*3
   out.extend([quant(.5+c) for c in channels]+[255])
 return out

def sample(data,u,v):
 x=u*8-.5;y=v*8-.5;ix=math.floor(x);iy=math.floor(y);fx=x-ix;fy=y-iy
 return [sum(data[(max(0,min(7,iy+j))*8+max(0,min(7,ix+i)))*4+c]/255*(fx if i else 1-fx)*(fy if j else 1-fy) for j in range(2) for i in range(2)) for c in range(3)]
def golden(size,kind):
 if size not in (16,32) or kind not in ('sdf','msdf'):raise ValueError('fixed domain')
 data=atlas(kind);out=[];width=1/size
 for y in range(size):
  for x in range(size):
   rgb=sample(data,(x+.5)/size,(y+.5)/size);distance=sorted(rgb)[1] if kind=='msdf' else rgb[0]
   t=max(0,min(1,(distance-(.5-width))/(2*width)));coverage=t*t*(3-2*t)
   out.extend([quant(coverage)]*3+[255])
 return out

def fragment(size,kind,arm):
 select='s.r' if kind=='sdf' or arm=='wrong_channel' else 'max(min(s.r,s.g),min(max(s.r,s.g),s.b))'
 expression='s.r' if arm=='alpha_fallback' else f'smoothstep({.5-1/size:.10f},{.5+1/size:.10f},{select})'
 if arm=='wrong_threshold':expression=f'smoothstep(0.65,0.75,{select})'
 if arm=='wrong_outline':expression=f'1.0-smoothstep(0.03,0.15,abs({select}-0.5))'
 return f'#version 300 es\nprecision highp float;uniform sampler2D atlas;out vec4 color;void main(){{vec3 s=texture(atlas,gl_FragCoord.xy/{size}.0).rgb;float a={expression};color=vec4(vec3(a),1);}}'
class Host(d.Host):
 def draw(self,size,kind,arm):
  if size not in (16,32) or kind not in ('sdf','msdf') or arm not in ('correct','alpha_fallback','wrong_channel','wrong_threshold','wrong_outline'):raise ValueError('fixed case')
  g=self.fn;tex=U();fb=U();rb=U();vao=U();p=0
  try:
   src=fragment(size,kind,arm);p,ok=self.program({'shader.vert':VERT,'shader.frag':src})
   if not ok['compile'] or not ok['link']:raise RuntimeError('shader')
   g('glUseProgram',None,[U])(p);g('glGenVertexArrays',None,[I,P])(1,C.byref(vao));g('glBindVertexArray',None,[U])(vao)
   data=golden(size,kind) if arm=='alpha_fallback' else atlas(kind);n=size if arm=='alpha_fallback' else 8
   g('glActiveTexture',None,[U])(0x84c0);g('glGenTextures',None,[I,P])(1,C.byref(tex));g('glBindTexture',None,[U,U])(0xde1,tex)
   for param,value in [(0x2801,0x2600 if arm=='alpha_fallback' else 0x2601),(0x2800,0x2600 if arm=='alpha_fallback' else 0x2601),(0x2802,0x812f),(0x2803,0x812f)]:g('glTexParameteri',None,[U,U,I])(0xde1,param,value)
   raw=(C.c_ubyte*len(data))(*data);g('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,0x8058,n,n,0,0x1908,0x1401,raw)
   loc=g('glGetUniformLocation',I,[U,C.c_char_p])(p,b'atlas');g('glUniform1i',None,[I,I])(loc,0)
   g('glGenFramebuffers',None,[I,P])(1,C.byref(fb));g('glBindFramebuffer',None,[U,U])(0x8d40,fb);g('glGenRenderbuffers',None,[I,P])(1,C.byref(rb));g('glBindRenderbuffer',None,[U,U])(0x8d41,rb);g('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,size,size);g('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,rb)
   if g('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO')
   for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):g('glDisable',None,[U])(cap)
   g('glViewport',None,[I]*4)(0,0,size,size);g('glDrawArrays',None,[U,I,I])(4,0,3)
   pixels=(C.c_ubyte*(size*size*4))();g('glReadPixels',None,[I]*4+[U,U,P])(0,0,size,size,0x1908,0x1401,pixels)
   if self.error():raise RuntimeError('GL error')
   image=list(pixels);expected=golden(size,kind);err=max(abs(a-b) for a,b in zip(image,expected))
   return dict(size=size,kind=kind,arm=arm,pixels=image,max_error=err,quality='PASS' if err<=3 else 'FAIL',atlas_sha256=hashlib.sha256(bytes(data)).hexdigest(),fragment_sha256=hashlib.sha256(src.encode()).hexdigest())
  finally:
   g('glUseProgram',None,[U])(0);g('glBindFramebuffer',None,[U,U])(0x8d40,0);g('glBindVertexArray',None,[U])(0)
   for obj,name in [(tex,'glDeleteTextures'),(vao,'glDeleteVertexArrays'),(fb,'glDeleteFramebuffers'),(rb,'glDeleteRenderbuffers')]:
    if obj.value:g(name,None,[I,P])(1,C.byref(obj))
   if p:g('glDeleteProgram',None,[U])(p)
def run(config,output):
 h=Host(config)
 try:rows=[h.draw(n,k,a) for n in (16,32) for k in ('sdf','msdf') for a in ('correct','alpha_fallback','wrong_threshold','wrong_outline','wrong_channel') if a!='wrong_channel' or k=='msdf']
 finally:h.close()
 decisions=[]
 for n in (16,32):
  for k in ('sdf','msdf'):
   candidate=next(r for r in rows if r['size']==n and r['kind']==k and r['arm']=='correct')
   fallback=next(r for r in rows if r['size']==n and r['kind']==k and r['arm']=='alpha_fallback')
   decisions.append(dict(size=n,kind=k,selected='distance' if candidate['quality']=='PASS' else 'alpha_fallback' if fallback['quality']=='PASS' else 'UNAVAILABLE',candidate_quality=candidate['quality'],fallback_exact=fallback['max_error']==0))
 passed=all(r['quality']=='FAIL' for r in rows if r['arm'].startswith('wrong_')) and all(x['fallback_exact'] and x['selected']!='UNAVAILABLE' for x in decisions) and all(r['quality']=='PASS' for r in rows if r['kind']=='msdf' and r['arm']=='correct')
 result=dict(status='HOST_PASS' if passed else 'FAIL',draws=len(rows),decisions=decisions,pixel_budget=3,rows=rows,vertex_sha256=hashlib.sha256(VERT.encode()).hexdigest(),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),performance='NOT_MEASURED',physical_device='NOT_RUN',scope='Authored rectangle distance decoder, two sizes, linear RGBA8 atlas. Not font layout or arbitrary MSDF generator quality.')
 out=Path(output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(json.loads(a.config.read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
