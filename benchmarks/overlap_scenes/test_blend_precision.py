import unittest
import blend_precision as b
class BlendPrecisionTests(unittest.TestCase):
 def test_half(self):self.assertEqual(b.half(.5),.5);self.assertNotEqual(b.half(.1),.1)
 def test_round(self):self.assertEqual(b.q8(.5),128/255)
 def test_empty(self):self.assertEqual(b.reference([],0,'linear'),[0]*16384)
 def test_goldens_distinct(self):
  o=b.t.scene(24);self.assertNotEqual(b.reference(o,0,'ideal8'),b.reference(o,0,'linear'))
 def test_half_close_to_linear(self):
  o=b.t.scene(24);self.assertLessEqual(b.summary(b.reference(o,0,'half'),b.reference(o,0,'linear'))['max_error'],1)
 def test_source_model_is_diagnostic(self):
  o=b.t.scene(8);self.assertNotEqual(b.reference(o,0,'ideal8'),b.reference(o,0,'source8'))
 def test_float32_missing_capability(self):
  h=object.__new__(b.FloatHost);h.metadata={'extensions':['GL_EXT_color_buffer_float']}
  with self.assertRaisesRegex(RuntimeError,'capabilities absent'):h.draw([],0,full_float=True)
 def test_half_missing_capability(self):
  h=object.__new__(b.FloatHost);h.metadata={'extensions':[]}
  with self.assertRaisesRegex(RuntimeError,'capability absent'):h.draw([],0)
if __name__=='__main__':unittest.main()
