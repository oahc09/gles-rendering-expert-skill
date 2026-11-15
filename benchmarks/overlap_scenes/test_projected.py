import unittest
import projected as p
class Projected(unittest.TestCase):
 def test_count(self):self.assertEqual(len(p.scenes()),4)
 def test_64(self):self.assertEqual(p.SIZE,64)
 def test_projection(self):self.assertEqual(p.project(dict(x=1,y=2,z=2,radius=.5),0),[.5,1,.25,.25])
 def test_camera_parallax(self):
  far=dict(x=0,y=0,z=4,radius=.5);near=dict(far,z=2)
  self.assertEqual(p.project(near,.2)[0],2*p.project(far,.2)[0])
 def test_cull_keeps_visible(self):
  for s in p.scenes():
   for c in (-.3,0,.3):self.assertEqual(len(p.arms(s,c)['offscreen_culling']),len(s['objects'])-2)
 def test_cull_cpu_identical(self):
  for s in p.scenes():
   a=p.arms(s,0);self.assertEqual(p.cpu(a['baseline'],0),p.cpu(a['offscreen_culling'],0))
 def test_negative_cpu_different(self):
  for s in p.scenes():
   a=p.arms(s,0);self.assertNotEqual(p.cpu(a['baseline'],0)[0],p.cpu(a['bad_foreground_drop'],0)[0])
 def test_spatial_heat(self):
  for s in p.scenes():
   _,heat=p.cpu(s['objects'],0);self.assertEqual(len(heat),4096);self.assertEqual(min(heat),0);self.assertGreater(max(heat),2)
 def test_metric_reject_size(self):
  with self.assertRaises(ValueError):p.metrics([],[])
 def test_metric_reject_nan(self):
  with self.assertRaises(ValueError):p.metrics([float('nan')]*16384,[0]*16384)
 def test_zero_alpha(self):self.assertIsNone(p.metrics([0]*16384,[0]*16384)['centroid_error_pixels'])
 def test_shader_sources(self):self.assertTrue(p.VERT.startswith('#version 300 es'));self.assertIn('exp(-3.0',p.FRAG)
if __name__=='__main__':unittest.main()
