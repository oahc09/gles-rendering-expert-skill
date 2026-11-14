import unittest,copy,math
from model import *
class FilmTests(unittest.TestCase):
 def test_prior_abi(self):self.assertEqual(prior.validate(ABI),[])
 def test_upgrade(self):self.assertEqual(migrate({'version':1},2)['ior'],1.4)
 def test_lossless_roundtrip(self):
  d={'version':1,'thickness_nm':200};self.assertEqual(migrate(migrate(d,2),1),d)
 def test_rejects(self):
  bad=[{'version':3},{'version':True},{'version':2,'thickness_nm':-1},{'version':2,'thickness_nm':float('nan')},{'version':2,'ior':0},{'version':2,'strength':2},{'version':1,'ior':1.6},{'version':2,'unknown':1}]
  for d in bad:
   with self.subTest(d=d),self.assertRaises(ValueError):validate(d)
 def test_rollback_refuses_loss(self):
  for field,value in [('ior',1.6),('strength',.5)]:
   with self.assertRaises(ValueError):migrate({'version':2,field:value},1)
 def test_target_reject(self):
  with self.assertRaises(ValueError):migrate({'version':1},4)
 def test_cache_invalidated(self):
  d={'version':2};k=cache_key(d,'shader','driver')
  self.assertNotEqual(k,cache_key(d,'shader2','driver'));self.assertNotEqual(k,cache_key(d,'shader','driver2'));self.assertNotEqual(k,cache_key(d,'shader','driver','mediump'));self.assertNotEqual(k,cache_key({'version':2,'ior':1.5},'shader','driver'))
 def test_zero_thickness(self):
  for x in rgb(0,.5):self.assertAlmostEqual(x,.04)
 def test_angle_color(self):self.assertGreater(max(abs(a-b) for a,b in zip(rgb(400,.1),rgb(400,.9))),.005)
 def test_bounds(self):
  for t in range(0,1201,20):
   for mu in (.05,.5,1):self.assertTrue(all(0<=x<=1 and math.isfinite(x) for x in rgb(t,mu)))
 def test_strength_zero(self):self.assertEqual(rgb(400,.5,strength=0),[.04]*3)
if __name__=='__main__':unittest.main()
