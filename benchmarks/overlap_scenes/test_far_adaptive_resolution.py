import json,unittest
from pathlib import Path
import far_adaptive_resolution as f
class AdaptiveFarTests(unittest.TestCase):
 def report(self,driver):return json.loads((Path(__file__).parent/'evidence'/('far-adaptive-resolution-'+driver+'.json')).read_text())
 def test_seven_cameras(self):self.assertEqual(len(f.CAMERAS),7);self.assertTrue(set((-.3,0,.3)).issubset(f.CAMERAS))
 def test_noninteger_scale(self):self.assertNotEqual(64/48,64//48)
 def test_full_oracle_same(self):
  a,b=f.scene();self.assertEqual(f.cpu(a,b,0,64),f.p.cpu(a+b,0)[0])
 def test_holdout_cpu_failure_preserved(self):
  a,b=f.scene();m=f.p.metrics(f.cpu(a,b,-.15,48),f.cpu(a,b,-.15,64));self.assertGreater(m['silhouette_disagree_pixels'],2)
 def test_logical_cost(self):
  r=f.logical_work(48);self.assertEqual(r['far_target_pixels'],2304);self.assertEqual(r['combined_attachment_bytes'],25600);self.assertEqual(r['draw_calls'],8)
 def test_saved_contract(self):
  for driver in ('mesa','angle'):
   r=self.report(driver);self.assertEqual(len(r['rows']),21);self.assertTrue(f.contract_valid(r['rows'],r['parallax'],r['global_policy']['selected']));self.assertEqual(r['status'],'FAIL');self.assertEqual(r['global_policy']['selected'],'baseline')
 def test_missing_holdout_rejected(self):
  r=self.report('angle');rows=[x for x in r['rows'] if x['camera']!=-.15];self.assertIsNone(f.select(rows));self.assertFalse(f.contract_valid(rows,r['parallax'],None))
 def test_duplicate_cameras_rejected(self):
  r=self.report('angle');rows=[r['rows'][0]]*21;self.assertIsNone(f.select(rows));self.assertFalse(f.contract_valid(rows,r['parallax'],None))
 def test_baseline_failure_unavailable(self):
  r=self.report('angle');r['rows'][0]['quality']='FAIL';self.assertIsNone(f.camera_selection(r['rows'],r['parallax']))
 def test_fixed_thresholds(self):
  r=self.report('mesa');self.assertEqual(r['thresholds'],dict(max_rgba8_error=4,silhouette_disagree_pixels=2,centroid_error_pixels=.1,parallax_error_pixels=.1))
if __name__=='__main__':unittest.main()
