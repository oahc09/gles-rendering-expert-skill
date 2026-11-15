#!/usr/bin/env python3
"""Bounded floating-point FBO → Reinhard → sRGB controls, not HDR-display validation."""
import argparse,ctypes as C,hashlib,importlib.util,json,math,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('hdr_diff',ROOT/'benchmarks/differential/run.py');diff=importlib.util.module_from_spec(spec);spec.loader.exec_module(diff)
U,I,P,F=diff.U,diff.I,diff.P,diff.F
W,H=16,8
LEVELS=[0,.00390625,.03125,.25,.5,1,4,16]
VERT='''#version 300 es
void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}
'''
HDR='''#version 300 es
precision highp float;uniform float exposure;
layout(location=0) out vec4 color;
void main(){float levels[8]=float[8](0.0,0.00390625,0.03125,0.25,0.5,1.0,4.0,16.0);
 int x=int(gl_FragCoord.x)%8;int y=int(gl_FragCoord.y)%8;
 color=vec4(levels[x],levels[y],levels[(x+y)%8],1.0)*vec4(exposure,exposure,exposure,1);}
'''
PREFIX='''#version 300 es
precision highp float;uniform sampler2D hdr;
layout(location=0) out vec4 color;
float encode(float x){return x<=0.0031308?12.92*x:1.055*pow(x,1.0/2.4)-0.055;}
vec3 srgb(vec3 x){return vec3(encode(x.r),encode(x.g),encode(x.b));}
void main(){vec3 linear=texelFetch(hdr,ivec2(gl_FragCoord.xy),0).rgb;
'''
EXPRESSIONS={'correct':'srgb(linear/(vec3(1.0)+linear))','bad-clamp-first':'srgb(clamp(linear,0.0,1.0)/(vec3(1.0)+clamp(linear,0.0,1.0)))','bad-gamma-direction':'pow(linear/(vec3(1.0)+linear),vec3(2.2))','bad-gamma-before-tonemap':'srgb(linear)/(vec3(1.0)+srgb(linear))'}
def fragment(arm):return PREFIX+'color=vec4('+EXPRESSIONS[arm]+',1.0);}'
def linear_pixels(exposure):
 return [v for y in range(H) for x in range(W) for v in (LEVELS[x%8]*exposure,LEVELS[y%8]*exposure,LEVELS[(x+y)%8]*exposure,1.)]
def encode_srgb(x):return 12.92*x if x<=.0031308 else 1.055*x**(1/2.4)-.055
def golden(exposure):
 hdr=linear_pixels(exposure);return [255 if i%4==3 else math.floor(encode_srgb(v/(1+v))*255+.5) for i,v in enumerate(hdr)]
def compare(pixels,expected):
 if len(pixels)!=W*H*4 or len(expected)!=len(pixels) or any(type(v)is not int or not 0<=v<=255 for v in pixels):return dict(status='INVALID',max_error=None)
 error=max(abs(a-b) for a,b in zip(pixels,expected));return dict(status='PASS' if error<=1 else 'FAIL',max_error=error)

class Host(diff.Host):
 def target(self,internal,type_):
  fb=U();tex=U();self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb)
  self.fn('glGenTextures',None,[I,P])(1,C.byref(tex));self.fn('glBindTexture',None,[U,U])(0xde1,tex)
  for key,value in ((0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812f),(0x2803,0x812f)):self.fn('glTexParameteri',None,[U,U,I])(0xde1,key,value)
  self.fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,internal,W,H,0,0x1908,type_,None)
  self.fn('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0,0xde1,tex,0)
  return fb,tex,self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)==0x8cd5
 def execute(self,exposure):
  programs=[];fb1=U();tex1=U();fb2=U();tex2=U();vao=U()
  try:
   fb1,tex1,complete=self.target(0x881a,0x140b) # RGBA16F / HALF_FLOAT
   if not complete:return dict(status='UNSUPPORTED_FLOAT_ATTACHMENT')
   fb2,tex2,complete=self.target(0x8058,0x1401)
   if not complete:raise RuntimeError('RGBA8 incomplete')
   for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):self.fn('glDisable',None,[U])(cap)
   self.fn('glViewport',None,[I]*4)(0,0,W,H);self.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));self.fn('glBindVertexArray',None,[U])(vao)
   prog,c=self.program({'shader.vert':VERT,'shader.frag':HDR});programs.append(prog)
   if not c['compile'] or not c['link']:raise RuntimeError('HDR source failed compile/link')
   self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb1);self.fn('glUseProgram',None,[U])(prog)
   loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,b'exposure');self.fn('glUniform1f',None,[I,F])(loc,exposure);self.fn('glDrawArrays',None,[U,I,I])(4,0,3)
   if self.error():raise RuntimeError('HDR draw failed')
   fp=(F*(W*H*4))();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,W,H,0x1908,0x1406,fp);err=self.error()
   float_result=dict(status='UNSUPPORTED_FLOAT_READBACK',gl_error=err) if err else dict(status='PASS' if list(fp)==linear_pixels(exposure) else 'FAIL',pixels=list(fp),max_error=max(abs(a-b) for a,b in zip(fp,linear_pixels(exposure))))
   self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb2);self.fn('glActiveTexture',None,[U])(0x84c0);self.fn('glBindTexture',None,[U,U])(0xde1,tex1)
   rows=[]
   for arm in EXPRESSIONS:
    prog,c=self.program({'shader.vert':VERT,'shader.frag':fragment(arm)});programs.append(prog)
    if not c['compile'] or not c['link']:raise RuntimeError('SDR source failed compile/link')
    self.fn('glUseProgram',None,[U])(prog);loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,b'hdr');self.fn('glUniform1i',None,[I,I])(loc,0);self.fn('glDrawArrays',None,[U,I,I])(4,0,3)
    pix=(C.c_ubyte*(W*H*4))();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,W,H,0x1908,0x1401,pix)
    if self.error():raise RuntimeError('SDR pass failed')
    rows.append(dict(arm=arm,pixels=list(pix),expected='PASS' if arm=='correct' else 'FAIL',comparison=compare(list(pix),golden(exposure)),source_sha256=hashlib.sha256(fragment(arm).encode()).hexdigest()))
   return dict(status='EXECUTED',exposure=exposure,float_attachment='RGBA16F_COMPLETE',float_readback=float_result,rows=rows)
  finally:
   self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindVertexArray',None,[U])(0)
   for prog in programs:self.fn('glDeleteProgram',None,[U])(prog)
   for obj,fn in ((fb1,'glDeleteFramebuffers'),(fb2,'glDeleteFramebuffers'),(tex1,'glDeleteTextures'),(tex2,'glDeleteTextures'),(vao,'glDeleteVertexArrays')):
    if obj.value:self.fn(fn,None,[I,P])(1,C.byref(obj))

def run(config,output):
 dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True);host=Host(config)
 try:runs=[host.execute(e) for e in (.25,1.,4.)]
 finally:host.close()
 ok=all(r.get('status')=='EXECUTED' and r['float_readback']['status']=='PASS' and all(x['comparison']['status']==x['expected'] for x in r['rows']) for r in runs)
 report=dict(status='HOST_PASS' if ok else 'FAIL',scope='Software GLES RGBA16F linear HDR, Reinhard tone map, explicit sRGB transfer to RGBA8; not HDR display validation',dimensions=[W,H],levels=LEVELS,exposures=[.25,1.,4.],pixel_order='bottom-up RGBA',source_hashes={'vertex':hashlib.sha256(VERT.encode()).hexdigest(),'hdr':hashlib.sha256(HDR.encode()).hexdigest()},physical_hdr_display='NOT_RUN',physical_gpu_performance='NOT_MEASURED',sdr_tolerance_codes=1,runs=runs,cpu_goldens={str(e):golden(e) for e in (.25,1.,4.)})
 dest.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--output',required=True);a=parser.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
