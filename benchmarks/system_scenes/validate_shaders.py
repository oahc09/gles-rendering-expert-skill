#!/usr/bin/env python3
"""Validate exact runtime shader captures; deduplicate identical sources by SHA."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,default=Path('/tmp/gles-system-scenes'));p.add_argument('--glslang',default='/tmp/gles-local-deps/root/usr/bin/glslangValidator');p.add_argument('--output',type=Path,default=Path('/tmp/gles-system-shaders'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);a.glslang=shutil.which(a.glslang) or a.glslang
jobs=[]
for scene in ('glass','sand','particle','shadowwater','forwardplus'):
 for mode in ('baseline','degraded')+ (('sorted',) if scene in ('sand','particle') else ('fallback',) if scene=='forwardplus' else ()):
  jobs.append(('effects',[scene,'capture.ppm',mode,'0']))
for scene in ('particle','boids','wave'):jobs.append(('simulation',[scene,'16','gpu','capture.json']))
for group in range(1,13):
 for mode in ('positive','negative'):jobs.append(('precision',[str(group),mode,'capture.ppm']))
results={};captures=[]
for index,(name,args) in enumerate(jobs):
 folder=a.output/str(index);folder.mkdir(exist_ok=True);env=dict(os.environ,GLES_SYSTEM_SHADER_DUMP=str(folder));cmd=[str(a.build/name)]+[str(folder/x) if x.startswith('capture.') else x for x in args];r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=60)
 if r.returncode:raise RuntimeError(r.stderr)
 files=[f for f in folder.iterdir() if f.suffix in ('.vert','.frag','.comp')]
 if not files:raise RuntimeError('Runtime shader source capture empty')
 captures.append({'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'stages':len(files)})
 for f in files:
  digest=hashlib.sha256(f.read_bytes()).hexdigest()
  if digest in results:results[digest]['occurrences']+=1;continue
  check=subprocess.run([a.glslang,str(f)],capture_output=True,text=True,timeout=30)
  results[digest]={'source':str(f),'source_sha256':digest,'stage':f.suffix,'occurrences':1,'returncode':check.returncode,'stdout':check.stdout,'stderr':check.stderr}
report={'status':'PASS' if all(r['returncode']==0 for r in results.values()) else 'FAIL','runtime_capture_jobs':len(jobs),'unique_shader_stages':len(results),'total_runtime_stages':sum(r['occurrences'] for r in results.values()),'binary_hashes':{n:hashlib.sha256((a.build/n).read_bytes()).hexdigest() for n in ('effects','simulation','precision')},'validator_sha256':hashlib.sha256(Path(a.glslang).read_bytes()).hexdigest(),'captures':captures,'results':list(results.values())}
(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],report['unique_shader_stages'],report['total_runtime_stages']);raise SystemExit(report['status']!='PASS')
