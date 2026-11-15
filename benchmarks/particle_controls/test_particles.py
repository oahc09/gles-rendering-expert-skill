import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('particle_controls',Path(__file__).with_name('run.py'));p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
class Particles(unittest.TestCase):
 def test_position_count(self):self.assertEqual(len(p.positions(0)),16)
 def test_position_motion(self):self.assertEqual(p.positions(2)[:2],[9.5,7.5])
 def test_particle_index(self):self.assertEqual(p.positions(0)[2::4],[0.,1.,2.,3.])
 def test_frame_difference(self):self.assertNotEqual(p.golden(0),p.golden(1))
 def test_coverage(self):self.assertEqual(sum(x!=0 for x in p.golden(0)[3::4]),36)
 def test_all_frames_inbounds(self):
  for f in (0,1,2):self.assertEqual(sum(x!=0 for x in p.golden(f)[3::4]),36)
 def test_exact(self):self.assertEqual(p.compare_image(p.golden(0),p.golden(0))['status'],'PASS')
 def test_wrong_frame(self):self.assertEqual(p.compare_image(p.golden(0),p.golden(1))['status'],'FAIL')
 def test_invalid_size(self):self.assertEqual(p.compare_image([],[])['status'],'INVALID')
 def test_nan(self):self.assertEqual(p.compare_image([float('nan')]*4096,p.golden(0))['status'],'INVALID')
 def test_bool(self):self.assertEqual(p.compare_image([False]*4096,p.golden(0))['status'],'INVALID')
 def test_barrier_consumer(self):self.assertTrue(p.BARRIER&0x2000)
 def test_barrier_mapping(self):self.assertTrue(p.BARRIER&0x200)
 def test_bounds_guard(self):self.assertIn('if(i>=4u)return',p.COMPUTE)
 def test_readonly_consumer(self):self.assertIn('readonly buffer',p.VERTEX)
if __name__=='__main__':unittest.main()
