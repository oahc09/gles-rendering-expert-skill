#!/usr/bin/env python3
"""Compile exact dumped runtime shader sources with glslang (not an alternate shader)."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
from run import SCENES,execute
p=argparse.ArgumentParser();p.add_argument('--binary',default='/tmp/gles-precision-lab/precision-lab');p.add_argument('--glslang',default='glslangValidator');p.add_argument('--output',type=Path,default=Path('/tmp/gles-precision-shaders'));a=p.parse_args();a.glslang=shutil.which(a.glslang) or a.glslang;a.output.mkdir(parents=True,exist_ok=True)
results=[]
for scene in SCENES:
 for mode in ('baseline','degraded','mediump'):
  out=a.output/(scene+'-'+mode);out.mkdir(exist_ok=True)
  os.environ['GLES_PRECISION_SHADER_DUMP']=str(out)
  execute(a.binary,scene,out/'frame.ppm',1,10000,mode)
  files=sorted(p for p in out.iterdir() if p.suffix in ('.vert','.frag','.comp'))
  if not files:raise RuntimeError('No dumped runtime shaders')
  for source in files:
   cmd=[a.glslang,str(source)];r=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
   results.append({'scene':scene,'mode':mode,'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
report={'status':'PASS' if all(r['returncode']==0 for r in results) else 'FAIL','scope':'exact runtime GLSL stage compilation; actual GLES host execution separately links programs','binary_sha256':hashlib.sha256(Path(a.binary).read_bytes()).hexdigest(),'validator_sha256':hashlib.sha256(Path(a.glslang).read_bytes()).hexdigest(),'stage_count':len(results),'results':results}
(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(results));raise SystemExit(report['status']!='PASS')
