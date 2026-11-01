import copy
import hashlib
import json
from pathlib import Path
import unittest
from run import HERE,validate_cases,request_for
from score import score
class RepairTests(unittest.TestCase):
    def setUp(self):self.data=json.loads((HERE/'cases-v1.0.4.json').read_text())
    def test_original_64_unchanged(self):self.assertEqual(self.data['cases'][:64],json.loads((HERE/'cases.json').read_text())['cases'])
    def test_88_unique_and_24_repairs(self):
        c=validate_cases(self.data);self.assertEqual(len(c),88);self.assertEqual(sum('repair' in x for x in c),24)
    def test_failure_logs_are_inputs_not_gold(self):
        r=request_for(self.data['cases'][64],'skill',True);self.assertIn('Actual failure log:',r['prompt']);self.assertNotIn('expected_findings',r);self.assertNotIn('repair',r)
    def test_report_identity(self):
        for c in self.data['cases'][64:]:
            p=HERE.parents[1]/c['repair']['reproduction_report'];self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),c['repair']['reproduction_sha256'])
    def response(self):
        c=self.data['cases'][64];s={'results':[{'case_id':c['case_id'],'condition':'no_skill','status':'RESPONSE_CAPTURED','response_sha256':'fixture'}]};a={'case_id':c['case_id'],'condition':'no_skill','response_sha256':'fixture','reviewer':'synthetic arithmetic fixture','rationale':'Not an actual model evaluation','true_positive_findings':c['expected_findings'],'rejected_legal_controls':[],'unsupported_findings':[],'debug_complete':True,'compile':{'status':'NOT_RUN'}};return s,a
    def test_unknown_metrics_null(self):
        s,a=self.response();m=score(s,[a],self.data)['metrics']['no_skill'];self.assertIsNone(m['root_cause_hit_rate']);self.assertIsNone(m['repair_regression_success_rate'])
    def test_scored_repair_denominators(self):
        s,a=self.response();a.update(root_cause_hit=True,unsupported_performance_claim=False);m=score(s,[a],self.data)['metrics']['no_skill'];self.assertEqual(m['root_cause_hit_reviewed'],1);self.assertEqual(m['root_cause_hit_rate'],1);self.assertEqual(m['unsupported_performance_claim_rate'],0)
    def test_fake_repair_pass_no_evidence_rejected(self):
        s,a=self.response();a['repair_regression']={'status':'PASS'}
        with self.assertRaises(ValueError):score(s,[a],self.data)
if __name__=='__main__':unittest.main()
