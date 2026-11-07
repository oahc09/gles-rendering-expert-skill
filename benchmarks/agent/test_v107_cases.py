import copy
import hashlib
import json
from pathlib import Path
import unittest
from build_v107_cases import build, BASELINE_SHA256
from run import validate_cases, request_for
from score import score

HERE = Path(__file__).parent

class PipelineCases(unittest.TestCase):
    def setUp(self):
        self.payload = build()
        self.case = self.payload['cases'][142]
        self.row = {'case_id': self.case['case_id'], 'condition': 'with_skill', 'response_sha256': 'unit-hash',
                    'reviewer': 'synthetic unit test only', 'rationale': 'infrastructure control',
                    'true_positive_findings': self.case['expected_findings'],
                    'rejected_legal_controls': [], 'unsupported_findings': []}
        self.summary = {'results': [{'case_id': self.case['case_id'], 'condition': 'with_skill',
                                     'response_sha256': 'unit-hash', 'status': 'RESPONSE_CAPTURED'}]}

    def metric(self):
        return score(self.summary, [self.row], self.payload)['metrics']['with_skill']

    def test_frozen_prefix_and_generated_inventory(self):
        raw = (HERE / 'cases-v1.0.6.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), BASELINE_SHA256)
        self.assertEqual(self.payload['cases'][:142], json.loads(raw)['cases'])
        self.assertEqual(self.payload, json.loads((HERE / 'cases-v1.0.7.json').read_text()))
        self.assertEqual(len(validate_cases(self.payload)), 172)
        self.assertEqual([c['case_id'] for c in self.payload['cases'][142:]], [f'A{i:03d}' for i in range(143,173)])

    def test_distinct_prompts_topics_and_modes(self):
        cases = self.payload['cases']
        self.assertEqual(len({c['prompt'] for c in cases}), 172)
        added = cases[142:]
        self.assertEqual(len({c['v107']['topic'] for c in added}), 10)
        self.assertEqual({c['mode'] for c in added}, {'Generate','Review','Diagnose','Optimize'})
        for c in added:
            self.assertEqual(c['v107']['model_calls'], 0)
            self.assertEqual(c['compile_evidence']['status'], 'NOT_RUN')
            self.assertEqual(set(request_for(c, 'skill', True)), {'schema_version','case_id','condition','system','prompt','capabilities'})

    def test_unknown_metrics_are_null(self):
        for key in ('first_run_success_rate','numeric_success_rate','visual_success_rate','correct_fix_rate'):
            self.assertIsNone(self.metric()[key])

    def test_compile_does_not_imply_runtime_or_visual(self):
        self.row['compile'] = self.evidence()
        self.assertEqual(self.metric()['compile_success_rate'], 1)
        self.assertIsNone(self.metric()['first_run_success_rate'])

    def evidence(self):
        return {'status':'PASS','command':'unit-fixture','artifact_sha256':'a','log_sha256':'b','environment':'unit-fixture'}

    def test_stage_requires_artifact_evidence(self):
        for stage in ('first_run','numeric','visual'):
            with self.subTest(stage=stage):
                self.row[stage] = {'status':'PASS'}
                with self.assertRaises(ValueError): self.metric()
                del self.row[stage]

    def test_numeric_and_visual_require_criteria(self):
        for stage in ('numeric','visual'):
            self.row[stage] = self.evidence()
            with self.assertRaises(ValueError): self.metric()
            self.row[stage]['criteria_reference'] = 'frozen-independent-criteria'
        self.assertEqual(self.metric()['visual_success_rate'], 1)

    def test_independent_first_run_failure(self):
        self.row['compile'] = self.evidence()
        self.row['first_run'] = dict(self.evidence(),status='FAIL')
        self.assertEqual(self.metric()['compile_success_rate'], 1)
        self.assertEqual(self.metric()['first_run_success_rate'], 0)

    def test_synthetic_report_is_not_model_result(self):
        self.summary['synthetic_infrastructure_test'] = True
        with self.assertRaises(ValueError): self.metric()

    def test_fix_requires_post_patch_regression(self):
        self.row.update(correct_fix=True, correct_fix_rationale='test')
        with self.assertRaises(ValueError): self.metric()

if __name__ == '__main__': unittest.main()
