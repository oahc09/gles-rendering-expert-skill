"""v1.1.0 candidate evidence bookkeeping, never a manual text release override."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def check(root=ROOT):
 root=Path(root);g=json.loads((root/'docs/v1.1.0/release-gates.json').read_text());ledger=json.loads((root/'docs/v1.1.0/debt-ledger.json').read_text())
 if g.get('target_version')!='1.1.0' or g.get('release_ready') is not False or g.get('release_authorized') is not False or g.get('accepted_limitations')!=[]:raise ValueError('no release readiness/authorization/waiver')
 if set(g['work_packages'])!={f'W{i}' for i in range(13)}:raise ValueError('missing package')
 for d in ledger['debts']:
  p=root/d['path']
  if hashlib.sha256(p.read_bytes()).hexdigest()!=d['sha256'] or json.loads(p.read_text())!=d['gate']:raise ValueError('predecessor gate altered')
 for w in g['work_packages'].values():
  if not w['status'] or not w['remaining']:raise ValueError('unexplained status')
  for path in w['evidence']:
   p=(root/path).resolve()
   if not p.is_relative_to(root.resolve()) or not p.is_file():raise ValueError('missing/escaped evidence')
 if g['prior_release_gate']!='docs/v1.0.9/release-gates.json':raise ValueError('predecessor disconnected')
 return {'status':'CANDIDATE_CONTRACT_PASS','release_ready':False,'release_authorized':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--require-release',action='store_true');a=p.parse_args();subprocess.run([sys.executable,str(ROOT/'tools/check_v109_gates.py')],check=True,stdout=subprocess.DEVNULL);print(json.dumps(check()));raise SystemExit(2 if a.require_release else 0)
