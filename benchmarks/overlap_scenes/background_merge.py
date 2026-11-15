#!/usr/bin/env python3
"""Exact-profile adjacent duplicate background Gaussian-alpha compaction."""
import argparse,copy,ctypes as C,hashlib,json,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import projected as p
import tiered as t
U,I,P,F=p.U,p.I,p.P,p.F
SIZE=64
VERT=p.VERT
FRAG=p.FRAG.replace('if(mode==0){a*=exp(-3.0*dot(point,point));}', 'if(mode==0 || mode==7){a*=exp(-3.0*dot(point,point));if(mode==7)a=1.0-(1.0-a)*(1.0-a);}')
project=p.project
class MergeHost(p.diff.Host):
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

def scene():
 obs=[]
 for j in range(4):
  o=dict(id=j*2,x=(j%2-.5)*.6,y=(j//2-.5)*.45,z=4+j*.2,radius=1.1,color=[.15+j*.12,.35,.75-j*.1,.3],mode=0,role='background')
  obs.extend([o,dict(o,id=j*2+1)])
 for j in range(3):obs.append(dict(id=8+j,x=(j-1)*.28,y=(j%2-.5)*.3,z=1.5+j*.1,radius=.2,color=[.85,.15+j*.15,.1,.6],mode=3,role='foreground'))
 return sorted(obs,key=lambda o:o['z'],reverse=True)
def compatible(a,b):
 return a.get('role')==b.get('role')=='background' and a['mode']==b['mode']==0 and a['z']>=4 and all(a[k]==b[k] for k in ('x','y','z','radius','color'))
def merge(obs):
 result=[];i=0
 while i<len(obs):
  if i+1<len(obs) and compatible(obs[i],obs[i+1]):result.append(dict(obs[i],mode=7,merged_ids=[obs[i]['id'],obs[i+1]['id']]));i+=2
  else:result.append(dict(obs[i]));i+=1
 return result
def foreground_error(a,b,objects,camera):
 fg=[o for o in objects if o['role']=='foreground'];mask,_=p.cpu(fg,camera)
 indices=[i for i in range(4096) if mask[i*4+3]>0]
 return max(abs(a[i*4+k]-b[i*4+k]) for i in indices for k in range(4))
def global_selection(all_base,all_merge):
 if not all_base:return None
 return 'merged_background' if all_merge else 'baseline'
def contract_valid(rows,parallax,policy):
 if len(rows)!=9 or len(parallax)!=2:return False
 if {(r['camera'],r['variant']) for r in rows}!={(c,v) for c in (-.3,0,.3) for v in ('baseline','merged_background','bad_single_alpha')}:return False
 if not all(r.get('readback_complete') is True for r in rows):return False
 if not all(r['quality']=='FAIL' for r in rows if r['variant']=='bad_single_alpha'):return False
 base=all(r['quality']=='PASS' for r in rows if r['variant']=='baseline') and all(r['status']=='PASS' for r in parallax if r['variant']=='baseline')
 merged=all(r['quality']=='PASS' for r in rows if r['variant']=='merged_background') and all(r['status']=='PASS' for r in parallax if r['variant']=='merged_background')
 return policy['selected']==global_selection(base,merged)
def run(config,output):
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True);objects=scene();compacted=merge(objects);rows=[];artifacts={};selections=[];h=MergeHost(config)
 try:
  for camera in (-.3,0,.3):
   gold,heat=p.cpu(objects,camera);prefix='camera'+str(camera);baseline=None
   variants={'baseline':objects,'merged_background':compacted,'bad_single_alpha':[dict(o,mode=0) if o['mode']==7 else o for o in compacted]}
   artifacts[prefix+'-golden.rgba']=bytes(gold);artifacts[prefix+'-heat.json']=json.dumps(dict(layers=heat,kind='CPU baseline coverage estimate')).encode()
   for name,obs in variants.items():
    pixels=h.draw(obs,camera)
    if baseline is None:baseline=pixels
    metrics=p.metrics(pixels,gold);roi=foreground_error(pixels,gold,objects,camera);good=t.accepted(metrics) and roi<=4
    expected=name!='bad_single_alpha'
    rows.append(dict(camera=camera,variant=name,metrics=metrics,readback_complete=len(pixels)==16384 and all(type(v)is int and 0<=v<=255 for v in pixels),estimated_covered_fragment_samples=sum(p.cpu(obs,camera)[1]),foreground_roi_max_error=roi,draw_count=len(obs),quality='PASS' if good else 'FAIL',expected='PASS' if expected else 'FAIL',status='PASS' if good==expected else 'FAIL',artifact_prefix=prefix+'-'+name))
    artifacts[prefix+'-'+name+'.rgba']=bytes(pixels)
 finally:h.close()
 parallax=[]
 for name in ('baseline','merged_background'):
  views=[r['metrics'] for r in rows if r['variant']==name];shift=views[-1]['alpha_centroid_x']-views[0]['alpha_centroid_x'];ref=views[-1]['cpu_alpha_centroid_x']-views[0]['cpu_alpha_centroid_x']
  parallax.append(dict(variant=name,observed_shift=shift,cpu_shift=ref,error=abs(shift-ref),status='PASS' if abs(shift-ref)<=.1 and abs(shift)>1 else 'FAIL'))
 archive=path.with_suffix('.zip')
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for name,value in sorted(artifacts.items()):
   info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,value)
 r=dict(status='HOST_PASS' if all(x['status']=='PASS' for x in rows+parallax) else 'FAIL',readbacks=9,performance_status='NOT_MEASURED',scope='Only adjacent duplicate background Gaussian-alpha billboards; analytically combined nonlinear alpha profile, not arbitrary Gaussian moment merge or learned 3DGS',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),shader_sha256=dict(vertex=hashlib.sha256(VERT.encode()).hexdigest(),fragment=hashlib.sha256(FRAG.encode()).hexdigest()),selections=selections,baseline_objects=objects,merged_objects=compacted,rows=rows,parallax=parallax,thresholds=dict(max_rgba8_error=4,silhouette_disagree_pixels=2,centroid_error_pixels=.1,foreground_roi_max_error=4),artifact_archive=dict(file=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),instructions='Extract beside report; complete 64x64 bottom-up RGBA8 and baseline coverage arrays'))
 all_merge=all(x['quality']=='PASS' for x in rows if x['variant']=='merged_background') and all(x['status']=='PASS' for x in parallax if x['variant']=='merged_background')
 all_base=all(x['quality']=='PASS' for x in rows if x['variant']=='baseline') and all(x['status']=='PASS' for x in parallax if x['variant']=='baseline')
 selected=global_selection(all_base,all_merge)
 r['global_policy']=dict(selected=selected,status='ACCEPTED_FOR_TESTED_CAMERA_SET' if selected else 'UNAVAILABLE',candidate_rejected=not all_merge,scope='One fixed strategy across all tested cameras, never per-frame optimization switching; unseen cameras still require validation')
 r['contract_status']='PASS' if contract_valid(rows,parallax,r['global_policy']) and len(selections)==3 else 'FAIL'
 path.write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--config',required=True);a.add_argument('--output',required=True);a.add_argument('--require-contract-only',action='store_true');args=a.parse_args();r=run(json.loads(Path(args.config).read_text()),args.output);print(r['status']);raise SystemExit(r['contract_status']!='PASS' if args.require_contract_only else r['status']!='HOST_PASS')
