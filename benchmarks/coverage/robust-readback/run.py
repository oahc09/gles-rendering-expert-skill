#!/usr/bin/env python3
"""Finite robust CPU readback contracts; no reset/context-loss injection."""
import argparse,ctypes as C,hashlib,importlib.util,json,re,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('robust_diff',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
U=d.U;I=d.I;P=d.P;F=d.F
VERT='#version 300 es\nvoid main(){gl_Position=vec4(0,0,0,1);}'
FRAG='#version 300 es\nprecision highp float;uniform vec4 value;out vec4 color;void main(){color=value;}'
def routes(version,extensions):
 out=[]
 if version>=(3,2):out.append(('core',''))
 if 'GL_KHR_robustness' in extensions:out.append(('KHR','KHR'))
 return out

def resolve(h,name,args):
 ptr=h.fn('eglGetProcAddress',P,[C.c_char_p],True)(name.encode())
 if not ptr:return None
 return C.CFUNCTYPE(None,*args)(ptr)
def golden(strided=False):
 colors=[(255,0,0,255),(0,255,0,255),(0,0,255,255),(255,255,0,255)]
 out=[165]*128
 for y in range(4):
  for x in range(4):
   off=(28+y*24+x*4) if strided else y*16+x*4
   out[off:off+4]=colors[x]
 return out

def probe(fn,args,payload=128,expected=None,error=0,h=None):
 data=(C.c_ubyte*(payload+32))(*([165]*(payload+32)))
 fn(*args,C.byref(data,16));got=h.error();values=list(data)
 expected=([165]*payload if expected is None else expected)
 return {'gl_error':got,'expected_error':error,'prefix_canary':values[:16],'suffix_canary':values[-16:],'payload':values[16:-16],'expected_payload':expected,'status':'PASS' if got==error and values[:16]==[165]*16 and values[-16:]==[165]*16 and values[16:-16]==expected else 'FAIL'}

def run(config):
 h=d.Host(config);fb=U();rb=U();program=0
 report={'schema_version':1,'status':'FAIL','execution_class':'SOFTWARE_HOST','routes':[],'reset_injection':'NOT_RUN','context_recovery':'NOT_RUN','physical_device':'NOT_RUN','performance':'NOT_MEASURED','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 try:
  ma=I();mi=I();h.fn('glGetIntegerv',None,[U,P])(0x821b,C.byref(ma));h.fn('glGetIntegerv',None,[U,P])(0x821c,C.byref(mi));version=(ma.value,mi.value)
  available=routes(version,h.metadata['extensions']);report['queried_api_version']=list(version);report['KHR_robustness_advertised']='GL_KHR_robustness' in h.metadata['extensions']
  if not available:report['status']='UNSUPPORTED';return report
  h.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));h.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb)
  h.fn('glGenRenderbuffers',None,[I,P])(1,C.byref(rb));h.fn('glBindRenderbuffer',None,[U,U])(0x8d41,rb);h.fn('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,4,4);h.fn('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,rb)
  if h.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO_INCOMPLETE')
  h.fn('glDisable',None,[U])(0x0bd0);h.fn('glEnable',None,[U])(0x0c11)
  for x,color in enumerate(((1,0,0,1),(0,1,0,1),(0,0,1,1),(1,1,0,1))):
   h.fn('glScissor',None,[I]*4)(x,0,1,4);h.fn('glClearColor',None,[F]*4)(*color);h.fn('glClear',None,[U])(0x4000)
  h.fn('glDisable',None,[U])(0x0c11);h.fn('glBindBuffer',None,[U,U])(0x88eb,0)
  program,obs=h.program({'shader.vert':VERT,'shader.frag':FRAG});report['uniform_program']={'compile':obs['compile'],'link':obs['link'],'vertex_sha256':hashlib.sha256(VERT.encode()).hexdigest(),'fragment_sha256':hashlib.sha256(FRAG.encode()).hexdigest()}
  if not obs['compile'] or not obs['link']:raise RuntimeError('PROGRAM_FAILED')
  loc=h.fn('glGetUniformLocation',I,[U,C.c_char_p])(program,b'value')
  if loc<0:raise RuntimeError('UNIFORM_INACTIVE')
  h.fn('glUseProgram',None,[U])(program);h.fn('glUniform4f',None,[I,F,F,F,F])(loc,.25,.5,.75,1)
  if h.error()!=0:raise RuntimeError('SETUP_GL_ERROR')
  for route,suffix in available:
   read=resolve(h,'glReadnPixels'+suffix,[I,I,I,I,U,U,I,P]);uniform=resolve(h,'glGetnUniformfv'+suffix,[U,I,I,P]);entry={'route':route,'read_entry':'glReadnPixels'+suffix,'uniform_entry':'glGetnUniformfv'+suffix,'bufSize_unit':'bytes','cases':[]}
   report['routes'].append(entry)
   if not read or not uniform:entry['status']='MISSING_ENTRYPOINT';continue
   for strided in (False,True):
    for pname,value in ((0xd05,4),(0xd02,6 if strided else 0),(0xd03,1 if strided else 0),(0xd04,1 if strided else 0)):h.fn('glPixelStorei',None,[U,I])(pname,value)
    required=116 if strided else 64
    for size in ([required,required-1] if strided else [64,63,0]):
     row=probe(read,[0,0,4,4,0x1908,0x1401,size],expected=golden(strided) if size==required else None,error=0 if size==required else 0x502,h=h)
     row.update(id=('strided' if strided else 'tight')+'-'+str(size),bufSize=size,required_bytes=required,pack={'alignment':4,'row_length':6 if strided else 0,'skip_rows':1 if strided else 0,'skip_pixels':1 if strided else 0});entry['cases'].append(row)
   uniformbytes=list(struct.pack('=4f',.25,.5,.75,1))+[165]*112
   for size in (16,15,0):
    row=probe(uniform,[program,loc,size],expected=uniformbytes if size==16 else None,error=0 if size==16 else 0x502,h=h);row.update(id='uniform-'+str(size),bufSize=size,required_bytes=16);entry['cases'].append(row)
   entry['status']='PASS' if all(x['status']=='PASS' for x in entry['cases']) else 'FAIL'
  report['status']='HOST_PASS' if all(x['status']=='PASS' for x in report['routes']) else 'FAIL';report['robust_calls']=sum(len(x['cases']) for x in report['routes'])
 finally:
  if program:h.fn('glUseProgram',None,[U])(0);h.fn('glDeleteProgram',None,[U])(program)
  if fb.value:h.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);h.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(fb))
  if rb.value:h.fn('glDeleteRenderbuffers',None,[I,P])(1,C.byref(rb))
  h.close()
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 try:r=run(json.loads(a.config.read_text()))
 except Exception as e:r={'status':'FAIL','diagnostic':type(e).__name__,'physical_device':'NOT_RUN'}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(0 if r['status']=='HOST_PASS' else 77 if r['status']=='UNSUPPORTED' else 1)
