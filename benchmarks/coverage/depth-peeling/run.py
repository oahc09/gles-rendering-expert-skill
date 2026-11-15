#!/usr/bin/env python3
"""Finite depth-texture peeling with overflow rejection, not unbounded transparency."""
import argparse,ctypes as C,hashlib,importlib.util,itertools,json,math,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('peel_host',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
U=d.U;I=d.I;F=d.F;P=d.P
V='#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}'
FRAG='#version 300 es\nprecision highp float;uniform highp sampler2D previousDepth;uniform int firstPass;uniform int wrongDepth;uniform vec2 plane;uniform vec4 rgba;out vec4 color;void main(){float z=floor((plane.x+plane.y*gl_FragCoord.x)*4096.0+0.5)/4096.0;if(firstPass==0 && wrongDepth==0 && z<=texelFetch(previousDepth,ivec2(gl_FragCoord.xy),0).r)discard;gl_FragDepth=z;color=vec4(rgba.rgb*rgba.a,rgba.a);}'
COMPOSE='#version 300 es\nprecision highp float;uniform sampler2D peeled;out vec4 color;void main(){color=texelFetch(peeled,ivec2(gl_FragCoord.xy),0);}'
LAYERS=[{'plane':[.1,.2],'rgba':[1,0,0,.5]},{'plane':[.9,-.2],'rgba':[0,0,1,.5]},{'plane':[.45,0],'rgba':[0,1,0,.25]}]
def depths(l):return [l['plane'][0]+l['plane'][1]*(x+.5) for y in range(4) for x in range(4)]
def validate(layers):
 if not isinstance(layers,list) or not layers or any(not isinstance(l,dict) for l in layers):return 'INVALID_INPUT'
 if any(not isinstance(l.get('plane'),list) or not isinstance(l.get('rgba'),list) for l in layers):return 'INVALID_INPUT'
 if any(len(l.get('plane',[]))!=2 or len(l.get('rgba',[]))!=4 for l in layers):return 'INVALID_INPUT'
 if any(type(v) not in (float,int) or not math.isfinite(v) for l in layers for v in l['plane']+l['rgba']):return 'INVALID_INPUT'
 if any(not -1<=v<=1 for l in layers for v in l['plane']):return 'INVALID_PLANE_RANGE'
 z=[depths(l) for l in layers]
 f32=lambda v:struct.unpack('f',struct.pack('f',v))[0]
 for l in layers:
  a,b=map(f32,l['plane'])
  for x in range(4):
   raw=l['plane'][0]+l['plane'][1]*(x+.5);paths=[raw,f32(a+f32(b*(x+.5))),f32(a+b*(x+.5))];bins=[math.floor(v*4096+.5) for v in paths]
   if any(not 0<=q<4096 for q in bins):return 'QUANTIZED_DEPTH_OUT_OF_RANGE'
   if len(set(bins))!=1 or any(abs((v*4096)%1-.5)<.001 for v in paths):return 'UNSAFE_QUANTIZATION_BOUNDARY'
 if any(not 0<=v<1 for row in z for v in row) or any(not 0<=v<=1 for l in layers for v in l['rgba']):return 'INVALID_RANGE'
 if any(math.floor(a*4096+.5)==math.floor(b*4096+.5) for i in range(len(z)) for j in range(i) for a,b in zip(z[i],z[j])):return 'AMBIGUOUS_TIE_OR_DEPTH_GAP'
 return 'VALID'
def oracle(layers):
 out=[]
 for pixel in range(16):
  c=[0.]*4
  for l in sorted(layers,key=lambda l:depths(l)[pixel],reverse=True):
   r=l['rgba'];c=[r[i]*r[3]+c[i]*(1-r[3]) for i in range(3)]+[r[3]+c[3]*(1-r[3])]
  out.extend(round(v*255) for v in c)
 return out

def run(config):
 h=d.Host(config);textures=[];fbos=[];programs=[];vao=U();query=U();counts={'geometry_draws':0,'compose_draws':0,'readbacks':0,'occlusion_queries':0}
 r={'schema_version':1,'status':'FAIL','execution_class':'SOFTWARE_HOST','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'physical_device':'NOT_RUN','performance':'NOT_MEASURED','cases':[],'layers':LAYERS}
 def check():
  e=h.error()
  if e:raise RuntimeError('GL_ERROR_'+str(e))
 def texture(fmt):
  t=U();h.fn('glGenTextures',None,[I,P])(1,C.byref(t));textures.append(t);h.fn('glBindTexture',None,[U,U])(0xde1,t);h.fn('glTexStorage2D',None,[U,I,U,I,I])(0xde1,1,fmt,4,4)
  for pn,v in ((0x2800,0x2600),(0x2801,0x2600),(0x2802,0x812f),(0x2803,0x812f)):h.fn('glTexParameteri',None,[U,U,I])(0xde1,pn,v)
  return t
 def fbo(color,depth=None):
  f=U();h.fn('glGenFramebuffers',None,[I,P])(1,C.byref(f));fbos.append(f);h.fn('glBindFramebuffer',None,[U,U])(0x8d40,f);h.fn('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0,0xde1,color,0)
  if depth:h.fn('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8d00,0xde1,depth,0)
  if h.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FORMAT_UNSUPPORTED')
  check();return f
 def program(src):
  p,o=h.program({'shader.vert':V,'shader.frag':src});programs.append(p)
  if not o['compile'] or not o['link']:raise RuntimeError('SHADER_FAILED')
  return p
 def uniform(p,name,fn,args,vals):
  loc=h.fn('glGetUniformLocation',I,[U,C.c_char_p])(p,name.encode());h.fn(fn,None,[I]+args)(loc,*vals)
 def read(f):
  h.fn('glBindFramebuffer',None,[U,U])(0x8d40,f);b=(C.c_ubyte*64)();h.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,b);check();counts['readbacks']+=1;return list(b)
 try:
  for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):h.fn('glDisable',None,[U])(cap)
  h.fn('glViewport',None,[I]*4)(0,0,4,4);h.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));h.fn('glBindVertexArray',None,[U])(vao);h.fn('glGenQueries',None,[I,P])(1,C.byref(query))
  precision=I();ranges=(I*2)();h.fn('glGetShaderPrecisionFormat',None,[U,U,P,P])(0x8b30,0x8df2,ranges,C.byref(precision));r['fragment_highp']={'precision':precision.value,'range':list(ranges)}
  if precision.value<23:raise RuntimeError('INSUFFICIENT_HIGHP_PRECISION')
  r['depth_domain']={'storage':'DEPTH_COMPONENT32F','quantum':1/4096,'shader':'floor(z*4096+0.5)/4096','comparison':'z_quantized <= previousDepth; no epsilon','ties':'reject equal quantized depth bins'}
  ma=I();h.fn('glGetIntegerv',None,[U,P])(0x8872,C.byref(ma));r['max_texture_image_units']=ma.value
  if ma.value<1:raise RuntimeError('INSUFFICIENT_TEXTURE_UNITS')
  colors=[texture(0x8058),texture(0x8058)];zs=[texture(0x8cac),texture(0x8cac)];peels=[fbo(colors[i],zs[i]) for i in range(2)];accum=fbo(texture(0x8058));p=program(FRAG);compose=program(COMPOSE);r['formats']={'peel_color':'RGBA8','peel_depth':'DEPTH_COMPONENT32F','accum':'RGBA8','framebuffer_complete':True}
  scenarios=[('three-'+''.join(map(str,o)),LAYERS,o,3,None) for o in itertools.permutations(range(3))]+[('two-crossing',LAYERS[:2],(1,0),2,None),('budget-overflow',LAYERS,(0,1,2),2,None),('missing-layer',LAYERS,(0,1,2),3,'missing_layer'),('wrong-depth',LAYERS,(0,1,2),3,'wrong_depth')]
  scenarios += [('tie-input',[LAYERS[0],LAYERS[0]],(0,1),2,None),('same-bin-input',[{'plane':[.5,0],'rgba':[1,0,0,.5]},{'plane':[.500001,0],'rgba':[0,0,1,.5]}],(0,1),2,None),('malformed-input',[{'plane':None,'rgba':[1,0,0,.5]}],(0,),1,None),('rounded-clear-depth',[{'plane':[.99999,0],'rgba':[1,0,0,.5]}],(0,),1,None),('bin-boundary',[{'plane':[.5001220703125,0],'rgba':[1,0,0,.5]}],(0,),1,None)]
  r['rejected_before_draw']=[]
  for name,layers,order,budget,negative in scenarios:
   admission=validate(layers)
   if admission!='VALID':
    r['rejected_before_draw'].append({'id':name,'reason':admission,'decision':'REJECT','geometry_draws':0,'compose_draws':0,'readbacks':0});continue
   h.fn('glBindFramebuffer',None,[U,U])(0x8d40,accum);h.fn('glClearColor',None,[F]*4)(0,0,0,0);h.fn('glClear',None,[U])(0x4000);stages=[];occupied=[]
   for stage in range(budget+1):
    current=stage%2;prior=1-current;h.fn('glBindFramebuffer',None,[U,U])(0x8d40,peels[current]);h.fn('glDisable',None,[U])(0xbe2);h.fn('glEnable',None,[U])(0xb71);h.fn('glDepthFunc',None,[U])(0x201);h.fn('glDepthMask',None,[C.c_ubyte])(1);h.fn('glClearDepthf',None,[F])(1);h.fn('glClearColor',None,[F]*4)(0,0,0,0);h.fn('glClear',None,[U])(0x4100)
    h.fn('glUseProgram',None,[U])(p);h.fn('glActiveTexture',None,[U])(0x84c0);h.fn('glBindTexture',None,[U,U])(0xde1,zs[prior]);uniform(p,'previousDepth','glUniform1i',[I],[0]);uniform(p,'firstPass','glUniform1i',[I],[int(stage==0)]);uniform(p,'wrongDepth','glUniform1i',[I],[int(negative=='wrong_depth')]);h.fn('glBeginQuery',None,[U,U])(0x8c2f,query)
    for i in order:
     if negative=='missing_layer' and i==1:continue
     uniform(p,'plane','glUniform2f',[F,F],layers[i]['plane']);uniform(p,'rgba','glUniform4f',[F]*4,layers[i]['rgba']);h.fn('glDrawArrays',None,[U,I,I])(4,0,3);counts['geometry_draws']+=1
    h.fn('glEndQuery',None,[U])(0x8c2f);result=U();h.fn('glGetQueryObjectuiv',None,[U,U,P])(query,0x8866,C.byref(result));check();occupied.append(bool(result.value));counts['occlusion_queries']+=1
    if stage==budget:break
    stages.append(read(peels[current]));h.fn('glBindFramebuffer',None,[U,U])(0x8d40,accum);h.fn('glDisable',None,[U])(0xb71);h.fn('glEnable',None,[U])(0xbe2);h.fn('glBlendFunc',None,[U,U])(0x305,1);h.fn('glUseProgram',None,[U])(compose);h.fn('glBindTexture',None,[U,U])(0xde1,colors[current]);uniform(compose,'peeled','glUniform1i',[I],[0]);h.fn('glDrawArrays',None,[U,I,I])(4,0,3);counts['compose_draws']+=1;check()
   pixels=read(accum);truth=oracle(layers);err=max(abs(a-b) for a,b in zip(pixels,truth));overflow=occupied[-1];admission=validate(layers);accepted=admission=='VALID' and not overflow and err<=2
   r['cases'].append({'id':name,'input_order':list(order),'layer_budget':budget,'input_validation':admission,'negative':negative,'peeled_color_stages':stages,'query_any_samples':occupied,'overflow':overflow,'pixels':pixels,'cpu_per_pixel_over':truth,'max_error':err,'decision':'ACCEPT_FINITE_SAMPLE' if accepted else 'REJECT','reject_reason':'LAYER_BUDGET_OVERFLOW' if overflow else 'QUALITY' if err>2 else admission})
  r['tie_policy']={'decision':validate([LAYERS[0],LAYERS[0]]),'action':'Reject before rendering; no invented tie ordering'}
  positives=[x for x in r['cases'] if x['negative'] is None and x['id']!='budget-overflow'];negatives=[x for x in r['cases'] if x not in positives]
  first=positives[0]['pixels'];r['permutation_max_difference']=max(max(abs(a-b) for a,b in zip(first,x['pixels'])) for x in positives[:6]);r['actual_counts']=counts
  r['status']='HOST_PASS' if all(x['decision']=='ACCEPT_FINITE_SAMPLE' for x in positives) and all(x['decision']=='REJECT' for x in negatives) and r['permutation_max_difference']<=2 and r['tie_policy']['decision']=='AMBIGUOUS_TIE_OR_DEPTH_GAP' else 'FAIL'
  r['cost']={'allocated_bytes_per_pixel':20,'description':'2 ping-pong*(RGBA8 color4+DEPTH32F4)+RGBA8 accumulator4','for_N_layers_budget_K':'(K+1)*N geometry draws including overflow proof +K composition draws; K+1 depth/color clears; synchronous query/readback costs included, not performance measurement','original_oit_reports':'UNCHANGED'}
 finally:
  h.fn('glUseProgram',None,[U])(0);h.fn('glBindFramebuffer',None,[U,U])(0x8d40,0)
  if query.value:h.fn('glDeleteQueries',None,[I,P])(1,C.byref(query))
  for p in programs:h.fn('glDeleteProgram',None,[U])(p)
  for f in fbos:h.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(f))
  for t in textures:h.fn('glDeleteTextures',None,[I,P])(1,C.byref(t))
  if vao.value:h.fn('glDeleteVertexArrays',None,[I,P])(1,C.byref(vao))
  h.close()
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 try:r=run(json.loads(a.config.read_text()))
 except Exception as e:r={'status':'FAIL','diagnostic':str(e) if str(e).startswith(('GL_ERROR','FORMAT_','SHADER_','INSUFFICIENT')) else type(e).__name__}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(0 if r['status']=='HOST_PASS' else 1)
