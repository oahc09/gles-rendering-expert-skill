#!/usr/bin/env python3
"""Actual L1 execution; reuses v1.0.5 image comparator and immutable baselines."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.append(str(ROOT/'benchmarks/visual_quality'))
from compare import compare,read_ppm
from numeric_reference import evaluate
CONFIG=json.loads((ROOT/'benchmarks/visual_quality/thresholds.json').read_text())
SCENES=('glass','sand','particle','shadowwater','forwardplus')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(cmd):
 r=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,timeout=90)
 if r.returncode:raise RuntimeError(f'{cmd}: {r.returncode}: {r.stderr}')
 return {'command':[str(x) for x in cmd],'stdout':r.stdout,'stderr':r.stderr,'returncode':r.returncode}
def validate_manifest(manifest,golden):
 expected={scene+'.ppm' for scene in SCENES}
 if not isinstance(manifest,dict) or set(manifest.get('images',{}))!=expected:raise ValueError('Exact five-scene inventory required')
 if manifest.get('schema_version')!=1 or manifest.get('size')!=[96,96] or manifest.get('seed')!=1337 or manifest.get('interaction')!=0:raise ValueError('Golden capture contract differs')
 if manifest.get('color_space')!='RGB8 engineering output, shader explicit transfers; no display HDR/WCG' or manifest.get('compression')!='none':raise ValueError('Golden color/format contract differs')
 if manifest.get('comparison_config_sha256')!=sha(ROOT/'benchmarks/visual_quality/thresholds.json'):raise ValueError('Comparison configuration requires explicit review')
 sources=manifest.get('source_hashes')
 if not isinstance(sources,dict) or not sources or any(not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in sources.values()):raise ValueError('Historical producer hashes required')
 for name,entry in manifest['images'].items():
  if not isinstance(entry,dict) or entry.get('sha256')!=sha(golden/name):raise ValueError('Reference integrity failed: '+name)
  metadata=entry.get('metadata',{})
  if metadata.get('scene')!=name[:-4] or metadata.get('mode')!='baseline' or metadata.get('touch')!=0 or metadata.get('seed')!=1337 or not isinstance(metadata.get('renderer'),str) or not metadata['renderer']:raise ValueError('Golden per-image metadata differs')
  w,h,_=read_ppm(golden/name)
  if (w,h)!=(96,96):raise ValueError('Golden actual dimensions differ')
 return True
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,default=Path('/tmp/gles-system-scenes'));p.add_argument('--output',type=Path,default=Path('/tmp/gles-system-report'));p.add_argument('--accept-goldens',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);golden=HERE/'golden';manifest={'images':{}};rows=[];fail=[]
 if not a.accept_goldens:
  manifest=json.loads((golden/'manifest.json').read_text())
  validate_manifest(manifest,golden)
 for scene in SCENES:
  baseline=a.output/(scene+'.ppm');row=run([a.build/'effects',scene,baseline,'baseline',0]);row['capture']=json.loads(row['stdout']);ref=golden/(scene+'.ppm')
  if a.accept_goldens:ref.write_bytes(baseline.read_bytes());manifest['images'][ref.name]={'sha256':sha(ref),'metadata':row['capture']}
  else:
   row['golden_comparison']=compare(ref,baseline,CONFIG,'P06' if scene in ('sand','particle') else 'P03')
   if not row['golden_comparison']['pass']:fail.append(scene+' baseline regression')
  rows.append(row)
  for mode,touch in [('degraded',0),('baseline',1)]+([('sorted',0)] if scene in ('sand','particle') else [('fallback',0)] if scene=='forwardplus' else []):
   path=a.output/f'{scene}-{mode}-{touch}.ppm';r=run([a.build/'effects',scene,path,mode,touch]);r['difference']=compare(baseline,path,CONFIG,'P06' if scene in ('sand','particle') else 'P03',a.output/f'{scene}-{mode}-{touch}-heat.ppm');r.update(scene=scene,mode=mode,touch=touch)
   if mode=='degraded' and r['difference']['pass']:fail.append(scene+' fault not detected')
   if touch and r['difference']['pass']:fail.append(scene+' interaction has no detectable output')
   if mode=='fallback' and not r['difference']['pass']:fail.append('forwardplus all-lights reference differs')
   # Sorted transparency is a non-equivalent correctness fallback, not an OIT oracle.
   rows.append(r)
 for group in range(1,13):
  positive=a.output/f'precision-{group}-positive.ppm';negative=a.output/f'precision-{group}-negative.ppm'
  r=run([a.build/'precision',group,'positive',positive]);r.update(group=group,kind='precision');run([a.build/'precision',group,'negative',negative]);r['comparison']=compare(positive,negative,CONFIG,'P06');w,h,px=read_ppm(positive);r['positive_mean_rgb']=sum(px)/len(px);r['cpu_positive_oracle']=evaluate(group,w,h,px);
  if not r['cpu_positive_oracle']['pass']:fail.append(f'precision group {group} positive oracle failed')
  r['negative_detected']=not r['comparison']['pass']
  if not r['negative_detected']:fail.append(f'precision group {group} fault not detected')
  rows.append(r)
 for kind in ('particle','boids','wave'):
  for steps in (1,16,64):
   for mode in ('cpu','gpu','degraded'):
    path=a.output/f'{kind}-{steps}-{mode}.json';r=run([a.build/'simulation',kind,steps,mode,path]);data=json.loads(path.read_text());r['simulation']=data;r['raw_sha256']=sha(path)
    if data['within_tolerance']!=(mode!='degraded'):fail.append(f'{kind}/{steps}/{mode} unexpected numeric result')
    if mode!='cpu':r['gpu_draw_capture_sha256']=sha(str(path)+'.ppm')
    rows.append(r)
 if a.accept_goldens:
  manifest.update(schema_version=1,comparison_config_sha256=sha(ROOT/'benchmarks/visual_quality/thresholds.json'),created_at=datetime.now(timezone.utc).isoformat(),source_hashes={p.name:sha(p) for p in (ROOT/'examples/system_scenes').glob('*') if p.is_file()},size=[96,96],color_space='RGB8 engineering output, shader explicit transfers; no display HDR/WCG',compression='none',seed=1337,interaction=0,hardware='software Mesa only')
  (golden/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 report={'status':'BASELINES_CREATED_NOT_VALIDATED' if a.accept_goldens else ('FAIL' if fail else 'PASS'),'layer':'L1_SOFTWARE_GLES','device':'NOT_RUN_DEVICE','failures':fail,'rows':rows,'binary_hashes':{n:sha(a.build/n) for n in ('simulation','effects','precision')},'source_hashes':{p.name:sha(p) for p in (ROOT/'examples/system_scenes').glob('*') if p.is_file()},'numeric_reference_sha256':sha(HERE/'numeric_reference.py'),'golden_manifest_sha256':sha(golden/'manifest.json'),'runner_sha256':sha(__file__),'comparator_sha256':sha(ROOT/'benchmarks/visual_quality/compare.py'),'threshold_sha256':sha(ROOT/'benchmarks/visual_quality/thresholds.json')}
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),fail);return bool(fail)
if __name__=='__main__':sys.exit(main())
