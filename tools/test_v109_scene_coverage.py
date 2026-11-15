import copy,json,unittest
from pathlib import Path
from check_v109_scene_coverage import ROOT,check
class CoverageTests(unittest.TestCase):
 def setUp(self): self.data=json.loads((ROOT/'docs/v1.0.9/scene-coverage.json').read_text())
 def test_current(self): self.assertEqual(check(self.data)['acceptance'],'INCOMPLETE')
 def test_no_missing_scene(self):
  self.data['scenes'].pop()
  with self.assertRaises(ValueError): check(self.data)
 def test_no_duplicate(self):
  self.data['scenes'][0]['id']='S02'
  with self.assertRaises(ValueError): check(self.data)
 def test_no_promoted_software_performance(self):
  self.data['scenes'][0]['performance']['status']='PARTIAL'
  with self.assertRaises(ValueError): check(self.data)
 def test_no_pass_without_acceptance(self):
  self.data['scenes'][0]['quality']['status']='PASS'
  with self.assertRaises(ValueError): check(self.data)
 def test_no_external_reference(self):
  self.data['scenes'][0]['implementation']=['../not-allowed']
  with self.assertRaises(ValueError): check(self.data)
 def test_no_implicit_scope(self):
  self.data['scenes'][0]['remaining']=''
  with self.assertRaises(ValueError): check(self.data)
