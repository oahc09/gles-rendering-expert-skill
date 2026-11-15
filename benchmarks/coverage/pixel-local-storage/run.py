#!/usr/bin/env python3
"""ANGLE-specific bounded PLS accumulation plus GLES3 ping-pong fallback."""
import argparse,ctypes as C,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('pls_host',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
U=d.U;I=d.I;P=d.P;F=d.F
V='#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}'
PLS='#version 300 es\n#extension GL_ANGLE_shader_pixel_local_storage : require\nprecision highp float;layout(binding=0,rgba8) uniform highp pixelLocalANGLE plane;uniform vec4 delta;void main(){pixelLocalStoreANGLE(plane,pixelLocalLoadANGLE(plane)+delta);}'
FALLBACK='#version 300 es\nprecision highp float;uniform sampler2D prior;uniform vec4 delta;out vec4 color;void main(){color=texelFetch(prior,ivec2(gl_FragCoord.xy),0)+delta;}'
DELTAS=[(64,32,16,64),(32,64,16,64),(16,16,16,16)]
def expected(count):return [sum(v[i] for v in DELTAS[:count]) for i in range(4)]*16
def quality(pixels,golden):return len(pixels)==64 and pixels==golden

def run(config):
 h=d.Host(config);textures=[];fbos=[];programs=[];vao=U();active=False
 report={'schema_version':1,'status':'FAIL','execution_class':'SOFTWARE_HOST','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'shader_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in [('vertex',V),('pls',PLS),('fallback',FALLBACK)]},'pls':'NOT_RUN','performance':'NOT_MEASURED','physical_device':'NOT_RUN','native_tile_residency':'NOT_MEASURED','events':[]}
 def check():
  e=h.error()
  if e:raise RuntimeError('GL_ERROR_'+str(e))
 def bind(f):h.fn('glBindFramebuffer',None,[U,U])(0x8d40,f)
 def texture():
  t=U();h.fn('glGenTextures',None,[I,P])(1,C.byref(t));textures.append(t);h.fn('glBindTexture',None,[U,U])(0xde1,t)
  h.fn('glTexStorage2D',None,[U,I,U,I,I])(0xde1,1,0x8058,4,4)
  for param in (0x2801,0x2800):h.fn('glTexParameteri',None,[U,U,I])(0xde1,param,0x2600)
  return t
 def fbo(t=None):
  f=U();h.fn('glGenFramebuffers',None,[I,P])(1,C.byref(f));fbos.append(f);bind(f)
  if t:h.fn('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0,0xde1,t,0)
  return f
 def program(src):
  p,obs=h.program({'shader.vert':V,'shader.frag':src});programs.append(p)
  if not obs['compile'] or not obs['link']:raise RuntimeError('SHADER_FAILED')
  return p
 def draw(p,delta):
  h.fn('glUseProgram',None,[U])(p);loc=h.fn('glGetUniformLocation',I,[U,C.c_char_p])(p,b'delta');h.fn('glUniform4f',None,[I,F,F,F,F])(loc,*[x/255 for x in delta]);h.fn('glDrawArrays',None,[U,I,I])(4,0,3);check()
 def read(f):
  bind(f);buf=(C.c_ubyte*64)();h.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,buf);check();return list(buf)
 try:
  for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):h.fn('glDisable',None,[U])(cap)
  h.fn('glViewport',None,[I]*4)(0,0,4,4);h.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));h.fn('glBindVertexArray',None,[U])(vao)
  ts=[texture(),texture()];fs=[fbo(t) for t in ts]
  for f in fs:bind(f);h.fn('glClearColor',None,[F]*4)(0,0,0,0);h.fn('glClear',None,[U])(0x4000)
  p=program(FALLBACK);fallback=[]
  for i,delta in enumerate(DELTAS):
   src=i%2;dst=1-src;bind(fs[dst]);h.fn('glActiveTexture',None,[U])(0x84c0);h.fn('glBindTexture',None,[U,U])(0xde1,ts[src]);draw(p,delta)
   if i>=1:fallback.append({'stage':i+1,'pixels':read(fs[dst]),'golden':expected(i+1)})
  report['fallback']={'status':'PASS' if all(quality(r['pixels'],r['golden']) for r in fallback) else 'FAIL','draws':3,'readbacks':fallback,'feedback_loop':False}
  ext=h.metadata['extensions'];report['advertised']='GL_ANGLE_shader_pixel_local_storage' in ext;report['coherent_advertised']='GL_ANGLE_shader_pixel_local_storage_coherent' in ext
  if not report['advertised']:
   report['pls']='UNSUPPORTED';report['status']='FALLBACK_PASS' if report['fallback']['status']=='PASS' else 'FAIL';return report
  funcs={}
  for name,args in [('glFramebufferTexturePixelLocalStorageANGLE',[I,U,I,I]),('glBeginPixelLocalStorageANGLE',[I,P]),('glEndPixelLocalStorageANGLE',[I,P]),('glPixelLocalStorageBarrierANGLE',[])]:
   ptr=h.fn('eglGetProcAddress',P,[C.c_char_p],True)(name.encode())
   if not ptr:raise RuntimeError('MISSING_ENTRYPOINT')
   funcs[name]=C.CFUNCTYPE(None,*args)(ptr)
  limit=I();h.fn('glGetIntegerv',None,[U,P])(0x96e0,C.byref(limit));report['max_planes']=limit.value
  if limit.value<1:raise RuntimeError('NO_PLANES')
  backing=texture();view=fbo(backing);plsfb=fbo();h.fn('glDrawBuffers',None,[I,P])(1,(U*1)(0));funcs['glFramebufferTexturePixelLocalStorageANGLE'](0,backing,0,0);check();p=program(PLS)
  begin=funcs['glBeginPixelLocalStorageANGLE'];end=funcs['glEndPixelLocalStorageANGLE'];barrier=funcs['glPixelLocalStorageBarrierANGLE']
  begin(1,(U*1)(0x96e3));active=True;check();report['events'].append('BEGIN_ZERO')
  begin(1,(U*1)(0x96e3));nested=h.error();report['negative_nested_begin']={'expected_error':0x502,'gl_error':nested}
  draw(p,DELTAS[0]);barrier();check();report['events'].append('DRAW_BARRIER_DRAW');draw(p,DELTAS[1]);end(1,(U*1)(0x96e6));active=False;check();report['events'].append('END_STORE')
  first=read(view);bind(plsfb);begin(1,(U*1)(0x96e5));active=True;check();draw(p,DELTAS[2]);end(1,(U*1)(0x96e6));active=False;check();report['events'].append('BEGIN_LOAD_DRAW_END_STORE');second=read(view)
  bind(plsfb);end(1,(U*1)(0x96e6));inactive=h.error();report['negative_inactive_end']={'expected_error':0x502,'gl_error':inactive}
  # Deterministic wrong-load negative; do NOT omit required barriers or inspect DONT_CARE.
  begin(1,(U*1)(0x96e3));active=True;check();draw(p,DELTAS[2]);end(1,(U*1)(0x96e6));active=False;check();wrong=read(view)
  report['pls']={'status':'PASS' if quality(first,expected(2)) and quality(second,expected(3)) and wrong==list(DELTAS[2])*16 and not quality(wrong,expected(3)) and nested==inactive==0x502 else 'FAIL','draws':4,'explicit_barriers':1,'readbacks':[{'stage':2,'pixels':first,'golden':expected(2)},{'stage':3,'pixels':second,'golden':expected(3)}],'negative_wrong_zero_load':{'pixels':wrong,'expected_actual':list(DELTAS[2])*16,'rejected_against_load_oracle':not quality(wrong,expected(3))}}
  report['status']='HOST_PASS' if report['pls']['status']==report['fallback']['status']=='PASS' else 'FAIL'
 finally:
  if active:
   try:funcs['glEndPixelLocalStorageANGLE'](1,(U*1)(0x1100))
   except Exception:pass
  h.fn('glUseProgram',None,[U])(0);bind(0)
  for p in programs:h.fn('glDeleteProgram',None,[U])(p)
  for f in fbos:h.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(f))
  for t in textures:h.fn('glDeleteTextures',None,[I,P])(1,C.byref(t))
  if vao.value:h.fn('glDeleteVertexArrays',None,[I,P])(1,C.byref(vao))
  h.close()
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 try:r=run(json.loads(a.config.read_text()))
 except Exception as e:r={'status':'FAIL','diagnostic':str(e) if str(e).startswith(('GL_ERROR_','SHADER_','MISSING_','NO_')) else type(e).__name__}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(0 if r['status'] in ('HOST_PASS','FALLBACK_PASS') else 1)
