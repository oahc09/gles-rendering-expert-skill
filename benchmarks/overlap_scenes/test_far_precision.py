import json,unittest
from pathlib import Path
import far_precision as f
class FarPrecisionTests(unittest.TestCase):
 def report(self,d):return json.loads((Path(__file__).parent/'evidence'/('far-precision-'+d+'.json')).read_text())
 def test_direct_draw_capability_gate(self):
  h=object.__new__(f.FarHost);h.metadata={'extensions':[]};a,b=f.scene()
  with self.assertRaisesRegex(RuntimeError,'capability missing'):h.draw(a,b,0,32)
 def test_bad_baseline_mechanism_rejected(self):
  r=self.report('angle');r['rows'][0]['mechanism_metrics']['max_rgba8_error']=100;self.assertIsNone(f.select(r['rows']))
 def test_half_gate(self):self.assertTrue(f.capability(['GL_EXT_color_buffer_half_float']));self.assertTrue(f.capability(['GL_EXT_color_buffer_float']));self.assertFalse(f.capability(['GL_EXT_float_blend']))
 def test_budget(self):self.assertTrue(f.budget_admitted(32));self.assertFalse(f.budget_admitted(32,max_allocation=20000));self.assertFalse(f.budget_admitted(32,max_logical=1))
 def test_cost(self):
  c=f.logical_work(32);self.assertEqual(c['combined_attachment_bytes'],24576);self.assertEqual(c['copy_logical_read_write_upper_bytes'],147456);self.assertEqual(c['draw_calls'],8)
 def test_original_target_preserved(self):
  a,b=f.scene();self.assertEqual(f.cpu(a,b,0,64),f.p.cpu(a+b,0)[0])
 def test_half_actual_cpu_values(self):
  a,_=f.scene();values=f.cpu_layers(a,0,32,half_precision=True);self.assertTrue(any(v!=int(v) for v in values));self.assertLessEqual(max(values),1)
 def test_seven_saved_views(self):
  for d in ('mesa','angle'):
   r=self.report(d);self.assertEqual(len(r['rows']),21);self.assertTrue(f.contract_valid(r['rows'],r['parallax'],r['global_policy']['selected']));self.assertEqual(r['global_policy']['selected'],'baseline');self.assertEqual(r['status'],'FAIL')
 def test_holdout_not_excluded(self):
  r=self.report('angle');rows=[x for x in r['rows'] if x['camera']!=.45];self.assertIsNone(f.select(rows));self.assertFalse(f.contract_valid(rows,r['parallax'],None))
 def test_baseline_invalid(self):
  r=self.report('angle');r['rows'][0]['quality']='FAIL';self.assertIsNone(f.camera_selection(r['rows'],r['parallax']))
 def test_threshold(self):self.assertEqual(self.report('mesa')['thresholds'],dict(max_rgba8_error=4,silhouette_disagree_pixels=2,centroid_error_pixels=.1,parallax_error_pixels=.1))
 def test_empty_contract(self):self.assertFalse(f.contract_valid([],[],None))
if __name__=='__main__':unittest.main()
