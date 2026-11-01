import copy,json,unittest
from check_release_gates import ROOT,check
class V105Gates(unittest.TestCase):
 def setUp(self):
  self.data=json.loads((ROOT/'docs/v1.0.5/release-gates.json').read_text());self.previous=json.loads((ROOT/'docs/v1.0.4-release-gates.json').read_text());self.ancestor=json.loads((ROOT/'docs/release-gates.json').read_text());self.skill=(ROOT/'SKILL.md').read_text()
 def verify(self):return check(self.data,self.skill,self.previous,self.ancestor)
 def all_pass(self):
  for data,version in ((self.ancestor,'1.0.3'),(self.previous,'1.0.4'),(self.data,'1.0.5')):
   for w in data['work_packages'].values():w['status']='PASS'
   data.update(metadata_version=version,release_ready=True)
  self.data['release_authorized']=True;self.skill=self.skill.replace('version: 1.0.2','version: 1.0.5')
 def test_current_blocked(self):self.assertFalse(self.verify())
 def test_missing_ancestor(self):
  with self.assertRaises(AssertionError):check(self.data,self.skill,self.previous)
 def test_missing_w8(self):
  del self.data['work_packages']['W8']
  with self.assertRaises(AssertionError):self.verify()
 def test_previous_false_ready(self):
  self.previous['release_ready']=True
  with self.assertRaises(AssertionError):self.verify()
 def test_ancestor_false_ready(self):
  self.ancestor['release_ready']=True
  with self.assertRaises(AssertionError):self.verify()
 def test_no_bump(self):
  self.skill=self.skill.replace('version: 1.0.2','version: 1.0.5')
  with self.assertRaises(AssertionError):self.verify()
 def test_waiver_not_inferred(self):
  self.data['accepted_limitations']=['missing hardware']
  with self.assertRaises(AssertionError):self.verify()
 def test_authorization_must_boolean(self):
  self.data['release_authorized']='yes'
  with self.assertRaises(AssertionError):self.verify()
 def test_all_pass_only_synthetic_control(self):
  self.all_pass();self.assertTrue(self.verify())
 def test_all_pass_no_authorization_cannot_bump(self):
  self.all_pass();self.data['release_authorized']=False
  with self.assertRaises(AssertionError):self.verify()
 def test_prior_blocker_cannot_skip(self):
  for w in self.data['work_packages'].values():w['status']='PASS'
  self.data['release_authorized']=True;self.assertFalse(self.verify())
 def test_wrong_predecessor(self):
  self.data['prior_release_gate']='docs/release-gates.json'
  with self.assertRaises(AssertionError):self.verify()
if __name__=='__main__':unittest.main()
