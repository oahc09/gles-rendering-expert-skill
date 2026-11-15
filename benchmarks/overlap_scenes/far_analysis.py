#!/usr/bin/env python3
"""Read-only spatial error decomposition of retained far-resolution evidence."""
import argparse,hashlib,json,zipfile
from pathlib import Path
import far_resolution as f

def stats(actual,gold,indices):
 indices=list(indices)
 if not indices:return dict(pixels=0,max_rgb=0,max_alpha=0,mean_rgb=0,mean_alpha=0,over_budget_pixels=0,silhouette_disagree=0)
 rgb=[abs(actual[i*4+k]-gold[i*4+k]) for i in indices for k in range(3)];alpha=[abs(actual[i*4+3]-gold[i*4+3]) for i in indices]
 return dict(pixels=len(indices),max_rgb=max(rgb),max_alpha=max(alpha),mean_rgb=sum(rgb)/len(rgb),mean_alpha=sum(alpha)/len(alpha),over_budget_pixels=sum(max(abs(actual[i*4+k]-gold[i*4+k]) for k in range(4))>4 for i in indices),silhouette_disagree=sum((actual[i*4+3]>12)!=(gold[i*4+3]>12) for i in indices))
def memberships(objects,camera,x,y):
 out=[]
 for o in objects:
  cx,cy,rx,ry=f.p.project(o,camera)
  if abs((x/64*2-1-cx)/rx)<1 and abs((y/64*2-1-cy)/ry)<1:out.append(o['id'])
 return tuple(out)
def analyze(report_path):
 r=json.loads(report_path.read_text());archive=report_path.parent/r['artifact_archive']['file']
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=r['artifact_archive']['sha256']:raise ValueError('archive hash mismatch')
 far=r['scene']['far'];near=r['scene']['foreground'];views=[]
 with zipfile.ZipFile(archive) as z:
  for row in r['rows']:
   if row['variant']!='far_half':continue
   camera=row['camera'];prefix=row['artifact_prefix'];gold=list(z.read('cam'+str(camera)+'-gold.rgba'));actual=list(z.read(prefix+'.rgba'));own=list(z.read(prefix+'-mechanism-cpu.rgba'))
   if not all(len(x)==16384 for x in (gold,actual,own)):raise ValueError('incomplete image')
   if own!=f.cpu(far,near,camera,32) or gold!=f.cpu(far,near,camera,64):raise ValueError('saved CPU oracle mismatch')
   roi=f.cpu_layers(near,camera,64);groups={k:[] for k in ['foreground_roi','outside_foreground','far_boundary_membership_changed','far_membership_same','inside_far_full_support','outside_far_full_support']}
   phases={str((x,y)):[] for y in (0,1) for x in (0,1)}
   for i in range(4096):
    x,y=i%64,i//64
    full=memberships(far,camera,x+.5,y+.5);low=memberships(far,camera,(x//2)*2+1,(y//2)*2+1)
    groups['foreground_roi' if roi[i*4+3]>0 else 'outside_foreground'].append(i)
    groups['far_boundary_membership_changed' if full!=low else 'far_membership_same'].append(i)
    groups['inside_far_full_support' if full else 'outside_far_full_support'].append(i)
    phases[str((x%2,y%2))].append(i)
   views.append(dict(camera=camera,actual_vs_original=stats(actual,gold,range(4096)),mechanism_cpu_vs_original=stats(own,gold,range(4096)),actual_vs_mechanism_cpu=stats(actual,own,range(4096)),regions={k:dict(actual=stats(actual,gold,v),cpu_resampling=stats(own,gold,v)) for k,v in groups.items()},nearest_phase={k:stats(own,gold,v) for k,v in phases.items()}))
 return dict(input_report=report_path.name,input_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),archive_sha256=r['artifact_archive']['sha256'],views=views)
def run(paths,output):
 result=dict(status='ANALYZED',thresholds_unchanged=dict(max_channel_error=4,silhouette_alpha_threshold=12),reports=[analyze(p) for p in paths],interpretation='Nearest 32->64 maps each 2x2 block to one low-grid center, offset ±0.5 full-resolution pixels per axis. CPU32-vs-CPU64 measures joint resampling, quantization, bounding truncation and subsequent foreground compositing; it is not an additive/unique causal attribution. Changed-membership regions flag hard Gaussian rectangle truncation opportunities, not proof of dominant causation. Same-membership errors can arise from nonlinear Gaussian sampling, nearest reconstruction and RGBA8 blend quantization. Driver residual is separately retained.',scope='Analysis only: no changed oracle/budget, new optimization acceptance, GL execution or performance claim.')
 Path(output).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--reports',nargs='+',type=Path,required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.reports,a.output)
