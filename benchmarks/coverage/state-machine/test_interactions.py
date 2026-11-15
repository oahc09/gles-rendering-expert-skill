import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class Interactions(unittest.TestCase):
 def setUp(self):self.e=json.loads((Path(__file__).parent/'evidence.json').read_text())
 def test_forty_plus_distinct_cases(self):self.assertEqual(len({r['case'] for r in self.e['rows']}),48)
 def test_positive_and_negative(self):self.assertEqual(sum(r['expected']==0 for r in self.e['rows']),24);self.assertEqual(sum(r['expected']!=0 for r in self.e['rows']),24)
 def test_expected_errors_observed(self):self.assertTrue(all(r['expected']==r['observed'] for r in self.e['rows']))
 def test_bound_sources(self):
  for p,h in self.e['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h)
 def test_not_physical(self):self.assertEqual(self.e['execution_class'],'SOFTWARE_GLES');self.assertIsNone(self.e['device'])
if __name__=='__main__':unittest.main()
