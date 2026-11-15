"""Six bounded subprocesses: three justified controls per implementation."""
import argparse,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def suite(mesa,angle,output):
 rows=[]
 with tempfile.TemporaryDirectory() as td:
  for driver,config in [('mesa',mesa),('angle',angle)]:
   for attachment,fetch in [('texture',False),('texture',True),('renderbuffer',True)]:
    p=Path(td)/f'{driver}-{attachment}-{fetch}.json';cmd=[sys.executable,str(HERE/'probe.py'),'--config',str(config),'--attachment',attachment,'--output',str(p)]+(['--fetch'] if fetch else [])
    try:
     r=subprocess.run(cmd,capture_output=True,timeout=20);rows.append(dict(case=f'{driver}-{attachment}-{fetch}',exit=r.returncode,report=json.loads(p.read_text()) if p.exists() else None))
    except subprocess.TimeoutExpired:rows.append(dict(case=f'{driver}-{attachment}-{fetch}',exit=None,report=None,failure='TIMEOUT'))
 result=dict(status='FAIL' if any(r['exit']!=0 or not r['report'] or r['report'].get('status')!='PASS' for r in rows) else 'HOST_PASS',rows=rows,source_sha256=hashlib.sha256((HERE/'probe.py').read_bytes()).hexdigest(),suite_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),performance_claim=False,root_cause_proven=False)
 output.write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--mesa',type=Path,required=True);p.add_argument('--angle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=suite(a.mesa,a.angle,a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
