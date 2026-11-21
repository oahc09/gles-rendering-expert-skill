import argparse,ctypes as C,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools/coverage'))
from texture_buffer import route
s=importlib.util.spec_from_file_location('tbhost',ROOT/'benchmarks/texture_access/mechanisms.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
U,I,P=m.U,m.I,m.P
COLORS=[255,0,0,255,0,255,0,255,0,0,255,255,255,255,0,255]
VERT=m.VERTEX
BUFFER='#version 310 es\n#extension GL_EXT_texture_buffer : require\nprecision highp float;precision highp samplerBuffer;uniform samplerBuffer tex;uniform int base;uniform int count;out vec4 color;void main(){color=textureSize(tex)==count?texelFetch(tex,base+int(gl_FragCoord.x)):vec4(1,0,1,1);}'
FALLBACK='#version 300 es\nprecision highp float;uniform sampler2D tex;out vec4 color;void main(){color=texelFetch(tex,ivec2(int(gl_FragCoord.x),0),0);}'
def run(config,output):
 h=m.TextureHost(config);gl=h.fn;objects=[];programs=[];rows=[]
 def obj(kind):
  x=U();gl('glGen'+kind,None,[I,P])(1,C.byref(x));objects.append((kind,x));return x
 def compile(src):
  v=VERT.replace('#version 300 es','#version 310 es') if src==BUFFER else VERT
  p,r=h.program({'shader.vert':v,'shader.frag':src});programs.append(p)
  if not r['compile'] or not r['link']:raise RuntimeError('compile/link')
  return p
 def draw(name,p,expected,base=0,count=4):
  gl('glUseProgram',None,[U])(p)
  for key,val in [('tex',0),('base',base),('count',count)]:gl('glUniform1i',None,[I,I])(gl('glGetUniformLocation',I,[U,C.c_char_p])(p,key.encode()),val)
  gl('glDrawArrays',None,[U,I,I])(4,0,3);buf=(C.c_ubyte*64)();gl('glReadPixels',None,[I]*4+[U,U,P])(0,0,4,4,0x1908,0x1401,buf);err=h.error()
  rows.append({'id':name,'status':'PASS' if list(buf)==expected*4 and err==0 else 'FAIL','gl_error':err,'pixels':list(buf),'expected':expected*4})
 try:
  vao=obj('VertexArrays');gl('glBindVertexArray',None,[U])(vao);fb=obj('Framebuffers');rb=obj('Renderbuffers');gl('glBindFramebuffer',None,[U,U])(0x8d40,fb);gl('glBindRenderbuffer',None,[U,U])(0x8d41,rb);gl('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,4,4);gl('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,rb)
  if gl('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO')
  for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):gl('glDisable',None,[U])(cap)
  gl('glViewport',None,[I]*4)(0,0,4,4);gl('glActiveTexture',None,[U])(0x84c0)
  fallback=obj('Textures');gl('glBindTexture',None,[U,U])(0xde1,fallback)
  for pname in (0x2800,0x2801):gl('glTexParameteri',None,[U,U,I])(0xde1,pname,0x2600)
  raw=(C.c_ubyte*16)(*COLORS);gl('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,0x8058,4,1,0,0x1908,0x1401,raw);draw('rgba8_2d_fallback',compile(FALLBACK),COLORS)
  major=I();minor=I();gl('glGetIntegerv',None,[U,P])(0x821b,C.byref(major));gl('glGetIntegerv',None,[U,P])(0x821c,C.byref(minor));version=[major.value,minor.value]
  names=['glTexBufferEXT','glTexBufferRangeEXT'];ptrs={n:gl('eglGetProcAddress',P,[C.c_char_p],True)(n.encode()) for n in names};chosen=route(version,h.metadata['extensions'],[n for n,a in ptrs.items() if a]);facts={'queried_api_version':version,'EXT_advertised':'GL_EXT_texture_buffer' in h.metadata['extensions'],'route':chosen}
  if chosen=='EXT':
   full=C.CFUNCTYPE(None,U,U,U)(ptrs[names[0]]);ranged=C.CFUNCTYPE(None,U,U,U,C.c_ssize_t,C.c_ssize_t)(ptrs[names[1]])
   alignment=I();maxtex=I();gl('glGetIntegerv',None,[U,P])(0x919f,C.byref(alignment));gl('glGetIntegerv',None,[U,P])(0x8c2b,C.byref(maxtex));A=alignment.value
   if h.error() or A<1 or A>65536 or maxtex.value<4:raise RuntimeError('capability limit unsupported')
   import math
   offset=math.lcm(A,4);data=[255,0,255,255]*(offset//4)+COLORS;raw=(C.c_ubyte*len(data))(*data)
   b=obj('Buffers');gl('glBindBuffer',None,[U,U])(0x8c2a,b);gl('glBufferData',None,[U,C.c_ssize_t,P,U])(0x8c2a,len(data),raw,0x88e8);t=obj('Textures');gl('glBindTexture',None,[U,U])(0x8c2a,t)
   ranged(0x8c2a,0x8058,b,offset,16);p=compile(BUFFER);draw('range_four_texels',p,COLORS)
   changed=[0,255,255,255]+COLORS[4:];patch=(C.c_ubyte*4)(0,255,255,255);gl('glBufferSubData',None,[U,C.c_ssize_t,C.c_ssize_t,P])(0x8c2a,offset,4,patch);draw('storage_update_visible',p,changed)
   full(0x8c2a,0x8058,b);draw('whole_store_nonzero_index',p,changed,offset//4,len(data)//4)
   negatives=[('negative_offset',0x8c2a,0x8058,-1,16,0x501),('zero_size',0x8c2a,0x8058,0,0,0x501),('overrun',0x8c2a,0x8058,offset,17,0x501),('wrong_target',0xde1,0x8058,0,16,0x500),('unsized_format',0x8c2a,0x1908,0,16,0x500)]
   if A>1:negatives.append(('misaligned_offset',0x8c2a,0x8058,1,16,0x501))
   for name,target,fmt,off,size,expected in negatives:
    ranged(target,fmt,b,off,size);err=h.error();rows.append({'id':name,'status':'PASS' if err==expected else 'FAIL','gl_error':err,'expected_error':expected})
   ranged(0x8c2a,0x8058,0,-1,0);err=h.error();rows.append({'id':'detach_ignores_offset_size','status':'PASS' if err==0 else 'FAIL','gl_error':err,'no_undefined_fetch':True})
   full(0x8c2a,0x8058,0);err=h.error();rows.append({'id':'detach_whole_store','status':'PASS' if err==0 else 'FAIL','gl_error':err,'no_undefined_fetch':True})
   facts.update(offset_alignment=A,max_texture_buffer_texels=maxtex.value,range_offset=offset,storage_bytes=len(data),misalignment_case='EXECUTED' if A>1 else 'NOT_APPLICABLE_ALIGNMENT_ONE')
  result={'status':'FAIL' if any(r['status']=='FAIL' for r in rows) else 'HOST_PASS' if chosen=='EXT' else 'FALLBACK_PASS','facts':facts,'rows':rows,'physical_acceptance':False,'performance_claim':False,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256((ROOT/'tools/coverage/texture_buffer.py').read_bytes()).hexdigest()}
 finally:
  gl('glUseProgram',None,[U])(0);gl('glBindFramebuffer',None,[U,U])(0x8d40,0)
  for p in programs:gl('glDeleteProgram',None,[U])(p)
  for kind,x in reversed(objects):gl('glDelete'+kind,None,[I,P])(1,C.byref(x))
  h.close()
 Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']=='FAIL')
