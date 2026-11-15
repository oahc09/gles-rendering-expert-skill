import unittest
from check_v109_evidence import check
class EvidenceTests(unittest.TestCase):
 def test_pixels_source_hash_allowed(self):self.assertEqual(check({'source_sha256':'a'*64,'pixels':[0,255],'status':'HOST_PASS'}),[])
 def test_environment_rejected(self):
  for k in ('metadata','compiler_sha256','compiler_version','config_sha256','executable_sha256','library_sha256','hostname'):
   with self.subTest(key=k):self.assertTrue(check({k:'x'}))
 def test_recursive(self):self.assertTrue(check({'draws':[{'metadata':{}}]}))
 def test_paths_rejected(self):
  for p in ('/tmp/a','/workspace/abc','/home/agent/x','/usr/lib/libGL.so'):
   with self.subTest(path=p):self.assertTrue(check({'log':p}))
 def test_public_url_and_relative_path(self):self.assertEqual(check({'source':'https://github.com/oahc09/gles-rendering-expert-skill','file':'benchmarks/shader_ab/run.py'}),[])
if __name__=='__main__':unittest.main()
