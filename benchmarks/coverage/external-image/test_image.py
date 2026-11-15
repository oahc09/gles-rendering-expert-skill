import unittest,json,hashlib
from pathlib import Path
P=Path(__file__).parent
class Tests(unittest.TestCase):
 def reports(self):return [json.loads((P/(n+'.json')).read_text()) for n in ['mesa','angle']]
 def test_real_sampling(self):
  expected=[v for y in range(4) for x in range(4) for v in (17+31*x+7*y,23+11*x+43*y,31+19*x+13*y,97+17*x+23*y)]
  for r in self.reports():
   self.assertEqual(r['status'],'HOST_PASS')
   for k in ['sampler2D_fallback','external_before_destroy','external_after_destroy']:self.assertEqual(r[k]['pixels'],expected);self.assertEqual(r[k]['max_byte_error'],0)
 def test_oracle_rejects_combined_transform_and_alpha_loss(self):
  rgba=lambda x,y:[17+31*x+7*y,23+11*x+43*y,31+19*x+13*y,97+17*x+23*y]
  expected=[v for y in range(4) for x in range(4) for v in rgba(x,y)]
  swapped=[v for y in range(4) for x in range(4) for v in [rgba(y,x)[1],rgba(y,x)[0],rgba(y,x)[2],rgba(y,x)[3]]]
  opaque=[255 if i%4==3 else v for i,v in enumerate(expected)]
  self.assertNotEqual(expected,swapped);self.assertNotEqual(expected,opaque)
 def test_image_lifecycle(self):
  for r in self.reports():self.assertTrue(r['create_image_success']);self.assertTrue(r['destroy_image_success']);self.assertEqual(r['destroy_egl_error'],0x3000)
 def test_defined_parameter_checks(self):
  for r in self.reports():
   self.assertEqual(len(r['parameter_checks']),3)
   for n in r['parameter_checks']:self.assertEqual(n['error'],n['expected'])
 def test_wrap_extension_changes_contract(self):
  for r in self.reports():
   n=next(x for x in r['parameter_checks'] if x['case']=='repeat-wrap');self.assertEqual(n['expected'],0 if r['external_wrap_modes_advertised'] else 0x500)
 def test_disabled_real_fallback(self):
  for n in ['mesa','angle']:
   r=json.loads((P/(n+'-disabled.json')).read_text());self.assertEqual(r['external_calls'],0);self.assertEqual(r['status'],'SAFE_FALLBACK_PASS');self.assertEqual(r['sampler2D_fallback']['max_byte_error'],0)
 def test_bindings_and_privacy(self):
  for n in ['mesa','angle','mesa-disabled','angle-disabled']:
   text=(P/(n+'.json')).read_text();r=json.loads(text);self.assertEqual(r['source_sha256'],hashlib.sha256((P/'run.py').read_bytes()).hexdigest());self.assertNotIn('/tmp/',text);self.assertNotIn('renderer',text);self.assertEqual(r['AHardwareBuffer'],'NOT_RUN')
 def test_initial_bad_oracle_preserved(self):
  r=json.loads((P/'initial-attempt/angle.json').read_text());self.assertEqual(r['status'],'FAIL');self.assertEqual(r['source_sha256'],hashlib.sha256((P/'initial-attempt/run.py').read_bytes()).hexdigest())
if __name__=='__main__':unittest.main()
