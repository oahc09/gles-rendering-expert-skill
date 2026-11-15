"""Closed typed runtime receipts; no dynamic code, commands or caller-defined expectations."""
import argparse,hashlib,json
from pathlib import Path
FIELDS={'id','probe','driver','api_domain','api','version','extension','collector','collector_sha256','report','report_sha256','positive','negative','negative_kind'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def same(a,b):
 if type(a) is not type(b):return False
 if isinstance(a,list):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
 if isinstance(a,dict):return set(a)==set(b) and all(same(a[k],b[k]) for k in a)
 return a==b
def pointer(obj,path):
 for key in path.strip('/').split('/'):
  obj=obj[int(key)] if isinstance(obj,list) else obj[key]
 return obj

def contract(probe,driver):
 if probe=='debug-output':return ('glDebugMessageInsert' if driver=='mesa' else 'glDebugMessageInsertKHR','3.2' if driver=='mesa' else '3.1',None if driver=='mesa' else 'GL_KHR_debug','/synchronous_return_observed','/negative_cases/1/gl_error',True,1280)
 if probe=='timer-query':return ('glGetQueryObjectui64vEXT','3.0','GL_EXT_disjoint_timer_query','/availability/1/available_at_result_read','/negatives/1/error',True,1282)
 if probe=='robust-readback':return ('glReadnPixels' if driver=='mesa' else 'glReadnPixelsKHR','3.2' if driver=='mesa' else '3.1',None if driver=='mesa' else 'GL_KHR_robustness','/routes/0/cases/0/gl_error','/routes/0/cases/1/gl_error',0,1282)
 if probe=='external-image':return ('glTexParameteri','3.0',None,'/external_before_destroy/max_byte_error','/parameter_checks/0/error',0,1280)
 raise ValueError('unknown probe')
def safe(root,relative):
 if type(relative) is not str or Path(relative).is_absolute():raise ValueError('invalid path')
 p=(root/relative).resolve()
 if not p.is_relative_to(root) or not p.is_file():raise ValueError('missing/escaping path')
 return p

def validate(root,document,catalogs):
 root=Path(root).resolve();errors=[];seen=set();apis=set()
 try:
  if type(document) is not dict or set(document)!={'schema_version','rows'} or not same(document['schema_version'],1) or type(document['rows']) is not list:raise ValueError('schema')
  if len(document['rows'])!=8:raise ValueError('required 4 probes x2 driver receipts missing')
 except (ValueError,KeyError,TypeError) as e:return {'status':'INCOMPLETE','errors':[str(e)],'linked_runtime_rows':0}
 for row in document['rows']:
  try:
   if type(row) is not dict or set(row)!=FIELDS:raise ValueError('row schema')
   probe=row['probe'];driver=row['driver']
   if driver not in ('mesa','angle'):raise ValueError('unknown driver')
   if (probe,driver) in seen:raise ValueError('duplicate row')
   seen.add((probe,driver));api,version,extension,pos,neg,pval,nval=contract(probe,driver)
   expected={'id':probe+'-'+driver,'api_domain':'gles','api':api,'version':version,'extension':extension,'positive':pos,'negative':neg,'negative_kind':'ACTUAL_API_ERROR','collector':'benchmarks/coverage/'+probe+'/run.py','report':'benchmarks/coverage/'+probe+'/'+driver+'.json'}
   if any(not same(row[k],v) for k,v in expected.items()):raise ValueError('closed contract route/assertion/polarity mismatch')
   cat=catalogs['gles'];cmd=next((c for c in cat['commands'] if c['name']==api),None)
   if cmd is None or version not in cat['core_snapshots']:raise ValueError('ghost/version')
   if extension is None:
    if version not in cmd['core_versions']:raise ValueError('unavailable core API')
   else:
    ext=next((e for e in cat['extensions'] if e['name']==extension),None)
    if not ext or cat['api'] not in ext['supported'] or not any(b['operation']=='require' and api in b['commands'] and b['conditions'].get('api',cat['api'])==cat['api'] for b in ext['blocks']):raise ValueError('extension API mismatch')
   source=safe(root,row['collector']);reportpath=safe(root,row['report'])
   if row['collector_sha256']!=sha(source) or row['report_sha256']!=sha(reportpath):raise ValueError('stale source/report hash')
   r=json.loads(reportpath.read_text())
   if not same(r.get('schema_version'),1) or r.get('source_sha256')!=row['collector_sha256'] or r.get('status')!='HOST_PASS' or r.get('execution_class')!='SOFTWARE_HOST':raise ValueError('report/collector execution mismatch')
   if not same(pointer(r,pos),pval) or not same(pointer(r,neg),nval):raise ValueError('runtime assertion failed')
   # Check case identity, expected errors against trusted constants, and actual route.
   if probe=='debug-output':
    expected_version=[3,2] if driver=='mesa' else [3,1]
    if not same(r['api_version'],expected_version) or r['route']!=('core' if driver=='mesa' else 'KHR') or not same(r['KHR_advertised'],True):raise ValueError('debug observed capability/route')
    msgs=r['application_messages']
    if [x['id'] for x in msgs]!=[901,904,905,905,907] or not all(same(x['user_matches'],True) for x in msgs):raise ValueError('debug callback contents')
    expected_msgs=[(901,'finite-start',0x8251,0x9148),(904,'finite-low-allowed',0x8251,0x9148),(905,'finite-group',0x8269,0x826b),(905,'finite-group',0x826a,0x826b),(907,'finite-low-restored',0x8251,0x9148)]
    for msg,(ident,text,kind,severity) in zip(msgs,expected_msgs):
     if not same(msg['id'],ident) or msg['message']!=text or not same(msg['source'],0x824a) or not same(msg['type'],kind) or not same(msg['severity'],severity):raise ValueError('debug callback golden')
    case=r['negative_cases'][1]
    if case['id']!='insert-api-source' or not same(case['expected_error'],1280) or api not in r['entrypoints'] or not same(r['callback_registration_matches'],True):raise ValueError('debug identity')
   elif probe=='timer-query':
    if not same(r['counter_bits'],{'elapsed':64,'timestamp':64}) or not same(r['workload_pixel_match'],True) or not same(r['active_query_matches'],True) or not same(r['objects_live'],True) or not same(r['deleted_not_objects'],True):raise ValueError('timer actual lifecycle/caps')
    case=r['negatives'][1]
    if case['case']!='read-active-result' or not same(case['expected'],1282) or api not in r['entrypoints'] or not same(r['extension_advertised'],True):raise ValueError('timer identity')
   elif probe=='robust-readback':
    route=r['routes'][0];p,n=route['cases'][:2]
    if not same(r['queried_api_version'],([3,2] if driver=='mesa' else [3,1])) or route['route']!=('core' if driver=='mesa' else 'KHR') or not same(r['KHR_robustness_advertised'],True):raise ValueError('robust actual capability/route')
    golden=[255,0,0,255,0,255,0,255,0,0,255,255,255,255,0,255]*4+[165]*64
    if not same(p['payload'],golden) or not same(p['prefix_canary'],[165]*16) or not same(p['suffix_canary'],[165]*16) or not same(p['bufSize'],64) or not same(n['bufSize'],63):raise ValueError('robust positive content')
    if route['read_entry']!=api or p['id']!='tight-64' or n['id']!='tight-63' or not same(n['expected_error'],1282):raise ValueError('robust identity')
    if not same(n['payload'],[165]*128) or not same(n['prefix_canary'],[165]*16) or not same(n['suffix_canary'],[165]*16):raise ValueError('robust canary')
   else:
    if not all(same(r['capabilities'].get(k),True) for k in ['GL_OES_EGL_image','GL_OES_EGL_image_external','GL_OES_EGL_image_external_essl3','EGL_KHR_image_base','EGL_KHR_gl_texture_2D_image']) or not same(r['force_disabled'],False):raise ValueError('external observed capability')
    case=r['parameter_checks'][0]
    if case['case']!='mipmap-min-filter' or not same(case['expected'],1280) or not same(r['create_image_success'],True):raise ValueError('external identity')
    golden=[v for y in range(4) for x in range(4) for v in (17+31*x+7*y,23+11*x+43*y,31+19*x+13*y,97+17*x+23*y)]
    if not same(r['external_before_destroy']['pixels'],golden):raise ValueError('pixel oracle')
   apis.add(api)
  except (ValueError,KeyError,TypeError,IndexError,OSError) as e:errors.append(str(e))
 return {'status':'RUNTIME_LINK_CONTRACT_PASS' if not errors else 'INCOMPLETE','errors':errors,'linked_runtime_rows':len(document['rows'])-len(errors),'distinct_linked_apis':len(apis),'compiled':'NOT_EVALUATED','device':'NOT_RUN','provider':'NOT_RUN','unlinked_registry':'UNKNOWN','policy_simulations_counted_as_actual':0,'release_ready':False,'scope':'four finite software-host API boundary receipts; source/report hashes are integrity, not execution authentication or complete semantic coverage'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);a=p.parse_args();base=a.root/'references/coverage';r=validate(a.root,json.loads((base/'runtime-links.json').read_text()),{'gles':json.loads((base/'gles-api-catalog.json').read_text())});print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='RUNTIME_LINK_CONTRACT_PASS' else 1)
