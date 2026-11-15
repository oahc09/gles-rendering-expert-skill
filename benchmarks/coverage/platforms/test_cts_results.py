import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/coverage'))
from cts_results import report,parse_qpa
class QPA(unittest.TestCase):
 def qpa(self,status='Pass'):return ('#beginTestCaseResult fixture.case\n<TestCaseResult CasePath="fixture.case"><Result StatusCode="'+status+'">fixture only</Result></TestCaseResult>\n#endTestCaseResult\n').encode()
 def test_fixture_parser_not_device(self):r=report(self.qpa(),['fixture.case'],0);self.assertEqual(r['status'],'PASS');self.assertFalse(r['device_validation']);self.assertFalse(r['certification_claim'])
 def test_process_failure_not_pass(self):self.assertEqual(report(self.qpa(),['fixture.case'],1)['status'],'FAIL')
 def test_missing_cases_incomplete(self):self.assertEqual(report(self.qpa(),['fixture.case','missing'],0)['status'],'INCOMPLETE')
 def test_extra_cases_incomplete(self):self.assertEqual(report(self.qpa(),['other'],0)['status'],'INCOMPLETE')
 def test_warning_not_pass(self):self.assertEqual(report(self.qpa('QualityWarning'),['fixture.case'],0)['status'],'FAIL')
 def test_unsupported_not_pass(self):self.assertEqual(report(self.qpa('NotSupported'),['fixture.case'],0)['status'],'FAIL')
 def test_unknown_rejected(self):
  with self.assertRaises(ValueError):report(self.qpa('Maybe'),['fixture.case'],0)
 def test_truncated_rejected(self):
  with self.assertRaises(ValueError):parse_qpa(self.qpa().decode().replace('#endTestCaseResult',''))
 def test_duplicate_rejected(self):
  with self.assertRaises(ValueError):parse_qpa((self.qpa()*2).decode())
 def test_empty_rejected(self):
  with self.assertRaises(ValueError):parse_qpa('')
 def test_boolean_exit_rejected(self):
  with self.assertRaises(ValueError):report(self.qpa(),['fixture.case'],False)
 def test_expected_string_not_list_rejected(self):
  with self.assertRaises(ValueError):report(self.qpa(),'fixture.case',0)
 def test_empty_expected_name_rejected(self):
  with self.assertRaises(ValueError):report(self.qpa(),[''],0)
if __name__=='__main__':unittest.main()
