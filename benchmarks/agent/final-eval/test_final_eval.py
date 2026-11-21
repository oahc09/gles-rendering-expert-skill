import copy,importlib.util,json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('final_evaluate',Path(__file__).with_name('evaluate.py'));ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)
class FinalEvalTests(unittest.TestCase):
 def test_frozen_categories(self):
  p=ev.validate();self.assertEqual(len(p['cases']),100);self.assertEqual(len({r['prompt'] for r in p['cases']}),100)
 def test_hidden_rubric(self):
  from run import request_for
  c=ev.validate()['cases'][0];r=request_for(c,'skill',False)
  self.assertNotIn('rubric',r);self.assertNotIn('expected_findings',r);self.assertNotIn(c['expected_findings'][0],r['prompt'])
 def test_null_interval(self):self.assertIsNone(ev.wilson(0,0))
 def test_small_sample_uncertainty(self):self.assertGreater(ev.wilson(0,20)[1],.05)
 def test_interval_bounds(self):
  for n in (1,20,100):
   for k in range(n+1):
    lo,hi=ev.wilson(k,n);self.assertTrue(0<=lo<=hi<=1)
 def test_bad_interval(self):
  with self.assertRaises(ValueError):ev.wilson(2,1)
 def test_synthetic_cannot_score(self):
  from score import score
  with self.assertRaises(ValueError):score({'synthetic_infrastructure_test':True},[],ev.validate())
 def test_no_provider_actual_shared_runner(self):
  import argparse
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);skill=root/'skill';skill.write_text('fixture only');out=root/'capture'
   args=argparse.Namespace(cases=ev.HERE/'cases.json',case=None,output=out,skill=skill,provider_label=None,synthetic_fixture=False,adapter=None)
   self.assertEqual(ev.capture(args),2);reviews=root/'reviews';reviews.write_text('[]')
   r=ev.summary(out,reviews);self.assertEqual(r['status'],'BLOCKED_BY_PROVIDER');self.assertIsNone(r['cost']['total']);self.assertEqual(r['paired_cases'],0)
   self.assertIsNone(r['final_metrics']['with_skill']['first_run']['ratio'])
 def test_frozen_mutation(self):
  original=ev.sha
  with patch.object(ev,'sha',side_effect=lambda p:'bad' if str(p).endswith('cases.json') else original(p)):
   with self.assertRaises(ValueError):ev.validate()
 def test_new_ids_not_old(self):
  ids={c['case_id'] for c in ev.validate()['cases']}
  for p in ev.HERE.parent.glob('cases*.json'):self.assertFalse(ids & {c['case_id'] for c in json.loads(p.read_text())['cases']})
if __name__=='__main__':unittest.main()
