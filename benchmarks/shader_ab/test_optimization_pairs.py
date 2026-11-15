import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('optimization_pairs',Path(__file__).with_name('optimization_pairs.py'));p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
class Pairs(unittest.TestCase):
 def test_four_patterns(self):
  for name in ('ramp','checker','edges','alpha'):self.assertEqual(len(p.texture_pixels(name)),256)
 def test_unknown_pattern(self):
  with self.assertRaises(ValueError):p.texture_pixels('bad')
 def test_alpha_distribution(self):self.assertGreater(len(set(p.texture_pixels('alpha')[3::4])),2)
 def test_repeat_sampling(self):self.assertEqual(p.fragment('sampling','baseline').count('texture(tex,uv)'),2)
 def test_merged_sampling(self):self.assertEqual(p.fragment('sampling','optimized').count('texture(tex,uv)'),1)
 def test_fusion_no_ssbo(self):self.assertNotIn('buffer Pixels',p.fragment('fusion','optimized'))
 def test_baseline_ssbo(self):self.assertIn('readonly buffer Pixels',p.fragment('fusion','baseline'))
 def test_compute_storage(self):self.assertIn('pixels[p.y*8+p.x]',p.COMPUTE)
 def test_four_frames(self):self.assertEqual(len({tuple(p.pure_golden(i)) for i in range(4)}),4)
 def test_golden_ranges(self):self.assertTrue(all(0<=x<=255 for f in range(4) for x in p.pure_golden(f)))
 def test_golden_alpha(self):self.assertEqual(set(p.pure_golden(0)[3::4]),{255})
 def test_compare_identity(self):self.assertEqual(p.compare(p.pure_golden(0),p.pure_golden(0))['status'],'PASS')
 def test_compare_negative(self):self.assertEqual(p.compare([0]*256,p.pure_golden(0))['status'],'FAIL')
 def test_invalid_nan(self):self.assertEqual(p.compare([float('nan')]*256,p.pure_golden(0))['status'],'INVALID')
 def test_invalid_size(self):self.assertEqual(p.compare([],[])['status'],'INVALID')
 def test_no_global_effects(self):self.assertNotIn('atomic',p.COMPUTE)
if __name__=='__main__':unittest.main()
