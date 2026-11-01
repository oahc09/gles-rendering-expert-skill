import importlib.util
import json
from pathlib import Path
import unittest
from interactive import render
from numeric_reference import reference,evaluate
ROOT=Path(__file__).resolve().parents[2]
class Contracts(unittest.TestCase):
 def test_three_simulations(self):
  text=(ROOT/'examples/system_scenes/simulation.cpp').read_text()
  for name in ('particle','boids','wave'):self.assertIn('"'+name+'"',text)
 def test_barrier_consumer_classes(self):
  text=(ROOT/'examples/system_scenes/simulation.cpp').read_text()
  for barrier in ('GL_SHADER_STORAGE_BARRIER_BIT','GL_SHADER_IMAGE_ACCESS_BARRIER_BIT','GL_TEXTURE_FETCH_BARRIER_BIT','GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT','GL_BUFFER_UPDATE_BARRIER_BIT'):self.assertIn(barrier,text)
 def test_invalid_nan_interaction(self):
  with self.assertRaises(ValueError):render('/not-executed',{'scene':'glass','touch':float('nan')})
 def test_invalid_scene_not_shell(self):
  with self.assertRaises(ValueError):render('/not-executed',{'scene':'glass; shell','touch':0})
 def test_interaction_out_of_bounds(self):
  with self.assertRaises(ValueError):render('/not-executed',{'scene':'glass','touch':2})
 def test_interaction_extra_arguments(self):
  with self.assertRaises(ValueError):render('/not-executed',{'scene':'glass','touch':0,'command':'bad'})
 def test_oracle_identity_12(self):
  for group in range(1,13):self.assertTrue(evaluate(group,32,32,reference(group,32,32))['pass'])
 def test_black_corruption_detected(self):
  for group in range(1,13):self.assertFalse(evaluate(group,32,32,[0]*3072)['pass'])
 def test_fallback_shader_300(self):
  text=(ROOT/'examples/system_scenes/effects.cpp').read_text();self.assertIn('#version 300 es',text);self.assertIn('glUniform4fv',text)
 def test_half_float_probe_and_explicit_fallback(self):
  text=(ROOT/'examples/system_scenes/effects.cpp').read_text();self.assertIn('rgba16f_renderable()',text);self.assertIn('glCheckFramebufferStatus',text);self.assertIn('GLES_TEST_FORCE_NO_RGBA16F',text);self.assertIn('BLOCKED_BY_CAPABILITY',text)
if __name__=='__main__':unittest.main()
