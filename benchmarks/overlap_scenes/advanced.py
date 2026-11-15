#!/usr/bin/env python3
"""Finite anisotropic Gaussian projection and refractive plate controls; no training/performance claims."""
import argparse,ctypes as C,hashlib,json,math,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import projected as p
U,I,P,F=p.U,p.I,p.P,p.F
SIZE=64
VERT=p.VERT
FRAG='''#version 300 es
precision highp float;
in vec2 local;uniform vec4 rect,tint;
uniform vec3 inverseCov;uniform int mode;
uniform sampler2D background;uniform float thickness;
layout(location=0) out vec4 color;
void main(){
 vec2 screen=gl_FragCoord.xy/64.0*2.0-1.0;
 vec2 d=screen-rect.xy;vec2 q=d/rect.zw;
 if(any(greaterThanEqual(abs(q),vec2(1.0))))discard;
 if(mode==0){
 float mahal=inverseCov.x*d.x*d.x+2.0*inverseCov.y*d.x*d.y+inverseCov.z*d.y*d.y;
 if(mahal>9.0)discard;
 color=vec4(tint.rgb,tint.a*exp(-0.5*mahal));
 }else{
 vec2 nxy=q*0.3;vec3 normal=vec3(nxy,sqrt(1.0-dot(nxy,nxy)));
 vec3 ray=refract(vec3(0,0,-1),normal,1.0/1.5);
 vec2 uv=gl_FragCoord.xy/64.0+ray.xy*(-thickness/ray.z)*0.2;
 color=vec4(texture(background,uv).rgb*tint.rgb,tint.a);
 }
}
'''
def covariance(sx,sy,sz,theta):
 c=math.cos(theta);s=math.sin(theta)
 return [[c*c*sx*sx+s*s*sy*sy,c*s*(sx*sx-sy*sy),0],[c*s*(sx*sx-sy*sy),s*s*sx*sx+c*c*sy*sy,0],[0,0,sz*sz]]
def project_gaussian(o,camera):
 x=o['x']-camera;y=o['y'];z=o['z'];j=[[1/z,0,-x/(z*z)],[0,1/z,-y/(z*z)]];c=o['covariance']
 a=[[sum(j[r][k]*c[k][l]*j[t][l] for k in range(3) for l in range(3)) for t in range(2)] for r in range(2)]
 det=a[0][0]*a[1][1]-a[0][1]**2
 if det<=0 or not math.isfinite(det):raise ValueError('non positive projected covariance')
 return [x/z,y/z,3*math.sqrt(a[0][0]),3*math.sqrt(a[1][1])],[a[1][1]/det,-a[0][1]/det,a[0][0]/det]
def objects():
 result=[]
 for i in range(9):
  result.append(dict(id=i,x=(i%3-1)*.3,y=(i//3-1)*.25,z=2+(i%3)*.4,covariance=covariance(.19,.055,.08,i*.47),color=[.2+(i%3)*.3,.2+(i%2)*.5,.7-(i%3)*.2,.4],mode=0))
 for i in range(2):result.append(dict(id=9+i,x=-.5+i,y=.5,z=4,covariance=covariance(.1,.04,.04,.3),color=[1,0,0,.0005],mode=0))
 return sorted(result,key=lambda o:o['z'],reverse=True)
def lod_plan(obs,budget=4/255,force_unsafe=False):
 removed=[o for o in obs if (o['id']%3==0 if force_unsafe else o['color'][3]<=.001)]
 # Absolute normalized alpha/compositing contribution bound per pixel: sum opacity.
 float_bound=sum(o['color'][3] for o in removed)
 bound=(math.ceil(float_bound*255)+len(removed))/255 if removed else 0
 accepted=bound<=budget
 return dict(status='ACCEPT_BOUNDED_LOD' if accepted else 'FALLBACK_BASELINE',predicted_max_channel_error=bound,float_alpha_bound=float_bound,quantization_bound='ceil(255*sum_removed_opacity)+removed_count code values',budget=budget,removed_ids=[o['id'] for o in removed],objects=[o for o in obs if o not in removed] if accepted else obs)
def glass_objects():
 return [dict(id=i,x=(i-1)*.23,y=(i%2)*.18-.09,z=2.2+i*.25,radius=.72,color=[.85+i*.05,.95-i*.05,.9,.32],mode=1,thickness=2.0+i*.5) for i in (2,1,0)]
def texels():return [v for y in range(16) for x in range(16) for v in (x*17,y*17,(x+y)*8,255)]
def sample(uv):
 # GLES normalized GL_LINEAR, CLAMP_TO_EDGE texel-centre convention.
 x=uv[0]*16-.5;y=uv[1]*16-.5;ix=math.floor(x);iy=math.floor(y);fx=x-ix;fy=y-iy;t=texels()
 def at(a,b,k):return t[(min(15,max(0,b))*16+min(15,max(0,a)))*4+k]/255
 return [sum(at(ix+dx,iy+dy,k)*(fx if dx else 1-fx)*(fy if dy else 1-fy) for dx in (0,1) for dy in (0,1)) for k in range(3)]
def refraction(u,v,thickness):
 nx=u*.3;ny=v*.3;nz=math.sqrt(1-nx*nx-ny*ny);eta=1/1.5;dot=-nz;k=1-eta*eta*(1-dot*dot)
 factor=eta*dot+math.sqrt(k)
 rx=-factor*nx;ry=-factor*ny;rz=-eta-factor*nz
 return [rx*(-thickness/rz)*.2,ry*(-thickness/rz)*.2]
def cpu(obs,camera,glass=False):
 pixels=[0]*(SIZE*SIZE*4);heat=[0]*(SIZE*SIZE)
 for o in obs:
  rect,inv=(p.project(o,camera),None) if glass else project_gaussian(o,camera)
  cx,cy,rx,ry=rect
  for y in range(SIZE):
   dy=(y+.5)/SIZE*2-1-cy;v=dy/ry
   if abs(v)>=1:continue
   for x in range(SIZE):
    dx=(x+.5)/SIZE*2-1-cx;u=dx/rx
    if abs(u)>=1:continue
    if glass:
     offset=refraction(u,v,o['thickness']);rgb=[a*b for a,b in zip(sample([(x+.5)/SIZE+offset[0],(y+.5)/SIZE+offset[1]]),o['color'][:3])];alpha=o['color'][3]
    else:
     q=inv[0]*dx*dx+2*inv[1]*dx*dy+inv[2]*dy*dy
     if q>9:continue
     alpha=o['color'][3]*math.exp(-.5*q);rgb=o['color'][:3]
    idx=(y*SIZE+x)*4;heat[y*SIZE+x]+=1
    for k in range(4):pixels[idx+k]=math.floor(max(0,min(1,(rgb[k]*alpha if k<3 else alpha)+pixels[idx+k]/255*(1-alpha)))*255+.5)
 return pixels,heat

class Host(p.diff.Host):
 def draw(self,obs,camera,glass=False):
  fb=U();rb=U();vao=U();tex=U();prog=0
  try:
   prog,c=self.program({'shader.vert':VERT,'shader.frag':FRAG})
   if not c['compile'] or not c['link']:raise RuntimeError('compile/link failed')
   self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb)
   self.fn('glGenRenderbuffers',None,[I,P])(1,C.byref(rb));self.fn('glBindRenderbuffer',None,[U,U])(0x8d41,rb);self.fn('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,SIZE,SIZE);self.fn('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,rb)
   if self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO incomplete')
   for cap in (0xbd0,0xb71,0xb90,0xc11,0xb44):self.fn('glDisable',None,[U])(cap)
   self.fn('glEnable',None,[U])(0xbe2);self.fn('glBlendFuncSeparate',None,[U]*4)(0x302,0x303,1,0x303);self.fn('glViewport',None,[I]*4)(0,0,SIZE,SIZE);self.fn('glClearColor',None,[F]*4)(0,0,0,0);self.fn('glClear',None,[U])(0x4000)
   self.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));self.fn('glBindVertexArray',None,[U])(vao);self.fn('glUseProgram',None,[U])(prog)
   loc={n:self.fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,n.encode()) for n in ('rect','tint','mode','inverseCov','thickness','background')}
   if glass:
    self.fn('glGenTextures',None,[I,P])(1,C.byref(tex));self.fn('glActiveTexture',None,[U])(0x84c0);self.fn('glBindTexture',None,[U,U])(0xde1,tex)
    for key,value in ((0x2801,0x2601),(0x2800,0x2601),(0x2802,0x812f),(0x2803,0x812f)):self.fn('glTexParameteri',None,[U,U,I])(0xde1,key,value)
    data=(C.c_ubyte*1024)(*texels());self.fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,0x8058,16,16,0,0x1908,0x1401,data);self.fn('glUniform1i',None,[I,I])(loc['background'],0)
   for o in obs:
    rect,inv=(p.project(o,camera),[1,0,1]) if glass else project_gaussian(o,camera)
    self.fn('glUniform4f',None,[I,F,F,F,F])(loc['rect'],*rect);self.fn('glUniform4f',None,[I,F,F,F,F])(loc['tint'],*o['color']);self.fn('glUniform3f',None,[I,F,F,F])(loc['inverseCov'],*inv);self.fn('glUniform1i',None,[I,I])(loc['mode'],o['mode']);self.fn('glUniform1f',None,[I,F])(loc['thickness'],o.get('thickness',0));self.fn('glDrawArrays',None,[U,I,I])(4,0,6)
   buf=(C.c_ubyte*(SIZE*SIZE*4))();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,SIZE,SIZE,0x1908,0x1401,buf)
   if self.error():raise RuntimeError('GL failed')
   return list(buf)
  finally:
   self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindVertexArray',None,[U])(0)
   if prog:self.fn('glDeleteProgram',None,[U])(prog)
   for obj,fn in ((fb,'glDeleteFramebuffers'),(rb,'glDeleteRenderbuffers'),(vao,'glDeleteVertexArrays'),(tex,'glDeleteTextures')):
    if obj.value:self.fn(fn,None,[I,P])(1,C.byref(obj))

def run(config,output):
 dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True);folder=dest.parent/(dest.stem+'-images');folder.mkdir(exist_ok=True);h=Host(config);rows=[];plans=[]
 try:
  for camera in (-.3,0,.3):
   for glass in (False,True):
    name='refractive-glass' if glass else 'anisotropic-gaussians';obs=glass_objects() if glass else objects();gold,heat=cpu(obs,camera,glass)
    if glass:
     # Valid optimization: zero-thickness entries would be culled only if alpha zero; here no gain, baseline retained.
     variants={'baseline':obs,'no-gain-fallback':obs,'bad-no-refraction':[dict(o,thickness=0) for o in obs]}
    else:
     safe=lod_plan(obs);unsafe=lod_plan(obs,force_unsafe=True);plans.append(dict(camera=camera,safe={k:v for k,v in safe.items() if k!='objects'},unsafe={k:v for k,v in unsafe.items() if k!='objects'}))
     variants={'baseline':obs,'bounded-lod':safe['objects'],'unsafe-lod-fallback':unsafe['objects'],'bad-drop-foreground':[o for o in obs if o['id']%3!=0],'bad-reverse-sort':list(reversed(obs))}
    stem=name+'-'+str(camera);(folder/(stem+'-cpu.rgba')).write_bytes(bytes(gold));(folder/(stem+'-heat.json')).write_text(json.dumps(heat,separators=(',',':')))
    baseline=None
    for arm,objects_ in variants.items():
     pix=h.draw(objects_,camera,glass)
     if arm=='baseline':baseline=pix
     m=p.metrics(pix,gold);status='PASS' if m['max_rgba8_error']<=4 and m['silhouette_disagree_pixels']<=2 and m['centroid_error_pixels'] is not None and m['centroid_error_pixels']<=.1 else 'FAIL'
     lod_delta=max(abs(x-y) for x,y in zip(pix,baseline))
     if arm=='bounded-lod' and lod_delta/255>safe['predicted_max_channel_error']:status='FAIL'
     if 'fallback' in arm and pix!=baseline:status='FAIL'
     image=stem+'-'+arm+'.rgba';(folder/image).write_bytes(bytes(pix));rows.append(dict(scene=name,camera_x=camera,arm=arm,expected='FAIL' if arm.startswith('bad-') else 'PASS',quality=status,metrics=m,draw_count=len(objects_),delta_from_baseline_codes=lod_delta,image=folder.name+'/'+image,image_sha256=hashlib.sha256(bytes(pix)).hexdigest(),cpu_golden=folder.name+'/'+stem+'-cpu.rgba',heatmap=folder.name+'/'+stem+'-heat.json'))
 finally:h.close()
 report=dict(status='HOST_PASS' if all(x['quality']==x['expected'] for x in rows) else 'FAIL',scope='authored 3D covariance Gaussians and background-sampled refractive plates; no learned/complete 3DGS, no recursive multi-interface optics',size=[SIZE,SIZE],format='bottom-up RGBA8',source_hashes={'vertex':hashlib.sha256(VERT.encode()).hexdigest(),'fragment':hashlib.sha256(FRAG.encode()).hexdigest()},physical_performance='NOT_MEASURED',scene_manifest={'gaussians':objects(),'glass':glass_objects(),'camera_x':[-.3,0,.3],'texture_rgba8':texels()},rows=rows,lod_decisions=plans)
 report['parallax']=[]
 for scene in ('anisotropic-gaussians','refractive-glass'):
  views=[x for x in rows if x['scene']==scene and x['arm']=='baseline']
  observed=views[-1]['metrics']['alpha_centroid_x']-views[0]['metrics']['alpha_centroid_x'];expected=views[-1]['metrics']['cpu_alpha_centroid_x']-views[0]['metrics']['cpu_alpha_centroid_x']
  status='PASS' if abs(observed-expected)<=.1 and abs(observed)>1 else 'FAIL'
  report['parallax'].append(dict(scene=scene,observed_shift_pixels=observed,cpu_shift_pixels=expected,error_pixels=abs(observed-expected),status=status))
 if any(x['status']!='PASS' for x in report['parallax']):report['status']='FAIL'
 report['thresholds']=dict(max_rgba8_error=4,silhouette_disagree_pixels=2,centroid_error_pixels=.1)
 archive=dest.with_suffix('.zip')
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for file in sorted(folder.iterdir()):
   info=zipfile.ZipInfo(folder.name+'/'+file.name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,file.read_bytes())
 report['artifact_archive']=dict(file=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),instructions='Extract beside report to resolve image references')
 dest.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--output',required=True);args=parser.parse_args();r=run(json.loads(Path(args.config).read_text()),args.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
