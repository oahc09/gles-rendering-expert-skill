#!/usr/bin/env python3
"""Finite source-informed attachment type/state transition controls, not upstream bug reproduction."""
import argparse,ctypes as C,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('attachment_diff',ROOT/'benchmarks/differential/run.py');diff=importlib.util.module_from_spec(spec);spec.loader.exec_module(diff)
U,I,P,F=diff.U,diff.I,diff.P,diff.F
VERT='#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}'
FLOAT='#version 300 es\nprecision highp float;layout(location=0)out vec4 color;void main(){color=vec4(.8,.2,.4,.5);}'
INTEGER='#version 300 es\nprecision highp int;layout(location=0)out uvec4 color;void main(){color=uvec4(7u,42u,65535u,123456u);}'
SPARSE='#version 300 es\nprecision highp float;precision highp int;layout(location=0)out vec4 a;layout(location=2)out uvec4 b;void main(){a=vec4(.8,.2,.4,.5);b=uvec4(7u,42u,65535u,123456u);}'
EXPECTED_INTEGER=[7,42,65535,123456]*16

def normalized_expected():
 src=[.8,.2,.4,.5];dst=[.2,.4,.6,1]
 return [int((src[k]*src[3]+dst[k]*(1-src[3]))*255+.5) if k<3 else 255 for k in range(4)]*16

def compare(actual,expected,integer=False):
 if len(actual)!=64 or len(expected)!=64 or any(type(v)is not int or v<0 or v>(2**32-1 if integer else 255) for v in actual):return dict(status='INVALID',max_error=None)
 err=max(abs(a-b) for a,b in zip(actual,expected));return dict(status='PASS' if err<=(0 if integer else 1) else 'FAIL',max_error=err)

class Host(diff.Host):
 def texture(self,integer):
  tex=U();self.fn('glGenTextures',None,[I,P])(1,C.byref(tex));self.fn('glBindTexture',None,[U,U])(0xde1,tex)
  for key in (0x2801,0x2800):self.fn('glTexParameteri',None,[U,U,I])(0xde1,key,0x2600)
  self.fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,0x8d70 if integer else 0x8058,4,4,0,0x8d99 if integer else 0x1908,0x1405 if integer else 0x1401,None)
  return tex
 def attach(self,tex,slot=0):
  self.fn('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0+slot,0xde1,tex,0)
 def draw(self,frag):
  prog,c=self.program({'shader.vert':VERT,'shader.frag':frag})
  try:
   if not c['compile'] or not c['link']:raise RuntimeError('compile/link failed')
   self.fn('glUseProgram',None,[U])(prog);self.fn('glDrawArrays',None,[U,I,I])(4,0,3)
   if self.error():raise RuntimeError('draw error')
  finally:self.fn('glUseProgram',None,[U])(0);self.fn('glDeleteProgram',None,[U])(prog)
 def read(self,integer,slot=0):
  self.fn('glReadBuffer',None,[U])(0x8ce0+slot);pixels=(U*64)() if integer else (C.c_ubyte*64)()
  self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x8d99 if integer else 0x1908,0x1405 if integer else 0x1401,pixels)
  if self.error():raise RuntimeError('readback error')
  return list(pixels)
 def clear_float(self,slot=0):self.fn('glClearBufferfv',None,[U,I,P])(0x1800,slot,(F*4)(.2,.4,.6,1))
 def execute(self):
  fb=U();vao=U();norm=U();uint=U();rows=[];sparse=dict(status='NOT_RUN')
  try:
   self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb);norm=self.texture(False);uint=self.texture(True)
   self.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));self.fn('glBindVertexArray',None,[U])(vao);self.fn('glViewport',None,[I]*4)(0,0,4,4)
   for cap in (0xbd0,0xb71,0xb90,0xc11,0xb44):self.fn('glDisable',None,[U])(cap)
   self.fn('glEnable',None,[U])(0xbe2);self.fn('glBlendFuncSeparate',None,[U]*4)(0x302,0x303,1,0x303)
   for name,tex,isint in [('normalized-before',norm,False),('integer-middle',uint,True),('normalized-after',norm,False)]:
    self.attach(tex)
    if self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('attachment incomplete')
    if isint:self.fn('glClearBufferuiv',None,[U,I,P])(0x1800,0,(U*4)(1,2,3,4))
    else:self.clear_float()
    self.draw(INTEGER if isint else FLOAT);pix=self.read(isint);enabled=bool(self.fn('glIsEnabled',U,[U])(0xbe2))
    rows.append(dict(id=name,expected='PASS',comparison=compare(pix,EXPECTED_INTEGER if isint else normalized_expected(),isint),blend_enabled=enabled,pixels=pix))
   self.fn('glDisable',None,[U])(0xbe2);self.clear_float();self.draw(FLOAT);pix=self.read(False);rows.append(dict(id='bad-disabled-blend',expected='FAIL',comparison=compare(pix,normalized_expected()),pixels=pix))
   self.attach(uint);self.draw(INTEGER.replace('42u','43u'));pixels=self.read(True);rows.append(dict(id='bad-integer-value',expected='FAIL',comparison=compare(pixels,EXPECTED_INTEGER,True),pixels=pixels))
   # Indexed sparse mixed-format MRT only when the implementation advertises support.
   indexed=any(e in self.metadata['extensions'] for e in ('GL_EXT_draw_buffers_indexed','GL_OES_draw_buffers_indexed')) or 'OpenGL ES 3.2' in self.metadata['api']
   maxdraw=I();self.fn('glGetIntegerv',None,[U,P])(0x8824,C.byref(maxdraw))
   if indexed and maxdraw.value>=3:
    getproc=self.fn('eglGetProcAddress',P,[C.c_char_p],True)
    def entry(names,restype,args):
     for name in names:
      ptr=getproc(name.encode())
      if ptr:return C.CFUNCTYPE(restype,*args)(ptr)
     return None
    suffix='' if 'OpenGL ES 3.2' in self.metadata['api'] else ('EXT' if 'GL_EXT_draw_buffers_indexed' in self.metadata['extensions'] else 'OES')
    disable=entry(('glDisablei'+suffix,),None,[U,U]);enable=entry(('glEnablei'+suffix,),None,[U,U]);blend=entry(('glBlendFuncSeparatei'+suffix,),None,[U,U,U,U,U])
    if enable is None or disable is None or blend is None:sparse=dict(status='UNSUPPORTED',reason='advertised indexed state entrypoints unavailable')
    else:
     self.attach(norm);self.attach(uint,2);self.fn('glDrawBuffers',None,[I,P])(3,(U*3)(0x8ce0,0,0x8ce2))
     if self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:sparse=dict(status='UNSUPPORTED',reason='mixed sparse MRT incomplete')
     else:
      enable(0xbe2,0);enable(0xbe2,2);blend(0,0x302,0x303,1,0x303);blend(2,0x302,0x303,1,0x303)
      self.clear_float();self.fn('glClearBufferuiv',None,[U,I,P])(0x1800,2,(U*4)(1,2,3,4));self.draw(SPARSE)
      normal=self.read(False,0);integer=self.read(True,2)
      sparse=dict(status='PASS' if compare(normal,normalized_expected())['status']=='PASS' and compare(integer,EXPECTED_INTEGER,True)['status']=='PASS' else 'FAIL',draw_buffers=['COLOR_ATTACHMENT0','NONE','COLOR_ATTACHMENT2'],normalized_pixels=normal,integer_pixels=integer,normalized=compare(normal,normalized_expected()),integer=compare(integer,EXPECTED_INTEGER,True))
      disable(0xbe2,0);self.clear_float();self.draw(SPARSE);bad=self.read(False,0)
      sparse['bad_disabled_index0']=dict(expected='FAIL',comparison=compare(bad,normalized_expected()),pixels=bad)
      if sparse['bad_disabled_index0']['comparison']['status']!='FAIL':sparse['status']='FAIL'
   else:sparse=dict(status='UNSUPPORTED',reason='indexed draw-buffer state or three draw buffers unavailable; finite single-attachment controls only')
   return dict(rows=rows,sparse_mrt=sparse,normalized_transition_byte_identical=rows[0]['pixels']==rows[2]['pixels'])
  finally:
   self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindVertexArray',None,[U])(0)
   for obj,fn in ((fb,'glDeleteFramebuffers'),(vao,'glDeleteVertexArrays'),(norm,'glDeleteTextures'),(uint,'glDeleteTextures')):
    if obj.value:self.fn(fn,None,[I,P])(1,C.byref(obj))

def run(config,output):
 host=Host(config)
 try:r=host.execute()
 finally:host.close()
 ok=all(x['comparison']['status']==x['expected'] and x.get('blend_enabled',True) for x in r['rows']) and r['sparse_mrt']['status']!='FAIL' and r['normalized_transition_byte_identical']
 report=dict(schema_version=1,status='HOST_PASS' if ok else 'FAIL',scope='finite source-informed FBO RGBA8 → RGBA32UI → RGBA8 and optional sparse mixed-format MRT; not complete ANGLE upstream bug reproduction',source_reference='ANGLE commit prefix 035f888; see v1.0.9 implementation review',source_hashes={n:hashlib.sha256(v.encode()).hexdigest() for n,v in {'vertex':VERT,'float':FLOAT,'integer':INTEGER,'sparse':SPARSE}.items()},normalized_cpu_golden=normalized_expected(),integer_cpu_golden=EXPECTED_INTEGER,physical_driver_gate='NOT_RUN',performance='NOT_MEASURED',**r)
 dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--output',required=True);a=parser.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
