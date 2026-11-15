#!/usr/bin/env python3
"""Finite two-geometry-pass weighted OIT; approximation may be quality rejected."""
import argparse,ctypes as C,hashlib,importlib.util,itertools,json,math,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('oit_host',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
U=d.U;I=d.I;P=d.P;F=d.F
V='#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}'
BASE='#version 300 es\nprecision highp float;uniform vec4 layer;uniform float weight;out vec4 color;void main(){BODY}'
ACCUM=BASE.replace('BODY','color=vec4(layer.rgb*layer.a,layer.a)*weight;')
REVEAL=BASE.replace('BODY','color=vec4(layer.a);')
SORTED=BASE.replace('BODY','color=layer;')
RESOLVE='#version 300 es\nprecision highp float;uniform sampler2D accum;uniform sampler2D reveal;uniform int copyOnly;out vec4 color;void main(){ivec2 p=ivec2(gl_FragCoord.xy);vec4 a=texelFetch(accum,p,0);float r=texelFetch(reveal,p,0).r;color=copyOnly!=0?a:vec4(a.rgb/max(a.a,0.0001)*(1.0-r),1.0-r);}'
SCENES=[{'id':'soft-colored','layers':[{'rgba':[1,0,.125,.25],'z':0},{'rgba':[0,1,.125,.25],'z':1},{'rgba':[.125,0,1,.25],'z':3}]},{'id':'high-opacity-colored','layers':[{'rgba':[1,0,0,.75],'z':0},{'rgba':[0,1,0,.5],'z':1},{'rgba':[0,0,1,.25],'z':3}]}]
def half(x):return struct.unpack('e',struct.pack('e',x))[0]
def q(x):return max(0,min(255,math.floor(x*255+.5)))
def oracle(layers,order,negative=None):
 a=[0.]*4;r=1.
 for index in order:
  if negative=='missing_layer' and index==1:continue
  c=layers[index]['rgba'];w=1/(1+layers[index]['z']);term=[half(x*c[3]*w) for x in c[:3]]+[half(c[3]*w)]
  a=[half(x+y) for x,y in zip(a,term)];r=half(r*(1-c[3])) if negative!='wrong_revealage' else half(r+c[3])
 return [q(x/max(a[3],.0001)*(1-r)) for x in a[:3]]+[q(1-r)]
def sorted_oracle(layers):
 p=[0.]*4
 for l in sorted(layers,key=lambda l:l['z'],reverse=True):
  c=l['rgba'];p=[half(c[i]*c[3]+p[i]*(1-c[3])) for i in range(3)]+[half(c[3]+p[3]*(1-c[3]))]
 return [q(x) for x in p]
def error(pixels,pixel):return max(abs(a-b) for a,b in zip(pixels,pixel*16)) if len(pixels)==64 else None

def run(config):
 h=d.Host(config);textures=[];fbos=[];programs=[];vao=U();counts={'draws':0,'readbacks':0}
 report={'schema_version':1,'status':'FAIL','execution_class':'SOFTWARE_HOST','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'shader_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in [('vertex',V),('accum',ACCUM),('reveal',REVEAL),('resolve',RESOLVE),('sorted',SORTED)]},'physical_device':'NOT_RUN','performance':'NOT_MEASURED','scenes':[]}
 def check():
  e=h.error()
  if e:raise RuntimeError('GL_ERROR_'+str(e))
 def bind(f):h.fn('glBindFramebuffer',None,[U,U])(0x8d40,f)
 def target(fmt):
  t=U();f=U();h.fn('glGenTextures',None,[I,P])(1,C.byref(t));textures.append(t);h.fn('glBindTexture',None,[U,U])(0xde1,t);h.fn('glTexStorage2D',None,[U,I,U,I,I])(0xde1,1,fmt,4,4)
  for param in (0x2801,0x2800):h.fn('glTexParameteri',None,[U,U,I])(0xde1,param,0x2600)
  h.fn('glGenFramebuffers',None,[I,P])(1,C.byref(f));fbos.append(f);bind(f);h.fn('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0,0xde1,t,0)
  if h.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('RGBA16F_NOT_RENDERABLE')
  check();return t,f
 def program(src):
  p,obs=h.program({'shader.vert':V,'shader.frag':src});programs.append(p)
  if not obs['compile'] or not obs['link']:raise RuntimeError('SHADER_FAILED')
  return p
 def clear(f,v):bind(f);h.fn('glClearColor',None,[F]*4)(v,v,v,v);h.fn('glClear',None,[U])(0x4000)
 def draw(p,layer):
  h.fn('glUseProgram',None,[U])(p);loc=h.fn('glGetUniformLocation',I,[U,C.c_char_p])(p,b'layer');h.fn('glUniform4f',None,[I,F,F,F,F])(loc,*layer['rgba']);loc=h.fn('glGetUniformLocation',I,[U,C.c_char_p])(p,b'weight');h.fn('glUniform1f',None,[I,F])(loc,1/(1+layer['z']));h.fn('glDrawArrays',None,[U,I,I])(4,0,3);counts['draws']+=1
 def resolve(a,r,copy=False):
  bind(final[1]);h.fn('glDisable',None,[U])(0xbe2);h.fn('glUseProgram',None,[U])(resolve_p)
  for unit,tex,name in [(0,a,b'accum'),(1,r,b'reveal')]:
   h.fn('glActiveTexture',None,[U])(0x84c0+unit);h.fn('glBindTexture',None,[U,U])(0xde1,tex);loc=h.fn('glGetUniformLocation',I,[U,C.c_char_p])(resolve_p,name);h.fn('glUniform1i',None,[I,I])(loc,unit)
  loc=h.fn('glGetUniformLocation',I,[U,C.c_char_p])(resolve_p,b'copyOnly');h.fn('glUniform1i',None,[I,I])(loc,int(copy));h.fn('glDrawArrays',None,[U,I,I])(4,0,3);counts['draws']+=1
  pixels=(C.c_ubyte*64)();h.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,pixels);check();counts['readbacks']+=1;return list(pixels)
 try:
  report['format_capability']={x:x in h.metadata['extensions'] for x in ('GL_EXT_color_buffer_float','GL_EXT_color_buffer_half_float')}
  if not any(report['format_capability'].values()):report['status']='UNSUPPORTED_FORMAT';return report
  for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):h.fn('glDisable',None,[U])(cap)
  h.fn('glViewport',None,[I]*4)(0,0,4,4);h.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));h.fn('glBindVertexArray',None,[U])(vao)
  accum=target(0x881a);reveal=target(0x881a);sort=target(0x881a);final=target(0x8058)
  accum_p=program(ACCUM);reveal_p=program(REVEAL);sorted_p=program(SORTED);resolve_p=program(RESOLVE)
  # Verify actual half-float additive blending and fetch, not extension string alone.
  clear(accum[1],0);h.fn('glEnable',None,[U])(0xbe2);h.fn('glBlendFunc',None,[U,U])(1,1)
  probe={'rgba':[.25,.5,.75,1],'z':0};draw(accum_p,probe);draw(accum_p,probe);probe_pixels=resolve(accum[0],accum[0],True);report['blend_probe']={'pixels':probe_pixels,'expected':[128,255,255,255]*16,'max_error':error(probe_pixels,[128,255,255,255])}
  if report['blend_probe']['max_error'] is None or report['blend_probe']['max_error']>1:raise RuntimeError('RGBA16F_BLEND_PROBE_FAILED')
  for scene in SCENES:
   layers=scene['layers'];clear(sort[1],0);h.fn('glEnable',None,[U])(0xbe2);h.fn('glBlendFuncSeparate',None,[U]*4)(0x302,0x303,1,0x303)
   for layer in sorted(layers,key=lambda x:x['z'],reverse=True):draw(sorted_p,layer)
   sortedpixels=resolve(sort[0],sort[0],True);base=sorted_oracle(layers);baseline={'pixels':sortedpixels,'cpu_oracle':base,'max_error':error(sortedpixels,base)};rows=[]
   for order,negative in [(o,None) for o in itertools.permutations(range(3))]+[((0,1,2),'wrong_revealage'),((0,1,2),'missing_layer')]:
    clear(accum[1],0);h.fn('glEnable',None,[U])(0xbe2);h.fn('glBlendFunc',None,[U,U])(1,1)
    for i in order:
     if not (negative=='missing_layer' and i==1):draw(accum_p,layers[i])
    clear(reveal[1],1);h.fn('glEnable',None,[U])(0xbe2);h.fn('glBlendFunc',None,[U,U])(1,1) if negative=='wrong_revealage' else h.fn('glBlendFunc',None,[U,U])(0,0x303)
    for i in order:
     if not (negative=='missing_layer' and i==1):draw(reveal_p,layers[i])
    pixels=resolve(accum[0],reveal[0]);cpu=oracle(layers,order,negative);normal=oracle(layers,order);e=error(pixels,cpu)
    rows.append({'order':list(order),'negative':negative,'pixels':pixels,'cpu_oracle':cpu,'algorithm_error':e,'algorithm_pass':e is not None and e<=1,'deviation_from_sorted':error(pixels,base),'negative_rejected':error(pixels,normal)>2 if negative else None})
   normal=[r for r in rows if r['negative'] is None];quality_pass=all(r['deviation_from_sorted']<=2 for r in normal);baseline_pass=baseline['max_error'] is not None and baseline['max_error']<=1
   report['scenes'].append({'id':scene['id'],'layers':layers,'sorted_baseline':baseline,'rows':rows,'permutation_max_difference':max(max(abs(a-b) for a,b in zip(normal[0]['pixels'],r['pixels'])) for r in normal),'quality_tolerance_bytes':2,'quality_status':'PASS' if quality_pass else 'REJECTED_APPROXIMATION','selection':'OIT' if quality_pass else 'SORTED_ALPHA' if baseline_pass else 'UNAVAILABLE'})
  report['status']='HOST_CONTRACT_PASS' if all(s['sorted_baseline']['max_error']<=1 and all(r['algorithm_pass'] and (r['negative'] is None or r['negative_rejected']) for r in s['rows']) and s['permutation_max_difference']<=1 for s in report['scenes']) else 'FAIL'
  report['actual_execution_counts']=counts
  report['cost_model']={'per_3_layer_oit_variant':{'geometry_draws':6,'resolve_draws':1,'color_clears':2,'readbacks':1},'per_sorted_baseline':{'geometry_draws':3,'copy_resolve_draws':1},'oit_render_target_bytes_per_pixel':20,'oit_targets':'RGBA16F accum8 + RGBA16F reveal8 + RGBA8 output4','extra_baseline_target_bytes_per_pixel':8,'nominal_geometry_attachment_rw_bytes_per_pixel':96,'bandwidth_counter_measured':False,'note':'96=6fragment layers*8byte target*(read+write); excludes resolves/clears, compression/caches and tile fusion. This is accounting, not physical DRAM traffic.'}
 finally:
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
 except Exception as e:r={'status':'FAIL','diagnostic':str(e) if str(e).startswith(('GL_ERROR_','SHADER_','RGBA16F_')) else type(e).__name__}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(0 if r['status']=='HOST_CONTRACT_PASS' else 77 if r['status']=='UNSUPPORTED_FORMAT' else 1)
