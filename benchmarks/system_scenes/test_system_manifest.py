import copy,json,tempfile,unittest
from pathlib import Path
from run import validate_manifest,HERE
class ManifestTests(unittest.TestCase):
 def setUp(self):self.manifest=json.loads((HERE/'golden/manifest.json').read_text())
 def invalid(self,mutate):
  m=copy.deepcopy(self.manifest);mutate(m)
  with self.assertRaises(ValueError):validate_manifest(m,HERE/'golden')
 def test_valid(self):self.assertTrue(validate_manifest(self.manifest,HERE/'golden'))
 def test_empty(self):self.invalid(lambda m:m.update(images={}))
 def test_missing(self):self.invalid(lambda m:m['images'].pop('glass.ppm'))
 def test_extra(self):self.invalid(lambda m:m['images'].update(extra=m['images']['glass.ppm']))
 def test_size(self):self.invalid(lambda m:m.update(size=[48,48]))
 def test_color(self):self.invalid(lambda m:m.update(color_space='linear'))
 def test_seed(self):self.invalid(lambda m:m.update(seed=0))
 def test_interaction(self):self.invalid(lambda m:m.update(interaction=1))
 def test_config_hash(self):self.invalid(lambda m:m.update(comparison_config_sha256='0'*64))
 def test_image_metadata(self):self.invalid(lambda m:m['images']['glass.ppm']['metadata'].update(mode='degraded'))
 def test_image_hash(self):self.invalid(lambda m:m['images']['glass.ppm'].update(sha256='0'*64))
 def test_producer_missing(self):self.invalid(lambda m:m.update(source_hashes={}))
 def test_actual_dimensions_even_with_updated_hash(self):
  import hashlib
  with tempfile.TemporaryDirectory() as directory:
   folder=Path(directory)
   for source in (HERE/'golden').glob('*.ppm'):(folder/source.name).write_bytes(source.read_bytes())
   wrong=folder/'glass.ppm';wrong.write_bytes(b'P6\n48 48\n255\n'+bytes(48*48*3));m=copy.deepcopy(self.manifest);m['images']['glass.ppm']['sha256']=hashlib.sha256(wrong.read_bytes()).hexdigest()
   with self.assertRaises(ValueError):validate_manifest(m,folder)
 def test_per_image_seed(self):self.invalid(lambda m:m['images']['glass.ppm']['metadata'].update(seed=0))
if __name__=='__main__':unittest.main()
