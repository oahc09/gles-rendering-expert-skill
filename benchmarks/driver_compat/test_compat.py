import copy,json
from pathlib import Path
import unittest
import compat
HERE=Path(__file__).parent
class CompatTests(unittest.TestCase):
    def setUp(self):
        self.record=json.loads((HERE/'software-probe.json').read_text());s=self.record['snapshot']
        self.issue=dict(id='SYNTHETIC-TEST-NOT-A-DRIVER-BUG',vendor=[s['gl_vendor']],renderer=[s['gl_renderer']],driver=[s['gl_version']],os=[s['os_build']],backend=[s['backend']],extensions_all=[],extensions_absent=[],symptom='Artificial fixture only',minimal_reproducer='test_compat.py',source='https://registry.khronos.org/OpenGL/index_es.php',confidence='synthetic',regression_tests=['identity-positive-negative'],expiry='2026-12-01',withdraw_when='Always test-only; never enable',action='disable test feature',evidence={})
    def test_exact_match_only_review(self):
        r=compat.evaluate(self.record,self.issue,'2026-11-01');self.assertEqual(r['status'],'MATCHED_REVIEW_REQUIRED');self.assertFalse(r['apply']);self.assertFalse(r['eligible_after_operator_review'])
    def test_each_identity_mismatch(self):
        for field in ('vendor','renderer','driver','os','backend'):
            i=copy.deepcopy(self.issue);i[field]=['different']
            self.assertEqual(compat.evaluate(self.record,i,'2026-11-01')['status'],'NOT_MATCHED')
    def test_extensions_exact(self):
        self.issue['extensions_all']=['GL_nonexistent']
        self.assertEqual(compat.evaluate(self.record,self.issue,'2026-11-01')['status'],'NOT_MATCHED')
        self.issue['extensions_all']=[];self.issue['extensions_absent']=self.record['snapshot']['gl_extensions'][:1]
        self.assertEqual(compat.evaluate(self.record,self.issue,'2026-11-01')['status'],'NOT_MATCHED')
    def test_expiry(self):self.assertEqual(compat.evaluate(self.record,self.issue,'2026-12-02')['status'],'EXPIRED')
    def test_confirmed_requires_evidence(self):
        self.issue['confidence']='confirmed'
        with self.assertRaises(ValueError):compat.validate_issue(self.issue)
    def test_no_brand_wildcard(self):
        self.issue['renderer']=['*']
        with self.assertRaises(ValueError):compat.validate_issue(self.issue)
    def test_blocked_capture(self):self.assertEqual(compat.evaluate({'status':'BLOCKED_BY_HARDWARE'},self.issue,'2026-11-01')['status'],'UNKNOWN')
    def test_bad_snapshot_rejected(self):
        del self.record['snapshot']['gl_extensions']
        with self.assertRaises(ValueError):compat.evaluate(self.record,self.issue,'2026-11-01')
    def test_no_invented_confirmed_issues(self):self.assertEqual(json.loads((HERE/'known-issues.json').read_text())['confirmed_issues'],[])
if __name__=='__main__':unittest.main()
