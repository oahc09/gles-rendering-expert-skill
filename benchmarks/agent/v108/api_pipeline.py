"""Bounded GL call-source repair with real two-driver error observations.

A parser accepts one frozen API name and bounded literal integer arguments only.
This is source-to-GL invocation, not C++ compilation or arbitrary code execution.
"""
import argparse,copy,hashlib,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
import repair
DIFF=repair.diff
FIXES={'viewport-negative':[0,0,4,4],'scissor-negative':[0,0,4,4],
 'pack-invalid':[0xd05,4],'enable-invalid':[0xbe2],'clear-invalid':[0x4000],
 'buffer-target-invalid':[0x8892,0],'texture-target-invalid':[0xde1,0]}
def corpus():return {c['id']:c for c in DIFF.cases() if c['id'] in FIXES}
def source(case,args):return case['function']+'('+','.join(str(x) for x in args)+');'
def parse(case,raw):
 if not isinstance(raw,str) or len(raw)>256:raise ValueError('call source quota')
 match=re.fullmatch(re.escape(case['function'])+r'\(\s*(-?(?:0x[0-9a-fA-F]+|\d+)(?:\s*,\s*-?(?:0x[0-9a-fA-F]+|\d+))*)\s*\);',raw)
 if not match:raise ValueError('single frozen API call with literals required')
 args=[int(s.strip(),16 if '0x' in s else 10) for s in match[1].split(',')]
 if len(args)!=len(case['args']) or any(abs(x)>65535 for x in args):raise ValueError('arity/range')
 return args
def run(case_id,patch,configs):
 case=corpus()[case_id];args=parse(case,patch)
 result={'measured_at_utc':datetime.now(timezone.utc).isoformat(),'case':case_id,'scope':'PARSED_API_SOURCE_REAL_DRIVER','provider_status':'BLOCKED_BY_PROVIDER','source':source(case,case['args']),'patch':patch,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 if args!=FIXES[case_id]:return dict(result,status='FAIL',reason='frozen intended operation must be preserved; error-free no-op is not repair')
 if len(configs)!=2 or {c.get('kind') for c in configs}!={'mesa','angle'}:return dict(result,status='BLOCKED_BY_DRIVER')
 selected=[dict(case,id=case_id+'-repro-'+str(i)) for i in range(3)]
 selected+=[dict(case,id=case_id+'-patched',args=args,expected=0)]
 observed=[DIFF.isolated(c,selected) for c in configs];result['observations']=observed
 if any(r.get('status')!='EXECUTED' or len(r.get('cases',[]))!=4 for r in observed):return dict(result,status='BLOCKED_BY_DRIVER')
 result['comparisons']=[DIFF.compare(c,observed[0]['cases'][i],observed[1]['cases'][i]) for i,c in enumerate(selected)]
 # Both original calls must reproduce exact specified API error and no harness error.
 return dict(result,status='HOST_PASS' if all(x=='PASS' for x in result['comparisons']) else 'FAIL')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 cfg=json.loads(a.config.read_text());rows=[]
 for cid,c in corpus().items():
  r=run(cid,source(c,FIXES[cid]),cfg);(a.output/(cid+'.json')).write_text(json.dumps(r,indent=2));rows.append({'case':cid,'status':r['status']})
 report={'scope':'AUTHORED_SOURCE_REPAIRS','provider_status':'BLOCKED_BY_PROVIDER','cases':rows,'status':'PASS' if all(x['status']=='HOST_PASS' for x in rows) else 'FAIL'}
 (a.output/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));sys.exit(0 if report['status']=='PASS' else 1)
