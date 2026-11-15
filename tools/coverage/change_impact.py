"""Read-only closed impact graph; never runs commands or promotes source candidates."""
import argparse,hashlib,json
from pathlib import Path
from lifecycle import validate as lifecycle_validate
ROOT=Path(__file__).resolve().parents[2]
LEDGER='docs/v1.1.0/source-ledger.json';RECEIPTS='references/coverage/runtime-links.json'
BASELINE_SHA256='52837152ed6e039e0a230e4e62be99225035f536cb01ac757cd2a84596b441b7'
TESTS={'ledger-lifecycle','runtime-links'}
TEST_PATHS={'ledger-lifecycle':'benchmarks/coverage/governance/test_lifecycle.py','runtime-links':'tools/coverage/test_runtime_links.py','probe-debug':'benchmarks/coverage/debug-output/test_debug.py','probe-timer':'benchmarks/coverage/timer-query/test_timer.py','probe-robust':'benchmarks/coverage/robust-readback/test_robust.py','probe-external':'benchmarks/coverage/external-image/test_image.py','candidate-advanced':'benchmarks/shader_ab/test_advanced.py','candidate-rendergraph':'tools/test_rendergraph_optimizer.py'}
PROBE_TEST={'debug-output':'probe-debug','timer-query':'probe-timer','robust-readback':'probe-robust','external-image':'probe-external'}

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe(root,path):
 if type(path) is not str or Path(path).is_absolute():raise ValueError('relative path required')
 p=(root/path).resolve()
 if not p.is_relative_to(root) or not p.is_file():raise ValueError('missing/escaping path')
 return p
def inventory(root):
 ledger=json.loads(safe(root,LEDGER).read_text());runtime=json.loads(safe(root,RECEIPTS).read_text());nodes=[];edges=[];subjects=[]
 def node(ident,kind,path,owner):
  nodes.append({'id':ident,'kind':kind,'path':path,'base_sha256':digest(safe(root,path)) if path else None,'subject':owner})
 for row in ledger['rules']:
  ident='candidate:'+row['id'];subjects.append(ident);node(ident,'candidate',LEDGER,ident)
  for i,e in enumerate(row.get('evidence',[])):
   key=ident+':evidence:'+str(i);node(key,'evidence',e['path'],ident);edges.append({'from':key,'to':ident})
  for field in ['rule','example','test']:
   key=ident+':'+field;node(key,field,row.get(field),ident);edges.append({'from':ident,'to':key})
 for row in runtime['rows']:
  ident='runtime:'+row['id'];subjects.append(ident);node(ident,'receipt',RECEIPTS,ident)
  for field,kind in [('collector','collector'),('report','report')]:
   key=ident+':'+kind;node(key,kind,row[field],ident);edges.append({'from':key,'to':ident})
 node('registry:gles','registry','references/coverage/gles-api-catalog.json','registry:gles')
 for subject in subjects:
  if subject.startswith('runtime:'):edges.append({'from':'registry:gles','to':subject})
 return {'schema_version':1,'subjects':subjects,'nodes':nodes,'edges':edges,'test_ids':['ledger-lifecycle','runtime-links']}
def analyze(root,index,today):
 root=Path(root).resolve()
 try:
  expected=inventory(root)
  if type(index) is not dict or set(index)!=set(expected) or type(index['schema_version']) is not int or index['schema_version']!=1:raise ValueError('index schema')
  if type(index['subjects']) is not list or len(index['subjects'])!=len(set(index['subjects'])) or set(index['subjects'])!=set(expected['subjects']):raise ValueError('subject inventory omission/duplicate')
  if index['test_ids']!=expected['test_ids']:raise ValueError('unrecognized test ID')
  if type(index['nodes']) is not list or type(index['edges']) is not list:raise ValueError('graph schema')
  byid={};wanted={n['id']:n for n in expected['nodes']};changed=[];unlinked=[]
  for n in index['nodes']:
   if type(n) is not dict or set(n)!={'id','kind','path','base_sha256','subject'}:raise ValueError('node schema')
   key=n['id']
   if type(key) is not str or key in byid or key not in wanted:raise ValueError('duplicate/orphan node')
   w=wanted[key]
   if any(n[k]!=w[k] for k in ['kind','path','subject']):raise ValueError('node inventory mapping mismatch')
   byid[key]=n
   if n['path'] is None:
    if n['base_sha256'] is not None:raise ValueError('unlinked node hash')
    unlinked.append(key)
   else:
    sha=n['base_sha256']
    if type(sha) is not str or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):raise ValueError('malformed base hash')
    if digest(safe(root,n['path']))!=sha:changed.append(key)
  if set(byid)!=set(wanted):raise ValueError('node omission')
  adjacency={k:[] for k in byid};pairs=[]
  for e in index['edges']:
   if type(e) is not dict or set(e)!={'from','to'} or e['from'] not in byid or e['to'] not in byid:raise ValueError('orphan edge')
   pair=(e['from'],e['to'])
   if pair in pairs:raise ValueError('duplicate edge')
   pairs.append(pair);adjacency[e['from']].append(e['to'])
  visiting=set();done=set()
  def walk(k):
   if k in visiting:raise ValueError('dependency cycle')
   if k in done:return
   visiting.add(k)
   for t in adjacency[k]:walk(t)
   visiting.remove(k);done.add(k)
  for k in byid:walk(k)
  if set(pairs)!={(e['from'],e['to']) for e in expected['edges']}:raise ValueError('edge omission/invented dependency')
  affected=set(changed);queue=list(changed)
  while queue:
   for t in adjacency[queue.pop()]:
    if t not in affected:affected.add(t);queue.append(t)
  baseline=hashlib.sha256(json.dumps(index,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  if baseline!=BASELINE_SHA256:raise ValueError('unreviewed baseline identity')
  impacted_subjects={byid[k]['subject'] for k in affected};selected=set();unresolved=[]
  for subject in sorted(impacted_subjects):
   if subject=='registry:gles':selected.add('runtime-links');continue
   if subject.startswith('runtime:'):
    selected.add('runtime-links')
    probe=subject[len('runtime:'):].rsplit('-',1)[0];selected.add(PROBE_TEST[probe])
   else:
    selected.add('ledger-lifecycle')
    path=byid[subject+':test']['path'];testid=next((k for k,v in TEST_PATHS.items() if v==path),None)
    if testid:selected.add(testid)
    else:unresolved.append({'subject':subject,'declared_test':path,'status':'UNRESOLVED_NOT_A_REGISTERED_TEST'})
  plan=[{'test_id':k,'path':TEST_PATHS[k],'selection':'VALIDATION_ONLY' if k in TESTS else 'DECLARED_LINK_REQUIRES_RELEVANCE_REVIEW' if k.startswith('candidate-') else 'RUNTIME_PROBE_REGRESSION'} for k in sorted(selected)]
  for item in plan:safe(root,item['path'])
  ledger=json.loads(safe(root,LEDGER).read_text())
  try:governance=lifecycle_validate(ledger['rules'],root,today)
  except (ValueError,TypeError,KeyError):governance={'status':'INCOMPLETE','reason':'ledger provenance/lifecycle validation failed','conflicts':[],'records':[]}
  return {'schema_version':1,'status':'CHANGE_REVIEW_REQUIRED' if changed else 'SNAPSHOT_UNCHANGED','changed_nodes':sorted(changed),'affected_targets':sorted(affected),'unlinked_targets':sorted(unlinked),'subject_count':len(index['subjects']),'governance':governance,'review_required':bool(changed or unlinked or governance['status']!='CONSISTENT'),'closed_test_ids_to_validate':sorted(selected),'regression_plan':plan,'unresolved_regression_links':unresolved,'command_execution':False,'adoption_allowed':False,'release_ready':False,'limitation':'Snapshot identity is not no substantive upstream change; candidates remain unadopted. Hash changes trigger review, not automatic baseline replacement.'}
 except (ValueError,KeyError,TypeError,OSError) as e:return {'schema_version':1,'status':'INCOMPLETE','reason':str(e),'adoption_allowed':False,'release_ready':False,'command_execution':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--date',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=analyze(a.root,json.loads((a.root/'references/coverage/impact-index.json').read_text()),a.date);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(1 if r['status']=='INCOMPLETE' else 0)
