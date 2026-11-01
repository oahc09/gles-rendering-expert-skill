#!/usr/bin/env python3
"""Actual restricted software context plus explicitly injected missing-capability tests."""
from pathlib import Path
import json,os,subprocess,hashlib
from run import compare,CONFIG,HERE
binary=Path('/tmp/gles-system-scenes');rows=[]
jobs=[('forwardplus','fallback',{'MESA_GLES_VERSION_OVERRIDE':'3.0'},0),('sand','sorted',{'MESA_GLES_VERSION_OVERRIDE':'3.0'},0),('particle','fallback',{'MESA_GLES_VERSION_OVERRIDE':'3.0','GLES_TEST_FORCE_NO_RGBA16F':'1'},0),('sand','baseline',{'GLES_TEST_FORCE_NO_RGBA16F':'1'},3),('particle','sorted',{'GLES_TEST_FORCE_NO_RGBA16F':'1'},0)]
for i,(scene,mode,override,expected) in enumerate(jobs):
 path=Path('/tmp')/f'gles-capability-{i}.ppm';cmd=[str(binary/'effects'),scene,str(path),mode,'0'];r=subprocess.run(cmd,env=dict(os.environ,**override),capture_output=True,text=True);row={'command':cmd,'override':override,'returncode':r.returncode,'expected':expected,'stdout':r.stdout,'stderr':r.stderr}
 if r.returncode==0:
  capture=json.loads(r.stdout);row['capture']=capture
  if override.get('MESA_GLES_VERSION_OVERRIDE')=='3.0' and not capture['version'].startswith('OpenGL ES 3.0'):raise RuntimeError('Restricted software API version not confirmed')
  row['image_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
  if scene=='forwardplus':row['comparison']=compare(HERE/'golden/forwardplus.ppm',path,CONFIG,'P03')
 rows.append(row)
for mode,expected in [('gpu',1),('cpu',0)]:
 cmd=[str(binary/'simulation'),'particle','16',mode,f'/tmp/gles-capability-{mode}.json'];r=subprocess.run(cmd,env=dict(os.environ,MESA_GLES_VERSION_OVERRIDE='3.0'),capture_output=True,text=True);rows.append({'command':cmd,'override':{'MESA_GLES_VERSION_OVERRIDE':'3.0'},'returncode':r.returncode,'expected':expected,'stdout':r.stdout,'stderr':r.stderr})
report={'status':'PASS' if all(r['returncode']==r['expected'] and r.get('comparison',{}).get('pass',True) for r in rows) else 'FAIL','scope':'Mesa GLES3.0 restriction + synthetic missing16F hook; NOT physical unsupported hardware','rows':rows,'binary_hashes':{name:hashlib.sha256((binary/name).read_bytes()).hexdigest() for name in ('effects','simulation')}}
(HERE/'capability-fallback-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status']);raise SystemExit(report['status']!='PASS')
