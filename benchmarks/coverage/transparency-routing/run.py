#!/usr/bin/env python3
"""Closed finite transparency registry: execute existing suites, validate, route."""
import argparse,hashlib,importlib.util,json,math,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
SOURCES={'weighted':'benchmarks/coverage/weighted-oit/run.py','sorted':'benchmarks/coverage/weighted-oit/exact_replay.py','peel':'benchmarks/coverage/depth-peeling/run.py','policy':'benchmarks/coverage/weighted-oit/exact_policy.py'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,rel):
 spec=importlib.util.spec_from_file_location(name,ROOT/rel);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def verify_freeze():
 f=json.loads((HERE/'freeze.json').read_text())
 for key,path in SOURCES.items():
  if sha(ROOT/path)!=f['sources'][key]['sha256'] or path!=f['sources'][key]['path']:raise ValueError('SOURCE_DRIFT')
 for path,digest in f['dependencies'].items():
  resolved=(ROOT/path).resolve()
  if not resolved.is_relative_to(ROOT) or sha(resolved)!=digest:raise ValueError('DEPENDENCY_SOURCE_DRIFT')
 return f

def registry():
 colors=[[1,0,0,.5],[0,0,1,.5]]
 def layers(planes):return [{'id':str(i),'plane':list(p),'rgba':colors[i]} for i,p in enumerate(planes)]
 return {'constant':layers([(.2,0),(.8,0)]),'sloped':layers([(.1,.04),(.6,.04)]),'crossing2':layers([(.1,.2),(.9,-.2)]),'crossing3':layers([(.1,.2),(.9,-.2)])+[{'id':'2','plane':[.45,0],'rgba':[0,1,0,.25]}],'ties':layers([(.5,0),(.5,0)])}
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'))
def input_hash(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def depths(l):return [l['plane'][0]+l['plane'][1]*(x+.5) for y in range(4) for x in range(4)]
def oracle(layers):
 pixels=[]
 for y in range(4):
  for x in range(4):
   p=[0.]*4
   for l in sorted(layers,key=lambda l:l['plane'][0]+l['plane'][1]*(x+.5),reverse=True):
    c=l['rgba'];p=[c[i]*c[3]+p[i]*(1-c[3]) for i in range(3)]+[c[3]+p[3]*(1-c[3])]
   pixels.extend(math.floor(v*255+.5) for v in p)
 return pixels

def _choose(request,evidence,bindings):
 freeze=verify_freeze();registered=registry();out={'request':request,'selection':'UNAVAILABLE','performance':'NOT_MEASURED'}
 for key in ('weighted','sorted','peel'):
  if key not in bindings or key not in evidence or bindings[key].get('body_sha256')!=input_hash(evidence[key]) or bindings[key].get('source_sha256')!=freeze['sources'][key]['sha256'] or bindings[key].get('exit_code')!=0:return dict(out,reason='EVIDENCE_BODY_OR_EXECUTION_MISMATCH')
 allowed={'id','scene','layers','layer_budget','quality_max_byte_error','require_exact'}
 if not isinstance(request,dict) or set(request)!=allowed:return dict(out,reason='INVALID_REQUEST_SCHEMA')
 if request['require_exact'] is not True:return dict(out,reason='ONLY_EXACT_OPERATOR_REQUESTS_SUPPORTED')
 budget=request['layer_budget'];tol=request['quality_max_byte_error'];scene=request['scene'];layers=request['layers']
 if type(budget) is not int or not 1<=budget<=3 or type(tol) is not int or not 0<=tol<=2:return dict(out,reason='INVALID_BUDGET_OR_QUALITY')
 if not isinstance(scene,str) or scene not in registered or layers!=registered[scene]:return dict(out,reason='UNREGISTERED_OR_CHANGED_GEOMETRY')
 out['input_sha256']=input_hash(layers);out['independent_cpu_oracle']=oracle(layers)
 for key in ('weighted','sorted','peel'):
  if evidence[key].get('source_sha256')!=freeze['sources'][key]['sha256']:return dict(out,reason='EVIDENCE_SOURCE_MISMATCH')
 if evidence['sorted'].get('policy_sha256')!=freeze['sources']['policy']['sha256']:return dict(out,reason='POLICY_SOURCE_MISMATCH')
 # Consume prior weighted candidate evidence, but do not relabel different inputs as this request.
 weighted=evidence['weighted']
 if weighted.get('status')!='HOST_CONTRACT_PASS':return dict(out,reason='WEIGHTED_AUDIT_INCOMPLETE')
 out['weighted_candidate_audit']={'status':'NOT_APPLICABLE_DIFFERENT_REGISTERED_INPUTS','evidence_scenes':[{'id':s['id'],'quality_status':s['quality_status'],'selection':s['selection']} for s in weighted['scenes']],'exact_fallback_allowed':False}
 policy=load('routing_exact_policy',SOURCES['policy']);policy_input=[{'id':l['id'],'rgba':l['rgba'],'depths':depths(l)} for l in layers];decision=policy.decide(policy_input,4,4);out['global_order_decision']=decision
 if decision['selection']=='EXACT_SORTED_ALPHA':
  if budget<len(layers):return dict(out,reason='LAYER_BUDGET_INSUFFICIENT')
  if evidence['sorted'].get('status')!='HOST_POLICY_PASS':return dict(out,reason='SORTED_EXECUTION_UNAVAILABLE')
  name={'constant':'constant_nonintersecting','sloped':'sloped_nonintersecting'}.get(scene)
  matches=[s for s in evidence['sorted']['scenes'] if s['id']==name]
  if len(matches)!=1:return dict(out,reason='SORTED_INPUT_NOT_CAPTURED')
  row=matches[0]
  if row['depth_evidence']!=policy_input or row['depth_planes']!=[l['plane'] for l in layers] or row['decision'].get('far_to_near')!=decision['far_to_near']:return dict(out,reason='SORTED_INPUT_OR_ORDER_MISMATCH')
  arm=[r for r in row['draws'] if r['order']==decision['far_to_near']]
  if len(arm)!=1:return dict(out,reason='SORTED_CAPTURE_AMBIGUOUS')
  pixels=arm[0]['pixels'];route='SORTED_ALPHA';proof={'scene':name,'order':decision['far_to_near']}
 else:
  if decision.get('reason')!='CROSSING_PER_PIXEL_ORDER':return dict(out,reason='UNSUPPORTED_GEOMETRY_'+decision.get('reason','UNKNOWN'))
  peel=load('routing_peel',SOURCES['peel']);plain=[{'plane':l['plane'],'rgba':l['rgba']} for l in layers]
  if peel.validate(plain)!='VALID':return dict(out,reason='UNSAFE_QUANTIZED_DEPTH_DOMAIN')
  if evidence['peel'].get('status')!='HOST_PASS':return dict(out,reason='PEEL_EXECUTION_UNAVAILABLE')
  if plain!=evidence['peel']['layers'][:len(plain)]:return dict(out,reason='PEEL_INPUT_MISMATCH')
  # Only actually captured budgets can be admitted; no fabricated K rerouting.
  ids={('crossing2',2):'two-crossing',('crossing3',3):'three-012',('crossing3',2):'budget-overflow'}
  name=ids.get((scene,budget));matches=[s for s in evidence['peel']['cases'] if s['id']==name]
  if len(matches)!=1:return dict(out,reason='BUDGET_NOT_CAPTURED')
  row=matches[0]
  if row['negative'] is not None or row['layer_budget']!=budget or row['input_order']!=([1,0] if scene=='crossing2' else [0,1,2]):return dict(out,reason='PEEL_REQUEST_MISMATCH')
  if row['input_validation']!='VALID' or len(row['query_any_samples'])!=budget+1:return dict(out,reason='PEEL_PROOF_INCOMPLETE')
  if row['query_any_samples'][-1] or row['overflow']:return dict(out,reason='LAYER_BUDGET_OVERFLOW')
  if row['decision']!='ACCEPT_FINITE_SAMPLE':return dict(out,reason='PEEL_EXECUTION_REJECTED')
  pixels=row['pixels'];route='DEPTH_PEELING';proof={'scene':name,'layer_budget':budget,'actual_query_any_samples':row['query_any_samples'],'quantized_domain':evidence['peel']['depth_domain']}
 if len(pixels)!=64 or any(type(v) is not int or not 0<=v<=255 for v in pixels):return dict(out,reason='INVALID_READBACK')
 error=max(abs(a-b) for a,b in zip(pixels,out['independent_cpu_oracle']));out.update(pixels=pixels,max_error=error,evidence_binding=proof)
 if error>tol:return dict(out,reason='REQUEST_QUALITY_NOT_MET')
 return dict(out,selection=route,reason='SOURCE_INPUT_BUDGET_AND_PIXEL_EVIDENCE_VERIFIED')

def choose(request,evidence,bindings):
 try:
  if not isinstance(evidence,dict) or not isinstance(bindings,dict):raise ValueError('MALFORMED_EVIDENCE')
  if any(not isinstance(evidence.get(k),dict) or not isinstance(bindings.get(k),dict) for k in ('weighted','sorted','peel')):raise ValueError('MALFORMED_RECEIPTS')
  return _choose(request,evidence,bindings)
 except (KeyError,TypeError,ValueError,IndexError):
  return {'request':request,'selection':'UNAVAILABLE','reason':'MALFORMED_OR_STALE_EVIDENCE','performance':'NOT_MEASURED'}

def suite_acceptance(rows):
 expected=[('constant-k2-t2','SORTED_ALPHA','SOURCE_INPUT_BUDGET_AND_PIXEL_EVIDENCE_VERIFIED'),('sloped-k2-t2','SORTED_ALPHA','SOURCE_INPUT_BUDGET_AND_PIXEL_EVIDENCE_VERIFIED'),('crossing2-k2-t2','DEPTH_PEELING','SOURCE_INPUT_BUDGET_AND_PIXEL_EVIDENCE_VERIFIED'),('crossing3-k3-t2','DEPTH_PEELING','SOURCE_INPUT_BUDGET_AND_PIXEL_EVIDENCE_VERIFIED'),('crossing3-k2-t2','UNAVAILABLE','LAYER_BUDGET_OVERFLOW'),('crossing2-k1-t2','UNAVAILABLE','BUDGET_NOT_CAPTURED'),('crossing3-k3-t0','UNAVAILABLE','REQUEST_QUALITY_NOT_MET'),('ties-k2-t2','UNAVAILABLE','UNSUPPORTED_GEOMETRY_AMBIGUOUS_TIE')]
 if len(rows)!=len(expected):return False
 for row,(ident,selection,reason) in zip(rows,expected):
  if row.get('request',{}).get('id')!=ident or row.get('selection')!=selection or row.get('reason')!=reason:return False
  if selection!='UNAVAILABLE' and (type(row.get('max_error')) is not int or row['max_error']>2 or len(row.get('pixels',[]))!=64):return False
 return True

def requests():
 reg=registry();rows=[]
 for scene,budget,tol in [('constant',2,2),('sloped',2,2),('crossing2',2,2),('crossing3',3,2),('crossing3',2,2),('crossing2',1,2),('crossing3',3,0),('ties',2,2)]:
  rows.append({'id':f'{scene}-k{budget}-t{tol}','scene':scene,'layers':reg[scene],'layer_budget':budget,'quality_max_byte_error':tol,'require_exact':True})
 return rows

def _read_bundle(directory):
 directory=Path(directory).resolve();report=json.loads((directory/'report.json').read_text());evidence={}
 for key in ('weighted','sorted','peel'):
  rec=report['receipts'][key];p=(directory/rec['artifact']).resolve()
  if p.parent!=directory or sha(p)!=rec['artifact_sha256']:raise ValueError('ARTIFACT_BODY_OR_PATH_CHANGED')
  body=json.loads(p.read_text())
  if input_hash(body)!=rec['body_sha256']:raise ValueError('ARTIFACT_BODY_CHANGED')
  evidence[key]=body
 return evidence,report['receipts']

def read_bundle(directory):
 try:return _read_bundle(directory)
 except (OSError,KeyError,TypeError,ValueError):raise ValueError('MALFORMED_OR_CHANGED_BUNDLE') from None

def execute(config,output,request_file=None):
 freeze=verify_freeze();output=Path(output);output.mkdir(parents=True,exist_ok=False);evidence={};receipts={}
 for key in ('weighted','sorted','peel'):
  path=output/(key+'.json');proc=subprocess.run([sys.executable,str(ROOT/SOURCES[key]),'--config',str(Path(config).resolve()),'--output',str(path)],capture_output=True,text=True,timeout=180)
  if not path.is_file():raise ValueError('COLLECTOR_NO_ARTIFACT')
  evidence[key]=json.loads(path.read_text());receipts[key]={'collector':SOURCES[key],'source_sha256':freeze['sources'][key]['sha256'],'exit_code':proc.returncode,'artifact':path.name,'artifact_sha256':sha(path),'body_sha256':input_hash(evidence[key])}
 tasks=json.loads(Path(request_file).read_text()) if request_file else requests();rows=[choose(t,evidence,receipts) for t in tasks]
 report={'schema_version':1,'status':'EXECUTED_FINITE_ROUTING','source_sha256':sha(__file__),'freeze_sha256':sha(HERE/'freeze.json'),'receipts':receipts,'results':rows,'actual_full_suite_counts':{'draws':evidence['weighted'].get('actual_execution_counts',{}).get('draws',0)+evidence['sorted'].get('actual_draws',0)+sum(evidence['peel'].get('actual_counts',{}).get(k,0) for k in ('geometry_draws','compose_draws')),'readbacks':evidence['weighted'].get('actual_execution_counts',{}).get('readbacks',0)+evidence['sorted'].get('actual_readbacks',0)+evidence['peel'].get('actual_counts',{}).get('readbacks',0),'occlusion_queries':evidence['peel'].get('actual_counts',{}).get('occlusion_queries',0)},'physical_device':'NOT_RUN','performance':'NOT_MEASURED','scope':'Closed fixed full-coverage analytic samples; not generic renderer or original W7/W8 release acceptance'}
 report['default_suite_acceptance']='NOT_APPLICABLE_CUSTOM_REQUESTS' if request_file else 'PASS' if suite_acceptance(rows) else 'FAIL'
 if not request_file:report['status']='HOST_ROUTING_PASS' if report['default_suite_acceptance']=='PASS' and all(x['exit_code']==0 for x in receipts.values()) else 'FAIL'
 (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);p.add_argument('--requests');a=p.parse_args();r=execute(a.config,a.output,a.requests);raise SystemExit(0 if r['status']!='FAIL' and all(x['exit_code']==0 for x in r['receipts'].values()) else 1)
