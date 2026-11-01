import json
from pathlib import Path
import tempfile
import unittest
from compare import compare,temporal,write_ppm,read_ppm,local_ssim
class VisualComparatorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.config=json.loads((Path(__file__).parent/'thresholds.json').read_text());self.a=self.root/'a.ppm';self.b=self.root/'b.ppm';write_ppm(self.a,32,32,[80,120,160]*1024)
 def tearDown(self):self.tmp.cleanup()
 def test_identical(self):self.assertTrue(compare(self.a,self.a,self.config,'P06')['pass'])
 def test_global_tint_rejected(self):
  write_ppm(self.b,32,32,[90,120,160]*1024);self.assertFalse(compare(self.a,self.b,self.config,'P06')['pass'])
 def test_local_corruption_rejected_despite_small_global_mae(self):
  values=[80,120,160]*1024;values[0]=255;write_ppm(self.b,32,32,values);r=compare(self.a,self.b,self.config,'P06');self.assertFalse(r['pass']);self.assertLess(r['scales']['1']['mae'],1)
 def test_missing_region_explicit(self):self.assertEqual(compare(self.a,self.a,self.config,'P01')['regions']['transparent']['status'],'NOT_APPLICABLE')
 def test_temporal_static_pass(self):self.assertTrue(temporal([self.a]*3,[self.a]*3)['pass'])
 def test_flicker_fail(self):
  write_ppm(self.b,32,32,[20,40,60]*1024);self.assertFalse(temporal([self.a]*3,[self.a,self.b,self.a])['pass'])
 def test_temporal_mismatch_rejected(self):
  with self.assertRaises(ValueError):temporal([self.a],[self.a])
 def test_heatmap_real(self):
  heat=self.root/'heat.ppm';compare(self.a,self.a,self.config,'P01',heat);self.assertEqual(read_ppm(heat)[2][:3],bytes([0,0,255]))
 def test_truncated_capture_rejected(self):
  self.b.write_bytes(b'P6\n32 32\n255\n123');
  with self.assertRaises(ValueError):compare(self.a,self.b,self.config,'P01')
 def test_ssim_identical_is_one(self):self.assertAlmostEqual(local_ssim(32,32,[100]*3072,[100]*3072),1)
if __name__=='__main__':unittest.main()
