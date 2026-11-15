#!/usr/bin/env python3
"""Actual GLES 3 texture mechanisms. Software correctness, not throughput claims."""
import ctypes as C
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'benchmarks/shader_ab'))
spec=importlib.util.spec_from_file_location('texture_ab',ROOT/'benchmarks/shader_ab/run.py');ab=importlib.util.module_from_spec(spec);spec.loader.exec_module(ab)
U,I,P=ab.U,ab.I,ab.P
VERTEX=ab.VERTEX
RGBA=[255,0,0,255,0,255,0,255,0,0,255,255,255,255,255,255]

def source(expr, array=False):
 return '#version 300 es\nprecision highp float;\nprecision highp sampler2DArray;\nuniform '+('sampler2DArray' if array else 'sampler2D')+' tex;\nlayout(location=0) out vec4 color;\nvoid main(){color='+expr+';}'

def cases():
 return [
 {'id':'etc2-compressed-block','mode':'etc2','source':source('texture(tex,vec2(0.5))'),'golden':[2,2,2,255]*16,'tolerance':0},
 {'id':'anisotropy-legal-control','mode':'aniso','source':source('texture(tex,gl_FragCoord.xy/4.0)'),'golden':[255,0,0,255]*16,'tolerance':0},
 {'id':'astc-void-extent','mode':'astc','source':source('texture(tex,vec2(0.5))'),'golden':[255,0,0,255]*16,'tolerance':0},
 {'id':'direct-upload-baseline','mode':'direct','source':source('texture(tex,gl_FragCoord.xy/4.0)'),'golden':[v for y in range(4) for x in range(4) for v in RGBA[4*((y//2)*2+x//2):4*((y//2)*2+x//2)+4]],'tolerance':0},
 {'id':'generated-mipmap','mode':'mip','source':source('textureLod(tex,vec2(0.5),1.0)'),'golden':[128,128,128,255]*16,'tolerance':1},
 {'id':'explicit-mipmap','mode':'explicit-mip','source':source('textureLod(tex,vec2(0.5),1.0)'),'golden':[128,128,128,255]*16,'tolerance':1},
 {'id':'array-layer-selection','mode':'array','source':source('texture(tex,vec3(vec2(0.5),1.0))',True),'golden':[0,255,0,255]*16,'tolerance':0},
 {'id':'pbo-upload','mode':'pbo','source':source('texture(tex,gl_FragCoord.xy/4.0)'),'golden':[v for y in range(4) for x in range(4) for v in RGBA[4*((y//2)*2+x//2):4*((y//2)*2+x//2)+4]],'tolerance':0},
 {'id':'r8-swizzle','mode':'r8','source':source('texture(tex,vec2(0.5))'),'golden':[128,128,128,255]*16,'tolerance':0},
 {'id':'rgb565-format','mode':'rgb565','source':source('texture(tex,vec2(0.5))'),'golden':[255,0,0,255]*16,'tolerance':0},
 {'id':'linear-filter','mode':'linear','source':source('texture(tex,vec2(0.5))'),'golden':[128,128,128,255]*16,'tolerance':1},
 {'id':'atlas-half-texel-guard','mode':'atlas','source':source('texture(tex,vec2(0.25,0.5))'),'golden':[255,0,0,255]*16,'tolerance':0},
 {'id':'atlas-bleed-negative','mode':'atlas','source':source('texture(tex,vec2(0.5,0.5))'),'golden':[255,0,0,255]*16,'tolerance':0,'negative':True},
 {'id':'resolution-loss-negative','mode':'lowres','source':source('texture(tex,gl_FragCoord.xy/4.0)'),'golden':[v for y in range(4) for x in range(4) for v in RGBA[4*((y//2)*2+x//2):4*((y//2)*2+x//2)+4]],'tolerance':0,'negative':True}]

class TextureHost(ab.ExperimentHost):
 def execute(self,c):
  gl=self.fn;tex=U();fb=U();rb=U();vao=U();pbo=U();program=0
  while self.error():pass
  try:
   program,compiled=self.program({'shader.vert':VERTEX,'shader.frag':c['source']})
   if not compiled['compile'] or not compiled['link']:raise RuntimeError('shader compile/link failed')
   gl('glGenFramebuffers',None,[I,P])(1,C.byref(fb));gl('glBindFramebuffer',None,[U,U])(0x8d40,fb)
   gl('glGenRenderbuffers',None,[I,P])(1,C.byref(rb));gl('glBindRenderbuffer',None,[U,U])(0x8d41,rb)
   gl('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,4,4);gl('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,rb)
   if gl('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO incomplete')
   for cap in (0x0bd0,0x0be2,0x0b71,0x0b90,0x0c11,0x0b44):gl('glDisable',None,[U])(cap)
   gl('glViewport',None,[I,I,I,I])(0,0,4,4);gl('glGenVertexArrays',None,[I,P])(1,C.byref(vao));gl('glBindVertexArray',None,[U])(vao)
   gl('glUseProgram',None,[U])(program);gl('glActiveTexture',None,[U])(0x84c0)
   target=0x8c1a if c['mode']=='array' else 0xde1
   gl('glGenTextures',None,[I,P])(1,C.byref(tex));gl('glBindTexture',None,[U,U])(target,tex)
   linear=c['mode'] in ('linear','atlas'); mip=c['mode'] in ('mip','explicit-mip')
   for pname,value in ((0x2801,0x2700 if mip else 0x2601 if linear else 0x2600),(0x2800,0x2601 if linear else 0x2600),(0x2802,0x812f),(0x2803,0x812f)):
    gl('glTexParameteri',None,[U,U,I])(target,pname,value)
   gl('glPixelStorei',None,[U,I])(0xcf5,1)
   start=time.perf_counter_ns(); logical=16
   if c['mode']=='etc2':
    pixels=(C.c_ubyte*8)(*([0]*8));logical=8
    gl('glCompressedTexImage2D',None,[U,I,U,I,I,I,I,P])(target,0,0x9274,4,4,0,8,pixels)
   elif c['mode']=='astc':
    # LDR void-extent constant-color block: 0xDFC mode, all-ones extents,
    # four little-endian UNORM16 channels. Oracle is solid opaque red.
    block=[0xfc,0xfd,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0,0,0,0,0xff,0xff]
    pixels=(C.c_ubyte*16)(*block);logical=16
    gl('glCompressedTexImage2D',None,[U,I,U,I,I,I,I,P])(target,0,0x93b0,4,4,0,16,pixels)
   elif c['mode']=='array':
    pixels=(C.c_ubyte*8)(255,0,0,255,0,255,0,255);logical=8
    gl('glTexImage3D',None,[U,I,I,I,I,I,I,U,U,P])(target,0,0x8058,1,1,2,0,0x1908,0x1401,pixels)
   elif c['mode']=='r8':
    pixels=(C.c_ubyte*1)(128);logical=1
    gl('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(target,0,0x8229,1,1,0,0x1903,0x1401,pixels)
    for pname,value in ((0x8e42,0x1903),(0x8e43,0x1903),(0x8e44,0x1903),(0x8e45,1)):gl('glTexParameteri',None,[U,U,I])(target,pname,value)
   elif c['mode']=='rgb565':
    pixels=(C.c_ushort*1)(0xf800);logical=2
    gl('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(target,0,0x8d62,1,1,0,0x1907,0x8363,pixels)
   else:
    width,height=2,2; data=RGBA
    if c['mode']=='aniso':width,height=4,4;data=[255,0,0,255]*16
    if c['mode']=='atlas':width,height=2,1;data=[255,0,0,255,0,255,0,255]
    if c['mode']=='lowres':width,height=1,1;data=[128,128,128,255]
    logical=len(data);pixels=(C.c_ubyte*len(data))(*data);pointer=pixels
    if c['mode']=='pbo':
     gl('glGenBuffers',None,[I,P])(1,C.byref(pbo));gl('glBindBuffer',None,[U,U])(0x88ec,pbo)
     gl('glBufferData',None,[U,C.c_ssize_t,P,U])(0x88ec,len(data),pixels,0x88e0);pointer=None
    gl('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(target,0,0x8058,width,height,0,0x1908,0x1401,pointer)
    if pbo.value:gl('glBindBuffer',None,[U,U])(0x88ec,0)
    if c['mode']=='mip':gl('glGenerateMipmap',None,[U])(target);logical+=4
    if c['mode']=='explicit-mip':
     small=(C.c_ubyte*4)(128,128,128,255);gl('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(target,1,0x8058,1,1,0,0x1908,0x1401,small);logical+=4
   if c['mode']=='aniso':
    gl('glGenerateMipmap',None,[U])(target)
    gl('glTexParameteri',None,[U,U,I])(target,0x2801,0x2703)
    gl('glTexParameteri',None,[U,U,I])(target,0x2800,0x2601)
    logical+=20
   if c['mode']=='aniso' and 'GL_EXT_texture_filter_anisotropic' in self.metadata.get('extensions',[]):
    maximum=C.c_float();gl('glGetFloatv',None,[U,P])(0x84ff,C.byref(maximum))
    gl('glTexParameterf',None,[U,U,C.c_float])(target,0x84fe,min(2.0,maximum.value))
   submit_ms=(time.perf_counter_ns()-start)/1e6
   loc=gl('glGetUniformLocation',I,[U,C.c_char_p])(program,b'tex');gl('glUniform1i',None,[I,I])(loc,0)
   gl('glDrawArrays',None,[U,I,I])(4,0,3);pixels=(C.c_ubyte*64)();gl('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,pixels)
   err=self.error();maximum=max(abs(a-b) for a,b in zip(pixels,c['golden']));quality='PASS' if maximum<=c['tolerance'] else 'FAIL'
   return dict(id=c['id'],mechanism=c['mode'],compile=True,link=True,gl_error=err,pixels=list(pixels),cpu_oracle_max_error=maximum,quality=quality,expected='FAIL' if c.get('negative') else 'PASS',source_sha256=hashlib.sha256(c['source'].encode()).hexdigest(),logical_texture_bytes=logical,cpu_upload_submission_ms=submit_ms,cpu_transcode_ms=None,physical_resident_bytes=None,gpu_upload_stall_ms=None,dram_bytes=None,performance_status='NOT_MEASURED')
  finally:
   gl('glBindBuffer',None,[U,U])(0x88ec,0);gl('glPixelStorei',None,[U,I])(0xcf5,4);gl('glUseProgram',None,[U])(0);gl('glBindFramebuffer',None,[U,U])(0x8d40,0);gl('glBindVertexArray',None,[U])(0)
   for obj,fn in [(pbo,'glDeleteBuffers'),(tex,'glDeleteTextures'),(vao,'glDeleteVertexArrays'),(rb,'glDeleteRenderbuffers'),(fb,'glDeleteFramebuffers')]:
    if obj.value:gl(fn,None,[I,P])(1,C.byref(obj))
   if program:gl('glDeleteProgram',None,[U])(program)

def run(config,output):
 h=TextureHost(config)
 try:
  ext=h.metadata.get('extensions',[])
  astc=any(x in ext for x in ('GL_KHR_texture_compression_astc_ldr','GL_KHR_texture_compression_astc_hdr'))
  rows=[h.execute(c) for c in cases() if c['mode']!='astc' or astc]
  indexed={r['id']:r for r in rows}
  comparisons=[{'baseline':a,'candidate':b,'pixel_equal':indexed[a]['pixels']==indexed[b]['pixels'],'performance_status':'NOT_MEASURED'} for a,b in [('direct-upload-baseline','pbo-upload'),('generated-mipmap','explicit-mipmap')]]
  ext=h.metadata.get('extensions',[])
  astc=any(x in ext for x in ('GL_KHR_texture_compression_astc_ldr','GL_KHR_texture_compression_astc_hdr'))
  aniso='GL_EXT_texture_filter_anisotropic' in ext
  result=dict(status='HOST_PASS' if all(r['gl_error']==0 and r['quality']==r['expected'] for r in rows) else 'FAIL',experiments=rows,paired_controls=comparisons,scope='Actual 4x4 software GLES texture mechanism correctness; CPU submit timings are not GPU stall/benefit.',compression_routes={'ETC2':{'route':'GLES3_CORE','execution':'EXECUTED_CONSTANT_BLOCK'},'ASTC':{'route':'EXTENSION_PRESENT' if astc else 'RGBA8_FALLBACK','execution':'EXECUTED_CONSTANT_BLOCK' if astc else 'NOT_RUN','physical_acceptance':'BLOCKED_BY_HARDWARE'},'anisotropy':{'route':'EXTENSION_PRESENT' if aniso else 'ISOTROPIC_FALLBACK','execution':'EXECUTED_LEGAL_PARAMETER' if aniso else 'EXECUTED_ISOTROPIC_FALLBACK'}},hardware='BLOCKED_BY_HARDWARE')
 finally:h.close()
 Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
