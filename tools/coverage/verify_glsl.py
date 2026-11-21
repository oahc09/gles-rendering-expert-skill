#!/usr/bin/env python3
"""Real glslang link and GLES compile/link; never regex language acceptance."""
import argparse,ctypes as C,hashlib,importlib.util,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'benchmarks/coverage/glsl'))
from corpus import cases
spec=importlib.util.spec_from_file_location('glsl_diff',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
class Host(d.Host):
 def shader(self,source,stage):
  obj=self.fn('glCreateShader',d.U,[d.U])({'vert':0x8b31,'frag':0x8b30,'comp':0x91b9,'geom':0x8dd9,'tesc':0x8e88,'tese':0x8e87}[stage]);raw=C.c_char_p(source.encode());self.fn('glShaderSource',None,[d.U,d.I,C.POINTER(C.c_char_p),d.P])(obj,1,C.byref(raw),None);self.fn('glCompileShader',None,[d.U])(obj);ok=d.I();self.fn('glGetShaderiv',None,[d.U,d.U,d.P])(obj,0x8b81,C.byref(ok));return obj,bool(ok.value),''
def contract_valid(report):
 expected={c['id']:c for c in cases()};rows=report.get('rows',[])
 if report.get('runtime')!='ACTUAL_GLES_COMPILE_LINK' or len(rows)!=len(expected) or {x.get('id') for x in rows}!=set(expected):return False
 for row in rows:
  case=expected[row['id']]
  if row.get('compiler_accept') is not case['expected'] or row.get('expected_accept') is not case['expected']:return False
  if row.get('source_sha256')!={n:hashlib.sha256(v.encode()).hexdigest() for n,v in case['sources'].items()}:return False
  must_skip=report.get('supports_gles32') is False and case['family'] in ('geometry-version','tessellation-version')
  if must_skip and row.get('status')!='NOT_SUPPORTED':return False
  if row.get('status')=='NOT_SUPPORTED':
   if report.get('supports_gles32') is not False or case['family'] not in ('geometry-version','tessellation-version') or row.get('runtime_status')!='NOT_SUPPORTED_GLES32':return False
  elif row.get('status')!='PASS' or row.get('runtime_accept') is not case['expected'] or row.get('gl_error')!=0:return False
 return True
def run(output,config=None,compiler='glslangValidator'):
 host=Host(config) if config else None;rows=[]
 major=d.I();minor=d.I()
 if host:
  host.fn('glGetIntegerv',None,[d.U,d.P])(0x821b,C.byref(major));host.fn('glGetIntegerv',None,[d.U,d.P])(0x821c,C.byref(minor))
 try:
  for case in cases():
   with tempfile.TemporaryDirectory() as temp:
    paths=[]
    for name,source in case['sources'].items():
     p=Path(temp)/name;p.write_text(source);paths.append(str(p))
    cp=subprocess.run([compiler,'-l',*paths],capture_output=True,text=True,timeout=30)
   row=dict(id=case['id'],family=case['family'],expected_accept=case['expected'],compiler_accept=cp.returncode==0,source_sha256={n:hashlib.sha256(v.encode()).hexdigest() for n,v in case['sources'].items()})
   unavailable=bool(host and case['family'] in ('geometry-version','tessellation-version') and (major.value,minor.value)<(3,2))
   if unavailable:row['runtime_status']='NOT_SUPPORTED_GLES32'
   elif host:
    prog,observed=host.program(case['sources']);host.fn('glDeleteProgram',None,[d.U])(prog);row.update(runtime_compile=observed['compile'],runtime_link=observed['link'],runtime_accept=observed['compile'] and observed['link'],gl_error=host.error())
   row['status']='NOT_SUPPORTED' if unavailable and row['compiler_accept']==case['expected'] else 'PASS' if row['compiler_accept']==case['expected'] and (not host or not unavailable and row['runtime_accept']==case['expected'] and row['gl_error']==0) else 'FAIL';rows.append(row)
 finally:
  if host:host.close()
 r=dict(status='FAIL' if any(x['status']=='FAIL' for x in rows) else 'PARTIAL' if any(x['status']=='NOT_SUPPORTED' for x in rows) else 'HOST_PASS',scope='authored language-family compile/link probes, not exhaustive grammar/CTS or runtime semantics',compiler='glslangValidator actual link',runtime='ACTUAL_GLES_COMPILE_LINK' if config else 'NOT_RUN',supports_gles32=(major.value,minor.value)>=(3,2) if config else None,performance='NOT_MEASURED',rows=rows,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest());r['contract_status']='PASS' if contract_valid(r) else 'FAIL';p=Path(output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--config');p.add_argument('--compiler',default='glslangValidator');p.add_argument('--require-contract-only',action='store_true');a=p.parse_args();r=run(a.output,json.loads(Path(a.config).read_text()) if a.config else None,a.compiler);print(r['status']);raise SystemExit(r['contract_status']!='PASS' if a.require_contract_only else r['status']!='HOST_PASS')
