#!/usr/bin/env python3
"""Finite rain billboards, Beer-Lambert volume slices and rounded UI proxies."""
import argparse,ctypes as C,hashlib,json,math,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import projected as p
import tiered as t
U,I,P,F=p.U,p.I,p.P,p.F
SIZE=64
VERT=p.VERT
FRAG="""#version 300 es
precision highp float;
uniform vec4 rect;uniform vec4 tint;uniform int mode;
layout(location=0) out vec4 color;
void main(){vec2 point=(gl_FragCoord.xy/64.0*2.0-1.0-rect.xy)/rect.zw;
 if(any(greaterThanEqual(abs(point),vec2(1))))discard;
 float q=dot(point,point);float a=tint.a;
 if(mode==4){if(q>1.0)discard;a*=max(0.0,1.0-q);}
 if(mode==5){if(q>=1.0)discard;a=1.0-exp(-tint.a*sqrt(max(0.0,1.0-q))*.25);}
 if(mode==6){vec2 edge=max(abs(point)-vec2(.75),vec2(0));if(length(edge)>.25)discard;}
 color=vec4(tint.rgb,a);
}
"""
def project(o,camera):return [(o['x']-camera)/o['z'],o['y']/o['z'],o['rx']/o['z'],o['ry']/o['z']]
class SceneHost(p.diff.Host):
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

def scenes():
 result=[]
 for name,mode,count in [('rain-droplet-proxy',4,9),('volume-slice-proxy',5,8),('rounded-layered-ui',6,6)]:
  obs=[]
  for i in range(count):
   z=2.5+i*.12
   x=((i%3)-1)*.3 if mode==4 else (i%2-.5)*.12
   y=((i//3)-1)*.28 if mode==4 else (i%3-1)*.1
   obs.append(dict(id=i,x=x,y=y,z=z,rx=.11 if mode==4 else .52,ry=.32 if mode==4 else .4,color=[.15+(i%3)*.25,.3+(i%2)*.2,.8-(i%3)*.2,.55 if mode==5 else .22],mode=mode))
  obs.extend([dict(id=count+j,x=12+j,y=0,z=2.5,rx=.1,ry=.2,color=[1,0,0,.5],mode=mode) for j in range(2)])
  result.append(dict(name=name,objects=sorted(obs,key=lambda o:o['z'],reverse=True)))
 return result
def opacity(o,u,v):
 if not(-1<u<1 and -1<v<1):return None
 q=u*u+v*v;a=o['color'][3]
 if o['mode']==4:return None if q>1 else a*max(0,1-q)
 if o['mode']==5:return None if q>=1 else 1-math.exp(-a*math.sqrt(max(0,1-q))*.25)
 if o['mode']==6 and math.hypot(max(abs(u)-.75,0),max(abs(v)-.75,0))>.25:return None
 return a
def visible(o,camera):
 x,y,rx,ry=project(o,camera);return x+rx>-1 and x-rx<1 and y+ry>-1 and y-ry<1
def cpu(objects,camera):
 pixels=[0]*16384;layers=[0]*4096;transmission=[1.]*4096;depths=[[] for _ in layers];alphas=[[] for _ in layers];colors=[[] for _ in layers];projected_area=[0]*16
 for o in objects:
  cx,cy,rx,ry=project(o,camera)
  for y in range(64):
   v=((y+.5)/64*2-1-cy)/ry
   for x in range(64):
    u=((x+.5)/64*2-1-cx)/rx;idx=y*64+x;tile=(y//16)*4+x//16
    if -1<u<1 and -1<v<1:projected_area[tile]+=1
    a=opacity(o,u,v)
    if a is None:continue
    layers[idx]+=1;transmission[idx]*=1-a;depths[idx].append(o['z']);alphas[idx].append(a);colors[idx].append(o['color'][:3])
    for k in range(4):
     value=(o['color'][k]*a if k<3 else a)+pixels[idx*4+k]/255*(1-a)
     pixels[idx*4+k]=math.floor(min(1,max(0,value))*255+.5)
 tiles=[]
 for ty in range(4):
  for tx in range(4):
   indices=[y*64+x for y in range(ty*16,ty*16+16) for x in range(tx*16,tx*16+16)]
   ds=[v for i in indices for v in depths[i]];aa=[v for i in indices for v in alphas[i]];cc=[v for i in indices for v in colors[i]]
   tiles.append(dict(tile=[tx,ty],screen_pixels=256,projected_bounds_fragment_samples=projected_area[ty*4+tx],covered_pixels=sum(layers[i]>0 for i in indices),shaded_fragment_samples=sum(layers[i] for i in indices),max_blend_layers=max(layers[i] for i in indices),mean_blend_layers=sum(layers[i] for i in indices)/256,source_alpha_range=[min(aa),max(aa)] if aa else None,source_rgb_range=[[min(c[k] for c in cc),max(c[k] for c in cc)] for k in range(3)] if cc else None,depth_range=[min(ds),max(ds)] if ds else None,mean_background_transmission=sum(transmission[i] for i in indices)/256,mean_final_rgba=[sum(pixels[i*4+k] for i in indices)/(256*255) for k in range(4)]))
 return pixels,dict(tiles=tiles,layer_heatmap=layers,background_transmission=transmission,scope='CPU per-pixel projected-bound/fragment model, no hardware counters; background contribution is transmittance not a physically shaded background')
def tile_error(actual,golden):
 out=[]
 for ty in range(4):
  for tx in range(4):
   ids=[y*64+x for y in range(ty*16,ty*16+16) for x in range(tx*16,tx*16+16)]
   e=[abs(actual[i*4+k]-golden[i*4+k]) for i in ids for k in range(4)]
   out.append(dict(tile=[tx,ty],max_rgba8_error=max(e),mean_rgba8_error=sum(e)/len(e),silhouette_disagree=sum((actual[i*4+3]>12)!=(golden[i*4+3]>12) for i in ids),interpretation='numerical and silhouette proxies, not calibrated perceptual error'))
 return out
def run(config,output):
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True);h=SceneHost(config);rows=[];artifacts={}
 try:
  for scene in scenes():
   for camera in (-.3,0,.3):
    obs=scene['objects'];gold,stats=cpu(obs,camera);prefix=scene['name']+'-'+str(camera);baseline=None
    variants={'baseline':obs,'offscreen_culling':[o for o in obs if visible(o,camera)],'bad_visible_drop':[o for o in obs if o['id']%2]}
    artifacts[prefix+'-cpu.rgba']=bytes(gold);artifacts[prefix+'-tiles.json']=json.dumps(stats,separators=(',',':')).encode()
    for name,objects in variants.items():
     actual=h.draw(objects,camera)
     if name=='baseline':baseline=actual
     m=p.metrics(actual,gold);quality=t.accepted(m);expected=name!='bad_visible_drop'
     rows.append(dict(scene=scene['name'],camera=camera,variant=name,quality='PASS' if quality else 'FAIL',expected='PASS' if expected else 'FAIL',metrics=m,tile_error=tile_error(actual,gold),draw_calls=len(objects),pixel_identical_to_baseline=actual==baseline,status='PASS' if quality==expected and (name!='offscreen_culling' or actual==baseline) else 'FAIL',artifact_prefix=prefix+'-'+name))
     artifacts[prefix+'-'+name+'.rgba']=bytes(actual)
 finally:h.close()
 archive=path.with_suffix('.zip')
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for name,value in sorted(artifacts.items()):
   info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,value)
 parallax=[]
 for scene in scenes():
  views=[r for r in rows if r['scene']==scene['name'] and r['variant']=='baseline'];a,b=views[0]['metrics'],views[-1]['metrics']
  observed=b['alpha_centroid_x']-a['alpha_centroid_x'];gold=b['cpu_alpha_centroid_x']-a['cpu_alpha_centroid_x']
  parallax.append(dict(scene=scene['name'],observed_shift=observed,cpu_shift=gold,error=abs(observed-gold),status='PASS' if abs(observed-gold)<=.1 and abs(observed)>1 else 'FAIL'))
 result=dict(status='HOST_PASS' if all(r['status']=='PASS' for r in rows+parallax) else 'FAIL',scope='Rain elliptical alpha billboards, eight Beer-Lambert radial density slices, rounded layered UI proxies; three translating cameras; no water refraction, ray marching or production UI system',performance_status='NOT_MEASURED',readbacks=len(rows),rows=rows,parallax=parallax,scene_inputs=scenes(),thresholds=dict(max_rgba8_error=4,silhouette_disagree_pixels=2,centroid_error_pixels=.1),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),shader_sha256=dict(vertex=hashlib.sha256(VERT.encode()).hexdigest(),fragment=hashlib.sha256(FRAG.encode()).hexdigest()),artifact_archive=dict(file=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),instructions='Extract beside report; RGBA files 64x64 bottom-up, tiles JSON includes complete per-pixel layers/transmittance'))
 path.write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--output',required=True);a=parser.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
