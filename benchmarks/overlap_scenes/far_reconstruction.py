#!/usr/bin/env python3
"""Separate low-resolution far FBO, bilinear resolve, full-resolution foreground."""
import argparse,ctypes as C,hashlib,json,math,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import projected as p
import tiered as t
U,I,P,F=p.U,p.I,p.P,p.F
COPY='#version 300 es\nprecision highp float;uniform sampler2D image;layout(location=0) out vec4 color;\nvoid main(){vec2 pos=gl_FragCoord.xy/float(SCALE)-.5;ivec2 lo=ivec2(floor(pos));vec2 w=fract(pos);ivec2 hi=textureSize(image,0)-1;\nvec4 a=texelFetch(image,clamp(lo,ivec2(0),hi),0),b=texelFetch(image,clamp(lo+ivec2(1,0),ivec2(0),hi),0),c=texelFetch(image,clamp(lo+ivec2(0,1),ivec2(0),hi),0),d=texelFetch(image,clamp(lo+ivec2(1),ivec2(0),hi),0);\ncolor=mix(mix(a,b,w.x),mix(c,d,w.x),w.y);}\n'
class FarHost(p.diff.Host):
 def draw(self,far,foreground,camera,far_size):
  if not far or not foreground or min(o['z'] for o in far)<=max(o['z'] for o in foreground):raise ValueError('Nonempty far/foreground layers require strict depth separation')
  if far_size not in (32,64):raise ValueError('size')
  fbs=[];textures=[];programs=[];vao=U()
  def target(size):
   fb=U();tex=U();self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));fbs.append(fb)
   self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb);self.fn('glGenTextures',None,[I,P])(1,C.byref(tex));textures.append(tex)
   self.fn('glBindTexture',None,[U,U])(0xde1,tex)
   for k,v in ((0x2800,0x2600),(0x2801,0x2600),(0x2802,0x812f),(0x2803,0x812f)):self.fn('glTexParameteri',None,[U,U,I])(0xde1,k,v)
   self.fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,0x8058,size,size,0,0x1908,0x1401,None)
   self.fn('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0,0xde1,tex,0)
   if self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO incomplete')
   return fb,tex
  def program(v,f):
   prog,info=self.program({'shader.vert':v,'shader.frag':f});programs.append(prog)
   if not info['compile'] or not info['link']:raise RuntimeError('compile/link failed')
   self.fn('glUseProgram',None,[U])(prog);return prog
  def layers(objects,size):
   prog=program(p.VERT.replace('0.03125',str(2/size)),p.FRAG.replace('/64.0','/'+str(float(size))))
   loc={n:self.fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,n.encode()) for n in ('rect','tint','mode')}
   self.fn('glEnable',None,[U])(0xbe2);self.fn('glBlendFuncSeparate',None,[U]*4)(0x302,0x303,1,0x303)
   for o in objects:
    self.fn('glUniform4f',None,[I,F,F,F,F])(loc['rect'],*p.project(o,camera));self.fn('glUniform4f',None,[I,F,F,F,F])(loc['tint'],*o['color'])
    self.fn('glUniform1i',None,[I,I])(loc['mode'],o['mode']);self.fn('glDrawArrays',None,[U,I,I])(4,0,6)
  try:
   self.fn('glActiveTexture',None,[U])(0x84c0);self.fn('glColorMask',None,[U]*4)(1,1,1,1);self.fn('glBlendEquationSeparate',None,[U,U])(0x8006,0x8006)
   for cap in (0xbd0,0xb71,0xb90,0xc11,0xb44):self.fn('glDisable',None,[U])(cap)
   self.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));self.fn('glBindVertexArray',None,[U])(vao)
   farfb,fartex=target(far_size);self.fn('glViewport',None,[I]*4)(0,0,far_size,far_size);self.fn('glClearColor',None,[F]*4)(0,0,0,0);self.fn('glClear',None,[U])(0x4000);layers(far,far_size)
   finalfb,_=target(64);self.fn('glViewport',None,[I]*4)(0,0,64,64);self.fn('glDisable',None,[U])(0xbe2)
   prog=program(p.VERT.replace('rect.xy+local*(rect.zw+vec2(0.03125))','local'),COPY.replace('SCALE',str(64//far_size)))
   self.fn('glActiveTexture',None,[U])(0x84c0);self.fn('glBindTexture',None,[U,U])(0xde1,fartex)
   loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,b'image');self.fn('glUniform1i',None,[I,I])(loc,0);self.fn('glDrawArrays',None,[U,I,I])(4,0,6)
   layers(foreground,64)
   buf=(C.c_ubyte*16384)();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,64,64,0x1908,0x1401,buf)
   if self.error():raise RuntimeError('GL error')
   return list(buf)
  finally:
   self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindVertexArray',None,[U])(0)
   for prog in programs:self.fn('glDeleteProgram',None,[U])(prog)
   for tex in textures:self.fn('glDeleteTextures',None,[I,P])(1,C.byref(tex))
   for fb in fbs:self.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(fb))
   if vao.value:self.fn('glDeleteVertexArrays',None,[I,P])(1,C.byref(vao))
def scene():
 far=[dict(id=i,x=(i%2-.5)*1.3,y=(i//2-.5)*.9,z=5+i*.2,radius=1.3,color=[.15+i*.15,.35,.7,.12],mode=0) for i in range(4)]
 near=[dict(id=4+i,x=(i-1)*.3,y=(i%2-.5)*.2,z=1.5+i*.1,radius=.19,color=[.85,.2+i*.15,.15,.65],mode=3) for i in range(3)]
 return sorted(far,key=lambda x:x['z'],reverse=True),sorted(near,key=lambda x:x['z'],reverse=True)
def cpu_layers(objects,camera,size,pixels=None):
 pixels=[0]*(size*size*4) if pixels is None else list(pixels)
 for o in objects:
  cx,cy,rx,ry=p.project(o,camera)
  for y in range(size):
   v=((y+.5)/size*2-1-cy)/ry
   for x in range(size):
    u=((x+.5)/size*2-1-cx)/rx
    if not(-1<u<1 and -1<v<1):continue
    alpha=o['color'][3]*(math.exp(-3*(u*u+v*v)) if o['mode']==0 else 1)
    for k in range(4):
     idx=(y*size+x)*4+k;value=(o['color'][k]*alpha if k<3 else alpha)+pixels[idx]/255*(1-alpha)
     pixels[idx]=math.floor(value*255+.5)
 return pixels
def cpu(far,near,camera,size):
 low=cpu_layers(far,camera,size);scale=64//size
 expanded=[]
 for y in range(64):
  for x in range(64):
   u,v=(x+.5)/scale-.5,(y+.5)/scale-.5;ix,iy=math.floor(u),math.floor(v);wx,wy=u-ix,v-iy
   for k in range(4):
    value=0
    for dx,dy,weight in ((0,0,(1-wx)*(1-wy)),(1,0,wx*(1-wy)),(0,1,(1-wx)*wy),(1,1,wx*wy)):
     xx=max(0,min(size-1,ix+dx));yy=max(0,min(size-1,iy+dy));value+=low[(yy*size+xx)*4+k]*weight
    expanded.append(math.floor(value+.5))

 return cpu_layers(near,camera,64,expanded)
def logical_work(far_size,far_layers=4,foreground_layers=3):
 # Bounding model, not actual shaded fragments or driver traffic.
 return dict(far_target_pixels=far_size*far_size,far_layer_pixel_upper_bound=far_size*far_size*far_layers,foreground_target_pixels=4096,foreground_layer_pixel_upper_bound=4096*foreground_layers,copy_output_pixels=4096,far_attachment_bytes=far_size*far_size*4,final_attachment_bytes=4096*4,combined_attachment_bytes=(far_size*far_size+4096)*4,draw_calls=far_layers+foreground_layers+1,copy_texel_fetch_upper_bound=4096*4,copy_logical_read_write_upper_bytes=4096*20,interpretation='Logical single-sample RGBA8 attachment storage and full-target invocation bounds; copy fetches bilinear far texels, cache/tiling/compression/residency and actual DRAM traffic are unknown')
def select(rows):
 expected={(c,v) for c in (-.3,0,.3) for v in ('baseline','far_bilinear','bad_foreground_drop')}
 if len(rows)!=9 or {(r['camera'],r['variant']) for r in rows}!=expected:return None
 baseline=all(r['quality']=='PASS' for r in rows if r['variant']=='baseline')
 candidate=all(r['quality']=='PASS' for r in rows if r['variant']=='far_bilinear')
 return None if not baseline else 'far_bilinear' if candidate else 'baseline'
def camera_selection(rows,parallax):
 if len(parallax)!=2 or [r.get('variant') for r in parallax]!=['baseline','far_bilinear']:return None
 choice=select(rows)
 if parallax[0]['status']!='PASS':return None
 if choice=='far_bilinear' and parallax[1]['status']!='PASS':return 'baseline'
 return choice
def contract_valid(rows,parallax,selected):
 expected={(c,v) for c in (-.3,0,.3) for v in ('baseline','far_bilinear','bad_foreground_drop')}
 if len(rows)!=9 or {(r['camera'],r['variant']) for r in rows}!=expected or len(parallax)!=2 or [r['variant'] for r in parallax]!=['baseline','far_bilinear']:return False
 if not all(r['complete_readback'] and t.accepted(r['mechanism_metrics']) for r in rows):return False
 if not all(r['quality']=='FAIL' for r in rows if r['variant']=='bad_foreground_drop'):return False
 return selected==camera_selection(rows,parallax)
def run(config,output):
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True);far,near=scene();h=FarHost(config);rows=[];artifacts={}
 try:
  for camera in (-.3,0,.3):
   gold=cpu(far,near,camera,64);prefix='cam'+str(camera);artifacts[prefix+'-gold.rgba']=bytes(gold)
   for name,size,fg in [('baseline',64,near),('far_bilinear',32,near),('bad_foreground_drop',32,near[:1])]:
    pixels=h.draw(far,fg,camera,size);own=cpu(far,fg,camera,size);m=p.metrics(pixels,gold);mechanism=p.metrics(pixels,own);fgmask=cpu_layers(near,camera,64);roi=max(abs(pixels[i*4+k]-gold[i*4+k]) for i in range(4096) if fgmask[i*4+3]>0 for k in range(4))
    rows.append(dict(camera=camera,variant=name,quality='PASS' if t.accepted(m) else 'FAIL',metrics=m,foreground_roi_max_error=roi,mechanism_metrics=mechanism,complete_readback=len(pixels)==16384,far_resolution=size,foreground_resolution=64,draw_calls=len(far)+len(fg)+1,artifact_prefix=prefix+'-'+name))
    artifacts[prefix+'-'+name+'.rgba']=bytes(pixels);artifacts[prefix+'-'+name+'-mechanism-cpu.rgba']=bytes(own)
 finally:h.close()
 selected=select(rows)
 parallax=[]
 for name in ('baseline','far_bilinear'):
  views=[r['metrics'] for r in rows if r['variant']==name];actual=views[-1]['alpha_centroid_x']-views[0]['alpha_centroid_x'];reference=views[-1]['cpu_alpha_centroid_x']-views[0]['cpu_alpha_centroid_x'];parallax.append(dict(variant=name,error=abs(actual-reference),status='PASS' if abs(actual-reference)<=.1 and abs(actual)>1 else 'FAIL'))
 selected=camera_selection(rows,parallax)
 archive=path.with_suffix('.zip')
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for name,data in sorted(artifacts.items()):
   info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
 contract=contract_valid(rows,parallax,selected)
 r=dict(status='HOST_PASS' if all(x['quality']=='PASS' for x in rows if x['variant']!='bad_foreground_drop') and all(x['status']=='PASS' for x in parallax) and contract else 'FAIL',contract_status='PASS' if contract else 'FAIL',global_policy=dict(selected=selected,status='ACCEPTED_FOR_TESTED_CAMERAS' if selected else 'UNAVAILABLE'),scope='actual separate far RGBA8 FBO -> four-fetch bilinear texelFetch copy -> full-resolution foreground source-over; four-fetch bilinear reconstruction; finite Gaussian/UI proxies',performance_status='NOT_MEASURED',readbacks=9,thresholds=dict(max_rgba8_error=4,silhouette_disagree_pixels=2,centroid_error_pixels=.1,parallax_error_pixels=.1),logical_work_comparison=dict(baseline=logical_work(64),far_bilinear=logical_work(32),performance_interpretation='No measured GPU time or bandwidth gain; both baseline and candidate include a 4096-pixel copy pass and eight draws'),scene=dict(far=far,foreground=near),rows=rows,parallax=parallax,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),artifact_archive=dict(file=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),instructions='Extract complete 64x64 bottom-up RGBA8 images beside report'))
 r['shader_source_sha256']={str(size):{'vertex':hashlib.sha256(p.VERT.replace('0.03125',str(2/size)).encode()).hexdigest(),'fragment':hashlib.sha256(p.FRAG.replace('/64.0','/'+str(float(size))).encode()).hexdigest(),'copy':hashlib.sha256(COPY.replace('SCALE',str(64//size)).encode()).hexdigest()} for size in (32,64)}
 r['cpu_dependency_sha256']=hashlib.sha256(Path(p.__file__).read_bytes()).hexdigest()
 r['selected_camera_artifacts']={str(row['camera']):row['artifact_prefix']+'.rgba' for row in rows if selected is not None and row['variant']==selected}
 r['copy_vertex_sha256']=hashlib.sha256(p.VERT.replace('rect.xy+local*(rect.zw+vec2(0.03125))','local').encode()).hexdigest()
 path.write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--config',required=True);a.add_argument('--output',required=True);a.add_argument('--require-contract-only',action='store_true');args=a.parse_args();r=run(json.loads(Path(args.config).read_text()),args.output);print(r['status']);raise SystemExit(r['contract_status']!='PASS' if args.require_contract_only else r['status']!='HOST_PASS')
