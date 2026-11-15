"""Validate candidate bookkeeping without claiming release authorization."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATUSES={'PASS','PARTIAL','NOT_RUN','BLOCKED_BY_HARDWARE','BLOCKED_BY_PROVIDER'}
def check(data, inherited):
 if data.get('target_version')!='1.0.9' or data.get('release_ready') is not False or data.get('release_authorized') is not False: raise ValueError('candidate is not release-ready or authorized')
 if data.get('accepted_limitations')!=[]: raise ValueError('no inherited waiver')
 if set(data.get('work_packages',{}))!={f'W{i}' for i in range(11)}: raise ValueError('work packages')
 for row in inherited['gates']:
  p=ROOT/row['path']
  if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256'] or json.loads(p.read_text())!=row['gate']: raise ValueError('inherited gate changed: '+str(p))
 for row in data['work_packages'].values():
  if row['status'] not in STATUSES or not row['remaining']: raise ValueError('status/remaining')
  for p in row['implementation']:
   if not (ROOT/p).is_file(): raise ValueError('missing '+p)
 return {'candidate_bookkeeping':'PASS','release_ready':False,'hardware':'BLOCKED_BY_HARDWARE','provider':'BLOCKED_BY_PROVIDER'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--require-release',action='store_true');a=p.parse_args()
 subprocess.run([sys.executable,str(ROOT/'tools/check_v108_gates.py')],check=True,stdout=subprocess.DEVNULL)
 print(json.dumps(check(json.loads((ROOT/'docs/v1.0.9/release-gates.json').read_text()),json.loads((ROOT/'docs/v1.0.9/inherited-gates.json').read_text()))))
 sys.exit(2 if a.require_release else 0)
