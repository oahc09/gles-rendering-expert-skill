import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('attachment_controls',Path(__file__).with_name('run.py'));a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
class Attachment(unittest.TestCase):
 def test_expected_blend(self):self.assertEqual(a.normalized_expected()[:4],[128,77,128,255])
 def test_integer(self):self.assertEqual(a.EXPECTED_INTEGER[:4],[7,42,65535,123456])
 def test_count(self):self.assertEqual(len(a.normalized_expected()),64)
 def test_identity_float(self):self.assertEqual(a.compare(a.normalized_expected(),a.normalized_expected())['status'],'PASS')
 def test_identity_int(self):self.assertEqual(a.compare(a.EXPECTED_INTEGER,a.EXPECTED_INTEGER,True)['status'],'PASS')
 def test_int_no_tolerance(self):x=a.EXPECTED_INTEGER.copy();x[0]+=1;self.assertEqual(a.compare(x,a.EXPECTED_INTEGER,True)['status'],'FAIL')
 def test_float_tolerance(self):x=a.normalized_expected();x[0]+=1;self.assertEqual(a.compare(x,a.normalized_expected())['status'],'PASS')
 def test_disabled_blend(self):self.assertEqual(a.compare([204,51,102,128]*16,a.normalized_expected())['status'],'FAIL')
 def test_out_of_range(self):self.assertEqual(a.compare([256]*64,a.normalized_expected())['status'],'INVALID')
 def test_nan(self):self.assertEqual(a.compare([float('nan')]*64,a.normalized_expected())['status'],'INVALID')
 def test_bool(self):self.assertEqual(a.compare([False]*64,a.normalized_expected())['status'],'INVALID')
 def test_sparse_location(self):self.assertIn('location=2',a.SPARSE)
if __name__=='__main__':unittest.main()
