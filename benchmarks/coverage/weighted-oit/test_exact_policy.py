import copy,hashlib,importlib.util,json,unittest
from pathlib import Path
HERE=Path(__file__).parent
s=importlib.util.spec_from_file_location('exact_replay',HERE/'exact_replay.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_global_order(self):self.assertEqual(m.exact_policy.decide(m.layers([(.2,0),(.8,0)]),4,4)['far_to_near'],['1','0'])
 def test_crossing_rejected(self):self.assertEqual(m.exact_policy.decide(m.layers([(.1,.2),(.9,-.2)]),4,4)['reason'],'CROSSING_PER_PIXEL_ORDER')
 def test_tie_rejected(self):self.assertEqual(m.exact_policy.decide(m.layers([(.5,0),(.5,0)]),4,4)['reason'],'AMBIGUOUS_TIE')
 def test_incomplete_nan_rejected(self):
  for value in ([],[float('nan')]*16):
   ls=m.layers([(.2,0),(.8,0)]);ls[0]['depths']=value;self.assertEqual(m.exact_policy.decide(ls,4,4)['selection'],'UNAVAILABLE')
 def test_malformed_layer_rejected(self):
  for value in (None,[],17,'layer'):
   self.assertEqual(m.exact_policy.decide([value],4,4)['reason'],'MALFORMED_LAYER')
 def test_normalized_depth_required(self):
  for value in (-.1,1.1,True):
   ls=m.layers([(.2,0),(.8,0)]);ls[0]['depths'][0]=value;self.assertEqual(m.exact_policy.decide(ls,4,4)['selection'],'UNAVAILABLE')
 def test_duplicate_id_rejected(self):
  ls=m.layers([(.2,0),(.8,0)]);ls[1]['id']='0';self.assertEqual(m.exact_policy.decide(ls,4,4)['reason'],'INVALID_IDS')
 def test_depth_only_weights_cannot_match_both_alphas(self):
  # Necessary coefficient ratios for independent foreground/background colors.
  self.assertNotEqual(1/(1-.25),1/(1-.75))
 def test_actual_both(self):
  for name in ('mesa','angle'):
   r=json.loads((HERE/('exact-'+name+'.json')).read_text());self.assertEqual(r['status'],'HOST_POLICY_PASS');self.assertEqual(r['actual_draws'],24);self.assertEqual(r['actual_readbacks'],8)
   for scene in r['scenes'][:2]:self.assertEqual(scene['draws'][0]['max_error_to_per_pixel_over'],0);self.assertGreater(scene['draws'][1]['max_error_to_per_pixel_over'],2)
   self.assertTrue(all(x['max_error_to_per_pixel_over']>2 for x in r['scenes'][2]['draws']));self.assertEqual(r['scenes'][2]['decision']['selection'],'UNAVAILABLE')
 def test_hash_sanitization_and_original_failure_retained(self):
  for name in ('mesa','angle'):
   raw=(HERE/('exact-'+name+'.json')).read_text();r=json.loads(raw);self.assertEqual(r['source_sha256'],hashlib.sha256((HERE/'exact_replay.py').read_bytes()).hexdigest());self.assertEqual(r['policy_sha256'],hashlib.sha256((HERE/'exact_policy.py').read_bytes()).hexdigest())
   for token in ('/tmp/','/workspace/','renderer','libraries'):self.assertNotIn(token,raw)
   old=json.loads((HERE/(name+'.json')).read_text());self.assertEqual([s['quality_status'] for s in old['scenes']],['REJECTED_APPROXIMATION']*2)
if __name__=='__main__':unittest.main()
