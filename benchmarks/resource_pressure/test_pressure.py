"""Run current GL code once, then exercise the evidence validator with mutations.

Negative mutations below are synthetic report corruption, not GPU executions.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from validate import validate_rows

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

class ResourcePressureRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='gles-pressure-regression-')
        report=Path(cls.temp.name)/'run.json'
        command=[sys.executable,str(HERE/'run.py'),'--output',str(report)]
        if os.environ.get('GLES_SDK_ROOT'):command+=['--sdk',os.environ['GLES_SDK_ROOT']]
        result=subprocess.run(command,capture_output=True,text=True,timeout=360)
        if result.returncode!=0:raise RuntimeError(result.stdout+result.stderr+(report.read_text() if report.exists() else ''))
        cls.report=json.loads(report.read_text())
        cls.rows=[json.loads(x) for x in cls.report['host_run']['stdout'].splitlines()]
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_actual_hundred_scene_host_run(self):
        self.assertEqual(validate_rows(self.rows,100)['scenes'],100)
        for name,expected in self.report['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected)
    def test_missing_scene_rejected(self):
        rows=copy.deepcopy(self.rows);del rows[2]
        with self.assertRaises(ValueError):validate_rows(rows,100)
    def test_duplicate_scene_rejected(self):
        rows=copy.deepcopy(self.rows);rows.insert(3,copy.deepcopy(rows[2]))
        with self.assertRaises(ValueError):validate_rows(rows,100)
    def test_resource_growth_rejected(self):
        rows=copy.deepcopy(self.rows);rows[2]['live_owned_objects']=1
        with self.assertRaises(ValueError):validate_rows(rows,100)
    def test_missing_delete_rejected(self):
        rows=copy.deepcopy(self.rows);rows[-1]['summary']['object_counters'][1]['deleted']-=1
        with self.assertRaises(ValueError):validate_rows(rows,100)
    def test_undisclosed_synthetic_completion_rejected(self):
        rows=copy.deepcopy(self.rows);rows[1]['real_gpu_delayed_completion']=True
        with self.assertRaises(ValueError):validate_rows(rows,100)
    def test_device_claim_rejected(self):
        rows=copy.deepcopy(self.rows);rows[-1]['summary']['android_real_loss']='PASS'
        with self.assertRaises(ValueError):validate_rows(rows,100)
    def test_residency_claim_rejected(self):
        rows=copy.deepcopy(self.rows);rows[-1]['summary']['vram_residency_measurement']=0
        with self.assertRaises(ValueError):validate_rows(rows,100)
    def test_generation_mismatch_rejected(self):
        rows=copy.deepcopy(self.rows);rows[27]['context_generation']=1
        with self.assertRaises(ValueError):validate_rows(rows,100)
    def test_fence_observation_mismatch_rejected(self):
        rows=copy.deepcopy(self.rows);rows[-1]['summary']['actual_zero_timeout_pending']+=1
        with self.assertRaises(ValueError):validate_rows(rows,100)
    def test_short_run_not_accepted(self):
        with self.assertRaises(ValueError):validate_rows(self.rows,99)
    def test_empty_report_rejected(self):
        with self.assertRaises(ValueError):validate_rows([],100)

if __name__=='__main__':unittest.main()
