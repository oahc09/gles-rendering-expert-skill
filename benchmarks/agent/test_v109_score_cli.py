import json,tempfile,unittest
from pathlib import Path
from score_v109 import score_files
from run import digest
HERE=Path(__file__).parent
class ScoreBoundary(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.cases=HERE/'cases-v1.0.9.json';self.reviews=self.root/'reviews.json';self.reviews.write_text('[]')
  self.summary={'status':'BLOCKED_BY_PROVIDER','case_source_sha256':digest(self.cases.read_text()),'results':[]}
 def tearDown(self):self.tmp.cleanup()
 def run_score(self):
  (self.root/'summary.json').write_text(json.dumps(self.summary));return score_files(self.root,self.reviews,self.cases)
 def test_blocked_is_not_score(self):
  r=self.run_score();self.assertEqual(r['status'],'BLOCKED_BY_PROVIDER');self.assertEqual(r['paired_cases'],0)
  self.assertTrue(all(m['ratio'] is None for g in r['v109_metrics'].values() for m in g.values()))
 def test_corpus_hash(self):
  self.summary['case_source_sha256']='wrong'
  with self.assertRaises(ValueError):self.run_score()
 def test_synthetic_never_quality(self):
  self.summary['synthetic_infrastructure_test']=True
  with self.assertRaises(ValueError):self.run_score()
 def test_response_escape(self):
  self.summary['results']=[{'response_file':'../outside','response_sha256':'wrong'}]
  with self.assertRaises(ValueError):self.run_score()
 def test_response_hash(self):
  (self.root/'response.txt').write_text('modified');self.summary['results']=[{'response_file':'response.txt','response_sha256':'wrong'}]
  with self.assertRaises(ValueError):self.run_score()
 def test_review_array(self):
  self.reviews.write_text('{}')
  with self.assertRaises(ValueError):self.run_score()
