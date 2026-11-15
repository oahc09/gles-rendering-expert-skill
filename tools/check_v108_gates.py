"""Additive v108 bookkeeping. Preserves and executes every predecessor gate."""
import argparse,json,subprocess,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check(data):
 assert data['target_version']=='1.0.8'
 assert set(data['work_packages'])=={f'W{i}' for i in range(9)}
 assert data['prior_release_gate']=='docs/v1.0.7-release-gates.json'
 assert data['release_ready'] is False and data['release_authorized'] is False
 assert not data.get('accepted_limitations')
 for item in data['work_packages'].values():
  assert item['status'] in ('PASS','PARTIAL','NOT_RUN','BLOCKED_BY_HARDWARE','BLOCKED_BY_PROVIDER')
  assert item['remaining'] and item['implementation']
  for p in item['implementation']:assert (ROOT/p).is_file(),p
 assert re.search(r'^\s*version:\s*[\"\']?1\.0\.2\b',(ROOT/'SKILL.md').read_text(),re.M)
 return False
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--require-release',action='store_true');a=p.parse_args()
 for v in ('1.0.3','1.0.4','1.0.5','1.0.6','1.0.7'):
  subprocess.run([sys.executable,str(ROOT/'tools/check_release_gates.py'),'--gates','v'+v],check=True,stdout=subprocess.DEVNULL)
 data=json.loads((ROOT/'docs/v1.0.8/release-gates.json').read_text());ready=check(data)
 print(json.dumps({'candidate_bookkeeping':'PASS','release_ready':ready,'note':'v108 recovery candidate remains blocked; no metadata bump'}));sys.exit(2 if a.require_release else 0)
