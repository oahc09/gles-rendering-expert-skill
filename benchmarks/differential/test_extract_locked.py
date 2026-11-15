import unittest,tempfile,zipfile,hashlib
from pathlib import Path
from extract_locked import extract
class ExtractTests(unittest.TestCase):
 def run_zip(self,items,want=None):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);z=root/'archive.zip'
   with zipfile.ZipFile(z,'w') as a:
    for name,data in items:a.writestr(name,data)
   return extract(z,root/'out',{'files':{'libEGL.so':want or hashlib.sha256(b'ok').hexdigest()}})
 def test_success(self):self.assertEqual(self.run_zip([('root/libEGL.so',b'ok'),('../ignored',b'bad')]),['libEGL.so'])
 def test_mismatch(self):
  with self.assertRaises(ValueError):self.run_zip([('root/libEGL.so',b'wrong')])
 def test_missing(self):
  with self.assertRaises(ValueError):self.run_zip([('other',b'ok')])
 def test_duplicate(self):
  with self.assertRaises(ValueError):self.run_zip([('a/libEGL.so',b'ok'),('b/libEGL.so',b'ok')])
