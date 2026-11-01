"""These tests validate tooling only; no external model/GPU is called."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from build_cases import build
from run import validate_cases, request_for, digest, HERE
from score import score

class InfrastructureTests(unittest.TestCase):
    def test_64_unique_cases_balanced(self):
        cases=validate_cases(build())
        self.assertEqual(len(cases),64)
        for mode in ('Generate','Review','Diagnose','Optimize'):
            self.assertEqual(sum(c['mode']==mode for c in cases),16)
        self.assertEqual(len({c['prompt'] for c in cases}),64)
    def test_materialized_cases_current(self):
        self.assertEqual(json.loads((HERE/'cases.json').read_text()),build())
    def test_duplicate_id_rejected(self):
        data=build(); data['cases'][1]['case_id']=data['cases'][0]['case_id']
        with self.assertRaises(ValueError): validate_cases(data)
    def test_skill_conditioning_and_no_groundtruth_leak(self):
        case=build()['cases'][0]
        off=request_for(case,'SECRET_SKILL_CONTENT',False)
        on=request_for(case,'SECRET_SKILL_CONTENT',True)
        self.assertNotIn('SECRET_SKILL_CONTENT',json.dumps(off))
        self.assertIn('SECRET_SKILL_CONTENT',json.dumps(on))
        for hidden in ('expected_findings','legal_controls','fallback','rubric'):
            self.assertNotIn(hidden,on)
    def test_no_provider_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'out'
            result=subprocess.run([sys.executable,str(HERE/'run.py'),'--output',str(output)],capture_output=True)
            self.assertEqual(result.returncode,2,result.stderr)
            summary=json.loads((output/'summary.json').read_text())
            self.assertEqual(summary['status'],'BLOCKED_BY_PROVIDER')
            self.assertEqual(summary['results'],[])
    def test_fixture_adapter_records_both_conditions(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); adapter=root/'adapter.py'
            adapter.write_text('import json,sys\nr=json.load(sys.stdin)\nprint("SYNTHETIC FIXTURE "+r["condition"])\n')
            output=root/'out'
            result=subprocess.run([sys.executable,str(HERE/'run.py'),'--adapter',f'{sys.executable} {adapter}','--provider-label','synthetic-test-not-a-model','--synthetic-fixture','--case','A001','--output',str(output)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            summary=json.loads((output/'summary.json').read_text())
            self.assertEqual(len(summary['results']),2)
            self.assertEqual(summary['model_quality'],'NOT_EVALUATED')
            with self.assertRaises(ValueError): score(summary,[],build())
    def test_timeout_is_failure_not_response(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); adapter=root/'adapter.py'
            adapter.write_text('import time\ntime.sleep(10)\n')
            result=subprocess.run([sys.executable,str(HERE/'run.py'),'--adapter',f'{sys.executable} {adapter}','--provider-label','synthetic-timeout','--synthetic-fixture','--timeout','0.05','--case','A001','--output',str(root/'out')],capture_output=True)
            self.assertEqual(result.returncode,1)
            summary=json.loads((root/'out'/'summary.json').read_text())
            self.assertTrue(all(r['status']=='ADAPTER_FAILED' for r in summary['results']))
    def row(self):
        case=build()['cases'][0]
        return {'case_id':'A001','condition':'no_skill','response_sha256':'abc','reviewer':'fixture-human','rationale':'synthetic scoring arithmetic test only','true_positive_findings':case['expected_findings'][:2],'rejected_legal_controls':case['legal_controls'],'unsupported_findings':[], 'compile':{'status':'NOT_RUN'}}
    def summary(self):
        return {'synthetic_infrastructure_test':False,'results':[{'case_id':'A001','condition':'no_skill','response_sha256':'abc','status':'RESPONSE_CAPTURED'}]}
    def test_metric_arithmetic_and_unmeasured_compile(self):
        metrics=score(self.summary(),[self.row()],build())['metrics']['no_skill']
        self.assertEqual(metrics['finding_recall'],2/3)
        self.assertEqual(metrics['finding_precision'],2/3)
        self.assertEqual(metrics['legal_control_false_positive_rate'],1)
        self.assertIsNone(metrics['compile_success_rate'])
    def test_stale_hash_rejected(self):
        row=self.row(); row['response_sha256']='bad'
        with self.assertRaises(ValueError): score(self.summary(),[row],build())
    def test_compile_claim_requires_artifact_evidence(self):
        row=self.row(); row['compile']={'status':'PASS'}
        with self.assertRaises(ValueError): score(self.summary(),[row],build())
    def test_unknown_true_positive_rejected(self):
        row=self.row(); row['true_positive_findings']=['not-in-rubric']
        with self.assertRaises(ValueError): score(self.summary(),[row],build())
    def score_cli(self, corpus_change=False, evidence_escape=False):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run=root/'run'; run.mkdir()
            corpus=json.dumps(build()); (root/'cases.json').write_text(corpus)
            summary=self.summary(); summary['case_source_sha256']=digest('changed' if corpus_change else corpus)
            summary['results'][0]['response_sha256']=digest('response')
            summary['results'][0]['response_file']='response.txt'
            (run/'response.txt').write_text('response')
            (run/'summary.json').write_text(json.dumps(summary))
            row=self.row(); row['response_sha256']=digest('response')
            if evidence_escape:
                (root/'outside.cpp').write_text('code')
                row['compile']={'status':'PASS','command':'compiler fixture','artifact_file':'../outside.cpp','artifact_sha256':digest('code'),'log_file':'log','log_sha256':digest('log'),'environment':'synthetic'}
            (root/'rows.json').write_text(json.dumps([row]))
            result=subprocess.run([sys.executable,str(HERE/'score.py'),'--run',str(run),'--cases',str(root/'cases.json'),'--adjudications',str(root/'rows.json'),'--output',str(root/'metrics.json'),'--evidence-root',str(run)],capture_output=True)
            return result
    def test_cli_rejects_changed_corpus(self):
        result=self.score_cli(corpus_change=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn(b'Corpus changed',result.stderr)
    def test_cli_rejects_evidence_path_escape(self):
        result=self.score_cli(evidence_escape=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn(b'outside root',result.stderr)
    def test_cli_valid_adjudication(self):
        result=self.score_cli()
        self.assertEqual(result.returncode,0,result.stderr)
    def test_empty_adjudication_is_not_success(self):
        self.assertEqual(score(self.summary(),[],build())['status'],'PARTIAL_REVIEW')

if __name__=='__main__': unittest.main(verbosity=2)
