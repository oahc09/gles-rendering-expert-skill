import json
from pathlib import Path
import unittest
from check_release_gates import check

ROOT = Path(__file__).resolve().parents[1]

class Gates107(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT/'docs/v1.0.7-release-gates.json').read_text())
        self.prior = [json.loads((ROOT/p).read_text()) for p in (
            'docs/v1.0.6/release-gates.json', 'docs/v1.0.5/release-gates.json',
            'docs/v1.0.4-release-gates.json', 'docs/release-gates.json')]
        self.skill = (ROOT/'SKILL.md').read_text()
    def validate(self): return check(self.data, self.skill, *self.prior)
    def test_current_candidate_stays_blocked(self): self.assertFalse(self.validate())
    def test_all_current_pass_cannot_override_ancestors(self):
        for item in self.data['work_packages'].values(): item['status']='PASS'
        self.data['release_authorized']=True
        self.assertFalse(self.validate())
    def test_missing_origin_rejected(self):
        with self.assertRaises(AssertionError): check(self.data,self.skill,*self.prior[:-1])
    def test_each_prior_flag_is_checked(self):
        for p in self.prior:
            p['release_ready']=True
            with self.assertRaises(AssertionError): self.validate()
            p['release_ready']=False
    def test_no_bump_without_gates(self):
        self.skill='version: 1.0.7'
        with self.assertRaises(AssertionError): self.validate()
    def test_exact_package_inventory(self):
        del self.data['work_packages']['W9']
        with self.assertRaises(AssertionError): self.validate()
    def test_no_implicit_waiver(self):
        self.data['accepted_limitations']=['hardware']
        with self.assertRaises(AssertionError): self.validate()
    def test_boolean_authorization(self):
        self.data['release_authorized']='yes'
        with self.assertRaises(AssertionError): self.validate()
    def test_exact_predecessor(self):
        self.data['prior_release_gate']='docs/release-gates.json'
        with self.assertRaises(AssertionError): self.validate()

if __name__ == '__main__': unittest.main()
