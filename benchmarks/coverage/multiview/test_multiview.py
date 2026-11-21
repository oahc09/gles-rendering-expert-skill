import pathlib,sys,json,hashlib,copy,unittest
ROOT=pathlib.Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools/coverage'));import multiview as m
class MultiviewTests(unittest.TestCase):
 def report(self):return json.loads((pathlib.Path(__file__).parent/'evidence/mesa.json').read_text())
 def test_gate_requires_dependencies(self):
  self.assertFalse(m.gate(['GL_OVR_multiview2'],True,2));self.assertFalse(m.gate(['GL_OVR_multiview','GL_OVR_multiview2'],False,2));self.assertFalse(m.gate(['GL_OVR_multiview','GL_OVR_multiview2'],True,1))
 def test_actual_archives(self):
  for n in ['mesa','angle']:
   r=json.loads((pathlib.Path(__file__).parent/'evidence'/f'{n}.json').read_text());self.assertTrue(m.validate_report(r));self.assertEqual(r['source_sha256'],hashlib.sha256(pathlib.Path(m.__file__).read_bytes()).hexdigest());self.assertEqual(r['host_source_sha256'],hashlib.sha256((ROOT/'benchmarks/differential/run.py').read_bytes()).hexdigest())
 def test_wrong_layer_rejected(self):
  r=self.report();r['rows'][1]['rgba8'][1]=r['rows'][1]['rgba8'][0];self.assertFalse(m.validate_report(r))
 def test_noop_sentinel_rejected(self):
  r=self.report();r['rows'][1]['rgba8']=[[0,0,255,255]*16]*2;self.assertFalse(m.validate_report(r))
 def test_error_missing_rejected(self):
  r=self.report();r['rows'][2]['observed_error']=0;self.assertFalse(m.validate_report(r))
 def test_incomplete_rejected(self):
  r=self.report();r['rows'].pop();self.assertFalse(m.validate_report(r))
 def test_unsupported_not_pass(self):
  r=self.report();r['status']='NOT_SUPPORTED';self.assertFalse(m.validate_report(r))
if __name__=='__main__':unittest.main()
