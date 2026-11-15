#!/usr/bin/env python3
"""Read-only threshold-crossing analysis, not a relaxed image oracle."""
import argparse,hashlib,json,math,zipfile
from pathlib import Path
import far_reconstruction as f

def load(path):
 report=json.loads(path.read_text());archive=path.parent/report['artifact_archive']['file']
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=report['artifact_archive']['sha256']:raise ValueError('archive digest mismatch')
 with zipfile.ZipFile(archive) as z:images={name:list(z.read(name)) for name in z.namelist()}
 return report,images

def analyze(root):
 records={d:load(root/f'far-reconstruction-{d}.json') for d in ('mesa','angle')};gold=records['mesa'][1]['cam0-gold.rgba'];far=records['mesa'][0]['scene']['far'];near=records['mesa'][0]['scene']['foreground']
 if gold!=records['angle'][1]['cam0-gold.rgba'] or gold!=f.cpu(far,near,0,64):raise ValueError('independent full oracle mismatch')
 low=f.cpu_layers(far,0,32);roi=f.cpu_layers(near,0,64);points=[]
 counts={d:0 for d in records}
 for i in range(4096):
  actual={d:images['cam0-far_bilinear.rgba'][i*4:i*4+4] for d,(_,images) in records.items()}
  mismatch={d:(p[3]>12)!=(gold[i*4+3]>12) for d,p in actual.items()}
  for d in counts:counts[d]+=mismatch[d]
  if not any(mismatch.values()):continue
  x,y=i%64,i//64;u=(x+.5)/2-.5;v=(y+.5)/2-.5;ix,iy=math.floor(u),math.floor(v);wx,wy=u-ix,v-iy
  samples=[];weighted=[0.]*4
  for dx,dy,w in [(0,0,(1-wx)*(1-wy)),(1,0,wx*(1-wy)),(0,1,(1-wx)*wy),(1,1,wx*wy)]:
   xx,yy=max(0,min(31,ix+dx)),max(0,min(31,iy+dy));rgba=low[(yy*32+xx)*4:(yy*32+xx)*4+4];samples.append(dict(x=xx,y=yy,weight=w,cpu_rgba=rgba))
   for k in range(4):weighted[k]+=rgba[k]*w
  images=records['mesa'][1];own=images['cam0-far_bilinear-mechanism-cpu.rgba'][i*4:i*4+4]
  if roi[i*4+3]:raise ValueError('unexpected foreground contribution at examined points')
  points.append(dict(x=x,y=y,coordinate_convention='zero-based bottom-up',cpu_full64=gold[i*4:i*4+4],cpu_bilinear_own=own,actual=actual,actual_baseline={d:imgs['cam0-baseline.rgba'][i*4:i*4+4] for d,(_,imgs) in records.items()},silhouette_mismatch=mismatch,alpha_gt12={**{d:p[3]>12 for d,p in actual.items()},'cpu_full64':gold[i*4+3]>12,'cpu_own':own[3]>12},cpu_low32_samples=samples,cpu_weighted_rgba=weighted,cpu_round_half_up=[math.floor(c+.5) for c in weighted],alpha_distance_to_round_boundary12_5=weighted[3]-12.5,foreground_coverage=False,mesa_extra=mismatch['mesa'] and not mismatch['angle']))
 return dict(status='ANALYZED',camera=0,threshold_alpha_gt=12,silhouette_budget_unchanged=2,mismatch_counts=counts,points=points,inputs={d:dict(report_sha256=hashlib.sha256((root/f'far-reconstruction-{d}.json').read_bytes()).hexdigest(),archive_sha256=r['artifact_archive']['sha256']) for d,(r,_) in records.items()},interpretation='CPU low32 samples are analytical and independently quantized, not actual intermediate framebuffer captures. Final pixels alone cannot distinguish low32 blend rounding from resolve arithmetic/conversion or combined effects. Normalized fixed-point conversion/blending precision is not uniquely represented by this half-up CPU oracle; a one-code driver difference is not sufficient proof of a spec violation. No threshold/budget change or unique causal attribution is made.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.write_text(json.dumps(analyze(a.evidence_root),indent=2)+'\n')
