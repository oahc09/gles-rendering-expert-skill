import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import policy as p

class Robustness(unittest.TestCase):
    def test_texture_valid(self): self.assertEqual(p.texture(4,4),64)
    def test_texture_negative(self): self.assertRaises(p.Rejected,p.texture,-1,4)
    def test_texture_zero(self): self.assertRaises(p.Rejected,p.texture,0,4)
    def test_texture_huge(self): self.assertRaises(p.Rejected,p.texture,2**63,2**63)
    def test_texture_budget(self): self.assertRaises(p.Rejected,p.texture,1024,1024)
    def test_texture_bool(self): self.assertRaises(p.Rejected,p.texture,True,4)
    def test_texture_channels(self): self.assertRaises(p.Rejected,p.texture,4,4,5)
    def test_shader_valid(self): self.assertIn('300 es',p.shader(b'#version 300 es\nvoid main(){}'))
    def test_shader_length(self): self.assertRaises(p.Rejected,p.shader,b'x'*(p.MAX_SHADER+1))
    def test_shader_encoding(self): self.assertRaises(p.Rejected,p.shader,b'\xff')
    def test_shader_nul(self): self.assertRaises(p.Rejected,p.shader,b'#version 300 es\x00')
    def test_shader_version(self): self.assertRaises(p.Rejected,p.shader,b'void main(){}')
    def test_dispatch_valid(self): self.assertEqual(p.dispatch(4,4,4),64)
    def test_dispatch_negative(self): self.assertRaises(p.Rejected,p.dispatch,-1,1,1)
    def test_dispatch_huge(self): self.assertRaises(p.Rejected,p.dispatch,2**63,1,1)
    def test_dispatch_product(self): self.assertRaises(p.Rejected,p.dispatch,64,64,2)
    def test_decode_short(self): self.assertRaises(p.Rejected,p.decode_rgba,b'abc',1,1)
    def test_decode_valid(self): self.assertEqual(len(p.decode_rgba(bytes(16),2,2)),16)
    def test_quota_cleanup(self):
        q=p.Quota();key=q.allocate(64);q.release(key);q.release(key);self.assertEqual(q.used,0)
    def test_quota_overflow(self):
        q=p.Quota();q.allocate(p.MAX_BYTES);self.assertRaises(p.Rejected,q.allocate,1);q.cleanup();self.assertEqual(q.used,0)
    def test_cleanup_rejection(self):
        def f(q,a): q.allocate(64);q.allocate(p.MAX_BYTES)
        r=p.controlled_job(f);self.assertEqual((r['status'],r['remaining_bytes']),('EXPECTED_ERROR',0))
    def test_cleanup_exception(self):
        def f(q,a): q.allocate(64);raise RuntimeError('authored harness failure')
        r=p.controlled_job(f);self.assertEqual((r['status'],r['remaining_bytes']),('HARNESS_FAILURE',0))
    def test_retry_timeout(self):
        def f(q,a):
            q.allocate(64)
            if a==0: raise TimeoutError('simulated watchdog')
        r=p.controlled_job(f,2);self.assertEqual(r['history'],['TEST_TIMEOUT','PASS']);self.assertEqual(r['remaining_bytes'],0)
    def test_retry_cap(self): self.assertRaises(p.Rejected,p.controlled_job,lambda q,a:None,4)
    def test_cancel_before_run(self): self.assertEqual(p.controlled_job(lambda q,a:self.fail('ran'),cancelled=True)['status'],'CANCELLED')
    def test_worker_cancel(self): self.assertEqual(p.worker_cancel(),{'status':'CANCELLED','cleanup':True})
    def test_process_timeout(self): self.assertEqual(p.isolated([sys.executable,'-c','import time;time.sleep(1)'],.02)['status'],'TEST_TIMEOUT')
    def test_process_error(self): self.assertEqual(p.isolated([sys.executable,'-c','raise RuntimeError("authored")'])['status'],'HARNESS_FAILURE')
    def test_process_signal_not_driver_proof(self): self.assertEqual(p.isolated([sys.executable,'-c','import os,signal;os.kill(os.getpid(),signal.SIGTERM)'])['status'],'HARNESS_FAILURE')
    def test_missing_executable(self): self.assertEqual(p.isolated(['/nonexistent/gles-test'])['status'],'HARNESS_FAILURE')
    def test_simulated_reset_cleanup(self):
        def f(q,a): q.allocate(64);raise TimeoutError('SIMULATED reset: no device reset')
        r=p.controlled_job(f);self.assertEqual(r['remaining_bytes'],0)

    def test_process_descendants_cleaned(self):
        import tempfile,time
        for mode in ('success','failure','timeout'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                marker=Path(d)/'escaped';ready=Path(d)/'spawned'
                descendant=f"import time,pathlib;time.sleep(.5);pathlib.Path({str(marker)!r}).write_text('leaked')"
                tail="time.sleep(2)" if mode=='timeout' else f"sys.exit({0 if mode=='success' else 1})"
                source=f"import subprocess,sys,time,pathlib;subprocess.Popen([sys.executable,'-c',{descendant!r}]);pathlib.Path({str(ready)!r}).write_text('spawned');{tail}"
                r=p.isolated([sys.executable,'-c',source],.2 if mode=='timeout' else 1)
                self.assertTrue(ready.exists())
                self.assertEqual(r['status'],{'success':'PASS','failure':'HARNESS_FAILURE','timeout':'TEST_TIMEOUT'}[mode])
                time.sleep(.65);self.assertFalse(marker.exists())
    def test_process_output_quota(self):
        r=p.isolated([sys.executable,'-c','import os;os.write(1,b"x"*1000000)'],log_bytes=4096)
        self.assertLessEqual(len(r['log']),4096)
        self.assertFalse(r['driver_evidence'])
    def test_process_memory_quota(self):
        r=p.isolated([sys.executable,'-c','x=bytearray(1024**3)'],memory_mb=128)
        self.assertEqual(r['status'],'HARNESS_FAILURE')
        self.assertFalse(r['driver_evidence'])
    def test_process_quota_validation(self):
        self.assertRaises(p.Rejected,p.isolated,[sys.executable],memory_mb=0)
        self.assertRaises(p.Rejected,p.isolated,[sys.executable],log_bytes=0)

if __name__=='__main__': unittest.main()
