#!/usr/bin/env python3
"""Frozen final-eval gate around existing paired capture and evidence-bound scoring."""
import argparse,hashlib,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from run import validate_cases,run as capture
from score_v109 import score_files

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate():
 frozen=json.loads((HERE/'freeze.json').read_text())
 for path,h in frozen['files'].items():
  p=(HERE/path).resolve()
  if not p.is_relative_to(HERE.parent.resolve()) or sha(p)!=h:raise ValueError('Frozen file missing/changed: '+path)
 payload=json.loads((HERE/'cases.json').read_text());cases=validate_cases(payload)
 cats={c['final_category'] for c in cases}
 if len(cases)!=100 or len(cats)!=5 or any(sum(c['final_category']==k for c in cases)!=20 for k in cats):raise ValueError('Expected five categories of20')
 prompts=[' '.join(c['prompt'].split()).casefold() for c in cases]
 if len(set(prompts))!=100:raise ValueError('Duplicate prompts')
 # Exact overlap rejection is not a guarantee against semantic or provider contamination.
 for path in HERE.parent.glob('cases*.json'):
  old=json.loads(path.read_text())
  if set(prompts)&{' '.join(c['prompt'].split()).casefold() for c in old['cases']}:raise ValueError('Exact old-corpus overlap')
 return payload

def wilson(k,n):
 if n==0:return None
 if not 0<=k<=n:raise ValueError('Invalid binomial denominator')
 z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;r=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 return [max(0,c-r),min(1,c+r)]

def summary(run,adjudications,evidence_root=None,usage=None):
 payload=validate();report=score_files(run,adjudications,HERE/'cases.json',evidence_root)
 reviews=json.loads(Path(adjudications).read_text());raw=json.loads((Path(run)/'summary.json').read_text())
 report['scope']={'expected_tasks':100,'expected_responses':200,'category_denominators':{k:20 for k in sorted({c['final_category'] for c in payload['cases']})},'independent_review':'NOT_VERIFIED_BY_TOOL','contamination':'UNKNOWN','heldout_certification':False}
 if raw.get('skill_snapshot_file'):
  sp=(Path(run)/raw['skill_snapshot_file']).resolve()
  if sp.parent!=Path(run).resolve() or sha(sp)!=raw['skill_sha256']:raise ValueError('Skill snapshot changed')
 if raw.get('protocol_sha256') and sha(Path(run)/'protocol.json')!=raw['protocol_sha256']:raise ValueError('Protocol changed')
 labels={c['case_id']:c for c in payload['cases']};metrics={}
 for condition in ('no_skill','with_skill'):
  rows=[r for r in reviews if r['condition']==condition];g=report.get('metrics',{}).get(condition,{})
  pairs={'finding_accuracy':(g.get('tp',0),g.get('tp',0)+g.get('fn',0)), 'legal_control_false_positive':(g.get('rejected_legal_controls',0),g.get('legal_controls',0)), 'first_compile':(g.get('compile_pass',0),g.get('compile_tested',0)), 'correctness_numeric':(g.get('numeric_pass',0),g.get('numeric_tested',0)), 'first_run':(g.get('first_run_pass',0),g.get('first_run_tested',0))}
  # Reproduced diagnosis is counted only with first_run evidence already hash-checked by score_files.
  dx=[r for r in rows if labels[r['case_id']]['mode']=='Diagnose' and r.get('first_run',{}).get('status') in ('PASS','FAIL')]
  pairs['diagnosis_reproduction']=(sum(r['first_run']['status']=='PASS' and r.get('debug_complete') is True for r in dx),len(dx))
  pairs['evidence_complete']=(sum(all(r.get(k,{}).get('status')=='PASS' for k in ('compile','first_run','numeric','visual')) for r in rows),len(rows))
  pairs['p0_illegal_generation']=(sum(r.get('p0_api_illegal') is True for r in rows),sum(type(r.get('p0_api_illegal')) is bool for r in rows))
  if any(r.get('p0_api_illegal') is not None and type(r['p0_api_illegal']) is not bool for r in rows):raise ValueError('Illegal-generation judgment must be boolean/null')
  metrics[condition]={k:{'numerator':a,'denominator':b,'ratio':a/b if b else None,'wilson95':wilson(a,b)} for k,(a,b) in pairs.items()}
 report['final_metrics']=metrics;report['confidence_caveat']='Wilson marginal intervals, not proof of iid sampling or paired treatment significance; five classes are authored, not population random samples.'
 report['cost']={'status':'UNKNOWN','currency':None,'total':None,'responses_accounted':0}
 if usage is not None:
  u=json.loads(Path(usage).read_text());actual={(r['case_id'],r['condition']):r for r in raw['results']};seen=set();total=0;currency=u['currency']
  if not isinstance(currency,str) or not currency:raise ValueError('Cost currency required')
  for row in u['rows']:
   key=(row['case_id'],row['condition']);v=row['cost']
   if key in seen or key not in actual or row['response_sha256']!=actual[key]['response_sha256']:raise ValueError('Cost response binding invalid')
   if type(v) not in (int,float) or not math.isfinite(v) or v<0:raise ValueError('Invalid cost')
   if evidence_root is None:raise ValueError('Cost receipt evidence root required')
   root=Path(evidence_root).resolve();p=(root/row['receipt_file']).resolve()
   if not p.is_relative_to(root) or sha(p)!=row['receipt_sha256']:raise ValueError('Cost receipt changed')
   total+=v;seen.add(key)
  report['cost']={'status':'RECEIPT_BOUND_NOT_INDEPENDENTLY_AUDITED','currency':currency,'total':total,'responses_accounted':len(seen),'complete':len(seen)==200}
 # No self-attested independence can promote this authored, as-yet unreviewed release corpus.
 report['release_acceptance']='NOT_EVALUATED';report['failure_analysis']='No provider responses: model failures unknown' if not raw['results'] else 'Use hash-bound adjudication rationales; independent review remains required'
 return report

def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
 c=sub.add_parser('capture');c.add_argument('--skill',type=Path,required=True);c.add_argument('--output',type=Path,required=True);c.add_argument('--adapter');c.add_argument('--provider-label');c.add_argument('--protocol',type=Path);c.add_argument('--timeout',type=float,default=180)
 s=sub.add_parser('score');s.add_argument('--run',type=Path,required=True);s.add_argument('--adjudications',type=Path,required=True);s.add_argument('--evidence-root',type=Path);s.add_argument('--usage',type=Path);s.add_argument('--output',type=Path,required=True)
 sub.add_parser('validate');a=p.parse_args();validate()
 if a.action=='validate':print('FROZEN_CORPUS_VALID_NOT_PROVIDER_EVALUATED');return 0
 if a.action=='capture':
  protocol=None
  if a.adapter:
   if not a.protocol:raise ValueError('Real provider requires paired budget protocol')
   protocol=json.loads(a.protocol.read_text())
   if any(k not in protocol for k in ('model','max_output_tokens','temperature','seed','both_conditions_identical')) or protocol['both_conditions_identical'] is not True:raise ValueError('Missing paired provider contract')
   if type(protocol['max_output_tokens']) is not int or protocol['max_output_tokens']<=0:raise ValueError('Invalid token budget')
  a.cases=HERE/'cases.json';a.synthetic_fixture=False;a.case=None;code=capture(a)
  (a.output/'skill-snapshot.md').write_bytes(a.skill.read_bytes())
  sp=a.output/'summary.json';sr=json.loads(sp.read_text());sr['skill_snapshot_file']='skill-snapshot.md';sp.write_text(json.dumps(sr,indent=2)+'\n')
  if protocol is not None:
   (a.output/'protocol.json').write_bytes(a.protocol.read_bytes())
   p=a.output/'summary.json';r=json.loads(p.read_text());r['protocol_sha256']=sha(a.protocol);r['protocol_enforcement']='ADAPTER_CONTRACT_NOT_REMOTE_ATTESTATION';p.write_text(json.dumps(r,indent=2)+'\n')
  return code
 r=summary(a.run,a.adjudications,a.evidence_root,a.usage);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');return 2 if r['status']=='BLOCKED_BY_PROVIDER' else 0
if __name__=='__main__':raise SystemExit(main())
