import hashlib,importlib.util,itertools,json,unittest
from pathlib import Path
HERE=Path(__file__).parent
s=importlib.util.spec_from_file_location('oit_run',HERE/'run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_cpu_permutation(self):
  for scene in m.SCENES:self.assertEqual(len({tuple(m.oracle(scene['layers'],o)) for o in itertools.permutations(range(3))}),1)
 def test_negative_oracles(self):
  for scene in m.SCENES:
   normal=m.oracle(scene['layers'],(0,1,2))
   for n in ['wrong_revealage','missing_layer']:self.assertNotEqual(m.oracle(scene['layers'],(0,1,2),n),normal)
 def test_not_exact_transparency(self):
  for scene in m.SCENES:self.assertNotEqual(m.oracle(scene['layers'],(0,1,2)),m.sorted_oracle(scene['layers']))
 def test_missing_pixels_unknown(self):self.assertIsNone(m.error([0]*63,[0]*4))
 def test_actual_evidence(self):
  for name in ('mesa','angle'):
   r=json.loads((HERE/(name+'.json')).read_text());self.assertEqual(r['status'],'HOST_CONTRACT_PASS');self.assertEqual(r['actual_execution_counts'],{'draws':119,'readbacks':19});self.assertLessEqual(r['blend_probe']['max_error'],1)
   for scene in r['scenes']:
    self.assertEqual(len(scene['rows']),8);self.assertEqual(scene['selection'],'SORTED_ALPHA');self.assertEqual(scene['quality_status'],'REJECTED_APPROXIMATION');self.assertEqual(scene['sorted_baseline']['max_error'],0)
    for row in scene['rows']:
     self.assertTrue(row['algorithm_pass']);self.assertEqual(row['algorithm_error'],0)
     if row['negative']:self.assertTrue(row['negative_rejected'])
 def test_cost_not_gain(self):
  for name in ('mesa','angle'):
   r=json.loads((HERE/(name+'.json')).read_text());self.assertEqual(r['cost_model']['per_3_layer_oit_variant']['geometry_draws'],6);self.assertEqual(r['cost_model']['oit_render_target_bytes_per_pixel'],20);self.assertFalse(r['cost_model']['bandwidth_counter_measured']);self.assertEqual(r['performance'],'NOT_MEASURED')
 def test_source_and_sanitization(self):
  for name in ('mesa','angle'):
   raw=(HERE/(name+'.json')).read_text();r=json.loads(raw);self.assertEqual(r['source_sha256'],hashlib.sha256((HERE/'run.py').read_bytes()).hexdigest())
   for token in ('/tmp/','/workspace/','renderer','libraries','os_build'):self.assertNotIn(token,raw)
if __name__=='__main__':unittest.main()
