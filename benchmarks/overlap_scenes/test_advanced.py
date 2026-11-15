import math,unittest
import advanced as a
class Advanced(unittest.TestCase):
 def test_covariance_symmetric(self):
  c=a.covariance(.2,.05,.1,.4);self.assertEqual(c[0][1],c[1][0]);self.assertNotEqual(c[0][1],0)
 def test_covariance_rotation_trace(self):
  c=a.covariance(.2,.05,.1,.4);self.assertAlmostEqual(c[0][0]+c[1][1],.2**2+.05**2)
 def test_projected_positive(self):
  for o in a.objects():
   rect,inv=a.project_gaussian(o,.3);self.assertGreater(inv[0]*inv[2]-inv[1]**2,0);self.assertGreater(rect[2],0)
 def test_perspective_depth_variance(self):
  o=a.objects()[2];_,i=a.project_gaussian(o,0);_,j=a.project_gaussian(o,.3);self.assertNotEqual(i,j)
 def test_invalid_covariance(self):
  o=dict(a.objects()[0],covariance=[[0]*3 for _ in range(3)])
  with self.assertRaises(ValueError):a.project_gaussian(o,0)
 def test_sorted(self):self.assertEqual([o['z'] for o in a.objects()],sorted([o['z'] for o in a.objects()],reverse=True))
 def test_lod_accepted(self):
  r=a.lod_plan(a.objects());self.assertEqual(r['status'],'ACCEPT_BOUNDED_LOD');self.assertEqual(len(r['removed_ids']),2);self.assertLessEqual(r['predicted_max_channel_error'],r['budget'])
 def test_lod_rejected(self):
  obs=a.objects();r=a.lod_plan(obs,force_unsafe=True);self.assertEqual(r['status'],'FALLBACK_BASELINE');self.assertEqual(r['objects'],obs)
 def test_lod_zero_budget(self):self.assertEqual(a.lod_plan(a.objects(),budget=0)['status'],'FALLBACK_BASELINE')
 def test_normal_incidence(self):self.assertEqual(a.refraction(0,0,2),[0,0])
 def test_thickness_linear(self):
  x=a.refraction(.5,.3,1);y=a.refraction(.5,.3,2);self.assertEqual(y,[2*z for z in x])
 def test_snell_bends(self):self.assertLess(a.refraction(.5,0,2)[0],0)
 def test_texture_centers(self):self.assertEqual(a.sample([.5/16,.5/16]),[0,0,0])
 def test_texture_clamp(self):self.assertEqual(a.sample([-1,-1]),[0,0,0])
 def test_cpu_lod_bound(self):
  obs=a.objects();r=a.lod_plan(obs);x,_=a.cpu(obs,0);y,_=a.cpu(r['objects'],0);self.assertLessEqual(max(abs(c-d) for c,d in zip(x,y))/255,r['predicted_max_channel_error'])
 def test_glass_cpu_has_pixels(self):self.assertGreater(sum(a.cpu(a.glass_objects(),0,True)[0]),0)
 def test_spatial_gaussian_heat(self):
  _,h=a.cpu(a.objects(),0);self.assertGreater(max(h),2);self.assertEqual(min(h),0)
if __name__=='__main__':unittest.main()
