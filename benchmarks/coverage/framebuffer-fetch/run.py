"""Actual ordered framebuffer fetch and separate-attachment ping-pong control."""
import argparse,ctypes as C,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools/coverage'))
from framebuffer_fetch import decide
spec=importlib.util.spec_from_file_location('fetch_host',ROOT/'benchmarks/texture_access/mechanisms.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
U,I,P=m.U,m.I,m.P;F=C.c_float
TRANSFORM='vec4(color.b,color.r,color.g,1.0)'
def shader(mode):
 if mode=='fallback':return '#version 300 es\nprecision highp float; uniform sampler2D tex;layout(location=0) out vec4 outColor;void main(){vec4 color=texelFetch(tex,ivec2(gl_FragCoord.xy),0);outColor='+TRANSFORM+';}'
 ext='GL_EXT_shader_framebuffer_fetch'+('_non_coherent' if mode!='coherent' else '')
 layout='location=0,noncoherent' if mode=='noncoherent' else 'location=0'
 return '#version 300 es\n#extension GL_EXT_shader_framebuffer_fetch : disable\n#extension '+ext+' : require\nprecision highp float;layout('+layout+') inout vec4 color;void main(){color='+TRANSFORM+';}'
def run(config,output,mode_filter=None):
 h=m.TextureHost(config);gl=h.fn;vao=U();textures=(U*2)();fb=(U*2)();programs=[];rows=[]
 try:
  ext=h.metadata['extensions'];gl('glGenVertexArrays',None,[I,P])(1,C.byref(vao));gl('glBindVertexArray',None,[U])(vao)
  gl('glGenTextures',None,[I,P])(2,textures);gl('glGenFramebuffers',None,[I,P])(2,fb)
  for t,f in zip(textures,fb):
   gl('glBindTexture',None,[U,U])(0xde1,t)
   gl('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,0x8058,4,4,0,0x1908,0x1401,None)
   for name in (0x2801,0x2800):gl('glTexParameteri',None,[U,U,I])(0xde1,name,0x2600)
   gl('glBindFramebuffer',None,[U,U])(0x8d40,f);gl('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0,0xde1,t,0)
   if gl('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO incomplete')
  for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):gl('glDisable',None,[U])(cap)
  gl('glViewport',None,[I]*4)(0,0,4,4);gl('glColorMask',None,[U]*4)(1,1,1,1)
  for mode in ([mode_filter] if mode_filter else ('coherent','noncoherent','fallback')):
   name='GL_EXT_shader_framebuffer_fetch'+('_non_coherent' if mode=='noncoherent' else '')
   if mode!='fallback' and name not in ext:rows.append({'mode':mode,'status':'NOT_SUPPORTED'});continue
   barrier=None
   if mode=='noncoherent':
    addr=gl('eglGetProcAddress',P,[C.c_char_p],True)(b'glFramebufferFetchBarrierEXT')
    if not addr:rows.append({'mode':mode,'status':'FAIL','reason':'advertised extension missing entrypoint'});continue
    barrier=C.CFUNCTYPE(None)(addr)
   p,obs=h.program({'shader.vert':m.VERTEX,'shader.frag':shader(mode)});programs.append(p)
   if not obs['compile'] or not obs['link']:rows.append({'mode':mode,'status':'FAIL','reason':'compile/link'});continue
   gl('glUseProgram',None,[U])(p);gl('glBindFramebuffer',None,[U,U])(0x8d40,fb[0]);gl('glClearColor',None,[F]*4)(.25,.5,.75,1);gl('glClear',None,[U])(0x4000)
   if mode=='fallback':gl('glUniform1i',None,[I,I])(gl('glGetUniformLocation',I,[U,C.c_char_p])(p,b'tex'),0)
   for step in range(2):
    if barrier:barrier()
    if mode=='fallback':
     gl('glBindFramebuffer',None,[U,U])(0x8d40,fb[(step+1)%2]);gl('glActiveTexture',None,[U])(0x84c0);gl('glBindTexture',None,[U,U])(0xde1,textures[step%2])
    gl('glDrawArrays',None,[U,I,I])(4,0,3)
   pixels=(C.c_ubyte*64)();gl('glReadPixels',None,[I]*4+[U,U,P])(0,0,4,4,0x1908,0x1401,pixels);error=h.error();expected=[128,191,64,255]*16;maximum=max(abs(a-b) for a,b in zip(pixels,expected))
   rows.append({'mode':mode,'status':'PASS' if error==0 and maximum<=1 else 'FAIL','gl_error':error,'pixels':list(pixels),'max_error':maximum,'barriers':2 if barrier else 0,'separate_source_destination':mode=='fallback'})
  if 'GL_EXT_shader_framebuffer_fetch_non_coherent' in ext:
   p,obs=h.program({'shader.vert':m.VERTEX,'shader.frag':shader('invalid-missing-qualifier')});programs.append(p);rows.append({'mode':'missing_noncoherent_qualifier','status':'PASS' if not obs['compile'] else 'FAIL','compile_rejected':not obs['compile']})
  result={'status':'FAIL' if any(r['status']=='FAIL' for r in rows) else 'HOST_PASS_WITH_UNSUPPORTED' if any(r['status']=='NOT_SUPPORTED' for r in rows) else 'HOST_PASS','rows':rows,'scope':'two ordered draws, one single-sample RGBA8 attachment; no MSAA/sRGB/helper-invocation/PLS or performance claim','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256((ROOT/'tools/coverage/framebuffer_fetch.py').read_bytes()).hexdigest(),'missing_barrier_policy':decide(ext,True,True,False),'physical_acceptance':False,'environment':h.metadata}
 finally:
  gl('glUseProgram',None,[U])(0);gl('glBindFramebuffer',None,[U,U])(0x8d40,0)
  for p in programs:
   if p:gl('glDeleteProgram',None,[U])(p)
  gl('glDeleteFramebuffers',None,[I,P])(2,fb);gl('glDeleteTextures',None,[I,P])(2,textures);gl('glDeleteVertexArrays',None,[I,P])(1,C.byref(vao));h.close()
 Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);p.add_argument('--mode',choices=['coherent','noncoherent','fallback']);a=p.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output,a.mode);print(r['status']);raise SystemExit(r['status']=='FAIL')
