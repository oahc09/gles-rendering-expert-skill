#!/usr/bin/env python3
"""Actual two-layer OVR multiview2 probe with sequential-render fallback."""
import argparse,ctypes as C,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'benchmarks/differential'))
from run import Host
U=C.c_uint;I=C.c_int;P=C.c_void_p
VERT='''#version 300 es
%s
%s
flat out highp uint view;
void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);view=%s;}
'''
FRAG='''#version 300 es
precision highp float;
flat in highp uint view;
out vec4 color;
void main(){color=view==0u?vec4(1,0,0,1):vec4(0,1,0,1);}
'''
def gate(ext,pointer,max_views):
 return set(['GL_OVR_multiview','GL_OVR_multiview2'])<=set(ext) and pointer and type(max_views) is int and max_views>=2

def validate_report(r):
 if r.get('status')!='HOST_PASS' or r.get('route_supported') is not True:return False
 rows=r.get('rows',[]);ids=['sequential_fallback_two_layers','multiview2_two_layers','zero_views','above_max_views','negative_base','non_array_texture']
 if len(rows)!=6 or {x.get('id') for x in rows}!=set(ids) or any(x.get('status')!='PASS' for x in rows):return False
 for row in rows:
  if row['id'] in ids[:2]:
   if row.get('rgba8')!=[[255,0,0,255]*16,[0,255,0,255]*16]:return False
  elif row.get('observed_error')!=(0x502 if row['id']=='non_array_texture' else 0x501):return False
 return r.get('readback_count')==4 and r.get('performance_claim') is False

def run(config):
 h=Host(config);objects=[];programs=[];rows=[];result={}
 def f(name,ret,args):return h.fn(name,ret,args)
 def gen(name):
  x=U();f('glGen'+name,None,[I,P])(1,C.byref(x));objects.append((name,x));return x.value
 def framebuffer_layer(fb,tex,layer):
  f('glBindFramebuffer',None,[U,U])(0x8d40,fb);f('glFramebufferTextureLayer',None,[U,U,U,I,I])(0x8d40,0x8ce0,tex,0,layer)
  if f('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5 or h.error():raise RuntimeError('layer FBO invalid')
 def read(fb,tex):
  images=[]
  for layer in range(2):
   framebuffer_layer(fb,tex,layer);buf=(C.c_ubyte*64)();f('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,buf)
   if h.error():raise RuntimeError('readback GL error')
   images.append(list(buf))
  return images
 try:
  ext=[e for e in ('GL_OVR_multiview','GL_OVR_multiview2') if e in h.metadata['extensions']]
  addr=h.fn('eglGetProcAddress',P,[C.c_char_p],True)(b'glFramebufferTextureMultiviewOVR')
  limit=I()
  if 'GL_OVR_multiview' in ext:f('glGetIntegerv',None,[U,P])(0x9631,C.byref(limit))
  if h.error():raise RuntimeError('capability query error')
  available=gate(ext,bool(addr),limit.value)
  if len(ext)==2 and not available:raise RuntimeError('advertised multiview2 has missing entrypoint/invalid limit')
  result.update(advertised=ext,max_views=limit.value if ext else None,route_supported=bool(available))
  tex=gen('Textures');f('glBindTexture',None,[U,U])(0x8c1a,tex);f('glTexStorage3D',None,[U,I,U,I,I,I])(0x8c1a,1,0x8058,4,4,2)
  fb=gen('Framebuffers');readfb=gen('Framebuffers');vao=gen('VertexArrays');f('glBindVertexArray',None,[U])(vao)
  expected=[[255,0,0,255]*16,[0,255,0,255]*16]
  def program(multi):
   src=VERT%('#extension GL_OVR_multiview2 : require' if multi else '', 'layout(num_views=2) in;' if multi else 'uniform highp uint selectedView;', 'uint(gl_ViewID_OVR)' if multi else 'selectedView')
   obj,check=h.program({'shader.vert':src,'shader.frag':FRAG});programs.append(obj)
   if not check['compile'] or not check['link']:raise RuntimeError('required program compile/link failed')
   return obj
  base=program(False);f('glUseProgram',None,[U])(base);loc=f('glGetUniformLocation',I,[U,C.c_char_p])(base,b'selectedView')
  f('glViewport',None,[I,I,I,I])(0,0,4,4);f('glDisable',None,[U])(0xbe2)
  for layer in range(2):
   framebuffer_layer(fb,tex,layer);f('glUniform1ui',None,[I,U])(loc,layer);f('glDrawArrays',None,[U,I,I])(4,0,3)
  fallback=read(readfb,tex);rows.append({'id':'sequential_fallback_two_layers','status':'PASS' if fallback==expected else 'FAIL','draw_calls':2,'rgba8':fallback})
  if available:
   # Destroy fallback pixels before the multiview draw; a no-op cannot pass.
   for layer in range(2):
    framebuffer_layer(fb,tex,layer);f('glClearColor',None,[C.c_float]*4)(0,0,1,1);f('glClear',None,[U])(0x4000)
   if h.error():raise RuntimeError('sentinel preclear failed')
   attach=C.CFUNCTYPE(None,U,U,U,I,I,I)(addr);f('glBindFramebuffer',None,[U,U])(0x8d40,fb);attach(0x8d40,0x8ce0,tex,0,0,2)
   if h.error() or f('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('multiview FBO invalid')
   prog=program(True);f('glUseProgram',None,[U])(prog);f('glDrawArrays',None,[U,I,I])(4,0,3)
   drawerr=h.error();pixels=read(readfb,tex);rows.append({'id':'multiview2_two_layers','status':'PASS' if drawerr==0 and pixels==expected else 'FAIL','draw_calls':1,'gl_error':drawerr,'rgba8':pixels})
   # API errors explicitly required by OVR_multiview rev6; not undefined shader behavior.
   f('glBindFramebuffer',None,[U,U])(0x8d40,fb)
   for name,baseview,views in [('zero_views',0,0),('above_max_views',0,limit.value+1),('negative_base',-1,2)]:
    attach(0x8d40,0x8ce0,tex,0,baseview,views);err=h.error();rows.append({'id':name,'status':'PASS' if err==0x501 else 'FAIL','expected_error':0x501,'observed_error':err})
   wrong=gen('Textures');f('glBindTexture',None,[U,U])(0xde1,wrong);f('glTexStorage2D',None,[U,I,U,I,I])(0xde1,1,0x8058,4,4)
   if h.error():raise RuntimeError('negative fixture allocation failed')
   attach(0x8d40,0x8ce0,wrong,0,0,2);err=h.error();rows.append({'id':'non_array_texture','status':'PASS' if err==0x502 else 'FAIL','expected_error':0x502,'observed_error':err})
  result.update(rows=rows,status='HOST_PASS' if all(x['status']=='PASS' for x in rows) and available else 'NOT_SUPPORTED' if not available else 'FAIL',fallback='sequential_per_layer_only_if_verified',readback_count=4 if available else 2,performance_claim=False,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),host_source_sha256=hashlib.sha256((ROOT/'benchmarks/differential/run.py').read_bytes()).hexdigest())
  if not all(x['status']=='PASS' for x in rows):result['status']='FAIL'
 except Exception as e:result.update(status='FAIL',reason=str(e),rows=rows)
 finally:
  for prog in programs:f('glDeleteProgram',None,[U])(prog)
  for kind,obj in reversed(objects):f('glDelete'+kind,None,[I,P])(1,C.byref(obj))
  h.close()
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=run(json.loads(a.config.read_text()));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(r['status']);raise SystemExit(not validate_report(r))
