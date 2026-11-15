import copy,json,unittest
from check_v109_research_chain import check,ROOT
class Chain(unittest.TestCase):
 def setUp(self):self.c=json.loads((ROOT/'docs/v1.0.9/research/experiment-chain.json').read_text())
 def test_links(self):self.assertEqual(check(self.c)['links'],4)
 def test_stale_review(self):
  self.c['review_sha256']='0'*64
  with self.assertRaises(ValueError):check(self.c)
 def test_stale_experiment(self):
  self.c['rows'][0]['files'][0]['sha256']='0'*64
  with self.assertRaises(ValueError):check(self.c)
 def test_promotion(self):
  self.c['rows'][0]['rule_promotion']='VERIFIED'
  with self.assertRaises(ValueError):check(self.c)
 def test_review_not_inferred(self):
  self.c['rows'][0]['independent_review']='PASS'
  with self.assertRaises(ValueError):check(self.c)
 def test_coverage(self):
  self.c['rows'].pop()
  with self.assertRaises(ValueError):check(self.c)
