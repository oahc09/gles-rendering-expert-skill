import importlib.util,json,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('progressive',HERE/'progressive.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Progressive(unittest.TestCase):
 def test_budget_and_capacity(self):
  for capacity,budget in [(63,64),(84,63)]:
   r=m.Refinement(capacity,budget)
   with self.assertRaises(ValueError):r.propose(0)
   self.assertEqual(r.loaded,set())
 def test_fixed_quality_boundary_and_preserve(self):
  r=m.Refinement();gold=[100]*64
  self.assertTrue(r.observe(0,[132]*64,gold)['selected'])
  self.assertFalse(r.observe(2,[133]*64,gold)['selected']);self.assertEqual(r.active,0)
 def test_invalid_observation_not_loaded(self):
  for pixels in [[0]*63,[float('nan')]*64,[True]*64,[256]*64]:
   r=m.Refinement()
   with self.assertRaises(ValueError):r.observe(0,pixels,[0]*64)
   self.assertEqual(r.loaded,set())
 def test_upload_reuse(self):
  r=m.Refinement();r.observe(1,[0]*64,[0]*64);self.assertEqual(r.propose(1),0)
 def test_saved_real_mip_sequences(self):
  for driver in ['mesa','angle']:
   d=json.loads((HERE/'evidence'/f'progressive-{driver}.json').read_text());self.assertEqual(d['status'],'HOST_PASS');self.assertEqual([x['max_error'] for x in d['frames']],[90,30,0,30,0]);self.assertEqual([x['upload_bytes'] for x in d['frames']],[4,16,64,0,0]);self.assertEqual(d['rejected_candidate']['optimization_status'],'REJECTED_BY_QUALITY');self.assertTrue(d['restored_exact'])
if __name__=='__main__':unittest.main()
