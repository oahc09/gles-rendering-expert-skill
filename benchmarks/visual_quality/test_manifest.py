import json,unittest
from run import GOLDEN,validate_manifest
class ManifestTests(unittest.TestCase):
 def setUp(self):self.manifest=json.loads((GOLDEN/'manifest.json').read_text())
 def test_complete(self):validate_manifest(self.manifest)
 def test_missing_item(self):
  del self.manifest['images']['P01-0.ppm']
  with self.assertRaises(ValueError):validate_manifest(self.manifest)
 def test_empty(self):
  self.manifest['images']={}
  with self.assertRaises(ValueError):validate_manifest(self.manifest)
 def test_extra_or_traversal(self):
  self.manifest['images']['../other.ppm']=next(iter(self.manifest['images'].values()))
  with self.assertRaises(ValueError):validate_manifest(self.manifest)
 def test_time_metadata(self):
  self.manifest['images']['P01-0.ppm']['capture']['time_seconds']=999
  with self.assertRaises(ValueError):validate_manifest(self.manifest)
 def test_color_space(self):
  self.manifest['color_space']='linear HDR'
  with self.assertRaises(ValueError):validate_manifest(self.manifest)
if __name__=='__main__':unittest.main()
