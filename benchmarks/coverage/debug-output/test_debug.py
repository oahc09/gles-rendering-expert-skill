import hashlib,importlib.util,json,unittest
from pathlib import Path
HERE=Path(__file__).parent
s=importlib.util.spec_from_file_location('debug_tests',HERE/'run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_no_alias_guess(self):
  self.assertIsNone(m.route((3,1),[]));self.assertEqual(m.route((3,1),['GL_KHR_debug']),'KHR');self.assertEqual(m.route((3,2),[]),'core')
 def test_disabled(self):self.assertIsNone(m.route((3,2),['GL_KHR_debug'],True))
 def test_actual_routes(self):
  for name,route in [('mesa','core'),('angle','KHR')]:
   r=json.loads((HERE/(name+'.json')).read_text());self.assertEqual(r['status'],'HOST_PASS');self.assertEqual(r['route'],route)
   self.assertTrue(all(n.endswith('KHR') for n in r['entrypoints']) if route=='KHR' else all(not n.endswith('KHR') for n in r['entrypoints']))
 def test_exact_callback_order_filters(self):
  for name in ('mesa','angle'):
   r=json.loads((HERE/(name+'.json')).read_text());self.assertEqual([x['id'] for x in r['application_messages']],[901,904,905,905,907]);self.assertTrue(r['synchronous_return_observed']);self.assertEqual(r['group_depth'],[1,2,1]);self.assertTrue(all(x['user_matches'] for x in r['application_messages']))
   self.assertEqual([x['severity'] for x in r['application_messages']],[m.LOW,m.LOW,m.NOTE,m.NOTE,m.LOW])
 def test_labels_and_unregister(self):
  for name in ('mesa','angle'):
   r=json.loads((HERE/(name+'.json')).read_text());self.assertEqual(r['label']['full'],'finite-owned-buffer');self.assertEqual(r['label']['length'],19);self.assertEqual(r['label']['truncated'],'finit');self.assertEqual(r['label']['truncated_length'],5);self.assertTrue(r['label']['null_terminated']);self.assertTrue(r['callback_registration_matches']);self.assertTrue(all(r['callback_unregister'].values()))
 def test_defined_negatives(self):
  for name in ('mesa','angle'):
   rows=json.loads((HERE/(name+'.json')).read_text())['negative_cases'];self.assertEqual(len(rows),5)
   for r in rows:self.assertEqual(r['gl_error'],r['expected_error']);self.assertNotEqual(r['gl_error'],0)
 def test_actual_safe_fallback(self):
  for name in ('mesa','angle'):
   r=json.loads((HERE/(name+'-disabled.json')).read_text());self.assertEqual(r['status'],'SAFE_FALLBACK_PASS');self.assertTrue(r['force_disabled']);self.assertEqual(r['fallback']['debug_functions_called'],0);self.assertEqual(r['fallback']['pixels'],[255,0,0,255]*16)
 def test_hash_and_only_experiment_text(self):
  for name in ('mesa','angle','mesa-disabled','angle-disabled'):
   raw=(HERE/(name+'.json')).read_text();r=json.loads(raw);self.assertEqual(r['source_sha256'],hashlib.sha256((HERE/'run.py').read_bytes()).hexdigest());self.assertFalse(r['driver_messages_recorded'])
   for x in r.get('application_messages',[]):self.assertEqual(x['message'].encode(),m.MESSAGES[x['id']]);self.assertEqual(x['source'],m.APP)
   for token in ('/tmp/','/workspace/','renderer','libraries','os_build','pointer_address'):self.assertNotIn(token,raw)
if __name__=='__main__':unittest.main()
