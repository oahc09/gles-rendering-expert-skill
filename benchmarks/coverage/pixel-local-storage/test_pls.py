import hashlib,importlib.util,json,unittest
from pathlib import Path
HERE=Path(__file__).parent
s=importlib.util.spec_from_file_location('pls_run',HERE/'run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_oracle(self):self.assertEqual(m.expected(2),[96,96,32,128]*16);self.assertEqual(m.expected(3),[112,112,48,144]*16)
 def test_negative_not_short_or_changed(self):
  self.assertFalse(m.quality(m.expected(2)[:-1],m.expected(2)));self.assertFalse(m.quality([0]*64,m.expected(2)))
 def test_actual_angle(self):
  r=json.loads((HERE/'angle.json').read_text());self.assertEqual(r['status'],'HOST_PASS');self.assertTrue(r['advertised']);self.assertEqual(r['pls']['explicit_barriers'],1);self.assertEqual(r['pls']['draws'],4)
  for row in r['pls']['readbacks']:self.assertEqual(row['pixels'],row['golden'])
  self.assertEqual(r['negative_nested_begin']['gl_error'],1282);self.assertEqual(r['negative_inactive_end']['gl_error'],1282)
  neg=r['pls']['negative_wrong_zero_load'];self.assertEqual(neg['pixels'],neg['expected_actual']);self.assertTrue(neg['rejected_against_load_oracle'])
 def test_actual_mesa_no_extension_acceptance(self):
  r=json.loads((HERE/'mesa.json').read_text());self.assertEqual(r['status'],'FALLBACK_PASS');self.assertFalse(r['advertised']);self.assertEqual(r['pls'],'UNSUPPORTED');self.assertEqual(r['events'],[])
 def test_actual_fallback_both(self):
  for name in ('mesa','angle'):
   r=json.loads((HERE/(name+'.json')).read_text());self.assertEqual(r['fallback']['status'],'PASS');self.assertEqual(r['fallback']['draws'],3);self.assertFalse(r['fallback']['feedback_loop'])
   for row in r['fallback']['readbacks']:self.assertEqual(row['pixels'],row['golden'])
 def test_hash_and_scope(self):
  for name in ('mesa','angle'):
   raw=(HERE/(name+'.json')).read_text();r=json.loads(raw);self.assertEqual(r['source_sha256'],hashlib.sha256((HERE/'run.py').read_bytes()).hexdigest());self.assertEqual(r['performance'],'NOT_MEASURED');self.assertEqual(r['physical_device'],'NOT_RUN')
   for token in ('/tmp/','/workspace/','renderer','libraries','os_build'):self.assertNotIn(token,raw)
if __name__=='__main__':unittest.main()
