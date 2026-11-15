"""Separate harness success from quality acceptance and optimization evidence."""
def evaluate(rows, golden, pattern):
 if pattern not in ('smooth','steep'):raise ValueError('unknown pattern')
 if len(golden)!=64 or any(type(v)!=int or not 0<=v<=255 for v in golden):raise ValueError('invalid golden')
 ids=[r.get('id') for r in rows]
 if len(ids)!=len(set(ids)) or not {'rgba','etc2'}<=set(ids) or set(ids)-{'rgba','etc2','astc'}:raise ValueError('missing/duplicate/unexpected branches')
 decisions=[];harness=True
 for row in rows:
  if row.get('status')=='NOT_RUN' and row['id']=='astc':
   decisions.append({'id':'astc','quality_acceptance':'NOT_RUN','optimization_status':'INSUFFICIENT_EVIDENCE'});continue
  pixels=row.get('pixels',[])
  if len(pixels)!=64 or any(type(v)!=int or not 0<=v<=255 for v in pixels):raise ValueError('invalid pixels')
  if row.get('compile') is not True or row.get('link') is not True or row.get('gl_error')!=0 or row.get('status')!='EXECUTED':raise ValueError('execution failure')
  error=max(abs(a-b) for a,b in zip(pixels,golden))
  quality='PASS' if error<=32 else 'FAIL'
  if row.get('quality')!=quality or row.get('cpu_oracle_max_error')!=error or row.get('quality_budget')!=32:raise ValueError('quality labels or thresholds inconsistent')
  expected='PASS' if pattern=='smooth' else 'FAIL';harness &= quality==expected
  decisions.append({'id':row['id'],'quality_acceptance':quality,'optimization_status':'REJECTED_BY_QUALITY' if quality=='FAIL' else 'INSUFFICIENT_EVIDENCE','auto_accept':False,'reason':'software correctness does not prove physical GPU performance'})
 return {'harness_status':'HOST_PASS' if harness else 'FAIL','decisions':decisions,'verified_improvement':False}
