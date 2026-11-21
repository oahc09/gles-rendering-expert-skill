#!/usr/bin/env python3
"""Freeze upstream enumeration, execute real CTS, retain case-only QPA."""
import argparse,hashlib,json,pathlib,subprocess,sys,gzip
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/coverage'))
from cts_results import report,parse_qpa
PATTERN='dEQP-GLES3.functional.fbo.completeness.*'
def case_records(raw):
 lines=[];inside=False
 for line in raw.splitlines():
  if line.startswith('#beginTestCaseResult '):inside=True
  if inside:lines.append(line)
  if line=='#endTestCaseResult':inside=False
 result='\n'.join(lines)+'\n';parse_qpa(result)
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--executable',type=pathlib.Path,required=True);p.add_argument('--private-dir',type=pathlib.Path,required=True);p.add_argument('--build-receipt',type=pathlib.Path,required=True);p.add_argument('--output-dir',type=pathlib.Path,required=True);a=p.parse_args()
 exe=a.executable.resolve();priv=a.private_dir.resolve();out=a.output_dir.resolve();priv.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
 receipt=json.loads(a.build_receipt.read_text())
 if receipt.get('source_revision')!='5bb4c7e83acea0fc73e3333625e4f20542e584d0' or receipt.get('tracked_source_clean') is not True or receipt.get('build_exit_code')!=0 or receipt.get('executable_sha256')!=hashlib.sha256(exe.read_bytes()).hexdigest():raise SystemExit('build receipt mismatch')
 cmd=[str(exe),'--deqp-case='+PATTERN,'--deqp-surface-type=pbuffer','--deqp-surface-width=64','--deqp-surface-height=64']
 r=subprocess.run(cmd+['--deqp-runmode=txt-caselist','--deqp-caselist-export-file='+str(priv/'enumeration.txt')],cwd=exe.parent,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
 (priv/'enumeration-console.txt').write_bytes(r.stdout)
 if r.returncode:raise SystemExit('CTS enumeration failed; no execution accepted')
 cases=[x[6:] for x in (priv/'enumeration.txt').read_text().splitlines() if x.startswith('TEST: ')]
 if not cases or len(cases)!=len(set(cases)) or any(not x.startswith(PATTERN[:-1]) for x in cases):raise SystemExit('invalid enumeration')
 expected='\n'.join(cases)+'\n';(out/'expected.txt').write_text(expected) # freeze BEFORE execution
 r=subprocess.run(cmd+['--deqp-log-filename='+str(priv/'original.qpa')],cwd=exe.parent,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
 (priv/'execution-console.txt').write_bytes(r.stdout)
 public=case_records((priv/'original.qpa').read_text()).encode();archive=gzip.compress(public,mtime=0);(out/'cases.qpa.gz').write_bytes(archive)
 result=report(public,cases,r.returncode);result.update({'source_revision':'5bb4c7e83acea0fc73e3333625e4f20542e584d0','scope':'software host; FBO completeness subset only','artifact':'cases.qpa.gz','artifact_sha256':hashlib.sha256(archive).hexdigest(),'performance_claim':False,'requested_pattern':PATTERN,'expected_sha256':hashlib.sha256(expected.encode()).hexdigest(),'redaction':'Only complete case records retained; session headers omitted. raw_qpa_sha256 refers to case-only published bytes, not private original.','build_receipt_sha256':hashlib.sha256(a.build_receipt.read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()})
 (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'cases':len(cases)}));raise SystemExit(result['status']!='PASS')
if __name__=='__main__':main()
