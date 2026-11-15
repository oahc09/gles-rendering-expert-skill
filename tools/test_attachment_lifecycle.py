import copy,unittest
from estimate_gpu_cost import estimate
def case(samples=1):
 return {'attachments':[{'id':'a','width':2,'height':2,'format':'RGBA8','samples':samples}],
 'lifecycle':[{'op':'begin','fbo':'a','loads':{'a':'clear'}},{'op':'draw','writes':['a'],'coverage':'partial'},{'op':'end','stores':{'a':'store'}}]}
class Lifecycle(unittest.TestCase):
 def test_clear_store(self):self.assertEqual(estimate(case())['logical_upper_bytes'],16)
 def test_lower_never_dram(self):
  r=estimate(case());self.assertEqual(r['logical_lower_bytes'],0);self.assertIsNone(r['dram_bytes'])
 def test_discard(self):
  d=case();d['lifecycle'][-1]['stores']['a']='discard';self.assertEqual(estimate(d)['logical_upper_bytes'],0)
 def test_consumer(self):
  d=case();d['lifecycle'].append({'op':'consume','attachment':'a'});self.assertEqual(estimate(d)['logical_upper_bytes'],32)
 def test_discard_consumer(self):
  d=case();d['lifecycle'][-1]['stores']['a']='discard';d['lifecycle'].append({'op':'consume','attachment':'a'})
  with self.assertRaises(ValueError):estimate(d)
 def test_two_pass(self):
  d=case();d['lifecycle'] += [{'op':'begin','fbo':'b','loads':{'a':'load'}},{'op':'end','stores':{'a':'store'}}];self.assertEqual(estimate(d)['logical_upper_bytes'],48)
 def test_switch_unknown(self):
  d=case();d['lifecycle'].insert(2,{'op':'switch','fbo':'b'});self.assertEqual(estimate(d)['logical_upper_bytes'],48)
 def test_scoped_preserve(self):
  d=case();d['lifecycle'].insert(2,{'op':'switch','fbo':'b'});d['driver_condition']={'fbo_switch':'preserves_tile',**{x:'fixture-not-device-evidence' for x in ('device','gpu','driver','backend','source')}}
  self.assertEqual(estimate(d)['logical_upper_bytes'],16);self.assertEqual(estimate(d)['condition_authenticity'],'NOT_AUTHENTICATED')
 def test_unscoped_driver(self):
  d=case();d['driver_condition']={'fbo_switch':'flushes_tile'}
  with self.assertRaises(ValueError):estimate(d)
 def test_msaa_resolve(self):
  d=case(4);d['lifecycle'].insert(2,{'op':'resolve','attachment':'a'});self.assertEqual(estimate(d)['logical_upper_bytes'],144)
 def test_single_sample_resolve_reject(self):
  d=case();d['lifecycle'].insert(2,{'op':'resolve','attachment':'a'})
  with self.assertRaises(ValueError):estimate(d)
 def test_unknown_format(self):
  d=case();d['attachments'][0]['format']='UNKNOWN';self.assertIsNone(estimate(d)['logical_upper_bytes'])
 def test_texture(self):
  d=case();d.update(texture_samples=4,bytes_per_sample=4);self.assertEqual(estimate(d)['logical_upper_bytes'],32)
 def test_unknown_texture(self):
  d=case();d['texture_samples']=4;self.assertIsNone(estimate(d)['logical_upper_bytes'])
 def test_full_overwrite_discard(self):
  d=case();d['lifecycle'][0]['loads']['a']='discard';d['lifecycle'][1]['coverage']='full_overwrite';self.assertEqual(estimate(d)['logical_upper_bytes'],16)
 def test_partial_undefined(self):
  d=case();d['lifecycle'][0]['loads']['a']='discard'
  with self.assertRaises(ValueError):estimate(d)
 def test_invalid_sequences(self):
  variants=[]
  d=case();d['lifecycle']=d['lifecycle'][1:];variants.append(d)
  d=case();d['lifecycle'].pop();variants.append(d)
  d=case();d['lifecycle'].insert(1,copy.deepcopy(d['lifecycle'][0]));variants.append(d)
  d=case();d['lifecycle'][0]['loads']['a']='load';variants.append(d)
  d=case();d['lifecycle'][-1]['stores']={};variants.append(d)
  for d in variants:
   with self.subTest(d=d),self.assertRaises(ValueError):estimate(d)
 def test_input_unchanged(self):
  d=case();before=copy.deepcopy(d);estimate(d);self.assertEqual(d,before)
