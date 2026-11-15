"""Check minimal public v109 evidence: correctness data, never local environment inventory."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN={'metadata','compiler_sha256','compiler_version','config_sha256','icd_sha256','executable_sha256','library_sha256','loaded_libraries','environment','os_release','hostname'}
def check(value,path='$'):
 errors=[]
 if isinstance(value,dict):
  for k,v in value.items():
   if k in FORBIDDEN:errors.append(path+'.'+k+': private environment inventory')
   errors.extend(check(v,path+'.'+k))
 elif isinstance(value,list):
  for i,v in enumerate(value):errors.extend(check(v,f'{path}[{i}]'))
 elif isinstance(value,str) and re.search(r'(?<!https:)(?:/tmp/|/workspace/|/home/|/usr/lib/|/usr/bin/)',value):
  errors.append(path+': local absolute path')
 return errors
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('files',nargs='*',type=Path);a=p.parse_args()
 paths=a.files or [p for folder in ('shader_ab','overlap_scenes','texture_access') for p in (ROOT/'benchmarks'/folder/'evidence').glob('*.json')]
 errors=[]
 for f in paths:
  try:errors.extend(f.name+': '+x for x in check(json.loads(f.read_text())))
  except (ValueError,OSError) as e:errors.append(f.name+': '+str(e))
 print(json.dumps({'status':'FAIL' if errors else 'PASS','files':len(paths),'errors':errors},indent=2));raise SystemExit(bool(errors))
