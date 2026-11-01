"""Corpus/infrastructure checks only: zero live provider calls or model-quality scores."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from build_v105_cases import build, BASELINE_SHA256, GROUPS
from run import validate_cases, request_for

HERE=Path(__file__).resolve().parent

class V105CorpusTests(unittest.TestCase):
    def test_predecessor_file_and_exact_prefix(self):
        raw=(HERE/'cases-v1.0.4.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),BASELINE_SHA256)
        self.assertEqual(build()['cases'][:88],json.loads(raw)['cases'])
    def test_materialization_and_existing_schema_validator(self):
        corpus=build()
        self.assertEqual(json.loads((HERE/'cases-v1.0.5.json').read_text()),corpus)
        self.assertEqual(len(validate_cases(corpus)),112)
    def test_six_topics_four_distinct_modes_each(self):
        added=build()['cases'][88:]
        self.assertEqual(len(added),24)
        self.assertEqual([c['case_id'] for c in added],[f'A{i:03d}' for i in range(89,113)])
        for topic in GROUPS:
            cases=[c for c in added if c['v105']['topic']==topic]
            self.assertEqual(len(cases),4)
            self.assertEqual({c['mode'] for c in cases},{'Generate','Review','Diagnose','Optimize'})
    def test_no_evaluation_or_annotation_promotion(self):
        corpus=build()
        self.assertEqual(corpus['paired_model_evaluation'],'NOT_RUN_PROVIDER')
        self.assertEqual(corpus['annotation_status'],'REVIEW_REQUIRED_BEFORE_RELEASE')
        for case in corpus['cases'][88:]:
            self.assertEqual(case['v105']['model_calls'],0)
            self.assertEqual(case['compile_evidence']['status'],'NOT_RUN')
            self.assertIsNone(case['compile_evidence']['artifact'])
            self.assertFalse(case['device_capabilities']['hardware_evidence_available'])
    def test_no_annotation_ground_truth_in_requests(self):
        for case in build()['cases'][88:]:
            request=request_for(case,'skill text',True)
            self.assertEqual(set(request),{'schema_version','case_id','condition','system','prompt','capabilities'})
            for key in ('expected_findings','legal_controls','fallback','rubric','v105'):
                self.assertNotIn(key,request)
    def test_provider_absence_stays_blocked_for_112_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'blocked'
            result=subprocess.run([sys.executable,str(HERE/'run.py'),'--cases',str(HERE/'cases-v1.0.5.json'),
                '--output',str(output)],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,2,result.stderr)
            evidence=json.loads((output/'summary.json').read_text())
            self.assertEqual(evidence['status'],'BLOCKED_BY_PROVIDER')
            self.assertEqual(evidence['case_count'],112)
            self.assertEqual(evidence['results'],[])
            self.assertEqual(evidence['model_quality'],'NOT_EVALUATED')
    def test_duplicate_new_id_rejected(self):
        corpus=copy.deepcopy(build());corpus['cases'][-1]['case_id']='A089'
        with self.assertRaises(ValueError):validate_cases(corpus)
    def test_expected_labels_nonempty_and_unique(self):
        for case in build()['cases'][88:]:
            self.assertGreaterEqual(len(case['expected_findings']),3)
            self.assertTrue(case['legal_controls'])
            self.assertEqual(len(case['expected_findings']),len(set(case['expected_findings'])))
    def test_prompts_differ_from_existing_tasks(self):
        corpus=build();prompts=[c['prompt'] for c in corpus['cases']]
        self.assertEqual(len(prompts),len(set(prompts)))
    def test_visual_safety_not_fabricated_compile_result(self):
        for case in build()['cases'][88:]:
            self.assertIn('visual_safety',case['rubric'])
            if case['v105']['topic'] in ('quality','precision','visual_tradeoff'):
                self.assertTrue(case['v105']['visual_safety_required'])

if __name__=='__main__':unittest.main()
