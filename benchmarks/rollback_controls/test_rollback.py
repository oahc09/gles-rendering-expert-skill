import importlib.util,json,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('rollback',HERE/'run.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class RollbackTests(unittest.TestCase):
 def validate(self,data):
  self.assertEqual(data['status'],'HOST_PASS');self.assertEqual(len(data['transactions']),4)
  for case in data['transactions']:
   self.assertEqual(case['restored_pixels'],data['baseline_pixels']);self.assertTrue(case['queried_bindings_match']);self.assertTrue(case['restored_byte_equal']);self.assertFalse(case['auto_accept']);self.assertFalse(case['verified_improvement'])
  self.assertTrue(data['transactions'][0]['candidate_differs']);self.assertTrue(data['transactions'][3]['candidate_differs'])
  self.assertEqual([x['decision'] for x in data['transactions']],['REJECTED_BY_QUALITY','INSUFFICIENT_EVIDENCE','INSUFFICIENT_EVIDENCE','REJECTED_BY_QUALITY'])
 def test_saved_dual_driver_evidence(self):
  for name in ('mesa','angle'):
   with self.subTest(name=name):self.validate(json.loads((HERE/'evidence'/f'{name}.json').read_text()))
 def test_gate_rejects_inconsistent_measurements(self):
  golden=[255,0,0,255]*16
  row=dict(pixels=golden,compile=True,link=True,gl_error=0,cpu_oracle_max_error=99)
  with self.assertRaises(ValueError):r.decide(row,golden)
 def test_missing_evidence_never_accepts(self):self.assertEqual(r.decide({},[0]*64,True),'INSUFFICIENT_EVIDENCE')
 def test_correct_single_observation_not_accepted(self):
  golden=[255,0,0,255]*16
  row=dict(id='pbo',pixels=golden,compile=True,link=True,gl_error=0,cpu_oracle_max_error=0,quality='PASS')
  self.assertEqual(r.decide(row,golden),'INSUFFICIENT_EVIDENCE')
if __name__=='__main__':unittest.main()
