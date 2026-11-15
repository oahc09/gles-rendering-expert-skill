import copy,hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).parent
def validate(guide,cases):
 expected={c['case_id']:c for c in cases['cases'] if c.get('v109')}
 rows=guide['rows']
 if guide['provider_results']!=0 or len(rows)!=len(expected) or {r['case_id'] for r in rows}!=set(expected):raise ValueError('coverage')
 for r in rows:
  c=expected[r['case_id']]
  if hashlib.sha256(c['prompt'].encode()).hexdigest()!=r['prompt_sha256']:raise ValueError('stale prompt')
  if r['finding'] not in c['expected_findings']:raise ValueError('finding mismatch')
  if r['automated_verdict'] is not None or r['independent_review']!='NOT_RUN':raise ValueError('not independent acceptance')
  if len(set(r['required_reasoning']))<2 or not all(isinstance(x,str) and x.strip() for x in r['required_reasoning']):raise ValueError('specific guidance')
 return True
class Guide(unittest.TestCase):
 def setUp(self):
  self.g=json.loads((ROOT/'v109-adjudication-guide.json').read_text());self.c=json.loads((ROOT/'cases-v1.0.9.json').read_text())
 def test_complete_bound_guide(self):self.assertTrue(validate(self.g,self.c))
 def test_stale_prompt(self):
  self.g['rows'][0]['prompt_sha256']='0'*64
  with self.assertRaises(ValueError):validate(self.g,self.c)
 def test_fake_independent_review(self):
  self.g['rows'][0]['independent_review']='PASS'
  with self.assertRaises(ValueError):validate(self.g,self.c)
 def test_missing_case(self):
  self.g['rows'].pop()
  with self.assertRaises(ValueError):validate(self.g,self.c)
 def test_not_provider_output(self):
  self.g['provider_results']=30
  with self.assertRaises(ValueError):validate(self.g,self.c)
