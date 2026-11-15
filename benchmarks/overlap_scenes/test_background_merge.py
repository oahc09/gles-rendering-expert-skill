import unittest
import background_merge as m
class BackgroundMergeTests(unittest.TestCase):
 def test_invalid_baseline_never_accepted(self):
  self.assertIsNone(m.global_selection(False,True));self.assertIsNone(m.global_selection(False,False))
 def test_valid_baseline_fallback(self):self.assertEqual(m.global_selection(True,False),'baseline')
 def test_valid_merge(self):self.assertEqual(m.global_selection(True,True),'merged_background')
 def test_empty_contract_rejected(self):self.assertFalse(m.contract_valid([],[],{'selected':None}))
 def test_count(self):self.assertEqual(len(m.scene()),11);self.assertEqual(len(m.merge(m.scene())),7)
 def test_foreground_unchanged(self):
  original=[o for o in m.scene() if o['role']=='foreground'];self.assertEqual(original,[o for o in m.merge(m.scene()) if o['role']=='foreground'])
 def test_color_mismatch_not_merged(self):
  a=m.scene()[0];b=dict(a,color=[0,0,0,.3]);self.assertFalse(m.compatible(a,b))
 def test_depth_mismatch(self):
  a=m.scene()[0];self.assertFalse(m.compatible(a,dict(a,z=a['z']+.1)))
 def test_projection_mismatch(self):
  a=m.scene()[0];self.assertFalse(m.compatible(a,dict(a,radius=.2)))
 def test_foreground_not_merged(self):
  a=dict(m.scene()[0],role='foreground');self.assertFalse(m.compatible(a,a))
 def test_only_adjacent(self):
  a=m.scene()[0];b=dict(a,color=[0,0,0,.3]);self.assertEqual(len(m.merge([a,b,a])),3)
 def test_no_input_mutation(self):
  a=m.scene();m.merge(a);self.assertTrue(all(o['mode'] in (0,3) for o in a))
 def test_combined_alpha_identity(self):
  for a in (0,.03,.3,.9,1):self.assertAlmostEqual(1-(1-a)**2,a+a*(1-a))
 def test_profile_not_single_gaussian(self):
  a=.3;g=.2;self.assertNotAlmostEqual(1-(1-a*g)**2,(1-(1-a)**2)*g)
if __name__=='__main__':unittest.main()
