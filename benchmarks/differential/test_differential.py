import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('differential',HERE/'run.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

class DifferentialTests(unittest.TestCase):
    def test_corpus_reuses_w1_and_has_four_domains(self):
        cases=d.cases()
        self.assertEqual(len(cases),47)
        self.assertEqual(len({c['id'] for c in cases}),47)
        self.assertEqual({c['kind'] for c in cases},{'shader','api_error','fbo_pixels','ssbo_numeric'})
        self.assertEqual(len([c for c in cases if c['kind']=='shader']),26)
    def test_missing_is_not_pass(self):
        c=d.cases()[0]
        self.assertEqual(d.compare(c,{'status':'UNKNOWN'},{'status':'UNKNOWN'}),'UNKNOWN')
        self.assertEqual(d.compare(c,{'status':'SKIP_UNSUPPORTED'},{'status':'UNKNOWN'}),'SKIP_UNSUPPORTED')
    def test_compile_and_link_are_independent(self):
        c=next(c for c in d.cases() if c['id']=='300-invalid-varying')
        row=dict(status='EXECUTED',compile=True,link=False,harness_gl_error=0)
        self.assertEqual(d.compare(c,row,row),'PASS')
        self.assertEqual(d.compare(c,row,dict(row,compile=False)),'FAIL')
    def test_rgba8_tolerance_boundary_and_golden(self):
        c=next(c for c in d.cases() if c['id']=='fbo-black')
        row=dict(status='EXECUTED',pixels=c['expected']*16,harness_gl_error=0)
        near=copy.deepcopy(row);near['pixels'][0]=1
        self.assertEqual(d.compare(c,row,near),'PASS')
        near['pixels'][0]=2
        self.assertEqual(d.compare(c,row,near),'FAIL')
        self.assertEqual(d.compare(c,near,near),'FAIL')
    def test_numeric_tolerance_and_nan(self):
        c=next(c for c in d.cases() if c['id']=='ssbo-add')
        row=dict(status='EXECUTED',compile=True,link=True,numeric=5.,harness_gl_error=0)
        self.assertEqual(d.compare(c,row,dict(row,numeric=5.000001)),'PASS')
        for value in (float('nan'),float('inf'),5.001):self.assertEqual(d.compare(c,row,dict(row,numeric=value)),'FAIL')
    def test_error_not_masked(self):
        c=next(c for c in d.cases() if c['id']=='pack-invalid')
        row=dict(status='EXECUTED',api_error=0x501,harness_gl_error=0)
        self.assertEqual(d.compare(c,row,row),'PASS')
        self.assertEqual(d.compare(c,row,dict(row,harness_gl_error=0x502)),'FAIL')
    def test_reducer_preserves_pair_not_any_failure(self):
        c=next(c for c in d.cases() if c['id']=='300-invalid-type')
        a=dict(id=c['id'],status='EXECUTED',compile=True,link=True,harness_gl_error=0)
        b=dict(a,compile=False,link=False)
        def replay(config,selected):
            # Unit fixture, deliberately not recorded as real-driver evidence.
            row=a if config==0 else b
            if 'mat4' not in selected[0]['sources']['shader.frag']:row=dict(row,compile=False,link=False)
            return dict(status='EXECUTED',cases=[row])
        with tempfile.TemporaryDirectory() as t,patch.object(d,'isolated',side_effect=replay):
            r=d.reduce_mismatch(c,[0,1],[a,b],Path(t))
            self.assertEqual(r['status'],'REPRODUCED')
            self.assertIn('mat4',(Path(t)/'reduced.frag').read_text())
            self.assertFalse(r['semantic_global_minimality'])
            self.assertLessEqual(len(r['trials']),12)
    def test_unavailable_reduction_is_inconclusive(self):
        c=next(c for c in d.cases() if c['id']=='pack-invalid')
        with tempfile.TemporaryDirectory() as t,patch.object(d,'isolated',return_value=dict(status='UNKNOWN',cases=[])):
            r=d.reduce_mismatch(c,[0,1],[{},{}],Path(t))
            self.assertEqual(r['status'],'INCONCLUSIVE')
            self.assertFalse(r['one_minimal'])
    def test_saved_actual_evidence(self):
        report=json.loads((HERE/'evidence/summary.json').read_text())
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(report['executed_comparisons'],47)
        self.assertEqual({x['implementation'] for x in report['implementations']},{'mesa','angle'})
        self.assertEqual(report['real_gpu_gate'],'BLOCKED_BY_HARDWARE')
        self.assertTrue(all(x['libraries'] and x['renderer'] for x in report['implementations']))

if __name__=='__main__':unittest.main()
