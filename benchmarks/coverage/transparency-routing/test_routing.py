import copy,hashlib,importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).parent
s=importlib.util.spec_from_file_location('transparency_router',HERE/'run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):self.e,self.b=m.read_bundle(HERE/'mesa-final');self.q=m.requests()
 def test_real_routes_both(self):
  for name in ('mesa','angle'):
   e,b=m.read_bundle(HERE/(name+'-final'));rows=[m.choose(q,e,b) for q in self.q];self.assertEqual([r['selection'] for r in rows],['SORTED_ALPHA','SORTED_ALPHA','DEPTH_PEELING','DEPTH_PEELING']+['UNAVAILABLE']*4)
   self.assertEqual([r.get('max_error') for r in rows[:4]],[0,0,1,1]);report=json.loads((HERE/(name+'-final/report.json')).read_text());self.assertEqual(report['actual_full_suite_counts'],{'draws':278,'readbacks':65,'occlusion_queries':38})
 def test_geometry_mutation(self):
  q=copy.deepcopy(self.q[2]);q['layers'][0]['rgba'][0]=.5;self.assertEqual(m.choose(q,self.e,self.b)['reason'],'UNREGISTERED_OR_CHANGED_GEOMETRY')
 def test_schema_mutation(self):
  q=copy.deepcopy(self.q[0]);q['command']='anything';self.assertEqual(m.choose(q,self.e,self.b)['reason'],'INVALID_REQUEST_SCHEMA')
 def test_budget_quality_types(self):
  for field,v in [('layer_budget',True),('layer_budget',0),('layer_budget',4),('quality_max_byte_error',3),('quality_max_byte_error',float('nan'))]:
   q=copy.deepcopy(self.q[0]);q[field]=v;self.assertEqual(m.choose(q,self.e,self.b)['selection'],'UNAVAILABLE')
 def test_no_approximate_fallback(self):
  q=copy.deepcopy(self.q[0]);q['require_exact']=False;self.assertEqual(m.choose(q,self.e,self.b)['selection'],'UNAVAILABLE')
 def test_body_changed(self):
  self.e['peel']['cases'][0]['pixels'][0]=0;self.assertEqual(m.choose(self.q[3],self.e,self.b)['reason'],'EVIDENCE_BODY_OR_EXECUTION_MISMATCH')
 def test_hash_changed(self):
  self.b['sorted']['body_sha256']='0'*64;self.assertEqual(m.choose(self.q[0],self.e,self.b)['reason'],'EVIDENCE_BODY_OR_EXECUTION_MISMATCH')
 def test_actual_source_required(self):
  self.e['peel']['source_sha256']='0'*64;self.b['peel']['body_sha256']=m.input_hash(self.e['peel']);self.assertEqual(m.choose(self.q[3],self.e,self.b)['reason'],'EVIDENCE_SOURCE_MISMATCH')
 def test_collector_failure(self):
  self.b['sorted']['exit_code']=1;self.assertEqual(m.choose(self.q[0],self.e,self.b)['selection'],'UNAVAILABLE')
 def test_unsupported_peel(self):
  self.e['peel']['status']='UNSUPPORTED_FORMAT';self.b['peel']['body_sha256']=m.input_hash(self.e['peel']);self.assertEqual(m.choose(self.q[3],self.e,self.b)['reason'],'PEEL_EXECUTION_UNAVAILABLE')
 def test_budget_capture_tamper(self):
  self.e['peel']['cases'][0]['layer_budget']=2;self.b['peel']['body_sha256']=m.input_hash(self.e['peel']);self.assertEqual(m.choose(self.q[3],self.e,self.b)['reason'],'PEEL_REQUEST_MISMATCH')
 def test_file_and_path_tampering(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'e';shutil.copytree(HERE/'mesa-final',p);(p/'peel.json').write_text('{}')
   with self.assertRaises(ValueError):m.read_bundle(p)
 def test_freeze_drift(self):
  with patch.object(m,'sha',return_value='changed'):
   with self.assertRaises(ValueError):m.verify_freeze()
 def test_all_unavailable_fails_default_acceptance(self):
  rows=[m.choose(q,self.e,self.b) for q in self.q];self.assertTrue(m.suite_acceptance(rows))
  for r in rows:r['selection']='UNAVAILABLE'
  self.assertFalse(m.suite_acceptance(rows));self.assertFalse(m.suite_acceptance([]))
 def test_malformed_receipts_controlled_rejection(self):
  for evidence,bindings in [(None,self.b),(self.e,[]),(self.e,{'weighted':None})]:self.assertEqual(m.choose(self.q[0],evidence,bindings)['selection'],'UNAVAILABLE')
 def test_malformed_bundle_controlled_error(self):
  with tempfile.TemporaryDirectory() as td:
   (Path(td)/'report.json').write_text('{"receipts":null}')
   with self.assertRaises(ValueError):m.read_bundle(td)
 def test_not_relabel_weighted_input(self):
  r=m.choose(self.q[3],self.e,self.b);self.assertEqual(r['weighted_candidate_audit']['status'],'NOT_APPLICABLE_DIFFERENT_REGISTERED_INPUTS');self.assertFalse(r['weighted_candidate_audit']['exact_fallback_allowed'])
if __name__=='__main__':unittest.main()
