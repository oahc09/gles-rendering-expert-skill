"""Synthetic contract tests only. Their numbers are NOT GPU measurements."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('capture',Path(__file__).with_name('capture.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class CaptureTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        (self.base/'trace.txt').write_text('synthetic fixture only')
        arm=dict(frame_time_ms=[10,11,12],gpu_time_ms=[5,6,7],cpu_time_ms=[2,3,4],counters=[],counter_unavailable_reason='synthetic fixture',raw_trace_path='trace.txt',raw_trace_sha256=hashlib.sha256((self.base/'trace.txt').read_bytes()).hexdigest())
        self.data=dict(status='MEASURED',hardware_kind='physical',evidence_origin='target_device',scenario_id='GPU01',correctness={'status':'PASS','method':'fixture'},sampling={'independent_runs':3,'warmup_method':'fixture','order':'ABBA'},baseline=copy.deepcopy(arm),variant=copy.deepcopy(arm),fallback='baseline',negative_result='none observed in fixture')
        self.data.update({k:'synthetic fixture, not real hardware' for k in m.DEVICE_FIELDS})
    def tearDown(self): self.temp.cleanup()
    def test_structural_fixture_not_authentication(self):
        self.assertEqual(m.validate(self.data,self.base),[])
        self.assertEqual(m.summarize(self.data)['conclusion'],'REVIEW_REQUIRED')
    def test_hardware_required(self):
        self.data['hardware_kind']='software';self.assertTrue(m.validate(self.data,self.base))
    def test_missing_identity(self):
        self.data['driver']=None;self.assertTrue(m.validate(self.data,self.base))
    def test_raw_trace_hash(self):
        self.data['baseline']['raw_trace_sha256']='bad';self.assertTrue(m.validate(self.data,self.base))
    def test_missing_raw_trace(self):
        (self.base/'trace.txt').unlink();self.assertTrue(m.validate(self.data,self.base))
    def test_numerical_values(self):
        for value in [float('nan'),float('inf'),-1,True,'fast']:
            data=copy.deepcopy(self.data);data['variant']['gpu_time_ms'][0]=value;self.assertTrue(m.validate(data,self.base))
    def test_counter_null_not_fabricated(self):
        self.data['baseline'].pop('counter_unavailable_reason');self.assertTrue(m.validate(self.data,self.base))
    def test_correctness_first(self):
        self.data['correctness']['status']='FAIL';self.assertTrue(m.validate(self.data,self.base))
    def test_negative_and_fallback(self):
        self.data['negative_result']='';self.data['fallback']='';self.assertEqual(len(m.validate(self.data,self.base)),2)
    def test_blocked_cannot_claim_win(self):
        self.assertTrue(m.validate({'status':'BLOCKED_BY_HARDWARE','conclusion':'WIN'},self.base))
    def test_default_blocked_exit(self):
        out=self.base/'blocked.json';r=subprocess.run([sys.executable,m.__file__,'--output',str(out)],capture_output=True)
        self.assertEqual(r.returncode,3);self.assertEqual(json.loads(out.read_text())['summary']['conclusion'],'UNMEASURED')
    def test_adapter_failure(self):
        out=self.base/'fail.json';r=subprocess.run([sys.executable,m.__file__,'--output',str(out),'--adapter',json.dumps([sys.executable,'-c','raise SystemExit(4)'])],capture_output=True)
        self.assertEqual(r.returncode,2);self.assertEqual(json.loads(out.read_text())['status'],'ADAPTER_FAILED')
    def test_malformed_shapes(self):
        self.assertTrue(m.validate([],self.base))
        for field in ['baseline','variant','sampling','correctness']:
            data=copy.deepcopy(self.data);data[field]=[];self.assertTrue(m.validate(data,self.base))
    def test_trace_escape(self):
        self.data['baseline']['raw_trace_path']='../outside.txt';self.assertTrue(m.validate(self.data,self.base))
    def test_unknown_scene(self):
        self.data['scenario_id']='FAKE';self.assertTrue(m.validate(self.data,self.base))

if __name__=='__main__':unittest.main()
