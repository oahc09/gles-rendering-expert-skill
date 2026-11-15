#!/usr/bin/env python3
"""Projected billboard GLES controls, not a trained 3DGS renderer or performance test."""
import argparse,ctypes as C,hashlib,importlib.util,json,math,os,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('overlap_diff',ROOT/'benchmarks/differential/run.py');diff=importlib.util.module_from_spec(spec);spec.loader.exec_module(diff)
U,I,P,F=diff.U,diff.I,diff.P,diff.F
SIZE=64
VERT='''#version 300 es
precision highp float;
uniform vec4 rect;
out vec2 local;
void main(){
 vec2 p[6]=vec2[6](vec2(-1,-1),vec2(1,-1),vec2(-1,1),vec2(-1,1),vec2(1,-1),vec2(1,1));
 local=p[gl_VertexID];gl_Position=vec4(rect.xy+local*(rect.zw+vec2(0.03125)),0,1);
}
'''
FRAG='''#version 300 es
precision highp float;
in vec2 local;uniform vec4 rect;uniform vec4 tint;uniform int mode;
layout(location=0) out vec4 color;
void main(){vec2 point=(gl_FragCoord.xy/64.0*2.0-1.0-rect.xy)/rect.zw;
 if(any(greaterThanEqual(abs(point),vec2(1.0)))){discard;}
 float a=tint.a;
 if(mode==0){a*=exp(-3.0*dot(point,point));}
 if(mode==1 && dot(point,point)>1.0){discard;}
 if(mode==2){a*=0.6+0.4*abs(point.x);}
 color=vec4(tint.rgb,a);
}
'''
def scenes():
 out=[]
 for name,mode,n in [('projected-gaussians',0,18),('transparent-particles',1,15),('layered-glass',2,8),('layered-ui',3,10)]:
  objects=[]
  for i in range(n):
   objects.append(dict(id=i,x=((i%5)-2)*.19,y=((i//5)-1)*.18,z=2.2+(i%4)*.35,radius=.40 if mode!=3 else .28,color=[.15+(i%3)*.3,.2+(i%4)*.18,.75-(i%3)*.2,.22+(i%3)*.08],mode=mode))
  # Visible object culling must retain all foreground silhouettes; these two are unambiguously offscreen.
  objects.extend([dict(id=n+j,x=10+j,y=0,z=2,radius=.1,color=[1,0,0,.5],mode=mode) for j in range(2)])
  out.append(dict(id=name,objects=sorted(objects,key=lambda o:o['z'],reverse=True)))
 return out

def project(obj,camera):
 # Perspective pinhole, 90 degree vertical FOV, camera translates along world X.
 return [(obj['x']-camera)/obj['z'],obj['y']/obj['z'],obj['radius']/obj['z'],obj['radius']/obj['z']]

def visible(obj,camera):
 x,y,w,h=project(obj,camera)
 return x+w>-1 and x-w<1 and y+h>-1 and y-h<1

def arms(scene,camera):
 base=scene['objects'];culled=[o for o in base if visible(o,camera)]
 # Deliberately unsafe foreground removal, not advertised as an optimization.
 bad=[o for o in culled if o['id']%3!=0]
 return {'baseline':base,'offscreen_culling':culled,'bad_foreground_drop':bad}

def cpu(objects,camera):
 pixels=[0]*(SIZE*SIZE*4);heat=[0]*(SIZE*SIZE)
 for o in objects:
  cx,cy,rx,ry=project(o,camera)
  for y in range(SIZE):
   v=((y+.5)/SIZE*2-1-cy)/ry
   if not -1<v<1:continue
   for x in range(SIZE):
    u=((x+.5)/SIZE*2-1-cx)/rx
    if not -1<u<1:continue
    q=u*u+v*v
    if o['mode']==1 and q>1:continue
    a=o['color'][3]
    if o['mode']==0:a*=math.exp(-3*q)
    if o['mode']==2:a*=.6+.4*abs(u)
    idx=(y*SIZE+x)*4;heat[y*SIZE+x]+=1
    for k in range(4):
     value=(o['color'][k]*a if k<3 else a)+pixels[idx+k]/255*(1-a)
     pixels[idx+k]=math.floor(min(1,max(0,value))*255+.5)
 return pixels,heat

class Host(diff.Host):
 def draw(self,objects,camera):
  fb=U();rb=U();vao=U();prog=0
  try:
   prog,compile_info=self.program({'shader.vert':VERT,'shader.frag':FRAG})
   if not compile_info['compile'] or not compile_info['link']:raise RuntimeError('shader compile/link failure')
   self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb)
   self.fn('glGenRenderbuffers',None,[I,P])(1,C.byref(rb));self.fn('glBindRenderbuffer',None,[U,U])(0x8d41,rb)
   self.fn('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,SIZE,SIZE);self.fn('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,rb)
   if self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO incomplete')
   for cap in (0xbd0,0xb71,0xb90,0xc11,0xb44):self.fn('glDisable',None,[U])(cap)
   self.fn('glEnable',None,[U])(0xbe2);self.fn('glBlendFuncSeparate',None,[U]*4)(0x302,0x303,1,0x303)
   self.fn('glViewport',None,[I]*4)(0,0,SIZE,SIZE);self.fn('glClearColor',None,[F]*4)(0,0,0,0);self.fn('glClear',None,[U])(0x4000)
   self.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));self.fn('glBindVertexArray',None,[U])(vao);self.fn('glUseProgram',None,[U])(prog)
   loc={n:self.fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,n.encode()) for n in ('rect','tint','mode')}
   for o in objects:
    self.fn('glUniform4f',None,[I,F,F,F,F])(loc['rect'],*project(o,camera));self.fn('glUniform4f',None,[I,F,F,F,F])(loc['tint'],*o['color'])
    self.fn('glUniform1i',None,[I,I])(loc['mode'],o['mode']);self.fn('glDrawArrays',None,[U,I,I])(4,0,6)
   buf=(C.c_ubyte*(SIZE*SIZE*4))();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,SIZE,SIZE,0x1908,0x1401,buf)
   if self.error():raise RuntimeError('GL operation failed')
   return list(buf)
  finally:
   self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindVertexArray',None,[U])(0)
   if prog:self.fn('glDeleteProgram',None,[U])(prog)
   if vao.value:self.fn('glDeleteVertexArrays',None,[I,P])(1,C.byref(vao))
   if rb.value:self.fn('glDeleteRenderbuffers',None,[I,P])(1,C.byref(rb))
   if fb.value:self.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(fb))

def metrics(actual,golden):
 if len(actual)!=SIZE*SIZE*4 or len(golden)!=len(actual):raise ValueError('image size')
 if any(type(v)is not int or not 0<=v<=255 for v in actual+golden):raise ValueError('RGBA8 input')
 errors=[abs(a-b) for a,b in zip(actual,golden)]
 masks=[sum((actual[i+3]>12)!=(golden[i+3]>12) for i in range(0,len(actual),4))]
 def centroid(p):
  total=sum(p[3::4]);return None if total==0 else sum((i%SIZE+.5)*a for i,a in enumerate(p[3::4]))/total
 ca,cg=centroid(actual),centroid(golden)
 return dict(max_rgba8_error=max(errors),mean_rgba8_error=sum(errors)/len(errors),silhouette_disagree_pixels=masks[0],alpha_centroid_x=ca,cpu_alpha_centroid_x=cg,centroid_error_pixels=abs(ca-cg) if ca is not None and cg is not None else None)

def run(config,output):
 report_path=Path(output);report_path.parent.mkdir(parents=True,exist_ok=True)
 out=report_path.parent/(report_path.stem+'-images');out.mkdir(parents=True,exist_ok=True);h=Host(config);rows=[]
 try:
  for s in scenes():
   for camera in (-.3,0,.3):
    variants=arms(s,camera);gold,heat=cpu(variants['baseline'],camera);baseline=None
    golden_name=s['id']+'-'+str(camera)+'-cpu.rgba';(out/golden_name).write_bytes(bytes(gold))
    for name,objects in variants.items():
     pixels=h.draw(objects,camera)
     if name=='baseline':baseline=pixels
     m=metrics(pixels,gold);quality='PASS' if m['max_rgba8_error']<=4 and m['silhouette_disagree_pixels']<=2 and m['centroid_error_pixels'] is not None and m['centroid_error_pixels']<=.1 else 'FAIL'
     if name=='offscreen_culling' and pixels!=baseline:quality='FAIL'
     stem=s['id']+'-'+str(camera)+'-'+name
     (out/(stem+'.rgba')).write_bytes(bytes(pixels))
     rows.append(dict(scene=s['id'],camera_x=camera,variant=name,expected='FAIL' if name.startswith('bad_') else 'PASS',quality=quality,metrics=m,draw_count=len(objects),baseline_pixel_identical=pixels==baseline,image=out.name+'/'+stem+'.rgba',image_sha256=hashlib.sha256(bytes(pixels)).hexdigest(),cpu_golden=out.name+'/'+golden_name,cpu_golden_sha256=hashlib.sha256(bytes(gold)).hexdigest(),performance_status='NOT_MEASURED'))
    (out/(s['id']+'-'+str(camera)+'-heat.json')).write_text(json.dumps(dict(size=[SIZE,SIZE],kind='CPU geometric fragment coverage estimate, not hardware counter',layers=heat),separators=(',',':'))+'\n')
 finally:h.close()
 report=dict(status='HOST_PASS' if all(x['quality']==x['expected'] for x in rows) else 'FAIL',size=[SIZE,SIZE],format='RGBA8 bottom-up',source_hashes={'vertex':hashlib.sha256(VERT.encode()).hexdigest(),'fragment':hashlib.sha256(FRAG.encode()).hexdigest()},scope='perspective-projected billboard scenes; Gaussian alpha proxy, not learned anisotropic 3DGS; glass alpha tint, not refraction',physical_performance='NOT_MEASURED',rows=rows)
 report['parallax']=[]
 for scene in scenes():
  views=[x for x in rows if x['scene']==scene['id'] and x['variant']=='baseline']
  observed=views[-1]['metrics']['alpha_centroid_x']-views[0]['metrics']['alpha_centroid_x']
  expected=views[-1]['metrics']['cpu_alpha_centroid_x']-views[0]['metrics']['cpu_alpha_centroid_x']
  report['parallax'].append(dict(scene=scene['id'],measured_centroid_shift_pixels=observed,cpu_predicted_shift_pixels=expected,error_pixels=abs(observed-expected),status='PASS' if abs(observed-expected)<=.1 and abs(observed)>1 else 'FAIL'))
 if any(x['status']!='PASS' for x in report['parallax']):report['status']='FAIL'
 report['thresholds']=dict(max_rgba8_error=4,silhouette_disagree_pixels=2,centroid_error_pixels=.1,reason='RGBA8 blend quantization accumulates across up to 18 translucent layers; no perceptual claim')
 archive=report_path.with_suffix('.zip')
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for path in sorted(out.iterdir()):
   info=zipfile.ZipInfo(out.name+'/'+path.name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
   z.writestr(info,path.read_bytes())
 report['artifact_archive']=dict(file=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),instructions='Extract beside report before resolving image/CPU/heatmap paths; all pixel evidence retained')
 report_path.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
