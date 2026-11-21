"""Process-isolated real probes; renderer faults remain FAIL, not skipped/PASS."""
import argparse,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def suite(config,output):
 rows=[]
 with tempfile.TemporaryDirectory() as td:
  for mode in ('coherent','noncoherent','fallback'):
   p=Path(td)/(mode+'.json')
   try:
    r=subprocess.run([sys.executable,str(HERE/'run.py'),'--mode',mode,'--config',str(config),'--output',str(p)],capture_output=True,timeout=45)
    row={'mode':mode,'process_exit_code':r.returncode}
    if r.returncode==0 and p.exists():row.update(status='PASS' if json.loads(p.read_text())['status']=='HOST_PASS' else 'NOT_SUPPORTED',evidence=json.loads(p.read_text()))
    else:row.update(status='FAIL',failure='PROCESS_SIGNAL' if r.returncode<0 else 'PROBE_FAILURE')
   except subprocess.TimeoutExpired:row={'mode':mode,'status':'FAIL','failure':'TIMEOUT','process_exit_code':None}
   rows.append(row)
 result={'status':'FAIL' if any(r['status']=='FAIL' for r in rows) else 'PARTIAL_UNSUPPORTED' if any(r['status']=='NOT_SUPPORTED' for r in rows) else 'HOST_PASS','rows':rows,'fallback_status':next(r['status'] for r in rows if r['mode']=='fallback'),'scope':'isolated actual software probes; failures preserved; no hardware/PLS/performance claim','suite_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'probe_sha256':hashlib.sha256((HERE/'run.py').read_bytes()).hexdigest()}
 Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=suite(a.config,a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
