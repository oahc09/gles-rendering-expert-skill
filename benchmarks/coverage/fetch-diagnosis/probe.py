"""Minimal isolated fetch diagnostic: exact typed API, no core inspection."""
import ctypes as C,json,sys,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'benchmarks/differential'));from run import Host
I=C.c_int;U=C.c_uint;P=C.c_void_p;F=C.c_float
VERT='#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.-1.,0,1);}'
def run(config,attachment,fetch,output):
 h=Host(config);gl=h.fn;report={'attachment':attachment,'fetch':fetch,'checkpoints':[]}
 def checkpoint(name):
  err=h.error();report['checkpoints'].append({'name':name,'gl_error':err});output.write_text(json.dumps(report,indent=2)+'\n')
  if err:raise RuntimeError('GL state error')
 fb=U();obj=U();vao=U();gl('glGenFramebuffers',None,[I,P])(1,C.byref(fb));gl('glBindFramebuffer',None,[U,U])(0x8d40,fb)
 if attachment=='texture':
  gl('glGenTextures',None,[I,P])(1,C.byref(obj));gl('glBindTexture',None,[U,U])(0xde1,obj);gl('glTexStorage2D',None,[U,I,U,I,I])(0xde1,1,0x8058,4,4);gl('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0,0xde1,obj,0);gl('glBindTexture',None,[U,U])(0xde1,0)
 else:
  gl('glGenRenderbuffers',None,[I,P])(1,C.byref(obj));gl('glBindRenderbuffer',None,[U,U])(0x8d41,obj);gl('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,4,4);gl('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,obj)
 report['fbo_complete']=gl('glCheckFramebufferStatus',U,[U])(0x8d40)==0x8cd5;checkpoint('attachment')
 gl('glGenVertexArrays',None,[I,P])(1,C.byref(vao));gl('glBindVertexArray',None,[U])(vao);gl('glViewport',None,[I]*4)(0,0,4,4);gl('glDisable',None,[U])(0xbe2);gl('glColorMask',None,[C.c_ubyte]*4)(1,1,1,1)
 frag='#version 300 es\n'+('#extension GL_EXT_shader_framebuffer_fetch : require\n' if fetch else '')+'precision highp float;layout(location=0) '+('inout' if fetch else 'out')+' vec4 color;void main(){color='+('vec4(color.b,color.r,color.g,1.0)' if fetch else 'vec4(0.75,0.25,0.5,1.0)')+';}'
 prog,obs=h.program({'shader.vert':VERT,'shader.frag':frag});report['compile']=obs['compile'];report['link']=obs['link'];checkpoint('compile_link')
 if not obs['compile'] or not obs['link'] or not report['fbo_complete']:raise RuntimeError('invalid setup')
 gl('glUseProgram',None,[U])(prog);gl('glClearColor',None,[F]*4)(.25,.5,.75,1);gl('glClear',None,[U])(0x4000);checkpoint('clear_before_draw')
 gl('glDrawArrays',None,[U,I,I])(4,0,3);checkpoint('draw_returned')
 buf=(C.c_ubyte*64)();gl('glReadPixels',None,[I]*4+[U,U,P])(0,0,4,4,0x1908,0x1401,buf);checkpoint('readback_returned');report['pixels']=list(buf);report['max_error']=max(abs(a-b) for a,b in zip(buf,[191,64,128,255]*16));report['status']='PASS' if report['max_error']<=1 else 'FAIL';output.write_text(json.dumps(report,indent=2)+'\n');h.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path);p.add_argument('--attachment',choices=['texture','renderbuffer']);p.add_argument('--fetch',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args();run(json.loads(a.config.read_text()),a.attachment,a.fetch,a.output)
