import copy,json,unittest,hashlib
from pathlib import Path
from build_v106_cases import build,BASELINE_SHA256
from run import validate_cases,request_for
from score import score
HERE=Path(__file__).parent
class V106Cases(unittest.TestCase):
 def test_frozen_prefix(self):
  raw=(HERE/'cases-v1.0.5.json').read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),BASELINE_SHA256);self.assertEqual(build()['cases'][:112],json.loads(raw)['cases'])
 def test_count_and_ids(self):
  c=build();self.assertEqual(len(validate_cases(c)),142);self.assertEqual([x['case_id'] for x in c['cases'][112:]],[f'A{i:03d}' for i in range(113,143)]);self.assertEqual(c,json.loads((HERE/'cases-v1.0.6.json').read_text()))
 def test_modes_topics_no_fake_results(self):
  cs=build()['cases'][112:];self.assertEqual({c['mode'] for c in cs},{'Generate','Review','Diagnose','Optimize'});self.assertEqual(len({c['v106']['topic'] for c in cs}),10)
  for c in cs:self.assertEqual(c['v106']['model_calls'],0);self.assertEqual(c['compile_evidence']['status'],'NOT_RUN');self.assertFalse(c['device_capabilities']['hardware_evidence_available'])
 def test_api_context(self):
  for c in build()['cases'][112:]:
   if c['v106']['topic'] in ('compute','lighting'):self.assertEqual(c['device_capabilities']['gles_version'],'3.1');self.assertEqual(c['device_capabilities']['glsl_version'],'310 es')
 def test_no_rubric_leak(self):
  for c in build()['cases'][112:]:self.assertEqual(set(request_for(c,'skill',True)),{'schema_version','case_id','condition','system','prompt','capabilities'})
 def fixture(self):
  cases=build();c=cases['cases'][112];row={'case_id':c['case_id'],'condition':'with_skill','response_sha256':'x','reviewer':'synthetic unit reviewer','rationale':'unit contract only','true_positive_findings':c['expected_findings'],'rejected_legal_controls':[],'unsupported_findings':[]}
  summary={'results':[{'case_id':c['case_id'],'condition':'with_skill','response_sha256':'x','status':'RESPONSE_CAPTURED'}]};return cases,row,summary
 def test_unmeasured_metrics_null(self):
  cs,row,s=self.fixture();g=score(s,[row],cs)['metrics']['with_skill'];self.assertIsNone(g['correct_fix_rate']);self.assertIsNone(g['introduced_regression_rate'])
 def test_fix_requires_actual_regression(self):
  cs,row,s=self.fixture();row.update(correct_fix=True,correct_fix_rationale='synthetic test')
  with self.assertRaises(ValueError):score(s,[row],cs)
 def test_failed_regression_cannot_correct(self):
  cs,row,s=self.fixture();row.update(correct_fix=True,correct_fix_rationale='unit',repair_regression={'status':'FAIL','command':'unit','artifact_sha256':'a','log_sha256':'b','environment':'unit'})
  with self.assertRaises(ValueError):score(s,[row],cs)
 def test_different_suite_cannot_pair(self):
  cs,row,s=self.fixture();e={'status':'PASS','command':'unit','artifact_sha256':'a','log_sha256':'b','environment':'unit','suite_sha256':'old'};row['baseline_regression']=e;row['repair_regression']=dict(e,suite_sha256='new')
  with self.assertRaises(ValueError):score(s,[row],cs)
 def test_regression_pair_metric_unit_only(self):
  cs,row,s=self.fixture();e={'status':'PASS','command':'unit','artifact_sha256':'a','log_sha256':'b','environment':'unit','suite_sha256':'same'};row['baseline_regression']=e;row['repair_regression']=dict(e,status='FAIL');g=score(s,[row],cs)['metrics']['with_skill'];self.assertEqual(g['regression_pairs'],1);self.assertEqual(g['introduced_regression_rate'],1)
 def test_marked_synthetic_summary_rejected(self):
  cs,row,s=self.fixture();s['synthetic_infrastructure_test']=True
  with self.assertRaises(ValueError):score(s,[row],cs)
if __name__=='__main__':unittest.main()
