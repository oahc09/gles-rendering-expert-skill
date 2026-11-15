import unittest
import tiered as t
class TieredTests(unittest.TestCase):
 def test_counts(self):
  for n in (8,24,48):self.assertEqual(len(t.scene(n)),n)
 def test_depth(self):self.assertEqual([o['z'] for o in t.scene(24)],sorted([o['z'] for o in t.scene(24)],reverse=True))
 def test_disjoint(self):
  for n in (8,24,48):
   for c in (-.3,0,.3):self.assertTrue(t.disjoint_groups(t.scene(n),c))
 def test_overlap_rejected(self):
  o=t.scene(8);o[0]['x']=o[1]['x'];o[0]['y']=o[1]['y'];self.assertFalse(t.disjoint_groups(o,0))
 def test_group_preserves_local_order(self):
  o=t.scene(24);g=sorted(o,key=lambda v:v['group'])
  for group in (0,1):self.assertEqual([x['id'] for x in o if x['group']==group],[x['id'] for x in g if x['group']==group])
 def test_gate(self):self.assertTrue(t.accepted(dict(max_rgba8_error=4,silhouette_disagree_pixels=2,centroid_error_pixels=.1)))
 def test_color_rejected(self):self.assertFalse(t.accepted(dict(max_rgba8_error=5,silhouette_disagree_pixels=0,centroid_error_pixels=0)))
 def test_mask_rejected(self):self.assertFalse(t.accepted(dict(max_rgba8_error=0,silhouette_disagree_pixels=3,centroid_error_pixels=0)))
 def test_centroid_rejected(self):self.assertFalse(t.accepted(dict(max_rgba8_error=0,silhouette_disagree_pixels=0,centroid_error_pixels=.11)))
 def test_missing_centroid(self):self.assertFalse(t.accepted(dict(max_rgba8_error=0,silhouette_disagree_pixels=0,centroid_error_pixels=None)))
if __name__=='__main__':unittest.main()
