"""Bind the existing actual ASTC decode mechanism to v1.1.0 priority evidence.

One authored LDR constant block is not arbitrary ASTC/HDR or device proof.
"""
import argparse,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
MECHANISM=ROOT/'benchmarks/texture_access/mechanisms.py'
spec=importlib.util.spec_from_file_location('astc_host',MECHANISM);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def verdict(row):
 p=row.get('pixels',[])
 return len(p)==64 and p==[255,0,0,255]*16 and row.get('gl_error')==0 and row.get('compile') is True and row.get('link') is True and row.get('quality')=='PASS'
def run(config,output):
 h=m.TextureHost(config)
 r={'status':'NOT_SUPPORTED','scope':'existing v1.0.9 mechanism, one ASTC4x4 LDR constant block sampled into RGBA8; not arbitrary ASTC/HDR/device acceptance','physical_gain':None,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'mechanism_sha256':hashlib.sha256(MECHANISM.read_bytes()).hexdigest()}
 try:
  if set(h.metadata['extensions'])&{'GL_KHR_texture_compression_astc_ldr','GL_KHR_texture_compression_astc_hdr'}:
   case=next(c for c in m.cases() if c['mode']=='astc');row=h.execute(case)
   # Do not publish host fingerprints or use submit timing as GPU performance.
   result={k:row[k] for k in ('compile','link','pixels','gl_error','quality','cpu_oracle_max_error','logical_texture_bytes')}
   wrong=dict(result,pixels=[0,255,0,255]*16)
   r.update(result=result,wrong_color_rejected=not verdict(wrong),status='HOST_PASS' if verdict(result) and not verdict(wrong) else 'FAIL')
 finally:
  h.close();Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(r,indent=2)+'\n')
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']=='FAIL')
