import copy
import json
import unittest
from check_release_gates import ROOT, check

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT/'docs/release-gates.json').read_text())
        self.skill = (ROOT/'SKILL.md').read_text()
    def test_candidate_not_ready(self):
        self.assertFalse(check(self.data, self.skill))
    def test_premature_bump_rejected(self):
        with self.assertRaises(AssertionError):
            check(self.data, self.skill.replace('version: 1.0.2','version: 1.0.3'))
    def test_lie_release_flag_rejected(self):
        self.data['release_ready'] = True
        with self.assertRaises(AssertionError): check(self.data, self.skill)
    def test_missing_work_package_rejected(self):
        del self.data['work_packages']['W3']
        with self.assertRaises(AssertionError): check(self.data, self.skill)
    def test_all_pass_wrong_version_rejected(self):
        for item in self.data['work_packages'].values(): item['status'] = 'PASS'
        self.data['release_ready'] = True
        with self.assertRaises(AssertionError): check(self.data, self.skill)
    def test_consistent_full_acceptance(self):
        # Synthetic bookkeeping control, never evidence that real gates passed.
        for item in self.data['work_packages'].values(): item['status'] = 'PASS'
        self.data.update(release_ready=True, metadata_version='1.0.3')
        self.assertTrue(check(self.data, self.skill.replace('version: 1.0.2','version: 1.0.3')))

if __name__ == '__main__': unittest.main()
