import json,unittest
from pathlib import Path
import far_reconstruction as f
class FarReconstructionTests(unittest.TestCase):
 def test_logical_work(self):
  a,b=f.logical_work(64),f.logical_work(32);self.assertEqual(a['combined_attachment_bytes'],32768);self.assertEqual(b['combined_attachment_bytes'],20480);self.assertEqual(a['draw_calls'],b['draw_calls']);self.assertEqual(b['draw_calls'],8);self.assertEqual(b['copy_output_pixels'],4096)
 def test_saved_thresholds_unchanged(self):
  for driver in ('mesa','angle'):
   r=json.loads((Path(__file__).parent/'evidence'/('far-reconstruction-'+driver+'.json')).read_text());self.assertEqual(r['thresholds'],dict(max_rgba8_error=4,silhouette_disagree_pixels=2,centroid_error_pixels=.1,parallax_error_pixels=.1))
 def test_bilinear_fetch_budget(self):
  b=f.logical_work(32);self.assertEqual(b['copy_texel_fetch_upper_bound'],16384);self.assertEqual(b['copy_logical_read_write_upper_bytes'],81920)
 def test_bilinear_differs_from_nearest(self):
  import far_resolution as nearest
  far,near=f.scene();self.assertNotEqual(f.cpu(far,near,0,32),nearest.cpu(far,near,0,32))
 def stored(self):return json.loads((Path(__file__).parent/'evidence/far-reconstruction-angle.json').read_text())
 def test_candidate_parallax_failure_fallback(self):
  r=self.stored();r['parallax'][1]['status']='FAIL';self.assertEqual(f.camera_selection(r['rows'],r['parallax']),'baseline');self.assertTrue(f.contract_valid(r['rows'],r['parallax'],'baseline'));self.assertFalse(f.contract_valid(r['rows'],r['parallax'],'far_bilinear'))
 def test_baseline_parallax_failure_unavailable(self):
  r=self.stored();r['parallax'][0]['status']='FAIL';self.assertIsNone(f.camera_selection(r['rows'],r['parallax']));self.assertTrue(f.contract_valid(r['rows'],r['parallax'],None));self.assertFalse(f.contract_valid(r['rows'],r['parallax'],'baseline'))
 def test_missing_parallax_rejected(self):
  r=self.stored();self.assertFalse(f.contract_valid(r['rows'],r['parallax'][:1],None))
 def test_duplicate_parallax_rejected(self):
  r=self.stored();self.assertFalse(f.contract_valid(r['rows'],[r['parallax'][0]]*2,None))
 def test_unknown_variant_rejected(self):
  r=self.stored();r['rows'][0]['variant']='unknown';self.assertIsNone(f.select(r['rows']));self.assertFalse(f.contract_valid(r['rows'],r['parallax'],None))
 def test_depth_separation(self):
  far,near=f.scene();self.assertGreater(min(o['z'] for o in far),max(o['z'] for o in near))
 def test_cpu_full_matches_existing(self):
  far,near=f.scene();self.assertEqual(f.cpu(far,near,0,64),f.p.cpu(far+near,0)[0])
 def test_low_changes_reference(self):
  far,near=f.scene();self.assertNotEqual(f.cpu(far,near,0,32),f.cpu(far,near,0,64))
 def test_near_full_resolution_preserved(self):
  _,near=f.scene();self.assertEqual(f.cpu([],near,0,32),f.cpu_layers(near,0,64))
 def test_empty_selection(self):self.assertIsNone(f.select([]))
 def test_empty_contract(self):self.assertFalse(f.contract_valid([],[],None))
 def test_saved_report_contract(self):
  for driver in ('mesa','angle'):
   p=Path(__file__).parent/'evidence'/('far-reconstruction-'+driver+'.json')
   report=json.loads(p.read_text());self.assertEqual(len(report['rows']),9);self.assertTrue(f.contract_valid(report['rows'],report['parallax'],report['global_policy']['selected']))
 def test_baseline_failure_rejects_selection(self):
  p=Path(__file__).parent/'evidence/far-reconstruction-angle.json';r=json.loads(p.read_text());r['rows'][0]['quality']='FAIL';self.assertIsNone(f.select(r['rows']));self.assertFalse(f.contract_valid(r['rows'],r['parallax'],'baseline'))
 def test_duplicate_rows_rejected(self):
  p=Path(__file__).parent/'evidence/far-reconstruction-angle.json';r=json.loads(p.read_text());rows=[r['rows'][0]]*9;self.assertIsNone(f.select(rows));self.assertFalse(f.contract_valid(rows,r['parallax'],None))
 def test_invalid_layers_rejected_before_gl(self):
  host=object.__new__(f.FarHost)
  with self.assertRaises(ValueError):host.draw([{'z':1}],[{'z':2}],0,32)
if __name__=='__main__':unittest.main()
