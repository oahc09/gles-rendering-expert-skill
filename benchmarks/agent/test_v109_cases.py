import copy
import json
import unittest
from build_v109_cases import build,TASKS,HERE
from run import validate_cases,request_for
from score_v109 import score

class V109Tests(unittest.TestCase):
    def test_thirty_distinct(self):
        self.assertEqual(len(TASKS),30); self.assertEqual(len({t[1] for t in TASKS}),30)
    def test_runner_compatibility(self): self.assertEqual(len(validate_cases(build())),202)
    def test_baseline_preserved(self): self.assertEqual(build()['cases'][:172],json.loads((HERE/'cases-v1.0.7.json').read_text())['cases'])
    def test_deterministic(self): self.assertEqual(build(),build())
    def test_generated_matches(self): self.assertEqual(build(),json.loads((HERE/'cases-v1.0.9.json').read_text()))
    def test_ground_truth_not_sent(self):
        r=request_for(build()['cases'][-1],'skill',True); self.assertNotIn('expected_findings',r); self.assertNotIn('rubric',r)
    def test_fixture_rejected(self):
        with self.assertRaises(ValueError): score({'synthetic_infrastructure_test':True},[],build())
    def test_unmeasured_null(self):
        r=score({'synthetic_infrastructure_test':False,'results':[]},[],build()); self.assertEqual(r['v109_metrics'],{})

    def test_execution_claim_needs_evidence(self):
        c=build()['cases'][-1]
        summary={'synthetic_infrastructure_test':False,'results':[{'case_id':c['case_id'],'condition':'with_skill','status':'RESPONSE_CAPTURED','response_sha256':'abc'}]}
        row={'case_id':c['case_id'],'condition':'with_skill','response_sha256':'abc','reviewer':'fixture-reviewer','rationale':'fixture','true_positive_findings':[], 'rejected_legal_controls':[], 'unsupported_findings':[], 'performance_complete':False,'v109_metrics':{'run_pass':True}}
        with self.assertRaises(ValueError): score(summary,[row],build())
    def test_declared_hashes_not_evidence(self):
        c=build()['cases'][-1]
        summary={'synthetic_infrastructure_test':False,'results':[{'case_id':c['case_id'],'condition':'with_skill','status':'RESPONSE_CAPTURED','response_sha256':'abc'}]}
        row={'case_id':c['case_id'],'condition':'with_skill','response_sha256':'abc','reviewer':'fixture-reviewer','rationale':'fixture','true_positive_findings':[], 'rejected_legal_controls':[], 'unsupported_findings':[], 'performance_complete':False,'v109_metrics':{'run_pass':True},'v109_evidence':{'run_pass':{'artifact_sha256':'x','log_sha256':'y','command':'test','environment':'fixture'}}}
        with self.assertRaises(ValueError): score(summary,[row],build())

if __name__=='__main__': unittest.main()
