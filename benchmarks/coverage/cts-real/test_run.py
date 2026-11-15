import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).with_name('run.py');s=importlib.util.spec_from_file_location('ctsreal',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class RecordTests(unittest.TestCase):
 def test_session_removed_status_unchanged(self):
  case='#beginTestCaseResult a\n<TestCaseResult CasePath="a"><Result StatusCode="Fail">x</Result></TestCaseResult>\n#endTestCaseResult\n'
  self.assertEqual(m.case_records('#sessionInfo HOST private\n'+case+'#endSession\n'),case)
 def test_truncation_rejected(self):
  with self.assertRaises(ValueError):m.case_records('#beginTestCaseResult a\n')
 def test_empty_rejected(self):
  with self.assertRaises(ValueError):m.case_records('#sessionInfo only\n')
if __name__=='__main__':unittest.main()
