import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('advanced_tests_target',Path(__file__).with_name('advanced.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

class AdvancedTests(unittest.TestCase):
    def test_ubo_300(self): self.assertIn('#version 300 es',a.sources('ubo')['shader.frag']);self.assertIn('std140',a.sources('ubo')['shader.frag'])
    def test_ssbo_310(self): self.assertIn('#version 310 es',a.sources('ssbo')['shader.frag'])
    def test_compute_present(self): self.assertIn('shader.comp',a.sources('compute'))
    def test_discard_golden(self): self.assertEqual(a.golden('discard')[:8],[0]*8);self.assertEqual(a.golden('discard')[8:12],[64,128,191,255])
    def test_depth_golden(self): self.assertEqual(a.golden('depth'),[0]*64)
    def test_unknown_not_pass(self):self.assertEqual(a.quality({'status':'SKIP_UNSUPPORTED'},[0]*64),'UNKNOWN')
    def test_error_not_pass(self):self.assertEqual(a.quality({'status':'EXECUTED','harness_gl_error':1,'pixels':[0]*64},[0]*64),'UNKNOWN')
    def test_negative_differs(self): self.assertNotEqual(a.sources('ubo'),a.sources('ubo',True))
    def test_real_pixels_contract(self):self.assertEqual(a.quality({'status':'EXECUTED','compile':True,'link':True,'harness_gl_error':0,'pixels':[0]*64},[255]*64),'FAIL')

    def test_invalid_pixel_values(self):
        for v in (float('nan'),float('inf'),True,-1,256):
            with self.subTest(value=v):
                self.assertEqual(a.quality({'status':'EXECUTED','compile':True,'link':True,'pixels':[v]*64},[0]*64),'UNKNOWN')
    def test_missing_compile_rejected(self):
        self.assertEqual(a.quality({'status':'EXECUTED','pixels':[0]*64},[0]*64),'UNKNOWN')

if __name__=='__main__':unittest.main()
