#!/usr/bin/env python3
"""Actual sorted-OVER verification and crossing failure, separate from failed OIT."""
import argparse,ctypes as C,hashlib,importlib.util,json,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import exact_policy
s=importlib.util.spec_from_file_location('oit_existing',HERE/'run.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
d=old.d;U=d.U;I=d.I;F=d.F;P=d.P
COLORS=[[1,0,0,.5],[0,0,1,.5]]
FRAG='#version 300 es\nprecision highp float;uniform vec4 layer;uniform vec2 depthPlane;out vec4 color;void main(){gl_FragDepth=depthPlane.x+depthPlane.y*gl_FragCoord.x;color=layer;}'
COPY='#version 300 es\nprecision highp float;uniform sampler2D source;out vec4 color;void main(){color=texelFetch(source,ivec2(gl_FragCoord.xy),0);}'
SCENES=[('constant_nonintersecting',[(.2,0),(.8,0)]),('sloped_nonintersecting',[(.1,.04),(.6,.04)]),('crossing',[(.1,.2),(.9,-.2)]),('ambiguous_equal',[(.5,0),(.5,0)])]
def layers(planes):return [{'id':str(i),'rgba':COLORS[i],'depths':[a+b*(x+.5) for y in range(4) for x in range(4)]} for i,(a,b) in enumerate(planes)]
def golden(ls):
 out=[]
 for pixel in range(16):
  rgba=[0.]*4
  for l in sorted(ls,key=lambda l:l['depths'][pixel],reverse=True):
   c=l['rgba'];rgba=[old.half(c[i]*c[3]+rgba[i]*(1-c[3])) for i in range(3)]+[old.half(c[3]+rgba[3]*(1-c[3]))]
  out.extend(old.q(x) for x in rgba)
 return out

def run(config):
 h=d.Host(config);tex=[];fb=[];programs=[];vao=U();r={'schema_version':1,'status':'FAIL','execution_class':'SOFTWARE_HOST','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256((HERE/'exact_policy.py').read_bytes()).hexdigest(),'physical_device':'NOT_RUN','performance':'NOT_MEASURED','scenes':[]}
 def check():
  if h.error():raise RuntimeError('GL_ERROR')
 def target(fmt):
  t=U();f=U();h.fn('glGenTextures',None,[I,P])(1,C.byref(t));tex.append(t);h.fn('glBindTexture',None,[U,U])(0xde1,t);h.fn('glTexStorage2D',None,[U,I,U,I,I])(0xde1,1,fmt,4,4)
  for pn in (0x2800,0x2801):h.fn('glTexParameteri',None,[U,U,I])(0xde1,pn,0x2600)
  h.fn('glGenFramebuffers',None,[I,P])(1,C.byref(f));fb.append(f);h.fn('glBindFramebuffer',None,[U,U])(0x8d40,f);h.fn('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0,0xde1,t,0)
  if h.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FORMAT_UNSUPPORTED')
  return t,f
 def compile(src):
  p,o=h.program({'shader.vert':old.V,'shader.frag':src});programs.append(p)
  if not o['compile'] or not o['link']:raise RuntimeError('COMPILE_FAILED')
  return p
 try:
  if not {'GL_EXT_color_buffer_float','GL_EXT_color_buffer_half_float'}&set(h.metadata['extensions']):r['status']='UNSUPPORTED_FORMAT';return r
  for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):h.fn('glDisable',None,[U])(cap)
  h.fn('glViewport',None,[I]*4)(0,0,4,4);h.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));h.fn('glBindVertexArray',None,[U])(vao)
  accum=target(0x881a);final=target(0x8058);p=compile(FRAG);copy=compile(COPY)
  for name,planes in SCENES:
   ls=layers(planes);decision=exact_policy.decide(ls,4,4);truth=golden(ls);rows=[]
   selected=decision.get('far_to_near',['1','0'])
   for order in [selected,list(reversed(selected))]:
    h.fn('glBindFramebuffer',None,[U,U])(0x8d40,accum[1]);h.fn('glClearColor',None,[F]*4)(0,0,0,0);h.fn('glClear',None,[U])(0x4000);h.fn('glEnable',None,[U])(0xbe2);h.fn('glBlendFuncSeparate',None,[U]*4)(0x302,0x303,1,0x303);h.fn('glUseProgram',None,[U])(p)
    for ident in order:
     i=int(ident);loc=h.fn('glGetUniformLocation',I,[U,C.c_char_p])(p,b'layer');h.fn('glUniform4f',None,[I,F,F,F,F])(loc,*COLORS[i]);loc=h.fn('glGetUniformLocation',I,[U,C.c_char_p])(p,b'depthPlane');h.fn('glUniform2f',None,[I,F,F])(loc,*planes[i]);h.fn('glDrawArrays',None,[U,I,I])(4,0,3)
    h.fn('glDisable',None,[U])(0xbe2);h.fn('glBindFramebuffer',None,[U,U])(0x8d40,final[1]);h.fn('glUseProgram',None,[U])(copy);h.fn('glActiveTexture',None,[U])(0x84c0);h.fn('glBindTexture',None,[U,U])(0xde1,accum[0]);h.fn('glDrawArrays',None,[U,I,I])(4,0,3);pixels=(C.c_ubyte*64)();h.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,pixels);check();values=list(pixels)
    rows.append({'order':order,'pixels':values,'max_error_to_per_pixel_over':max(abs(x-y) for x,y in zip(values,truth))})
   r['scenes'].append({'id':name,'depth_planes':planes,'depth_evidence':ls,'decision':decision,'cpu_per_pixel_over':truth,'draws':rows})
  r['status']='HOST_POLICY_PASS' if all(x['draws'][0]['max_error_to_per_pixel_over']<=1 and x['draws'][1]['max_error_to_per_pixel_over']>2 for x in r['scenes'][:2]) and r['scenes'][2]['decision']['selection']=='UNAVAILABLE' and all(x['max_error_to_per_pixel_over']>2 for x in r['scenes'][2]['draws']) and r['scenes'][3]['decision']['reason']=='AMBIGUOUS_TIE' else 'FAIL';r['actual_draws']=24;r['actual_readbacks']=8
 finally:
  h.fn('glUseProgram',None,[U])(0);h.fn('glBindFramebuffer',None,[U,U])(0x8d40,0)
  for p in programs:h.fn('glDeleteProgram',None,[U])(p)
  for f in fb:h.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(f))
  for t in tex:h.fn('glDeleteTextures',None,[I,P])(1,C.byref(t))
  if vao.value:h.fn('glDeleteVertexArrays',None,[I,P])(1,C.byref(vao))
  h.close()
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 try:r=run(json.loads(a.config.read_text()))
 except Exception as e:r={'status':'FAIL','diagnostic':type(e).__name__}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(0 if r['status']=='HOST_POLICY_PASS' else 1)
