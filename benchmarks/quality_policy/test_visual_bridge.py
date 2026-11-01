import copy,json,unittest
from visual_bridge import ROOT,bind_report,gate_scale
class VisualBridge(unittest.TestCase):
 def setUp(self):self.report=json.loads((ROOT/'benchmarks/visual_quality/software-validation.json').read_text());self.decision={'level':2,'recommendation':{'render_scale':.7}}
 def test_measured_water_rejected(self):
  r=gate_scale(self.decision,'P03',self.report);self.assertFalse(r['scale_only_visual_pass']);self.assertEqual(r['safe_scale_recommendation'],1)
 def test_other_scale_does_not_approve_full_preset(self):
  r=gate_scale(self.decision,'P01',self.report);self.assertTrue(r['scale_only_visual_pass']);self.assertFalse(r['full_preset_may_apply'])
 def test_unknown_scene_rejected(self):
  with self.assertRaises(ValueError):gate_scale(self.decision,'P99',self.report)
 def test_changed_source_evidence_rejected(self):
  self.report['source_sha256']='0'*64
  with self.assertRaises(ValueError):bind_report(self.report)
 def test_failed_suite_rejected(self):
  self.report['status']='FAIL'
  with self.assertRaises(ValueError):bind_report(self.report)
if __name__=='__main__':unittest.main()
