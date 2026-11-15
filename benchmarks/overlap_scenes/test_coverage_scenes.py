import math,unittest
import coverage_scenes as c
class CoverageTests(unittest.TestCase):
 def test_types(self):self.assertEqual({o['mode'] for s in c.scenes() for o in s['objects']},{4,5,6})
 def test_three_scenes(self):self.assertEqual(len(c.scenes()),3)
 def test_rain(self):
  o={'mode':4,'color':[0,0,0,.5]};self.assertEqual(c.opacity(o,0,0),.5);self.assertAlmostEqual(c.opacity(o,.5,0),.375);self.assertIsNone(c.opacity(o,.9,.9))
 def test_volume(self):
  o={'mode':5,'color':[0,0,0,.5]};self.assertAlmostEqual(c.opacity(o,0,0),1-math.exp(-.125));self.assertIsNone(c.opacity(o,.9,.9))
 def test_ui_corner(self):
  o={'mode':6,'color':[0,0,0,.5]};self.assertEqual(c.opacity(o,.8,.8),.5);self.assertIsNone(c.opacity(o,.99,.99))
 def test_empty_background(self):
  pixels,stats=c.cpu([],0);self.assertEqual(sum(pixels),0);self.assertTrue(all(t['mean_background_transmission']==1 and t['depth_range'] is None for t in stats['tiles']))
 def test_tile_coverage_conservation(self):
  pixels,stats=c.cpu(c.scenes()[0]['objects'],0);self.assertEqual(sum(t['shaded_fragment_samples'] for t in stats['tiles']),sum(stats['layer_heatmap']))
 def test_projected_bound(self):
  _,stats=c.cpu(c.scenes()[1]['objects'],0);self.assertTrue(all(t['projected_bounds_fragment_samples']>=t['shaded_fragment_samples'] for t in stats['tiles']))
 def test_culling_preserves_cpu(self):
  for s in c.scenes():
   o=s['objects'];self.assertEqual(c.cpu(o,.3)[0],c.cpu([x for x in o if c.visible(x,.3)],.3)[0])
 def test_errors(self):
  a=[0]*16384;b=list(a);b[0]=255;tiles=c.tile_error(a,b);self.assertEqual(tiles[0]['max_rgba8_error'],255);self.assertEqual(sum(x['max_rgba8_error']>0 for x in tiles),1)
if __name__=='__main__':unittest.main()
