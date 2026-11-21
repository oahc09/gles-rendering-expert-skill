import copy,json,unittest
from pathlib import Path
from check_coverage import validate_extension_metadata
M=Path(__file__).resolve().parents[2]/'references/coverage/source-manifest.json'
class CitationTests(unittest.TestCase):
 def setUp(self):self.m=json.loads(M.read_text())
 def test_metadata_not_text_proof(self):
  r=validate_extension_metadata(self.m);self.assertEqual(r['offline_text_verification'],'NOT_PERFORMED');self.assertEqual(r['citation_count'],3)
 def test_no_full_text_vendoring(self):
  for item in self.m['extension_specs']:self.assertNotIn('file',item)
  for name in ('KHR_KHR_debug.txt','OES_OES_EGL_image_external.txt','EXT_EXT_disjoint_timer_query.txt'):self.assertFalse((M.parent/'registry'/name).exists())
 def test_reject_revision(self):
  self.m['extension_specs'][0]['revision']='0'*40
  with self.assertRaises(ValueError):validate_extension_metadata(self.m)
 def test_reject_hash(self):
  self.m['extension_specs'][0]['retrieved_sha256']='unknown'
  with self.assertRaises(ValueError):validate_extension_metadata(self.m)
 def test_reject_offline_claim(self):
  self.m['extension_specs'][0]['file']='registry/spec.txt'
  with self.assertRaises(ValueError):validate_extension_metadata(self.m)
 def test_reject_url(self):
  self.m['extension_specs'][0]['url']='https://example.com/spec.txt'
  with self.assertRaises(ValueError):validate_extension_metadata(self.m)
 def test_reject_missing(self):
  self.m['extension_specs'].pop()
  with self.assertRaises(ValueError):validate_extension_metadata(self.m)
if __name__=='__main__':unittest.main()
