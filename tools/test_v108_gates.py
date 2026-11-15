import unittest,json,copy
from check_v108_gates import ROOT,check
class V108Gates(unittest.TestCase):
 def setUp(self):self.d=json.loads((ROOT/'docs/v1.0.8/release-gates.json').read_text())
 def test_candidate_not_release(self):self.assertFalse(check(self.d))
 def test_false_ready_rejected(self):
  self.d['release_ready']=True
  with self.assertRaises(AssertionError):check(self.d)
 def test_missing_package_rejected(self):
  del self.d['work_packages']['W7']
  with self.assertRaises(AssertionError):check(self.d)
 def test_waiver_rejected(self):
  self.d['accepted_limitations']=['hardware']
  with self.assertRaises(AssertionError):check(self.d)
 def test_predecessor_rejected(self):
  self.d['prior_release_gate']='other'
  with self.assertRaises(AssertionError):check(self.d)
