import unittest,importlib.util,json,hashlib
from pathlib import Path
P=Path(__file__).parent
s=importlib.util.spec_from_file_location('finite_timer',P/'run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def reports(self):return [json.loads((P/(x+'.json')).read_text()) for x in ('mesa','angle')]
 def test_actual_semantics(self):
  for r in self.reports():
   self.assertEqual(r['status'],'HOST_PASS')
   for k in ('generated_not_yet_objects','active_query_matches','objects_live','deleted_not_objects','workload_pixel_match'):self.assertTrue(r[k])
 def test_actual_negative_errors(self):
  for r in self.reports():
   self.assertEqual(len(r['negatives']),6)
   for n in r['negatives']:self.assertEqual(n['error'],n['expected'])
 def test_query_results(self):
  for r in self.reports():
   self.assertEqual(len(r['availability']),3);self.assertTrue(all(x['available_after_result'] for x in r['availability']));self.assertTrue(all(x['available_at_result_read'] for x in r['availability']));self.assertTrue(r['elapsed_is_uint64_and_non_saturated']);self.assertTrue(r['timestamp_nondecreasing']);self.assertFalse(r['disjoint_after']);self.assertFalse(r['disjoint_before'])
 def test_disjoint_unknown_rejected(self):
  for b,a in [(True,False),(False,True),(None,False),(False,None),(0,False)]:self.assertFalse(m.valid_timing(b,a,64,True))
 def test_capability_validity(self):
  self.assertTrue(m.valid_timing(False,False,64,True))
  for bits in [0,29,30,32,63,65,None,True]:self.assertFalse(m.valid_timing(False,False,bits,True))
  self.assertFalse(m.valid_timing(False,False,64,False))
 def test_disabled_actual_fallback(self):
  for name in ['mesa','angle']:
   r=json.loads((P/(name+'-disabled.json')).read_text());self.assertEqual(r['status'],'SAFE_FALLBACK_PASS');self.assertEqual(r['timer_entrypoint_calls'],0);self.assertTrue(r['fallback']['pixel_match'])
 def test_safe_archive_binding(self):
  for name in ['mesa','angle','mesa-disabled','angle-disabled']:
   text=(P/(name+'.json')).read_text();r=json.loads(text);self.assertEqual(r['source_sha256'],hashlib.sha256((P/'run.py').read_bytes()).hexdigest());self.assertNotIn('/tmp/',text);self.assertNotIn('renderer',text);self.assertFalse(r['raw_timestamps_recorded'])
 def test_exact_ext_entries(self):
  for r in self.reports():self.assertEqual(set(r['entrypoints']),set(m.SIG));self.assertTrue(all(x.endswith('EXT') for x in r['entrypoints']))
if __name__=='__main__':unittest.main()
