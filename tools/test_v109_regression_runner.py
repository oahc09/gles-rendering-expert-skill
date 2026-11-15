import unittest,tempfile
from pathlib import Path
from run_v109_regression import summarize,validate_manifest
class RunnerTests(unittest.TestCase):
 def test_pass(self):self.assertEqual(summarize('tests',0,'Ran 2 tests in 0.01s\n\nOK\n')['status'],'PASS')
 def test_skips_fail(self):self.assertEqual(summarize('tests',0,'Ran 2 tests in 0.1s\n\nOK (skipped=1)\n')['status'],'FAIL')
 def test_empty_not_pass(self):self.assertEqual(summarize('tests',0,'Ran 0 tests in 0.1s\n\nOK\n')['status'],'FAIL')
 def test_crash_not_pass(self):self.assertEqual(summarize('tests',1,'Ran 2 tests in 0.1s\n\nOK\n')['status'],'FAIL')
 def test_unparsed_not_pass(self):self.assertEqual(summarize('tests',0,'anything')['status'],'FAIL')
 def test_no_raw_output_disclosure(self):self.assertNotIn('secret',str(summarize('tests',0,'secret machine path\nRan 2 tests in 0.1s\n\nOK\n')))
 def test_paths(self):
  for ds in ([],['../outside'],['/tmp'],['tools','tools'],[['tools']]):
   with self.assertRaises(ValueError):validate_manifest({'schema_version':1,'directories':ds})
