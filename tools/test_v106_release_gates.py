import copy,json,unittest
from pathlib import Path
from check_release_gates import check
ROOT=Path(__file__).resolve().parents[1]
class Gates106(unittest.TestCase):
 def setUp(self):
  self.data=json.loads((ROOT/'docs/v1.0.6/release-gates.json').read_text());self.prev=json.loads((ROOT/'docs/v1.0.5/release-gates.json').read_text());self.ancestor=json.loads((ROOT/'docs/v1.0.4-release-gates.json').read_text());self.old=json.loads((ROOT/'docs/release-gates.json').read_text());self.skill=(ROOT/'SKILL.md').read_text()
 def run_check(self):return check(self.data,self.skill,self.prev,self.ancestor,self.old)
 def test_real_candidate_blocked(self):self.assertFalse(self.run_check())
 def test_no_oldest(self):
  with self.assertRaises(AssertionError):check(self.data,self.skill,self.prev,self.ancestor)
 def test_missing_package(self):
  del self.data['work_packages']['W10']
  with self.assertRaises(AssertionError):self.run_check()
 def test_false_prior_flag(self):
  self.prev['release_ready']=True
  with self.assertRaises(AssertionError):self.run_check()
 def test_false_ancestor_flag(self):
  self.ancestor['release_ready']=True
  with self.assertRaises(AssertionError):self.run_check()
 def test_false_origin_flag(self):
  self.old['release_ready']=True
  with self.assertRaises(AssertionError):self.run_check()
 def test_all_current_pass_not_enough(self):
  for p in self.data['work_packages'].values():p['status']='PASS'
  self.assertFalse(self.run_check())
 def test_no_version_bump(self):
  self.skill='version: 1.0.6'
  with self.assertRaises(AssertionError):self.run_check()
 def test_no_truthy_authorization(self):
  self.data['release_authorized']='yes'
  with self.assertRaises(AssertionError):self.run_check()
 def test_no_risk_waiver(self):
  self.data['accepted_limitations']=['hardware']
  with self.assertRaises(AssertionError):self.run_check()
 def test_exact_predecessor_reference(self):
  self.data['prior_release_gate']='docs/release-gates.json'
  with self.assertRaises(AssertionError):self.run_check()
if __name__=='__main__':unittest.main()
