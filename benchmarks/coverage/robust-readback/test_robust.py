import hashlib,importlib.util,json,unittest
from pathlib import Path
HERE=Path(__file__).parent
s=importlib.util.spec_from_file_location('robust_test_run',HERE/'run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_no_capability(self):self.assertEqual(m.routes((3,1),[]),[])
 def test_no_core_guess(self):self.assertEqual(m.routes((3,1),['GL_KHR_robustness']),[('KHR','KHR')])
 def test_core_and_extension_separate(self):self.assertEqual(len(m.routes((3,2),['GL_KHR_robustness'])),2)
 def test_strided_offsets(self):
  g=m.golden(True);self.assertEqual(g[:28],[165]*28);self.assertEqual(g[28:32],[255,0,0,255]);self.assertEqual(g[44:52],[165]*8);self.assertEqual(g[112:116],[255,255,0,255]);self.assertEqual(g[116:],[165]*12)
 def test_tight_pixels(self):self.assertEqual(m.golden()[:16],[255,0,0,255,0,255,0,255,0,0,255,255,255,255,0,255])
 def test_canary_corruption_rejected(self):
  import ctypes as C
  class H:
   def error(self):return 0
  def bad(ptr):C.cast(ptr,C.POINTER(C.c_ubyte))[-1]=0
  self.assertEqual(m.probe(bad,[],h=H())['status'],'FAIL')
 def test_unexpected_error_rejected(self):
  class H:
   def error(self):return 1282
  self.assertEqual(m.probe(lambda ptr:None,[],h=H())['status'],'FAIL')
 def test_real_reports_complete(self):
  for name,count in [('mesa',16),('angle',8)]:
   r=json.loads((HERE/(name+'.json')).read_text());self.assertEqual(r['status'],'HOST_PASS');self.assertEqual(r['source_sha256'],hashlib.sha256((HERE/'run.py').read_bytes()).hexdigest());self.assertEqual(r['robust_calls'],count)
   for route in r['routes']:
    self.assertEqual(len(route['cases']),8)
    for row in route['cases']:
     self.assertEqual(row['payload'],row['expected_payload']);self.assertEqual(row['prefix_canary'],[165]*16);self.assertEqual(row['suffix_canary'],[165]*16);self.assertEqual(row['gl_error'],row['expected_error'])
     if row['bufSize']<row['required_bytes']:self.assertEqual(row['gl_error'],1282);self.assertEqual(row['payload'],[165]*128)
 def test_no_reset_or_private_fingerprint(self):
  for name in ['mesa','angle']:
   raw=(HERE/(name+'.json')).read_text();r=json.loads(raw);self.assertEqual(r['reset_injection'],'NOT_RUN');self.assertEqual(r['context_recovery'],'NOT_RUN')
   for key in ('/tmp/','/workspace/','libraries','os_build','renderer','executable_sha256'):self.assertNotIn(key,raw)
if __name__=='__main__':unittest.main()
