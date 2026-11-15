import json,unittest
from pathlib import Path
import far_resolution as f
class FarResolutionTests(unittest.TestCase):
 def test_logical_work(self):
  a,b=f.logical_work(64),f.logical_work(32);self.assertEqual(a['combined_attachment_bytes'],32768);self.assertEqual(b['combined_attachment_bytes'],20480);self.assertEqual(a['draw_calls'],b['draw_calls']);self.assertEqual(b['draw_calls'],8);self.assertEqual(b['copy_output_pixels'],4096)
 def test_saved_thresholds_unchanged(self):
  for driver in ('mesa','angle'):
   r=json.loads((Path(__file__).parent/'evidence'/('far-resolution-'+driver+'.json')).read_text());self.assertEqual(r['thresholds'],dict(max_rgba8_error=4,silhouette_disagree_pixels=2,centroid_error_pixels=.1,parallax_error_pixels=.1))
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
   p=Path(__file__).parent/'evidence'/('far-resolution-'+driver+'.json')
   report=json.loads(p.read_text());self.assertEqual(len(report['rows']),9);self.assertTrue(f.contract_valid(report['rows'],report['parallax'],report['global_policy']['selected']))
 def test_baseline_failure_rejects_selection(self):
  p=Path(__file__).parent/'evidence/far-resolution-angle.json';r=json.loads(p.read_text());r['rows'][0]['quality']='FAIL';self.assertIsNone(f.select(r['rows']));self.assertFalse(f.contract_valid(r['rows'],r['parallax'],'baseline'))
 def test_duplicate_rows_rejected(self):
  p=Path(__file__).parent/'evidence/far-resolution-angle.json';r=json.loads(p.read_text());rows=[r['rows'][0]]*9;self.assertIsNone(f.select(rows));self.assertFalse(f.contract_valid(rows,r['parallax'],None))
 def test_invalid_layers_rejected_before_gl(self):
  host=object.__new__(f.FarHost)
  with self.assertRaises(ValueError):host.draw([{'z':1}],[{'z':2}],0,32)
if __name__=='__main__':unittest.main()
