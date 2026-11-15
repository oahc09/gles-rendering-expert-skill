"""Actual C++17 GLES interactions; sanitized source-bound report, not timing."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCES=['examples/closure/gles-runtime/state_interactions.cpp','examples/validation/egl_smoke.cpp','references/examples/pbo_streaming_upload.cpp']
def run():
 with tempfile.TemporaryDirectory() as tmp:
  binary=Path(tmp)/'states'
  compile=subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-Wno-unused-function',str(ROOT/SOURCES[0]),'-lEGL','-lGLESv2','-pthread','-o',str(binary)],capture_output=True,text=True)
  result={'schema_version':1,'scope':'48 distinct software GL legal/error interactions; not performance or physical-device validation','source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},'compile':'PASS' if compile.returncode==0 else 'FAIL','execution_class':'SOFTWARE_GLES','device':None,'provider':None,'rows':[],'status':'FAIL'}
  if compile.returncode:raise RuntimeError(compile.stderr)
  child=subprocess.run([str(binary)],capture_output=True,text=True,env={**os.environ,'MESA_SHADER_CACHE_DISABLE':'true'})
  if child.returncode:raise RuntimeError(child.stderr)
  lines=[json.loads(line) for line in child.stdout.splitlines()]
  if len(lines)!=49 or lines[-1]!={'status':'PASS','checks':48,'execution_class':'SOFTWARE_GLES','physical_performance':None}:raise ValueError('missing or failed execution summary')
  rows=lines[:-1]
  if len(rows)!=48 or len({x['case'] for x in rows})!=48 or any(x['observed']!=x['expected'] or x['status']!='PASS' for x in rows):raise ValueError('incomplete/error mismatch')
  result.update(rows=rows,status='PASS');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();x=run();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'status':x['status'],'checks':len(x['rows'])}))
