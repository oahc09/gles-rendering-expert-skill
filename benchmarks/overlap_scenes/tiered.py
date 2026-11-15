#!/usr/bin/env python3
"""Bounded transparency grouping and resolution fallback controls, no GPU timings."""
import argparse,copy,ctypes as C,hashlib,json,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import projected as p
U,I,P,F=p.U,p.I,p.P,p.F
project=p.project
class TierHost(p.diff.Host):
 def draw(self,objects,camera,resolution=64):
  fb=U();rb=U();vao=U();dst=U();drb=U();prog=0; SIZE=resolution
  try:
   prog,compile_info=self.program({'shader.vert':p.VERT.replace('0.03125',str(2/resolution)), 'shader.frag':p.FRAG.replace('/64.0','/'+str(float(resolution)))})
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
   previous=None; self.tint_updates=0
   for o in objects:
    self.fn('glUniform4f',None,[I,F,F,F,F])(loc['rect'],*project(o,camera))
    if o['color']!=previous:
     self.fn('glUniform4f',None,[I,F,F,F,F])(loc['tint'],*o['color']); self.tint_updates+=1; previous=o['color']
    self.fn('glUniform1i',None,[I,I])(loc['mode'],o['mode']);self.fn('glDrawArrays',None,[U,I,I])(4,0,6)
   if resolution!=64:
    self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(dst));self.fn('glBindFramebuffer',None,[U,U])(0x8ca9,dst)
    self.fn('glGenRenderbuffers',None,[I,P])(1,C.byref(drb));self.fn('glBindRenderbuffer',None,[U,U])(0x8d41,drb)
    self.fn('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,64,64)
    self.fn('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8ca9,0x8ce0,0x8d41,drb)
    if self.fn('glCheckFramebufferStatus',U,[U])(0x8ca9)!=0x8cd5:raise RuntimeError('resolve FBO incomplete')
    self.fn('glBindFramebuffer',None,[U,U])(0x8ca8,fb)
    self.fn('glBlitFramebuffer',None,[I]*8+[U,U])(0,0,SIZE,SIZE,0,0,64,64,0x4000,0x2600)
    self.fn('glBindFramebuffer',None,[U,U])(0x8d40,dst)
   SIZE=64
   buf=(C.c_ubyte*(SIZE*SIZE*4))();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,SIZE,SIZE,0x1908,0x1401,buf)
   if self.error():raise RuntimeError('GL operation failed')
   return list(buf)
  finally:
   self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindVertexArray',None,[U])(0)
   if drb.value:self.fn('glDeleteRenderbuffers',None,[I,P])(1,C.byref(drb))
   if dst.value:self.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(dst))
   if prog:self.fn('glDeleteProgram',None,[U])(prog)
   if vao.value:self.fn('glDeleteVertexArrays',None,[I,P])(1,C.byref(vao))
   if rb.value:self.fn('glDeleteRenderbuffers',None,[I,P])(1,C.byref(rb))
   if fb.value:self.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(fb))

def scene(count):
 # Two screen-disjoint columns. Global depth interleaves materials; each column order is preserved by grouping.
 obs=[]
 for i in range(count):
  side=i%2;z=3+i*.025
  obs.append(dict(id=i,x=(-.62 if side==0 else .62)*z,y=((i//2)%4-1.5)*.15*z,z=z,radius=.18*z,color=[.9,.2,.1,.15] if side==0 else [.1,.3,.9,.15],mode=0,group=side))
 return sorted(obs,key=lambda o:o['z'],reverse=True)
def disjoint_groups(obs,camera):
 for a in obs:
  for b in obs:
   if a['group']==b['group']:continue
   ax,ay,ar,_=project(a,camera);bx,by,br,_=project(b,camera)
   if abs(ax-bx)<ar+br and abs(ay-by)<ar+br:return False
 return True
def accepted(m):return m['max_rgba8_error']<=4 and m['silhouette_disagree_pixels']<=2 and m['centroid_error_pixels'] is not None and m['centroid_error_pixels']<=.1
def run(config,output):
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True);archive=path.with_suffix('.zip');rows=[];artifacts={};h=TierHost(config)
 try:
  for count in (8,24,48):
   obs=scene(count)
   for cam in (-.3,0,.3):
    gold,heat=p.cpu(obs,cam);base=h.draw(obs,cam);baseupdates=h.tint_updates
    grouped=sorted(obs,key=lambda o:o['group']) if disjoint_groups(obs,cam) else obs
    grouped_pixels=h.draw(grouped,cam);groupupdates=h.tint_updates
    low=h.draw(obs,cam,32)
    # Deliberate foreground-removal counterexample; never select it.
    bad=h.draw(obs[:len(obs)//2],cam)
    prefix=f'tier{count}-camera{cam}'
    metrics={k:p.metrics(v,gold) for k,v in dict(baseline=base,grouped=grouped_pixels,half_resolution=low,bad_drop=bad).items()}
    use_low=accepted(metrics['half_resolution']);chosen=low if use_low else base
    for name,pixels in dict(cpu=gold,baseline=base,grouped=grouped_pixels,half_resolution=low,bad_drop=bad,selected=chosen).items():artifacts[prefix+'-'+name+'.rgba']=bytes(pixels)
    artifacts[prefix+'-heat.json']=json.dumps(dict(size=[64,64],layers=heat,kind='CPU geometric estimate; not hardware counters')).encode()
    rows.append(dict(tier_object_count=count,camera_x=cam,metrics=metrics,grouping_proven_disjoint=disjoint_groups(obs,cam),grouping_pixel_identical=base==grouped_pixels,tint_uniform_updates=dict(baseline=baseupdates,grouped=groupupdates),draws_per_arm=dict(baseline=count,grouped=count,half_resolution=count,bad_drop=count//2),baseline_quality='PASS' if accepted(metrics['baseline']) else 'FAIL',fallback_acceptable=accepted(p.metrics(chosen,gold)),tier_acceptance='PASS' if accepted(metrics['baseline']) else 'REJECTED_CPU_GOLDEN',resolution_candidate='PASS' if use_low else 'REJECTED_FALLBACK',selected_metrics=p.metrics(chosen,gold),status='PASS' if accepted(metrics['baseline']) and grouped_pixels==base and accepted(p.metrics(chosen,gold)) and not accepted(metrics['bad_drop']) else 'FAIL',artifact_prefix=prefix))
 finally:h.close()
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for name,value in sorted(artifacts.items()):
   info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,value)
 result=dict(status='HOST_PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',scope='8/24/48 authored Gaussian-alpha billboards; screen-disjoint material grouping; 64->32 render then actual GLES nearest framebuffer upsample and quality-gated baseline fallback',physical_performance='NOT_MEASURED',million_scale='NOT_RUN',readbacks=36,thresholds=dict(max_rgba8_error=4,silhouette_disagree_pixels=2,centroid_error_pixels=.1),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),artifact_archive=dict(file=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),instructions='Extract beside report; prefix-name.rgba files are 64x64 bottom-up RGBA8'),rows=rows)
 result['shader_source_sha256']={str(n):{'vertex':hashlib.sha256(p.VERT.replace('0.03125',str(2/n)).encode()).hexdigest(),'fragment':hashlib.sha256(p.FRAG.replace('/64.0','/'+str(float(n))).encode()).hexdigest()} for n in (32,64)}
 result['harness_contract']='PASS' if all(r['grouping_proven_disjoint'] and r['grouping_pixel_identical'] and not accepted(r['metrics']['bad_drop']) and (r['resolution_candidate']=='PASS' or r['selected_metrics']==r['metrics']['baseline']) for r in rows) else 'FAIL'
 result['acceptable_tiers']=[n for n in (8,24,48) if all(r['baseline_quality']=='PASS' for r in rows if r['tier_object_count']==n)]
 result['baseline_failure_cause']='UNDETERMINED; accumulated blend/oracle differences suspected, not established; threshold unchanged' if result['status']=='FAIL' else None
 result['parallax']=[dict(tier_object_count=count,error_pixels=abs((views[-1]['metrics']['baseline']['alpha_centroid_x']-views[0]['metrics']['baseline']['alpha_centroid_x'])-(views[-1]['metrics']['baseline']['cpu_alpha_centroid_x']-views[0]['metrics']['baseline']['cpu_alpha_centroid_x']))) for count in (8,24,48) for views in [[r for r in rows if r['tier_object_count']==count]]]
 path.write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--config',required=True);a.add_argument('--output',required=True);a.add_argument('--require-harness-only',action='store_true');args=a.parse_args();r=run(json.loads(Path(args.config).read_text()),args.output);print(r['status']);raise SystemExit(r['harness_contract']!='PASS' if args.require_harness_only else r['status']!='HOST_PASS')
