import copy,json,tempfile,unittest
from pathlib import Path
import runtime_links as m
ROOT=Path(__file__).resolve().parents[2]
class Tests(unittest.TestCase):
 def setUp(self):
  self.doc=json.loads((ROOT/'references/coverage/runtime-links.json').read_text());self.cats={'gles':json.loads((ROOT/'references/coverage/gles-api-catalog.json').read_text())}
 def check(self,d=None,root=ROOT):return m.validate(root,d or self.doc,self.cats)
 def reject(self,key,value):
  d=copy.deepcopy(self.doc);d['rows'][0][key]=value;self.assertEqual(self.check(d)['status'],'INCOMPLETE')
 def test_real(self):
  r=self.check();self.assertEqual(r['status'],'RUNTIME_LINK_CONTRACT_PASS');self.assertEqual(r['linked_runtime_rows'],8);self.assertEqual(r['distinct_linked_apis'],6);self.assertEqual(r['compiled'],'NOT_EVALUATED')
 def test_missing(self):self.doc['rows'].pop();self.assertEqual(self.check()['status'],'INCOMPLETE')
 def test_ghost(self):self.reject('api','glImaginary')
 def test_version(self):self.reject('version','2.0')
 def test_extension(self):self.reject('extension','GL_KHR_robustness')
 def test_source_hash(self):self.reject('collector_sha256','0'*64)
 def test_report_hash(self):self.reject('report_sha256','0'*64)
 def test_path_escape(self):self.reject('report','../../tmp/private.json')
 def test_assertion(self):self.reject('positive','/policy_simulations/injected_disjoint_rejected')
 def test_polarity(self):self.reject('negative',self.doc['rows'][0]['positive'])
 def test_policy_not_actual(self):self.reject('negative_kind','POLICY_SIMULATION')
 def test_schema(self):self.doc['rows'][0]['expected']=True;self.assertEqual(self.check()['status'],'INCOMPLETE')
 def test_schema_bool_not_integer(self):self.doc['schema_version']=True;self.assertEqual(self.check()['status'],'INCOMPLETE')
 def tamper(self,mutate,index=0):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);d=copy.deepcopy(self.doc)
   for row in d['rows']:
    for field in ['collector','report']:
     path=root/row[field];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/row[field]).read_bytes())
   row=d['rows'][index];path=root/row['report'];r=json.loads(path.read_text());mutate(r);path.write_text(json.dumps(r));row['report_sha256']=m.sha(path)
   self.assertEqual(self.check(d,root)['status'],'INCOMPLETE')
 def test_bool_not_int_assertion(self):self.tamper(lambda r:r.update(synchronous_return_observed=1))
 def test_forged_expected_and_actual(self):
  def mutate(r):r['negative_cases'][1].update(expected_error=0,gl_error=0)
  self.tamper(mutate)
 def test_rehashed_wrong_collector(self):self.tamper(lambda r:r.update(source_sha256='0'*64))
 def test_unsupported_not_pass(self):self.tamper(lambda r:r.update(status='UNSUPPORTED'))
 def test_rehashed_robust_pixels(self):
  self.tamper(lambda r:r['routes'][0]['cases'][0].update(payload=[0]*128),4)
 def test_rehashed_canary_float_type(self):
  self.tamper(lambda r:r['routes'][0]['cases'][0].update(prefix_canary=[165.0]*16),4)
 def test_rehashed_debug_route_cap(self):
  self.tamper(lambda r:r.update(KHR_advertised=False,api_version=[2,0],route='core'),1)
 def test_rehashed_robust_cap(self):self.tamper(lambda r:r.update(KHR_robustness_advertised=False),5)
 def test_rehashed_external_cap(self):self.tamper(lambda r:r['capabilities'].update(GL_OES_EGL_image_external=False),6)
 def test_rehashed_timer_content(self):self.tamper(lambda r:r.update(workload_pixel_match=False),2)
 def test_registry_missing_api(self):self.cats['gles']['commands']=[c for c in self.cats['gles']['commands'] if c['name']!='glDebugMessageInsert'];self.assertEqual(self.check()['status'],'INCOMPLETE')
if __name__=='__main__':unittest.main()
