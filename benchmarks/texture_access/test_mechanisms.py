import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('texture_mechanisms',Path(__file__).with_name('mechanisms.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Mechanisms(unittest.TestCase):
 def test_distinct_mechanisms(self):
  cases=m.cases();self.assertEqual(len(cases),14);self.assertEqual(len({c['mode'] for c in cases}),13)
  self.assertTrue({'mip','explicit-mip','array','pbo','r8','rgb565','linear','atlas','lowres'} <= {c['mode'] for c in cases})
 def test_oracles_and_negatives(self):
  cases=m.cases();self.assertEqual(sum(bool(c.get('negative')) for c in cases),2)
  for c in cases:
   self.assertEqual(len(c['golden']),64);self.assertTrue(all(type(v)==int and 0<=v<=255 for v in c['golden']))
 def test_no_machine_metadata_output(self):
  source=Path(m.__file__).read_text();self.assertNotIn('metadata=h.metadata',source)
if __name__=='__main__':unittest.main()
