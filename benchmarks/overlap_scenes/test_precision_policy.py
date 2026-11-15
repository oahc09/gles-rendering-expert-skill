import unittest
from precision_policy import choose
EXT=['GL_EXT_color_buffer_float','GL_EXT_float_blend']
B=dict(max_allocation_bytes=81920,max_logical_transfer_bytes=10000000,max_renderbuffer_size=4096)
class PrecisionPolicy(unittest.TestCase):
 def call(self,quality=None,budget=None,ext=EXT,target='linear'):
  return choose(64,64,48,ext,quality or {'RGBA8':False,'RGBA16F':False,'RGBA32F':True},target,budget or B)
 def test_cost_not_free(self):
  d=self.call();self.assertEqual(d['selected'],'RGBA32F');r=d['candidates'][-1];self.assertEqual(r['logical_allocation_bytes'],81920);self.assertEqual(r['allocation_ratio_to_rgba8'],5);self.assertEqual(r['logical_transfer_upper_bytes'],6373376)
 def test_cheapest_passing(self):self.assertEqual(self.call(dict.fromkeys(('RGBA8','RGBA16F','RGBA32F'),True))['selected'],'RGBA8')
 def test_memory_reject(self):
  d=self.call(budget={**B,'max_allocation_bytes':81919});self.assertIsNone(d['selected'])
 def test_transfer_reject(self):
  self.assertIsNone(self.call(budget={**B,'max_logical_transfer_bytes':1})['selected'])
 def test_dimensions_reject(self):
  self.assertIsNone(self.call(budget={**B,'max_renderbuffer_size':63})['selected'])
 def test_missing_blend(self):self.assertIsNone(self.call(ext=['GL_EXT_color_buffer_float'])['selected'])
 def test_missing_color(self):self.assertIsNone(self.call(ext=['GL_EXT_float_blend'])['selected'])
 def test_quality_fallback(self):
  q={'RGBA8':True,'RGBA16F':False,'RGBA32F':True}
  self.assertEqual(self.call(q,budget={**B,'max_allocation_bytes':16384})['selected'],'RGBA8')
 def test_no_failed_fallback(self):
  self.assertEqual(self.call(dict.fromkeys(('RGBA8','RGBA16F','RGBA32F'),False))['status'],'UNAVAILABLE')
 def test_half_supported(self):
  q={'RGBA8':False,'RGBA16F':True,'RGBA32F':False}
  self.assertEqual(self.call(q,ext=['GL_EXT_color_buffer_half_float'])['selected'],'RGBA16F')
 def test_contract_required(self):
  with self.assertRaises(ValueError):self.call(target='automatic')
 def test_truthy_not_quality(self):
  with self.assertRaises(ValueError):self.call({'RGBA8':1,'RGBA16F':False,'RGBA32F':True})
 def test_invalid_dimension(self):
  with self.assertRaises(ValueError):choose(True,64,48,EXT,{},'linear',B)
 def test_zero_budget(self):
  self.assertIsNone(self.call(budget={**B,'max_allocation_bytes':0})['selected'])
