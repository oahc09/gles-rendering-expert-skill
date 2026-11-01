import copy
import json
import unittest
from check_release_gates import ROOT,check
class V104GateTests(unittest.TestCase):
    def setUp(self):
        self.new=json.loads((ROOT/'docs/v1.0.4-release-gates.json').read_text());self.old=json.loads((ROOT/'docs/release-gates.json').read_text());self.skill=(ROOT/'SKILL.md').read_text()
    def test_prior_preserved(self):self.assertFalse(check(self.new,self.skill,self.old))
    def test_old_block_cannot_be_hidden(self):
        for x in self.new['work_packages'].values():x['status']='PASS'
        self.assertFalse(check(self.new,self.skill,self.old))
    def test_missing_prior_rejected(self):
        with self.assertRaises(AssertionError):check(self.new,self.skill)
    def test_no_inferred_risk_waiver(self):
        self.new['accepted_limitations']=['user merged old PR']
        with self.assertRaises(AssertionError):check(self.new,self.skill,self.old)
    def test_inconsistent_prior_flag_rejected(self):
        self.old['release_ready']=True
        for x in self.new['work_packages'].values():x['status']='PASS'
        with self.assertRaises(AssertionError):check(self.new,self.skill,self.old)
    def test_missing_prior_package_rejected(self):
        del self.old['work_packages']['W3']
        with self.assertRaises(AssertionError):check(self.new,self.skill,self.old)
    def test_wrong_prior_target_rejected(self):
        self.old['target_version']='1.0.2'
        with self.assertRaises(AssertionError):check(self.new,self.skill,self.old)
    def test_future_prior_release_preserves_its_metadata_until_new_ready(self):
        for x in self.old['work_packages'].values():x['status']='PASS'
        self.old.update(release_ready=True,metadata_version='1.0.3')
        self.new['metadata_version']='1.0.3'
        self.assertFalse(check(self.new,self.skill.replace('version: 1.0.2','version: 1.0.3'),self.old))
    def test_no_premature_v104_metadata(self):
        with self.assertRaises(AssertionError):check(self.new,self.skill.replace('version: 1.0.2','version: 1.0.4'),self.old)
if __name__=='__main__':unittest.main()
