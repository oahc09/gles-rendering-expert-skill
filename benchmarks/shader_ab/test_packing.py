import unittest
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('packing_tests',Path(__file__).with_name('packing.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class PackingTests(unittest.TestCase):
 def test_unsigned_extremes(self):self.assertEqual(p.pack([1,1,1,1],False),0xffffffff);self.assertEqual(p.pack([0,0,0,0],False),0)
 def test_signed_extremes(self):self.assertEqual(p.pack([-1,-1,-1,-1],True),0x81818181);self.assertEqual(p.pack([1]*4,True),0x7f7f7f7f)
 def test_signed_negative128_clamps(self):self.assertEqual(p.unpack(0x80808080,True),[-1]*4)
 def test_clamp(self):self.assertEqual(p.pack([-2,2,0,0],False),0xff00)
 def test_channel_order(self):self.assertEqual(p.bytes_rgba(0x01020304),[4,3,2,1])
 def test_case_count(self):self.assertEqual(len(p.cases()),8);self.assertTrue(all(len(c['golden'])==64 for c in p.cases()))
 def test_no_gl_failure_as_pixel_failure(self):self.assertEqual(p.compare({'status':'COMPILE_FAILED'},[0]*64)['status'],'UNKNOWN')
 def test_highp_before_shift(self):s=p.source(p.cases()[0],'fixed');self.assertIn('highp uint b=uint(v.y);',s);self.assertIn('(b<<8u)',s)
 def test_fixed_unpack_highp(self):c=next(c for c in p.cases() if c['id']=='snorm-unpack-0');self.assertIn('highp int a=',p.source(c,'fixed'))
 def test_legacy_distinct(self):self.assertNotEqual(p.source(p.cases()[0],'fixed'),p.source(p.cases()[0],'legacy'))
 def test_rounding_defined_inputs(self):self.assertEqual(p.nearest(-1.6),-2);self.assertEqual(p.nearest(1.6),2)
 def test_invalid_pixels_cannot_be_negative_success(self):
  for value in (float('nan'),True,-1,256):
   r=dict(status='EXECUTED',compile=True,link=True,harness_gl_error=0,pixels=[value]*64)
   self.assertEqual(p.compare(r,[0]*64)['status'],'UNKNOWN')
 def test_compile_and_link_required(self):
  for field in ('compile','link'):
   r=dict(status='EXECUTED',compile=True,link=True,harness_gl_error=0,pixels=[0]*64);r[field]=False
   self.assertEqual(p.compare(r,[0]*64)['status'],'UNKNOWN')
if __name__=='__main__':unittest.main()
