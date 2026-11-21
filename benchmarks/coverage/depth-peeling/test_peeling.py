import hashlib,importlib.util,json,math,unittest
from pathlib import Path
HERE=Path(__file__).parent
s=importlib.util.spec_from_file_location('peel_tests',HERE/'run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_fixed_inputs(self):self.assertEqual(m.validate(m.LAYERS),'VALID')
 def test_malformed(self):
  for x in (None,[],[None],[{'plane':None,'rgba':[0]*4}],[{'plane':3,'rgba':[0]*4}]):self.assertNotEqual(m.validate(x),'VALID')
 def test_tie_bin_rejected(self):
  self.assertEqual(m.validate([m.LAYERS[0],m.LAYERS[0]]),'AMBIGUOUS_TIE_OR_DEPTH_GAP')
  self.assertEqual(m.validate([{'plane':[.5,0],'rgba':[0]*4},{'plane':[.500001,0],'rgba':[0]*4}]),'AMBIGUOUS_TIE_OR_DEPTH_GAP')
 def test_quantized_clear_depth_rejected(self):
  self.assertEqual(m.validate([{'plane':[.99999,0],'rgba':[0]*4}]),'QUANTIZED_DEPTH_OUT_OF_RANGE')
 def test_quantization_boundary_rejected(self):
  self.assertEqual(m.validate([{'plane':[.5001220703125,0],'rgba':[0]*4}]),'UNSAFE_QUANTIZATION_BOUNDARY')
 def test_ranges(self):
  for v in (float('nan'),-1,2,True):self.assertNotEqual(m.validate([{'plane':[v,0],'rgba':[0]*4}]),'VALID')
 def test_real_positive_and_permutations(self):
  for driver in ('mesa','angle'):
   r=json.loads((HERE/(driver+'.json')).read_text());self.assertEqual(r['status'],'HOST_PASS');self.assertLessEqual(r['permutation_max_difference'],2);self.assertGreaterEqual(r['fragment_highp']['precision'],23)
   for row in r['cases'][:7]:
    self.assertEqual(row['decision'],'ACCEPT_FINITE_SAMPLE');self.assertLessEqual(row['max_error'],2);self.assertEqual(row['query_any_samples'],[True]*row['layer_budget']+[False])
 def test_every_peel_independent_oracle(self):
  for driver in ('mesa','angle'):
   r=json.loads((HERE/(driver+'.json')).read_text())
   for row in r['cases'][:7]:
    layers=m.LAYERS[:2] if row['id']=='two-crossing' else m.LAYERS
    for stage,pixels in enumerate(row['peeled_color_stages']):
     expected=[]
     for y in range(4):
      for x in range(4):
       l=sorted(layers,key=lambda l:l['plane'][0]+l['plane'][1]*(x+.5))[stage];c=l['rgba'];expected.extend(math.floor(v*255+.5) for v in [c[i]*c[3] for i in range(3)]+[c[3]])
     self.assertEqual(pixels,expected)
 def test_actual_overflow_and_errors_rejected(self):
  for driver in ('mesa','angle'):
   r=json.loads((HERE/(driver+'.json')).read_text());rows={x['id']:x for x in r['cases']}
   self.assertEqual(rows['budget-overflow']['query_any_samples'],[True]*3);self.assertEqual(rows['budget-overflow']['reject_reason'],'LAYER_BUDGET_OVERFLOW')
   for n in ('budget-overflow','missing-layer','wrong-depth'):self.assertEqual(rows[n]['decision'],'REJECT');self.assertGreater(rows[n]['max_error'],2)
 def test_preflight_no_draws(self):
  for driver in ('mesa','angle'):
   rows=json.loads((HERE/(driver+'.json')).read_text())['rejected_before_draw'];self.assertEqual(len(rows),5)
   for r in rows:self.assertEqual(r['decision'],'REJECT');self.assertEqual(r['geometry_draws']+r['compose_draws']+r['readbacks'],0)
 def test_hash_and_no_private_fingerprints(self):
  for driver in ('mesa','angle'):
   raw=(HERE/(driver+'.json')).read_text();r=json.loads(raw);self.assertEqual(r['source_sha256'],hashlib.sha256((HERE/'run.py').read_bytes()).hexdigest());self.assertEqual(r['actual_counts'],{'geometry_draws':107,'compose_draws':28,'readbacks':38,'occlusion_queries':38})
   for token in ('/tmp/','/workspace/','renderer','libraries'):self.assertNotIn(token,raw)
if __name__=='__main__':unittest.main()
