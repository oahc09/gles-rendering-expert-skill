#!/usr/bin/env python3
"""Authored NV12 shader fusion, not decoder/native video evidence."""
import argparse,ctypes as C,hashlib,importlib.util,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('video_host',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
U=d.U;I=d.I;P=d.P
VERT='#version 300 es\nvoid main(){vec2 p=vec2(float((gl_VertexID<<1)&2),float(gl_VertexID&2));gl_Position=vec4(p*2.-1.,0.,1.);}'
META={'width':4,'height':4,'y_stride':6,'uv_stride':6,'matrix':'BT709','range':'limited','siting':'centered','reconstruction':'nearest-block'}
def authored(frame):
 y=[40+20*x+17*j+frame*9 for j in range(4) for x in range(4)];uv=[80,180,170,90,110,160,190,70]
 return [v for row in range(4) for v in y[row*4:row*4+4]+[231,232]], [v for row in range(2) for v in uv[row*4:row*4+4]+[233,234]]
def validate(meta,y,uv):
 if type(meta) is not dict or set(meta)!=set(META):raise ValueError('metadata fields')
 for k in ['width','height','y_stride','uv_stride']:
  if type(meta[k]) is not int:raise ValueError('integer dimensions/strides')
 if meta['width']!=4 or meta['height']!=4 or not 4<=meta['y_stride']<=64 or not 4<=meta['uv_stride']<=64:raise ValueError('finite layout')
 for k in ['matrix','range','siting','reconstruction']:
  if meta[k]!=META[k]:raise ValueError('unsupported metadata')
 for data,stride,rows in [(y,meta['y_stride'],4),(uv,meta['uv_stride'],2)]:
  if type(data) is not list or len(data)!=stride*rows or any(type(v) is not int or not 0<=v<=255 for v in data):raise ValueError('plane bounds/bytes')
 return [y[j*meta['y_stride']+x] for j in range(4) for x in range(4)],[uv[j*meta['uv_stride']+x] for j in range(2) for x in range(4)]
def rgb_cpu(y,u,v):
 yy=(y-16)/219;cb=(u-128)/224;cr=(v-128)/224
 # Independent expanded BT.709 inverse coefficients, not importing shader/policy.
 return [min(1,max(0,c)) for c in (yy+1.5748*cr,yy-0.1873242729306488*cb-0.4681242729306488*cr,yy+1.8556*cb)]
def quant(v):return max(0,min(255,int(math.floor(v*255+.5))))
def oracle(y,uv):
 result=[];base=[]
 for j in range(4):
  for x in range(4):
   idx=((j//2)*2+x//2)*2;c=rgb_cpu(y[j*4+x],uv[idx],uv[idx+1]);base+=list(map(quant,c))+[255];a=.25 if x<2 else .5;ui=[.8,.2,.4];result += [quant(c[k]*(1-a)+ui[k]*a) for k in range(3)]+[255]
 return result,base
FRAG='''#version 300 es
precision highp float;
uniform sampler2D yp;uniform sampler2D uvp;uniform sampler2D rgba;uniform int mode;
out vec4 color;
void main(){ivec2 p=ivec2(gl_FragCoord.xy);vec3 c;
if(mode==1){c=texelFetch(rgba,p,0).rgb;}else{
 float code=texelFetch(yp,p,0).r*255.;vec2 cc=texelFetch(uvp,p/2,0).rg*255.;if(mode==3)cc=cc.yx;
 float y=mode==2?code/255.:(code-16.)/219.;vec2 chroma=(cc-128.)/(mode==2?255.:224.);
 float r=y+2.*(1.-.2126)*chroma.y;float b=y+2.*(1.-.0722)*chroma.x;float g=(y-.2126*r-.0722*b)/(1.-.2126-.0722);c=clamp(vec3(r,g,b),0.,1.);}
 float a=p.x<2?.25:.5;color=vec4(c*(1.-a)+vec3(.8,.2,.4)*a,1.);}
'''
def run(config):
 # Preflight invalid inputs before a Host/context/draw exists.
 rejected=[]
 for name,change in [('missing-stride',lambda m:m.pop('y_stride')),('unsupported-matrix',lambda m:m.update(matrix='BT601')),('unsupported-siting',lambda m:m.update(siting='cosited')),('short-stride',lambda m:m.update(uv_stride=3))]:
  meta=dict(META);change(meta)
  try:validate(meta,*authored(0));raise RuntimeError('INVALID_INPUT_ACCEPTED')
  except ValueError:rejected.append({'case':name,'status':'REJECTED_PREFLIGHT','draws':0})
 h=d.Host(config);textures=(U*3)();program=0
 r={'schema_version':1,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'status':'FAIL','execution_class':'SOFTWARE_HOST','native_video':'NOT_RUN','decoder':'NOT_RUN','AHardwareBuffer':'NOT_RUN','physical_device':'NOT_RUN','performance':'NOT_MEASURED','metadata':META,'preflight_rejections':rejected,'frames':[]}
 try:
  program,info=h.program({'shader.vert':VERT,'shader.frag':FRAG})
  if not(info['compile'] and info['link']):raise RuntimeError('SHADER_FAILED')
  h.fn('glGenTextures',None,[I,P])(3,textures);h.fn('glPixelStorei',None,[U,I])(0xcf5,1)
  for frame in [0,1]:
   yp,uvp=validate(dict(META),*authored(frame));expected,base=oracle(yp,uvp)
   for unit,(w,hei,internal,fmt,data) in enumerate([(4,4,0x8229,0x1903,yp),(2,2,0x822b,0x8227,uvp),(4,4,0x8058,0x1908,base)]):
    h.fn('glActiveTexture',None,[U])(0x84c0+unit);h.fn('glBindTexture',None,[U,U])(0xde1,textures[unit]);raw=(C.c_ubyte*len(data))(*data);h.fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,internal,w,hei,0,fmt,0x1401,raw)
    for pname,val in [(0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812f),(0x2803,0x812f)]:h.fn('glTexParameteri',None,[U,U,I])(0xde1,pname,val)
   h.fn('glUseProgram',None,[U])(program)
   for unit,name in enumerate([b'yp',b'uvp',b'rgba']):h.fn('glUniform1i',None,[I,I])(h.fn('glGetUniformLocation',I,[U,C.c_char_p])(program,name),unit)
   for mode,name in enumerate(['gpu-nv12','cpu-rgba-fallback','wrong-range','uv-swap']):
    h.fn('glUniform1i',None,[I,I])(h.fn('glGetUniformLocation',I,[U,C.c_char_p])(program,b'mode'),mode);h.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);h.fn('glViewport',None,[I,I,I,I])(0,0,4,4)
    for state in [0xbd0,0xbe2,0xb71]:h.fn('glDisable',None,[U])(state)
    h.fn('glDrawArrays',None,[U,I,I])(4,0,3);out=(C.c_ubyte*64)();h.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,out)
    if h.error():raise RuntimeError('GL_ERROR')
    error=max(abs(a-b) for a,b in zip(out,expected));r['frames'].append({'frame':frame,'mode':name,'pixels':list(out),'cpu_expected':expected,'max_byte_error':error,'decision':'ACCEPTED' if error<=2 else 'REJECTED_QUALITY'})
  ok=all((x['max_byte_error']<=2)==(x['mode'] in ['gpu-nv12','cpu-rgba-fallback']) for x in r['frames']);r.update(status='HOST_PASS' if ok else 'FAIL',draws=8,readbacks=8,quality_budget=2,texture_bytes=88,output_bytes=64);return r
 finally:
  h.fn('glUseProgram',None,[U])(0)
  if program:h.fn('glDeleteProgram',None,[U])(program)
  h.fn('glDeleteTextures',None,[I,P])(3,textures);h.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 try:r=run(json.loads(a.config.read_text()))
 except Exception as e:r={'status':'FAIL','error_class':type(e).__name__}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(0 if r['status']=='HOST_PASS' else 1)
