import json,unittest
from score import score
from run import HERE
class V105Metrics(unittest.TestCase):
 def setUp(self):
  self.cases=json.loads((HERE/'cases-v1.0.5.json').read_text());c=self.cases['cases'][88]
  self.summary={'results':[{'case_id':c['case_id'],'condition':'no_skill','status':'RESPONSE_CAPTURED','response_sha256':'arithmetic-fixture'}]}
  self.row={'case_id':c['case_id'],'condition':'no_skill','response_sha256':'arithmetic-fixture','reviewer':'synthetic scoring arithmetic only','rationale':'not an actual model response','true_positive_findings':[],'rejected_legal_controls':[],'unsupported_findings':[]}
 def metrics(self):return score(self.summary,[self.row],self.cases)['metrics']['no_skill']
 def test_missing_is_null(self):
  m=self.metrics()
  for key in ('evidence_sufficient_rate','visual_safe_rate','wrong_advice_rate','root_cause_hit_rate'):self.assertIsNone(m[key])
 def test_requires_rationale(self):
  self.row['evidence_sufficient']=True
  with self.assertRaises(ValueError):self.metrics()
 def test_visual_requires_independent_criteria(self):
  self.row.update(visual_safe=True,visual_safe_rationale='arithmetic fixture')
  with self.assertRaises(ValueError):self.metrics()
 def test_denominators(self):
  self.row.update(evidence_sufficient=True,evidence_sufficient_rationale='fixture',visual_safe=False,visual_safe_rationale='fixture',visual_criteria_reference='fixed prior threshold fixture',wrong_advice=True,wrong_advice_rationale='fixture',root_cause_hit=False)
  m=self.metrics();self.assertEqual(m['evidence_sufficient_rate'],1);self.assertEqual(m['visual_safe_rate'],0);self.assertEqual(m['wrong_advice_rate'],1);self.assertEqual(m['root_cause_hit_rate'],0)
 def test_string_not_bool(self):
  self.row['visual_safe']='yes'
  with self.assertRaises(ValueError):self.metrics()
if __name__=='__main__':unittest.main()
